"""Risk analysis and district map endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.integrations.nominatim import NominatimAdapter
from backend.app.schemas.risk import (
    DistrictRiskResponse,
    DistrictSummaryItem,
    LiveWeatherInfo,
    LocationSuggestion,
)
from backend.app.services.risk_service import RiskService

router = APIRouter(prefix="/risk", tags=["Risk"])
nominatim_adapter = NominatimAdapter()


@router.get("/weather", response_model=Optional[LiveWeatherInfo])
def get_live_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """Fetch live weather metrics and 48-hour rainfall forecast from OpenWeatherMap for any location."""
    data = RiskService.get_weather(lat=lat, lon=lon)
    if not data:
        raise HTTPException(status_code=404, detail="Live weather data currently unavailable.")
    return data


@router.get("/suggestions", response_model=List[LocationSuggestion])
def get_location_suggestions(
    q: str = Query(..., min_length=2, description="Place or district name query")
):
    """Search multiple places matching the query, showing place name, district, and state across India."""
    return nominatim_adapter.search_suggestions(query=q, limit=6)


@router.get("/districts", response_model=List[DistrictSummaryItem])
def get_all_districts(
    lang: str = Query("en", description="Language: 'en' or 'hi'"), db: Session = Depends(get_db)
):
    """Retrieve all districts with their current summary risk levels."""
    return RiskService.list_all_districts_summary(db=db, lang=lang)


@router.get("/district/{name}", response_model=DistrictRiskResponse)
def get_district_risk(
    name: str,
    lang: str = Query("en", description="Language: 'en' or 'hi'"),
    lat: Optional[float] = Query(None, description="Exact latitude if selected from suggestions"),
    lon: Optional[float] = Query(None, description="Exact longitude if selected from suggestions"),
    state: Optional[str] = Query(None, description="State name if selected from suggestions"),
    district: Optional[str] = Query(
        None, description="District qualifier if selected from suggestions"
    ),
    db: Session = Depends(get_db),
):
    """Retrieve detailed 48h flood risk, factor breakdown, and 5km grid evaluation for a district."""
    result = RiskService.get_district_risk(
        db=db,
        district_name=name,
        lang=lang,
        lat=lat,
        lon=lon,
        state=state,
        district_qualifier=district,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"District '{name}' not found.")
    return result
