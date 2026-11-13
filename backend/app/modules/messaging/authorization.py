"""Authorize the exact conversation participants and its current monitoring consent."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.identity.schemas import Principal
from app.modules.patients.authorization import require_patient_access, set_database_identity


def require_thread(session: Session, principal: Principal, thread_id: UUID) -> dict[str, object]:
    set_database_identity(session, principal)
    row = (
        session.execute(
            text("""SELECT t.id, t.patient_id, t.physician_id, t.relationship_id, t.created_at
        FROM message_threads t
        JOIN care_relationships r ON r.id = t.relationship_id
          AND r.patient_id = t.patient_id AND r.physician_id = t.physician_id
        JOIN consents c ON c.id = r.consent_id AND c.patient_id = t.patient_id
        JOIN patients p ON p.id = t.patient_id
        JOIN physicians ph ON ph.id = t.physician_id
        WHERE t.id = :id AND t.closed_at IS NULL
          AND r.status = 'active' AND r.ended_at IS NULL
          AND c.purpose = 'monitoring' AND c.revoked_at IS NULL
          AND ((:role = 'patient' AND p.user_id = :actor)
            OR (:role = 'physician' AND ph.user_id = :actor))"""),
            {"id": thread_id, "actor": principal.user_id, "role": principal.role},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Active conversation not found")
    require_patient_access(session, principal, row["patient_id"])
    return dict(row)
