from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # ── Tradier (primary production provider) ────────────────────────────────
    tradier_token: str = ""
    # Set to "true" to use the Tradier sandbox endpoint (paper trading / dev)
    tradier_sandbox: bool = False

    # ── Robinhood (kept for local/dev use only — not used on Railway) ─────────
    rh_username: str = ""
    rh_password: str = ""
    rh_mfa_secret: str = ""
    rh_pickle_b64: str = ""

    # ── Schwab Trader API ────────────────────────────────────────────────────
    # Obtain from developer.schwab.com — run schwab_auth.py once to get refresh token
    schwab_client_id: str = ""
    schwab_client_secret: str = ""
    schwab_refresh_token: str = ""   # 7-day TTL; re-run schwab_auth.py to renew

    # ── Polygon (alternative provider) ───────────────────────────────────────
    polygon_api_key: str = ""

    # ── General ──────────────────────────────────────────────────────────────
    cache_ttl: int = 60
    data_provider: str = "schwab"    # schwab (primary) | tradier | polygon | robinhood
    cors_origins: str = "http://localhost:3000"
    rate_limit: int = 30

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = False

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
