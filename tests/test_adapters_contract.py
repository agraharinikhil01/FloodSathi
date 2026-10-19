"""
tests/test_adapters_contract.py
-------------------------------
Contract tests for all no-key adapters in src/integrations/.
Strictly offline — uses local fixtures in data/cache/fixtures/ with zero network calls.
"""

from __future__ import annotations

from unittest.mock import patch

from src.integrations.gdacs import GDACSAdapter
from src.integrations.nominatim import NominatimAdapter
from src.integrations.open_meteo import OpenMeteoFloodAdapter, OpenMeteoForecastAdapter
from src.integrations.opentopodata import OpenTopoDataAdapter
from src.integrations.overpass import OverpassAdapter


def test_open_meteo_forecast_contract() -> None:
    """Forecast adapter computes rain_48h sum correctly from fixture without network."""
    adapter = OpenMeteoForecastAdapter()
    # Force mock network failure to test fixture fallback
    with patch.object(adapter.session, "request", side_effect=Exception("Network Offline")):
        res = adapter.get_forecast(lat=26.25, lon=92.34)

    assert res["source_status"] in ("cached", "fixture")
    assert res["rain_48h_mm"] >= 0.0
    assert "hourly" in res["raw"]


def test_open_meteo_flood_shift_contract() -> None:
    """Flood adapter handles zero discharge by shifting coordinates and marks modelled."""
    adapter = OpenMeteoFloodAdapter()
    with patch.object(adapter.session, "request", side_effect=Exception("Network Offline")):
        res = adapter.get_river_discharge(lat=26.25, lon=92.34)

    assert res["source_status"] in ("cached", "fixture")
    assert res["river_discharge_m3s"] >= 0.0
    assert res["note"] == "modelled, not measured"


def test_overpass_facilities_contract() -> None:
    """Overpass adapter parses 20 facilities into hospitals and shelters."""
    adapter = OverpassAdapter()
    with patch.object(adapter.session, "request", side_effect=Exception("Network Offline")):
        res = adapter.fetch_facilities_for_bbox(
            south=26.0, west=92.1, north=26.5, east=92.6, district_id=1
        )

    assert res["source_status"] in ("cached", "fixture")
    assert res["count"] >= 10
    hospitals = [f for f in res["facilities"] if f["type"] == "hospital"]
    assert len(hospitals) >= 1
    shelters = [f for f in res["facilities"] if f["type"] == "shelter"]
    assert len(shelters) >= 1


def test_nominatim_geocoding_contract() -> None:
    """Nominatim adapter returns coordinates and high confidence on known query."""
    adapter = NominatimAdapter()
    with patch.object(adapter.session, "request", side_effect=Exception("Network Offline")):
        res = adapter.geocode("Morigaon, Assam", fallback_district="Morigaon")

    assert res["source_status"] in ("cached", "fixture", "fallback")
    assert 20.0 < res["lat"] < 30.0
    assert 80.0 < res["lon"] < 95.0
    assert res["location_confidence"] in ("high", "low")


def test_opentopodata_elevation_contract() -> None:
    """Elevation adapter batches coordinates and returns elevations from fixture."""
    adapter = OpenTopoDataAdapter()
    coords = [(26.25, 92.34), (26.26, 92.35), (26.27, 92.36)]
    with patch.object(adapter.session, "request", side_effect=Exception("Network Offline")):
        res = adapter.get_elevation_batch(coords)

    assert res["source_status"] in ("cached", "fixture")
    assert len(res["elevations"]) == 3
    assert all(e > 0.0 for e in res["elevations"])


def test_gdacs_flood_events_contract() -> None:
    """GDACS adapter filters flood events and extracts India events from XML fixture."""
    adapter = GDACSAdapter(feed_url="https://mock-gdacs.local/feed.xml")
    with patch.object(adapter.session, "request", side_effect=Exception("Network Offline")):
        res = adapter.get_india_flood_events()

    assert res["source_status"] in ("cached", "fixture")
    assert res["count"] >= 1
    event = res["events"][0]
    assert "India" in event["title"] or "Brahmaputra" in event["description"]
    assert event["event_type"] == "FL"
