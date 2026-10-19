"""
tests/test_auth.py
------------------
Unit and integration tests for authentication, RBAC permissions,
rate limiting, and input validation guards.
"""

from __future__ import annotations

import time

from src.auth.auth import (
    authenticate,
    can_access_dashboard,
    can_manage_alerts,
    can_trigger_matching,
    check_rate_limit,
    has_permission,
    hash_password,
    sanitize_input,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    """Verify that bcrypt hashes correctly and verifies matching passwords."""
    raw_pwd = "EmergencySecurePass123!"
    pw_hash = hash_password(raw_pwd)

    assert pw_hash != raw_pwd
    assert pw_hash.startswith("$2b$") or pw_hash.startswith("$2a$")
    assert verify_password(raw_pwd, pw_hash) is True
    assert verify_password("WrongPassword!", pw_hash) is False


def test_authenticate_user() -> None:
    """Verify end-to-end database credential authentication."""
    # Seeded demo credentials
    user = authenticate("coordinator", "demo1234")
    assert user is not None
    assert user["username"] == "coordinator"
    assert user["role"] == "coordinator"
    assert "password_hash" not in user

    # Invalid password
    bad_user = authenticate("coordinator", "wrongpassword")
    assert bad_user is None

    # Unknown username
    none_user = authenticate("nonexistent_coordinator", "demo1234")
    assert none_user is None


def test_role_hierarchy_permissions() -> None:
    """Verify role-based access control rules across system components."""
    # Citizen
    assert not can_access_dashboard("citizen")
    assert not can_manage_alerts("citizen")
    assert not can_trigger_matching("citizen")

    # Volunteer
    assert can_access_dashboard("volunteer")
    assert not can_manage_alerts("volunteer")
    assert not can_trigger_matching("volunteer")

    # Coordinator
    assert can_access_dashboard("coordinator")
    assert can_manage_alerts("coordinator")
    assert can_trigger_matching("coordinator")

    # Admin
    assert can_access_dashboard("admin")
    assert can_manage_alerts("admin")
    assert can_trigger_matching("admin")

    # Relative rank helper
    assert has_permission("admin", "coordinator")
    assert not has_permission("citizen", "volunteer")


def test_sliding_window_rate_limiting() -> None:
    """Verify sliding-window rate limiting prevents flooding."""
    history: list[float] = []

    # 5 requests should pass
    for _ in range(5):
        assert check_rate_limit(history, max_requests=5, window_seconds=60) is True

    # 6th request within window must be rejected
    assert check_rate_limit(history, max_requests=5, window_seconds=60) is False

    # Simulate expired timestamps
    old_time = time.time() - 100
    stale_history = [old_time, old_time, old_time]
    assert check_rate_limit(stale_history, max_requests=2, window_seconds=60) is True


def test_sanitize_input_guards() -> None:
    """Verify input validation and length limits."""
    # Valid input
    ok, text = sanitize_input("  Help us in Mayong village!  ", max_length=1000)
    assert ok is True
    assert text == "Help us in Mayong village!"

    # Empty string
    ok, err = sanitize_input("   ", max_length=1000)
    assert ok is False
    assert "empty" in err.lower()

    # Oversized string
    oversized = "A" * 1001
    ok, err = sanitize_input(oversized, max_length=1000)
    assert ok is False
    assert "maximum" in err.lower()

    # Null-byte injection
    injection = "Help me please\x00DROP TABLE users;"
    ok, err = sanitize_input(injection, max_length=1000)
    assert ok is False
    assert "prohibited" in err.lower()
