"""
Options business logic layer.
Orchestrates: provider → model hydration → derived fields → unusual scoring.
"""
import asyncio
import logging
from datetime import datetime
from typing import List

from app.models.options import (
    OptionContract,
    OptionChainResponse,
    UnusualOptionsResponse,
    TopContractsResponse,
    ExpirationResponse,
)
from app.providers import provider
from app.services.unusual_engine import score_contracts
import app.cache as cache

logger = logging.getLogger(__name__)

UNUSUAL_TOP_N    = 25
MAX_EXPIRATIONS  = 6    # fetch nearest 6 expirations (covers 0DTE → ~6 weeks)
CONCURRENCY      = 10   # parallel expiry fetches


def _hydrate(raw: dict, underlying_price: float) -> OptionContract:
    mid = raw.get("mid", 0.0)
    oi  = raw.get("open_interest", 0) or 0
    vol = raw.get("volume", 0) or 0
    return OptionContract(
        **raw,
        oi_notional      = round(oi  * mid * 100, 2),
        vol_notional     = round(vol * mid * 100, 2),
        vol_oi_ratio     = round(vol / max(oi, 1), 4),
        underlying_price = underlying_price,
        moneyness        = round(raw.get("strike", 0) / underlying_price, 4) if underlying_price else None,
    )


async def _fetch_chain(ticker: str) -> tuple[float, List[str], List[OptionContract]]:
    """
    Fetch price + nearest MAX_EXPIRATIONS expirations in ONE bulk API call.
    Returns (underlying_price, all_expirations, contracts).
    """
    price, all_expirations = await asyncio.gather(
        provider.get_underlying_price(ticker),
        provider.get_expirations(ticker),
    )

    if not all_expirations:
        return price, [], []

    expirations_to_fetch = all_expirations[:MAX_EXPIRATIONS]

    try:
        raw_list = await provider.get_option_chain_bulk(ticker, expirations_to_fetch)
    except AttributeError:
        # Fallback for providers that don't implement bulk fetch
        semaphore = asyncio.Semaphore(CONCURRENCY)
        async def fetch_one(exp):
            async with semaphore:
                try:
                    return await provider.get_option_chain(ticker, exp)
                except Exception as exc:
                    logger.warning(f"Failed {ticker} {exp}: {exc}")
                    return []
        results = await asyncio.gather(*[fetch_one(e) for e in expirations_to_fetch])
        raw_list = [r for batch in results for r in batch]

    contracts = [_hydrate(r, price) for r in raw_list if r.get("strike")]
    return price, all_expirations, contracts


async def get_full_chain(ticker: str) -> OptionChainResponse:
    ticker = ticker.upper()
    key    = cache.cache_key("chain", ticker)
    cached = await cache.get(key)
    if cached:
        return cached

    price, expirations, contracts = await _fetch_chain(ticker)
    contracts = score_contracts(contracts, price)

    calls = [c for c in contracts if c.option_type == "call"]
    puts  = [c for c in contracts if c.option_type == "put"]

    result = OptionChainResponse(
        ticker            = ticker,
        underlying_price  = price,
        timestamp         = datetime.utcnow(),
        expirations       = expirations,
        contracts         = contracts,
        total_call_oi     = sum(c.open_interest for c in calls),
        total_put_oi      = sum(c.open_interest for c in puts),
        total_call_volume = sum(c.volume for c in calls),
        total_put_volume  = sum(c.volume for c in puts),
        call_put_ratio    = round(
            sum(c.volume for c in calls) / max(sum(c.volume for c in puts), 1), 3
        ),
    )
    await cache.set(key, result)
    return result


async def get_unusual_options(ticker: str) -> UnusualOptionsResponse:
    ticker = ticker.upper()
    key    = cache.cache_key("unusual", ticker)
    cached = await cache.get(key)
    if cached:
        return cached

    chain      = await get_full_chain(ticker)
    all_scored = chain.contracts

    top_calls  = [c for c in all_scored if c.option_type == "call"][:UNUSUAL_TOP_N]
    top_puts   = [c for c in all_scored if c.option_type == "put" ][:UNUSUAL_TOP_N]
    combined   = all_scored[:UNUSUAL_TOP_N * 2]

    result = UnusualOptionsResponse(
        ticker             = ticker,
        underlying_price   = chain.underlying_price,
        timestamp          = chain.timestamp,
        top_calls          = top_calls,
        top_puts           = top_puts,
        combined           = combined,
        total_unusual_flow = round(sum(c.vol_notional for c in combined), 2),
    )
    await cache.set(key, result)
    return result


async def get_top_contracts(ticker: str, metric: str, limit: int = 25) -> TopContractsResponse:
    ticker = ticker.upper()
    key    = cache.cache_key("top", ticker, metric, limit)
    cached = await cache.get(key)
    if cached:
        return cached

    chain  = await get_full_chain(ticker)
    sort_map = {
        "oi_notional":   lambda c: c.oi_notional,
        "vol_notional":  lambda c: c.vol_notional,
        "open_interest": lambda c: c.open_interest,
        "volume":        lambda c: c.volume,
        "unusual_score": lambda c: c.unusual_score,
    }
    sorted_contracts = sorted(
        chain.contracts, key=sort_map.get(metric, sort_map["unusual_score"]), reverse=True
    )[:limit]

    result = TopContractsResponse(
        ticker           = ticker,
        underlying_price = chain.underlying_price,
        timestamp        = chain.timestamp,
        metric           = metric,
        contracts        = sorted_contracts,
    )
    await cache.set(key, result)
    return result


async def get_expirations(ticker: str) -> ExpirationResponse:
    ticker = ticker.upper()
    key    = cache.cache_key("expirations", ticker)
    cached = await cache.get(key)
    if cached:
        return cached

    expirations = await provider.get_expirations(ticker)
    result = ExpirationResponse(
        ticker      = ticker,
        expirations = expirations,
        timestamp   = datetime.utcnow(),
    )
    await cache.set(key, result)
    return result
