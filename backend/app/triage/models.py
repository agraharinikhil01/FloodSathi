"""
src/triage/models.py
--------------------
Pydantic schemas for emergency help request triage and extraction.
Strictly validates location, urgency, primary need, demographic impact,
and language identification.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

UrgencyLevel = Literal["critical", "high", "medium", "low"]
NeedType = Literal["rescue", "medical", "food", "shelter", "other"]
LanguageType = Literal["en", "hi", "hinglish"]

URGENCY_MAP = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
}


class TriageResult(BaseModel):
    """Structured extraction of an incoming unstructured emergency message."""

    location_text: str = Field(
        ..., description="Detected village, landmark, street, or district name"
    )
    urgency: UrgencyLevel = Field(..., description="Triage priority: critical, high, medium, low")
    urgency_score: int = Field(
        default=3, description="Integer urgency mapped 1 to 5 for coordinator ranking"
    )
    need: NeedType = Field(
        ..., description="Primary emergency need: rescue, medical, food, shelter, other"
    )
    people_count: int = Field(
        default=1, ge=1, le=1000, description="Estimated number of affected individuals"
    )
    vulnerable: list[str] = Field(
        default_factory=list,
        description="Identified vulnerable individuals: elderly, children, pregnant, disabled",
    )
    summary: str = Field(..., description="Concise English situational summary")
    summary_hi: str | None = Field(default=None, description="Concise Hindi situational summary")
    language: LanguageType = Field(
        default="en", description="Identified language of user submission"
    )

    @field_validator("urgency", mode="before")
    @classmethod
    def normalize_urgency(cls, val: Any) -> str:
        """Coerce raw strings or integers into standard urgency levels."""
        if isinstance(val, int):
            if val >= 5:
                return "critical"
            elif val == 4:
                return "high"
            elif val == 3:
                return "medium"
            return "low"
        val_str = str(val).lower().strip()
        if val_str in ("critical", "severe", "extreme", "immediate"):
            return "critical"
        elif val_str in ("high", "urgent"):
            return "high"
        elif val_str in ("medium", "moderate"):
            return "medium"
        elif val_str in ("low", "minor"):
            return "low"
        return "medium"

    @field_validator("urgency_score", mode="before")
    @classmethod
    def populate_urgency_score(cls, val: Any, info: Any) -> int:
        """Map categorical urgency to numeric score 1-5."""
        if isinstance(val, int) and 1 <= val <= 5:
            return val
        return 3

    @field_validator("need", mode="before")
    @classmethod
    def normalize_need(cls, val: Any) -> str:
        """Normalize emergency need categories."""
        v = str(val).lower().strip()
        if any(w in v for w in ("rescue", "boat", "evacuate", "trapped", "drowning")):
            return "rescue"
        elif any(w in v for w in ("med", "doctor", "injury", "sick", "medicine", "fever")):
            return "medical"
        elif any(w in v for w in ("food", "water", "ration", "khana", "hungry")):
            return "food"
        elif any(w in v for w in ("shelter", "roof", "tent", "stay")):
            return "shelter"
        return "rescue" if "rescue" in v else "other"

    def model_post_init(self, __context: Any) -> None:
        """Ensure urgency_score reflects normalized urgency."""
        object.__setattr__(self, "urgency_score", URGENCY_MAP.get(self.urgency, 3))


class RequestCreate(BaseModel):
    """Incoming user request submission payload."""

    raw_text: str = Field(..., min_length=3, max_length=1000)
    fallback_district: str | None = None
