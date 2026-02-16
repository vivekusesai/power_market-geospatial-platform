"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/power_market"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/power_market"

    # Application
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Map Defaults
    default_map_center_lat: float = 39.8283
    default_map_center_lon: float = -98.5795
    default_map_zoom: int = 5

    # Performance
    max_assets_per_request: int = 5000
    max_price_records_per_request: int = 10000


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
