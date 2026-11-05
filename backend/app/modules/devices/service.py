"""Paired-device token and ingestion helpers; no clinical decision lives here."""

from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from json import dumps
from secrets import token_urlsafe
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clinical_rules.models import Observation as RuleObservation
from app.core.correlation import current_request_id
from app.modules.alerts.service import evaluate_and_persist
from app.modules.audit.service import record
from app.modules.devices.schemas import DeviceReadingRequest
from app.modules.observations.schemas import ObservationCreate, canonical_value


def _hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def create_device(
    session: Session, *, patient_id: UUID, user_id: UUID, kind: str, vendor: str, serial: str | None
) -> tuple[UUID, str]:
    token = token_urlsafe(32)
    device_id = uuid4()
    session.execute(
        text("""INSERT INTO devices (id, patient_id, kind, vendor, serial, status, pairing_token_hash, paired_at, created_by)
          VALUES (:id, :patient_id, :kind, :vendor, :serial, 'active', :token_hash, now(), :created_by)"""),
        {
            "id": device_id,
            "patient_id": patient_id,
            "kind": kind,
            "vendor": vendor,
            "serial": serial,
            "token_hash": _hash(token),
            "created_by": user_id,
        },
    )
    return device_id, token


def authenticate_device(session: Session, *, device_id: UUID, token: str) -> UUID:
    """Authenticate a token while restricted to the URL's device row, then elevate only server context."""
    session.execute(text("SELECT set_config('app.role', 'device', true)"))
    session.execute(text("SELECT set_config('app.device_id', :id, true)"), {"id": str(device_id)})
    row = (
        session.execute(
            text("SELECT patient_id, pairing_token_hash, status FROM devices WHERE id = :id"),
            {"id": device_id},
        )
        .mappings()
        .one_or_none()
    )
    if (
        row is None
        or row["status"] != "active"
        or not compare_digest(str(row["pairing_token_hash"]), _hash(token))
    ):
        raise HTTPException(status_code=401, detail="Invalid device credentials")
    session.execute(text("SELECT set_config('app.role', 'worker', true)"))
    return row["patient_id"]


def record_device_reading(
    session: Session,
    *,
    device_id: UUID,
    patient_id: UUID,
    payload: DeviceReadingRequest,
    idempotency_key: str,
    now: datetime,
) -> dict[str, object]:
    """Use the manual observation schema/conversion and the same synchronous alert evaluator."""
    manual_shape = ObservationCreate(**payload.model_dump(), confirm_unusual=False)
    request_hash = sha256(
        dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    existing = (
        session.execute(
            text("""SELECT request_hash, response_body FROM idempotency_records
      WHERE actor_or_device_id = :actor AND operation = 'device.reading.create' AND key = :key"""),
            {"actor": device_id, "key": idempotency_key},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        if existing["request_hash"] != request_hash:
            raise HTTPException(
                status_code=409, detail="Idempotency key was reused with a different reading"
            )
        return existing["response_body"]
    if manual_shape.measured_at.tzinfo is None or manual_shape.measured_at.astimezone(UTC) > now:
        raise HTTPException(
            status_code=422, detail="measured_at must be a non-future UTC-offset time"
        )
    value, unit = canonical_value(manual_shape)
    observation_id = uuid4()
    row = (
        session.execute(
            text("""INSERT INTO observations
      (id, patient_id, type, value_num, components, unit, original_value, original_unit, measured_at, source, device_id, context, idempotency_key)
      VALUES (:id, :patient_id, CAST(:type AS observation_type), :value, CAST(:components AS jsonb), :unit, :original_value, :original_unit, :measured_at, 'device', :device_id, CAST(:context AS jsonb), :key)
      RETURNING id, patient_id, type::text, value_num AS value, unit, original_value, original_unit, components, measured_at, recorded_at, source::text, quality_flag, supersedes_id"""),
            {
                "id": observation_id,
                "patient_id": patient_id,
                "type": payload.type,
                "value": value,
                "components": dumps(payload.components, default=str),
                "unit": unit,
                "original_value": payload.value,
                "original_unit": payload.unit,
                "measured_at": payload.measured_at.astimezone(UTC),
                "device_id": device_id,
                "context": dumps(payload.context),
                "key": idempotency_key,
            },
        )
        .mappings()
        .one()
    )
    response = dict(row)
    for key in ("id", "patient_id", "supersedes_id"):
        if response.get(key) is not None:
            response[key] = str(response[key])
    response["alerts"] = evaluate_and_persist(
        session,
        patient_id=patient_id,
        observation_id=observation_id,
        observation=RuleObservation(
            type=payload.type,
            value=value,
            components=payload.components,
            context=payload.context,
            measured_at=payload.measured_at,
        ),
        evaluation_time=now,
    )
    session.execute(
        text("""INSERT INTO idempotency_records (id, actor_or_device_id, operation, key, request_hash, response_status, response_body)
      VALUES (:id, :actor, 'device.reading.create', :key, :request_hash, 201, CAST(:body AS jsonb))"""),
        {
            "id": uuid4(),
            "actor": device_id,
            "key": idempotency_key,
            "request_hash": request_hash,
            "body": dumps(response, default=str),
        },
    )
    session.execute(
        text(
            "INSERT INTO outbox_events (id, event_type, payload_ref) VALUES (:id, 'ObservationRecorded', CAST(:payload AS jsonb))"
        ),
        {
            "id": uuid4(),
            "payload": dumps(
                {
                    "observation_id": str(observation_id),
                    "patient_id": str(patient_id),
                    "request_id": current_request_id(),
                }
            ),
        },
    )
    session.execute(
        text("UPDATE devices SET last_sync_at = :now, last_received_at = :now WHERE id = :id"),
        {"id": device_id, "now": now},
    )
    record(
        session,
        actor_id=None,
        actor_role=None,
        action="device.observation.create",
        resource_type="observation",
        resource_id=observation_id,
        patient_id=patient_id,
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        winner = (
            session.execute(
                text(
                    "SELECT request_hash, response_body FROM idempotency_records WHERE actor_or_device_id = :actor AND operation = 'device.reading.create' AND key = :key"
                ),
                {"actor": device_id, "key": idempotency_key},
            )
            .mappings()
            .one_or_none()
        )
        if winner is None or winner["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency request could not be replayed")
        return winner["response_body"]
    return response
