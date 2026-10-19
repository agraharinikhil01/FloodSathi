"""
src/db/init_db.py
-----------------
Initialises FloodSaathi's SQLite database from schema.sql and loads seed data.

Usage:
    python src/db/init_db.py

Privacy: No real personal data is stored. All citizen records are synthetic.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DB_PATH = ROOT / os.getenv("DB_PATH", "floodsaathi.db")
SEED_DIR = ROOT / "data" / "seed"

# ─── Seed Data ────────────────────────────────────────────────────────────────
DISTRICTS: list[dict] = [
    # Assam
    {"name": "Morigaon", "state": "Assam", "lat": 26.25, "lon": 92.34, "dlat": 0.3, "dlon": 0.3},
    {"name": "Dhubri", "state": "Assam", "lat": 26.02, "lon": 89.98, "dlat": 0.3, "dlon": 0.3},
    {"name": "Barpeta", "state": "Assam", "lat": 26.32, "lon": 91.01, "dlat": 0.3, "dlon": 0.3},
    {"name": "Lakhimpur", "state": "Assam", "lat": 27.24, "lon": 94.10, "dlat": 0.3, "dlon": 0.3},
    {"name": "Goalpara", "state": "Assam", "lat": 26.17, "lon": 90.62, "dlat": 0.3, "dlon": 0.3},
    # Bihar
    {"name": "Darbhanga", "state": "Bihar", "lat": 26.15, "lon": 85.90, "dlat": 0.25, "dlon": 0.25},
    {
        "name": "Muzaffarpur",
        "state": "Bihar",
        "lat": 26.12,
        "lon": 85.36,
        "dlat": 0.25,
        "dlon": 0.25,
    },
    {"name": "Sitamarhi", "state": "Bihar", "lat": 26.59, "lon": 85.48, "dlat": 0.25, "dlon": 0.25},
    # Kerala
    {"name": "Alappuzha", "state": "Kerala", "lat": 9.49, "lon": 76.33, "dlat": 0.2, "dlon": 0.2},
    {"name": "Ernakulam", "state": "Kerala", "lat": 9.98, "lon": 76.28, "dlat": 0.2, "dlon": 0.2},
]

VOLUNTEER_NAMES = [
    "Arjun Singh",
    "Meena Devi",
    "Raju Sharma",
    "Sunita Kumari",
    "Vikram Rao",
    "Priya Nair",
    "Ajay Verma",
    "Kavitha Menon",
    "Ramesh Patel",
    "Anita Das",
    "Suresh Babu",
    "Lakshmi Iyer",
    "Mohan Lal",
    "Geeta Rani",
    "Sanjay Gupta",
    "Usha Pillai",
    "Deepak Kumar",
    "Asha Devi",
    "Rajesh Tiwari",
    "Nandini Roy",
]

SKILLS_POOL = [
    "rescue,first-aid",
    "first-aid,logistics",
    "rescue,diving",
    "logistics,communication",
    "medical,first-aid",
    "cooking,logistics",
    "rescue,communication",
    "medical,psychology",
]

RAW_MESSAGES_EN = [
    "Water has entered our house, 4 people are stuck, one is old and cannot walk.",
    "We need food and drinking water urgently, 10 people here including 3 kids.",
    "My mother needs medicine, she is diabetic. We are on the rooftop.",
    "6 people trapped on second floor, water level rising fast, please send boat.",
    "There is a pregnant woman in our colony, she needs immediate medical help.",
]

RAW_MESSAGES_HI = [
    "bhaiya paani ghar mein ghus gaya, 5 log hain, ek budhiya hai aur chal nahi sakti.",
    "khana aur paani chahiye, hum 8 log hain, 2 bachche bhi hain, bahut bhookh lagi hai.",
    "mere papa ko insulin chahiye, hum chhath par hain, naav bhejo please.",
    "hamare mohalle mein 12 log phanse hain, ek mahila ki delivery hone wali hai.",
    "koi sun raha hai? hum dono din se chhat par hain, kuch nahi khaya.",
]

RAW_MESSAGES_HINGLISH = [
    "bhaiya 3 log hain mere ghar mein, ek aadmi ki tabiyat kharab hai, rescue karo.",
    "yaar food nahi hai past 2 days, 6 people stuck, please help karo.",
    "meri dadi ko hospital chahiye, ghar mein paani hai, please boat bhejo.",
    "10 log hain, children bhi hain, shelter chahiye, bahut rain ho raha hai.",
    "water rising fast, hamara ghar ground floor par hai, please rescue.",
]

NEEDS = ["rescue", "medical", "food", "shelter", "other"]
VULNERABLE = [["elderly"], ["children"], ["pregnant"], ["disabled"], ["elderly", "children"], []]
STATUSES = ["new"] * 4 + ["assigned"] * 4 + ["resolved"] * 2  # weighted


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bbox(lat: float, lon: float, delta_lat: float, delta_lon: float) -> tuple:
    return lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon


def _rand_point(lat: float, lon: float, delta: float = 0.15) -> tuple[float, float]:
    return (
        lat + random.uniform(-delta, delta),
        lon + random.uniform(-delta, delta),
    )


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables from schema.sql."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    print("[OK] Tables created")


def seed_districts(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert districts, return name->id mapping."""
    mapping: dict[str, int] = {}
    for d in DISTRICTS:
        min_lat, max_lat, min_lon, max_lon = _bbox(d["lat"], d["lon"], d["dlat"], d["dlon"])
        conn.execute(
            """
            INSERT OR IGNORE INTO districts
                (name, state, centroid_lat, centroid_lon,
                 bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (d["name"], d["state"], d["lat"], d["lon"], min_lat, max_lat, min_lon, max_lon),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM districts WHERE name=?", (d["name"],)).fetchone()
        mapping[d["name"]] = row[0]
    print(f"[OK] {len(DISTRICTS)} districts seeded")
    return mapping


def seed_grid_points(conn: sqlite3.Connection, district_map: dict[str, int]) -> None:
    """Insert 2 grid points per district (centroid +- offset)."""
    for d in DISTRICTS:
        did = district_map[d["name"]]
        for offset in [0.1, -0.1]:
            conn.execute(
                "INSERT INTO grid_points (district_id, lat, lon) VALUES (?, ?, ?)",
                (did, d["lat"] + offset, d["lon"] + offset),
            )
    conn.commit()
    print(f"[OK] {len(DISTRICTS) * 2} grid points seeded")


def seed_facilities(conn: sqlite3.Connection, district_map: dict[str, int]) -> None:
    """Insert synthetic facility data (Overpass fetch attempted separately)."""
    random.seed(42)
    count = 0
    for d in DISTRICTS:
        did = district_map[d["name"]]
        for ftype in ("hospital", "shelter", "school"):
            lat, lon = _rand_point(d["lat"], d["lon"])
            capacity = random.randint(50, 500)
            conn.execute(
                """
                INSERT INTO facilities (district_id, name, type, lat, lon, capacity, source)
                VALUES (?, ?, ?, ?, ?, ?, 'seed')
                """,
                (did, f"{d['name']} {ftype.title()} {count % 3 + 1}", ftype, lat, lon, capacity),
            )
            count += 1
    conn.commit()
    print(f"[OK] {count} facilities seeded")


def seed_volunteers(conn: sqlite3.Connection, district_map: dict[str, int]) -> None:
    """Insert 20 synthetic volunteers."""
    random.seed(99)
    district_names = list(district_map.keys())
    for i, name in enumerate(VOLUNTEER_NAMES):
        d_name = district_names[i % len(district_names)]
        d_info = next(x for x in DISTRICTS if x["name"] == d_name)
        lat, lon = _rand_point(d_info["lat"], d_info["lon"])
        conn.execute(
            """
            INSERT INTO volunteers (district_id, name, skills, capacity, lat, lon, available, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (district_map[d_name], name, random.choice(SKILLS_POOL), 1, lat, lon, _now()),
        )
    conn.commit()
    print(f"[OK] {len(VOLUNTEER_NAMES)} volunteers seeded")


def seed_help_requests(conn: sqlite3.Connection, district_map: dict[str, int]) -> None:
    """Insert 100 synthetic help requests."""
    random.seed(7)
    all_messages = (
        [(m, "en") for m in RAW_MESSAGES_EN * 7]
        + [(m, "hi") for m in RAW_MESSAGES_HI * 7]
        + [(m, "hinglish") for m in RAW_MESSAGES_HINGLISH * 6]
    )
    random.shuffle(all_messages)
    district_names = list(district_map.keys())

    for i in range(100):
        raw, lang = all_messages[i % len(all_messages)]
        d_name = random.choice(district_names)
        d_info = next(x for x in DISTRICTS if x["name"] == d_name)
        lat, lon = _rand_point(d_info["lat"], d_info["lon"], delta=0.1)
        urgency = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 30, 35, 20])[0]
        need = random.choice(NEEDS)
        people = random.randint(1, 15)
        vg = random.choice(VULNERABLE)
        status = random.choice(STATUSES)
        ts = _now()
        conn.execute(
            """
            INSERT INTO help_requests
                (district_id, raw_text, language, location_raw, lat, lon,
                 urgency, need, people_count, vulnerable_groups,
                 summary_en, summary_hi, triage_method, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'fallback', ?, ?, ?)
            """,
            (
                district_map[d_name],
                raw,
                lang,
                d_name,
                lat,
                lon,
                urgency,
                need,
                people,
                json.dumps(vg),
                f"[Synthetic] {need} needed for {people} people in {d_name}",
                f"[Synthetic] {d_name} needs {need} for {people} people",
                status,
                ts,
                ts,
            ),
        )
    conn.commit()
    print("[OK] 100 help requests seeded")


