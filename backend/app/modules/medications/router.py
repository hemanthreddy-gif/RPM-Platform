"""Audited medication version and self-report endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.medications.schemas import (
    DoseReportRequest,
    DoseReportResponse,
    MedicationRequest,
    MedicationResponse,
)
from app.modules.medications.service import (
    adherence_summary,
    create_version,
    list_current,
    report_dose,
)
from app.modules.patients.authorization import require_patient_access

router = APIRouter(prefix="/api/v1", tags=["medications"])


def _medication_patient(session: Session, medication_id: UUID) -> UUID:
    patient_id = session.execute(
        text("SELECT patient_id FROM medications WHERE id = :id"), {"id": medication_id}
    ).scalar_one_or_none()
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Medication not found")
    return patient_id


def _dose_patient(session: Session, dose_event_id: UUID) -> UUID:
    patient_id = session.execute(
        text("""SELECT m.patient_id FROM dose_events d JOIN medications m ON m.id = d.medication_id
          WHERE d.id = :id"""),
        {"id": dose_event_id},
    ).scalar_one_or_none()
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Dose event not found")
    return patient_id


@router.post(
    "/patients/{patient_id}/medications",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_medication(
    patient_id: UUID,
    payload: MedicationRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    try:
        response = create_version(
            session, patient_id=patient_id, actor_id=principal.user_id, payload=payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="medication.create_version",
        resource_type="medication",
        resource_id=UUID(str(response["id"])),
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.put("/medications/{medication_id}", response_model=MedicationResponse)
def update_medication(
    medication_id: UUID,
    payload: MedicationRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    patient_id = _medication_patient(session, medication_id)
    require_patient_access(session, principal, patient_id)
    try:
        response = create_version(
            session,
            patient_id=patient_id,
            actor_id=principal.user_id,
            payload=payload,
            medication_id=medication_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="medication.create_version",
        resource_type="medication",
        resource_id=medication_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.get("/patients/{patient_id}/medications", response_model=list[MedicationResponse])
def current_medications(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    require_patient_access(session, principal, patient_id)
    response = list_current(session, patient_id=patient_id)
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="medication.list_current",
        resource_type="medication",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.post("/dose-events/{dose_event_id}/report", response_model=DoseReportResponse)
def report_dose_event(
    dose_event_id: UUID,
    payload: DoseReportRequest,
    request: Request,
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    patient_id = _dose_patient(session, dose_event_id)
    require_patient_access(session, principal, patient_id)
    try:
        response, reported_patient_id = report_dose(
            session,
            dose_event_id=dose_event_id,
            patient_user_id=principal.user_id,
            status=payload.status,
            reported_at=payload.reported_at.astimezone(UTC),
            concern_note=payload.concern_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if reported_patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Dose event not found")
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="dose_event.self_report",
        resource_type="dose_event",
        resource_id=dose_event_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.get("/patients/{patient_id}/adherence")
def get_adherence_summary(
    patient_id: UUID,
    request: Request,
    days: int = Query(default=7),
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    if days not in {7, 14, 30}:
        raise HTTPException(status_code=422, detail="days must be one of 7, 14, or 30")
    response = adherence_summary(session, patient_id=patient_id, days=days, now=datetime.now(UTC))
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="medication.adherence_summary",
        resource_type="medication_adherence",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.get("/patients/{patient_id}/medication-concerns")
def list_medication_concerns(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    """Expose patient-authored concern flags to an authorized physician; no advice is generated."""
    require_patient_access(session, principal, patient_id)
    rows = (
        session.execute(
            text("""SELECT id, dose_event_id, reported_by, note, created_at
              FROM medication_concern_flags WHERE patient_id = :patient_id
              ORDER BY created_at DESC"""),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="medication.concern_flag.list",
        resource_type="medication_concern_flag",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return [dict(row) for row in rows]
