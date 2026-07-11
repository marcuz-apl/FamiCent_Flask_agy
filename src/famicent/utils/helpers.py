"""Shared helper utilities for FamiCent.

Provides constants, CSRF token generation, and common formatting helpers.
"""
from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SESSION_TIMEOUT_SECONDS: int = 300  # 5 minutes
DEFAULT_ADMIN_USERNAME: str = "admin"
DEFAULT_ADMIN_PASSWORD: str = "admin123"
GENERATED_PASSWORD_LENGTH: int = 24
TOTP_ISSUER_NAME: str = "FamiCent"
TOTP_DIGEST: str = "sha256"
TOTP_DIGITS: int = 6
TOTP_INTERVAL: int = 30


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token.

    Returns:
        A 64-character hex token.
    """
    return secrets.token_hex(32)


def generate_secure_password(length: int = GENERATED_PASSWORD_LENGTH) -> str:
    """Generate a cryptographically random password.

    Uses `secrets.choice` over `string.ascii_letters + string.digits + string.punctuation`
    as specified in R43.

    Args:
        length: Number of characters. Defaults to 24.

    Returns:
        A random password string.
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


def format_currency(amount: float) -> str:
    """Format a float as USD currency string.

    Args:
        amount: The numeric amount.

    Returns:
        Formatted string like '$1,234.56'.
    """
    return f"${amount:,.2f}"


def format_date(dt: datetime | str | None) -> str:
    """Format a datetime or string representation of date for display.

    Args:
        dt: A datetime object, date string, or None.

    Returns:
        Formatted string like 'Jul 08, 2026', 'Every Monday', 'Jul 15', or '—' if None.
    """
    if dt is None:
        return "—"
    
    if isinstance(dt, datetime):
        return dt.strftime("%b %d, %Y")
        
    val_str = str(dt).strip()
    if not val_str:
        return "—"
        
    # Check weekly weekday options '1'-'7'
    weekdays = {
        "1": "Every Monday",
        "2": "Every Tuesday",
        "3": "Every Wednesday",
        "4": "Every Thursday",
        "5": "Every Friday",
        "6": "Every Saturday",
        "7": "Every Sunday"
    }
    if val_str in weekdays:
        return weekdays[val_str]
        
    # Check monthly MM-DD values
    if "-" in val_str:
        parts = val_str.split("-")
        if len(parts) == 2:
            try:
                # E.g. "07-15" -> "Jul 15"
                parsed = datetime.strptime(val_str, "%m-%d")
                return parsed.strftime("%b %d")
            except ValueError:
                pass
        elif len(parts) == 3:
            try:
                parsed = datetime.strptime(val_str, "%Y-%m-%d")
                return parsed.strftime("%b %d, %Y")
            except ValueError:
                pass
                
    return val_str
