from .base import OptionsDataProvider
from .robinhood import RobinhoodProvider
from .polygon import PolygonProvider
from .tradier import TradierProvider
from app.config import settings


def get_provider() -> OptionsDataProvider:
    """Factory: return the configured provider singleton."""
    mapping = {
        "robinhood": RobinhoodProvider,
        "polygon": PolygonProvider,
        "tradier": TradierProvider,
    }
    cls = mapping.get(settings.data_provider.lower())
    if cls is None:
        raise ValueError(
            f"Unknown provider '{settings.data_provider}'. "
            f"Valid options: {list(mapping.keys())}"
        )
    return cls()


# Module-level singleton — shared across all requests
provider: OptionsDataProvider = get_provider()
