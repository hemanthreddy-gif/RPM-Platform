"""Audited authorized endpoints for deterministic Phase 8 insight artifacts."""

from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.insights.schemas import (
    ArtifactReviewRequest,
    ArtifactRevisionRequest,
    InsightArtifactResponse,
    SummaryCreateRequest,
)
from app.modules.insights.service import (
    create_summary,
    latest_insights,
    range_for_days,
    review_summary,
)
from app.modules.patients.authorization import require_patient_access, set_database_identity

router = APIRouter(prefix="/api/v1", tags=["grounded insights"])


@router.get("/patients/{patient_id}/insights", response_model=list[InsightArtifactResponse])
def list_insights(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    require_patient_access(session, principal, patient_id)
    response = latest_insights(session, patient_id=patient_id)
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="insight.list",
        resource_type="ai_artifact",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.post(
    "/patients/{patient_id}/summaries",
    response_model=InsightArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_summary(
    patient_id: UUID,
    payload: SummaryCreateRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    require_patient_access(session, principal, patient_id)
    if payload.from_ is not None or payload.to is not None:
        if (
            payload.from_ is None
            or payload.to is None
            or payload.from_.tzinfo is None
            or payload.to.tzinfo is None
            or payload.from_ >= payload.to
        ):
            raise HTTPException(
                status_code=422,
                detail="Custom range needs ordered timezone-aware from and to values",
            )
        start, end = payload.from_.astimezone(UTC), payload.to.astimezone(UTC)
    elif payload.days in {7, 14, 30}:
        start, end = range_for_days(payload.days)
    else:
        raise HTTPException(status_code=422, detail="days must be 7, 14, or 30")
    response = create_summary(
        session, patient_id=patient_id, created_by=principal.user_id, start=start, end=end
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="summary.create_draft",
        resource_type="ai_artifact",
        resource_id=UUID(str(response["id"])),
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.post("/ai-artifacts/{artifact_id}/review", response_model=InsightArtifactResponse)
def review_patient_summary(
    artifact_id: UUID,
    payload: ArtifactReviewRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    set_database_identity(session, principal)
    try:
        response, patient_id = review_summary(
            session,
            artifact_id=artifact_id,
            reviewer_id=principal.user_id,
            decision=payload.decision,
        )
        require_patient_access(session, principal, patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action=f"summary.{payload.decision}",
        resource_type="ai_artifact",
        resource_id=artifact_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.post(
    "/ai-artifacts/{artifact_id}/revisions",
    response_model=InsightArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def revise_patient_summary(
    artifact_id: UUID,
    payload: ArtifactRevisionRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    # The source is resolved through the versioning service and then authorized before commit.
    from sqlalchemy import text

    source = (
        session.execute(
            text("SELECT patient_id FROM ai_artifacts WHERE id = :id AND kind = 'summary'"),
            {"id": artifact_id},
        )
        .mappings()
        .one_or_none()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Summary artifact not found")
    patient_id = source["patient_id"]
    require_patient_access(session, principal, patient_id)
    start, end = range_for_days(payload.days)
    try:
        response = create_summary(
            session,
            patient_id=patient_id,
            created_by=principal.user_id,
            start=start,
            end=end,
            supersedes_id=artifact_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="summary.create_revision",
        resource_type="ai_artifact",
        resource_id=UUID(str(response["id"])),
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response
