"""
tests/test_sachet.py
--------------------
Contract tests for SACHET RSS and CAP XML feed parsing.
Strictly offline — uses local fixture files with zero network calls.
"""

from __future__ import annotations

from pathlib import Path

from src.integrations.sachet import (
    SachetAdapter,
    is_alert_expired,
    is_flood_related,
    match_district_name,
    parse_cap_xml,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "data" / "cache" / "sachet"


def test_parse_morigaon_cap_xml() -> None:
    """Parse severe flood CAP alert and verify all standard fields."""
    xml_path = FIXTURES_DIR / "cap_alert_morigaon_flood.xml"
    assert xml_path.exists(), "CAP fixture missing"

    data = parse_cap_xml(xml_path.read_text(encoding="utf-8"))
    assert data is not None
    assert data["identifier"] == "SACHET-AS-2026-FL-0042"
    assert data["status"] == "Actual"
    assert data["msgType"] == "Alert"
    assert data["severity"] == "Severe"
    assert "Morigaon" in data["headline"]
    assert "Brahmaputra" in data["description"]
    assert "Morigaon, Assam" in data["areaDesc"]
    assert len(data["polygon"]) > 0
    assert len(data["circle"]) > 0


def test_parse_update_cap_xml() -> None:
    """Parse Update message type alert for Dhubri."""
    xml_path = FIXTURES_DIR / "cap_alert_dhubri_update.xml"
    assert xml_path.exists(), "Update CAP fixture missing"

    data = parse_cap_xml(xml_path.read_text(encoding="utf-8"))
    assert data is not None
    assert data["msgType"] == "Update"
    assert data["severity"] == "Moderate"
    assert "Dhubri" in data["areaDesc"]


def test_flood_keyword_filtering() -> None:
    """Alerts with flood or rain keywords are accepted; unrelated alerts rejected."""
    flood_alert = {"event": "Flash Flood", "headline": "Water rising", "description": "River full"}
    heat_alert = {
        "event": "Heat Wave",
        "headline": "High temperature",
        "description": "45C weather",
    }

    assert is_flood_related(flood_alert) is True
    assert is_flood_related(heat_alert) is False


def test_alert_expiration_logic() -> None:
    """Past expiration returns True, future expiration returns False."""
    assert is_alert_expired("2020-01-01T00:00:00Z") is True
    assert is_alert_expired("2099-01-01T00:00:00Z") is False


def test_fuzzy_district_matching() -> None:
    """Match district names even with trailing state names or punctuation."""
    mock_districts = [
        {"id": 1, "name": "Morigaon"},
        {"id": 2, "name": "Dhubri"},
        {"id": 3, "name": "Darbhanga"},
    ]

    m1 = match_district_name("Morigaon District, Assam Revenue Circle", mock_districts)
    m2 = match_district_name("Parts of South Dhubri along Brahmaputra", mock_districts)
    m3 = match_district_name("Jaipur City, Rajasthan", mock_districts)

    assert m1 is not None and m1["name"] == "Morigaon"
    assert m2 is not None and m2["name"] == "Dhubri"
    assert m3 is None


def test_sachet_adapter_sync_with_local_fixtures() -> None:
    """Adapter loads local RSS and CAP fixtures and extracts valid alerts."""
    adapter = SachetAdapter(rss_url="mock://invalid-url")
    # Feed fetch will fail network and fall back to local sample_rss.xml
    alerts = adapter.sync_alerts()

    assert len(alerts) >= 1
    morigaon_alert = next((a for a in alerts if "Morigaon" in (a.get("headline") or "")), None)
    assert morigaon_alert is not None
    assert morigaon_alert["normalized_level"] == "severe"
