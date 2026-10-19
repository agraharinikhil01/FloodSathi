"""
tests/test_adapters_live.py
---------------------------
Live network integration tests hitting external endpoints.
Run explicitly with: pytest -m live
"""

from __future__ import annotations

import pytest

from src.integrations.gdacs import GDACSAdapter
from src.integrations.nominatim import NominatimAdapter
from src.integrations.open_meteo import OpenMeteoFloodAdapter, OpenMeteoForecastAdapter
from src.integrations.opentopodata import OpenTopoDataAdapter


@pytest.mark.live
def test_live_open_meteo_forecast() -> None:
    """Hit live Open-Meteo Forecast endpoint once."""
    adapter = OpenMeteoForecastAdapter()
    res = adapter.get_forecast(lat=26.25, lon=92.34)
    assert res["source_status"] in ("live", "cached")
    assert res["rain_48h_mm"] >= 0.0


@pytest.mark.live
def test_live_open_meteo_flood() -> None:
    """Hit live Open-Meteo Flood endpoint once."""
    adapter = OpenMeteoFloodAdapter()
    res = adapter.get_river_discharge(lat=26.25, lon=92.34)
    assert res["source_status"] in ("live", "cached")
    assert res["river_discharge_m3s"] >= 0.0


@pytest.mark.live
def test_live_nominatim_geocode() -> None:
    """Hit live Nominatim geocoding endpoint once."""
    adapter = NominatimAdapter()
    res = adapter.geocode("Dispur, Assam")
    assert res["source_status"] in ("live", "cached")
    assert res["lat"] > 0.0


@pytest.mark.live
def test_live_opentopodata_elevation() -> None:
    """Hit live OpenTopoData elevation endpoint once."""
    adapter = OpenTopoDataAdapter()
    res = adapter.get_elevation_batch([(26.25, 92.34)])
    assert res["source_status"] in ("live", "cached")
    assert len(res["elevations"]) == 1


@pytest.mark.live
def test_live_gdacs_flood_feed() -> None:
    """Hit live GDACS flood RSS feed once."""
    adapter = GDACSAdapter()
    res = adapter.get_india_flood_events()
    assert res["source_status"] in ("live", "cached")
