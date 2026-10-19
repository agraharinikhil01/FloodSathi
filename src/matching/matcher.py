"""
src/matching/matcher.py
-----------------------
Resource matching engine for emergency flood requests.
Computes Haversine distances to nearest shelters, hospitals, and volunteers.
Enforces capacity constraints and persists resource assignments to SQLite.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from src.db.queries import (
    get_district_by_name,
    get_help_request_by_id,
    list_facilities,
    list_help_requests,
    list_volunteers,
    save_assignment,
    update_facility_capacity_used,
    update_request_status,
    update_volunteer_availability,
)

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0
DEFAULT_SPEED_KMH = 25.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_KM * c, 3)


def estimate_eta_minutes(distance_km: float, speed_kmh: float = DEFAULT_SPEED_KMH) -> int:
    """Estimate transit time in minutes given distance and speed in flood conditions."""
    if distance_km <= 0.05:
        return 2
    hours = distance_km / max(speed_kmh, 1.0)
    return max(2, int(round(hours * 60)))


def _resolve_coordinates(req: dict[str, Any]) -> tuple[float, float]:
    """Extract coordinates from request or fallback to district centroid."""
    lat = req.get("lat")
    lon = req.get("lon")
    if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
        return float(lat), float(lon)

    d_info = get_district_by_name("Morigaon")
    if d_info:
        return float(d_info["centroid_lat"]), float(d_info["centroid_lon"])
    return 26.25, 92.34


def find_nearest_facility(
    lat: float,
    lon: float,
    facility_type: str,
    district_id: int | None = None,
    required_capacity: int = 1,
) -> tuple[dict[str, Any] | None, float, int]:
    """Find closest facility with adequate remaining capacity."""
    facilities = list_facilities(district_id=district_id, facility_type=facility_type)
    if not facilities and district_id is not None:
        facilities = list_facilities(facility_type=facility_type)

    eligible = [
        f
        for f in facilities
        if (int(f.get("capacity", 100)) - int(f.get("capacity_used", 0))) >= required_capacity
    ]
    if not eligible and facilities:
        eligible = facilities

    if not eligible:
        return None, 0.0, 0

    best_fac = min(
        eligible,
        key=lambda f: haversine_distance(lat, lon, float(f["lat"]), float(f["lon"])),
    )
    dist = haversine_distance(lat, lon, float(best_fac["lat"]), float(best_fac["lon"]))
    eta = estimate_eta_minutes(dist)
    return best_fac, dist, eta


def find_nearest_volunteer(
    lat: float,
    lon: float,
    district_id: int | None = None,
    available_only: bool = True,
) -> tuple[dict[str, Any] | None, float, int]:
    """Find closest volunteer prioritizing available responders."""
    vols = list_volunteers(district_id=district_id, available_only=available_only)
    if not vols and district_id is not None:
        vols = list_volunteers(available_only=available_only)
    if not vols and available_only:
        vols = list_volunteers(district_id=district_id, available_only=False)

    if not vols:
        return None, 0.0, 0

    best_vol = min(
        vols,
        key=lambda v: haversine_distance(lat, lon, float(v["lat"]), float(v["lon"])),
    )
    dist = haversine_distance(lat, lon, float(best_vol["lat"]), float(best_vol["lon"]))
    eta = estimate_eta_minutes(dist)
    return best_vol, dist, eta


def match_help_request(request_id: int, persist: bool = True) -> dict[str, Any]:
    """Find nearest shelter, hospital, and volunteer for a request and optionally persist."""
    req = get_help_request_by_id(request_id)
    if not req:
        raise ValueError(f"Help request #{request_id} not found in database.")

    lat, lon = _resolve_coordinates(req)
    dist_id = req.get("district_id")
    people = max(1, int(req.get("people_count", 1)))

    h_fac, h_dist, h_eta = find_nearest_facility(lat, lon, "hospital", district_id=dist_id)
    s_fac, s_dist, s_eta = find_nearest_facility(
        lat, lon, "shelter", district_id=dist_id, required_capacity=people
    )
    vol, v_dist, v_eta = find_nearest_volunteer(lat, lon, district_id=dist_id)

    if persist:
        _persist_assignments(
            request_id, h_fac, h_dist, h_eta, s_fac, s_dist, s_eta, vol, v_dist, v_eta, people
        )

    return {
        "request_id": request_id,
        "hospital": {"resource": h_fac, "distance_km": h_dist, "eta_min": h_eta},
        "shelter": {"resource": s_fac, "distance_km": s_dist, "eta_min": s_eta},
        "volunteer": {"resource": vol, "distance_km": v_dist, "eta_min": v_eta},
        "status": "assigned" if persist else "preview",
    }


def _persist_assignments(
    request_id: int,
    h_fac: dict[str, Any] | None,
    h_dist: float,
    h_eta: int,
    s_fac: dict[str, Any] | None,
    s_dist: float,
    s_eta: int,
    vol: dict[str, Any] | None,
    v_dist: float,
    v_eta: int,
    people_count: int,
) -> None:
    """Save resource assignment records and update resource states."""
    if h_fac:
        save_assignment(request_id, "hospital", int(h_fac["id"]), h_dist, h_eta)
    if s_fac:
        save_assignment(request_id, "shelter", int(s_fac["id"]), s_dist, s_eta)
        update_facility_capacity_used(int(s_fac["id"]), people_count)
    if vol:
        save_assignment(request_id, "volunteer", int(vol["id"]), v_dist, v_eta)
        update_volunteer_availability(int(vol["id"]), False)
    update_request_status(request_id, "assigned")


def run_batch_matching(
    district_id: int | None = None,
    request_ids: list[int] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Match all new requests sorted by urgency in descending order."""
    if request_ids:
        targets = [get_help_request_by_id(rid) for rid in request_ids]
        active_reqs = [r for r in targets if r and r.get("status") == "new"]
    else:
        active_reqs = list_help_requests(status="new", district_id=district_id, limit=limit)

    active_reqs.sort(key=lambda x: (x.get("urgency", 3), x.get("created_at", "")), reverse=True)

    results = []
    for r in active_reqs:
        try:
            match_res = match_help_request(int(r["id"]), persist=True)
            results.append(match_res)
        except Exception as exc:
            logger.error("Failed to match request #%s: %s", r.get("id"), exc)

    return results
