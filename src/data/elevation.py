"""
src/data/elevation.py
---------------------
Fetches ground elevation (meters ASL) via OpenTopoData SRTM API.
Includes disk caching (7-day TTL) and fallback values from data/cache/fallback.json.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)

CACHE_FILE = config.CACHE_DIR / "elevation_cache.json"
FALLBACK_FILE = config.CACHE_DIR / "fallback.json"
CACHE_TTL_SECONDS = 7 * 86400  # 7 days


def _load_json(path: Path) -> dict[str, Any]:
    """Read JSON file if present, else empty dict."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Error reading %s: %s", path, exc)
    return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    """Save dictionary to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Error writing cache %s: %s", path, exc)


def _get_fallback_elevation(district_name: str | None = None) -> float:
    """Return default elevation from fallback JSON or a default 35.0m."""
    fallback_data = _load_json(FALLBACK_FILE)
    elev_map = fallback_data.get("elevation_m", {})
    if district_name and district_name in elev_map:
        return float(elev_map[district_name])
    return 35.0


def fetch_elevation_batch(
    coords: list[tuple[float, float]], district_name: str | None = None
) -> list[float]:
    """Fetch elevation for multiple (lat, lon) coordinates in one API call with cache."""
    cache = _load_json(CACHE_FILE)
    now_ts = time.time()
    results: list[float] = [0.0] * len(coords)
    missing_indices: list[int] = []
    missing_query_coords: list[tuple[float, float]] = []

    for idx, (lat, lon) in enumerate(coords):
        key = f"{round(lat, 4)}_{round(lon, 4)}"
        entry = cache.get(key)
        if entry and (now_ts - entry.get("timestamp", 0) < CACHE_TTL_SECONDS):
            results[idx] = float(entry["elevation"])
        else:
            missing_indices.append(idx)
            missing_query_coords.append((lat, lon))

    if missing_query_coords:
        locs_str = "|".join(f"{lat},{lon}" for lat, lon in missing_query_coords)
        url = f"{config.OPENTOPODATA_URL}/srtm30m"
        try:
            resp = requests.get(url, params={"locations": locs_str}, timeout=config.HTTP_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get("results", [])
                for i, res in enumerate(data):
                    idx = missing_indices[i]
                    elev = float(res.get("elevation") or _get_fallback_elevation(district_name))
                    results[idx] = round(elev, 1)
                    key = f"{round(coords[idx][0], 4)}_{round(coords[idx][1], 4)}"
                    cache[key] = {"timestamp": now_ts, "elevation": results[idx]}
                _save_json(CACHE_FILE, cache)
            else:
                logger.warning("OpenTopoData returned %d; using fallback", resp.status_code)
                _fill_fallbacks(results, missing_indices, district_name)
        except Exception as exc:
            logger.warning("Elevation request failed: %s; using fallback", exc)
            _fill_fallbacks(results, missing_indices, district_name)

    return results


def _fill_fallbacks(results: list[float], indices: list[int], district_name: str | None) -> None:
    """Populate missing indices with default fallback elevation."""
    fallback_elev = _get_fallback_elevation(district_name)
    for idx in indices:
        results[idx] = fallback_elev


def get_elevation(lat: float, lon: float, district_name: str | None = None) -> float:
    """Return elevation for a single (lat, lon) coordinate."""
    res = fetch_elevation_batch([(lat, lon)], district_name=district_name)
    return res[0]
