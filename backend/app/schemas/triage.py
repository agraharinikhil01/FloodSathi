"""Pydantic schemas for emergency help request submission and triage response."""

from typing import List, Optional

from pydantic import BaseModel, Field


class TriageSubmission(BaseModel):
    """User submitted emergency distress message."""

    message: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Raw distress text in Hindi, English, or Hinglish",
    )
    district: Optional[str] = Field(default="Patna", description="Optional selected district name")
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_text: Optional[str] = None
    location_source: Optional[str] = None
    location_confidence: Optional[str] = None


class Coordinates(BaseModel):
    """Latitude and Longitude of extracted location."""

    lat: Optional[float] = None
    lon: Optional[float] = None


class TriageResponse(BaseModel):
    """Structured extraction response from triage engine."""

    id: int
    status: str
    triage_method: str
    urgency: str
    urgency_score: int
    need: str
    people_count: int
    vulnerable: List[str]
    location_text: str
    location_confidence: str
    location_source: Optional[str] = None
    coordinates: Coordinates
    district: Optional[str] = None
    summary: str
    summary_hi: Optional[str] = None
    language: str
    created_at: str
