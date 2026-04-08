from pydantic import BaseModel
from typing import Optional, List, Literal


class CalculatorRequest(BaseModel):
    ticker: str
    current_price: float
    target_price: float
    option_type: Literal["call", "put", "auto"]  # auto = infer from direction
    expiration: str                               # YYYY-MM-DD
    max_premium: Optional[float] = None
    preferred_strike: Optional[float] = None
    account_size: Optional[float] = None
    risk_per_trade: Optional[float] = None        # dollars at risk


class StrikeAnalysis(BaseModel):
    # Identity
    strike: float
    expiration: str
    option_type: Literal["call", "put"]

    # Pricing
    bid: float
    ask: float
    mid: float
    mark: float

    # Activity
    volume: int
    open_interest: int
    implied_volatility: float

    # Greeks
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]

    # Derived
    moneyness_pct: float          # (strike - current) / current * 100
    intrinsic_at_target: float    # max(target - strike, 0) for calls
    estimated_value_at_target: float
    estimated_roi_pct: float
    breakeven: float              # strike ± premium
    breakeven_move_pct: float     # % move needed from current to breakeven

    # Quality scores (0–100)
    liquidity_score: float
    spread_pct: float             # (ask - bid) / mid * 100

    # Classification
    tier: Literal["aggressive", "balanced", "safer", "avoid"]
    avoid_reasons: List[str]
    badges: List[str]

    # Max entry
    ideal_max_entry: float        # don't pay more than this
    contracts_for_risk: Optional[int]   # how many contracts given risk $ input


class CalculatorResponse(BaseModel):
    ticker: str
    current_price: float
    target_price: float
    move_pct: float               # (target - current) / current * 100
    option_type: Literal["call", "put"]
    expiration: str
    dte: int                      # days to expiration from today
    expiry_fit_score: float       # [0, 1] — how well DTE matches move magnitude

    recommended_aggressive: Optional[StrikeAnalysis]
    recommended_balanced: Optional[StrikeAnalysis]
    recommended_safer: Optional[StrikeAnalysis]
    avoid_list: List[StrikeAnalysis]
    all_strikes: List[StrikeAnalysis]
