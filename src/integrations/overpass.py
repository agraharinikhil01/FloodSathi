"""
src/integrations/overpass.py
----------------------------
Overpass OpenStreetMap API adapter for emergency facilities and shelters.
Queries bounding boxes for hospitals, clinics, schools, community centres, and assembly points.
Caches queries for 7 days and populates the SQLite facilities table.
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.queries import list_facilities, save_facility
from src.integrations.base import BaseAdapter

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class OverpassAdapter(BaseAdapter):
    """Adapter for querying OSM facilities via Overpass API with 7-day cache TTL."""

    def __init__(self) -> None:
        """Initialize with 7-day cache TTL."""
        super().__init__(source_name="overpass", cache_ttl_seconds=7 * 86400)

    def _build_query(self, south: float, west: float, north: float, east: float) -> str:
        """Construct Overpass QL query string for target facilities in bounding box."""
        bbox = f"{south:.4f},{west:.4f},{north:.4f},{east:.4f}"
        return f"""
        [out:json][timeout:15];
        (
          node["amenity"="hospital"]({bbox});
          way["amenity"="hospital"]({bbox});
          node["amenity"="clinic"]({bbox});
          way["amenity"="clinic"]({bbox});
          node["amenity"="school"]({bbox});
          way["amenity"="school"]({bbox});
          node["amenity"="community_centre"]({bbox});
          way["amenity"="community_centre"]({bbox});
          node["emergency"="assembly_point"]({bbox});
          way["emergency"="assembly_point"]({bbox});
        );
        out center;
        """.strip()

    def _parse_facility_element(self, element: dict[str, Any]) -> dict[str, Any] | None:
        """Extract facility properties and coordinate centroid from an OSM element."""
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or tags.get("operator")
        if not name:
            name = f"Unnamed {tags.get('amenity', 'Facility').title()}"

        # Resolve coordinates from node lat/lon or way center
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")
        if lat is None or lon is None:
            return None

        amenity = tags.get("amenity")
        emergency = tags.get("emergency")

        if amenity in ("hospital", "clinic"):
            f_type = "hospital"
        elif amenity in ("community_centre", "school") or emergency == "assembly_point":
            f_type = "shelter"
        else:
            f_type = "school"

        return {
            "name": name,
            "type": f_type,
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "osm_id": f"{element.get('type', 'node')}_{element.get('id')}",
            "capacity": 150 if f_type == "hospital" else 300,
        }

    def fetch_facilities_for_bbox(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
        district_id: int | None = None,
    ) -> dict[str, Any]:
        """Fetch and persist emergency facilities in a bounding box."""
        # Reuse existing facilities from DB if available
        existing_db = list_facilities(district_id=district_id)
        if existing_db and len(existing_db) >= 10:
            return {
                "facilities": existing_db,
                "count": len(existing_db),
                "fetched_at": "DB",
                "source_status": "cached",
                "latency_ms": 0.0,
            }

        query_str = self._build_query(south, west, north, east)
        cache_key = f"overpass_bbox_{south:.2f}_{west:.2f}_{north:.2f}_{east:.2f}"

        resp = self.execute_request(
            url=OVERPASS_URL,
            method="POST",
            data={"data": query_str},
            custom_cache_key=cache_key,
        )

        elements = (
            resp.get("data", {}).get("elements", []) if isinstance(resp.get("data"), dict) else []
        )
        saved: list[dict[str, Any]] = []

        for el in elements:
            fac = self._parse_facility_element(el)
            if fac:
                db_id = save_facility(
                    district_id=district_id,
                    name=fac["name"],
                    facility_type=fac["type"],
                    lat=fac["lat"],
                    lon=fac["lon"],
                    capacity=fac["capacity"],
                    osm_id=fac["osm_id"],
                    source="overpass",
                )
                fac["id"] = db_id
                saved.append(fac)

        return {
            "facilities": saved,
            "count": len(saved),
            "fetched_at": resp["fetched_at"],
            "source_status": resp["source_status"],
            "latency_ms": resp["latency_ms"],
        }
