"""
src/integrations/gdacs.py
-------------------------
Global Disaster Alert and Coordination System (GDACS) flood feed adapter.
Polls public GDACS flood RSS feed (https://www.gdacs.org/xml/rss_fl.xml),
filters events affecting India, and provides regional disaster context.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import config
from src.integrations.base import BaseAdapter

logger = logging.getLogger(__name__)


class GDACSAdapter(BaseAdapter):
    """Adapter for GDACS RSS feeds with 1-hour cache TTL."""

    def __init__(self, feed_url: str | None = None) -> None:
        """Initialize with 1-hour cache TTL."""
        super().__init__(source_name="gdacs", cache_ttl_seconds=3600)
        self.feed_url = feed_url or config.GDACS_FEED_URL

    def get_india_flood_events(self) -> dict[str, Any]:
        """Fetch and filter GDACS flood events affecting India."""
        resp = self.execute_request(url=self.feed_url, is_xml=True)
        raw_xml = resp.get("data")

        events: list[dict[str, Any]] = []
        if isinstance(raw_xml, str) and raw_xml.strip():
            try:
                import re

                clean_xml = re.sub(r"&(?!(?:amp|lt|gt|quot|apos);)", "&amp;", raw_xml)
                root = ET.fromstring(clean_xml)
                channel = root.find("channel")
                items = channel.findall("item") if channel is not None else root.findall("item")

                for it in items:
                    title = (it.findtext("title") or "").strip()
                    desc = (it.findtext("description") or "").strip()
                    link = (it.findtext("link") or "").strip()
                    pub_date = (it.findtext("pubDate") or "").strip()

                    # Filter for India context
                    combined = f"{title} {desc}".lower()
                    if (
                        "india" in combined
                        or "assam" in combined
                        or "bihar" in combined
                        or "kerala" in combined
                    ):
                        events.append(
                            {
                                "title": title,
                                "description": desc,
                                "link": link,
                                "pubDate": pub_date,
                                "event_type": "FL",
                            }
                        )
            except Exception as exc:
                logger.warning("Failed parsing GDACS XML: %s", exc)

        return {
            "events": events,
            "count": len(events),
            "fetched_at": resp["fetched_at"],
            "source_status": resp["source_status"],
            "latency_ms": resp["latency_ms"],
        }
