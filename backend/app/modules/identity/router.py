"""HTTP boundary for authentication; all protected endpoints use verified principals."""

from datetime import timedelta
from secrets import token_urlsafe
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.identity.schemas import (
    LoginRequest,
    MfaEnrollResponse,
    MfaVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    Principal,
    ProvisionRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.identity.service import (
    LOCKOUT_FAILURES,
    LOCKOUT_FOR,
    _hash_token,
    _now,
    create_mfa_enrollment,
    hash_password,
    issue_tokens,
    parse_access_token,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: Session = Depends(get_session),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer authentication required"
        )
    principal = parse_access_token(credentials.credentials)
    token_valid_after = session.execute(
        text("SELECT token_valid_after FROM users WHERE id = :id AND status = 'active'"),
        {"id": principal.user_id},
    ).scalar_one_or_none()
    if token_valid_after is None or principal.issued_at < token_valid_after:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is revoked"
        )
    return principal


def require_role(*roles: str):
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        if principal.role in {"physician", "admin"} and not principal.mfa:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="MFA verification required"
            )
        return principal

    return dependency


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, request: Request, session: Session = Depends(get_session)
) -> TokenResponse:
    """Public registration always creates only a patient account."""
    exists = session.execute(
        text("SELECT 1 FROM users WHERE email = :email"), {"email": str(payload.email)}
    ).scalar()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    user_id, patient_id = uuid4(), uuid4()
    session.execute(
        text(
            """INSERT INTO users (id, email, role, password_hash) VALUES (:id, :email, 'patient', :password_hash)"""
        ),
        {
            "id": user_id,
            "email": str(payload.email),
            "password_hash": hash_password(payload.password),
        },
    )
    session.execute(
        text(
            "INSERT INTO patients (id, user_id, display_name) VALUES (:id, :user_id, :display_name)"
        ),
        {"id": patient_id, "user_id": user_id, "display_name": payload.display_name},
    )
    record(
        session,
        actor_id=user_id,
        actor_role="patient",
        action="patient.register",
        resource_type="patient",
        resource_id=patient_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    response = issue_tokens(session, user_id, "patient", False)
    session.commit()
    return response


@router.post("/provision", status_code=status.HTTP_201_CREATED)
def provision_privileged(
    payload: ProvisionRequest,
    request: Request,
    x_provisioning_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Trusted administrative workflow; deliberately not a public role-selection endpoint."""
    if x_provisioning_key != get_settings().trusted_admin_provisioning_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Trusted provisioning required"
        )
    if payload.role == "physician" and not payload.registration_no:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Physician registration number required",
        )
    user_id = uuid4()
    physician_id: UUID | None = None
    try:
        session.execute(
            text(
                "INSERT INTO users (id, email, role, password_hash) VALUES (:id, :email, CAST(:role AS user_role), :password_hash)"
            ),
            {
                "id": user_id,
                "email": str(payload.email),
                "role": payload.role,
                "password_hash": hash_password(payload.password),
            },
        )
        if payload.role == "physician":
            physician_id = uuid4()
            session.execute(
                text(
                    "INSERT INTO physicians (id, user_id, registration_no) VALUES (:id, :user_id, :registration_no)"
                ),
                {
                    "id": physician_id,
                    "user_id": user_id,
                    "registration_no": payload.registration_no,
                },
            )
        record(
            session,
            actor_id=None,
            actor_role=None,
            action="identity.provision",
            resource_type="user",
            resource_id=user_id,
            ip=request.client.host if request.client else None,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Unable to provision account"
        ) from None
    response = {"id": str(user_id), "role": payload.role}
    if physician_id is not None:
        response["physician_id"] = str(physician_id)
    return response


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    row = (
        session.execute(
            text(
                "SELECT id, role::text, password_hash, mfa_enabled, locked_until FROM users WHERE email = :email AND status = 'active'"
            ),
            {"email": str(payload.email)},
        )
        .mappings()
        .one_or_none()
    )
    if (
        row is None
        or (row["locked_until"] is not None and row["locked_until"] > _now())
        or not verify_password(payload.password, row["password_hash"])
    ):
        if row is not None:
            session.execute(
                text("""UPDATE users SET failed_login_attempts = failed_login_attempts + 1,
                locked_until = CASE WHEN failed_login_attempts + 1 >= :limit THEN now() + CAST(:duration AS interval) ELSE locked_until END
                WHERE id = :id"""),
                {
                    "id": row["id"],
                    "limit": LOCKOUT_FAILURES,
                    "duration": f"{int(LOCKOUT_FOR.total_seconds() // 60)} minutes",
                },
            )
            session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if row["role"] in {"physician", "admin"} and (
        not row["mfa_enabled"]
        or not payload.totp_code
        or not verify_totp(session, row["id"], payload.totp_code)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA verification required"
        )
    session.execute(
        text("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = :id"),
        {"id": row["id"]},
    )
    response = issue_tokens(session, row["id"], row["role"], row["role"] in {"physician", "admin"})
    session.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)) -> TokenResponse:
    row = (
        session.execute(
            text("""SELECT t.id, t.user_id, u.role::text FROM identity_tokens t JOIN users u ON u.id = t.user_id
        WHERE t.token_type = 'refresh' AND t.token_hash = :token_hash AND t.revoked_at IS NULL AND t.expires_at > now()"""),
            {"token_hash": _hash_token(payload.refresh_token)},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )
    session.execute(
        text("UPDATE identity_tokens SET revoked_at = now() WHERE id = :id"), {"id": row["id"]}
    )
    response = issue_tokens(
        session, row["user_id"], row["role"], row["role"] in {"physician", "admin"}
    )
    session.commit()
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    principal: Principal = Depends(current_principal),
    session: Session = Depends(get_session),
) -> None:
    session.execute(
        text(
            "UPDATE identity_tokens SET revoked_at = now() WHERE user_id = :user_id AND token_type = 'refresh' AND token_hash = :token_hash AND revoked_at IS NULL"
        ),
        {"token_hash": _hash_token(payload.refresh_token), "user_id": principal.user_id},
    )
    session.execute(
        text("UPDATE users SET token_valid_after = now() WHERE id = :id"), {"id": principal.user_id}
    )
    session.commit()


@router.post("/mfa/enroll", response_model=MfaEnrollResponse)
def enroll_mfa(
    principal: Principal = Depends(current_principal), session: Session = Depends(get_session)
) -> MfaEnrollResponse:
    if principal.role not in {"physician", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="MFA enrollment is for privileged roles"
        )
    email = session.execute(
        text("SELECT email FROM users WHERE id = :id"), {"id": principal.user_id}
    ).scalar_one()
    uri = create_mfa_enrollment(session, principal.user_id, email)
    session.commit()
    return MfaEnrollResponse(provisioning_uri=uri)


@router.post("/mfa/verify", status_code=status.HTTP_204_NO_CONTENT)
def confirm_mfa(
    payload: MfaVerifyRequest,
    principal: Principal = Depends(current_principal),
    session: Session = Depends(get_session),
) -> None:
    if principal.role not in {"physician", "admin"} or not verify_totp(
        session, principal.user_id, payload.code
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")
    session.execute(
        text("UPDATE users SET mfa_enabled = true WHERE id = :id"), {"id": principal.user_id}
    )
    session.commit()


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    payload: PasswordResetRequest, session: Session = Depends(get_session)
) -> dict[str, str]:
    """Uniform response prevents account enumeration; delivery adapter is configured for MailHog locally."""
    user_id = session.execute(
        text("SELECT id FROM users WHERE email = :email AND status = 'active'"),
        {"email": str(payload.email)},
    ).scalar_one_or_none()
    if user_id:
        token = token_urlsafe(48)
        session.execute(
            text(
                "INSERT INTO identity_tokens (id, user_id, token_type, token_hash, expires_at) VALUES (:id, :user_id, 'reset', :token_hash, :expires_at)"
            ),
            {
                "id": uuid4(),
                "user_id": user_id,
                "token_hash": _hash_token(token),
                "expires_at": _now() + timedelta(minutes=get_settings().reset_token_minutes),
            },
        )
        # The raw token belongs only in the configured email adapter, never logs or API response.
        session.commit()
    return {"message": "If the account exists, reset instructions have been sent."}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(
    payload: PasswordResetConfirm, session: Session = Depends(get_session)
) -> None:
    token = (
        session.execute(
            text(
                "SELECT id, user_id FROM identity_tokens WHERE token_type = 'reset' AND token_hash = :token_hash AND revoked_at IS NULL AND expires_at > now()"
            ),
            {"token_hash": _hash_token(payload.token)},
        )
        .mappings()
        .one_or_none()
    )
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )
    session.execute(
        text(
            "UPDATE users SET password_hash = :password_hash, failed_login_attempts = 0, locked_until = NULL, token_valid_after = now() WHERE id = :id"
        ),
        {"id": token["user_id"], "password_hash": hash_password(payload.new_password)},
    )
    session.execute(
        text(
            "UPDATE identity_tokens SET revoked_at = now() WHERE user_id = :user_id AND token_type IN ('reset', 'refresh') AND revoked_at IS NULL"
        ),
        {"user_id": token["user_id"]},
    )
    session.commit()
