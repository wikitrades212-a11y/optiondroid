"""
Tradier options data provider — STUB.
Implement when Tradier API token is available.
Swap in via DATA_PROVIDER=tradier in .env.
"""
from typing import List
from .base import OptionsDataProvider


class TradierProvider(OptionsDataProvider):
    """
    Stub implementation for Tradier Brokerage API.
    See: https://documentation.tradier.com/brokerage-api/markets/get-options-chains
    """

    async def get_underlying_price(self, ticker: str) -> float:
        raise NotImplementedError("TradierProvider not yet implemented")

    async def get_expirations(self, ticker: str) -> List[str]:
        raise NotImplementedError("TradierProvider not yet implemented")

    async def get_option_chain(self, ticker: str, expiration: str) -> List[dict]:
        raise NotImplementedError("TradierProvider not yet implemented")

    async def health_check(self) -> bool:
        return False
