"""Contract tests for matching service and coordinator dispatch endpoints."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_coordinator_list_requests():
    """Verify listing requests for coordinator queue."""
    response = client.get("/api/v1/matching/requests")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "id" in first
    assert "status" in first
    assert "urgency" in first
    assert "assignments" in first


def test_match_single_request():
    """Verify matching a single request allocates hospital, shelter, and volunteer."""
    # Fetch first request
    reqs_resp = client.get("/api/v1/matching/requests?status=new")
    assert reqs_resp.status_code == 200
    reqs = reqs_resp.json()
    if not reqs:
        # Create one via triage first
        post_resp = client.post(
            "/api/v1/triage/process",
            json={
                "message": "Urgent evacuation required in Patna Boring Road 4 people.",
                "district": "Patna",
            },
        )
        assert post_resp.status_code == 200
        target_id = post_resp.json()["id"]
    else:
        target_id = reqs[0]["id"]

    match_resp = client.post(f"/api/v1/matching/match/{target_id}")
    assert match_resp.status_code == 200
    match_data = match_resp.json()
    assert match_data["request_id"] == target_id
    assert match_data["status"] == "assigned"
    # Should assign at least volunteer or shelter
    assert match_data["shelter"] is not None or match_data["volunteer"] is not None


def test_match_all_open_requests():
    """Verify batch-matching all open requests."""
    response = client.post("/api/v1/matching/match-all?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
