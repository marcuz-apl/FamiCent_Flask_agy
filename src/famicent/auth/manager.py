"""Password hashing and session management.

Uses Argon2id for password hashing (R18) with the parameters specified in rules.md.
Session validation checks timeout against SESSION_TIMEOUT_SECONDS.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError

from famicent.utils.helpers import SESSION_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Argon2id hasher configured per R18
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    type=Type.ID,  # Argon2id
)


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id.

    Args:
        password: The plaintext password.

    Returns:
        The Argon2id hash string.
    """
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Args:
        password_hash: The stored hash.
        password: The plaintext password to check.

    Returns:
        True if the password matches.
    """
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def is_session_expired(last_activity: datetime | None, timeout_seconds: int = SESSION_TIMEOUT_SECONDS) -> bool:
    """Check whether a session has exceeded the inactivity timeout.

    Args:
        last_activity: Timestamp of the last user action.
        timeout_seconds: Dynamic timeout value in seconds.

    Returns:
        True if the session is expired or last_activity is None.
    """
    if last_activity is None:
        return True
    delta = datetime.utcnow() - last_activity
    return delta > timedelta(seconds=timeout_seconds)
