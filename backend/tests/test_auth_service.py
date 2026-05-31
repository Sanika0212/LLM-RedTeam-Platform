"""Tests for auth_service — password hashing and JWT tokens."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_hash_password_produces_bcrypt_hash():
    hashed = hash_password("mypassword")
    assert hashed.startswith("$2b$")


def test_hash_password_unique_salts():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # different salts


def test_verify_password_correct():
    hashed = hash_password("correct")
    assert verify_password("correct", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_verify_password_malformed():
    assert verify_password("anything", "no-dollar-sign") is False


def test_verify_password_legacy_sha256():
    """Legacy SHA-256 hashes should still verify correctly."""
    import hashlib
    salt = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    pw_hash = hashlib.sha256(f"{salt}:legacypass".encode()).hexdigest()
    legacy_hash = f"{salt}${pw_hash}"
    assert verify_password("legacypass", legacy_hash) is True
    assert verify_password("wrongpass", legacy_hash) is False


def test_create_and_decode_token():
    # JWT spec requires 'sub' to be a string
    token = create_access_token({"sub": "42", "role": "admin"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_decode_invalid_token():
    result = decode_token("not.a.valid.token")
    assert result is None


def test_decode_tampered_token():
    token = create_access_token({"sub": 1})
    tampered = token[:-5] + "XXXXX"
    assert decode_token(tampered) is None
