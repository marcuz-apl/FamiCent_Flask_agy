"""TOTP multi-factor authentication helpers.

Implements RFC 6238 TOTP with SHA-256, 6-digit codes, and 30-second window (R21).
"""
from __future__ import annotations

import io
import logging

import pyotp
import qrcode  # type: ignore[import-untyped]
import qrcode.constants  # type: ignore[import-untyped]

from famicent.utils.helpers import TOTP_DIGITS, TOTP_INTERVAL, TOTP_ISSUER_NAME

logger = logging.getLogger(__name__)


def generate_secret() -> str:
    """Generate a new TOTP secret key.

    Returns:
        A base32-encoded secret string.
    """
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    """Create a TOTP instance with the app's standard parameters.

    Args:
        secret: The base32-encoded secret.

    Returns:
        A configured ``pyotp.TOTP`` object.
    """
    return pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)


def verify_code(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret.

    Allows ±1 window for clock skew tolerance.

    Args:
        secret: The base32-encoded secret.
        code: The 6-digit code from the authenticator app.

    Returns:
        True if the code is valid within the time window.
    """
    totp = get_totp(secret)
    return totp.verify(code, valid_window=1)


def get_provisioning_uri(secret: str, username: str) -> str:
    """Generate the otpauth:// URI for QR-code enrollment.

    Args:
        secret: The base32-encoded secret.
        username: The user's display name.

    Returns:
        An otpauth:// URI string.
    """
    totp = get_totp(secret)
    return totp.provisioning_uri(name=username, issuer_name=TOTP_ISSUER_NAME)


def generate_qr_base64(uri: str) -> str:
    """Generate a QR-code PNG as a base64-encoded data URI.

    Args:
        uri: The otpauth:// URI to encode.

    Returns:
        A data URI string (``data:image/png;base64,...``) for embedding in HTML.
    """
    import base64

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
