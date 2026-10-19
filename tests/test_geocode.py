"""
tests/test_geocode.py
---------------------
Unit and integration tests for multi-tier resilient geocoding service:
- Mocked Geoapify, Photon, and Nominatim responses (no network)
- Fallback order on 401, 429, and timeout
- Daily cap enforcement and counter table
- District ranking & confidence rules (high, medium, low)
- Missing API key behavior
- Zero key leakage in logs, URLs, and API response payloads
- Never-crash guarantee
"""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.integrations.geocode import (
    GeocodeService,
    check_and_increment_daily_cap,
    mask_key,
)


@pytest.fixture
def mock_db(tmp_path, monkeypatch):
    """Temporary SQLite database for api_usage daily cap testing."""
    db_file = tmp_path / "test_api_usage.db"
    monkeypatch.setattr("src.integrations.geocode.get_db_path", lambda: db_file)
    return db_file


@pytest.fixture
def geocode_service(tmp_path, monkeypatch):
    """GeocodeService instance with a temporary disk cache."""
    cache_dir = tmp_path / "geocode_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.integrations.geocode.config.CACHE_DIR", tmp_path)
    srv = GeocodeService()
    # Disable sleep delay during tests to run instantly
    srv.cache_dir = cache_dir
    return srv


# ─────────────────────────────────────────────────────────────────────────────
# 1. Geoapify Success & Normalization
# ─────────────────────────────────────────────────────────────────────────────
def test_geoapify_success_normalization(geocode_service):
    """Mock Geoapify 200 response and check normalized schema output."""
    mock_payload = {
        "results": [
            {
                "name": "Boring Road Crossing",
                "formatted": "Boring Road Crossing, Patna, Bihar, 800001, India",
                "lat": 25.6120,
                "lon": 85.1150,
                "result_type": "street",
                "category": "highway",
                "bbox": [85.110, 25.610, 85.120, 25.615],
                "rank": {"confidence": 0.95, "match_type": "full_match"},
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with (
        patch.object(geocode_service.session, "get", return_value=mock_resp),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", "test-secret-key-12345"),
    ):

        results = geocode_service.geocode(q="Boring Road", district_name="Patna", limit=1)

    assert len(results) >= 1
    res = results[0]
    assert res["name"] == "Boring Road Crossing"
    assert "Patna" in res["display_name"]
    assert res["lat"] == 25.6120
    assert res["lon"] == 85.1150
    assert res["type"] == "street"
    assert res["source"] == "geoapify"
    assert res["confidence"] in ("high", "medium")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Confidence Rules
# ─────────────────────────────────────────────────────────────────────────────
def test_confidence_rules(geocode_service):
    """
    Test confidence classification:
    - Street/building inside district => 'medium'
    - City/district or outside boundary => 'low'
    """
    # Street inside district
    conf_street = geocode_service.evaluate_confidence(
        "street", inside_district=True, source="geoapify"
    )
    assert conf_street == "medium"

    # City match inside district
    conf_city = geocode_service.evaluate_confidence("city", inside_district=True, source="geoapify")
    assert conf_city == "low"

    # Street match outside district
    conf_outside = geocode_service.evaluate_confidence(
        "street", inside_district=False, source="geoapify"
    )
    assert conf_outside == "low"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fallback Order: 401 Unauthorized
# ─────────────────────────────────────────────────────────────────────────────
def test_fallback_order_on_401(geocode_service):
    """When Geoapify returns 401, service should smoothly fall back to Photon."""
    geoapify_resp = MagicMock()
    geoapify_resp.status_code = 401

    photon_resp = MagicMock()
    photon_resp.status_code = 200
    photon_resp.json.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [85.123, 25.609]},
                "properties": {
                    "name": "Danapur Station",
                    "type": "station",
                    "city": "Patna",
                    "state": "Bihar",
                },
            }
        ]
    }

    def mock_get(url, **kwargs):
        if "geoapify.com" in url:
            return geoapify_resp
        if "photon.komoot.io" in url:
            return photon_resp
        return MagicMock(status_code=404)

    with (
        patch.object(geocode_service.session, "get", side_effect=mock_get),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", "test-key"),
    ):

        results = geocode_service.geocode(q="Danapur Station", district_name="Patna")

    assert len(results) >= 1
    assert results[0]["source"] == "photon"
    assert results[0]["name"] == "Danapur Station"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Fallback Order: 429 Rate Limit
