"""
src/risk/explainer.py
---------------------
Generates plain-language, bilingual explanations of the primary risk drivers.
Used for map popups and coordinator decision support.
"""

from __future__ import annotations

from typing import Any


def explain_risk(factors: dict[str, float], metrics: dict[str, Any], lang: str = "en") -> str:
    """Generate a one-sentence explanation highlighting the dominant flood risk factor."""
    rain_c = factors.get("rain_contrib", 0.0)
    discharge_c = factors.get("discharge_contrib", 0.0)
    elev_c = factors.get("elevation_contrib", 0.0)

    rain_val = metrics.get("precip_48h_mm", 0.0)
    discharge_val = metrics.get("river_discharge_m3s", 0.0)
    elev_val = metrics.get("elevation_m", 30.0)

    # Determine dominant risk contributor
    if discharge_c >= rain_c and discharge_c >= elev_c and discharge_val > 2500:
        if lang == "hi":
            return f"नदी का डिस्चार्ज अत्यधिक ({discharge_val:.0f} m³/s) है और 48 घंटे की बारिश {rain_val:.0f}mm है।"
        return f"River discharge high ({discharge_val:.0f} m³/s) and 48h rain at {rain_val:.0f} mm."
    elif rain_c >= discharge_c and rain_val > 100:
        if lang == "hi":
            return f"अत्यधिक 48 घंटे की बारिश ({rain_val:.0f} mm) के कारण जलभराव का खतरा।"
        return (
            f"Heavy 48h cumulative rainfall ({rain_val:.0f} mm) driving severe surface inundation."
        )
    elif elev_c > 0.08 and elev_val < 25:
        if lang == "hi":
            return f"निचला इलाका ({elev_val:.0f}m) और बढ़ते जलस्तर से जलभराव का गंभीर जोखिम।"
        return f"Low-lying terrain ({elev_val:.0f}m ASL) vulnerable to water accumulation."
    else:
        if lang == "hi":
            return f"सामान्य वर्षा ({rain_val:.0f} mm) और नदी प्रवाह स्तर स्थिर।"
        return f"Moderate precipitation ({rain_val:.0f} mm) with stable river flow."
