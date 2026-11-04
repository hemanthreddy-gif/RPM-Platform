"""Audited physician alert lifecycle endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.alerts.service import transition
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.patients.authorization import require_patient_access

router = APIRouter(prefix="/api/v1", tags=["alerts"])


def _alert_patient(session: Session, alert_id: UUID) -> UUID:
    patient_id = session.execute(
        text("SELECT patient_id FROM alerts WHERE id = :id"), {"id": alert_id}
    ).scalar_one_or_none()
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return patient_id


@router.get("/alerts")
def list_alerts(
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    # RLS filters the query after the request's trusted identity has been set by this access check.
    if principal.role == "patient":
        patient_id = session.execute(
            text("SELECT id FROM patients WHERE user_id = :id"), {"id": principal.user_id}
        ).scalar_one()
    else:
        patient_id = None
    if patient_id is not None:
        require_patient_access(session, principal, patient_id)
    rows = (
        session.execute(
            text(
                "SELECT id, patient_id, rule_code, rule_version, severity::text, status::text, created_at FROM alerts ORDER BY created_at DESC LIMIT 100"
            )
        )
        .mappings()
        .all()
    )
    for row in rows:
        require_patient_access(session, principal, row["patient_id"])
        record(
            session,
            actor_id=principal.user_id,
            actor_role=principal.role,
            action="alert.list",
            resource_type="alert",
            resource_id=row["id"],
            patient_id=row["patient_id"],
            ip=request.client.host if request.client else None,
        )
    session.commit()
    return [dict(row) for row in rows]


def _transition(
    alert_id: UUID, action: str, request: Request, principal: Principal, session: Session
) -> None:
    patient_id = _alert_patient(session, alert_id)
    require_patient_access(session, principal, patient_id)
    try:
        transition(session, alert_id=alert_id, actor_id=principal.user_id, action=action)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action=f"alert.{action}",
        resource_type="alert",
        resource_id=alert_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()


@router.post("/alerts/{alert_id}/acknowledge", status_code=204)
def acknowledge(
    alert_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> None:
    _transition(alert_id, "acknowledge", request, principal, session)


@router.post("/alerts/{alert_id}/resolve", status_code=204)
def resolve(
    alert_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> None:
    _transition(alert_id, "resolve", request, principal, session)
