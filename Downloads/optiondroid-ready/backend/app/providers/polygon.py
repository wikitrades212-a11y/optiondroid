"""
Polygon.io options data provider — STUB.
Implement when Polygon API key is available.
Swap in via DATA_PROVIDER=polygon in .env.
"""
from typing import List
from .base import OptionsDataProvider


class PolygonProvider(OptionsDataProvider):
    """
    Stub implementation for Polygon.io.
    See: https://polygon.io/docs/options
    """

    async def get_underlying_price(self, ticker: str) -> float:
        raise NotImplementedError("PolygonProvider not yet implemented")

    async def get_expirations(self, ticker: str) -> List[str]:
        raise NotImplementedError("PolygonProvider not yet implemented")

    async def get_option_chain(self, ticker: str, expiration: str) -> List[dict]:
        raise NotImplementedError("PolygonProvider not yet implemented")

    async def health_check(self) -> bool:
        return False
