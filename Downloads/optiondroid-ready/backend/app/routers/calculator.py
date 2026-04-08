"""
Target Move Calculator API router.

GET /api/calculator — analyze strikes for a given move target
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.calculator import CalculatorResponse
from app.services.calculator_service import analyze_target_move

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calculator", tags=["calculator"])


def _ticker_guard(ticker: str) -> str:
    t = ticker.strip().upper()
    if not t.isalpha() or len(t) > 6:
        raise HTTPException(status_code=422, detail=f"Invalid ticker: {ticker!r}")
    return t


@router.get("", response_model=CalculatorResponse, summary="Target move strike analysis")
async def calculator(
    ticker: str         = Query(..., description="Equity ticker, e.g. SPY"),
    current_price: float = Query(..., description="Current stock price"),
    target_price: float  = Query(..., description="Your target stock price"),
    option_type: str    = Query("auto", description="call | put | auto"),
    expiration: str     = Query(..., description="Expiration date YYYY-MM-DD"),
    max_premium: Optional[float] = Query(None, description="Max premium willing to pay"),
    preferred_strike: Optional[float] = Query(None, description="Preferred strike (optional hint)"),
    account_size: Optional[float] = Query(None, description="Account size in $"),
    risk_per_trade: Optional[float] = Query(None, description="Max risk per trade in $"),
):
    ticker = _ticker_guard(ticker)

    # Resolve "auto" direction from price move
    if option_type == "auto":
        resolved_type = "call" if target_price > current_price else "put"
    elif option_type in ("call", "put"):
        resolved_type = option_type
    else:
        raise HTTPException(status_code=422, detail="option_type must be call, put, or auto")

    if current_price <= 0 or target_price <= 0:
        raise HTTPException(status_code=422, detail="Prices must be positive")

    try:
        return await analyze_target_move(
            ticker=ticker,
            current_price=current_price,
            target_price=target_price,
            option_type=resolved_type,
            expiration=expiration,
            max_premium=max_premium,
            preferred_strike=preferred_strike,
            account_size=account_size,
            risk_per_trade=risk_per_trade,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
