"""
backend/app/routers/geocode.py
------------------------------
FastAPI endpoints for multi-tier geocoding and reverse geocoding:
- GET /api/v1/geocode?q=&lat=&lon=&district=&type=
- GET /api/v1/reverse?lat=&lon=&district=
Protected by a 30 req/minute per-IP rate limiter.
"""

import threading
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.integrations.geocode import GeocodeService
from backend.app.models.schema import District
from backend.app.schemas.geocode import GeocodeResult

router = APIRouter(prefix="", tags=["Geocoding"])

geocode_service = GeocodeService()

# 30 requests per minute per IP rate limiter
IP_REQUESTS: Dict[str, List[float]] = {}
IP_LOCK = threading.Lock()
MAX_REQUESTS_PER_MINUTE = 30


def check_ip_rate_limit(request: Request) -> None:
    """Enforce maximum 30 requests per minute per client IP."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    cutoff = now - 60.0

    with IP_LOCK:
        timestamps = IP_REQUESTS.get(client_ip, [])
        # Keep only timestamps in the last 60 seconds
        valid_timestamps = [ts for ts in timestamps if ts > cutoff]
        if len(valid_timestamps) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute.",
            )
        valid_timestamps.append(now)
        IP_REQUESTS[client_ip] = valid_timestamps


@router.get("/geocode", response_model=List[GeocodeResult])
def geocode_location(
    request: Request,
    q: str = Query(..., min_length=1, description="Location search query (Hindi or English)"),
    lat: Optional[float] = Query(None, description="Proximity bias latitude"),
    lon: Optional[float] = Query(None, description="Proximity bias longitude"),
    district: Optional[str] = Query(None, description="Active target district name"),
    type: str = Query("autocomplete", description="'autocomplete' or 'search'"),
    limit: int = Query(5, ge=1, le=10, description="Max results"),
    db: Session = Depends(get_db),
):
    """
    Geocode place query with multi-tier failover (Geoapify -> Photon -> Nominatim).
    Biased towards active district center and bounding box.
    """
    check_ip_rate_limit(request)

    bias_lat = lat
    bias_lon = lon
    bbox: Optional[Dict[str, float]] = None

    if district:
        d = db.query(District).filter(District.name.ilike(district.strip())).first()
        if d:
            if bias_lat is None:
                bias_lat = d.centroid_lat
            if bias_lon is None:
                bias_lon = d.centroid_lon
            if d.bbox_min_lat is not None and d.bbox_max_lat is not None:
                bbox = {
                    "min_lat": d.bbox_min_lat,
                    "max_lat": d.bbox_max_lat,
                    "min_lon": d.bbox_min_lon or (bias_lon - 0.25 if bias_lon else 0.0),
                    "max_lon": d.bbox_max_lon or (bias_lon + 0.25 if bias_lon else 0.0),
                }

    results = geocode_service.geocode(
        q=q,
        lat=bias_lat,
        lon=bias_lon,
        district_name=district,
        bbox=bbox,
        is_autocomplete=(type == "autocomplete"),
        limit=limit,
    )
    return results


@router.get("/reverse", response_model=GeocodeResult)
def reverse_geocode(
    request: Request,
    lat: float = Query(..., description="Latitude to reverse geocode"),
    lon: float = Query(..., description="Longitude to reverse geocode"),
    district: Optional[str] = Query(None, description="Context district name"),
):
    """
    Reverse geocode GPS coordinates to human-readable address with multi-tier failover.
    """
    result = geocode_service.reverse(
        lat=lat,
        lon=lon,
        district_name=district,
    )
    return result
