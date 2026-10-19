"""
tests/test_imd.py
-----------------
Contract tests for optional IMD adapter.
Ensures warning codes mapping, fallback JSON loading, and fuzzy matching work offline.
"""

from __future__ import annotations

from src.integrations.imd import (
    IMDAdapter,
    decode_warning_code,
    load_warning_code_mappings,
    match_imd_district,
)


def test_decode_known_and_unknown_warning_codes() -> None:
    """Known codes map to labels; unknown codes become 'Unknown code X'."""
    mappings = load_warning_code_mappings()

    c1 = decode_warning_code("1", mappings)
    assert c1["color"] == "Green"
    assert c1["level"] == "low"

    c4 = decode_warning_code("4", mappings)
    assert c4["color"] == "Red"
    assert c4["level"] == "severe"

    c99 = decode_warning_code("99", mappings)
    assert c99["label"] == "Unknown code 99"
    assert c99["level"] == "low"


def test_match_imd_district_fuzzy() -> None:
    """Fuzzy matching correctly identifies district despite minor variations."""
    districts = [
        {"id": 1, "name": "Morigaon"},
        {"id": 2, "name": "Dhubri"},
        {"id": 3, "name": "Darbhanga"},
    ]

    m1 = match_imd_district("MORIGAON", districts)
    m2 = match_imd_district("Darbhanga Rural", districts)
    m3 = match_imd_district("UnknownDistrict", districts)

    assert m1 is not None and m1["name"] == "Morigaon"
    assert m2 is not None and m2["name"] == "Darbhanga"
    assert m3 is None


def test_imd_adapter_offline_disabled_behavior() -> None:
    """Adapter returns fallback data when disabled without making network calls."""
    adapter = IMDAdapter(enabled=False)
    assert adapter.status == "Disabled"

    warnings = adapter.get_district_warnings()
    assert isinstance(warnings, list)
    assert len(warnings) > 0

    morigaon_w = next((w for w in warnings if w["matched_district"] == "Morigaon"), None)
    assert morigaon_w is not None
    assert morigaon_w["day_1"]["color"] == "Red"
    assert morigaon_w["day_1"]["level"] == "severe"


def test_imd_district_badge_extraction() -> None:
    """District badge helper returns structured color and text."""
    adapter = IMDAdapter(enabled=False)
    badge = adapter.get_district_badge("Morigaon")

    assert badge is not None
    assert "Red" in badge["label"]
    assert badge["level"] == "severe"
