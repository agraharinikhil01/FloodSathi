"""Contract test for health endpoint and DB connection."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint returns app metadata and official disclaimer."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "FloodSaathi"
    assert "Decision-support tool" in data["disclaimer"]


def test_health_endpoint():
    """Verify health endpoint returns ok and database connection is healthy."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "FloodSaathi"
    assert data["database"] == "connected"
    assert "timestamp" in data
