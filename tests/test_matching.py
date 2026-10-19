"""
tests/test_matching.py
-----------------------
Unit and integration tests for Haversine resource matching engine.
Verifies distance calculations, capacity constraints, volunteer availability,
and database assignment persistence.
"""

from __future__ import annotations

from src.db.queries import (
    get_assignments_for_request,
    get_help_request_by_id,
    list_facilities,
    list_volunteers,
    save_help_request,
    update_facility_capacity_used,
)
from src.matching.matcher import (
    estimate_eta_minutes,
    find_nearest_facility,
    find_nearest_volunteer,
    haversine_distance,
    match_help_request,
    run_batch_matching,
)


def test_haversine_distance_known_coordinates() -> None:
    """Verify Haversine formula against known great-circle distances."""
    # Zero distance
    assert haversine_distance(26.25, 92.34, 26.25, 92.34) == 0.0

    # Delhi (28.6139, 77.2090) to Mumbai (19.0760, 72.8777) is approx 1148 km
    dist = haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1140.0 <= dist <= 1160.0


def test_estimate_eta_minutes() -> None:
    """Verify ETA calculation bounds and speed logic."""
    assert estimate_eta_minutes(0.0) == 2
    # 25 km at 25 km/h -> 60 minutes
    assert estimate_eta_minutes(25.0, speed_kmh=25.0) == 60
    # 5 km at 25 km/h -> 12 minutes
    assert estimate_eta_minutes(5.0, speed_kmh=25.0) == 12


def test_find_nearest_facility_with_capacity() -> None:
    """Verify nearest facility selection and capacity constraint handling."""
    # Find nearest hospital to Morigaon centroid
    fac, dist, eta = find_nearest_facility(26.25, 92.34, "hospital")
    assert fac is not None
    assert fac["type"] == "hospital"
    assert dist > 0.0
    assert eta >= 2

    # Verify shelter capacity filtering
    shelters = list_facilities(facility_type="shelter")
    assert len(shelters) > 0
    first_id = shelters[0]["id"]
    # Artificially fill capacity
    cap = shelters[0]["capacity"]
    update_facility_capacity_used(first_id, cap)

    # Search with required capacity = 1
    fac2, _, _ = find_nearest_facility(26.25, 92.34, "shelter", required_capacity=1)
    assert fac2 is not None


def test_find_nearest_volunteer_availability() -> None:
    """Verify that available volunteers are strictly prioritized."""
    vols = list_volunteers(available_only=True)
    assert len(vols) > 0
    vol, dist, eta = find_nearest_volunteer(26.25, 92.34, available_only=True)
    assert vol is not None
    assert vol["available"] == 1
    assert dist >= 0.0


def test_match_single_help_request_persists_assignments() -> None:
    """Test full matching flow on a new emergency request."""
    req_id = save_help_request(
        district_id=1,
        raw_text="Test emergency matching: 4 people trapped",
        language="en",
        location_raw="Morigaon Town",
        lat=26.255,
        lon=92.345,
        urgency=5,
        need="rescue",
        people_count=4,
        vulnerable_groups=["elderly"],
        summary_en="4 people trapped",
        triage_method="fallback",
        status="new",
    )

    res = match_help_request(req_id, persist=True)
    assert res["status"] == "assigned"
    assert res["hospital"]["resource"] is not None
    assert res["shelter"]["resource"] is not None
    assert res["volunteer"]["resource"] is not None

    # Check database status and assignments table
    updated_req = get_help_request_by_id(req_id)
    assert updated_req is not None
    assert updated_req["status"] == "assigned"

    assigns = get_assignments_for_request(req_id)
    assert len(assigns) == 3
    types = {a["resource_type"] for a in assigns}
    assert types == {"hospital", "shelter", "volunteer"}


def test_run_batch_matching_orders_by_urgency() -> None:
    """Verify that batch matching matches requests prioritizing highest urgency."""
    req1 = save_help_request(
        district_id=1,
        raw_text="Low urgency inquiry",
        language="en",
        location_raw="Morigaon",
        lat=26.25,
        lon=92.34,
        urgency=2,
        need="other",
        people_count=1,
        vulnerable_groups=[],
        summary_en="Inquiry",
        triage_method="fallback",
        status="new",
    )
    req2 = save_help_request(
        district_id=1,
        raw_text="CRITICAL RESCUE",
        language="en",
        location_raw="Morigaon",
        lat=26.25,
        lon=92.34,
        urgency=5,
        need="rescue",
        people_count=6,
        vulnerable_groups=["children"],
        summary_en="Rescue needed",
        triage_method="fallback",
        status="new",
    )

    matched = run_batch_matching(request_ids=[req1, req2])
    assert len(matched) == 2
    # The first matched should be the critical request
    assert matched[0]["request_id"] == req2
    assert matched[1]["request_id"] == req1
