"""
scripts/refresh_fixtures.py
---------------------------
Maintenance script to refresh local cache fixtures with live data once.
Run periodically or prior to offline hackathon demos to populate data/cache/fixtures/.
"""

from __future__ import annotations

import json
import logging

import requests

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("refresh_fixtures")

FIXTURES_DIR = config.CACHE_DIR / "fixtures"


def refresh_open_meteo_forecast() -> None:
    """Fetch live forecast for Morigaon and save to fixture."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 26.25,
        "longitude": 92.34,
        "hourly": "precipitation",
        "daily": "precipitation_sum",
        "forecast_days": 7,
        "timezone": "Asia/Kolkata",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            target = FIXTURES_DIR / "open_meteo_forecast" / "forecast_sample.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(resp.json(), indent=2), encoding="utf-8")
            logger.info("✓ Refreshed Open-Meteo Forecast fixture")
    except Exception as exc:
        logger.warning("Could not refresh forecast fixture: %s", exc)


def refresh_open_meteo_flood() -> None:
    """Fetch live flood discharge and save to fixture."""
    url = "https://flood-api.open-meteo.com/v1/flood"
    params = {
        "latitude": 26.25,
        "longitude": 92.34,
        "daily": "river_discharge,river_discharge_max",
        "forecast_days": 7,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            target = FIXTURES_DIR / "open_meteo_flood" / "flood_sample.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(resp.json(), indent=2), encoding="utf-8")
            logger.info("✓ Refreshed Open-Meteo Flood fixture")
    except Exception as exc:
        logger.warning("Could not refresh flood fixture: %s", exc)


def refresh_nominatim() -> None:
    """Fetch live Nominatim geocoding results and save to fixture."""
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": config.NOMINATIM_USER_AGENT}
    try:
        resp = requests.get(
            url,
            params={"q": "Morigaon, Assam", "format": "json", "limit": 1, "countrycodes": "in"},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            target = FIXTURES_DIR / "nominatim" / "nominatim_sample.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(resp.json(), indent=2), encoding="utf-8")
            logger.info("✓ Refreshed Nominatim fixture")
    except Exception as exc:
        logger.warning("Could not refresh Nominatim fixture: %s", exc)


def refresh_opentopodata() -> None:
    """Fetch live elevation and save to fixture."""
    url = "https://api.opentopodata.org/v1/srtm90m"
    try:
        resp = requests.get(url, params={"locations": "26.25,92.34|26.26,92.35"}, timeout=10)
        if resp.status_code == 200:
            target = FIXTURES_DIR / "opentopodata" / "elevation_sample.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(resp.json(), indent=2), encoding="utf-8")
            logger.info("✓ Refreshed OpenTopoData fixture")
    except Exception as exc:
        logger.warning("Could not refresh OpenTopoData fixture: %s", exc)


def main() -> None:
    logger.info("Starting fixtures refresh...")
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    refresh_open_meteo_forecast()
    refresh_open_meteo_flood()
    refresh_nominatim()
    refresh_opentopodata()
    logger.info("Fixtures refresh run complete.")


if __name__ == "__main__":
    main()
