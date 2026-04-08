"""
Charles Schwab Trader API — options data provider.

Auth: OAuth2 authorization_code flow.
  - Initial token setup: run `python schwab_auth.py` locally once.
  - Deploy SCHWAB_REFRESH_TOKEN to Railway.
  - Access tokens are auto-refreshed every 29 minutes (30-min TTL).
  - Refresh tokens expire in 7 days — re-run schwab_auth.py to renew.

Env vars required:
  SCHWAB_CLIENT_ID      - App key from developer.schwab.com
  SCHWAB_CLIENT_SECRET  - App secret from developer.schwab.com
  SCHWAB_REFRESH_TOKEN  - Long-lived token from initial OAuth dance

API docs: https://developer.schwab.com/products/trader-api--individual
"""
import asyncio
import base64
import logging
import time
from typing import List, Optional

import httpx

from .base import OptionsDataProvider
from app.config import settings

logger = logging.getLogger(__name__)

_TOKEN_URL    = "https://api.schwabapi.com/v1/oauth/token"
_QUOTES_URL   = "https://api.schwabapi.com/marketdata/v1/quotes"
_CHAINS_URL   = "https://api.schwabapi.com/marketdata/v1/chains"

# Access tokens live 30 minutes; refresh with 60 s margin.
_ACCESS_TOKEN_TTL = 30 * 60 - 60   # seconds


