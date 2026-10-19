"""Matching Service orchestrating Haversine distance, capacity updates, and resource allocation."""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.models.schema import (
    Assignment,
    District,
    Facility,
    HelpRequest,
    Volunteer,
    utcnow_str,
)

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0
DEFAULT_SPEED_KMH = 25.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two coordinates in kilometers."""
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


class MatchingService:
    """High-level service matching open emergency requests to closest facilities and volunteers."""

    @staticmethod
    def _find_nearest_facility(
        db: Session,
        lat: float,
        lon: float,
        facility_types: List[str],
        district_id: Optional[int] = None,
        required_capacity: int = 1,
    ) -> Tuple[Optional[Facility], float, int]:
        """Find closest facility with adequate remaining capacity."""
        query = db.query(Facility).filter(Facility.type.in_(facility_types))
        if district_id is not None:
            facilities = query.filter(Facility.district_id == district_id).all()
            if not facilities:
                facilities = query.all()
        else:
            facilities = query.all()

        eligible = [f for f in facilities if (f.capacity - f.capacity_used) >= required_capacity]
        if not eligible and facilities:
            eligible = facilities

        if not eligible:
            return None, 0.0, 0

        best = min(eligible, key=lambda f: haversine_distance(lat, lon, f.lat, f.lon))
        dist = haversine_distance(lat, lon, best.lat, best.lon)
        eta = estimate_eta_minutes(dist)
        return best, dist, eta

    @staticmethod
    def _find_nearest_volunteer(
        db: Session,
        lat: float,
        lon: float,
        district_id: Optional[int] = None,
        available_only: bool = True,
    ) -> Tuple[Optional[Volunteer], float, int]:
        """Find closest volunteer prioritizing available responders."""
        query = db.query(Volunteer)
        if available_only:
            query = query.filter(Volunteer.available == 1)

        if district_id is not None:
            vols = query.filter(Volunteer.district_id == district_id).all()
            if not vols:
                vols = query.all()
        else:
            vols = query.all()

        if not vols and available_only:
            # Fall back to all volunteers regardless of current availability
            return MatchingService._find_nearest_volunteer(
                db, lat, lon, district_id, available_only=False
            )

        if not vols:
            return None, 0.0, 0

        best = min(vols, key=lambda v: haversine_distance(lat, lon, v.lat, v.lon))
        dist = haversine_distance(lat, lon, best.lat, best.lon)
        eta = estimate_eta_minutes(dist)
        return best, dist, eta

    @classmethod
    def match_request(cls, db: Session, request_id: int, persist: bool = True) -> Dict[str, Any]:
        """Match request to nearest hospital, shelter, and volunteer, updating DB and capacity."""
        req = db.query(HelpRequest).filter(HelpRequest.id == request_id).first()
        if not req:
            raise ValueError(f"Help request #{request_id} not found.")

        # Coordinate fallback
        lat = req.lat
        lon = req.lon
        if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
            district = req.district or db.query(District).first()
            lat = district.centroid_lat if district else 25.5941
            lon = district.centroid_lon if district else 85.1376

        people = max(1, req.people_count or 1)

        # 1. Hospital / Clinic
        h_fac, h_dist, h_eta = cls._find_nearest_facility(
            db, lat, lon, ["hospital", "clinic"], district_id=req.district_id
        )
        # 2. Shelter / Community Centre / School
        s_fac, s_dist, s_eta = cls._find_nearest_facility(
            db,
            lat,
            lon,
            ["shelter", "community_centre", "school"],
            district_id=req.district_id,
            required_capacity=people,
        )
        # 3. Volunteer
        vol, v_dist, v_eta = cls._find_nearest_volunteer(
            db, lat, lon, district_id=req.district_id, available_only=True
        )

        if persist:
            # Clear previous assignments for this request if any
            db.query(Assignment).filter(Assignment.request_id == req.id).delete()

            # Record assignments
            if h_fac:
                db.add(
                    Assignment(
                        request_id=req.id,
                        resource_type="hospital",
                        resource_id=h_fac.id,
                        distance_km=h_dist,
                        eta_min=h_eta,
                        assigned_at=utcnow_str(),
                    )
                )
            if s_fac:
                db.add(
                    Assignment(
                        request_id=req.id,
                        resource_type="shelter",
                        resource_id=s_fac.id,
                        distance_km=s_dist,
                        eta_min=s_eta,
                        assigned_at=utcnow_str(),
                    )
                )
                s_fac.capacity_used = min(s_fac.capacity, s_fac.capacity_used + people)

            if vol:
                db.add(
                    Assignment(
                        request_id=req.id,
                        resource_type="volunteer",
                        resource_id=vol.id,
                        distance_km=v_dist,
                        eta_min=v_eta,
                        assigned_at=utcnow_str(),
                    )
                )
                vol.available = 0

            req.status = "assigned"
            req.updated_at = utcnow_str()
            db.commit()
            db.refresh(req)

        return {
            "request_id": req.id,
            "status": req.status,
            "hospital": (
                {
                    "id": h_fac.id if h_fac else None,
                    "name": h_fac.name if h_fac else "None within area",
                    "type": h_fac.type if h_fac else "hospital",
                    "distance_km": h_dist,
                    "eta_min": h_eta,
                }
                if h_fac
                else None
            ),
            "shelter": (
                {
                    "id": s_fac.id if s_fac else None,
                    "name": s_fac.name if s_fac else "None within area",
                    "type": s_fac.type if s_fac else "shelter",
                    "distance_km": s_dist,
                    "eta_min": s_eta,
                }
                if s_fac
                else None
            ),
            "volunteer": (
                {
                    "id": vol.id if vol else None,
                    "name": vol.name if vol else "No active volunteer",
                    "skills": vol.skills if vol else "",
                    "distance_km": v_dist,
                    "eta_min": v_eta,
                }
                if vol
                else None
            ),
        }

    @classmethod
    def match_all_open(cls, db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Batch-match open requests prioritized by urgency (5 -> 1)."""
        open_reqs = (
            db.query(HelpRequest)
            .filter(HelpRequest.status == "new")
            .order_by(HelpRequest.urgency.desc(), HelpRequest.created_at.asc())
            .limit(limit)
            .all()
        )
        results = []
        for req in open_reqs:
            res = cls.match_request(db=db, request_id=req.id, persist=True)
            results.append(res)
        return results

    @classmethod
    def list_requests_with_assignments(
        cls,
        db: Session,
        status: Optional[str] = None,
        district_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List requests with full triage metadata and current assignments."""
        query = db.query(HelpRequest)
        if status:
            query = query.filter(HelpRequest.status == status)
        if district_name:
            district = db.query(District).filter(District.name.ilike(district_name)).first()
            if district:
                query = query.filter(HelpRequest.district_id == district.id)

        requests = (
            query.order_by(HelpRequest.urgency.desc(), HelpRequest.created_at.desc())
            .limit(limit)
            .all()
        )

        output = []
        for r in requests:
            assignments = db.query(Assignment).filter(Assignment.request_id == r.id).all()
            matched_info = {}
            for a in assignments:
                if a.resource_type == "volunteer":
                    vol = db.query(Volunteer).filter(Volunteer.id == a.resource_id).first()
                    matched_info["volunteer"] = {
                        "name": vol.name if vol else "Volunteer",
                        "distance_km": a.distance_km,
                        "eta_min": a.eta_min,
                    }
                elif a.resource_type in ["shelter", "hospital"]:
                    fac = db.query(Facility).filter(Facility.id == a.resource_id).first()
                    matched_info[a.resource_type] = {
                        "name": fac.name if fac else a.resource_type,
                        "distance_km": a.distance_km,
                        "eta_min": a.eta_min,
                    }

            output.append(
                {
                    "id": r.id,
                    "district": r.district.name if r.district else "Unknown",
                    "raw_text": r.raw_text,
                    "language": r.language,
                    "urgency": r.urgency,
                    "need": r.need,
                    "people_count": r.people_count,
                    "location_raw": r.location_raw,
                    "lat": r.lat,
                    "lon": r.lon,
                    "location_source": r.location_source or "failed",
                    "location_confidence": r.location_confidence or "low",
                    "summary_en": r.summary_en,
                    "summary_hi": r.summary_hi,
                    "status": r.status,
                    "created_at": r.created_at,
                    "assignments": matched_info,
                }
            )

        return output

    @classmethod
    def update_request_location(
        cls,
        db: Session,
        request_id: int,
        lat: float,
        lon: float,
        location_raw: Optional[str] = None,
        location_source: str = "manual_pin",
        location_confidence: str = "high",
    ) -> HelpRequest:
        """Update and verify a request's geographic location."""
        req = db.query(HelpRequest).filter(HelpRequest.id == request_id).first()
        if not req:
            raise ValueError(f"Help request {request_id} not found")
        req.lat = lat
        req.lon = lon
        if location_raw:
            req.location_raw = location_raw
        req.location_source = location_source
        req.location_confidence = location_confidence
        req.updated_at = utcnow_str()
        db.commit()
        db.refresh(req)
        return req
