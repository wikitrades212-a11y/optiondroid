from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Literal
from datetime import datetime


class OptionContract(BaseModel):
    # Identity
    ticker: str
    strike: float
    expiration: str          # ISO date string: YYYY-MM-DD
    option_type: Literal["call", "put"]

    # Pricing
    bid: float = 0.0
    ask: float = 0.0
    mid: float = 0.0
    last: float = 0.0
    mark: float = 0.0

    # Activity
    volume: int = 0
    open_interest: int = 0
    implied_volatility: float = 0.0

    # Calculated notionals
    oi_notional: float = 0.0       # open_interest * mid * 100
    vol_notional: float = 0.0      # volume * mid * 100
    vol_oi_ratio: float = 0.0      # volume / max(open_interest, 1)

    # Unusual scoring (populated by engine)
    unusual_score: float = 0.0
    unusual_rank: int = 0
    reason_tags: List[str] = Field(default_factory=list)

    # Greeks (if available)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None

    # Meta
    underlying_price: Optional[float] = None
    moneyness: Optional[float] = None     # strike / underlying_price


class OptionChainResponse(BaseModel):
    ticker: str
    underlying_price: float
    timestamp: datetime
    expirations: List[str]
    contracts: List[OptionContract]
    total_call_oi: int
    total_put_oi: int
    total_call_volume: int
    total_put_volume: int
    call_put_ratio: float


class UnusualOptionsResponse(BaseModel):
    ticker: str
    underlying_price: float
    timestamp: datetime
    top_calls: List[OptionContract]
    top_puts: List[OptionContract]
    combined: List[OptionContract]
    total_unusual_flow: float    # aggregate vol_notional of unusual contracts


class TopContractsResponse(BaseModel):
    ticker: str
    underlying_price: float
    timestamp: datetime
    metric: str
    contracts: List[OptionContract]


class ExpirationResponse(BaseModel):
    ticker: str
    expirations: List[str]
    timestamp: datetime
