"""
Robinhood options data provider using robin_stocks.

Performance design (two-phase bulk fetch):
  Phase 1 — Instruments: one paginated call fetches all instrument metadata
             (strike, expiry, type) for N expirations. ~2-3s for SPY.
  Phase 2 — Market data: batched calls of 200 instrument IDs per request,
             running all batches concurrently. ~0.5-1s total.
  Total cold fetch for SPY (6 expirations, ~2000 contracts): ~3-4s.

Provider is swappable: implement OptionsDataProvider ABC in polygon.py / tradier.py.

Auth strategy (in priority order):
  1. RH_PICKLE_B64 env var → decode pickle → verify token → skip password login.
  2. Existing ~/.tokens/robinhood.pickle → verify token → skip password login.
  3. RH_USERNAME + RH_PASSWORD (+ optional RH_MFA_SECRET) → fresh login.
  Failure is cached: after the first permanent failure, all subsequent requests
  return the same classified error without re-attempting login.
"""
import asyncio
import base64
import logging
import pickle as _pickle
from functools import partial
from pathlib import Path
from typing import List, Optional

import pyotp
import robin_stocks.robinhood as rh
import robin_stocks.robinhood.helper as rh_helper
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import OptionsDataProvider
from app.config import settings

logger = logging.getLogger(__name__)

INSTRUMENTS_URL = "https://api.robinhood.com/options/instruments/"
MARKETDATA_URL  = "https://api.robinhood.com/marketdata/options/"
MDATA_BATCH     = 200   # IDs per market-data request (~8KB URL, well under limits)

_PICKLE_PATH = Path.home() / ".tokens" / "robinhood.pickle"


