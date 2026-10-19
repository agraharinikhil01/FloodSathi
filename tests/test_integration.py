"""
tests/test_integration.py
-------------------------
End-to-end integration test validating the entire disaster lifecycle:
Raw distress message -> Triage -> Geocoding -> DB persistence -> Resource Matching ->
Status transition -> Emergency Alert dispatch.
"""

from __future__ import annotations

from src.alerts.generator import generate_alert_for_district
from src.db.queries import (
    get_assignments_for_request,
    get_help_request_by_id,
    list_alerts,
)
from src.matching.matcher import match_help_request
from src.triage.triage import triage_help_request


def test_end_to_end_disaster_lifecycle() -> None:
    """Validate full flow from unstructured citizen message to matched response and alerts."""
    raw_citizen_msg = (
        "Mayong me 4 log fase hain, pani gale tak aa gaya hai. "
        "2 bachche aur ek bujurg hain, jaldi rescue boat bhejo!"
    )

    # 1. Citizen Triage & Persistence
    triage_output = triage_help_request(
        raw_text=raw_citizen_msg,
        fallback_district="Morigaon",
        save_to_db=True,
    )
    req_id = triage_output["request_id"]
    assert req_id is not None
    assert req_id > 0

    triage_res = triage_output["triage"]
    assert triage_res.need == "rescue"
    assert triage_res.urgency in ("critical", "high")
    assert triage_res.people_count >= 1
    assert triage_output["lat"] > 0.0
    assert triage_output["lon"] > 0.0

    # Verify initial database state
    initial_req = get_help_request_by_id(req_id)
    assert initial_req is not None
    assert initial_req["status"] == "new"

    # 2. Automated Resource Allocation & Matching
    match_result = match_help_request(req_id, persist=True)
    assert match_result["status"] == "assigned"
    assert match_result["hospital"]["resource"] is not None
    assert match_result["shelter"]["resource"] is not None
    assert match_result["volunteer"]["resource"] is not None

    # Verify request transitioned to 'assigned'
    updated_req = get_help_request_by_id(req_id)
    assert updated_req is not None
    assert updated_req["status"] == "assigned"

    # Verify assignments table entries
    assignments = get_assignments_for_request(req_id)
    assert len(assignments) == 3
    resource_types = {a["resource_type"] for a in assignments}
    assert resource_types == {"hospital", "shelter", "volunteer"}
    for a in assignments:
        assert a["distance_km"] >= 0.0
        assert a["eta_min"] >= 2

    # 3. Public Emergency Alert Generation
    alert = generate_alert_for_district(
        district_id=1,
        district_name="Morigaon",
        level="High",
        metrics={"precip_48h_mm": 180.0, "river_discharge_m3s": 1200.0},
        channel="public",
    )
    assert alert is not None
    assert len(alert["message_en"]) <= 160
    assert len(alert["message_hi"]) <= 160

    # Verify alert record in database
    district_alerts = list_alerts("Morigaon")
    assert len(district_alerts) > 0
    assert district_alerts[0]["level"].lower() in ("high", "severe")
