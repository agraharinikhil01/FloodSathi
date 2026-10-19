"""Contract tests for risk assessment and district query endpoints."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_all_districts():
    """Verify listing all districts returns a valid array of summaries."""
    response = client.get("/api/v1/risk/districts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    first = data[0]
    assert "name" in first
    assert "state" in first
    assert "risk_level" in first


def test_get_district_risk_patna():
    """Verify detailed risk calculation for Patna including official alert override."""
    response = client.get("/api/v1/risk/district/Patna")
    assert response.status_code == 200
    data = response.json()
    assert data["district"]["name"] == "Patna"
    assert "risk" in data
    assert data["risk"]["level"] in ["low", "medium", "high", "severe"]
    assert "factors" in data["risk"]
    assert "rain_contrib" in data["risk"]["factors"]
    assert "discharge_contrib" in data["risk"]["factors"]
    assert "elevation_contrib" in data["risk"]["factors"]
    assert "population_contrib" in data["risk"]["factors"]
    assert len(data["grid_points"]) == 9
    assert "disclaimer" in data


def test_get_district_risk_not_found():
    """Verify non-existent district returns 404."""
    response = client.get("/api/v1/risk/district/NonExistentDistrictXYZ")
    assert response.status_code == 404
