"""
config.py
---------
Central settings loader for FloodSaathi.
All other modules must import from here — never call os.environ directly.
Raises ValueError with a clear message if a required key is missing.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (safe to call multiple times)
load_dotenv()


def _require(key: str) -> str:
    """Return the env value for key; raise ValueError if missing or empty."""
    val = os.environ.get(key, "").strip()
    if not val:
        raise ValueError(
            f"[config] Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in the value."
        )
    return val


def _get(key: str, default: str = "") -> str:
    """Return the env value for key, or default if not set."""
    return os.environ.get(key, default).strip()


def get_anthropic_api_key() -> str:
    """Return the Anthropic API key. Raises if not set."""
    return _require("ANTHROPIC_API_KEY")


def get_anthropic_api_key_safe() -> str | None:
    """Return the Anthropic API key if set and not placeholder, else None."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key or "REPLACE" in key:
        return None
    return key


def get_geoapify_api_key_safe() -> str | None:
    """Return the Geoapify API key if set and not placeholder, else None."""
    key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
    if not key or "REPLACE" in key:
        return None
    return key


def get_openweather_api_key_safe() -> str | None:
    """Return the OpenWeather API key if set and not placeholder, else None."""
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key or "REPLACE" in key:
        return None
    return key


GEOAPIFY_API_KEY: str | None = get_geoapify_api_key_safe()
GEOCODE_DAILY_CAP: int = int(_get("GEOCODE_DAILY_CAP", "2500"))
OPENWEATHER_API_KEY: str | None = get_openweather_api_key_safe()


# ── Database ───────────────────────────────────────────────────────────────
DB_PATH: Path = Path(_get("DB_PATH", "floodsaathi.db"))

# ── Cache ──────────────────────────────────────────────────────────────────
CACHE_DIR: Path = Path(_get("CACHE_DIR", "data/cache"))
CACHE_TTL_WEATHER_H: int = int(_get("CACHE_TTL_WEATHER_H", "1"))
CACHE_TTL_FACILITIES_H: int = int(_get("CACHE_TTL_FACILITIES_H", "24"))
CACHE_TTL_GEOCODE_DAYS: int = int(_get("CACHE_TTL_GEOCODE_DAYS", "7"))

# ── App ────────────────────────────────────────────────────────────────────
DEFAULT_DISTRICT: str = _get("DEFAULT_DISTRICT", "Morigaon")
LOG_LEVEL: str = _get("LOG_LEVEL", "INFO").upper()

# ── External API URLs ──────────────────────────────────────────────────────
OPEN_METEO_BASE_URL: str = _get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")
OPEN_METEO_FLOOD_URL: str = _get("OPEN_METEO_FLOOD_URL", "https://flood-api.open-meteo.com/v1")
OVERPASS_URL: str = _get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
NOMINATIM_URL: str = _get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
OPENTOPODATA_URL: str = _get("OPENTOPODATA_URL", "https://api.opentopodata.org/v1")

# ── Feature flags & External Feeds ─────────────────────────────────────────
ENABLE_SACHET: bool = _get("ENABLE_SACHET", "true").lower() == "true"
ENABLE_MCP: bool = _get("ENABLE_MCP", "false").lower() == "true"
SACHET_RSS_URL: str = _get(
    "SACHET_RSS_URL", "https://sachet.ndma.gov.in/cap_public_website/rss/assam.xml"
)
IMD_ENABLED: bool = _get("IMD_ENABLED", "false").lower() == "true"
IMD_API_BASE: str = _get("IMD_API_BASE", "https://api.imd.gov.in/api/v1")
GDACS_FEED_URL: str = _get("GDACS_FEED_URL", "https://www.gdacs.org/xml/rss_fl.xml")
NOMINATIM_USER_AGENT: str = _get("NOMINATIM_USER_AGENT", "FloodSaathi/1.0 (contact@floodsaathi.in)")

# ── HTTP ───────────────────────────────────────────────────────────────────
HTTP_TIMEOUT: int = 5  # seconds
HTTP_RETRIES: int = 2
NOMINATIM_RATE_LIMIT_S: float = 1.0  # seconds between geocoding requests

# ── Risk thresholds ────────────────────────────────────────────────────────
RISK_WEIGHT_RAIN: float = 0.40
RISK_WEIGHT_DISCHARGE: float = 0.35
RISK_WEIGHT_ELEVATION: float = 0.15
RISK_WEIGHT_POPULATION: float = 0.10
RISK_RAIN_MAX_MM: float = 200.0  # saturation point for 48h rain
RISK_DISCHARGE_MAX_RATIO: float = 4.0  # multiples of baseline discharge
RISK_ELEVATION_MAX_M: float = 50.0  # metres; below this = higher risk

# ── Triage ─────────────────────────────────────────────────────────────────
TRIAGE_MAX_MESSAGE_LEN: int = 1000
TRIAGE_RATE_LIMIT_PER_MIN: int = 5
CLAUDE_MODEL: str = "claude-3-5-haiku-20241022"
CLAUDE_MAX_TOKENS: int = 512
CLAUDE_TIMEOUT: int = 15

# ── Ensure cache dir exists ────────────────────────────────────────────────
CACHE_DIR.mkdir(parents=True, exist_ok=True)
