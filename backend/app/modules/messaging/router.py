"""Audited, consent-scoped messaging. It is never an emergency or alert channel."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.messaging.schemas import (
    MessageCreateRequest,
    MessageResponse,
    ThreadCreateRequest,
    ThreadResponse,
)
from app.modules.patients.authorization import require_patient_access, set_database_identity

NOTICE = "Messaging is not an emergency channel. Expected response time is configured for this synthetic demo; monitoring is not real-time."
router = APIRouter(prefix="/api/v1", tags=["messaging"])


def _thread(session: Session, thread_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text(
                "SELECT id, patient_id, physician_id, relationship_id, created_at FROM message_threads WHERE id = :id AND closed_at IS NULL"
            ),
            {"id": thread_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Message thread not found")
    return dict(row)


@router.post("/message-threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ThreadCreateRequest,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, payload.patient_id)
    relationship = session.execute(
        text("""SELECT id FROM care_relationships WHERE patient_id = :patient_id AND physician_id = :physician_id
      AND status = 'active' AND ended_at IS NULL AND consent_id IN (SELECT id FROM consents WHERE patient_id = :patient_id AND purpose = 'monitoring' AND revoked_at IS NULL)"""),
        {"patient_id": payload.patient_id, "physician_id": payload.physician_id},
    ).scalar_one_or_none()
    if relationship is None:
        raise HTTPException(
            status_code=403, detail="No active monitoring relationship and consent for this thread"
        )
    if principal.role == "physician":
        owned = session.execute(
            text("SELECT 1 FROM physicians WHERE id = :id AND user_id = :user_id"),
            {"id": payload.physician_id, "user_id": principal.user_id},
        ).scalar_one_or_none()
        if owned is None:
            raise HTTPException(
                status_code=403, detail="Physician may only create their own thread"
            )
    existing = (
        session.execute(
            text(
                "SELECT id, patient_id, physician_id, created_at FROM message_threads WHERE relationship_id = :relationship_id AND closed_at IS NULL"
            ),
            {"relationship_id": relationship},
        )
        .mappings()
        .one_or_none()
    )
    if existing is None:
        row = (
            session.execute(
                text("""INSERT INTO message_threads (id, patient_id, physician_id, relationship_id)
          VALUES (:id, :patient_id, :physician_id, :relationship_id) RETURNING id, patient_id, physician_id, created_at"""),
                {
                    "id": uuid4(),
                    "patient_id": payload.patient_id,
                    "physician_id": payload.physician_id,
                    "relationship_id": relationship,
                },
            )
            .mappings()
            .one()
        )
    else:
        row = existing
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="message_thread.create_or_read",
        resource_type="message_thread",
        resource_id=row["id"],
        patient_id=payload.patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return {**dict(row), "expected_response_notice": NOTICE}


@router.post(
    "/message-threads/{thread_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    thread_id: UUID,
    payload: MessageCreateRequest,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    thread = _thread(session, thread_id)
    require_patient_access(session, principal, UUID(str(thread["patient_id"])))
    physician_user = session.execute(
        text("SELECT user_id FROM physicians WHERE id = :id"), {"id": thread["physician_id"]}
    ).scalar_one()
    patient_user = session.execute(
        text("SELECT user_id FROM patients WHERE id = :id"), {"id": thread["patient_id"]}
    ).scalar_one()
    if principal.user_id not in {physician_user, patient_user}:
        raise HTTPException(status_code=403, detail="Thread participant required")
    recipient = patient_user if principal.user_id == physician_user else physician_user
    row = (
        session.execute(
            text("""INSERT INTO messages (id, thread_id, sender_id, recipient_id, body, kind)
      VALUES (:id, :thread_id, :sender_id, :recipient_id, :body, :kind) RETURNING id, sender_id, recipient_id, body, kind, sent_at, read_at"""),
            {
                "id": uuid4(),
                "thread_id": thread_id,
                "sender_id": principal.user_id,
                "recipient_id": recipient,
                "body": payload.body.strip(),
                "kind": payload.kind,
            },
        )
        .mappings()
        .one()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="message.send",
        resource_type="message",
        resource_id=row["id"],
        patient_id=UUID(str(thread["patient_id"])),
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return dict(row)


@router.get("/message-threads/{thread_id}/messages", response_model=list[MessageResponse])
def list_messages(
    thread_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    thread = _thread(session, thread_id)
    require_patient_access(session, principal, UUID(str(thread["patient_id"])))
    rows = (
        session.execute(
            text(
                "SELECT id, sender_id, recipient_id, body, kind, sent_at, read_at FROM messages WHERE thread_id = :id ORDER BY sent_at"
            ),
            {"id": thread_id},
        )
        .mappings()
        .all()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="message.list",
        resource_type="message_thread",
        resource_id=thread_id,
        patient_id=UUID(str(thread["patient_id"])),
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [dict(row) for row in rows]


@router.post("/message-threads/{thread_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    thread_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> None:
    thread = _thread(session, thread_id)
    require_patient_access(session, principal, UUID(str(thread["patient_id"])))
    session.execute(
        text(
            "UPDATE messages SET read_at = now() WHERE thread_id = :id AND recipient_id = :user_id AND read_at IS NULL"
        ),
        {"id": thread_id, "user_id": principal.user_id},
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="message.read_receipt",
        resource_type="message_thread",
        resource_id=thread_id,
        patient_id=UUID(str(thread["patient_id"])),
        ip=request.client.host if request.client else None,
    )
    session.commit()


@router.get("/messages/unread-count")
def unread_count(
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    set_database_identity(session, principal)
    count = session.execute(
        text("SELECT count(*) FROM messages WHERE recipient_id = :user_id AND read_at IS NULL"),
        {"user_id": principal.user_id},
    ).scalar_one()
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="message.unread_count",
        resource_type="message",
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return {"unread_count": count}
