"""Pydantic schemas for risk assessment, grid points, and factor breakdown."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Latitude and Longitude coordinates."""

    lat: float
    lon: float


class BoundingBox(BaseModel):
    """Bounding box coordinates."""

    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None


class DistrictMeta(BaseModel):
    """District geographical and administrative metadata."""

    id: int
    name: str
    state: str
    centroid: Coordinates
    bbox: BoundingBox


class OfficialAlertInfo(BaseModel):
    """Official NDMA / IMD alert information."""

    source: str
    level: str
    message_en: str
    message_hi: str
    sent_at: str
    identifier: Optional[str] = None


class RiskDetail(BaseModel):
    """Composite risk details, factor breakdown, and override state."""

    level: str
    model_level: str
    raw_score: float
    is_overridden: bool
    official_badge: Optional[str] = None
    official_alert: Optional[OfficialAlertInfo] = None
    explanation: str
    factors: Dict[str, float]
    metrics: Dict[str, float]


class GridPointRisk(BaseModel):
    """Individual 5km grid point risk evaluation."""

    id: int
    lat: float
    lon: float
    elevation_m: float
    rain_48h_mm: float
    river_discharge_m3s: float
    risk_score: float
    risk_level: str
    factors: Dict[str, float]


class FacilitiesSummary(BaseModel):
    """Count of available emergency infrastructure."""

    total: int
    shelters: int
    hospitals: int


class LiveWeatherInfo(BaseModel):
    """Real-time weather observation and forecast from OpenWeatherMap."""

    temp_c: float
    feels_like_c: float
    humidity_pct: int
    pressure_hpa: int
    wind_speed_kmh: float
    clouds_pct: int
    condition: str
    description: str
    icon: str
    rain_1h_mm: float
    rain_48h_mm: float
    city_name: Optional[str] = None
    source: str = "openweather"
    fetched_at: Optional[str] = None


class DistrictRiskResponse(BaseModel):
    """Complete response for district risk analysis."""

    district: DistrictMeta
    risk: RiskDetail
    facilities_summary: FacilitiesSummary
    grid_points: List[GridPointRisk]
    live_weather: Optional[LiveWeatherInfo] = None
    disclaimer: str = Field(default="Decision-support tool. Follow official IMD / NDMA warnings.")


class DistrictSummaryItem(BaseModel):
    """Summary item for district list."""

    id: int
    name: str
    state: str
    lat: float
    lon: float
    risk_level: str
    has_official_alert: bool
    alert_source: Optional[str] = None


class LocationSuggestion(BaseModel):
    """Matching location suggestion with district and state details."""

    name: str
    district: str
    state: str
    display_name: str
    lat: float
    lon: float
