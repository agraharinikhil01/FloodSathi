"""Pydantic schemas for alerts and system telemetry."""

from typing import List, Optional

from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    """Emergency alert response schema."""

    id: int
    district: str
    level: str
    message_en: str
    message_hi: str
    channel: str
    source: str
    identifier: str
    sent_at: str


class AlertCreate(BaseModel):
    """Schema for generating or dispatching a new alert."""

    district: str = Field(...)
    level: str = Field(default="high")
    channel: str = Field(default="all")


class BroadcastResponse(BaseModel):
    """Response returned upon simulating alert broadcast."""

    status: str
    mock: bool
    alert_id: int
    channel: str
    dispatched_count: int
    delivery_rate: str
    timestamp: str
    message: str


class AdapterStatusItem(BaseModel):
    """Telemetry item for an external data source adapter."""

    name: str
    status: str
    cache_policy: str
    latency_ms: Optional[float] = None
    last_fetched: Optional[str] = None
    note: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """System-wide telemetry and health status response."""

    status: str
    app: str
    version: str
    database: str
    active_districts: int
    active_requests: int
    adapters: List[AdapterStatusItem]
    timestamp: str
