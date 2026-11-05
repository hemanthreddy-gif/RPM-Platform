"""Authorized HTTP surface for private meal-photo review; no nutrition analysis endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.modules.audit.service import record
from app.modules.identity.router import require_role
from app.modules.identity.schemas import Principal
from app.modules.nutrition.schemas import (
    MealPhotoCommentRequest,
    MealPhotoCommentResponse,
    MealPhotoResponse,
)
from app.modules.nutrition.service import (
    add_physician_comment,
    create_meal_photo,
    list_meal_photos,
    meal_photo_key,
    normalize_meal_photo,
)
from app.modules.nutrition.storage import MealPhotoStorageError, get_meal_photo_storage
from app.modules.patients.authorization import require_patient_access, set_database_identity

router = APIRouter(prefix="/api/v1", tags=["meal photo review"])


def _patient_id(session: Session, principal: Principal) -> UUID:
    patient_id = session.execute(
        text("SELECT id FROM patients WHERE user_id = :user_id"), {"user_id": principal.user_id}
    ).scalar_one_or_none()
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient_id


@router.post("/meals", response_model=MealPhotoResponse, status_code=status.HTTP_201_CREATED)
def upload_meal_photo(
    request: Request,
    payload: bytes = Body(),
    eaten_at: datetime = Query(),
    principal: Principal = Depends(require_role("patient")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Upload a private, re-encoded plate photo for optional physician review."""
    set_database_identity(session, principal)
    patient_id = _patient_id(session, principal)
    try:
        photo = normalize_meal_photo(payload, request.headers.get("content-type"), get_settings())
        created = create_meal_photo(
            session,
            patient_id=patient_id,
            eaten_at=eaten_at.astimezone(UTC),
            photo=photo,
            storage=get_meal_photo_storage(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MealPhotoStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        record(
            session,
            actor_id=principal.user_id,
            actor_role=principal.role,
            action="meal_photo.create",
            resource_type="meal",
            resource_id=created.id,
            patient_id=patient_id,
            ip=request.client.host if request.client else None,
        )
        session.commit()
    except Exception:
        session.rollback()
        get_meal_photo_storage().delete(created.image_key)
        raise
    return created.response


@router.get("/patients/{patient_id}/meals", response_model=list[MealPhotoResponse])
def get_meal_photos(
    patient_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    require_patient_access(session, principal, patient_id)
    response = list_meal_photos(session, patient_id)
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="meal_photo.list",
        resource_type="meal",
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response


@router.get("/meals/{meal_id}/image")
def get_meal_photo_image(
    meal_id: UUID,
    request: Request,
    principal: Principal = Depends(require_role("patient", "physician")),
    session: Session = Depends(get_session),
) -> Response:
    set_database_identity(session, principal)
    try:
        patient_id, image_key = meal_photo_key(session, meal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    require_patient_access(session, principal, patient_id)
    try:
        image = get_meal_photo_storage().read(image_key)
    except MealPhotoStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="meal_photo.image.read",
        resource_type="meal",
        resource_id=meal_id,
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return Response(
        content=image,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/meals/{meal_id}/comments",
    response_model=MealPhotoCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_meal_photo_comment(
    meal_id: UUID,
    payload: MealPhotoCommentRequest,
    request: Request,
    principal: Principal = Depends(require_role("physician")),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    set_database_identity(session, principal)
    try:
        patient_id, _ = meal_photo_key(session, meal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    require_patient_access(session, principal, patient_id)
    response = add_physician_comment(
        session, meal_id=meal_id, author_id=principal.user_id, body=payload.body
    )
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action="meal_photo.comment.create",
        resource_type="meal_photo_comment",
        resource_id=UUID(str(response["id"])),
        patient_id=patient_id,
        ip=request.client.host if request.client else None,
    )
    session.commit()
    return response
