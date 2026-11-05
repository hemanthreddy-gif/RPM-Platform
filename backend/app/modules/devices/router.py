"""Authorized device pairing/read APIs; device tokens never grant patient data reads."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.devices.schemas import (
    DeviceCreateRequest,
    DeviceCreateResponse,
    DeviceReadingRequest,
    DeviceResponse,
)
from app.modules.devices.service import authenticate_device, create_device, record_device_reading
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.patients.authorization import require_patient_access, set_database_identity

router = APIRouter(prefix="/api/v1", tags=["devices"])


def _patient_id(session: Session, principal: Principal) -> UUID:
    patient_id = session.execute(
        text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": principal.user_id}
    ).scalar_one_or_none()
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient_id


@router.post("/devices", response_model=DeviceCreateResponse, status_code=status.HTTP_201_CREATED)
def pair_device(
    payload: DeviceCreateRequest,
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    set_database_identity(session, principal)
    patient_id = _patient_id(session, principal)
    try:
        device_id, pairing_token = create_device(
            session,
            patient_id=patient_id,
            user_id=principal.user_id,
            kind=payload.kind,
            vendor=payload.vendor,
            serial=payload.serial,
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Device could not be paired") from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="device.pair",
        resource_type="device",
        resource_id=device_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return {"id": device_id, "pairing_token": pairing_token, "status": "active"}


@router.get("/patients/{patient_id}/devices", response_model=list[DeviceResponse])
def list_devices(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    require_patient_access(session, principal, patient_id)
    rows = (
        session.execute(
            text(
                "SELECT id, kind, vendor, serial, status, last_sync_at, last_received_at FROM devices WHERE patient_id = :patient_id ORDER BY paired_at DESC"
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
        action="device.list",
        resource_type="device",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [dict(row) for row in rows]


@router.post("/devices/{device_id}/readings", status_code=status.HTTP_201_CREATED)
def ingest_device_reading(
    device_id: UUID,
    payload: DeviceReadingRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    x_device_token: str = Header(alias="X-Device-Token", min_length=32, max_length=512),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    patient_id = authenticate_device(session, device_id=device_id, token=x_device_token)
    return record_device_reading(
        session,
        device_id=device_id,
        patient_id=patient_id,
        payload=payload,
        idempotency_key=idempotency_key,
        now=datetime.now(UTC),
    )
