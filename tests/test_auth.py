"""Unit tests for the auth module (manager + mfa)."""
from __future__ import annotations

import pytest

from famicent.auth.manager import hash_password, is_session_expired, verify_password
from famicent.auth.mfa import (
    generate_qr_base64,
    generate_secret,
    get_provisioning_uri,
    verify_code,
)


# ---------------------------------------------------------------------------
# Password hashing (R18)
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_returns_string(self):
        result = hash_password("securepass")
        assert isinstance(result, str)
        assert len(result) > 20

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password(hashed, "mypassword") is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password(hashed, "wrongpassword") is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # Argon2 includes a random salt


# ---------------------------------------------------------------------------
# Session expiry (R23)
# ---------------------------------------------------------------------------

class TestSessionExpiry:
    def test_none_activity_is_expired(self):
        assert is_session_expired(None) is True

    def test_recent_activity_not_expired(self):
        from datetime import datetime
        assert is_session_expired(datetime.utcnow()) is False

    def test_old_activity_is_expired(self):
        from datetime import datetime, timedelta
        old = datetime.utcnow() - timedelta(seconds=600)
        assert is_session_expired(old) is True


# ---------------------------------------------------------------------------
# MFA / TOTP (R21)
# ---------------------------------------------------------------------------

class TestMFA:
    def test_generate_secret_returns_base32(self):
        secret = generate_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16

    def test_provisioning_uri_format(self):
        secret = generate_secret()
        uri = get_provisioning_uri(secret, "testuser")
        assert "otpauth://totp/" in uri
        assert "testuser" in uri
        assert "FamiCent" in uri

    def test_verify_code_with_current_code(self):
        import pyotp
        secret = generate_secret()
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        current_code = totp.now()
        assert verify_code(secret, current_code) is True

    def test_verify_code_with_wrong_code(self):
        secret = generate_secret()
        assert verify_code(secret, "000000") is False

    def test_qr_base64_starts_with_data_uri(self):
        secret = generate_secret()
        uri = get_provisioning_uri(secret, "testuser")
        qr = generate_qr_base64(uri)
        assert qr.startswith("data:image/png;base64,")
