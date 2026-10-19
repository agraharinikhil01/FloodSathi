"""
src/risk/engine.py
------------------
Core flood risk calculation engine.
Formula:
    risk = 0.40 * rain_48h + 0.35 * river_discharge + 0.15 * low_elevation + 0.10 * population
All factors are normalised 0 to 1 and mapped to Low, Medium, High, or Severe.
"""

from __future__ import annotations

from typing import Any

from src.risk.explainer import explain_risk

# Constants for normalisation
MAX_RAIN_48H_MM = 200.0
MAX_DISCHARGE_M3S = 6000.0
CRITICAL_ELEVATION_M = 50.0
MAX_POPULATION = 50000.0

WEIGHT_RAIN = 0.40
WEIGHT_DISCHARGE = 0.35
WEIGHT_ELEVATION = 0.15
WEIGHT_POPULATION = 0.10

LEVEL_THRESHOLDS = [
    (0.75, "Severe"),
    (0.50, "High"),
    (0.25, "Medium"),
    (0.00, "Low"),
]


def score_risk(
    rain_48h_mm: float,
    river_discharge_m3s: float,
    elevation_m: float,
    population: float = 15000.0,
    lang: str = "en",
) -> dict[str, Any]:
    """Calculate composite flood risk and factor contributions for a point."""
    # Normalise each factor between 0.0 and 1.0
    norm_rain = max(0.0, min(1.0, rain_48h_mm / MAX_RAIN_48H_MM))
    norm_discharge = max(0.0, min(1.0, river_discharge_m3s / MAX_DISCHARGE_M3S))
    # Lower elevation means higher inundation risk
    norm_elevation = max(0.0, min(1.0, 1.0 - (elevation_m / CRITICAL_ELEVATION_M)))
    norm_pop = max(0.0, min(1.0, population / MAX_POPULATION))

    # Calculate weighted contributions
    rain_contrib = round(WEIGHT_RAIN * norm_rain, 4)
    discharge_contrib = round(WEIGHT_DISCHARGE * norm_discharge, 4)
    elevation_contrib = round(WEIGHT_ELEVATION * norm_elevation, 4)
    population_contrib = round(WEIGHT_POPULATION * norm_pop, 4)

    raw_score = round(rain_contrib + discharge_contrib + elevation_contrib + population_contrib, 4)
    clamped_score = min(1.0, max(0.0, raw_score))

    level = "Low"
    for threshold, lvl in LEVEL_THRESHOLDS:
        if clamped_score >= threshold:
            level = lvl
            break

    factors = {
        "rain_contrib": rain_contrib,
        "discharge_contrib": discharge_contrib,
        "elevation_contrib": elevation_contrib,
        "population_contrib": population_contrib,
        "norm_rain": round(norm_rain, 4),
        "norm_discharge": round(norm_discharge, 4),
        "norm_elevation": round(norm_elevation, 4),
        "norm_population": round(norm_pop, 4),
    }

    metrics = {
        "precip_48h_mm": rain_48h_mm,
        "river_discharge_m3s": river_discharge_m3s,
        "elevation_m": elevation_m,
        "population": population,
    }

    explanation = explain_risk(factors, metrics, lang=lang)

    return {
        "score": clamped_score,
        "level": level,
        "explanation": explanation,
        "factors": factors,
        "metrics": metrics,
    }


def compute_risk_for_points(
    points_data: list[dict[str, Any]], lang: str = "en"
) -> list[dict[str, Any]]:
    """Compute risk score and explanation for an array of evaluated points."""
    evaluated: list[dict[str, Any]] = []
    for pt in points_data:
        r_eval = score_risk(
            rain_48h_mm=float(pt.get("precip_48h_mm", 0.0)),
            river_discharge_m3s=float(pt.get("river_discharge_m3s", 0.0)),
            elevation_m=float(pt.get("elevation_m", 35.0)),
            population=float(pt.get("population", 15000.0)),
            lang=lang,
        )
        res = dict(pt)
        res["score"] = r_eval["score"]
        res["level"] = r_eval["level"]
        res["explanation"] = r_eval["explanation"]
        res["factors"] = r_eval["factors"]
        evaluated.append(res)
    return evaluated
