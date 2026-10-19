"""
src/db/queries.py
-----------------
Database queries and helper functions for FloodSaathi SQLite database.
All DB access goes through these functions.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

import config


def get_connection() -> sqlite3.Connection:
    """Return an open SQLite connection with Row factory and WAL mode."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def list_districts() -> list[dict[str, Any]]:
    """Return all districts as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, name, state, centroid_lat, centroid_lon,
                   bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
            FROM districts
            ORDER BY name ASC
            """).fetchall()
        return [dict(r) for r in rows]


def get_district_by_name(name: str) -> dict[str, Any] | None:
    """Return a single district by name or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, state, centroid_lat, centroid_lon,
                   bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
            FROM districts
            WHERE name = ?
            """,
            (name,),
        ).fetchone()
        return dict(row) if row else None


def get_district_by_id(district_id: int) -> dict[str, Any] | None:
    """Return a single district by its integer ID or None."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, state, centroid_lat, centroid_lon,
                   bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
            FROM districts
            WHERE id = ?
            """,
            (district_id,),
        ).fetchone()
        return dict(row) if row else None


def get_latest_risk_score(district_id: int) -> dict[str, Any] | None:
    """Return the most recent risk score record for a given district."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, district_id, level, explanation, score_raw, computed_at
            FROM risk_scores
            WHERE district_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            (district_id,),
        ).fetchone()
        return dict(row) if row else None


def save_risk_score(district_id: int, level: str, explanation: str, score_raw: float) -> int:
    """Insert a new risk score evaluation for a district and return inserted ID."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO risk_scores (district_id, level, explanation, score_raw, computed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (district_id, level.lower(), explanation, score_raw, now_iso),
        )
        conn.commit()
        return cur.lastrowid or 0


def list_facilities(
    district_id: int | None = None,
    facility_type: str | None = None,
) -> list[dict[str, Any]]:
    """Return facilities filtered optionally by district and facility type."""
    query = "SELECT id, district_id, name, type, lat, lon, capacity, capacity_used, source FROM facilities WHERE 1=1"
    params: list[Any] = []
    if district_id is not None:
        query += " AND district_id = ?"
        params.append(district_id)
    if facility_type is not None:
        query += " AND type = ?"
        params.append(facility_type)
    query += " ORDER BY name ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def ensure_facilities_schema() -> None:
    """Ensure facilities table has osm_id column."""
    with get_connection() as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(facilities)").fetchall()]
        if "osm_id" not in cols:
            conn.execute("ALTER TABLE facilities ADD COLUMN osm_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_facilities_osmid ON facilities(osm_id)")
        conn.commit()


