"""
src/integrations/imd.py
-----------------------
Optional India Meteorological Department (IMD) API adapter.
Operates behind the IMD_ENABLED feature flag.
Fetches district warnings (/districtwarning) and nowcasts (/districtnowcast),
decodes Day 1-3 warning codes using data/imd_warning_codes.json,
and provides fuzzy district matching.
"""

from __future__ import annotations

import difflib
import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

import config
from src.db.queries import list_districts

logger = logging.getLogger(__name__)

TIMEOUT_S = 10.0
RETRIES = 2
CACHE_TTL_S = 900  # 15 minutes
IMD_CACHE_DIR = config.CACHE_DIR / "imd"
MAPPING_FILE = Path(__file__).resolve().parents[2] / "data" / "imd_warning_codes.json"


def _load_json(path: Path) -> Any:
    """Safely load JSON file if it exists."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Error loading %s: %s", path, exc)
    return None


def _save_json(path: Path, data: Any) -> None:
    """Save data to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Error saving %s: %s", path, exc)


def load_warning_code_mappings() -> dict[str, Any]:
    """Load color and weather warning code descriptions from JSON mapping."""
    data = _load_json(MAPPING_FILE)
    if isinstance(data, dict):
        return data
    return {"color_codes": {}, "weather_codes": {}}


def decode_warning_code(code: str | int, mappings: dict[str, Any]) -> dict[str, str]:
    """Translate raw IMD code to readable level and label."""
    c_str = str(code).strip()
    color_map = mappings.get("color_codes", {})

    if c_str in color_map:
        info = color_map[c_str]
        return {
            "code": c_str,
            "label": info.get("label", f"Code {c_str}"),
            "color": info.get("color", "Green"),
            "level": info.get("level", "low"),
        }

    return {
        "code": c_str,
        "label": f"Unknown code {c_str}",
        "color": "Grey",
        "level": "low",
    }


def match_imd_district(imd_name: str, districts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Fuzzy match an IMD district name to one of FloodSaathi's districts."""
    target = imd_name.lower().strip()
    for d in districts:
        if d["name"].lower() in target or target in d["name"].lower():
            return d

    names = [d["name"].lower() for d in districts]
    matches = difflib.get_close_matches(target, names, n=1, cutoff=0.70)
    if matches:
        matched_str = matches[0]
        for d in districts:
            if d["name"].lower() == matched_str:
                return d
    return None


class IMDAdapter:
    """IMD API client with caching, retries, and fallback."""

    def __init__(self, base_url: str | None = None, enabled: bool | None = None) -> None:
        """Initialize adapter state and configuration."""
        self.base_url = base_url or config.IMD_API_BASE
        self.enabled = config.IMD_ENABLED if enabled is None else enabled
        self.status = "Live" if self.enabled else "Disabled"

    def _fetch_endpoint(self, endpoint: str, fallback_filename: str) -> Any:
        """Generic fetch with timeout, 2 retries, 15m cache, and local fallback."""
        cache_path = IMD_CACHE_DIR / f"{endpoint.strip('/')}_cache.json"
        fallback_path = IMD_CACHE_DIR / fallback_filename

        if not self.enabled:
            self.status = "Disabled"
            # Return cached or fallback data when disabled
            return _load_json(cache_path) or _load_json(fallback_path) or []

        now = time.time()
        cached = _load_json(cache_path)
        if cached and isinstance(cached, dict) and (now - cached.get("timestamp", 0) < CACHE_TTL_S):
            self.status = "Cached (15m window)"
            return cached.get("data", [])

        url = f"{self.base_url}{endpoint}"
        for attempt in range(RETRIES + 1):
            try:
                resp = requests.get(url, timeout=TIMEOUT_S)
                if resp.status_code == 200:
                    data = resp.json()
                    _save_json(cache_path, {"timestamp": now, "data": data})
                    self.status = "Live (200 OK)"
                    return data
                elif resp.status_code in (401, 403):
                    logger.warning("IMD API auth failure HTTP %d", resp.status_code)
                    break
            except Exception as exc:
                logger.warning("IMD fetch error attempt %d: %s", attempt + 1, exc)
                if attempt < RETRIES:
                    time.sleep(1.0)

        self.status = "Failed (Using Fallback)"
        if cached and isinstance(cached, dict):
            return cached.get("data", [])
        return _load_json(fallback_path) or []

    def get_district_warnings(self, district_id: int | None = None) -> list[dict[str, Any]]:
        """Fetch and decode district warnings for all or specific district."""
        raw_list = self._fetch_endpoint("/districtwarning", "districtwarning_sample.json")
        mappings = load_warning_code_mappings()
        districts = list_districts()

        results: list[dict[str, Any]] = []
        for item in raw_list if isinstance(raw_list, list) else []:
            imd_name = item.get("district_name", "")
            matched_d = match_imd_district(imd_name, districts)
            if district_id and matched_d and matched_d["id"] != district_id:
                continue

            day1 = decode_warning_code(item.get("day_1_code", "0"), mappings)
            day2 = decode_warning_code(item.get("day_2_code", "0"), mappings)
            day3 = decode_warning_code(item.get("day_3_code", "0"), mappings)

            results.append(
                {
                    "imd_district_name": imd_name,
                    "matched_district": matched_d["name"] if matched_d else None,
                    "district_id": matched_d["id"] if matched_d else None,
                    "state": item.get("state_name", ""),
                    "warning_text": item.get("warning_text", ""),
                    "day_1": day1,
                    "day_2": day2,
                    "day_3": day3,
                }
            )

        return results

    def get_district_nowcast(self, district_id: int | None = None) -> list[dict[str, Any]]:
        """Fetch short-term nowcasts with severity and phenomenon."""
        raw_list = self._fetch_endpoint("/districtnowcast", "districtnowcast_sample.json")
        districts = list_districts()

        results: list[dict[str, Any]] = []
        for item in raw_list if isinstance(raw_list, list) else []:
            imd_name = item.get("district_name", "")
            matched_d = match_imd_district(imd_name, districts)
            if district_id and matched_d and matched_d["id"] != district_id:
                continue

            results.append(
                {
                    "imd_district_name": imd_name,
                    "matched_district": matched_d["name"] if matched_d else None,
                    "district_id": matched_d["id"] if matched_d else None,
                    "severity": item.get("severity", "Info"),
                    "level": item.get("level", "medium"),
                    "color": item.get("color", "Yellow"),
                    "phenomenon": item.get("phenomenon", ""),
                    "valid_until": item.get("valid_until", ""),
                    "nowcast_text": item.get("nowcast_text", ""),
                }
            )
        return results

    def get_district_badge(self, district_name: str) -> dict[str, str] | None:
        """Return warning badge label and level for a specific district name."""
        warnings = self.get_district_warnings()
        for w in warnings:
            if w.get("matched_district", "").lower() == district_name.lower():
                day1 = w["day_1"]
                return {
                    "label": f"IMD {day1['color']}: {day1['label']}",
                    "level": day1["level"],
                    "color": day1["color"].lower(),
                    "text": w["warning_text"],
                }
        return None
