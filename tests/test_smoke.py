"""
tests/test_smoke.py
-------------------
Phase 0 smoke tests — verify the scaffold is healthy before building features.
"""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path


def test_schema_sql_exists(project_root: Path) -> None:
    """schema.sql must exist and be non-empty."""
    schema = project_root / "src" / "db" / "schema.sql"
    assert schema.exists(), "schema.sql not found"
    assert schema.stat().st_size > 0, "schema.sql is empty"


def test_schema_creates_all_tables(db_conn: sqlite3.Connection) -> None:
    """All 9 expected tables must exist after schema is applied."""
    expected = {
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
    }
    rows = db_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    actual = {row["name"] for row in rows}
    missing = expected - actual
    assert not missing, f"Missing tables: {missing}"


def test_config_imports_cleanly() -> None:
    """config.py must import without raising (dummy API key is set in conftest)."""
    import config  # noqa: F401

    assert hasattr(config, "DB_PATH")
    assert hasattr(config, "DEFAULT_DISTRICT")
    assert hasattr(config, "CACHE_DIR")


def test_src_packages_importable() -> None:
    """All src sub-packages must be importable (even if empty)."""
    packages = [
        "src",
        "src.utils",
        "src.data",
        "src.risk",
        "src.triage",
        "src.matching",
        "src.db",
        "src.alerts",
        "src.auth",
        "src.integrations",
    ]
    for pkg in packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Cannot import {pkg}"


def test_env_example_has_required_keys(project_root: Path) -> None:
    """.env.example must contain the critical key names."""
    env_example = project_root / ".env.example"
    assert env_example.exists(), ".env.example not found"
    content = env_example.read_text(encoding="utf-8")
    for key in ("ANTHROPIC_API_KEY", "DB_PATH", "CACHE_DIR", "DEFAULT_DISTRICT"):
        assert key in content, f"{key} missing from .env.example"


def test_requirements_txt_exists(project_root: Path) -> None:
    """requirements.txt must list key dependencies."""
    req = project_root / "requirements.txt"
    assert req.exists()
    content = req.read_text()
    for pkg in ("streamlit", "anthropic", "pydantic", "folium", "pytest"):
        assert pkg in content, f"{pkg} missing from requirements.txt"


def test_gitignore_blocks_env(project_root: Path) -> None:
    """.gitignore must include .env pattern."""
    gitignore = project_root / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text()
    assert ".env" in content
    assert "*.db" in content
