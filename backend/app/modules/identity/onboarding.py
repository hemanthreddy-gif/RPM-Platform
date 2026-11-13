"""Trusted invitations; bootstrap credentials cannot authorize any patient-data access."""

from datetime import timedelta
from re import fullmatch
from secrets import compare_digest, token_urlsafe
from uuid import uuid4

import pyotp
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.audit.service import record
from app.modules.identity.schemas import (
    PhysicianEnrollmentResponse,
    PhysicianInvitationRequest,
    PhysicianInvitationResponse,
    PhysicianOnboardingComplete,
    PhysicianOnboardingStart,
    Principal,
    TokenResponse,
)
from app.modules.identity.service import _hash_token, _now, _secret_box, hash_password, issue_tokens


def authorize_invitation_manager(key: str | None, principal: Principal | None) -> None:
    if principal and principal.role == "admin" and principal.mfa:
        return
    expected = get_settings().trusted_admin_provisioning_key
    if key and expected and compare_digest(key, expected):
        return
    raise HTTPException(status_code=403, detail="Trusted administrative provisioning required")


def read_physician_profile(session: Session, principal: Principal) -> dict[str, object]:
    row = (
        session.execute(
            text("""SELECT id,
        COALESCE(display_name, 'Physician ' || registration_no) AS display_name,
        specialty, registration_no FROM physicians WHERE user_id = :id"""),
            {"id": principal.user_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Physician profile not found")
    return dict(row)


def create_invitation(
    session: Session,
    payload: PhysicianInvitationRequest,
    principal: Principal | None,
    ip: str | None,
    *,
    invitation_token: str | None = None,
) -> PhysicianInvitationResponse:
    # Private bootstrap operators may supply an environment-held random token. The public
    # request schema rejects this field and HTTP routes never pass it to the service.
    if invitation_token is not None and not fullmatch(r"[A-Za-z0-9_-]{64,256}", invitation_token):
        raise ValueError("Bootstrap invitation token must contain 64–256 URL-safe characters")
    # Keep the supplied address compatible with the existing exact-match sign-in flow.
    # Only invitation duplicate detection and serialization use a case-folded key.
    email = str(payload.email)
    email_key = email.lower()
    # Serialize reissues for one address so an operator cannot leave several valid invitations.
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"), {"email": email_key}
    )
    existing = session.execute(
        text("SELECT 1 FROM users WHERE lower(email) = :email"), {"email": email_key}
    ).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    session.execute(
        text("""UPDATE physician_invitations SET expires_at = now(),
             enrollment_expires_at = now(), password_hash = NULL, encrypted_secret = NULL
             WHERE lower(email) = :email AND completed_at IS NULL"""),
        {"email": email_key},
    )
    invitation_id, token = uuid4(), invitation_token or token_urlsafe(48)
    expires_at = _now() + timedelta(hours=48)
    session.execute(
        text("""INSERT INTO physician_invitations
          (id, email, display_name, registration_no, specialty, token_hash, expires_at, created_by)
          VALUES (:id, :email, :name, :registration, :specialty, :hash, :expiry, :actor)"""),
        {
            "id": invitation_id,
            "email": email,
            "name": payload.display_name.strip(),
            "registration": payload.registration_no.strip(),
            "specialty": payload.specialty,
            "hash": _hash_token(token),
            "expiry": expires_at,
            "actor": principal.user_id if principal else None,
        },
    )
    record(
        session,
        actor_id=principal.user_id if principal else None,
        actor_role=principal.role if principal else None,
        action="identity.physician_invitation_created",
        resource_type="physician_invitation",
        resource_id=invitation_id,
        ip=ip,
    )
    session.commit()
    return PhysicianInvitationResponse(invitation_token=token, expires_at=expires_at)


def start_onboarding(
    session: Session, payload: PhysicianOnboardingStart, ip: str | None
) -> PhysicianEnrollmentResponse:
    row = (
        session.execute(
            text("""SELECT id, email FROM physician_invitations
          WHERE token_hash = :hash AND expires_at > now()
          AND started_at IS NULL AND completed_at IS NULL FOR UPDATE"""),
            {"hash": _hash_token(payload.invitation_token)},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=400, detail="Invitation is invalid, expired or already used"
        )
    enrollment_token, secret = token_urlsafe(48), pyotp.random_base32()
    expiry = _now() + timedelta(minutes=15)
    session.execute(
        text("""UPDATE physician_invitations SET started_at = now(),
          enrollment_hash = :hash, enrollment_expires_at = :expiry,
          password_hash = :password, encrypted_secret = :secret WHERE id = :id"""),
        {
            "id": row["id"],
            "hash": _hash_token(enrollment_token),
            "expiry": expiry,
            "password": hash_password(payload.password),
            "secret": _secret_box().encrypt(secret.encode()).decode(),
        },
    )
    record(
        session,
        actor_id=None,
        actor_role=None,
        action="identity.physician_enrollment_started",
        resource_type="physician_invitation",
        resource_id=row["id"],
        ip=ip,
    )
    session.commit()
    return PhysicianEnrollmentResponse(
        enrollment_token=enrollment_token,
        provisioning_uri=pyotp.TOTP(secret).provisioning_uri(
            name=row["email"], issuer_name="RPM Platform (synthetic demo)"
        ),
        expires_at=expiry,
    )


def complete_onboarding(
    session: Session, payload: PhysicianOnboardingComplete, ip: str | None
) -> TokenResponse:
    row = (
        session.execute(
            text("""SELECT * FROM physician_invitations WHERE enrollment_hash = :hash
          AND enrollment_expires_at > now() AND expires_at > now()
          AND completed_at IS NULL AND failed_attempts < 5 FOR UPDATE"""),
            {"hash": _hash_token(payload.enrollment_token)},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=400, detail="Setup is invalid, expired or already completed"
        )
    secret = _secret_box().decrypt(row["encrypted_secret"].encode()).decode()
    if not pyotp.TOTP(secret).verify(payload.code, valid_window=1):
        session.execute(
            text(
                "UPDATE physician_invitations SET failed_attempts = failed_attempts + 1 "
                "WHERE id = :id"
            ),
            {"id": row["id"]},
        )
        record(
            session,
            actor_id=None,
            actor_role=None,
            action="identity.physician_enrollment_failed",
            resource_type="physician_invitation",
            resource_id=row["id"],
            ip=ip,
        )
        session.commit()
        raise HTTPException(
            status_code=400, detail="Code was not accepted; setup allows five attempts"
        )
    user_id, physician_id = uuid4(), uuid4()
    try:
        session.execute(
            text("""INSERT INTO users (id, email, role, password_hash, mfa_enabled)
              VALUES (:id, :email, 'physician', :password, true)"""),
            {"id": user_id, "email": row["email"], "password": row["password_hash"]},
        )
        session.execute(
            text("""INSERT INTO physicians (id, user_id, display_name, registration_no, specialty)
              VALUES (:id, :user_id, :name, :registration, :specialty)"""),
            {
                "id": physician_id,
                "user_id": user_id,
                "name": row["display_name"],
                "registration": row["registration_no"],
                "specialty": row["specialty"],
            },
        )
        session.execute(
            text("""INSERT INTO mfa_enrollments (id, user_id, encrypted_secret)
              VALUES (:id, :user_id, :secret)"""),
            {"id": uuid4(), "user_id": user_id, "secret": row["encrypted_secret"]},
        )
        session.execute(
            text("""UPDATE physician_invitations SET completed_at = now(), password_hash = NULL,
              encrypted_secret = NULL, enrollment_hash = NULL WHERE id = :id"""),
            {"id": row["id"]},
        )
        record(
            session,
            actor_id=user_id,
            actor_role="physician",
            action="identity.physician_onboarding_completed",
            resource_type="user",
            resource_id=user_id,
            ip=ip,
        )
        response = issue_tokens(session, user_id, "physician", True)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Account details are already in use; contact the demo administrator",
        ) from None
    return response
