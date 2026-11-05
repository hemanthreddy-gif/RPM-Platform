"""Explicit application authorization and transaction-local database identity."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.identity.schemas import Principal


def set_database_identity(session: Session, principal: Principal) -> None:
    """Set trusted identity only after JWT verification, for the current transaction."""
    session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": str(principal.user_id)},
    )
    session.execute(text("SELECT set_config('app.role', :role, true)"), {"role": principal.role})
    if principal.role == "patient":
        patient_id = session.execute(
            text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": principal.user_id}
        ).scalar_one_or_none()
        if patient_id is not None:
            session.execute(
                text("SELECT set_config('app.patient_id', :patient_id, true)"),
                {"patient_id": str(patient_id)},
            )


def require_patient_access(
    session: Session, principal: Principal, patient_id: UUID, purpose: str = "monitoring"
) -> None:
    if principal.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrators cannot read clinical data"
        )
    set_database_identity(session, principal)
    if principal.role == "patient":
        # Reassert the identity-scoped patient setting in this request transaction before
        # relying on RLS.  The equality check is explicit defense in depth for all routes.
        own_patient_id = session.execute(
            text("SELECT id FROM patients WHERE user_id = :user_id"),
            {"user_id": principal.user_id},
        ).scalar_one_or_none()
        if own_patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active relationship and consent for this patient",
            )
        session.execute(
            text("SELECT set_config('app.patient_id', :patient_id, true)"),
            {"patient_id": str(patient_id)},
        )
        return
    allowed = session.execute(
        text("SELECT can_access_patient(:patient_id, :purpose)"),
        {"patient_id": patient_id, "purpose": purpose},
    ).scalar_one()
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active relationship and consent for this patient",
        )