# ─────────────────────────────────────────────────────────────────────────────
def test_fallback_order_on_429(geocode_service):
    """When Geoapify returns 429, service should immediately fall back to Photon."""
    geoapify_resp = MagicMock()
    geoapify_resp.status_code = 429

    photon_resp = MagicMock()
    photon_resp.status_code = 200
    photon_resp.json.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [92.345, 26.255]},
                "properties": {
                    "name": "Morigaon Bazar",
                    "type": "village",
                    "district": "Morigaon",
                    "state": "Assam",
                },
            }
        ]
    }

    def mock_get(url, **kwargs):
        if "geoapify.com" in url:
            return geoapify_resp
        if "photon.komoot.io" in url:
            return photon_resp
        return MagicMock(status_code=404)

    with (
        patch.object(geocode_service.session, "get", side_effect=mock_get),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", "test-key"),
    ):

        results = geocode_service.geocode(q="Morigaon Bazar", district_name="Morigaon")

    assert len(results) >= 1
    assert results[0]["source"] == "photon"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fallback Order: Timeout
# ─────────────────────────────────────────────────────────────────────────────
def test_fallback_order_on_timeout(geocode_service):
    """When Geoapify times out, service falls back to Photon."""
    photon_resp = MagicMock()
    photon_resp.status_code = 200
    photon_resp.json.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [85.90, 26.15]},
                "properties": {"name": "Laheriasarai", "type": "suburb"},
            }
        ]
    }

    def mock_get(url, **kwargs):
        if "geoapify.com" in url:
            raise requests.exceptions.Timeout("Geoapify timed out")
        if "photon.komoot.io" in url:
            return photon_resp
        return MagicMock(status_code=404)

    with (
        patch.object(geocode_service.session, "get", side_effect=mock_get),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", "test-key"),
    ):

        results = geocode_service.geocode(q="Laheriasarai", district_name="Darbhanga")

    assert len(results) >= 1
    assert results[0]["source"] == "photon"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Fallback to Nominatim when Photon also fails
# ─────────────────────────────────────────────────────────────────────────────
def test_fallback_to_nominatim_when_photon_fails(geocode_service):
    """When Geoapify and Photon both fail, fall back to Nominatim."""
    nominatim_resp = MagicMock()
    nominatim_resp.status_code = 200
    nominatim_resp.json.return_value = [
        {
            "name": "Boring Canal Road",
            "display_name": "Boring Canal Road, Patna, Bihar, 800001, India",
            "lat": "25.6150",
            "lon": "85.1200",
            "type": "residential",
            "boundingbox": ["25.610", "25.620", "85.115", "85.125"],
        }
    ]

    def mock_get(url, **kwargs):
        if "geoapify.com" in url:
            return MagicMock(status_code=500)
        if "photon.komoot.io" in url:
            return MagicMock(status_code=502)
        if "nominatim.openstreetmap.org" in url:
            return nominatim_resp
        return MagicMock(status_code=404)

    with (
        patch.object(geocode_service.session, "get", side_effect=mock_get),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", "test-key"),
    ):

        results = geocode_service.geocode(q="Boring Canal Road", district_name="Patna")

    assert len(results) >= 1
    assert results[0]["source"] == "nominatim"
    assert results[0]["lat"] == 25.6150


# ─────────────────────────────────────────────────────────────────────────────
# 7. Daily Cap Enforcement
# ─────────────────────────────────────────────────────────────────────────────
def test_daily_cap_behaviour(mock_db):
    """When daily usage counter reaches cap, check_and_increment_daily_cap returns False."""
    cap = 5
    # First 5 calls succeed
    for _ in range(cap):
        allowed = check_and_increment_daily_cap(service="geoapify", cap=cap)
        assert allowed is True

    # 6th call exceeds cap
    exceeded = check_and_increment_daily_cap(service="geoapify", cap=cap)
    assert exceeded is False


