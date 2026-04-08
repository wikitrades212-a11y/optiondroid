import logging
from typing import Literal

from .base import OptionsDataProvider
from .robinhood import RobinhoodProvider
from .polygon import PolygonProvider
from .tradier import TradierProvider
from .schwab import SchwabProvider
from app.config import settings

logger = logging.getLogger(__name__)

# ── Readiness states ──────────────────────────────────────────────────────────

ProviderReadiness = Literal[
    "live",             # health check passed, real-time data
    "delayed",          # health check passed, data is delayed (Polygon free tier)
    "pending_approval", # credentials set but awaiting broker approval
    "misconfigured",    # required env vars missing
    "unavailable",      # health check failed (network or auth error)
]

# Map provider → how to determine if credentials are present
def _has_creds(name: str) -> bool:
    if name == "polygon":
        return bool(settings.polygon_api_key)
    if name == "schwab":
        return bool(
            settings.schwab_client_id
            and settings.schwab_client_secret
            and settings.schwab_refresh_token
        )
    if name == "tradier":
        return bool(settings.tradier_token)
    if name == "robinhood":
        return bool(settings.rh_username and settings.rh_password)
    return False


# Providers that require external approval beyond just setting credentials
_APPROVAL_REQUIRED = {"schwab", "tradier"}

# Providers that deliver delayed data on their standard/free tier
_DELAYED_TIER = {"polygon"}


_PROVIDER_MAP = {
    "robinhood": RobinhoodProvider,
    "polygon":   PolygonProvider,
    "tradier":   TradierProvider,
    "schwab":    SchwabProvider,
}


def get_provider() -> OptionsDataProvider:
    """
    Factory: instantiate and return the provider selected by DATA_PROVIDER env var.
    Raises ValueError for unknown names; individual providers raise RuntimeError
    if their required credentials are missing.
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


async def get_provider_status() -> dict:
    """
    Return a readiness snapshot for the active provider.
    Called at startup and exposed via GET /api/provider/status.
    """
    name = settings.data_provider.lower()

    if not _has_creds(name):
        return _status(name, "misconfigured", f"{name.capitalize()} credentials not set.")

    if name in _APPROVAL_REQUIRED:
        # We have credentials but can't confirm API access without trying —
        # attempt a health check; if it fails assume approval is still pending.
        try:
            ok = await provider.health_check()
        except Exception:
            ok = False
        if not ok:
            return _status(
                name,
                "pending_approval",
                f"{name.capitalize()} credentials configured but API access not confirmed. "
                "Approval may still be pending.",
            )
        return _status(name, "live", f"{name.capitalize()} is live.")

    # For non-approval providers (polygon, robinhood) run health check
    try:
        ok = await provider.health_check()
    except Exception as exc:
        return _status(name, "unavailable", f"{name.capitalize()} health check failed: {exc}")

    # Polygon: distinguish "key valid but no options subscription" from full unavailability
    if name == "polygon" and not ok:
        key_valid = getattr(provider, "key_valid", False)
        if key_valid:
            return _status(
                name,
                "unavailable",
                "Polygon API key is valid but your plan does not include options data. "
                "Upgrade at https://polygon.io/dashboard/subscriptions to a plan with options.",
            )

    if not ok:
        return _status(name, "unavailable", f"{name.capitalize()} is not reachable.")

    readiness: ProviderReadiness = "delayed" if name in _DELAYED_TIER else "live"
    msg = (
        "Polygon data is 15-minute delayed on free tier. Upgrade to a paid plan for real-time."
        if readiness == "delayed"
        else f"{name.capitalize()} is live."
    )
    return _status(name, readiness, msg)


def _status(name: str, readiness: ProviderReadiness, message: str) -> dict:
    is_live = readiness in ("live", "delayed")
    return {
        "provider":               name,
        "readiness":              readiness,
        "is_live":                is_live,
        "live_quotes":            readiness == "live",
        "recommendations_enabled": is_live,
        "message":                message,
    }


# ── Module-level singleton — shared across all requests ───────────────────────

try:
    provider: OptionsDataProvider = get_provider()
except Exception as exc:
    logger.error(f"Provider init failed: {exc}")
    # Create a no-op stub so the app starts but every data call raises cleanly
    from .base import OptionsDataProvider as _Base

    class _NullProvider(_Base):
        _msg = str(exc)
        async def get_underlying_price(self, ticker): raise RuntimeError(self._msg)
        async def get_expirations(self, ticker): raise RuntimeError(self._msg)
        async def get_option_chain(self, ticker, expiration): raise RuntimeError(self._msg)
        async def health_check(self): return False

    provider: OptionsDataProvider = _NullProvider()
