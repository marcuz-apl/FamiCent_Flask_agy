"""Unit tests for the database crypto layer (AES-256-GCM)."""
from __future__ import annotations

import os

import pytest
from cryptography.exceptions import InvalidTag

from famicent.db.crypto import decrypt, derive_key, encrypt, generate_salt


class TestCrypto:
    """Tests for AES-256-GCM encryption / decryption (R19, R20)."""

    def _make_key(self, password: str = "testpassword") -> bytes:
        salt = generate_salt()
        return derive_key(password, salt)

    def test_generate_salt_is_16_bytes(self):
        salt = generate_salt()
        assert len(salt) == 16

    def test_derive_key_is_32_bytes(self):
        salt = generate_salt()
        key = derive_key("password", salt)
        assert len(key) == 32

    def test_encrypt_returns_bytes(self):
        key = self._make_key()
        result = encrypt("hello world", key)
        assert isinstance(result, bytes)

    def test_encrypt_decrypt_roundtrip(self):
        key = self._make_key()
        plaintext = "secret account number 1234"
        ciphertext = encrypt(plaintext, key)
        recovered = decrypt(ciphertext, key)
        assert recovered == plaintext

    def test_different_ciphertexts_for_same_plaintext(self):
        """Each call must produce a unique nonce (random IV)."""
        key = self._make_key()
        c1 = encrypt("same text", key)
        c2 = encrypt("same text", key)
        assert c1 != c2

    def test_wrong_key_raises_invalid_tag(self):
        key1 = self._make_key("password1")
        key2 = self._make_key("password2")
        ciphertext = encrypt("secret", key1)
        with pytest.raises(InvalidTag):
            decrypt(ciphertext, key2)

    def test_tampered_ciphertext_raises_invalid_tag(self):
        key = self._make_key()
        ciphertext = bytearray(encrypt("secret", key))
        ciphertext[-1] ^= 0xFF  # flip last byte
        with pytest.raises(InvalidTag):
            decrypt(bytes(ciphertext), key)

    def test_unicode_plaintext(self):
        key = self._make_key()
        text = "Ünïcödé tëxt 日本語"
        assert decrypt(encrypt(text, key), key) == text
