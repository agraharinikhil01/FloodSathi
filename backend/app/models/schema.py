"""SQLAlchemy 2 database models for FloodSaathi."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.app.db import Base


def utcnow_str() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class District(Base):
    """District boundary and metadata."""

    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    state = Column(String, nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    bbox_min_lat = Column(Float, nullable=True)
    bbox_max_lat = Column(Float, nullable=True)
    bbox_min_lon = Column(Float, nullable=True)
    bbox_max_lon = Column(Float, nullable=True)

    grid_points = relationship("GridPoint", back_populates="district", cascade="all, delete-orphan")
    facilities = relationship("Facility", back_populates="district")
    volunteers = relationship("Volunteer", back_populates="district")
    risk_scores = relationship("RiskScore", back_populates="district", cascade="all, delete-orphan")
    help_requests = relationship("HelpRequest", back_populates="district")
    alerts = relationship("Alert", back_populates="district")


class GridPoint(Base):
    """5km resolution geographical grid sample point within a district."""

    __tablename__ = "grid_points"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(
        Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)

    district = relationship("District", back_populates="grid_points")
    weather_snapshots = relationship(
        "WeatherSnapshot", back_populates="grid_point", cascade="all, delete-orphan"
    )


class WeatherSnapshot(Base):
    """Periodic forecast and weather observation for a grid point."""

    __tablename__ = "weather_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    grid_point_id = Column(
        Integer, ForeignKey("grid_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fetched_at = Column(String, nullable=False, default=utcnow_str)
    valid_from = Column(String, nullable=False)
    valid_to = Column(String, nullable=False)
    precip_1h_mm = Column(Float, nullable=True)
    precip_24h_mm = Column(Float, nullable=True)
    precip_48h_mm = Column(Float, nullable=True)
    river_discharge_m3s = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)

    grid_point = relationship("GridPoint", back_populates="weather_snapshots")


class RiskScore(Base):
    """Calculated composite risk level for a district."""

    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(
        Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level = Column(String, nullable=False)  # 'low', 'medium', 'high', 'severe'
    explanation = Column(Text, nullable=True)
    score_raw = Column(Float, nullable=True)  # 0.0 - 1.0 composite
    computed_at = Column(String, nullable=False, default=utcnow_str)

    district = relationship("District", back_populates="risk_scores")


class Facility(Base):
    """Hospitals, shelters, clinics and assembly points."""

    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(
        Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    type = Column(
        String, nullable=False, index=True
    )  # 'hospital','shelter','school','clinic','community_centre','assembly_point'
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    capacity = Column(Integer, default=0)
    capacity_used = Column(Integer, default=0)
    source = Column(String, default="seed")
    osm_id = Column(String, nullable=True, index=True)

    district = relationship("District", back_populates="facilities")


class Volunteer(Base):
    """Field volunteers available for rescue and assistance."""

    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(
        Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    skills = Column(String, nullable=True)  # e.g., 'rescue,first-aid,boat'
    capacity = Column(Integer, default=1)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    available = Column(Integer, default=1, index=True)  # 1 or 0
    created_at = Column(String, nullable=False, default=utcnow_str)

    district = relationship("District", back_populates="volunteers")


class HelpRequest(Base):
    """Citizen emergency requests triaged with Claude / NLP."""

    __tablename__ = "help_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(
        Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_text = Column(Text, nullable=False)
    language = Column(String, nullable=True)  # 'en','hi','hinglish'
    location_raw = Column(String, nullable=True)
    location_source = Column(
        String, nullable=True
    )  # 'geoapify','photon','nominatim','gps','manual_pin','failed'
    location_confidence = Column(String, nullable=True)  # 'high','medium','low'
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    urgency = Column(Integer, nullable=True, index=True)  # 1 to 5
    need = Column(String, nullable=True)  # 'rescue','medical','food','shelter','other'
    people_count = Column(Integer, nullable=True)
    vulnerable_groups = Column(Text, nullable=True)  # JSON string e.g., '["elderly", "children"]'
    summary_en = Column(Text, nullable=True)
    summary_hi = Column(Text, nullable=True)
    triage_method = Column(String, nullable=True)  # 'llm' or 'fallback'
    status = Column(
        String, nullable=False, default="new", index=True
    )  # 'new','assigned','resolved'
    created_at = Column(String, nullable=False, default=utcnow_str, index=True)
    updated_at = Column(String, nullable=False, default=utcnow_str)

    district = relationship("District", back_populates="help_requests")
    assignments = relationship(
        "Assignment", back_populates="help_request", cascade="all, delete-orphan"
    )


class Assignment(Base):
    """Dispatched resource matched to a help request."""

    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(
        Integer, ForeignKey("help_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type = Column(String, nullable=False)  # 'hospital','shelter','volunteer'
    resource_id = Column(Integer, nullable=False)
    distance_km = Column(Float, nullable=True)
    eta_min = Column(Integer, nullable=True)
    assigned_at = Column(String, nullable=False, default=utcnow_str)

    help_request = relationship("HelpRequest", back_populates="assignments")


class Alert(Base):
    """Official NDMA/IMD or system-generated emergency alert."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(
        Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    level = Column(String, nullable=False)  # 'low','medium','high','severe'
    message_hi = Column(Text, nullable=False)
    message_en = Column(Text, nullable=False)
    channel = Column(String, nullable=False)  # 'public','volunteer','all'
    sent_at = Column(String, nullable=False, default=utcnow_str, index=True)
    source = Column(String, default="internal")  # 'internal','SACHET','IMD'
    identifier = Column(String, nullable=True, index=True)

    district = relationship("District", back_populates="alerts")


class User(Base):
    """Authenticated coordinator or volunteer user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False)  # 'coordinator','volunteer','admin'
    password_hash = Column(String, nullable=False)
    created_at = Column(String, nullable=False, default=utcnow_str)


class ApiUsage(Base):
    """Daily API usage counter for third-party rate-limited and quota-bound APIs."""

    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service = Column(String, nullable=False, index=True)  # e.g., 'geoapify'
    date_str = Column(String, nullable=False, index=True)  # 'YYYY-MM-DD'
    count = Column(Integer, default=0, nullable=False)
