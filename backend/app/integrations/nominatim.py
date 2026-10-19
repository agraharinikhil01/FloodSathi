"""
src/integrations/nominatim.py
-----------------------------
Nominatim OpenStreetMap geocoding adapter for Indian locations.
Enforces 1 request/second throttling, permanent disk caching,
and fallback to district centroid with low location_confidence.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from backend.app.integrations.base import BaseAdapter
from src.db.queries import get_district_by_name

logger = logging.getLogger(__name__)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_rate_lock = threading.Lock()
_last_request_time = 0.0


def _enforce_rate_limit() -> None:
    """Enforce strict 1.0 second delay between live Nominatim requests."""
    global _last_request_time
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _last_request_time = time.time()


class NominatimAdapter(BaseAdapter):
    """Adapter for Nominatim geocoding with permanent caching and rate limiting."""

    def __init__(self) -> None:
        """Initialize with permanent cache TTL (100 years)."""
        super().__init__(source_name="nominatim", cache_ttl_seconds=100 * 365 * 86400)

    def geocode(self, location_text: str, fallback_district: str | None = None) -> dict[str, Any]:
        """Geocode query string to lat/lon with 1 req/s rate limit and centroid fallback."""
        cleaned_query = (location_text or "").strip()
        if not cleaned_query:
            cleaned_query = fallback_district or "Morigaon"

        params = {
            "q": cleaned_query,
            "format": "json",
            "limit": 1,
            "countrycodes": "in",
        }

        # Rate limiter before sending request
        _enforce_rate_limit()

        resp = self.execute_request(
            url=NOMINATIM_SEARCH_URL,
            params=params,
            custom_cache_key=f"nominatim_{cleaned_query.lower()}",
        )

        data = resp.get("data")
        if isinstance(data, list) and len(data) > 0:
            top = data[0]
            lat = float(top.get("lat", 0.0))
            lon = float(top.get("lon", 0.0))
            return {
                "query": cleaned_query,
                "lat": lat,
                "lon": lon,
                "display_name": top.get("display_name", cleaned_query),
                "location_confidence": "high",
                "fetched_at": resp["fetched_at"],
                "source_status": resp["source_status"],
                "latency_ms": resp["latency_ms"],
            }

        # Fallback to district center
        target_district = fallback_district or "Morigaon"
        d_info = get_district_by_name(target_district)
        c_lat = float(d_info["centroid_lat"]) if d_info else 26.25
        c_lon = float(d_info["centroid_lon"]) if d_info else 92.34

        return {
            "query": cleaned_query,
            "lat": c_lat,
            "lon": c_lon,
            "display_name": f"{target_district} District Centroid",
            "location_confidence": "low",
            "fetched_at": resp["fetched_at"],
            "source_status": (
                resp["source_status"] if resp["source_status"] != "live" else "fallback"
            ),
            "latency_ms": resp["latency_ms"],
        }

    def search_suggestions(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        """Return list of matching locations with exact place name, district, and state."""
        cleaned_query = (query or "").strip()
        if not cleaned_query or len(cleaned_query) < 2:
            return []

        params = {
            "q": cleaned_query,
            "format": "json",
            "limit": limit,
            "countrycodes": "in",
            "addressdetails": 1,
        }

        _enforce_rate_limit()

        resp = self.execute_request(
            url=NOMINATIM_SEARCH_URL,
            params=params,
            custom_cache_key=f"suggest_{cleaned_query.lower()}_{limit}",
        )

        data = resp.get("data")
        suggestions = []

        if isinstance(data, list):
            for item in data:
                addr = item.get("address", {})
                district = (
                    addr.get("state_district")
                    or addr.get("county")
                    or addr.get("city")
                    or addr.get("subdistrict")
                    or ""
                )
                state = addr.get("state") or ""
                place_name = item.get("name") or item.get("display_name", "").split(",")[0].strip()

                lat_val = float(item.get("lat", 0.0))
                lon_val = float(item.get("lon", 0.0))

                suggestions.append(
                    {
                        "name": place_name,
                        "district": district or place_name,
                        "state": state or "India",
                        "display_name": item.get("display_name", ""),
                        "lat": lat_val,
                        "lon": lon_val,
                    }
                )

        return suggestions
