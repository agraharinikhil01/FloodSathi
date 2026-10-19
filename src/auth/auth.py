"""
src/auth/auth.py
----------------
Authentication, role-based access control (RBAC), and security helpers.
Uses bcrypt for secure password hashing and verification.
Enforces session rate limiting and input sanitization to protect emergency infrastructure.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import bcrypt

from src.db.queries import create_user, get_user_by_username

logger = logging.getLogger(__name__)

ROLE_LEVELS: dict[str, int] = {
    "citizen": 0,
    "volunteer": 1,
    "coordinator": 2,
    "admin": 3,
}

DEFAULT_CREDENTIALS = [
    ("coordinator", "demo1234", "coordinator"),
    ("volunteer", "demo1234", "volunteer"),
    ("admin", "admin1234", "admin"),
]


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception as exc:
        logger.warning("Password verification failed with error: %s", exc)
        return False


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate credentials against users table; returns user profile if valid."""
    user = get_user_by_username(username)
    if not user:
        return None
    if verify_password(password, user["password_hash"]):
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "created_at": user["created_at"],
        }
    return None


def seed_default_users() -> None:
    """Ensure standard demo accounts are initialized with bcrypt hashes."""
    for uname, pwd, role in DEFAULT_CREDENTIALS:
        existing = get_user_by_username(uname)
        if not existing:
            pw_hash = hash_password(pwd)
            create_user(uname, role, pw_hash)


def has_permission(user_role: str, required_role: str) -> bool:
    """Check if user role satisfies minimum required role level."""
    u_level = ROLE_LEVELS.get(user_role.lower(), 0)
    r_level = ROLE_LEVELS.get(required_role.lower(), 0)
    return u_level >= r_level


def can_access_dashboard(role: str) -> bool:
    """Check if role can view coordinator operations dashboard."""
    return has_permission(role, "volunteer")


def can_manage_alerts(role: str) -> bool:
    """Check if role can generate and broadcast official public alerts."""
    return has_permission(role, "coordinator")


def can_trigger_matching(role: str) -> bool:
    """Check if role can execute automated resource allocation."""
    return has_permission(role, "coordinator")


def check_rate_limit(
    history: list[float],
    max_requests: int = 5,
    window_seconds: int = 60,
) -> bool:
    """Sliding-window rate limiter checking if a new request is allowed."""
    now = time.time()
    cutoff = now - window_seconds
    valid_history = [t for t in history if t > cutoff]
    history.clear()
    history.extend(valid_history)

    if len(history) >= max_requests:
        return False

    history.append(now)
    return True


def sanitize_input(text: str, max_length: int = 1000) -> tuple[bool, str]:
    """Validate and clean user input text, rejecting oversize or null-byte strings."""
    if not text or not text.strip():
        return False, "Input cannot be empty."
    if len(text) > max_length:
        return False, f"Input exceeds maximum allowed length of {max_length} characters."
    if "\x00" in text:
        return False, "Input contains prohibited characters."
    return True, text.strip()
