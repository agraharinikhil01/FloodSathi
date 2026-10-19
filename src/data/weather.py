"""
src/data/weather.py
-------------------
Fetches weather and river discharge forecasts from Open-Meteo APIs.
Implements timeout, 2 retries, 1-hour cache, and fallback to data/cache/fallback.json.
Returns a pandas DataFrame.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

import config

logger = logging.getLogger(__name__)

CACHE_FILE = config.CACHE_DIR / "weather_cache.json"
FALLBACK_FILE = config.CACHE_DIR / "fallback.json"
CACHE_TTL_SECONDS = config.CACHE_TTL_WEATHER_H * 3600


def _load_json(file_path: Path) -> dict[str, Any]:
    """Read and parse a JSON file if it exists, else return empty dict."""
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Error reading %s: %s", file_path, exc)
    return {}


def _save_json(file_path: Path, data: dict[str, Any]) -> None:
    """Save dictionary data to a JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Error writing cache to %s: %s", file_path, exc)


def _http_get_with_retry(
    url: str, params: dict[str, Any], retries: int = config.HTTP_RETRIES
) -> dict[str, Any] | None:
    """Perform HTTP GET with timeout and retries."""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("API returned HTTP %d on attempt %d", resp.status_code, attempt + 1)
        except (requests.RequestException, Exception) as exc:
            logger.warning("Request failed on attempt %d: %s", attempt + 1, exc)
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
    return None


def fetch_forecast_raw(lat: float, lon: float) -> dict[str, Any] | None:
    """Fetch 7-day precipitation and wind speed from Open-Meteo Forecast API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,rain,wind_speed_10m",
        "forecast_days": 7,
        "timezone": "UTC",
    }
    return _http_get_with_retry(f"{config.OPEN_METEO_BASE_URL}/forecast", params)


def fetch_discharge_raw(lat: float, lon: float) -> dict[str, Any] | None:
    """Fetch river discharge forecast from Open-Meteo Flood API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "river_discharge",
        "forecast_days": 7,
    }
    return _http_get_with_retry(f"{config.OPEN_METEO_FLOOD_URL}/flood", params)


def _parse_weather_metrics(raw: dict[str, Any]) -> dict[str, float]:
    """Calculate cumulative precipitations and wind speed from Open-Meteo hourly data."""
    hourly = raw.get("hourly", {})
    precips = hourly.get("precipitation", [])
    winds = hourly.get("wind_speed_10m", [])

    precip_1h = float(precips[0]) if precips else 0.0
    precip_24h = float(sum(precips[:24])) if len(precips) >= 24 else float(sum(precips))
    precip_48h = float(sum(precips[:48])) if len(precips) >= 48 else float(sum(precips))
    precip_7d = float(sum(precips)) if precips else 0.0
    wind_max = float(max(winds[:48])) if winds else 15.0

    return {
        "precip_1h_mm": round(precip_1h, 2),
        "precip_24h_mm": round(precip_24h, 2),
        "precip_48h_mm": round(precip_48h, 2),
        "precip_7d_mm": round(precip_7d, 2),
        "wind_speed_kmh": round(wind_max, 1),
    }


def _parse_discharge_metrics(raw: dict[str, Any]) -> float:
    """Extract maximum river discharge over forecast window."""
    daily = raw.get("daily", {})
    discharge_series = daily.get("river_discharge", [])
    valid_vals = [float(v) for v in discharge_series if v is not None]
    return round(max(valid_vals), 2) if valid_vals else 1200.0


def _get_fallback_data(district_name: str | None = None) -> dict[str, Any]:
    """Return fallback metrics for weather and river discharge."""
    fallback_json = _load_json(FALLBACK_FILE)
    w_map = fallback_json.get("weather", {})
    d_map = fallback_json.get("discharge", {})

    target = district_name or config.DEFAULT_DISTRICT
    w_info = w_map.get(
        target,
        {
            "precip_1h_mm": 15.0,
            "precip_24h_mm": 80.0,
            "precip_48h_mm": 140.0,
            "wind_speed_kmh": 30.0,
        },
    )
    d_info = d_map.get(target, {"river_discharge_m3s": 3500.0})

    return {
        "precip_1h_mm": float(w_info.get("precip_1h_mm", 15.0)),
        "precip_24h_mm": float(w_info.get("precip_24h_mm", 80.0)),
        "precip_48h_mm": float(w_info.get("precip_48h_mm", 140.0)),
        "precip_7d_mm": float(w_info.get("precip_48h_mm", 140.0)) * 2.2,
        "wind_speed_kmh": float(w_info.get("wind_speed_kmh", 30.0)),
        "river_discharge_m3s": float(d_info.get("river_discharge_m3s", 3500.0)),
    }


def fetch_weather_and_discharge(
    points: list[dict[str, Any]], district_name: str | None = None
) -> pd.DataFrame:
    """Fetch 7-day weather and discharge for a list of points and return a DataFrame."""
    cache = _load_json(CACHE_FILE)
    now_ts = time.time()
    rows: list[dict[str, Any]] = []

    for pt in points:
        lat = round(float(pt.get("lat", 0.0)), 4)
        lon = round(float(pt.get("lon", 0.0)), 4)
        pt_id = pt.get("id")
        cache_key = f"{lat}_{lon}"
        cached_entry = cache.get(cache_key)

        if cached_entry and (now_ts - cached_entry.get("timestamp", 0) < CACHE_TTL_SECONDS):
            item = dict(cached_entry["data"])
            item["source"] = "cache"
        else:
            w_raw = fetch_forecast_raw(lat, lon)
            d_raw = fetch_discharge_raw(lat, lon)

            if w_raw is not None and d_raw is not None:
                item = _parse_weather_metrics(w_raw)
                item["river_discharge_m3s"] = _parse_discharge_metrics(d_raw)
                item["source"] = "live"
                cache[cache_key] = {"timestamp": now_ts, "data": item}
            elif cached_entry:
                item = dict(cached_entry["data"])
                item["source"] = "stale_cache"
            else:
                item = _get_fallback_data(district_name)
                item["source"] = "fallback"

        item["lat"] = lat
        item["lon"] = lon
        if pt_id is not None:
            item["grid_point_id"] = pt_id
        rows.append(item)

    _save_json(CACHE_FILE, cache)
    return pd.DataFrame(rows)
