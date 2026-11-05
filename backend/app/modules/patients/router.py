"""Patient profile, consent, and trusted assignment API surface."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.patients.authorization import require_patient_access, set_database_identity

router = APIRouter(prefix="/api/v1", tags=["patients"])


class ConsentRequest(BaseModel):
    purpose: str = Field(pattern="^(monitoring|ai_processing|sharing)$")
    version: str = Field(min_length=1, max_length=64)


class AssignmentRequest(BaseModel):
    patient_id: UUID
    physician_id: UUID
    consent_id: UUID


class WorklistItem(BaseModel):
    """A deliberately small, authorized physician worklist projection."""

    id: UUID
    display_name: str
    timezone: str
    has_hypertension: bool
    active_alert_severity: str | None
    latest_observation_at: datetime | None


@router.get("/patients/me")
def get_me(
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    set_database_identity(session, principal)
    row = (
        session.execute(
            text(
                "SELECT id, display_name, timezone, has_hypertension FROM patients WHERE user_id = :user_id"
            ),
            {"user_id": principal.user_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found"
        )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="patient.read_self",
        resource_type="patient",
        resource_id=row["id"],
        patient_id=row["id"],
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return dict(row)


@router.get("/patients/{patient_id}")
def get_patient(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    row = (
        session.execute(
            text(
                "SELECT id, display_name, timezone, has_hypertension FROM patients WHERE id = :id"
            ),
            {"id": patient_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found"
        )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="patient.read",
        resource_type="patient",
        resource_id=patient_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return dict(row)


@router.get("/physician/patients", response_model=list[WorklistItem])
def physician_worklist(
    request: Request,
    query: str = "",
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    """List only patients with an active monitoring relationship and consent.

    The query is intentionally a display-only projection.  It does not infer a clinical
    priority: the server returns the persisted alert severity and the latest accepted data time.
    RLS still applies to ``patients`` and each returned record is re-authorized and audited.
    """
    set_database_identity(session, principal)
    needle = query.strip()
    if len(needle) > 100:
        raise HTTPException(status_code=422, detail="Search query is too long")
    rows = (
        session.execute(
            text(
                """SELECT p.id, p.display_name, p.timezone, p.has_hypertension,
                  (SELECT a.severity::text FROM alerts a
                    WHERE a.patient_id = p.id
                      AND a.status IN ('open', 'notified', 'escalated')
                    ORDER BY CASE a.severity WHEN 'urgent' THEN 3 WHEN 'attention' THEN 2 ELSE 1 END DESC,
                             a.created_at DESC LIMIT 1) AS active_alert_severity,
                  (SELECT max(o.measured_at) FROM observations o WHERE o.patient_id = p.id) AS latest_observation_at
                  FROM patients p
                  JOIN care_relationships r ON r.patient_id = p.id AND r.status = 'active' AND r.ended_at IS NULL
                  JOIN physicians ph ON ph.id = r.physician_id AND ph.user_id = :user_id
                  JOIN consents c ON c.id = r.consent_id AND c.patient_id = p.id
                    AND c.purpose = 'monitoring' AND c.revoked_at IS NULL
                  WHERE (:query = '' OR p.display_name ILIKE :pattern)
                  ORDER BY CASE (SELECT a.severity::text FROM alerts a
                    WHERE a.patient_id = p.id AND a.status IN ('open', 'notified', 'escalated')
                    ORDER BY CASE a.severity WHEN 'urgent' THEN 3 WHEN 'attention' THEN 2 ELSE 1 END DESC,
                             a.created_at DESC LIMIT 1)
                    WHEN 'urgent' THEN 3 WHEN 'attention' THEN 2 WHEN 'informational' THEN 1 ELSE 0 END DESC,
                  latest_observation_at ASC NULLS FIRST, p.display_name ASC LIMIT 100"""
            ),
            {"user_id": principal.user_id, "query": needle, "pattern": f"%{needle}%"},
        )
        .mappings()
        .all()
    )
    response: list[dict[str, object]] = []
    for row in rows:
        require_patient_access(session, principal, row["id"])
        record(
            session,
            actor_id=principal.user_id,
            actor_role=principal.role,
            action="patient.worklist.read",
            resource_type="patient",
            resource_id=row["id"],
            patient_id=row["id"],
            ip=request.client.host if request.client else None,
        )
        response.append(dict(row))
    session.commit()
    return response


@router.get("/consents")
def list_consents(
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    set_database_identity(session, principal)
    patient_id = session.execute(
        text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": principal.user_id}
    ).scalar_one()
    rows = (
        session.execute(
            text(
                "SELECT id, purpose, version, granted_at, revoked_at FROM consents WHERE patient_id = :patient_id ORDER BY granted_at DESC"
            ),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="consent.list",
        resource_type="consent",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [dict(row) for row in rows]


@router.post("/consents", status_code=status.HTTP_201_CREATED)
def grant_consent(
    payload: ConsentRequest,
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    set_database_identity(session, principal)
    patient_id = session.execute(
        text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": principal.user_id}
    ).scalar_one()
    consent_id = uuid4()
    session.execute(
        text(
            "INSERT INTO consents (id, patient_id, purpose, version, granted_at) VALUES (:id, :patient_id, :purpose, :version, :granted_at)"
        ),
        {
            "id": consent_id,
            "patient_id": patient_id,
            "purpose": payload.purpose,
            "version": payload.version,
            "granted_at": datetime.now(UTC),
        },
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="consent.grant",
        resource_type="consent",
        resource_id=consent_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return {"id": str(consent_id)}


@router.post("/consents/{consent_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_consent(
    consent_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> None:
    set_database_identity(session, principal)
    patient_id = session.execute(
        text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": principal.user_id}
    ).scalar_one()
    updated = session.execute(
        text(
            "UPDATE consents SET revoked_at = now() WHERE id = :id AND patient_id = :patient_id "
            "AND revoked_at IS NULL RETURNING id"
        ),
        {"id": consent_id, "patient_id": patient_id},
    ).scalar_one_or_none()
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Active consent not found"
        )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="consent.revoke",
        resource_type="consent",
        resource_id=consent_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()


@router.post("/admin/assignments", status_code=status.HTTP_201_CREATED)
def assign_physician(
    payload: AssignmentRequest,
    request: Request,
    principal: Principal = Depends(require_role("admin")),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    consent = session.execute(
        text(
            "SELECT patient_id FROM consents WHERE id = :id AND purpose = 'monitoring' AND revoked_at IS NULL"
        ),
        {"id": payload.consent_id},
    ).scalar_one_or_none()
    physician = session.execute(
        text("SELECT id FROM physicians WHERE id = :id"), {"id": payload.physician_id}
    ).scalar_one_or_none()
    if consent != payload.patient_id or physician is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Active monitoring consent and physician are required",
        )
    relationship_id = uuid4()
    session.execute(
        text(
            "INSERT INTO care_relationships (id, patient_id, physician_id, consent_id, status, started_at) VALUES (:id, :patient_id, :physician_id, :consent_id, 'active', now())"
        ),
        {
            "id": relationship_id,
            "patient_id": payload.patient_id,
            "physician_id": payload.physician_id,
            "consent_id": payload.consent_id,
        },
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="relationship.assign",
        resource_type="care_relationship",
        resource_id=relationship_id,
        patient_id=payload.patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return {"id": str(relationship_id)}
