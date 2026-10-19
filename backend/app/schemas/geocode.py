"""Geocode schema definitions."""

from typing import Any, Optional

from pydantic import BaseModel


class GeocodeResult(BaseModel):
    name: str
    display_name: str
    lat: float
    lon: float
    type: str = "place"
    bbox: Optional[Any] = None
    source: str  # 'geoapify' | 'photon' | 'nominatim' | 'gps' | 'manual_pin' | 'failed'
    confidence: str  # 'high' | 'medium' | 'low'
    source_status: Optional[str] = None