def save_facility(
    district_id: int | None,
    name: str,
    facility_type: str,
    lat: float,
    lon: float,
    capacity: int = 100,
    osm_id: str | None = None,
    source: str = "overpass",
) -> int:
    """Save or update facility in database."""
    ensure_facilities_schema()
    with get_connection() as conn:
        if osm_id:
            existing = conn.execute(
                "SELECT id FROM facilities WHERE osm_id = ?", (osm_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE facilities
                    SET district_id = ?, name = ?, type = ?, lat = ?, lon = ?, capacity = ?, source = ?
                    WHERE osm_id = ?
                    """,
                    (district_id, name, facility_type, lat, lon, capacity, source, osm_id),
                )
                conn.commit()
                return int(existing["id"])

        cur = conn.execute(
            """
            INSERT INTO facilities (district_id, name, type, lat, lon, capacity, source, osm_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (district_id, name, facility_type, lat, lon, capacity, source, osm_id),
        )
        conn.commit()
        return cur.lastrowid or 0


def list_volunteers(
    district_id: int | None = None,
    available_only: bool = True,
) -> list[dict[str, Any]]:
    """Return volunteers optionally filtered by district and availability."""
    query = "SELECT id, district_id, name, skills, capacity, lat, lon, available, created_at FROM volunteers WHERE 1=1"
    params: list[Any] = []
    if district_id is not None:
        query += " AND district_id = ?"
        params.append(district_id)
    if available_only:
        query += " AND available = 1"
    query += " ORDER BY name ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def ensure_alerts_schema() -> None:
    """Ensure alerts table has source and identifier columns and indexes."""
    with get_connection() as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(alerts)").fetchall()]
        if "source" not in cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN source TEXT DEFAULT 'internal'")
        if "identifier" not in cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN identifier TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_identifier ON alerts(identifier)")
        conn.commit()


def save_or_update_alert(
    district_id: int | None,
    level: str,
    message_en: str,
    message_hi: str,
    channel: str = "public",
    source: str = "internal",
    identifier: str | None = None,
) -> int:
    """Insert or update an alert. If identifier exists, update existing record."""
    ensure_alerts_schema()
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        if identifier:
            existing = conn.execute(
                "SELECT id FROM alerts WHERE identifier = ?", (identifier,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE alerts
                    SET district_id = ?, level = ?, message_en = ?, message_hi = ?,
                        channel = ?, sent_at = ?, source = ?
                    WHERE identifier = ?
                    """,
                    (
                        district_id,
                        level.lower(),
                        message_en,
                        message_hi,
                        channel,
                        now_iso,
                        source,
                        identifier,
                    ),
                )
                conn.commit()
                return int(existing["id"])

        cur = conn.execute(
            """
            INSERT INTO alerts (district_id, level, message_hi, message_en, channel, sent_at, source, identifier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                district_id,
                level.lower(),
                message_hi,
                message_en,
                channel,
                now_iso,
                source,
                identifier,
            ),
        )
        conn.commit()
        return cur.lastrowid or 0


def delete_alert_by_identifier(identifier: str) -> bool:
    """Delete an alert by its unique identifier (used for msgType Cancel)."""
    ensure_alerts_schema()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM alerts WHERE identifier = ?", (identifier,))
        conn.commit()
        return cur.rowcount > 0


def get_active_official_alert(district_id: int) -> dict[str, Any] | None:
    """Return the latest official (SACHET) alert for a district."""
    ensure_alerts_schema()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, district_id, level, message_en, message_hi, channel, sent_at, source, identifier
            FROM alerts
            WHERE district_id = ? AND source = 'SACHET'
            ORDER BY sent_at DESC
            LIMIT 1
            """,
            (district_id,),
        ).fetchone()
        return dict(row) if row else None


def list_alerts(
    district_id: int | str | None = None, source: str | None = None
) -> list[dict[str, Any]]:
    """Return alerts optionally filtered by district (ID or name) and source."""
    ensure_alerts_schema()
    query = (
        "SELECT id, district_id, level, message_en, message_hi, channel, sent_at, source,"
        " identifier FROM alerts WHERE 1=1"
    )
    params: list[Any] = []
    if district_id is not None:
        resolved_id = None
        if isinstance(district_id, str):
            d_info = get_district_by_name(district_id)
            if d_info:
                resolved_id = d_info["id"]
        else:
            resolved_id = district_id

        if resolved_id is not None:
            query += " AND district_id = ?"
            params.append(resolved_id)
    if source is not None:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY sent_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def ensure_help_requests_schema() -> None:
    """Ensure help_requests table has location_source and location_confidence columns."""
    with get_connection() as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(help_requests)").fetchall()]
        if "location_source" not in cols:
            conn.execute("ALTER TABLE help_requests ADD COLUMN location_source TEXT")
        if "location_confidence" not in cols:
            conn.execute("ALTER TABLE help_requests ADD COLUMN location_confidence TEXT")
        conn.commit()


def save_help_request(
    raw_text: str,
    language: str,
    location_raw: str,
    lat: float | None,
    lon: float | None,
    urgency: int,
    need: str,
    people_count: int,
    vulnerable_groups: list[str],
    summary_en: str,
    summary_hi: str | None = None,
    triage_method: str = "llm",
    district_id: int | None = None,
    status: str = "new",
    location_source: str | None = None,
    location_confidence: str | None = None,
) -> int:
    """Insert a triaged emergency request into help_requests table."""
    ensure_help_requests_schema()
    now_iso = datetime.now(timezone.utc).isoformat()
    vg_json = json.dumps(vulnerable_groups)

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO help_requests
                (district_id, raw_text, language, location_raw, lat, lon,
                 urgency, need, people_count, vulnerable_groups,
                 summary_en, summary_hi, triage_method, status, created_at, updated_at,
                 location_source, location_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                district_id,
                raw_text,
                language,
                location_raw,
                lat,
                lon,
                urgency,
                need,
                people_count,
                vg_json,
                summary_en,
                summary_hi,
                triage_method,
                status,
                now_iso,
                now_iso,
                location_source,
                location_confidence,
            ),
        )
        conn.commit()
        return cur.lastrowid or 0


def list_help_requests(
    status: str | None = None,
    urgency: int | None = None,
    district_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return help requests optionally filtered by status, minimum urgency, or district."""
    ensure_help_requests_schema()
    query = """
    SELECT id, district_id, raw_text, language, location_raw, lat, lon,
           urgency, need, people_count, vulnerable_groups,
           summary_en, summary_hi, triage_method, status, created_at, updated_at,
           location_source, location_confidence
    FROM help_requests
    WHERE 1=1
    """
    params: list[Any] = []
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if urgency is not None:
        query += " AND urgency >= ?"
        params.append(urgency)
    if district_id is not None:
        query += " AND district_id = ?"
        params.append(district_id)

    query += " ORDER BY urgency DESC, created_at DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["vulnerable_groups"] = json.loads(d["vulnerable_groups"] or "[]")
            except Exception:
                d["vulnerable_groups"] = []
            result.append(d)
        return result


def get_help_request_by_id(request_id: int) -> dict[str, Any] | None:
    """Return single help request record by ID."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, district_id, raw_text, language, location_raw, lat, lon,
                   urgency, need, people_count, vulnerable_groups,
                   summary_en, summary_hi, triage_method, status, created_at, updated_at
            FROM help_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["vulnerable_groups"] = json.loads(d["vulnerable_groups"] or "[]")
        except Exception:
            d["vulnerable_groups"] = []
        return d


def save_assignment(
    request_id: int,
    resource_type: str,
    resource_id: int,
    distance_km: float,
    eta_min: int,
) -> int:
    """Record a resource assignment (shelter, hospital, volunteer) for a help request."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO assignments (request_id, resource_type, resource_id, distance_km, eta_min, assigned_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (request_id, resource_type, resource_id, round(distance_km, 2), eta_min, now_iso),
        )
        conn.commit()
        return cur.lastrowid or 0


def get_assignments_for_request(request_id: int) -> list[dict[str, Any]]:
    """Fetch all resource assignments for a single help request."""
    query = """
    SELECT a.id, a.request_id, a.resource_type, a.resource_id, a.distance_km, a.eta_min, a.assigned_at,
           CASE
               WHEN a.resource_type IN ('hospital', 'shelter') THEN f.name
               ELSE v.name
           END as resource_name,
           CASE
               WHEN a.resource_type IN ('hospital', 'shelter') THEN f.lat
               ELSE v.lat
           END as resource_lat,
           CASE
               WHEN a.resource_type IN ('hospital', 'shelter') THEN f.lon
               ELSE v.lon
           END as resource_lon
    FROM assignments a
    LEFT JOIN facilities f ON a.resource_id = f.id AND a.resource_type IN ('hospital', 'shelter')
    LEFT JOIN volunteers v ON a.resource_id = v.id AND a.resource_type = 'volunteer'
    WHERE a.request_id = ?
    ORDER BY a.assigned_at ASC
    """
    with get_connection() as conn:
        rows = conn.execute(query, (request_id,)).fetchall()
        return [dict(r) for r in rows]


def update_request_status(request_id: int, status: str) -> None:
    """Update status ('new', 'assigned', 'resolved') of a help request."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE help_requests SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso, request_id),
        )
        conn.commit()


def get_facility_by_id(facility_id: int) -> dict[str, Any] | None:
    """Fetch single facility record by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, district_id, name, type, lat, lon, capacity, capacity_used, source FROM facilities WHERE id = ?",
            (facility_id,),
        ).fetchone()
        return dict(row) if row else None


def get_volunteer_by_id(volunteer_id: int) -> dict[str, Any] | None:
    """Fetch single volunteer record by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, district_id, name, skills, capacity, lat, lon, available, created_at FROM volunteers WHERE id = ?",
            (volunteer_id,),
        ).fetchone()
        return dict(row) if row else None


def update_volunteer_availability(volunteer_id: int, available: bool) -> None:
    """Set volunteer availability state (1 or 0)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE volunteers SET available = ? WHERE id = ?",
            (1 if available else 0, volunteer_id),
        )
        conn.commit()