class SchwabProvider(OptionsDataProvider):

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _check_config(self):
        missing = [
            v for v in ("schwab_client_id", "schwab_client_secret", "schwab_refresh_token")
            if not getattr(settings, v, "")
        ]
        if missing:
            raise RuntimeError(
                f"Schwab provider is missing required env vars: "
                f"{[v.upper() for v in missing]}. "
                f"Run schwab_auth.py locally to generate SCHWAB_REFRESH_TOKEN, "
                f"then add all three to Railway Variables."
            )

    async def _get_access_token(self) -> str:
        """Return a valid access token, refreshing if expired."""
        async with self._lock:
            if self._access_token and time.monotonic() < self._token_expires_at:
                return self._access_token

            self._check_config()
            logger.info("Schwab: refreshing access token via refresh_token grant.")

            creds = base64.b64encode(
                f"{settings.schwab_client_id}:{settings.schwab_client_secret}".encode()
            ).decode()

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    _TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {creds}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": settings.schwab_refresh_token,
                    },
                )

            if resp.status_code == 401:
                raise RuntimeError(
                    "Schwab: token refresh returned 401 — client_id or client_secret is wrong."
                )
            if resp.status_code == 400:
                body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                err = body.get("error", "")
                desc = body.get("error_description", resp.text[:200])
                if err in ("invalid_grant", "invalid_token"):
                    raise RuntimeError(
                        f"Schwab: refresh token is expired or invalid ({desc}). "
                        f"Re-run schwab_auth.py locally to generate a new SCHWAB_REFRESH_TOKEN."
                    )
                raise RuntimeError(f"Schwab: token refresh failed — {desc}")
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Schwab: token refresh HTTP {resp.status_code} — {resp.text[:200]}"
                )

            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires_at = time.monotonic() + _ACCESS_TOKEN_TTL
            logger.info("Schwab: access token refreshed, valid for ~29 minutes.")
            return self._access_token

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ── Provider interface ────────────────────────────────────────────────────

    async def get_underlying_price(self, ticker: str) -> float:
        token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                _QUOTES_URL,
                headers=self._auth_headers(token),
                params={"symbols": ticker.upper(), "fields": "quote"},
            )
        self._raise_for_status(resp, f"quote/{ticker}")
        data = resp.json()
        entry = data.get(ticker.upper(), {})
        quote = entry.get("quote", {})
        price = (
            quote.get("lastPrice")
            or quote.get("askPrice")
            or quote.get("bidPrice")
        )
        if not price:
            raise ValueError(f"No price data returned for {ticker} from Schwab.")
        logger.debug(f"Schwab: {ticker} price = {price}")
        return float(price)

    async def get_expirations(self, ticker: str) -> List[str]:
        """
        Schwab has no dedicated expirations endpoint.
        Fetch the chain with strikeCount=1 to get the expiration date map cheaply.
        """
        token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                _CHAINS_URL,
                headers=self._auth_headers(token),
                params={
                    "symbol": ticker.upper(),
                    "contractType": "CALL",
                    "strikeCount": 1,
                },
            )
        self._raise_for_status(resp, f"expirations/{ticker}")
        data = resp.json()
        exp_map = data.get("callExpDateMap", {})
        # Keys are formatted "YYYY-MM-DD:DTE" — strip the DTE suffix.
        dates = sorted({k.split(":")[0] for k in exp_map.keys()})
        logger.debug(f"Schwab: {ticker} expirations = {dates}")
        return dates

    async def get_option_chain(self, ticker: str, expiration: str) -> List[dict]:
        return await self.get_option_chain_bulk(ticker, [expiration])

    async def get_option_chain_bulk(
        self,
        ticker: str,
        expirations: List[str],
    ) -> List[dict]:
        """
        Fetch all requested expirations in ONE Schwab API call.
        Schwab returns the full chain; we filter to the requested expirations.
        """
        token = await self._get_access_token()
        exp_set = set(expirations)
        from_date = min(expirations)
        to_date   = max(expirations)

        logger.info(
            f"Schwab: fetching option chain for {ticker} "
            f"({len(expirations)} expirations, {from_date} → {to_date})"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                _CHAINS_URL,
                headers=self._auth_headers(token),
                params={
                    "symbol":                  ticker.upper(),
                    "contractType":            "ALL",
                    "strikeCount":             50,
                    "includeUnderlyingQuote":  "false",
                    "fromDate":                from_date,
                    "toDate":                  to_date,
                },
            )
        self._raise_for_status(resp, f"chains/{ticker}")
        data = resp.json()

        contracts: List[dict] = []
        for side_key in ("callExpDateMap", "putExpDateMap"):
            exp_map = data.get(side_key, {})
            for exp_key, strikes in exp_map.items():
                # exp_key = "2025-04-18:3" — date:DTE
                exp_date = exp_key.split(":")[0]
                if exp_date not in exp_set:
                    continue
                for _strike_str, option_list in strikes.items():
                    for o in option_list:
                        normalized = self._normalize(o, ticker)
                        if normalized:
                            contracts.append(normalized)

        logger.info(f"Schwab: {ticker} → {len(contracts)} contracts fetched.")
        return contracts

    def _normalize(self, o: dict, ticker: str) -> Optional[dict]:
        def _f(key, default=0.0):
            val = o.get(key)
            try:
                return float(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        def _i(key, default=0):
            val = o.get(key)
            try:
                return int(float(val)) if val is not None else default
            except (TypeError, ValueError):
                return default

        strike = _f("strikePrice")
        if not strike:
            return None

        bid  = _f("bid")
        ask  = _f("ask")
        last = _f("last")
        mid  = round((bid + ask) / 2, 4) if (bid + ask) > 0 else last

        # Schwab returns IV as a percentage (e.g. 27.5 = 27.5% IV).
        # Normalize to decimal fraction to match the rest of the app.
        raw_iv = _f("volatility")
        iv = round(raw_iv / 100.0, 6) if raw_iv else 0.0

        def _greek(key) -> Optional[float]:
            val = o.get(key)
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        opt_type = (o.get("putCall") or "").lower()  # "call" | "put"

        return {
            "ticker":             ticker.upper(),
            "strike":             strike,
            "expiration":         o.get("expirationDate", ""),
            "option_type":        opt_type,
            "bid":                bid,
            "ask":                ask,
            "mid":                mid,
            "last":               last,
            "mark":               mid,
            "volume":             _i("totalVolume"),
            "open_interest":      _i("openInterest"),
            "implied_volatility": iv,
            "delta":              _greek("delta"),
            "gamma":              _greek("gamma"),
            "theta":              _greek("theta"),
            "vega":               _greek("vega"),
            "rho":                _greek("rho"),
        }

    async def health_check(self) -> bool:
        missing = [
            v for v in ("schwab_client_id", "schwab_client_secret", "schwab_refresh_token")
            if not getattr(settings, v, "")
        ]
        if missing:
            logger.warning(
                f"Schwab: health check skipped — missing env vars: "
                f"{[v.upper() for v in missing]}"
            )
            return False
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    _QUOTES_URL,
                    headers=self._auth_headers(token),
                    params={"symbols": "SPY", "fields": "quote"},
                )
            ok = resp.status_code == 200
            if ok:
                logger.info("Schwab: health check passed.")
            else:
                logger.warning(f"Schwab: health check HTTP {resp.status_code}.")
            return ok
        except Exception as exc:
            logger.warning(f"Schwab: health check failed — {exc}")
            return False

    # ── Error helpers ─────────────────────────────────────────────────────────

    def _raise_for_status(self, resp: httpx.Response, context: str):
        if resp.status_code == 401:
            raise RuntimeError(
                "Schwab: 401 Unauthorized — access token may have expired mid-request. "
                "Will retry on next request."
            )
        if resp.status_code == 403:
            raise RuntimeError(
                "Schwab: 403 Forbidden — this app may lack market data entitlement. "
                "Check your app's permissions at developer.schwab.com."
            )
        if resp.status_code == 429:
            raise RuntimeError(
                "Schwab: 429 rate limited — backing off. (~120 req/min allowed)"
            )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Schwab {context}: HTTP {resp.status_code} — {resp.text[:300]}"
            )
