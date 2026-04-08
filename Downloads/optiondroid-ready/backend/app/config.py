from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # ── Polygon (primary production provider) ────────────────────────────────
    # Free tier: 15-minute delayed data.  Paid tiers: real-time.
    polygon_api_key: str = ""

    # ── Schwab Trader API (pending approval — not active) ────────────────────
    # Intended future primary once developer.schwab.com access is approved.
    # Run schwab_auth.py once locally to get SCHWAB_REFRESH_TOKEN (7-day TTL).
    schwab_client_id: str = ""
    schwab_client_secret: str = ""
    schwab_refresh_token: str = ""

    # ── Tradier (not active — approval pending) ───────────────────────────────
    tradier_token: str = ""
    tradier_sandbox: bool = False

    # ── Robinhood (not used in production) ────────────────────────────────────
    rh_username: str = ""
    rh_password: str = ""
    rh_mfa_secret: str = ""
    rh_pickle_b64: str = ""

    # ── General ──────────────────────────────────────────────────────────────
    cache_ttl: int = 60
    data_provider: str = "polygon"   # polygon (primary) | schwab | tradier | robinhood
    cors_origins: str = "http://localhost:3000"
    rate_limit: int = 30

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = False

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
