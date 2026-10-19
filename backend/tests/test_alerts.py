"""Contract tests for alerts, mock broadcast, and system telemetry endpoints."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_get_alerts_list():
    """Verify alerts endpoint returns a list with official and system alerts."""
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "message_en" in first
        assert "message_hi" in first
        assert "level" in first
        assert len(first["message_en"]) <= 160
        assert len(first["message_hi"]) <= 160


def test_generate_and_broadcast_alert():
    """Verify generating a new alert and simulating broadcast dispatch."""
    gen_resp = client.post(
        "/api/v1/alerts/generate",
        json={"district": "Patna", "level": "severe", "channel": "all"},
    )
    assert gen_resp.status_code == 200
    alert_data = gen_resp.json()
    assert "id" in alert_data
    assert alert_data["level"] == "severe"
    assert "message_en" in alert_data
    assert "message_hi" in alert_data

    # Simulate broadcast
    alert_id = alert_data["id"]
    bc_resp = client.post(f"/api/v1/alerts/{alert_id}/broadcast?channel=all")
    assert bc_resp.status_code == 200
    bc_data = bc_resp.json()
    assert bc_data["status"] == "success"
    assert bc_data["mock"] is True
    assert "dispatched_count" in bc_data


def test_get_system_telemetry():
    """Verify system telemetry status endpoint returns health and adapter details."""
    response = client.get("/api/v1/status/system")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "adapters" in data
    assert len(data["adapters"]) >= 6
    names = [a["name"] for a in data["adapters"]]
    assert any("Open-Meteo" in n for n in names)
    assert any("SACHET" in n for n in names)
