"""Pydantic schemas for health and common responses."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="ok")
    app: str = Field(default="FloodSaathi")
    version: str = Field(default="2.0.0")
    database: str = Field(default="connected")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ErrorDetail(BaseModel):
    """Standard error response detail."""

    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""

    error: ErrorDetail
