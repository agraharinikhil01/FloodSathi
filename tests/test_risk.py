"""
tests/test_risk.py
------------------
Unit tests for the FloodSaathi risk engine and factor scoring.
"""

from __future__ import annotations

from src.risk.engine import score_risk


def test_zero_conditions_produce_low_risk() -> None:
    """Zero rain and baseline discharge at high elevation should be Low risk."""
    res = score_risk(
        rain_48h_mm=0.0,
        river_discharge_m3s=0.0,
        elevation_m=100.0,  # Above critical elevation
        population=0.0,
    )
    assert res["level"] == "Low"
    assert res["score"] == 0.0
    assert res["factors"]["rain_contrib"] == 0.0
    assert res["factors"]["discharge_contrib"] == 0.0


def test_extreme_conditions_produce_severe_risk() -> None:
    """Maximum rain and discharge at sea level should produce Severe risk."""
    res = score_risk(
        rain_48h_mm=250.0,  # Exceeds max 200 mm
        river_discharge_m3s=7000.0,  # Exceeds max 6000 m3/s
        elevation_m=0.0,  # Sea level
        population=60000.0,  # High population
    )
    assert res["level"] == "Severe"
    assert res["score"] >= 0.75
    assert "River discharge" in res["explanation"] or "rainfall" in res["explanation"]


def test_heavy_rain_dominates_score() -> None:
    """Heavy rain with moderate river flow triggers High or Severe level."""
    res = score_risk(
        rain_48h_mm=195.0,
        river_discharge_m3s=1800.0,
        elevation_m=35.0,
        population=15000.0,
    )
    assert res["level"] in ("High", "Severe")
    assert res["factors"]["rain_contrib"] > res["factors"]["discharge_contrib"]


def test_elevation_effect_on_risk() -> None:
    """Identical rain & discharge at sea-level vs high altitude gives higher score to sea-level."""
    low_land = score_risk(rain_48h_mm=80.0, river_discharge_m3s=2000.0, elevation_m=5.0)
    high_land = score_risk(rain_48h_mm=80.0, river_discharge_m3s=2000.0, elevation_m=80.0)

    assert low_land["score"] > high_land["score"]
    assert low_land["factors"]["elevation_contrib"] > high_land["factors"]["elevation_contrib"]


def test_bilingual_explanation_generation() -> None:
    """Explanation generates valid non-empty text in both Hindi and English."""
    res_en = score_risk(rain_48h_mm=160.0, river_discharge_m3s=4000.0, elevation_m=10.0, lang="en")
    res_hi = score_risk(rain_48h_mm=160.0, river_discharge_m3s=4000.0, elevation_m=10.0, lang="hi")

    assert len(res_en["explanation"]) > 10
    assert len(res_hi["explanation"]) > 10
    assert any(ord(c) > 127 for c in res_hi["explanation"])  # Contains Devanagari characters


def test_score_stays_bounded() -> None:
    """Scores never exceed 1.0 or fall below 0.0 regardless of inputs."""
    res_huge = score_risk(rain_48h_mm=9999.0, river_discharge_m3s=99999.0, elevation_m=-50.0)
    res_neg = score_risk(rain_48h_mm=-50.0, river_discharge_m3s=-100.0, elevation_m=500.0)

    assert 0.0 <= res_huge["score"] <= 1.0
    assert 0.0 <= res_neg["score"] <= 1.0
