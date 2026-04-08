"""
Abstract base class for options data providers.
All provider implementations MUST inherit from this class.
Swap providers by changing DATA_PROVIDER in .env.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple


class OptionsDataProvider(ABC):
    """
    Contract for any options data source.
    Implementations: RobinhoodProvider, PolygonProvider, TradierProvider
    """

    @abstractmethod
    async def get_underlying_price(self, ticker: str) -> float:
        """Return the current spot price of the underlying."""
        ...

    @abstractmethod
    async def get_expirations(self, ticker: str) -> List[str]:
        """Return list of available expiration dates (YYYY-MM-DD)."""
        ...

    @abstractmethod
    async def get_option_chain(
        self,
        ticker: str,
        expiration: str,
    ) -> List[dict]:
        """
        Return raw option contract dicts for a single expiration.
        Each dict must contain at minimum:
          strike_price, expiration_date, type,
          bid_price, ask_price, last_trade_price,
          volume, open_interest, implied_volatility
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if provider is reachable and authenticated."""
        ...
