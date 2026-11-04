"""Identity primitives; passwords and bearer secrets never leave this module."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid4

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.schemas import Principal, TokenResponse

PASSWORDS = PasswordHasher()
LOCKOUT_FAILURES = 5
LOCKOUT_FOR = timedelta(minutes=15)


def _hash_token(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _secret_box() -> Fernet:
    return Fernet(get_settings().mfa_encryption_key.encode())


def hash_password(password: str) -> str:
    return PASSWORDS.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return PASSWORDS.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def issue_tokens(session: Session, user_id: UUID, role: str, mfa: bool) -> TokenResponse:
    settings = get_settings()
    now = _now()
    access_expiry = now + timedelta(minutes=settings.access_token_minutes)
    access = jwt.encode(
        {"sub": str(user_id), "role": role, "mfa": mfa, "exp": access_expiry, "iat": now},
        settings.jwt_secret,
        algorithm="HS256",
    )
    refresh = token_urlsafe(48)
    session.execute(
        text("""INSERT INTO identity_tokens (id, user_id, token_type, token_hash, expires_at)
                VALUES (:id, :user_id, 'refresh', :token_hash, :expires_at)"""),
        {
            "id": uuid4(),
            "user_id": user_id,
            "token_hash": _hash_token(refresh),
            "expires_at": now + timedelta(days=settings.refresh_token_days),
        },
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


def parse_access_token(token: str) -> Principal:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return Principal(
            user_id=UUID(payload["sub"]),
            role=payload["role"],
            mfa=bool(payload["mfa"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token"
        ) from exc


def verify_totp(session: Session, user_id: UUID, code: str) -> bool:
    encrypted = session.execute(
        text("SELECT encrypted_secret FROM mfa_enrollments WHERE user_id = :id"), {"id": user_id}
    ).scalar_one_or_none()
    return bool(
        encrypted
        and pyotp.TOTP(_secret_box().decrypt(encrypted.encode()).decode()).verify(
            code, valid_window=1
        )
    )


def create_mfa_enrollment(session: Session, user_id: UUID, email: str) -> str:
    """Replace the unverified enrollment secret; verification enables MFA on the user."""
    secret = pyotp.random_base32()
    session.execute(
        text("""INSERT INTO mfa_enrollments (id, user_id, encrypted_secret)
                VALUES (:id, :user_id, :secret)
                ON CONFLICT (user_id) DO UPDATE SET encrypted_secret = EXCLUDED.encrypted_secret, enrolled_at = now()"""),
        {
            "id": uuid4(),
            "user_id": user_id,
            "secret": _secret_box().encrypt(secret.encode()).decode(),
        },
    )
    return pyotp.TOTP(secret).provisioning_uri(
        name=email, issuer_name="RPM Platform (synthetic demo)"
    )
