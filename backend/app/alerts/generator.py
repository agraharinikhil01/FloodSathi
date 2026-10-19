"""
src/alerts/generator.py
-----------------------
Emergency alert generator for High and Severe risk areas.
Calls Claude Haiku to synthesize concise bilingual advisories (Hindi & English, max 160 chars)
with actionable evacuation or safety instructions.
Includes deterministic fallback templates when LLM keys or network are unavailable.
Saves generated advisories into the SQLite alerts table.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import config
from src.db.queries import get_district_by_name, list_districts, save_or_update_alert

logger = logging.getLogger(__name__)

MAX_ALERT_CHARS = 160


def _truncate_160(text: str) -> str:
    """Ensure message strictly satisfies the 160-character SMS/broadcast limit."""
    clean = " ".join(text.strip().split())
    if len(clean) <= MAX_ALERT_CHARS:
        return clean
    return clean[: MAX_ALERT_CHARS - 3] + "..."


def _generate_fallback_alert(
    district_name: str, level: str, metrics: dict[str, Any]
) -> dict[str, str]:
    """Deterministic, template-based bilingual alert generation adhering to 160 chars."""
    rain = metrics.get("precip_48h_mm", 0.0)
    discharge = metrics.get("river_discharge_m3s", 0.0)
    lvl_upper = level.upper()

    if lvl_upper == "SEVERE":
        msg_en = f"EMERGENCY: {district_name} flood severe ({rain:.0f}mm rain, {discharge:.0f}m3/s flow). Evacuate to higher ground/shelter immediately. Dial 1077."
        msg_hi = f"आपातकालीन: {district_name} में गंभीर बाढ़ ({rain:.0f}mm बारिश)। तुरंत ऊंचे स्थान या राहत शिविर जाएं। हेल्पलाइन 1077।"
    else:  # High
        msg_en = f"ALERT: High flood risk in {district_name} ({rain:.0f}mm rain). Stay away from rivers and waterlogged roads. Keep essentials ready."
        msg_hi = f"चेतावनी: {district_name} में बाढ़ का उच्च जोखिम ({rain:.0f}mm बारिश)। नदियों और जलभराव से दूर रहें। जरूरी सामान तैयार रखें।"

    return {
        "message_en": _truncate_160(msg_en),
        "message_hi": _truncate_160(msg_hi),
        "generator": "template_fallback",
    }


def _call_claude_for_alert(
    district_name: str, level: str, metrics: dict[str, Any], api_key: str
) -> dict[str, str] | None:
    """Call Claude Haiku API to generate concise bilingual emergency alert text."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, timeout=config.CLAUDE_TIMEOUT)
        prompt = f"""
You are an emergency disaster response coordinator in India.
Write a concise emergency public alert for {district_name} district under {level.upper()} flood risk.
48-hour rainfall: {metrics.get('precip_48h_mm', 0):.0f} mm.
River discharge: {metrics.get('river_discharge_m3s', 0):.0f} m3/s.

CRITICAL RULES:
1. Provide one message in English and one message in Hindi.
2. Each message MUST be under 160 characters (strict SMS limit).
3. Include an immediate actionable instruction (evacuate, shelter, avoid riverbanks).
4. Output STRICT JSON only: {{"message_en": "...", "message_hi": "..."}}
""".strip()

        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=256,
            system="You output valid JSON only. Never include preamble or markdown wrappers.",
            messages=[{"role": "user", "content": prompt}],
        )

        content = resp.content[0].text.strip()
        if content.startswith("```"):
            content = content.strip("`").replace("json\n", "", 1).strip()

        parsed = json.loads(content)
        msg_en = _truncate_160(str(parsed.get("message_en", "")))
        msg_hi = _truncate_160(str(parsed.get("message_hi", "")))

        if msg_en and msg_hi:
            return {
                "message_en": msg_en,
                "message_hi": msg_hi,
                "generator": "claude",
            }
    except Exception as exc:
        logger.warning("Claude alert generation failed: %s; falling back to template", exc)

    return None


def generate_alert_for_district(
    district_id: int | None,
    district_name: str,
    level: str,
    metrics: dict[str, Any],
    channel: str = "public",
) -> dict[str, Any]:
    """Generate and persist bilingual emergency advisory for a district."""
    api_key = config.get_anthropic_api_key_safe()
    alert_content = None

    if api_key:
        alert_content = _call_claude_for_alert(district_name, level, metrics, api_key)

    if not alert_content:
        alert_content = _generate_fallback_alert(district_name, level, metrics)

    msg_en = alert_content["message_en"]
    msg_hi = alert_content["message_hi"]
    now_iso = datetime.now(timezone.utc).isoformat()
    identifier = f"LLM-ALERT-{district_name.upper()}-{int(datetime.now().timestamp())}"

    # Persist in SQLite alerts table
    saved_id = save_or_update_alert(
        district_id=district_id,
        level=level.lower(),
        message_en=msg_en,
        message_hi=msg_hi,
        channel=channel,
        source="LLM",
        identifier=identifier,
    )

    return {
        "id": saved_id,
        "district_id": district_id,
        "district_name": district_name,
        "level": level.capitalize(),
        "message_en": msg_en,
        "message_hi": msg_hi,
        "char_count_en": len(msg_en),
        "char_count_hi": len(msg_hi),
        "generator": alert_content.get("generator", "template_fallback"),
        "created_at": now_iso,
        "channel": channel,
    }


def generate_alerts_for_high_risk_districts(
    risk_results: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Scan districts and generate advisories for any High or Severe areas."""
    generated: list[dict[str, Any]] = []

    if not risk_results:
        # Default scan from all districts
        districts = list_districts()
        for d in districts:
            # Generate sample High/Severe alert for top flood districts
            if d["name"] in ("Morigaon", "Dhubri", "Darbhanga"):
                al = generate_alert_for_district(
                    district_id=d["id"],
                    district_name=d["name"],
                    level="Severe" if d["name"] == "Morigaon" else "High",
                    metrics={"precip_48h_mm": 165.0, "river_discharge_m3s": 4200.0},
                )
                generated.append(al)
        return generated

    for r in risk_results:
        lvl = r.get("level", "Low")
        if lvl.lower() in ("high", "severe"):
            d_name = r.get("district_name") or config.DEFAULT_DISTRICT
            d_info = get_district_by_name(d_name)
            d_id = d_info["id"] if d_info else None
            metrics = {
                "precip_48h_mm": r.get("precip_48h_mm", 120.0),
                "river_discharge_m3s": r.get("river_discharge_m3s", 3500.0),
            }
            al = generate_alert_for_district(
                district_id=d_id,
                district_name=d_name,
                level=lvl,
                metrics=metrics,
            )
            generated.append(al)

    return generated
