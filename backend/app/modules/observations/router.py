"""Audited immutable observation and target HTTP endpoints; alerts begin in Phase 4."""

from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clinical_rules.models import Observation as RuleObservation
from app.core.database import get_session
from app.modules.alerts.service import evaluate_and_persist
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.observations.schemas import (
    CorrectionRequest,
    ObservationCreate,
    ObservationResponse,
    TargetRequest,
    canonical_value,
)
from app.modules.patients.authorization import require_patient_access, set_database_identity

router = APIRouter(prefix="/api/v1", tags=["observations"])


def _patient_id(session: Session, user_id: UUID) -> UUID:
    return session.execute(
        text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": user_id}
    ).scalar_one()


def _response(row: Any) -> dict[str, object]:
    data = dict(row)
    for key in ("id", "patient_id", "supersedes_id"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


def _validate_time(measured_at: datetime) -> str | None:
    if measured_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="measured_at must include a UTC offset")
    if measured_at.astimezone(UTC) > datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Future measurements are not accepted")
    return "backdated" if (datetime.now(UTC) - measured_at.astimezone(UTC)).days > 90 else None


@router.post(
    "/observations", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED
)
def create_observation(
    payload: ObservationCreate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Record manual patient data and the durable Phase 4 orchestration seam atomically."""
    set_database_identity(session, principal)
    patient_id = _patient_id(session, principal.user_id)
    request_hash = sha256(
        dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    existing = (
        session.execute(
            text("""SELECT request_hash, response_status, response_body FROM idempotency_records
        WHERE actor_or_device_id = :actor AND operation = 'observation.create' AND key = :key"""),
            {"actor": principal.user_id, "key": idempotency_key},
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        if existing["request_hash"] != request_hash:
            raise HTTPException(
                status_code=409, detail="Idempotency key was reused with a different request"
            )
        if existing["response_body"] is None:
            raise HTTPException(status_code=409, detail="Original request is still being processed")
        return existing["response_body"]
    quality_flag = _validate_time(payload.measured_at)
    value, unit = canonical_value(payload)
    observation_id = uuid4()
    row = (
        session.execute(
            text("""INSERT INTO observations
        (id, patient_id, type, value_num, components, unit, original_value, original_unit, measured_at, source, entered_by, context, quality_flag, idempotency_key)
        VALUES (:id, :patient_id, CAST(:type AS observation_type), :value, CAST(:components AS jsonb), :unit, :original_value, :original_unit, :measured_at, 'manual', :entered_by, CAST(:context AS jsonb), :quality_flag, :key)
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
                "entered_by": principal.user_id,
                "context": dumps(payload.context),
                "quality_flag": quality_flag,
                "key": idempotency_key,
            },
        )
        .mappings()
        .one()
    )
    response = _response(row)
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
        evaluation_time=datetime.now(UTC),
    )
    session.execute(
        text("""INSERT INTO idempotency_records (id, actor_or_device_id, operation, key, request_hash, response_status, response_body)
        VALUES (:id, :actor, 'observation.create', :key, :request_hash, 201, CAST(:body AS jsonb))"""),
        {
            "id": uuid4(),
            "actor": principal.user_id,
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
                {"observation_id": str(observation_id), "patient_id": str(patient_id)}
            ),
        },
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="observation.create",
        resource_type="observation",
        resource_id=observation_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    try:
        session.commit()
    except IntegrityError:
        # The unique actor/operation/key constraint serializes concurrent retries. The losing
        # transaction rolls back its observation/audit/outbox writes before replaying the winner.
        session.rollback()
        winner = (
            session.execute(
                text("""SELECT request_hash, response_body FROM idempotency_records
              WHERE actor_or_device_id = :actor AND operation = 'observation.create' AND key = :key"""),
                {"actor": principal.user_id, "key": idempotency_key},
            )
            .mappings()
            .one_or_none()
        )
        if (
            winner is None
            or winner["request_hash"] != request_hash
            or winner["response_body"] is None
        ):
            raise HTTPException(status_code=409, detail="Idempotency request could not be replayed")
        return winner["response_body"]
    return response


