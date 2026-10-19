"""Contract tests for emergency help request triage endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_triage_process_english_critical():
    """Verify processing critical English request extracts rescue need and elderly vulnerability."""
    payload = {
        "message": "Water entered ground floor, 5 people stuck on rooftop including elderly grandmother. Please send boat urgently!",
        "district": "Patna",
    }
    response = client.post("/api/v1/triage/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["need"] == "rescue"
    assert data["urgency"] in ["critical", "high"]
    assert data["people_count"] >= 1
    assert "elderly" in data["vulnerable"]
    assert data["status"] == "new"
    assert "summary" in data


def test_triage_process_hindi():
    """Verify processing Hindi message accurately detects language and need."""
    payload = {
        "message": "भैया हमारे घर में पानी भर गया है, 4 लोग फंसे हैं, खाने पीने को कुछ नहीं है 2 दिन से।",
        "district": "Patna",
    }
    response = client.post("/api/v1/triage/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["language"] in ["hi", "hinglish"]
    assert data["need"] in ["food", "rescue"]
    assert data["people_count"] >= 1
    assert data["urgency_score"] >= 3


def test_triage_process_hinglish_medical():
    """Verify processing Hinglish message detects medical urgency."""
    payload = {
        "message": "Bhaiya paani bahut tez aa raha hai, road blocked hai, pregnant lady hai hospital pahunchana hai jaldi.",
        "district": "Patna",
    }
    response = client.post("/api/v1/triage/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["need"] == "medical"
    assert "pregnant" in data["vulnerable"]
    assert data["urgency"] in ["critical", "high"]
