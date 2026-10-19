"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FloodSaathi core configuration settings."""

    # Project metadata
    PROJECT_NAME: str = "FloodSaathi"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./floodsaathi.db"
    CACHE_DIR: str = "data/cache"

    # Security & Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production-floodsaathi-super-safe"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # External APIs & Offline flag
    GEOAPIFY_API_KEY: str = ""
    GEOCODE_DAILY_CAP: int = 2500
    OPENWEATHER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OFFLINE_DEMO: bool = True
    NOMINATIM_USER_AGENT: str = "FloodSaathi/2.0 (contact@floodsaathi.local)"
    SACHET_RSS_URL: str = "https://sachet.ndma.gov.in/feed/rss"
    IMD_ENABLED: bool = False
    IMD_API_BASE: str = "https://api.imd.gov.in/api/v1"
    DEFAULT_DISTRICT: str = "Patna"

    # Demo credentials
    COORDINATOR_EMAIL: str = "coordinator@demo"
    COORDINATOR_PASSWORD: str = "admin123"
    VOLUNTEER_EMAIL: str = "volunteer@demo"
    VOLUNTEER_PASSWORD: str = "volunteer123"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
