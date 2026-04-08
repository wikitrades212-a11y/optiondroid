"""
Options API router.

Endpoints:
  GET /api/options               Full option chain
  GET /api/options/unusual       Unusual options (scored + ranked)
  GET /api/options/top           Top N by metric
  GET /api/options/expirations   Available expiration dates
  GET /api/options/export        CSV export
"""
import csv
import io
import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from app.models.options import (
    OptionChainResponse,
    UnusualOptionsResponse,
    TopContractsResponse,
    ExpirationResponse,
)
from app.services import (
    get_full_chain,
    get_unusual_options,
    get_top_contracts,
    get_expirations,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/options", tags=["options"])

VALID_METRICS = {"oi_notional", "vol_notional", "open_interest", "volume", "unusual_score"}


def _ticker_guard(ticker: str) -> str:
    t = ticker.strip().upper()
    if not t.isalpha() or len(t) > 6:
        raise HTTPException(status_code=422, detail=f"Invalid ticker: {ticker!r}")
    return t


@router.get("", response_model=OptionChainResponse, summary="Full option chain")
async def option_chain(
    ticker: str = Query(..., description="Equity ticker symbol, e.g. SPY"),
):
    ticker = _ticker_guard(ticker)
    try:
        return await get_full_chain(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/unusual",
    response_model=UnusualOptionsResponse,
    summary="Unusual options — scored and ranked",
)
async def unusual_options(
    ticker: str = Query(..., description="Equity ticker symbol"),
):
    ticker = _ticker_guard(ticker)
    try:
        return await get_unusual_options(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/top", response_model=TopContractsResponse, summary="Top N contracts by metric")
async def top_contracts(
    ticker: str = Query(..., description="Equity ticker symbol"),
    metric: str = Query("oi_notional", description=f"Sort metric: {VALID_METRICS}"),
    limit: int = Query(25, ge=1, le=100, description="Number of results"),
):
    ticker = _ticker_guard(ticker)
    if metric not in VALID_METRICS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid metric '{metric}'. Valid: {sorted(VALID_METRICS)}",
        )
    try:
        return await get_top_contracts(ticker, metric, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/expirations",
    response_model=ExpirationResponse,
    summary="Available option expirations",
)
async def expirations(
    ticker: str = Query(..., description="Equity ticker symbol"),
):
    ticker = _ticker_guard(ticker)
    try:
        return await get_expirations(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/export", summary="Export option chain as CSV")
async def export_csv(
    ticker: str = Query(..., description="Equity ticker symbol"),
    option_type: Optional[Literal["call", "put"]] = Query(None),
    min_volume: int = Query(0, ge=0),
    min_oi: int = Query(0, ge=0),
):
    ticker = _ticker_guard(ticker)
    try:
        chain = await get_full_chain(ticker)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    contracts = chain.contracts
    if option_type:
        contracts = [c for c in contracts if c.option_type == option_type]
    contracts = [c for c in contracts if c.volume >= min_volume and c.open_interest >= min_oi]

    output = io.StringIO()
    fields = [
        "ticker", "expiration", "option_type", "strike",
        "bid", "ask", "mid", "last", "mark",
        "volume", "open_interest", "implied_volatility",
        "oi_notional", "vol_notional", "vol_oi_ratio",
        "unusual_score", "unusual_rank", "reason_tags",
        "delta", "gamma", "theta", "vega",
        "underlying_price", "moneyness",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for c in contracts:
        row = c.model_dump()
        row["reason_tags"] = "|".join(c.reason_tags)
        writer.writerow(row)

    filename = f"{ticker}_options_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
