"""
tests/test_alerts.py
--------------------
Unit tests for the emergency alert generation, bilingual translation,
160-character constraint adherence, and Plotly forecast charts.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src.alerts.generator import (
    MAX_ALERT_CHARS,
    _generate_fallback_alert,
    _truncate_160,
    generate_alert_for_district,
    generate_alerts_for_high_risk_districts,
)
from src.db.queries import list_alerts
from src.utils.charts import plot_48h_rainfall, plot_river_discharge


def test_truncate_160_strictly_enforces_limit() -> None:
    """Strings over 160 characters are truncated with ellipsis, preserving <= 160 chars."""
    long_text = "Severe flood emergency alert! " * 10  # ~300 chars
    res = _truncate_160(long_text)
    assert len(res) <= MAX_ALERT_CHARS
    assert res.endswith("...")

    short_text = "Stay safe on higher ground."
    assert _truncate_160(short_text) == short_text


def test_fallback_alert_bilingual_and_bounded() -> None:
    """Template fallback generates valid English & Hindi advisories under 160 chars."""
    metrics = {"precip_48h_mm": 175.0, "river_discharge_m3s": 4500.0}
    alert = _generate_fallback_alert("Morigaon", "Severe", metrics)

    assert len(alert["message_en"]) <= MAX_ALERT_CHARS
    assert len(alert["message_hi"]) <= MAX_ALERT_CHARS
    assert "Morigaon" in alert["message_en"]
    assert any(ord(c) > 127 for c in alert["message_hi"])  # Contains Devanagari


def test_generate_alert_and_persist_to_database() -> None:
    """generate_alert_for_district creates alert record in SQLite alerts table."""
    metrics = {"precip_48h_mm": 160.0, "river_discharge_m3s": 3800.0}
    res = generate_alert_for_district(
        district_id=1,
        district_name="Morigaon",
        level="Severe",
        metrics=metrics,
        channel="public",
    )

    assert res["id"] > 0
    assert res["level"] == "Severe"
    assert res["char_count_en"] <= MAX_ALERT_CHARS
    assert res["char_count_hi"] <= MAX_ALERT_CHARS

    # Verify presence in database
    db_alerts = list_alerts(district_id=1)
    saved = next((a for a in db_alerts if a["id"] == res["id"]), None)
    assert saved is not None
    assert saved["level"] == "severe"


def test_generate_alerts_for_high_risk_districts() -> None:
    """Scanner detects High and Severe items and creates advisories."""
    risk_data = [
        {"district_name": "Morigaon", "level": "Severe", "precip_48h_mm": 180.0},
        {"district_name": "Dhubri", "level": "High", "precip_48h_mm": 140.0},
        {"district_name": "Lakhimpur", "level": "Low", "precip_48h_mm": 20.0},
    ]
    alerts = generate_alerts_for_high_risk_districts(risk_data)
    assert len(alerts) == 2  # Only Morigaon and Dhubri, not Lakhimpur
    names = {a["district_name"] for a in alerts}
    assert "Morigaon" in names
    assert "Dhubri" in names


def test_plotly_forecast_charts_render() -> None:
    """Plotly chart builders create valid figures with correct layout and traces."""
    times = [f"+{i}h" for i in range(1, 49)]
    precips = [5.0] * 48
    fig_rain = plot_48h_rainfall(times, precips, threshold_mm_per_hr=10.0)

    assert isinstance(fig_rain, go.Figure)
    assert len(fig_rain.data) == 1
    assert "48-Hour Precipitation" in fig_rain.layout.title.text

    dates = ["Day 1", "Day 2", "Day 3"]
    discharges = [2000.0, 3500.0, 4200.0]
    fig_discharge = plot_river_discharge(dates, discharges, danger_threshold_m3s=3000.0)

    assert isinstance(fig_discharge, go.Figure)
    assert len(fig_discharge.data) == 1
    assert "River Discharge" in fig_discharge.layout.title.text
