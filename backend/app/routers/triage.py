"""Emergency triage router for processing citizen distress messages."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.schemas.triage import TriageResponse, TriageSubmission
from backend.app.services.triage_service import TriageService

router = APIRouter(prefix="/triage", tags=["Triage"])


@router.post("/process", response_model=TriageResponse)
def process_help_request(payload: TriageSubmission, db: Session = Depends(get_db)):
    """Process incoming distress message using Claude API or deterministic fallback, geocode and save."""
    try:
        result = TriageService.triage_and_save(
            db=db,
            raw_text=payload.message,
            default_district_name=payload.district or "Patna",
            pinned_lat=payload.lat,
            pinned_lon=payload.lon,
            pinned_location_text=payload.location_text,
            pinned_source=payload.location_source,
            pinned_confidence=payload.location_confidence,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Triage processing failed: {str(exc)}")
