"""The sole writer for append-only audit records."""

from ipaddress import ip_address
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def record(
    session: Session,
    *,
    actor_id: UUID | None,
    actor_role: str | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    patient_id: UUID | None = None,
    ip: str | None = None,
) -> None:
    """Append a minimal audit event in the caller's transaction."""
    try:
        audit_ip = str(ip_address(ip)) if ip is not None else None
    except ValueError:
        audit_ip = None
    session.execute(
        text("""
            SELECT record_audit_event(
              :actor_id, CAST(:actor_role AS user_role), :action, :resource_type,
              :resource_id, :patient_id, CAST(:ip AS inet)
            )
        """),
        {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "patient_id": patient_id,
            "ip": audit_ip,
        },
    )
