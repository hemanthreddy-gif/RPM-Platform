"""Meal-photo review operations; deliberately contains no nutrition or AI decisions."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.nutrition.storage import MealPhotoStorage

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


@dataclass(frozen=True)
class NormalizedMealPhoto:
    image: bytes
    content_type: str
    sha256_hex: str


@dataclass(frozen=True)
class CreatedMealPhoto:
    id: UUID
    image_key: str
    response: dict[str, object]


def normalize_meal_photo(
    payload: bytes, content_type: str | None, settings: Settings
) -> NormalizedMealPhoto:
    """Validate and re-encode one JPEG/PNG image, removing metadata including EXIF."""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValueError("Only JPEG and PNG meal photos are accepted")
    if not payload:
        raise ValueError("Meal photo is empty")
    if len(payload) > settings.meal_photo_max_bytes:
        raise ValueError("Meal photo exceeds the allowed size")
    try:
        with Image.open(BytesIO(payload)) as candidate:
            if candidate.format not in {"JPEG", "PNG"}:
                raise ValueError("Only JPEG and PNG meal photos are accepted")
            candidate.verify()
        with Image.open(BytesIO(payload)) as source:
            source.load()
            if source.width * source.height > settings.meal_photo_max_pixels:
                raise ValueError("Meal photo has too many pixels")
            oriented = ImageOps.exif_transpose(source)
            if oriented.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", oriented.size, "white")
                background.paste(oriented, mask=oriented.getchannel("A"))
                normalized = background
            else:
                normalized = oriented.convert("RGB")
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=85, optimize=True)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("Meal photo is corrupt or unsupported") from exc
    image = output.getvalue()
    if not image:
        raise ValueError("Meal photo is corrupt or unsupported")
    return NormalizedMealPhoto(
        image=image, content_type="image/jpeg", sha256_hex=sha256(image).hexdigest()
    )


def create_meal_photo(
    session: Session,
    *,
    patient_id: UUID,
    eaten_at: datetime,
    photo: NormalizedMealPhoto,
    storage: MealPhotoStorage,
) -> CreatedMealPhoto:
    """Store a private image before atomically recording its opaque metadata and audit event."""
    meal_id = uuid4()
    image_key = f"meal-photos/{meal_id}.jpg"
    storage.put(image_key, photo.image)
    uploaded_at = datetime.now(UTC)
    try:
        session.execute(
            text("""INSERT INTO meals
              (id, patient_id, eaten_at, image_key, status, uploaded_at, image_sha256,
               image_content_type, image_size_bytes)
              VALUES (:id, :patient_id, :eaten_at, :image_key, 'submitted', :uploaded_at,
                :image_sha256, :image_content_type, :image_size_bytes)"""),
            {
                "id": meal_id,
                "patient_id": patient_id,
                "eaten_at": eaten_at.astimezone(UTC),
                "image_key": image_key,
                "uploaded_at": uploaded_at,
                "image_sha256": photo.sha256_hex,
                "image_content_type": photo.content_type,
                "image_size_bytes": len(photo.image),
            },
        )
    except Exception:
        storage.delete(image_key)
        raise
    response = {
        "id": meal_id,
        "eaten_at": eaten_at.astimezone(UTC),
        "uploaded_at": uploaded_at,
        "status": "submitted",
        "image_content_type": photo.content_type,
        "image_size_bytes": len(photo.image),
        "comments": [],
    }
    return CreatedMealPhoto(id=meal_id, image_key=image_key, response=response)


def _comments(session: Session, meal_id: UUID) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in session.execute(
            text("""SELECT id, body, created_at FROM meal_photo_comments
              WHERE meal_id = :meal_id ORDER BY created_at ASC"""),
            {"meal_id": meal_id},
        )
        .mappings()
        .all()
    ]


def list_meal_photos(session: Session, patient_id: UUID) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text("""SELECT id, eaten_at, uploaded_at, status::text AS status,
              image_content_type, image_size_bytes
          FROM meals WHERE patient_id = :patient_id AND image_key IS NOT NULL
          ORDER BY uploaded_at DESC"""),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )
    return [{**dict(row), "comments": _comments(session, row["id"])} for row in rows]


def meal_photo_key(session: Session, meal_id: UUID) -> tuple[UUID, str]:
    row = (
        session.execute(
            text(
                "SELECT patient_id, image_key FROM meals WHERE id = :id AND image_key IS NOT NULL"
            ),
            {"id": meal_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ValueError("Meal photo not found")
    return row["patient_id"], row["image_key"]


def add_physician_comment(
    session: Session, *, meal_id: UUID, author_id: UUID, body: str
) -> dict[str, object]:
    result = (
        session.execute(
            text("""INSERT INTO meal_photo_comments (id, meal_id, author_id, body)
          VALUES (:id, :meal_id, :author_id, :body)
          RETURNING id, body, created_at"""),
            {"id": uuid4(), "meal_id": meal_id, "author_id": author_id, "body": body},
        )
        .mappings()
        .one()
    )
    return dict(result)
