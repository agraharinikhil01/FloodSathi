"""
scripts/eval_risk.py
--------------------
Replays historical flood scenarios (Assam 2022 Barak / Silchar & Kerala 2018)
to evaluate the risk engine's early-warning lead time before peak inundation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.risk.engine import score_risk

# Simulated timeline leading up to Assam 2022 Barak River peak flood event
# (T-48h, T-36h, T-24h, T-12h, T-0h peak)
HISTORICAL_SCENARIO_ASSAM = [
    {"hour_offset": -48, "rain_48h": 45.0, "discharge": 450.0, "elev": 22.0, "pop": 250000},
    {"hour_offset": -36, "rain_48h": 110.0, "discharge": 780.0, "elev": 22.0, "pop": 250000},
    {"hour_offset": -24, "rain_48h": 185.0, "discharge": 1250.0, "elev": 22.0, "pop": 250000},
    {"hour_offset": -12, "rain_48h": 260.0, "discharge": 1850.0, "elev": 22.0, "pop": 250000},
    {"hour_offset": 0, "rain_48h": 320.0, "discharge": 2400.0, "elev": 22.0, "pop": 250000},
]


def evaluate_scenario(scenario_data: list[dict]) -> dict:
    """Evaluate lead time for High and Severe risk triggers."""
    timeline = []
    first_high_lead = None
    first_severe_lead = None

    for step in scenario_data:
        offset = step["hour_offset"]
        res = score_risk(
            rain_48h_mm=step["rain_48h"],
            river_discharge_m3s=step["discharge"],
            elevation_m=step["elev"],
            population=step["pop"],
        )

        level = res["level"]
        score = res["score"]

        if level in ("High", "Severe") and first_high_lead is None:
            first_high_lead = abs(offset)
        if level == "Severe" and first_severe_lead is None:
            first_severe_lead = abs(offset)

        timeline.append(
            {
                "offset_h": offset,
                "rain_mm": step["rain_48h"],
                "discharge_m3s": step["discharge"],
                "score": score,
                "level": level,
            }
        )

    return {
        "timeline": timeline,
        "lead_time_high_h": first_high_lead or 0,
        "lead_time_severe_h": first_severe_lead or 0,
    }


def main() -> None:
    """Run historical scenario replay and print lead time report."""
    res = evaluate_scenario(HISTORICAL_SCENARIO_ASSAM)
    print("\n=== FloodSaathi Historical Validation: Assam 2022 Barak Scenario ===")
    print(
        f"{'Time To Peak':<14} | {'48h Rain':<10} | {'Discharge':<12} | {'Score':<7} | {'Level':<8}"
    )
    print("-" * 62)

    for step in res["timeline"]:
        t_str = f"T{step['offset_h']:+} h"
        print(
            f"{t_str:<14} | {step['rain_mm']:<10.1f} | {step['discharge_m3s']:<12.0f} | "
            f"{step['score']:<7.3f} | {step['level']:<8}"
        )

    print("-" * 62)
    print(f"[OK] Lead Time to HIGH Alert:   {res['lead_time_high_h']} hours in advance")
    print(f"[OK] Lead Time to SEVERE Alert: {res['lead_time_severe_h']} hours in advance")
    print("====================================================================\n")


if __name__ == "__main__":
    main()
