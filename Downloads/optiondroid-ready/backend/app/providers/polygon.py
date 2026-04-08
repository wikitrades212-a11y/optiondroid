"""
Polygon.io — primary options data provider.

Auth: API key via POLYGON_API_KEY env var.
Data tier: Free tier = 15-minute delayed; paid tiers = real-time.
Docs: https://polygon.io/docs/options

Endpoints used:
  GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}  → underlying price
  GET /v3/reference/options/{underlying}                       → expirations
  GET /v3/snapshot/options/{underlying}                        → option chain + greeks
"""
import logging
from datetime import date
from typing import List, Optional

import httpx

from .base import OptionsDataProvider
from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.polygon.io"

# Polygon free tier delivers 15-minute delayed data.
# Set POLYGON_REALTIME=true in env if you have a paid subscription.
_IS_REALTIME = False   # updated at runtime from settings


class PolygonProvider(OptionsDataProvider):

    def __init__(self):
        if not settings.polygon_api_key:
            raise RuntimeError(
                "POLYGON_API_KEY is not set. "
                "Add it to Railway Variables (Settings → Variables)."
            )
        self._key = settings.polygon_api_key
        logger.info("Using Polygon provider.")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _params(self, extra: Optional[dict] = None) -> dict:
        p = {"apiKey": self._key}
        if extra:
            p.update(extra)
        return p

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=_BASE, timeout=20.0)

    def _raise_for_status(self, resp: httpx.Response, context: str):
        if resp.status_code == 403:
            raise RuntimeError(
                "Polygon: 403 Forbidden — API key is invalid or lacks required permissions."
            )
        if resp.status_code == 429:
            raise RuntimeError(
                "Polygon: 429 rate limited — reduce request frequency or upgrade plan."
            )
        if resp.status_code == 404:
            raise ValueError(f"Polygon: {context} not found (404).")
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Polygon {context} failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

    async def _paginate(self, path: str, params: dict, *, max_pages: int = 20) -> List[dict]:
        """Collect all results across paginated responses using Polygon's next_url pattern."""
        results: List[dict] = []
        url = f"{_BASE}{path}"
        async with self._client() as client:
            for _ in range(max_pages):
                resp = await client.get(url, params=params)
                self._raise_for_status(resp, path)
                body = resp.json()
                batch = body.get("results") or []
                results.extend(batch)
                next_url = body.get("next_url")
                if not next_url:
                    break
                # next_url already includes cursor; re-attach apiKey only
                url = next_url
                params = {"apiKey": self._key}
        logger.debug(f"Polygon paginated {path} → {len(results)} total records.")
        return results

    # ── Provider interface ────────────────────────────────────────────────────

    async def get_underlying_price(self, ticker: str) -> float:
        path = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}"
        async with self._client() as client:
            resp = await client.get(path, params=self._params())
        self._raise_for_status(resp, f"stock snapshot/{ticker}")
        data = resp.json()

        ticker_data = data.get("ticker") or {}
        day   = ticker_data.get("day") or {}
        prev  = ticker_data.get("prevDay") or {}
        last  = ticker_data.get("lastTrade") or {}
        quote = ticker_data.get("lastQuote") or {}

        # Prefer: last trade → day close → prev close → mid of bid/ask
        price = (
            last.get("p")
            or day.get("c")
            or prev.get("c")
            or (
                ((quote.get("P") or 0) + (quote.get("p") or 0)) / 2
                if (quote.get("P") or 0) + (quote.get("p") or 0) > 0
                else None
            )
        )
        if not price:
            raise ValueError(f"No price data returned for {ticker} from Polygon.")
        logger.debug(f"Polygon: {ticker} price = {price}")
        return float(price)

    async def get_expirations(self, ticker: str) -> List[str]:
        """
        Collect unique future expiration dates from reference options data.
        Uses /v3/reference/options/{underlying} — no market data, cheap call.
        """
        today = date.today().isoformat()
        records = await self._paginate(
            f"/v3/reference/options/{ticker.upper()}",
            params=self._params({
                "expiration_date.gte": today,
                "limit": 250,
                "sort": "expiration_date",
                "order": "asc",
            }),
        )
        seen = set()
        expirations: List[str] = []
        for r in records:
            exp = r.get("expiration_date")
            if exp and exp not in seen:
                seen.add(exp)
                expirations.append(exp)
        logger.info(f"Polygon: {ticker} expirations → {len(expirations)} dates found.")
        return sorted(expirations)

    async def get_option_chain(self, ticker: str, expiration: str) -> List[dict]:
        """Fetch all contracts for a single expiration from the snapshot endpoint."""
        records = await self._paginate(
            f"/v3/snapshot/options/{ticker.upper()}",
            params=self._params({
                "expiration_date": expiration,
                "limit": 250,
            }),
        )
        contracts = [self._normalize(r, ticker) for r in records]
        contracts = [c for c in contracts if c is not None]
        logger.info(
            f"Polygon: normalized {len(contracts)} contracts for {ticker} {expiration}."
        )
        return contracts

    async def get_option_chain_bulk(
        self,
        ticker: str,
        expirations: List[str],
    ) -> List[dict]:
        """
        Fetch contracts for multiple expirations in one paginated call.
        Polygon snapshot accepts expiration_date.gte / expiration_date.lte so we can
        pull a date range in a single set of pages.
        """
        if not expirations:
            return []
        from_date = min(expirations)
        to_date   = max(expirations)
        exp_set   = set(expirations)

        records = await self._paginate(
            f"/v3/snapshot/options/{ticker.upper()}",
            params=self._params({
                "expiration_date.gte": from_date,
                "expiration_date.lte": to_date,
                "limit": 250,
            }),
        )
        contracts = []
        for r in records:
            details = r.get("details") or {}
            exp = details.get("expiration_date", "")
            if exp not in exp_set:
                continue
            c = self._normalize(r, ticker)
            if c:
                contracts.append(c)

        logger.info(
            f"Polygon: bulk fetch {ticker} {from_date}→{to_date} "
            f"→ {len(contracts)} contracts normalized."
        )
        return contracts

    def _normalize(self, r: dict, ticker: str) -> Optional[dict]:
        details  = r.get("details") or {}
        greeks   = r.get("greeks") or {}
        quote    = r.get("last_quote") or {}
        trade    = r.get("last_trade") or {}
        day      = r.get("day") or {}

        strike = details.get("strike_price")
        if not strike:
            return None

        opt_type = (details.get("contract_type") or "").lower()
        if opt_type not in ("call", "put"):
            return None

        expiration = details.get("expiration_date", "")

        def _f(val, default: float = 0.0) -> float:
            try:
                return float(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        def _i(val, default: int = 0) -> int:
            try:
                return int(float(val)) if val is not None else default
            except (TypeError, ValueError):
                return default

        def _greek(key) -> Optional[float]:
            val = greeks.get(key)
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        bid  = _f(quote.get("bid"))
        ask  = _f(quote.get("ask"))
        last = _f(trade.get("price") or day.get("close"))
        mid  = round((bid + ask) / 2, 4) if (bid + ask) > 0 else last

        # Polygon returns IV as a decimal fraction (e.g. 0.35 = 35% IV)
        iv = _f(r.get("implied_volatility"))

        # Volume: prefer day.volume, fall back to 0
        volume       = _i(day.get("volume"))
        open_interest = _i(r.get("open_interest"))

        return {
            "ticker":             ticker.upper(),
            "strike":             float(strike),
            "expiration":         expiration,
            "option_type":        opt_type,
            "bid":                bid,
            "ask":                ask,
            "mid":                mid,
            "last":               last,
            "mark":               mid,
            "volume":             volume,
            "open_interest":      open_interest,
            "implied_volatility": iv,
            "delta":              _greek("delta"),
            "gamma":              _greek("gamma"),
            "theta":              _greek("theta"),
            "vega":               _greek("vega"),
            "rho":                _greek("rho"),
        }

    async def health_check(self) -> bool:
        """
        Two-stage check:
          1. Validate API key using a free-tier endpoint (stock aggregates).
          2. Confirm options data access using the options snapshot endpoint.

        Returns True only when both pass (options data is accessible).
        Sets self.key_valid and self.options_authorized for status reporting.
        """
        if not settings.polygon_api_key:
            logger.warning("Polygon: health check skipped — POLYGON_API_KEY not set.")
            self.key_valid = False
            self.options_authorized = False
            return False

        # Stage 1: key validation (works on free tier)
        try:
            async with self._client() as client:
                resp = await client.get(
                    "/v2/aggs/ticker/SPY/prev",
                    params=self._params({"adjusted": "true"}),
                )
            self.key_valid = resp.status_code == 200
        except Exception as exc:
            logger.warning(f"Polygon: key validation failed — {exc}")
            self.key_valid = False
            self.options_authorized = False
            return False

        if not self.key_valid:
            logger.warning("Polygon: API key appears invalid (stock aggs returned non-200).")
            self.options_authorized = False
            return False

        # Stage 2: options access check
        try:
            async with self._client() as client:
                resp = await client.get(
                    "/v3/snapshot/options/SPY",
                    params=self._params({"limit": "1"}),
                )
            self.options_authorized = resp.status_code == 200
            if self.options_authorized:
                logger.info("Polygon: health check passed — options access confirmed.")
            else:
                logger.warning(
                    f"Polygon: API key valid but options access denied "
                    f"(HTTP {resp.status_code}). "
                    f"Upgrade to a Polygon plan that includes options data."
                )
        except Exception as exc:
            logger.warning(f"Polygon: options access check failed — {exc}")
            self.options_authorized = False

        return self.options_authorized

    # Readable flags set during health_check; default False until first check runs
    key_valid: bool = False
    options_authorized: bool = False