@router.post(
    "/observations/{observation_id}/correct", response_model=ObservationResponse, status_code=201
)
def correct_observation(
    observation_id: UUID,
    payload: CorrectionRequest,
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    set_database_identity(session, principal)
    patient_id = _patient_id(session, principal.user_id)
    original = (
        session.execute(
            text(
                "SELECT id, type::text FROM observations WHERE id = :id AND patient_id = :patient_id"
            ),
            {"id": observation_id, "patient_id": patient_id},
        )
        .mappings()
        .one_or_none()
    )
    if original is None or original["type"] != payload.type:
        raise HTTPException(status_code=404, detail="Observation not found")
    quality_flag, value, unit = _validate_time(payload.measured_at), *canonical_value(payload)
    new_id = uuid4()
    row = (
        session.execute(
            text("""INSERT INTO observations (id, patient_id, type, value_num, components, unit, original_value, original_unit, measured_at, source, entered_by, context, quality_flag, supersedes_id)
        VALUES (:id, :patient_id, CAST(:type AS observation_type), :value, CAST(:components AS jsonb), :unit, :original_value, :original_unit, :measured_at, 'manual', :entered_by, CAST(:context AS jsonb), :quality_flag, :supersedes_id)
        RETURNING id, patient_id, type::text, value_num AS value, unit, original_value, original_unit, components, measured_at, recorded_at, source::text, quality_flag, supersedes_id"""),
            {
                "id": new_id,
                "patient_id": patient_id,
                "type": payload.type,
                "value": value,
                "components": dumps(payload.components, default=str),
                "unit": unit,
                "original_value": payload.value,
                "original_unit": payload.unit,
                "measured_at": payload.measured_at.astimezone(UTC),
                "entered_by": principal.user_id,
                "context": dumps(payload.context),
                "quality_flag": quality_flag,
                "supersedes_id": observation_id,
            },
        )
        .mappings()
        .one()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="observation.correct",
        resource_type="observation",
        resource_id=new_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return _response(row)


@router.get("/patients/{patient_id}/observations", response_model=list[ObservationResponse])
def list_observations(
    patient_id: UUID,
    request: Request,
    include_history: bool = False,
    type: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    require_patient_access(session, principal, patient_id)
    if type is not None and type not in {"glucose", "blood_pressure", "heart_rate", "spo2"}:
        raise HTTPException(status_code=422, detail="Unsupported observation type")
    if (from_ is not None and from_.tzinfo is None) or (to is not None and to.tzinfo is None):
        raise HTTPException(status_code=422, detail="Date filters must include a UTC offset")
    if from_ is not None and to is not None and from_ > to:
        raise HTTPException(status_code=422, detail="from must not be after to")
    rows = (
        session.execute(
            text("""SELECT o.id, o.patient_id, o.type::text, o.value_num AS value, o.unit, o.original_value, o.original_unit, o.components, o.measured_at, o.recorded_at, o.source::text, o.quality_flag, o.supersedes_id FROM observations o
        WHERE o.patient_id = :patient_id AND (:include_history OR NOT EXISTS (SELECT 1 FROM observations child WHERE child.supersedes_id = o.id))
        AND (CAST(:type AS observation_type) IS NULL OR o.type = CAST(:type AS observation_type))
        AND (CAST(:from_time AS timestamptz) IS NULL OR o.measured_at >= CAST(:from_time AS timestamptz))
        AND (CAST(:to_time AS timestamptz) IS NULL OR o.measured_at <= CAST(:to_time AS timestamptz))
        ORDER BY o.measured_at DESC OFFSET :offset LIMIT :limit"""),
            {
                "patient_id": patient_id,
                "include_history": include_history,
                "type": type,
                "from_time": from_,
                "to_time": to,
                "offset": offset,
                "limit": limit,
            },
        )
        .mappings()
        .all()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="observation.list",
        resource_type="observation",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [_response(row) for row in rows]


@router.get("/patients/{patient_id}/observations/daily")
def daily_aggregates(
    patient_id: UUID,
    request: Request,
    type: str,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    """UTC daily aggregates; blood-pressure components stay in source records."""
    require_patient_access(session, principal, patient_id)
    if type not in {"glucose", "heart_rate", "spo2"}:
        raise HTTPException(
            status_code=422, detail="Daily aggregation is unavailable for this type"
        )
    rows = (
        session.execute(
            text("""SELECT date_trunc('day', measured_at) AS day, min(value_num) AS min,
          max(value_num) AS max, avg(value_num) AS mean, count(*) AS count
          FROM observations o WHERE patient_id = :patient_id
          AND type = CAST(:type AS observation_type)
          AND NOT EXISTS (SELECT 1 FROM observations child WHERE child.supersedes_id = o.id)
          GROUP BY date_trunc('day', measured_at) ORDER BY day"""),
            {"patient_id": patient_id, "type": type},
        )
        .mappings()
        .all()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="observation.daily_aggregate",
        resource_type="observation",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [dict(row) for row in rows]


@router.get("/patients/{patient_id}/observations/in-range")
def percentage_in_range(
    patient_id: UUID,
    request: Request,
    type: str,
    context: str = "default",
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Report sampled-reading percentage only when a physician target exists."""
    require_patient_access(session, principal, patient_id)
    if type not in {"glucose", "heart_rate", "spo2"}:
        raise HTTPException(
            status_code=422, detail="In-range percentage is unavailable for this type"
        )
    target = (
        session.execute(
            text("""SELECT low, high FROM monitoring_targets WHERE patient_id = :patient_id
          AND type = CAST(:type AS observation_type) AND context = :context
          ORDER BY version DESC LIMIT 1"""),
            {"patient_id": patient_id, "type": type, "context": context},
        )
        .mappings()
        .one_or_none()
    )
    if target is None or target["low"] is None or target["high"] is None:
        raise HTTPException(status_code=409, detail="No physician-defined range is available")
    result = (
        session.execute(
            text("""SELECT count(*) AS sample_size,
          100.0 * avg(CASE WHEN value_num >= :low AND value_num <= :high THEN 1 ELSE 0 END) AS percentage
          FROM observations o WHERE patient_id = :patient_id AND type = CAST(:type AS observation_type)
          AND NOT EXISTS (SELECT 1 FROM observations child WHERE child.supersedes_id = o.id)"""),
            {"patient_id": patient_id, "type": type, "low": target["low"], "high": target["high"]},
        )
        .mappings()
        .one()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="observation.in_range",
        resource_type="observation",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return {
        "type": type,
        "context": context,
        "low": target["low"],
        "high": target["high"],
        **dict(result),
    }


@router.put("/patients/{patient_id}/targets", status_code=status.HTTP_201_CREATED)
def set_target(
    patient_id: UUID,
    payload: TargetRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    version = session.execute(
        text("""SELECT coalesce(max(version), 0) + 1 FROM monitoring_targets
          WHERE patient_id = :patient_id AND type = CAST(:type AS observation_type) AND context = :context"""),
        {"patient_id": patient_id, "type": payload.type, "context": payload.context},
    ).scalar_one()
    target_id = uuid4()
    row = (
        session.execute(
            text("""INSERT INTO monitoring_targets (id, patient_id, type, context, low, high, set_by, version, effective_from)
          VALUES (:id, :patient_id, CAST(:type AS observation_type), :context, :low, :high, :set_by, :version, now())
          RETURNING id, patient_id, type::text, context, low, high, set_by, version, effective_from"""),
            {
                "id": target_id,
                "patient_id": patient_id,
                "type": payload.type,
                "context": payload.context,
                "low": payload.low,
                "high": payload.high,
                "set_by": principal.user_id,
                "version": version,
            },
        )
        .mappings()
        .one()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="target.create_version",
        resource_type="monitoring_target",
        resource_id=target_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return _response(row)


@router.get("/patients/{patient_id}/targets")
def list_targets(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    require_patient_access(session, principal, patient_id)
    rows = (
        session.execute(
            text("""SELECT DISTINCT ON (type, context) id, patient_id, type::text, context, low, high, set_by, version, effective_from
          FROM monitoring_targets WHERE patient_id = :patient_id ORDER BY type, context, version DESC"""),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="target.list",
        resource_type="monitoring_target",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [_response(row) for row in rows]