def test_service_skips_geoapify_when_daily_cap_reached(geocode_service):
    """When daily cap is reached, Geoapify is skipped entirely without HTTP request."""
    photon_resp = MagicMock()
    photon_resp.status_code = 200
    photon_resp.json.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [85.1, 25.6]},
                "properties": {"name": "Fallback Loc", "type": "place"},
            }
        ]
    }

    with (
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=False),
        patch.object(geocode_service.session, "get", return_value=photon_resp) as mock_get,
    ):

        results = geocode_service.geocode(q="Test query", district_name="Patna")

    # Verify Geoapify URL was never requested
    for call_args in mock_get.call_args_list:
        url = call_args[0][0]
        assert "geoapify.com" not in url

    assert len(results) >= 1
    assert results[0]["source"] == "photon"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Missing Key Behavior
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_key_behaviour(geocode_service):
    """When GEOAPIFY_API_KEY is empty, service skips Geoapify without error."""
    photon_resp = MagicMock()
    photon_resp.status_code = 200
    photon_resp.json.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [85.1, 25.6]},
                "properties": {"name": "No Key Fallback", "type": "place"},
            }
        ]
    }

    with (
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", ""),
        patch.dict("os.environ", {"GEOAPIFY_API_KEY": ""}),
        patch.object(geocode_service.session, "get", return_value=photon_resp) as mock_get,
    ):

        results = geocode_service.geocode(q="No Key Query", district_name="Patna")

    for call_args in mock_get.call_args_list:
        url = call_args[0][0]
        assert "geoapify.com" not in url

    assert len(results) >= 1
    assert results[0]["source"] == "photon"


# ─────────────────────────────────────────────────────────────────────────────
# 9. Never Crash Fallback
# ─────────────────────────────────────────────────────────────────────────────
def test_never_crash_when_all_fail(geocode_service):
    """When all external APIs throw exceptions, service returns district fallback safely."""
    with patch.object(
        geocode_service.session, "get", side_effect=requests.exceptions.ConnectionError("Offline")
    ):
        results = geocode_service.geocode(q="Completely Unknown Area", district_name="Patna")

    assert len(results) >= 1
    res = results[0]
    assert res["confidence"] == "low"
    assert res["source"] in ("fixtures", "district_center", "failed")
    assert res["lat"] != 0.0
    assert res["lon"] != 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 10. Reverse Geocoding
# ─────────────────────────────────────────────────────────────────────────────
def test_reverse_geocoding(geocode_service):
    """Test reverse geocoding returns high-confidence normalized location."""
    mock_geo_resp = MagicMock()
    mock_geo_resp.status_code = 200
    mock_geo_resp.json.return_value = {
        "results": [
            {
                "name": "Gandhi Maidan",
                "formatted": "Gandhi Maidan, Patna, Bihar, 800001, India",
                "lat": 25.6178,
                "lon": 85.1415,
                "result_type": "amenity",
            }
        ]
    }

    with (
        patch.object(geocode_service.session, "get", return_value=mock_geo_resp),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", "test-key"),
    ):

        res = geocode_service.reverse_geocode(lat=25.6178, lon=85.1415, district_name="Patna")

    assert res["name"] == "Gandhi Maidan"
    assert res["confidence"] == "high"
    assert res["source"] == "geoapify"


# ─────────────────────────────────────────────────────────────────────────────
# 11. Secret Key Never Appears in Logs or API Responses
# ─────────────────────────────────────────────────────────────────────────────
def test_key_leak_prevention_in_logs_and_response(geocode_service, caplog):
    """Ensure GEOAPIFY_API_KEY is scrubbed from URLs, logs, and response structures."""
    secret_key = "super_secret_geoapify_key_xyz987"
    url_with_key = (
        f"https://api.geoapify.com/v1/geocode/search?text=Patna&apiKey={secret_key}&limit=5"
    )

    masked = mask_key(url_with_key)
    assert secret_key not in masked
    assert "apiKey=***" in masked

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "name": "Secret Test Spot",
                "formatted": "Secret Test Spot, Patna, Bihar",
                "lat": 25.6,
                "lon": 85.1,
                "result_type": "place",
            }
        ]
    }

    with (
        caplog.at_level(logging.DEBUG),
        patch.object(geocode_service.session, "get", return_value=mock_resp),
        patch("src.integrations.geocode.check_and_increment_daily_cap", return_value=True),
        patch("src.integrations.geocode.config.GEOAPIFY_API_KEY", secret_key),
    ):

        results = geocode_service.geocode(q="Secret Test Spot", district_name="Patna")

    # 1. Assert key is never in result dictionary
    res_str = json.dumps(results)
    assert secret_key not in res_str

    # 2. Assert key is never in any logged string
    for record in caplog.records:
        assert secret_key not in record.message
