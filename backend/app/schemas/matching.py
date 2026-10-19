"""Pydantic schemas for resource matching and coordinator dispatch."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ResourceDetail(BaseModel):
    """Resource match detail with distance and ETA."""

    id: Optional[int] = None
    name: str
    type: Optional[str] = None
    skills: Optional[str] = None
    distance_km: float
    eta_min: int


class MatchResponse(BaseModel):
    """Response returned when a request is matched to emergency resources."""

    request_id: int
    status: str
    hospital: Optional[ResourceDetail] = None
    shelter: Optional[ResourceDetail] = None
    volunteer: Optional[ResourceDetail] = None


class CoordinatorRequestItem(BaseModel):
    """Help request with assignment info for coordinator dashboard."""

    id: int
    district: str
    raw_text: str
    language: Optional[str] = None
    urgency: Optional[int] = None
    need: Optional[str] = None
    people_count: Optional[int] = None
    location_raw: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_source: Optional[str] = None
    location_confidence: Optional[str] = None
    summary_en: Optional[str] = None
    summary_hi: Optional[str] = None
    status: str
    created_at: str
    assignments: Dict[str, Any]


class UpdateLocationPayload(BaseModel):
    """Payload to update and verify a request's location."""

    lat: float
    lon: float
    location_raw: Optional[str] = None
    location_source: str = "manual_pin"
    location_confidence: str = "high"
