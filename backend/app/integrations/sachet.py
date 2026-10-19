"""
src/integrations/sachet.py
--------------------------
SACHET NDMA RSS and CAP (Common Alerting Protocol v1.2) feed integration.
Fetches public emergency alerts, parses CAP XML, filters flood/cyclone/river events,
matches districts, and updates the alerts database table with official advisories.
"""

from __future__ import annotations

import difflib
import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from backend.app.config import get_settings
from src.db.queries import (
    delete_alert_by_identifier,
    list_districts,
    save_or_update_alert,
)

config = get_settings()
logger = logging.getLogger(__name__)

USER_AGENT = "FloodSaathi-EmergencySupport/1.0 (+https://github.com/floodsaathi)"
POLL_INTERVAL_S = 300  # 5 minutes
HTTP_TIMEOUT_S = 10.0
SACHET_FIXTURE_DIR = Path(config.CACHE_DIR) / "sachet"
CACHE_META_FILE = Path(config.CACHE_DIR) / "sachet_meta.json"

SEVERITY_MAP = {
    "extreme": "severe",
    "severe": "severe",
    "moderate": "high",
    "minor": "medium",
    "unknown": "low",
}

RELEVANT_KEYWORDS = {
    "flood",
    "flash flood",
    "inundation",
    "rain",
    "rainfall",
    "river",
    "monsoon",
    "cyclone",
    "waterlogging",
    "dam",
    "barrage",
    "brahmaputra",
    "kopili",
    "ganga",
}


def _strip_ns(tag: str) -> str:
    """Return local XML tag without namespace."""
    return tag.split("}")[-1] if "}" in tag else tag


def _find_text(element: ET.Element, name: str) -> str:
    """Find child element text ignoring XML namespace."""
    for child in element:
        if _strip_ns(child.tag).lower() == name.lower():
            return (child.text or "").strip()
    return ""


def parse_cap_xml(xml_content: str) -> dict[str, Any] | None:
    """Parse a CAP v1.2 XML string into a structured dictionary."""
    try:
        root = ET.fromstring(xml_content)
    except Exception as exc:
        logger.warning("Failed to parse CAP XML: %s", exc)
        return None

    identifier = _find_text(root, "identifier")
    sent = _find_text(root, "sent")
    status = _find_text(root, "status")
    msg_type = _find_text(root, "msgType")

    info_el = None
    for child in root:
        if _strip_ns(child.tag).lower() == "info":
            info_el = child
            break

    if info_el is None:
        return None

    area_el = None
    for child in info_el:
        if _strip_ns(child.tag).lower() == "area":
            area_el = child
            break

    area_desc = _find_text(area_el, "areaDesc") if area_el is not None else ""
    circle = _find_text(area_el, "circle") if area_el is not None else ""
    polygon = _find_text(area_el, "polygon") if area_el is not None else ""

    return {
        "identifier": identifier,
        "sent": sent,
        "status": status,
        "msgType": msg_type,
        "category": _find_text(info_el, "category"),
        "event": _find_text(info_el, "event"),
        "urgency": _find_text(info_el, "urgency"),
        "severity": _find_text(info_el, "severity"),
        "certainty": _find_text(info_el, "certainty"),
        "headline": _find_text(info_el, "headline"),
        "description": _find_text(info_el, "description"),
        "instruction": _find_text(info_el, "instruction"),
        "effective": _find_text(info_el, "effective"),
        "expires": _find_text(info_el, "expires"),
        "areaDesc": area_desc,
        "circle": circle,
        "polygon": polygon,
    }


def is_flood_related(cap_data: dict[str, Any]) -> bool:
    """Check if CAP alert contains flood, rain, cyclone, or river keywords."""
    combined = " ".join(
        [
            cap_data.get("event", ""),
            cap_data.get("headline", ""),
            cap_data.get("description", ""),
        ]
    ).lower()
    return any(keyword in combined for keyword in RELEVANT_KEYWORDS)


def is_alert_expired(expires_str: str) -> bool:
    """Return True if expiration time has passed."""
    if not expires_str:
        return False
    try:
        exp_dt = datetime.fromisoformat(expires_str)
        now_dt = datetime.now(timezone.utc)
        return exp_dt < now_dt
    except Exception:
        return False


