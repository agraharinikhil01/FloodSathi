"""
src/integrations/open_meteo.py
------------------------------
Adapters for Open-Meteo Forecast and Flood APIs.
Calculates 48-hour precipitation and handles river discharge spatial shifting
when initial discharge readings are zero or null.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.integrations.base import BaseAdapter

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"


class OpenMeteoForecastAdapter(BaseAdapter):
    """Adapter for Open-Meteo Weather Forecast API with 1-hour cache TTL."""

    def __init__(self) -> None:
        """Initialize with 1-hour cache TTL."""
        super().__init__(source_name="open_meteo_forecast", cache_ttl_seconds=3600)

    def get_forecast(self, lat: float, lon: float) -> dict[str, Any]:
        """Fetch 7-day hourly precipitation and compute 48h rain sum."""
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "hourly": "precipitation",
            "daily": "precipitation_sum",
            "forecast_days": 7,
            "timezone": "Asia/Kolkata",
        }
        resp = self.execute_request(url=FORECAST_URL, params=params)
        data = resp.get("data")

        rain_48h = 0.0
        daily_sum = 0.0
        if isinstance(data, dict):
            hourly_precip = data.get("hourly", {}).get("precipitation", [])
            rain_48h = round(float(sum(hourly_precip[:48])), 2) if hourly_precip else 0.0
            daily_precip = data.get("daily", {}).get("precipitation_sum", [])
            daily_sum = round(float(daily_precip[0]), 2) if daily_precip else 0.0

        return {
            "lat": lat,
            "lon": lon,
            "rain_48h_mm": rain_48h,
            "daily_sum_mm": daily_sum,
            "raw": data,
            "fetched_at": resp["fetched_at"],
            "source_status": resp["source_status"],
            "latency_ms": resp["latency_ms"],
        }


class OpenMeteoFloodAdapter(BaseAdapter):
    """Adapter for Open-Meteo Flood API with 3-hour cache TTL and river shift logic."""

    def __init__(self) -> None:
        """Initialize with 3-hour cache TTL."""
        super().__init__(source_name="open_meteo_flood", cache_ttl_seconds=10800)

    def _query_discharge(self, lat: float, lon: float) -> tuple[float, dict[str, Any]]:
        """Query discharge at coordinates and return maximum discharge and raw data."""
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "river_discharge,river_discharge_max",
            "forecast_days": 7,
        }
        res = self.execute_request(url=FLOOD_URL, params=params)
        data = res.get("data")
        max_d = 0.0
        if isinstance(data, dict):
            daily = data.get("daily", {})
            d_vals = daily.get("river_discharge", []) + daily.get("river_discharge_max", [])
            valid = [float(v) for v in d_vals if v is not None and v > 0]
            if valid:
                max_d = max(valid)
        return max_d, res

    def get_river_discharge(self, lat: float, lon: float) -> dict[str, Any]:
        """Fetch river discharge; if null/zero, shift coords in 4 directions."""
        max_val, initial_res = self._query_discharge(lat, lon)
        shifted = False

        if max_val <= 0.0:
            # 5 km grid shift retry (+/- 0.05 and 0.1 degrees north/south/east/west)
            shifts = [(0.07, 0.0), (-0.07, 0.0), (0.0, 0.07), (0.0, -0.07)]
            for d_lat, d_lon in shifts:
                shifted_val, _ = self._query_discharge(lat + d_lat, lon + d_lon)
                if shifted_val > max_val:
                    max_val = shifted_val
                    shifted = True

        return {
            "lat": lat,
            "lon": lon,
            "river_discharge_m3s": round(max_val, 2),
            "note": "modelled, not measured",
            "shifted_grid": shifted,
            "fetched_at": initial_res["fetched_at"],
            "source_status": initial_res["source_status"],
            "latency_ms": initial_res["latency_ms"],
        }
