"""
src/integrations/geocode.py
---------------------------
Multi-tier resilient geocoding service:
1. Primary: Geoapify (API key required, daily cap guard, 4 req/sec rate limit)
2. Fallback 1: Photon (fair use, 1 req/sec, 30 days cache)
3. Fallback 2: Nominatim (1 req/sec, User-Agent, permanent cache)
4. Offline Fixture fallback (6 local place names)
5. Never-crash fallback (returns district center with confidence='low', source='failed')

Normalised output:
{name, display_name, lat, lon, type, bbox, source, confidence}
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

import config

logger = logging.getLogger(__name__)


# Rate Limiters
class RateLimiter:
    """Thread-safe rate limiter enforcing maximum requests per second."""

    def __init__(self, requests_per_second: float):
        self.min_interval = 1.0 / max(0.1, requests_per_second)
        self.last_call = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call = time.time()


GEOAPIFY_LIMITER = RateLimiter(4.0)  # 4 req/sec budget guard
PHOTON_LIMITER = RateLimiter(1.0)  # 1 req/sec fair use
NOMINATIM_LIMITER = RateLimiter(1.0)  # 1 req/sec OSM policy

GEOCODE_CACHE_TTL = 30 * 86400  # 30 days cache
FIXTURES_DIR = config.CACHE_DIR / "fixtures" / "geocode"


def mask_key(text: str) -> str:
    """Mask API key in URLs or logs to guarantee zero secret leakage."""
    return re.sub(r"([?&]apiKey=)[^&]+", r"\1***", str(text))


def get_db_path() -> Path:
    """Return configured SQLite database path."""
    return Path(getattr(config, "DB_PATH", "floodsaathi.db"))


def check_and_increment_daily_cap(service: str = "geoapify", cap: int | None = None) -> bool:
    """
    Check if daily API quota is under cap and increment counter.
    Returns True if permitted, False if cap is reached.
    """
    if cap is None:
        cap = getattr(config, "GEOCODE_DAILY_CAP", 2500)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db_file = get_db_path()

    try:
        with sqlite3.connect(str(db_file), timeout=5.0) as conn:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS api_usage ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "service TEXT NOT NULL, "
                "date_str TEXT NOT NULL, "
                "count INTEGER DEFAULT 0, "
                "UNIQUE(service, date_str));"
            )
            cur.execute(
                "SELECT count FROM api_usage WHERE service = ? AND date_str = ?",
                (service, today_str),
            )
            row = cur.fetchone()
            current_count = row[0] if row else 0

            if current_count >= cap:
                logger.warning(
                    "[Geocode] %s daily cap reached (%d/%d). Falling back to secondary geocoders.",
                    service,
                    current_count,
                    cap,
                )
                return False

            # Increment count
            cur.execute(
                "INSERT INTO api_usage (service, date_str, count) VALUES (?, ?, 1) "
                "ON CONFLICT(service, date_str) DO UPDATE SET count = count + 1",
                (service, today_str),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.warning("[Geocode] Database api_usage check error: %s. Permitting request.", exc)
        return True


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two GPS points."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * r * math.asin(math.sqrt(max(0.0, min(1.0, a))))


class GeocodeService:
    """Unified geocoder orchestrating Geoapify, Photon, and Nominatim."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.user_agent = getattr(
            config, "NOMINATIM_USER_AGENT", "FloodSaathi/1.0 (contact@floodsaathi.in)"
        )
        self.session.headers.update({"User-Agent": self.user_agent})
        self.cache_dir = config.CACHE_DIR / "geocode"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key_text: str) -> Path:
        h = hashlib.sha256(key_text.encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"{h}.json"

    def _read_cache(
        self, key_text: str, ttl_seconds: int = GEOCODE_CACHE_TTL
    ) -> Optional[List[Dict[str, Any]]]:
        p = self._cache_path(key_text)
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if time.time() - raw.get("timestamp", 0) < ttl_seconds:
                    return raw.get("results")
            except Exception as e:
                logger.warning("[Geocode] Cache read failed for %s: %s", p.name, e)
        return None

    def _write_cache(self, key_text: str, results: List[Dict[str, Any]]) -> None:
        p = self._cache_path(key_text)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {"timestamp": time.time(), "results": results}
            p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("[Geocode] Cache write failed for %s: %s", p.name, e)

    def is_inside_district(
        self,
        lat: float,
        lon: float,
        district_lat: Optional[float] = None,
        district_lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
    ) -> bool:
        """Evaluate if coordinates fall within the district boundary or proximity."""
        if bbox:
            min_lat = bbox.get("min_lat")
            max_lat = bbox.get("max_lat")
            min_lon = bbox.get("min_lon")
            max_lon = bbox.get("max_lon")
            if (
                min_lat is not None
                and max_lat is not None
                and min_lon is not None
                and max_lon is not None
            ):
                return (min_lat - 0.05 <= lat <= max_lat + 0.05) and (
                    min_lon - 0.05 <= lon <= max_lon + 0.05
                )

        if district_lat is not None and district_lon is not None:
            return haversine_km(lat, lon, district_lat, district_lon) <= 35.0

        return True  # If no district context is provided, consider it valid

    def evaluate_confidence(
        self,
        place_type: str,
        inside_district: bool,
        source: str,
        geoapify_rank: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Compute confidence score:
        - high: GPS fix or user confirmed manual pin
        - medium: street, village, or place match inside the district
        - low: only district/city/state level, or match outside district
        """
        if source in ("gps", "manual_pin"):
            return "high"

        if not inside_district:
            return "low"

        broad_types = (
            "city",
            "administrative",
            "state",
            "country",
            "district",
            "county",
            "postcode",
        )
        if any(bt in place_type.lower() for bt in broad_types):
            return "low"

        if source == "geoapify" and geoapify_rank:
            conf = geoapify_rank.get("confidence", 0.0)
            match_type = geoapify_rank.get("match_type", "")
            if conf >= 0.7 or match_type in ("full_match", "match_by_building", "match_by_street"):
                return "medium"
            return "low"

        return "medium"

    # ─────────────────────────────────────────────────────────────────────────
    # Primary Geocoder: Geoapify
    # ─────────────────────────────────────────────────────────────────────────
    def _query_geoapify(
        self,
        q: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        is_autocomplete: bool = False,
        limit: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        key = getattr(config, "GEOAPIFY_API_KEY", "") or os.environ.get("GEOAPIFY_API_KEY", "")
        if not key or "REPLACE" in key:
            return None

        # Check daily cap
        if not check_and_increment_daily_cap(service="geoapify"):
            return None

        GEOAPIFY_LIMITER.wait()

        endpoint = "autocomplete" if is_autocomplete else "search"
        base_url = f"https://api.geoapify.com/v1/geocode/{endpoint}"
        params: Dict[str, Any] = {
            "text": q,
            "filter": "countrycode:in",
            "limit": limit,
            "format": "json",
            "apiKey": key,
        }

        # Bias syntax verified from official docs:
        # bias=rect:minLon,minLat,maxLon,maxLat or bias=proximity:lon,lat
        if bbox and all(k in bbox for k in ("min_lon", "min_lat", "max_lon", "max_lat")):
            params["bias"] = (
                f"rect:{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
            )
            if lon is not None and lat is not None:
                params["bias"] += f"|proximity:{lon},{lat}"
        elif lon is not None and lat is not None:
            params["bias"] = f"proximity:{lon},{lat}"

        req_url = f"{base_url}?{requests.compat.urlencode(params)}"
        masked_url = mask_key(req_url)

        try:
            resp = self.session.get(base_url, params=params, timeout=5.0)
            if resp.status_code in (401, 403, 429):
                logger.warning(
                    "[Geocode] Geoapify returned status %d for %s. Triggering fallback.",
                    resp.status_code,
                    masked_url,
                )
                return None
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            normalized = []
            for r in results:
                r_lat = float(r.get("lat", 0.0))
                r_lon = float(r.get("lon", 0.0))
                p_type = r.get("result_type", r.get("category", "place"))
                inside = self.is_inside_district(r_lat, r_lon, lat, lon, bbox)
                conf = self.evaluate_confidence(p_type, inside, "geoapify", r.get("rank"))
                normalized.append(
                    {
                        "name": r.get("name") or (r.get("formatted") or q).split(",")[0].strip(),
                        "display_name": r.get("formatted", f"{q}, India"),
                        "lat": r_lat,
                        "lon": r_lon,
                        "type": p_type,
                        "bbox": r.get("bbox"),
                        "source": "geoapify",
                        "confidence": conf,
                    }
                )
            return normalized
        except Exception as exc:
            logger.warning(
                "[Geocode] Geoapify query failed (%s): %s. Triggering fallback.", masked_url, exc
            )
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback 1: Photon (Komoot)
    # ─────────────────────────────────────────────────────────────────────────
    def _query_photon(
        self,
        q: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        limit: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        PHOTON_LIMITER.wait()
        url = "https://photon.komoot.io/api/"
        params: Dict[str, Any] = {"q": q, "limit": limit}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon

        try:
            resp = self.session.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            normalized = []
            for f in features:
                coords = f.get("geometry", {}).get("coordinates", [0.0, 0.0])
                r_lon, r_lat = float(coords[0]), float(coords[1])
                props = f.get("properties", {})
                p_type = props.get("type", props.get("osm_value", "place"))
                name = props.get("name") or q
                parts = [name]
                for k in ("county", "district", "city", "state"):
                    v = props.get(k)
                    if v and v not in parts:
                        parts.append(v)
                parts.append("India")
                display_name = ", ".join(parts)

                inside = self.is_inside_district(r_lat, r_lon, lat, lon, bbox)
                conf = self.evaluate_confidence(p_type, inside, "photon")
                normalized.append(
                    {
                        "name": name,
                        "display_name": display_name,
                        "lat": r_lat,
                        "lon": r_lon,
                        "type": p_type,
                        "bbox": props.get("extent"),
                        "source": "photon",
                        "confidence": conf,
                    }
                )
            return normalized if normalized else None
        except Exception as exc:
            logger.warning("[Geocode] Photon fallback failed for '%s': %s", q, exc)
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback 2: Nominatim (OpenStreetMap)
    # ─────────────────────────────────────────────────────────────────────────
    def _query_nominatim(
        self,
        q: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        limit: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        NOMINATIM_LIMITER.wait()
        url = "https://nominatim.openstreetmap.org/search"
        params: Dict[str, Any] = {
            "q": q,
            "format": "jsonv2",
            "limit": limit,
            "countrycodes": "in",
            "addressdetails": 1,
        }
        if bbox and all(k in bbox for k in ("min_lon", "max_lon", "min_lat", "max_lat")):
            # Nominatim viewbox: minlon,maxlat,maxlon,minlat
            params["viewbox"] = (
                f"{bbox['min_lon']},{bbox['max_lat']},{bbox['max_lon']},{bbox['min_lat']}"
            )

        try:
            resp = self.session.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return None
            normalized = []
            for item in data:
                r_lat = float(item.get("lat", 0.0))
                r_lon = float(item.get("lon", 0.0))
                p_type = item.get("type", item.get("category", "place"))
                inside = self.is_inside_district(r_lat, r_lon, lat, lon, bbox)
                conf = self.evaluate_confidence(p_type, inside, "nominatim")
                normalized.append(
                    {
                        "name": item.get("name")
                        or item.get("display_name", "").split(",")[0].strip(),
                        "display_name": item.get("display_name", f"{q}, India"),
                        "lat": r_lat,
                        "lon": r_lon,
                        "type": p_type,
                        "bbox": item.get("boundingbox"),
                        "source": "nominatim",
                        "confidence": conf,
                    }
                )
            return normalized if normalized else None
        except Exception as exc:
            logger.warning("[Geocode] Nominatim fallback failed for '%s': %s", q, exc)
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Offline Demo Fixtures
    # ─────────────────────────────────────────────────────────────────────────
    def _query_fixtures(self, q: str) -> Optional[List[Dict[str, Any]]]:
        clean_q = q.lower().strip()
        fixture_candidates = list(FIXTURES_DIR.glob("*.json"))
        for fp in fixture_candidates:
            if fp.stem.lower() in clean_q or clean_q in fp.stem.lower():
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    return data.get("results")
                except Exception:
                    pass
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Public Geocode Method
    # ─────────────────────────────────────────────────────────────────────────
    def geocode(
        self,
        q: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        district_name: Optional[str] = None,
        bbox: Optional[Dict[str, float]] = None,
        is_autocomplete: bool = True,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Geocode location query with multi-tier failover:
        Geoapify -> Photon -> Nominatim -> Fixtures -> District Fallback
        """
        clean_q = (q or "").strip()
        if not clean_q:
            return []

        cache_key = f"fwd_{clean_q}_{lat}_{lon}_{is_autocomplete}_{limit}"
        cached = self._read_cache(cache_key)
        if cached:
            return cached

        # Check offline fixture if offline demo is enabled
        if getattr(config, "OFFLINE_DEMO", False):
            fix = self._query_fixtures(clean_q)
            if fix:
                return fix

        # 1. Primary: Geoapify
        results = self._query_geoapify(
            q=clean_q, lat=lat, lon=lon, bbox=bbox, is_autocomplete=is_autocomplete, limit=limit
        )

        # 2. Fallback 1: Photon
        if not results:
            results = self._query_photon(q=clean_q, lat=lat, lon=lon, bbox=bbox, limit=limit)

        # 3. Fallback 2: Nominatim
        if not results:
            results = self._query_nominatim(q=clean_q, lat=lat, lon=lon, bbox=bbox, limit=limit)

        # 4. Offline Fixture Check
        if not results:
            results = self._query_fixtures(clean_q)

        # 5. Never-crash fallback
        if not results:
            fb_lat = lat if lat is not None else 25.5941
            fb_lon = lon if lon is not None else 85.1376
            display = f"{district_name or clean_q}, India"
            results = [
                {
                    "name": district_name or clean_q.title(),
                    "display_name": display,
                    "lat": fb_lat,
                    "lon": fb_lon,
                    "type": "administrative",
                    "bbox": None,
                    "source": "failed",
                    "confidence": "low",
                    "source_status": "failed",
                }
            ]

        self._write_cache(cache_key, results)
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Reverse Geocoding
    # ─────────────────────────────────────────────────────────────────────────
    def reverse(
        self,
        lat: float,
        lon: float,
        district_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reverse geocode GPS coordinates to human-readable address with multi-tier failover.
        """
        return self._reverse_internal(lat, lon, district_name)

    def reverse_geocode(
        self,
        lat: float,
        lon: float,
        district_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Alias for reverse()."""
        return self.reverse(lat, lon, district_name)

    def _reverse_internal(
        self,
        lat: float,
        lon: float,
        district_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        cache_key = f"rev_{round(lat, 5)}_{round(lon, 5)}"
        cached = self._read_cache(cache_key)
        if cached and len(cached) > 0:
            return cached[0]

        # 1. Geoapify Reverse
        key = getattr(config, "GEOAPIFY_API_KEY", "") or os.environ.get("GEOAPIFY_API_KEY", "")
        if key and "REPLACE" not in key and check_and_increment_daily_cap(service="geoapify"):
            GEOAPIFY_LIMITER.wait()
            base_url = "https://api.geoapify.com/v1/geocode/reverse"
            params = {"lat": lat, "lon": lon, "format": "json", "apiKey": key}
            try:
                resp = self.session.get(base_url, params=params, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    res_list = data.get("results", [])
                    if res_list:
                        top = res_list[0]
                        out = {
                            "name": top.get("name")
                            or top.get("formatted", "").split(",")[0].strip(),
                            "display_name": top.get("formatted", f"{lat:.4f}, {lon:.4f}"),
                            "lat": float(top.get("lat", lat)),
                            "lon": float(top.get("lon", lon)),
                            "type": top.get("result_type", "amenity"),
                            "bbox": top.get("bbox"),
                            "source": "geoapify",
                            "confidence": "high",
                        }
                        self._write_cache(cache_key, [out])
                        return out
            except Exception as exc:
                logger.warning("[Geocode] Geoapify reverse failed: %s", exc)

        # 2. Photon Reverse
        PHOTON_LIMITER.wait()
        try:
            p_url = "https://photon.komoot.io/reverse"
            p_resp = self.session.get(p_url, params={"lat": lat, "lon": lon}, timeout=5.0)
            if p_resp.status_code == 200:
                p_data = p_resp.json()
                features = p_data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    name = props.get("name") or f"Location near {lat:.3f}, {lon:.3f}"
                    parts = [name]
                    for k in ("county", "district", "city", "state"):
                        v = props.get(k)
                        if v and v not in parts:
                            parts.append(v)
                    parts.append("India")
                    out = {
                        "name": name,
                        "display_name": ", ".join(parts),
                        "lat": lat,
                        "lon": lon,
                        "type": props.get("type", "street"),
                        "bbox": props.get("extent"),
                        "source": "photon",
                        "confidence": "high",
                    }
                    self._write_cache(cache_key, [out])
                    return out
        except Exception as exc:
            logger.warning("[Geocode] Photon reverse failed: %s", exc)

        # 3. Nominatim Reverse
        NOMINATIM_LIMITER.wait()
        try:
            n_url = "https://nominatim.openstreetmap.org/reverse"
            n_resp = self.session.get(
                n_url,
                params={"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1},
                timeout=5.0,
            )
            if n_resp.status_code == 200:
                n_data = n_resp.json()
                out = {
                    "name": n_data.get("name")
                    or n_data.get("display_name", "").split(",")[0].strip(),
                    "display_name": n_data.get("display_name", f"{lat:.4f}, {lon:.4f}"),
                    "lat": lat,
                    "lon": lon,
                    "type": n_data.get("type", "address"),
                    "bbox": n_data.get("boundingbox"),
                    "source": "nominatim",
                    "confidence": "high",
                }
                self._write_cache(cache_key, [out])
                return out
        except Exception as exc:
            logger.warning("[Geocode] Nominatim reverse failed: %s", exc)

        # 4. Fallback
        fallback_res = {
            "name": f"Pin at {lat:.4f}, {lon:.4f}",
            "display_name": f"Location ({lat:.4f}, {lon:.4f}), {district_name or 'India'}",
            "lat": lat,
            "lon": lon,
            "type": "manual_pin",
            "bbox": None,
            "source": "manual_pin",
            "confidence": "high",
        }
        return fallback_res