def match_district_name(area_desc: str, districts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Match CAP areaDesc to a monitored district using fuzzy substring matching."""
    text_clean = area_desc.lower()
    for d in districts:
        name_lower = d["name"].lower()
        if name_lower in text_clean:
            return d

    # Fallback to closest match
    district_names = [d["name"].lower() for d in districts]
    words = [w.strip(",.- ") for w in text_clean.split()]
    for word in words:
        matches = difflib.get_close_matches(word, district_names, n=1, cutoff=0.75)
        if matches:
            matched_name = matches[0]
            for d in districts:
                if d["name"].lower() == matched_name:
                    return d
    return None


class SachetAdapter:
    """Adapter managing SACHET RSS polling, CAP parsing, and caching."""

    def __init__(self, rss_url: str | None = None) -> None:
        """Initialize adapter with URL, headers, and cache state."""
        self.rss_url = rss_url or config.SACHET_RSS_URL
        self.last_poll_ts = 0.0
        self.etag: str | None = None
        self.last_modified: str | None = None
        self.last_status = "Initialized"

    def fetch_feed_xml(self) -> str | None:
        """Fetch RSS feed with ETag/If-Modified-Since and backoff handling."""
        now = time.time()
        if now - self.last_poll_ts < POLL_INTERVAL_S:
            logger.info("Serving last SACHET poll within 5-min interval.")
            return self._load_fallback_feed()

        self.last_poll_ts = now
        headers = {"User-Agent": USER_AGENT}
        if self.etag:
            headers["If-None-Match"] = self.etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified

        try:
            resp = requests.get(self.rss_url, headers=headers, timeout=HTTP_TIMEOUT_S)
            if resp.status_code == 304:
                self.last_status = "Cached (304 Not Modified)"
                return self._load_fallback_feed()
            if resp.status_code == 200:
                self.etag = resp.headers.get("ETag")
                self.last_modified = resp.headers.get("Last-Modified")
                self.last_status = "Live (200 OK)"
                return resp.text
            self.last_status = f"Failed (HTTP {resp.status_code})"
        except Exception as exc:
            logger.warning("SACHET RSS request failed: %s; using fixture", exc)
            self.last_status = "Failed (Timeout/Offline - Using Cache)"

        return self._load_fallback_feed()

    def _load_fallback_feed(self) -> str:
        """Load local fallback RSS XML fixture."""
        sample_file = SACHET_FIXTURE_DIR / "sample_rss.xml"
        if sample_file.exists():
            return sample_file.read_text(encoding="utf-8")
        return ""

    def load_cap_xml_by_link(self, link: str) -> str:
        """Fetch CAP XML from link or local cached fixture file."""
        if os.path.exists(link) or (Path(link).is_file()):
            return Path(link).read_text(encoding="utf-8")

        clean_link = link.replace("\\", "/").split("/")[-1]
        local_cand = SACHET_FIXTURE_DIR / clean_link
        if local_cand.exists():
            return local_cand.read_text(encoding="utf-8")

        if link.startswith("http"):
            try:
                resp = requests.get(
                    link, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_S
                )
                if resp.status_code == 200:
                    return resp.text
            except Exception as exc:
                logger.warning("Failed fetching linked CAP XML %s: %s", link, exc)

        return ""

    def sync_alerts(self) -> list[dict[str, Any]]:
        """Poll feed, parse all valid CAP alerts, update DB, and return saved alerts."""
        raw_rss = self.fetch_feed_xml()
        if not raw_rss:
            return []

        try:
            root = ET.fromstring(raw_rss)
        except Exception as exc:
            logger.warning("Could not parse RSS XML: %s", exc)
            return []

        districts = list_districts()
        processed_alerts: list[dict[str, Any]] = []

        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall("item")

        for item in items:
            link = (item.findtext("link") or "").strip()
            if not link:
                continue

            cap_text = self.load_cap_xml_by_link(link)
            if not cap_text:
                continue

            cap = parse_cap_xml(cap_text)
            if not cap:
                continue

            # Skip expired alerts and status != Actual
            if cap.get("status") != "Actual":
                continue
            if is_alert_expired(cap.get("expires", "")):
                continue

            # Handle msgType Update & Cancel
            msg_type = cap.get("msgType", "Alert")
            ident = cap.get("identifier", "")
            if msg_type == "Cancel":
                delete_alert_by_identifier(ident)
                continue

            # Filter flood/cyclone/rain events
            if not is_flood_related(cap):
                continue

            matched_d = match_district_name(cap.get("areaDesc", ""), districts)
            d_id = matched_d["id"] if matched_d else None

            severity_raw = (cap.get("severity") or "unknown").lower()
            level = SEVERITY_MAP.get(severity_raw, "medium")

            headline = cap.get("headline") or cap.get("event") or "Official Flood Alert"
            instruction = cap.get("instruction") or "Follow official instructions."
            msg_en = f"{headline}. {instruction}"
            msg_hi = f"[आधिकारिक चेतावनी] {headline}। {instruction}"

            save_or_update_alert(
                district_id=d_id,
                level=level,
                message_en=msg_en,
                message_hi=msg_hi,
                channel="public",
                source="SACHET",
                identifier=ident,
            )

            cap["matched_district"] = matched_d["name"] if matched_d else None
            cap["normalized_level"] = level
            processed_alerts.append(cap)

        return processed_alerts
