"""Trusted onboarding, bounded MFA bootstrap and single-use invitation regression tests."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pyotp
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.modules.identity.onboarding import (
    authorize_invitation_manager,
    complete_onboarding,
    create_invitation,
    start_onboarding,
)
from app.modules.identity.router import login
from app.modules.identity.schemas import (
    LoginRequest,
    PhysicianInvitationRequest,
    PhysicianOnboardingComplete,
    PhysicianOnboardingStart,
    Principal,
)
from app.modules.identity.service import parse_access_token, verify_totp


def test_patient_or_unverified_admin_cannot_issue_invitation() -> None:
    for role, mfa in [("patient", False), ("physician", True), ("admin", False)]:
        principal = Principal(
            user_id=uuid4(),
            role=role,
            mfa=mfa,
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        with pytest.raises(HTTPException) as failure:
            authorize_invitation_manager(None, principal)
        assert failure.value.status_code == 403
    with pytest.raises(HTTPException):
        authorize_invitation_manager("incorrect-key", None)


def test_bootstrap_token_cannot_be_supplied_by_http_request() -> None:
    with pytest.raises(ValidationError):
        PhysicianInvitationRequest.model_validate(
            {
                "email": "synthetic@example.com",
                "display_name": "Synthetic Physician",
                "registration_no": "SYNTHETIC-BOOTSTRAP",
                "invitation_token": token_urlsafe(48),
            }
        )


@pytest.mark.parametrize("token", ["short", "!" * 64, "a" * 257])
def test_bootstrap_rejects_invalid_token_before_database_work(token: str) -> None:
    payload = PhysicianInvitationRequest(
        email="synthetic@example.com",
        display_name="Synthetic Physician",
        registration_no="SYNTHETIC-BOOTSTRAP",
    )
    with Session() as session, pytest.raises(ValueError, match="URL-safe"):
        create_invitation(session, payload, None, None, invitation_token=token)


def invitation(session: Session) -> str:
    suffix = uuid4()
    return create_invitation(
        session,
        PhysicianInvitationRequest(
            email=f"synthetic-{suffix}@example.com",
            display_name="Synthetic Physician",
            registration_no=f"SYN-{suffix}",
        ),
        None,
        None,
    ).invitation_token


def test_onboarding_issues_privileged_tokens_only_after_mfa_and_cannot_replay(
    integration_connection: Connection,
) -> None:
    session = Session(bind=integration_connection, join_transaction_mode="create_savepoint")
    token = invitation(session)
    enrollment = start_onboarding(
        session,
        PhysicianOnboardingStart(invitation_token=token, password="Synthetic-password-2026"),
        None,
    )
    assert (
        session.execute(
            text("SELECT 1 FROM physician_invitations WHERE token_hash = :t"), {"t": token}
        ).scalar_one_or_none()
        is None
    )
    assert (
        session.execute(
            text(
                "SELECT count(*) FROM users WHERE email = (SELECT email FROM physician_invitations "
                "WHERE enrollment_hash IS NOT NULL ORDER BY created_at DESC LIMIT 1)"
            )
        ).scalar_one()
        == 0
    )
    with pytest.raises(HTTPException):
        start_onboarding(
            session,
            PhysicianOnboardingStart(invitation_token=token, password="Synthetic-password-2026"),
            None,
        )
    secret = parse_qs(urlparse(enrollment.provisioning_uri).query)["secret"][0]
    request = PhysicianOnboardingComplete(
        enrollment_token=enrollment.enrollment_token, code=pyotp.TOTP(secret).now()
    )
    result = complete_onboarding(session, request, None)
    principal = parse_access_token(result.access_token)
    assert principal.role == "physician" and principal.mfa
    assert verify_totp(session, principal.user_id, request.code)
    with pytest.raises(HTTPException):
        complete_onboarding(session, request, None)
    assert (
        session.execute(
            text(
                "SELECT encrypted_secret FROM physician_invitations WHERE completed_at IS NOT NULL "
                "ORDER BY completed_at DESC LIMIT 1"
            )
        ).scalar_one()
        is None
    )
    session.close()


def test_expired_invitation_and_exhausted_mfa_bootstrap_are_rejected(
    integration_connection: Connection,
) -> None:
    session = Session(bind=integration_connection, join_transaction_mode="create_savepoint")
    token = invitation(session)
    session.execute(
        text("UPDATE physician_invitations SET expires_at = now() - interval '1 second'")
    )
    with pytest.raises(HTTPException):
        start_onboarding(
            session,
            PhysicianOnboardingStart(invitation_token=token, password="Synthetic-password-2026"),
            None,
        )
    token = invitation(session)
    enrollment = start_onboarding(
        session,
        PhysicianOnboardingStart(invitation_token=token, password="Synthetic-password-2026"),
        None,
    )
    secret = parse_qs(urlparse(enrollment.provisioning_uri).query)["secret"][0]
    totp = pyotp.TOTP(secret)
    invalid = next(f"{i:06}" for i in range(100) if not totp.verify(f"{i:06}", valid_window=1))
    for _ in range(5):
        with pytest.raises(HTTPException):
            complete_onboarding(
                session,
                PhysicianOnboardingComplete(
                    enrollment_token=enrollment.enrollment_token, code=invalid
                ),
                None,
            )
    with pytest.raises(HTTPException):
        complete_onboarding(
            session,
            PhysicianOnboardingComplete(
                enrollment_token=enrollment.enrollment_token, code=totp.now()
            ),
            None,
        )
    session.close()


def test_mixed_case_invitation_email_can_sign_in_after_onboarding(
    integration_connection: Connection,
) -> None:
    session = Session(bind=integration_connection, join_transaction_mode="create_savepoint")
    email = f"Synthetic.Physician.{uuid4()}@example.com"
    password = "Synthetic-password-2026"
    payload = PhysicianInvitationRequest(
        email=email,
        display_name="Synthetic Mixed Case Physician",
        registration_no=f"SYN-{uuid4()}",
    )
    bootstrap_token = token_urlsafe(48)
    token = create_invitation(
        session, payload, None, None, invitation_token=bootstrap_token
    ).invitation_token
    assert token == bootstrap_token
    enrollment = start_onboarding(
        session, PhysicianOnboardingStart(invitation_token=token, password=password), None
    )
    secret = parse_qs(urlparse(enrollment.provisioning_uri).query)["secret"][0]
    code = pyotp.TOTP(secret).now()
    setup = complete_onboarding(
        session,
        PhysicianOnboardingComplete(enrollment_token=enrollment.enrollment_token, code=code),
        None,
    )
    signed_in = login(LoginRequest(email=email, password=password, totp_code=code), session)
    assert (
        parse_access_token(signed_in.access_token).user_id
        == parse_access_token(setup.access_token).user_id
    )
    assert parse_access_token(signed_in.access_token).mfa
    # Case-insensitive duplicate protection still rejects a second invitation.
    with pytest.raises(HTTPException) as failure:
        create_invitation(session, payload.model_copy(update={"email": email.lower()}), None, None)
    assert failure.value.status_code == 409
    session.close()
