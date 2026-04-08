from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    rh_username: str = ""
    rh_password: str = ""
    rh_mfa_secret: str = ""
    # Base64-encoded robinhood.pickle for cloud deployments (no persistent disk)
    rh_pickle_b64: str = ""

    cache_ttl: int = 60
    data_provider: str = "robinhood"
    cors_origins: str = "http://localhost:3000"
    rate_limit: int = 30

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = False

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
