"""Matching and coordinator dispatch endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.schemas.matching import CoordinatorRequestItem, MatchResponse
from backend.app.services.matching_service import MatchingService

router = APIRouter(prefix="/matching", tags=["Matching"])


@router.post("/match/{request_id}", response_model=MatchResponse)
def match_single_request(request_id: int, db: Session = Depends(get_db)):
    """Match a single help request to the nearest hospital, shelter, and volunteer."""
    try:
        result = MatchingService.match_request(db=db, request_id=request_id, persist=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(exc)}")


@router.post("/match-all", response_model=List[MatchResponse])
def match_all_open_requests(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Batch-match all open requests prioritized by urgency (5 to 1)."""
    try:
        return MatchingService.match_all_open(db=db, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch matching failed: {str(exc)}")


@router.get("/requests", response_model=List[CoordinatorRequestItem])
def get_coordinator_requests(
    status: Optional[str] = Query(None, description="Filter by status: new, assigned, resolved"),
    district: Optional[str] = Query(None, description="Filter by district name"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve help requests with triage details and assigned resources for coordinator queue."""
    return MatchingService.list_requests_with_assignments(
        db=db, status=status, district_name=district, limit=limit
    )


@router.patch("/request/{request_id}/location")
def update_request_location(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Correct and verify a help request's location, setting confidence to high and source to manual_pin/gps."""
    try:
        lat = float(payload["lat"])
        lon = float(payload["lon"])
        loc_raw = payload.get("location_raw")
        source = payload.get("location_source", "manual_pin")
        conf = payload.get("location_confidence", "high")

        req = MatchingService.update_request_location(
            db=db,
            request_id=request_id,
            lat=lat,
            lon=lon,
            location_raw=loc_raw,
            location_source=source,
            location_confidence=conf,
        )
        return {
            "status": "success",
            "request_id": req.id,
            "lat": req.lat,
            "lon": req.lon,
            "location_raw": req.location_raw,
            "location_source": req.location_source,
            "location_confidence": req.location_confidence,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(exc)}")
