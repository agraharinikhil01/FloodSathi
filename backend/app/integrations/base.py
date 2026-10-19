"""
src/integrations/base.py
------------------------
Common base adapter for no-key data integrations.
Enforces requests.Session, 10s timeout, exponential backoff retries,
disk caching with TTL, last-good fallback, fixture fallbacks, and standard returns.
Never crashes the UI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from backend.app.config import get_settings

config = get_settings()

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 10.0
DEFAULT_RETRIES = 2
CACHE_BASE_PATH = Path(config.CACHE_DIR)
FIXTURES_BASE_DIR = CACHE_BASE_PATH / "fixtures"


class BaseAdapter:
    """Base class for robust, resilient, no-key HTTP integrations."""

    def __init__(self, source_name: str, cache_ttl_seconds: int = 3600) -> None:
        """Initialize adapter with source name, cache directory, and session."""
        self.source_name = source_name
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_dir = CACHE_BASE_PATH / source_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fixture_dir = FIXTURES_BASE_DIR / source_name
        self.fixture_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.user_agent = config.NOMINATIM_USER_AGENT
        self.session.headers.update({"User-Agent": self.user_agent})

    def _hash_key(self, text: str) -> str:
        """Generate a SHA-256 hash prefix for cache filenames."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _read_file_json(self, path: Path) -> Any | None:
        """Read and parse JSON from a path safely."""
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("[%s] Failed reading JSON %s: %s", self.source_name, path, exc)
        return None

    def _write_file_json(self, path: Path, data: Any) -> None:
        """Write JSON to a path safely."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("[%s] Failed writing JSON %s: %s", self.source_name, path, exc)

    def _get_fixture(self, key_hash: str, is_xml: bool = False) -> Any | None:
        """Look for a fixture file matching the key or the first available fixture."""
        if is_xml:
            xml_candidates = list(self.fixture_dir.glob("*.xml"))
            if xml_candidates:
                try:
                    return xml_candidates[0].read_text(encoding="utf-8")
                except Exception as exc:
                    logger.warning("[%s] Failed reading XML fixture: %s", self.source_name, exc)
            return None

        exact_match = self.fixture_dir / f"{key_hash}.json"
        if exact_match.exists():
            return self._read_file_json(exact_match)

        candidates = list(self.fixture_dir.glob("*.json"))
        if candidates:
            return self._read_file_json(candidates[0])
        return None

    def execute_request(
        self,
        url: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        custom_cache_key: str | None = None,
        is_xml: bool = False,
    ) -> dict[str, Any]:
        """Execute request with retries, caching, and multi-tier fallbacks."""
        serialized_key = (
            custom_cache_key
            or f"{method}_{url}_{json.dumps(params or {}, sort_keys=True)}_{str(data)}"
        )
        key_hash = self._hash_key(serialized_key)

        cache_file = self.cache_dir / f"{key_hash}.json"
        last_good_file = self.cache_dir / f"last_good_{key_hash}.json"

        now_ts = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Check valid cache
        cached_entry = self._read_file_json(cache_file)
        if (
            cached_entry
            and isinstance(cached_entry, dict)
            and (now_ts - cached_entry.get("timestamp", 0) < self.cache_ttl_seconds)
        ):
            logger.info("[%s] Cache hit for %s", self.source_name, url)
            return {
                "data": cached_entry.get("payload"),
                "fetched_at": cached_entry.get("fetched_at", now_iso),
                "source_status": "cached",
                "latency_ms": 0.0,
            }

        # 2. Live Request with 2 Retries & Exponential Backoff
        req_headers = dict(headers or {})
        start_time = time.time()
        last_exception = None

        for attempt in range(DEFAULT_RETRIES + 1):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=req_headers,
                    timeout=DEFAULT_TIMEOUT_S,
                )
                latency_ms = round((time.time() - start_time) * 1000, 1)

                if resp.status_code == 200:
                    payload = resp.text if is_xml else resp.json()
                    entry = {
                        "timestamp": now_ts,
                        "fetched_at": now_iso,
                        "payload": payload,
                    }
                    self._write_file_json(cache_file, entry)
                    self._write_file_json(last_good_file, entry)
                    logger.info(
                        "[%s] %s %s -> HTTP 200 (%.1f ms)",
                        self.source_name,
                        method,
                        url,
                        latency_ms,
                    )
                    return {
                        "data": payload,
                        "fetched_at": now_iso,
                        "source_status": "live",
                        "latency_ms": latency_ms,
                    }
                else:
                    logger.warning(
                        "[%s] HTTP %d on attempt %d for %s",
                        self.source_name,
                        resp.status_code,
                        attempt + 1,
                        url,
                    )
            except Exception as exc:
                last_exception = exc
                latency_ms = round((time.time() - start_time) * 1000, 1)
                logger.warning(
                    "[%s] Request failed attempt %d: %s", self.source_name, attempt + 1, exc
                )
                if attempt < DEFAULT_RETRIES:
                    time.sleep(1.0 * (2**attempt))

        # 3. Fallback: last-good cache
        last_good = self._read_file_json(last_good_file)
        if last_good and isinstance(last_good, dict):
            logger.info("[%s] Serving last-good cache after error", self.source_name)
            return {
                "data": last_good.get("payload"),
                "fetched_at": last_good.get("fetched_at", now_iso),
                "source_status": "cached",
                "latency_ms": round((time.time() - start_time) * 1000, 1),
                "error": str(last_exception),
            }

        # 4. Fallback: fixture
        fixture_payload = self._get_fixture(key_hash, is_xml=is_xml)
        if fixture_payload is not None:
            logger.info("[%s] Serving fixture data after failure", self.source_name)
            return {
                "data": fixture_payload,
                "fetched_at": now_iso,
                "source_status": "fixture",
                "latency_ms": round((time.time() - start_time) * 1000, 1),
            }

        # 5. Failed without data
        logger.error("[%s] All attempts and fallbacks exhausted for %s", self.source_name, url)
        return {
            "data": None,
            "fetched_at": now_iso,
            "source_status": "failed",
            "latency_ms": round((time.time() - start_time) * 1000, 1),
            "error": str(last_exception),
        }
