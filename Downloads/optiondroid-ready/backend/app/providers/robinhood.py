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
import time
from functools import partial
from pathlib import Path
from typing import List, Optional

import httpx
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
_TOKEN_URL      = "https://api.robinhood.com/oauth2/token/"
_CLIENT_ID      = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"

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

    async def _try_refresh_token(self) -> bool:
        """
        Use the refresh_token + device_token stored in the pickle to obtain
        a new access_token without any user interaction.

        This is the key to making Robinhood work on Railway:
        - The device_token in the pickle is already trusted (approved once locally)
        - Robinhood accepts refresh_token grants from trusted devices without re-challenging
        - The new access_token is written back to the pickle and re-injected into the session
        """
        if not _PICKLE_PATH.exists():
            return False
        try:
            with open(_PICKLE_PATH, "rb") as fh:
                session_data = _pickle.load(fh)
        except Exception as exc:
            logger.warning(f"Robinhood: could not read pickle for token refresh: {exc}")
            return False

        refresh_token = session_data.get("refresh_token", "")
        device_token  = session_data.get("device_token", "")
        if not refresh_token:
            logger.warning("Robinhood: pickle has no refresh_token — cannot refresh.")
            return False

        logger.info("Robinhood: attempting token refresh using stored refresh_token.")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    _TOKEN_URL,
                    data={
                        "grant_type":    "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id":     _CLIENT_ID,
                        "expires_in":    86400,
                        "scope":         "internal",
                        "device_token":  device_token,
                    },
                )
        except Exception as exc:
            logger.warning(f"Robinhood: token refresh request failed: {exc}")
            return False

        if resp.status_code != 200:
            logger.warning(
                f"Robinhood: token refresh returned HTTP {resp.status_code} — "
                "refresh token may be expired. Re-run save_login.py to re-authenticate."
            )
            return False

        data = resp.json()
        new_access  = data.get("access_token", "")
        new_refresh = data.get("refresh_token", refresh_token)  # RH may issue a new one
        token_type  = data.get("token_type", "Bearer")

        if not new_access:
            logger.warning("Robinhood: token refresh response contained no access_token.")
            return False

        # Persist updated tokens back to the pickle
        session_data["access_token"]  = new_access
        session_data["refresh_token"] = new_refresh
        session_data["token_type"]    = token_type
        try:
            _PICKLE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_PICKLE_PATH, "wb") as fh:
                _pickle.dump(session_data, fh)
        except Exception as exc:
            logger.warning(f"Robinhood: could not write refreshed pickle: {exc}")
            # Continue anyway — the new token is injected into the session below

        rh_helper.update_session("Authorization", f"{token_type} {new_access}")
        rh_helper.set_login_state(True)
        logger.info("Robinhood: token refreshed successfully. Session updated.")
        return True

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
                # Immediately try token refresh so we start with a fresh access
                # token rather than a potentially-stale one. This is what keeps
                # Railway working across container restarts and redeployments:
                # the device_token in the pickle is already trusted, so Robinhood
                # issues a new access_token without triggering device verification.
                refreshed = await self._try_refresh_token()
                if not refreshed:
                    logger.warning(
                        "Robinhood: token refresh failed; proceeding with pickle token "
                        "(may expire soon). Will retry refresh on next auth failure."
                    )
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
        """
        Run a blocking robin_stocks call in a thread pool.
        If the call raises a 401-style error (expired access token), attempt
        one token refresh and retry before propagating the failure.
        """
        await self._ensure_auth()
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, partial(fn, *args, **kwargs))
        except Exception as exc:
            msg = str(exc).lower()
            if "401" in msg or "unauthorized" in msg or "not logged in" in msg:
                logger.warning(
                    "Robinhood: 401/unauthorized on API call — attempting token refresh."
                )
                self._authenticated = False
                refreshed = await self._try_refresh_token()
                if refreshed:
                    self._authenticated = True
                    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))
                else:
                    self._login_failed = True
                    self._login_error  = (
                        "Access token expired and refresh failed. "
                        "Re-run save_login.py locally and update RH_PICKLE_B64 in Railway."
                    )
                    raise RuntimeError(
                        f"Robinhood session expired: {self._login_error}"
                    ) from exc
            raise

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
