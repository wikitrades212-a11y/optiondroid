import logging

from .base import OptionsDataProvider
from .robinhood import RobinhoodProvider
from .polygon import PolygonProvider
from .tradier import TradierProvider
from .schwab import SchwabProvider
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER_MAP = {
    "robinhood": RobinhoodProvider,
    "polygon":   PolygonProvider,
    "tradier":   TradierProvider,
    "schwab":    SchwabProvider,
}


def get_provider() -> OptionsDataProvider:
    """
    Factory: instantiate and return the provider selected by DATA_PROVIDER env var.

    Fallback chain (when primary is mis-configured):
      schwab → polygon (if POLYGON_API_KEY set)
      tradier → polygon (if POLYGON_API_KEY set)
      any → no automatic fallback; raises ValueError so the error is explicit.

    To enable fallback, set both primary and fallback credentials in Railway.
    """
    name = settings.data_provider.lower()
    cls  = _PROVIDER_MAP.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown DATA_PROVIDER='{settings.data_provider}'. "
            f"Valid options: {sorted(_PROVIDER_MAP.keys())}"
        )
    logger.info(f"Provider: using '{name}'.")
    return cls()


# Module-level singleton — shared across all requests
provider: OptionsDataProvider = get_provider()