class RobinhoodProvider(OptionsDataProvider):
    _authenticated: bool = False
    _login_failed: bool = False
    _login_error: str = ""
    _lock = asyncio.Lock()
    _chain_id_cache: dict = {}

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _restore_pickle(self) -> None:
        """If RH_PICKLE_B64 is set, decode it and write to the standard pickle path."""
        if not settings.rh_pickle_b64:
            return
        _PICKLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not _PICKLE_PATH.exists():
            try:
                data = base64.b64decode(settings.rh_pickle_b64)
                _PICKLE_PATH.write_bytes(data)
                logger.info(f"Restored Robinhood session pickle ({len(data)} bytes).")
            except Exception as exc:
                logger.warning(f"Failed to restore pickle from RH_PICKLE_B64: {exc}")

    def _try_activate_pickle(self) -> bool:
        """
        Load existing pickle, inject the Bearer token into the robin_stocks
        session, and return True if the pickle contained a non-empty token.
        Does NOT verify the token against the network — that happens lazily on
        the first real API call.
        """
        if not _PICKLE_PATH.exists():
            return False
        try:
            with open(_PICKLE_PATH, "rb") as fh:
                session_data = _pickle.load(fh)
            token = session_data.get("access_token", "")
            token_type = session_data.get("token_type", "Bearer")
            if not token:
                logger.debug("Pickle exists but contains no access_token.")
                return False
            rh_helper.update_session("Authorization", f"{token_type} {token}")
            rh_helper.set_login_state(True)
            logger.info("Robinhood: activated session from pickle (token not yet network-verified).")
            return True
        except Exception as exc:
            logger.warning(f"Could not load pickle: {exc}")
            return False

    def _classify_login_error(self, message: str) -> str:
        """
        Map a raw exception/response message to a user-friendly classified error.
        Returns the classified string (does NOT set _login_error itself).
        """
        msg = message.lower()
        if "unable to log in" in msg or "invalid credentials" in msg or "credentials" in msg:
            return (
                "Invalid username or password. "
                "Check RH_USERNAME / RH_PASSWORD in Railway Variables."
            )
        if "mfa" in msg or "two-factor" in msg or "otp" in msg:
            return (
                "MFA authentication failed. "
                "Ensure RH_MFA_SECRET is the correct base-32 TOTP secret, not a one-time code."
            )
        if "challenge" in msg or "verification_workflow" in msg or "device" in msg:
            return (
                "Robinhood device/identity challenge required. "
                "Complete the challenge interactively with save_login.py, "
                "then encode the result as RH_PICKLE_B64."
            )
        if "too many" in msg or "rate" in msg or "throttl" in msg:
            return (
                "Robinhood rate-limited this login attempt. "
                "Wait a few minutes before redeploying."
            )
        if "token" in msg and ("expired" in msg or "invalid" in msg):
            return (
                "Stored session token is expired or invalid. "
                "Re-run save_login.py to refresh RH_PICKLE_B64."
            )
        return f"Robinhood login error: {message}"

    async def _ensure_auth(self) -> None:
        async with self._lock:
            if self._authenticated:
                return

            # Cached failure — do not retry on every request.
            if self._login_failed:
                raise RuntimeError(f"Robinhood login unavailable: {self._login_error}")

            # ── Strategy 1: pickle session (preferred, avoids password login) ──
            self._restore_pickle()   # no-op if RH_PICKLE_B64 not set
            if self._try_activate_pickle():
                # Mark authenticated optimistically; first API call will reveal
                # token expiry, which will propagate as a data error (not a login loop).
                self._authenticated = True
                return

            # ── Strategy 2: fresh password login ─────────────────────────────
            if not settings.rh_username or not settings.rh_password:
                self._login_failed = True
                self._login_error = (
                    "No credentials available: set RH_USERNAME + RH_PASSWORD "
                    "(or RH_PICKLE_B64 for a pre-authenticated session) "
                    "in Railway Variables."
                )
                logger.error(f"Robinhood: {self._login_error}")
                raise RuntimeError(f"Robinhood login unavailable: {self._login_error}")

            mfa_code: Optional[str] = None
            if settings.rh_mfa_secret:
                try:
                    mfa_code = pyotp.TOTP(settings.rh_mfa_secret).now()
                    logger.debug("Robinhood: generated TOTP MFA code.")
                except Exception as exc:
                    self._login_failed = True
                    self._login_error = (
                        f"Invalid RH_MFA_SECRET — TOTP generation failed: {exc}. "
                        "RH_MFA_SECRET must be the base-32 TOTP secret, not a numeric code."
                    )
                    logger.error(f"Robinhood: {self._login_error}")
                    raise RuntimeError(f"Robinhood login unavailable: {self._login_error}")

            logger.info(
                f"Robinhood: attempting password login for {settings.rh_username!r} "
                f"(MFA: {'yes' if mfa_code else 'no'})."
            )
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    partial(
                        rh.login,
                        settings.rh_username,
                        settings.rh_password,
                        mfa_code=mfa_code,
                        store_session=True,
                    ),
                )
                self._authenticated = True
                logger.info("Robinhood: password login successful.")
            except Exception as exc:
                raw = str(exc)
                classified = self._classify_login_error(raw)
                self._login_failed = True
                self._login_error = classified
                logger.error(f"Robinhood login failed — {classified} (raw: {raw!r})")
                raise RuntimeError(f"Robinhood login unavailable: {classified}") from exc

    async def _run(self, fn, *args, **kwargs):
        """Run a blocking robin_stocks call in a thread pool."""
        await self._ensure_auth()
        return await asyncio.get_event_loop().run_in_executor(
            None, partial(fn, *args, **kwargs)
        )

    # ── Chain info ────────────────────────────────────────────────────────────

    async def _get_chain_id(self, ticker: str) -> str:
        if ticker not in self._chain_id_cache:
            chains = await self._run(rh.options.get_chains, ticker)
            if not chains:
                raise ValueError(f"No option chain found for {ticker}")
            self._chain_id_cache[ticker] = chains["id"]
        return self._chain_id_cache[ticker]

    # ── Provider interface ────────────────────────────────────────────────────

    async def get_underlying_price(self, ticker: str) -> float:
        quote = await self._run(rh.stocks.get_latest_price, ticker.upper())
        if not quote or not quote[0]:
            raise ValueError(f"No price data for {ticker}")
        return float(quote[0])

    async def get_expirations(self, ticker: str) -> List[str]:
        chains = await self._run(rh.options.get_chains, ticker.upper())
        if not chains:
            raise ValueError(f"No option chain found for {ticker}")
        return sorted(chains.get("expiration_dates", []))

    async def get_option_chain(self, ticker: str, expiration: str) -> List[dict]:
        """Single-expiry shim — delegates to bulk for consistency."""
        return await self.get_option_chain_bulk(ticker.upper(), [expiration])

    async def get_option_chain_bulk(
        self,
        ticker: str,
        expirations: List[str],
    ) -> List[dict]:
        """
        Two-phase bulk fetch for multiple expirations.

        Phase 1: One paginated instruments call (page_size=500) → all strikes/types.
        Phase 2: Concurrent batched market-data calls (200 IDs each) → bid/ask/OI/IV.
        Merge on instrument_id and normalize.
        """
        ticker   = ticker.upper()
        chain_id = await self._get_chain_id(ticker)
        exp_str  = ",".join(expirations)

        # ── Phase 1: instruments ──────────────────────────────────────────────
        inst_url = (
            f"{INSTRUMENTS_URL}"
            f"?chain_id={chain_id}&state=active"
            f"&expiration_dates={exp_str}&page_size=500"
        )

        def _fetch_instruments():
            return rh_helper.request_get(inst_url, "pagination") or []

        instruments = await self._run(_fetch_instruments)
        if not instruments:
            return []

        logger.debug(f"{ticker}: {len(instruments)} instruments for {len(expirations)} expirations")

        # ── Phase 2: market data in parallel batches ───────────────────────────
        ids     = [i["id"] for i in instruments]
        batches = [ids[i: i + MDATA_BATCH] for i in range(0, len(ids), MDATA_BATCH)]

        async def fetch_mdata_batch(batch_ids: List[str]) -> List[dict]:
            url = f"{MARKETDATA_URL}?ids={','.join(batch_ids)}"
            def _get():
                return rh_helper.request_get(url, "results") or []
            return await self._run(_get)

        mdata_batches = await asyncio.gather(*[fetch_mdata_batch(b) for b in batches])
        mdata_list    = [item for batch in mdata_batches for item in batch]

        # Index market data by instrument_id for O(1) merge
        mdata_by_id = {m["instrument_id"]: m for m in mdata_list}

        # ── Merge + normalize ─────────────────────────────────────────────────
        result = []
        for inst in instruments:
            if not inst.get("strike_price"):
                continue
            mdata = mdata_by_id.get(inst["id"], {})
            result.append(self._normalize(inst, mdata, ticker))

        return result

    def _normalize(self, inst: dict, mdata: dict, ticker: str) -> dict:
        def _f(key, src=None, default=0.0):
            src = src or {}
            val = src.get(key)
            try:
                return float(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        def _i(key, src=None, default=0):
            src = src or {}
            val = src.get(key)
            try:
                return int(float(val)) if val is not None else default
            except (TypeError, ValueError):
                return default

        bid  = _f("bid_price",  mdata)
        ask  = _f("ask_price",  mdata)
        last = _f("last_trade_price", mdata)
        mid  = round((bid + ask) / 2, 4) if (bid + ask) > 0 else last
        mark = _f("adjusted_mark_price", mdata) or mid

        return {
            "ticker":             ticker,
            "strike":             _f("strike_price", inst),
            "expiration":         inst.get("expiration_date", ""),
            "option_type":        inst.get("type", ""),
            "bid":                bid,
            "ask":                ask,
            "mid":                mid,
            "last":               last,
            "mark":               mark,
            "volume":             _i("volume",        mdata),
            "open_interest":      _i("open_interest", mdata),
            "implied_volatility": _f("implied_volatility", mdata),
            "delta":              _f("delta", mdata) or None,
            "gamma":              _f("gamma", mdata) or None,
            "theta":              _f("theta", mdata) or None,
            "vega":               _f("vega",  mdata) or None,
            "rho":                _f("rho",   mdata) or None,
        }

    async def health_check(self) -> bool:
        try:
            await self._ensure_auth()
            profile = await self._run(rh.profiles.load_account_profile)
            return profile is not None
        except Exception:
            return False
