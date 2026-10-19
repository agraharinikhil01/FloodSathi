"""
tests/conftest.py
-----------------
Shared pytest fixtures for FloodSaathi.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env so tests can read config without crashing on missing keys
load_dotenv()

# Ensure a dummy API key is set for tests that import config
# (real API calls are mocked; this prevents the ValueError guard from firing)
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key-for-pytest")
os.environ.setdefault("DB_PATH", "test_floodsaathi.db")


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    """Ensure test database exists with schema and core districts for integration tests."""
    db_file = Path("test_floodsaathi.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass
    schema_path = Path(__file__).parent.parent / "src" / "db" / "schema.sql"
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    # Seed core test districts
    districts = [
        ("Morigaon", "Assam", 26.25, 92.34),
        ("Dhubri", "Assam", 26.02, 89.98),
        ("Darbhanga", "Bihar", 26.15, 85.90),
    ]
    for name, state, lat, lon in districts:
        conn.execute(
            """
            INSERT OR IGNORE INTO districts (name, state, centroid_lat, centroid_lon)
            VALUES (?, ?, ?, ?)
            """,
            (name, state, lat, lon),
        )

    # Seed core test facilities
    facilities = [
        (1, "Morigaon Civil Hospital", "hospital", 26.255, 92.345, 150, 0),
        (1, "Morigaon High School Relief Camp", "shelter", 26.260, 92.350, 200, 10),
        (1, "Community Hall Ward 2", "shelter", 26.245, 92.335, 100, 0),
    ]
    for dist_id, name, f_type, lat, lon, cap, used in facilities:
        conn.execute(
            """
            INSERT INTO facilities (district_id, name, type, lat, lon, capacity, capacity_used, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'seed')
            """,
            (dist_id, name, f_type, lat, lon, cap, used),
        )

    # Seed core test volunteers
    volunteers = [
        (1, "Arjun Singh", "rescue,boat", 1, 26.252, 92.342, 1, "2026-10-19T00:00:00Z"),
        (1, "Priya Sharma", "medical,first-aid", 1, 26.258, 92.348, 1, "2026-10-19T00:00:00Z"),
    ]
    for dist_id, name, skills, cap, lat, lon, avail, created in volunteers:
        conn.execute(
            """
            INSERT INTO volunteers (district_id, name, skills, capacity, lat, lon, available, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dist_id, name, skills, cap, lat, lon, avail, created),
        )

    # Seed core test users
    try:
        import bcrypt

        c_hash = bcrypt.hashpw(b"demo1234", bcrypt.gensalt(rounds=4)).decode("utf-8")
        a_hash = bcrypt.hashpw(b"admin1234", bcrypt.gensalt(rounds=4)).decode("utf-8")
    except Exception:
        c_hash = "dummy_hash"
        a_hash = "dummy_hash"

    users = [
        ("coordinator", "coordinator", c_hash, "2026-10-19T00:00:00Z"),
        ("volunteer", "volunteer", c_hash, "2026-10-19T00:00:00Z"),
        ("admin", "admin", a_hash, "2026-10-19T00:00:00Z"),
    ]
    for uname, role, p_hash, created in users:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (username, role, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (uname, role, p_hash, created),
        )
    conn.commit()
    conn.close()
    yield
    # Cleanup test db
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def tmp_db(tmp_path: Path) -> Path:
    """Create a fresh in-memory-style SQLite DB from schema.sql for each test."""
    schema_path = Path(__file__).parent.parent / "src" / "db" / "schema.sql"
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture(scope="function")
def db_conn(tmp_db: Path):
    """Return an open SQLite connection to the temp test DB."""
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()