def seed_risk_scores(conn: sqlite3.Connection, district_map: dict[str, int]) -> None:
    """Insert synthetic initial risk scores."""
    random.seed(3)
    levels = ["low", "medium", "high", "severe"]
    explanations = {
        "low": "Precipitation below 20 mm/24h; river discharge normal.",
        "medium": "Precipitation 20-50 mm/24h; discharge slightly elevated.",
        "high": "Precipitation > 50 mm/24h; discharge 2x normal; low elevation.",
        "severe": "Discharge 3x normal + 48h cumulative rain > 150 mm.",
    }
    for name, did in district_map.items():
        level = random.choice(levels)
        score = {"low": 0.15, "medium": 0.40, "high": 0.65, "severe": 0.90}[level]
        conn.execute(
            """
            INSERT INTO risk_scores (district_id, level, explanation, score_raw, computed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (did, level, explanations[level], score, _now()),
        )
    conn.commit()
    print(f"[OK] Risk scores seeded for {len(district_map)} districts")


def seed_user(conn: sqlite3.Connection) -> None:
    """Insert a single demo coordinator account."""
    try:
        import bcrypt

        pw_hash = bcrypt.hashpw(b"demo1234", bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib

        pw_hash = hashlib.sha256(b"demo1234").hexdigest()  # fallback, not for prod
    conn.execute(
        "INSERT OR IGNORE INTO users (username, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("coordinator", "coordinator", pw_hash, _now()),
    )
    conn.commit()
    print("[OK] Demo user seeded (username=coordinator, password=demo1234)")


def print_summary(conn: sqlite3.Connection) -> None:
    tables = [
        "districts",
        "grid_points",
        "weather_snapshots",
        "risk_scores",
        "facilities",
        "volunteers",
        "help_requests",
        "assignments",
        "alerts",
        "users",
    ]
    print("\n--- Database Summary -----------------------------")
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<25} {n:>5} rows")
    size_kb = DB_PATH.stat().st_size / 1024
    print(f"\n  DB file: {DB_PATH}")
    print(f"  Size:    {size_kb:.1f} KB")
    print("-------------------------------------------------\n")


def main() -> None:
    print(f"\nFloodSaathi -- DB Initialisation\n   DB: {DB_PATH}\n")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    create_tables(conn)
    district_map = seed_districts(conn)
    seed_grid_points(conn, district_map)
    seed_facilities(conn, district_map)
    seed_volunteers(conn, district_map)
    seed_help_requests(conn, district_map)
    seed_risk_scores(conn, district_map)
    seed_user(conn)

    print_summary(conn)
    conn.close()
    print("[DONE] Database ready.\n")


if __name__ == "__main__":
    main()
