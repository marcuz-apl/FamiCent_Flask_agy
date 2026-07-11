"""AES-256-GCM encryption and decryption helpers.

Provides field-level encryption for sensitive database columns. Keys are derived
from the master password using scrypt (R20: n=16384, r=8, p=1).
"""
from __future__ import annotations

import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

logger = logging.getLogger(__name__)

# scrypt parameters per R20
_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LENGTH = 32  # 256 bits
_NONCE_LENGTH = 12  # 96 bits for AES-GCM


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from a password using scrypt.

    Args:
        password: The master password.
        salt: A unique salt (should be stored alongside encrypted data).

    Returns:
        A 32-byte derived key.
    """
    kdf = Scrypt(salt=salt, length=_KEY_LENGTH, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(password.encode("utf-8"))


def generate_salt() -> bytes:
    """Generate a random 16-byte salt for key derivation.

    Returns:
        A 16-byte random salt.
    """
    return os.urandom(16)


def encrypt(plaintext: str, key: bytes) -> bytes:
    """Encrypt a plaintext string with AES-256-GCM.

    The output format is: nonce (12 bytes) || ciphertext+tag.

    Args:
        plaintext: The string to encrypt.
        key: A 32-byte AES key (from `derive_key`).

    Returns:
        The nonce prepended to the ciphertext bytes.
    """
    nonce = os.urandom(_NONCE_LENGTH)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt(data: bytes, key: bytes) -> str:
    """Decrypt AES-256-GCM encrypted data back to a string.

    Expects the format produced by `encrypt`: nonce (12 bytes) || ciphertext+tag.

    Args:
        data: The encrypted bytes (nonce + ciphertext).
        key: The same 32-byte AES key used for encryption.

    Returns:
        The decrypted plaintext string.

    Raises:
        cryptography.exceptions.InvalidTag: If the key is wrong or data is tampered.
    """
    nonce = data[:_NONCE_LENGTH]
    ciphertext = data[_NONCE_LENGTH:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
