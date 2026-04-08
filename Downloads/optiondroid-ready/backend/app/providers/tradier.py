"""
Tradier Brokerage API — options data provider.

Auth: Bearer token (TRADIER_TOKEN env var).
Sandbox: set TRADIER_SANDBOX=true for paper-trading/dev endpoint.

API docs: https://documentation.tradier.com/brokerage-api/markets/get-options-chains
"""
import logging
from typing import List

import httpx

from .base import OptionsDataProvider
from app.config import settings

logger = logging.getLogger(__name__)

_PROD_BASE    = "https://api.tradier.com/v1"
_SANDBOX_BASE = "https://sandbox.tradier.com/v1"


class TradierProvider(OptionsDataProvider):

    def __init__(self):
        base = _SANDBOX_BASE if settings.tradier_sandbox else _PROD_BASE
        self._base = base
        self._headers = {
            "Authorization": f"Bearer {settings.tradier_token}",
            "Accept": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers,
            timeout=20.0,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _check_token(self):
        if not settings.tradier_token:
            raise RuntimeError(
                "TRADIER_TOKEN is not set. "
                "Add it to Railway Variables (Settings → Variables)."
            )

    def _raise_for_status(self, resp: httpx.Response, context: str):
        if resp.status_code == 401:
            raise RuntimeError(
                "Tradier: 401 Unauthorized — check TRADIER_TOKEN is correct "
                "and the account has market data access."
            )
        if resp.status_code == 403:
            raise RuntimeError(
                "Tradier: 403 Forbidden — this token may lack options data permissions."
            )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Tradier {context} failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

    # ── Provider interface ────────────────────────────────────────────────────

    async def get_underlying_price(self, ticker: str) -> float:
        self._check_token()
        async with self._client() as client:
            resp = await client.get("/markets/quotes", params={"symbols": ticker.upper()})
        self._raise_for_status(resp, f"quote/{ticker}")
        data = resp.json()
        quote = data.get("quotes", {}).get("quote")
        if quote is None:
            raise ValueError(f"No quote data returned for {ticker}")
        # last or ask or bid
        price = quote.get("last") or quote.get("ask") or quote.get("bid")
        if price is None:
            raise ValueError(f"No price fields in Tradier quote for {ticker}")
        return float(price)

    async def get_expirations(self, ticker: str) -> List[str]:
        self._check_token()
        async with self._client() as client:
            resp = await client.get(
                "/markets/options/expirations",
                params={"symbol": ticker.upper(), "includeAllRoots": "true"},
            )
        self._raise_for_status(resp, f"expirations/{ticker}")
        data = resp.json()
        expirations = data.get("expirations", {}).get("date") or []
        if isinstance(expirations, str):
            expirations = [expirations]
        return sorted(expirations)

    async def get_option_chain(self, ticker: str, expiration: str) -> List[dict]:
        self._check_token()
        async with self._client() as client:
            resp = await client.get(
                "/markets/options/chains",
                params={
                    "symbol": ticker.upper(),
                    "expiration": expiration,
                    "greeks": "true",
                },
            )
        self._raise_for_status(resp, f"chain/{ticker}/{expiration}")
        data = resp.json()
        options = data.get("options", {}).get("option") or []
        if isinstance(options, dict):
            options = [options]
        return [self._normalize(o) for o in options]

    def _normalize(self, o: dict) -> dict:
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

        greeks = o.get("greeks") or {}

        bid  = _f("bid")
        ask  = _f("ask")
        last = _f("last")
        mid  = round((bid + ask) / 2, 4) if (bid + ask) > 0 else last

        return {
            "ticker":             o.get("root_symbol", ""),
            "strike":             _f("strike"),
            "expiration":         o.get("expiration_date", ""),
            "option_type":        (o.get("option_type") or "").lower(),
            "bid":                bid,
            "ask":                ask,
            "mid":                mid,
            "last":               last,
            "mark":               mid,
            "volume":             _i("volume"),
            "open_interest":      _i("open_interest"),
            "implied_volatility": float(greeks["mid_iv"]) if greeks.get("mid_iv") is not None else _f("mid_iv"),
            "delta":              float(greeks["delta"]) if greeks.get("delta") is not None else None,
            "gamma":              float(greeks["gamma"]) if greeks.get("gamma") is not None else None,
            "theta":              float(greeks["theta"]) if greeks.get("theta") is not None else None,
            "vega":               float(greeks["vega"])  if greeks.get("vega")  is not None else None,
            "rho":                float(greeks["rho"])   if greeks.get("rho")   is not None else None,
        }

    async def health_check(self) -> bool:
        if not settings.tradier_token:
            logger.warning("Tradier: TRADIER_TOKEN not set — health check skipped.")
            return False
        try:
            async with self._client() as client:
                resp = await client.get("/user/profile")
            return resp.status_code == 200
        except Exception as exc:
            logger.warning(f"Tradier health check failed: {exc}")
            return False
