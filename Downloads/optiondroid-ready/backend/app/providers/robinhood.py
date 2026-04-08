"""
Robinhood options data provider using robin_stocks.

Performance design (two-phase bulk fetch):
  Phase 1 — Instruments: one paginated call fetches all instrument metadata
             (strike, expiry, type) for N expirations. ~2-3s for SPY.
  Phase 2 — Market data: batched calls of 200 instrument IDs per request,
             running all batches concurrently. ~0.5-1s total.
  Total cold fetch for SPY (6 expirations, ~2000 contracts): ~3-4s.

Provider is swappable: implement OptionsDataProvider ABC in polygon.py / tradier.py.
"""
import asyncio
import base64
import logging
import os
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
        pickle_path = Path.home() / ".tokens" / "robinhood.pickle"
        pickle_path.parent.mkdir(parents=True, exist_ok=True)
        if not pickle_path.exists():
            try:
                data = base64.b64decode(settings.rh_pickle_b64)
                pickle_path.write_bytes(data)
                logger.info(f"Restored Robinhood session pickle ({len(data)} bytes).")
            except Exception as exc:
                logger.warning(f"Failed to restore pickle: {exc}")

    async def _ensure_auth(self) -> None:
        async with self._lock:
            if self._authenticated:
                return
            # Don't retry if a previous login attempt already failed permanently.
            if self._login_failed:
                raise RuntimeError(f"Robinhood login unavailable: {self._login_error}")
            # Fail fast — never call rh.login with empty credentials because
            # robin_stocks falls back to interactive input() prompts, which
            # raise EOFError on Railway (no terminal).
            if not settings.rh_username or not settings.rh_password:
                self._login_failed = True
                self._login_error = (
                    "RH_USERNAME and RH_PASSWORD environment variables must be set. "
                    "Configure them in the Railway dashboard."
                )
                logger.error(f"Robinhood login skipped: {self._login_error}")
                raise RuntimeError(self._login_error)
            self._restore_pickle()
            try:
                mfa_code: Optional[str] = None
                if settings.rh_mfa_secret:
                    mfa_code = pyotp.TOTP(settings.rh_mfa_secret).now()
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    partial(rh.login, settings.rh_username, settings.rh_password,
                            mfa_code=mfa_code, store_session=True),
                )
                self._authenticated = True
                logger.info("Robinhood session established.")
            except Exception as exc:
                self._login_failed = True
                self._login_error = str(exc)
                logger.error(f"Robinhood login failed: {exc}")
                raise RuntimeError(f"Robinhood authentication error: {exc}") from exc

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
