"""Audited, read-only FHIR R4 subset endpoints."""

from datetime import datetime
from json import loads
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.fhir.service import (
    bundle,
    medication_request_resource,
    medication_statement_resource,
    observation_resource,
    patient_resource,
    validate_r4_subset,
)
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.patients.authorization import require_patient_access

router = APIRouter(prefix="/api/v1/fhir", tags=["FHIR R4 subset"])


def _object(value: object) -> dict[str, object]:
    return loads(value) if isinstance(value, str) else value  # type: ignore[return-value]


@router.get("/Patient/{patient_id}")
def get_patient_fhir(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    row = (
        session.execute(
            text("SELECT id, display_name FROM patients WHERE id = :id"), {"id": patient_id}
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = patient_resource(dict(row))
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="fhir.patient.read",
        resource_type="fhir_export",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return result


@router.get("/Observation")
def get_observations_fhir(
    patient: UUID,
    request: Request,
    code: str | None = None,
    date_from: datetime | None = Query(default=None, alias="date"),
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient)
    observation_query = """SELECT id, patient_id, type::text, value_num AS value, unit, components, context, measured_at, recorded_at FROM observations
      WHERE patient_id = :patient"""
    query_params: dict[str, object] = {"patient": patient}
    if date_from is not None:
        observation_query += " AND measured_at >= :date_from"
        query_params["date_from"] = date_from
    observation_query += " ORDER BY measured_at"
    rows = (
        session.execute(
            text(observation_query),
            query_params,
        )
        .mappings()
        .all()
    )
    resources: list[dict[str, object]] = []
    for row in rows:
        data = dict(row)
        data["components"] = _object(data["components"])
        data["context"] = _object(data["context"])
        try:
            resource = observation_resource(data)
        except ValueError:
            continue
        code_block = resource.get("code")
        coding = None
        if isinstance(code_block, dict) and isinstance(code_block.get("coding"), list):
            first_coding = code_block["coding"][0] if code_block["coding"] else None
            if isinstance(first_coding, dict):
                coding = first_coding.get("code")
        if code is None or code == coding:
            resources.append(resource)
    result = bundle(resources)
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="fhir.observation.search",
        resource_type="fhir_export",
        patient_id=patient,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return result


@router.get("/Patient/{patient_id}/$everything")
def patient_bundle(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    patient_row = (
        session.execute(
            text("SELECT id, display_name FROM patients WHERE id = :id"), {"id": patient_id}
        )
        .mappings()
        .one_or_none()
    )
    if patient_row is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    rows = (
        session.execute(
            text(
                "SELECT id, patient_id, name, start_date FROM medications WHERE patient_id = :patient"
            ),
            {"patient": patient_id},
        )
        .mappings()
        .all()
    )
    result = bundle(
        [
            patient_resource(dict(patient_row)),
            *[medication_statement_resource(dict(row)) for row in rows],
            *[medication_request_resource(dict(row)) for row in rows],
        ]
    )
    validate_r4_subset(result)
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="fhir.patient.bundle.export",
        resource_type="fhir_export",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return result
