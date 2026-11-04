"""Focused unit regression coverage for Phase 2 security primitives."""

from datetime import timedelta
from uuid import uuid4

import jwt
import pyotp
import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.modules.identity.service import _now, hash_password, parse_access_token, verify_password


def test_argon2_password_hash_round_trip_and_rejects_wrong_secret() -> None:
    password_hash = hash_password("synthetic-password-123")
    assert password_hash.startswith("$argon2")
    assert verify_password("synthetic-password-123", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_expired_access_token_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "patient",
            "mfa": False,
            "exp": _now() - timedelta(seconds=1),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException, match="Invalid or expired"):
        parse_access_token(token)


def test_totp_requires_the_current_code() -> None:
    totp = pyotp.TOTP(pyotp.random_base32())
    assert totp.verify(totp.now())
    assert not totp.verify("000000")
