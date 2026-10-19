"""Alerts Service generating bilingual advisories, official alert synchronization, and mock broadcast dispatch."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.integrations.sachet import SachetAdapter
from backend.app.models.schema import Alert, District, utcnow_str

logger = logging.getLogger(__name__)
settings = get_settings()
sachet_adapter = SachetAdapter()

MAX_ALERT_CHARS = 160


def _truncate_160(text: str) -> str:
    """Ensure message strictly satisfies the 160-character broadcast limit."""
    clean = " ".join(text.strip().split())
    if len(clean) <= MAX_ALERT_CHARS:
        return clean
    return clean[: MAX_ALERT_CHARS - 3] + "..."


def _generate_template_alert(
    district_name: str, level: str, rain_mm: float = 65.0
) -> Dict[str, str]:
    """Deterministic, bilingual emergency alert text under 160 chars."""
    lvl_upper = level.upper()
    if lvl_upper == "SEVERE":
        msg_en = f"EMERGENCY: {district_name} flood severe ({rain_mm:.0f}mm rain). Evacuate to higher ground/shelter immediately. Helpline: 1077."
        msg_hi = f"आपातकालीन: {district_name} में गंभीर बाढ़ ({rain_mm:.0f}mm बारिश)। तुरंत सुरक्षित आश्रय स्थल जाएं। हेल्पलाइन 1077।"
    elif lvl_upper == "HIGH":
        msg_en = f"ALERT: High flood risk in {district_name} ({rain_mm:.0f}mm rain). Stay away from rivers and waterlogged roads. Keep essentials ready."
        msg_hi = f"चेतावनी: {district_name} में बाढ़ का उच्च जोखिम ({rain_mm:.0f}mm बारिश)। नदियों से दूर रहें। जरूरी सामान तैयार रखें।"
    else:
        msg_en = f"ADVISORY: Moderate rain expected in {district_name} ({rain_mm:.0f}mm). Follow official district updates."
        msg_hi = f"सलाह: {district_name} में सामान्य बारिश का अनुमान ({rain_mm:.0f}mm)। आधिकारिक सूचनाओं पर नजर रखें।"

    return {
        "message_en": _truncate_160(msg_en),
        "message_hi": _truncate_160(msg_hi),
        "source": "internal",
    }


class AlertService:
    """Service for querying, synthesizing, and broadcasting emergency flood alerts."""

    @staticmethod
    def list_alerts(
        db: Session, district_name: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List current official and generated alerts."""
        query = db.query(Alert)
        if district_name:
            dist = db.query(District).filter(District.name.ilike(district_name)).first()
            if dist:
                query = query.filter(Alert.district_id == dist.id)

        alerts = query.order_by(Alert.sent_at.desc()).limit(limit).all()

        results = []
        for a in alerts:
            results.append(
                {
                    "id": a.id,
                    "district": a.district.name if a.district else "All Districts",
                    "level": a.level,
                    "message_en": a.message_en,
                    "message_hi": a.message_hi,
                    "channel": a.channel,
                    "source": a.source or "internal",
                    "identifier": a.identifier or f"ALERT-{a.id}",
                    "sent_at": a.sent_at,
                }
            )
        return results

    @classmethod
    def generate_alert(
        cls, db: Session, district_name: str, level: str, channel: str = "all"
    ) -> Dict[str, Any]:
        """Generate a new bilingual alert for a district and save to alerts table."""
        dist = db.query(District).filter(District.name.ilike(district_name)).first()
        if not dist:
            dist = db.query(District).first()

        d_name = dist.name if dist else district_name

        # LLM or Template Generation
        api_key = settings.ANTHROPIC_API_KEY.strip()
        texts = None

        if api_key and "REPLACE" not in api_key and not settings.OFFLINE_DEMO:
            try:
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                prompt = (
                    f"Create an emergency flood broadcast for {d_name} (Level: {level.upper()}). "
                    f'Return JSON only: {{"message_en": "<max 150 chars in English>", "message_hi": "<max 150 chars in Hindi>"}}'
                )
                payload = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": prompt}],
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    import json as pyjson
                    import re

                    raw = resp.json()["content"][0]["text"]
                    match = re.search(r"(\{.*\})", raw, re.DOTALL)
                    if match:
                        parsed = pyjson.loads(match.group(1))
                        texts = {
                            "message_en": _truncate_160(parsed.get("message_en", "")),
                            "message_hi": _truncate_160(parsed.get("message_hi", "")),
                            "source": "claude",
                        }
            except Exception as exc:
                logger.warning("Claude alert gen fallback: %s", exc)

        if not texts:
            texts = _generate_template_alert(d_name, level)

        new_alert = Alert(
            district_id=dist.id if dist else None,
            level=level.lower(),
            message_en=texts["message_en"],
            message_hi=texts["message_hi"],
            channel=channel,
            source=texts.get("source", "internal"),
            identifier=f"ALERT-{d_name.upper()}-{int(datetime.now(timezone.utc).timestamp())}",
            sent_at=utcnow_str(),
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)

        return {
            "id": new_alert.id,
            "district": d_name,
            "level": new_alert.level,
            "message_en": new_alert.message_en,
            "message_hi": new_alert.message_hi,
            "channel": new_alert.channel,
            "source": new_alert.source,
            "identifier": new_alert.identifier,
            "sent_at": new_alert.sent_at,
        }

    @staticmethod
    def mock_broadcast(alert_id: int, channel: str = "all") -> Dict[str, Any]:
        """Simulate broadcasting alert via SMS gateway or siren network."""
        return {
            "status": "success",
            "mock": True,
            "alert_id": alert_id,
            "channel": channel,
            "dispatched_count": 1420,
            "delivery_rate": "99.2%",
            "timestamp": utcnow_str(),
            "message": "Mock broadcast simulated successfully. No real SMS sent.",
        }