def update_facility_capacity_used(facility_id: int, delta: int) -> None:
    """Adjust capacity_used for a shelter or hospital."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE facilities
            SET capacity_used = MAX(0, MIN(capacity, capacity_used + ?))
            WHERE id = ?
            """,
            (delta, facility_id),
        )
        conn.commit()


def list_assignments_with_details(district_id: int | None = None) -> list[dict[str, Any]]:
    """List all assignments with joined request, facility, and volunteer details."""
    query = """
    SELECT a.id as assignment_id, a.request_id, a.resource_type, a.resource_id,
           a.distance_km, a.eta_min, a.assigned_at,
           r.district_id, r.location_raw, r.urgency, r.need, r.people_count, r.status as request_status,
           r.lat as request_lat, r.lon as request_lon,
           CASE
               WHEN a.resource_type IN ('hospital', 'shelter') THEN f.name
               ELSE v.name
           END as resource_name,
           CASE
               WHEN a.resource_type IN ('hospital', 'shelter') THEN f.lat
               ELSE v.lat
           END as resource_lat,
           CASE
               WHEN a.resource_type IN ('hospital', 'shelter') THEN f.lon
               ELSE v.lon
           END as resource_lon
    FROM assignments a
    JOIN help_requests r ON a.request_id = r.id
    LEFT JOIN facilities f ON a.resource_id = f.id AND a.resource_type IN ('hospital', 'shelter')
    LEFT JOIN volunteers v ON a.resource_id = v.id AND a.resource_type = 'volunteer'
    WHERE 1=1
    """
    params: list[Any] = []
    if district_id is not None:
        query += " AND r.district_id = ?"
        params.append(district_id)
    query += " ORDER BY a.assigned_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_user_by_username(username: str) -> dict[str, Any] | None:
    """Retrieve user record by username."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, role, password_hash, created_at FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        return dict(row) if row else None


def create_user(username: str, role: str, password_hash: str) -> int:
    """Insert or update a user account in database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (username, role, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                role = excluded.role,
                password_hash = excluded.password_hash
            """,
            (username.strip(), role.strip().lower(), password_hash, now_iso),
        )
        conn.commit()
        return cur.lastrowid or 0


def list_users() -> list[dict[str, Any]]:
    """Return all registered system users (excluding password hashes for safety)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY username ASC"
        ).fetchall()
        return [dict(r) for r in rows]
