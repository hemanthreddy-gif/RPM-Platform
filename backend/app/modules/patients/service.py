"""Authorized patient profile and monitoring-relationship operations."""

from datetime import UTC, date, datetime
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.audit.service import record
from app.modules.identity.schemas import Principal
from app.modules.patients.authorization import require_patient_access, set_database_identity
from app.modules.patients.schemas import ProfileUpdate

MAX_PICTURE_BYTES = 2 * 1024 * 1024
MAX_PICTURE_PIXELS = 12_000_000
PROFILE_COLUMNS = """id, display_name, date_of_birth, gender, phone, height_cm, weight_kg,
    timezone, has_hypertension, (profile_picture IS NOT NULL) AS has_profile_picture,
    profile_picture_updated_at"""


def age_on(born: date | None, today: date) -> int | None:
    if born is None:
        return None
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def own_patient_id(session: Session, principal: Principal, *, lock: bool = False) -> UUID:
    if principal.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access is required")
    set_database_identity(session, principal)
    patient_id = session.execute(
        text("SELECT id FROM patients WHERE user_id = :id" + (" FOR UPDATE" if lock else "")),
        {"id": principal.user_id},
    ).scalar_one_or_none()
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return UUID(str(patient_id))


def _profile(session: Session, patient_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text(f"SELECT {PROFILE_COLUMNS} FROM patients WHERE id = :id"), {"id": patient_id}
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return {**dict(row), "age": age_on(row["date_of_birth"], datetime.now(UTC).date())}


def _audit(
    session: Session,
    principal: Principal,
    patient_id: UUID,
    action: str,
    resource_type: str = "patient",
    resource_id: UUID | None = None,
    ip: str | None = None,
) -> None:
    record(
        session,
        actor_id=principal.user_id,
        actor_role=principal.role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id or patient_id,
        patient_id=patient_id,
        ip=ip,
    )


def read_profile(
    session: Session,
    principal: Principal,
    patient_id: UUID | None = None,
    ip: str | None = None,
) -> dict[str, object]:
    patient_id = patient_id or own_patient_id(session, principal)
    require_patient_access(session, principal, patient_id)
    result = _profile(session, patient_id)
    _audit(session, principal, patient_id, "patient.profile.read", ip=ip)
    return result


def update_profile(
    session: Session,
    principal: Principal,
    payload: ProfileUpdate,
    ip: str | None = None,
) -> dict[str, object]:
    patient_id = own_patient_id(session, principal)
    session.execute(
        text("""UPDATE patients SET display_name = :display_name,
        date_of_birth = :date_of_birth, gender = :gender, phone = :phone,
        height_cm = :height_cm, weight_kg = :weight_kg, timezone = :timezone,
        has_hypertension = :has_hypertension WHERE id = :id"""),
        {**payload.model_dump(), "id": patient_id},
    )
    _audit(session, principal, patient_id, "patient.profile.update", ip=ip)
    return _profile(session, patient_id)


def normalize_picture(payload: bytes, content_type: str | None) -> bytes:
    """Bound decoding, orient, resize and strip metadata; never serve original upload bytes."""
    if content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Choose a JPEG or PNG profile picture")
    if not payload or len(payload) > MAX_PICTURE_BYTES:
        raise HTTPException(status_code=413, detail="Picture must be between 1 byte and 2 MB")
    try:
        with Image.open(BytesIO(payload)) as candidate:
            if candidate.format not in {"JPEG", "PNG"}:
                raise ValueError("Unsupported image")
            if candidate.width * candidate.height > MAX_PICTURE_PIXELS:
                raise ValueError("Picture dimensions are too large")
            candidate.verify()
        with Image.open(BytesIO(payload)) as source:
            source.load()
            normalized = ImageOps.exif_transpose(source).convert("RGB")
            normalized.thumbnail((512, 512))
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=85, optimize=True)
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail="Picture is corrupt or unsupported") from exc
    return output.getvalue()


def update_picture(
    session: Session,
    principal: Principal,
    payload: bytes,
    content_type: str | None,
    ip: str | None = None,
) -> dict[str, object]:
    patient_id = own_patient_id(session, principal)
    picture = normalize_picture(payload, content_type)
    session.execute(
        text("""UPDATE patients SET profile_picture = :picture,
        profile_picture_updated_at = now() WHERE id = :id"""),
        {"picture": picture, "id": patient_id},
    )
    _audit(session, principal, patient_id, "patient.picture.update", ip=ip)
    return _profile(session, patient_id)


def read_picture(
    session: Session,
    principal: Principal,
    patient_id: UUID,
    ip: str | None = None,
) -> bytes:
    require_patient_access(session, principal, patient_id)
    picture = session.execute(
        text("SELECT profile_picture FROM patients WHERE id = :id"),
        {"id": patient_id},
    ).scalar_one_or_none()
    if picture is None:
        raise HTTPException(status_code=404, detail="Profile picture not found")
    _audit(session, principal, patient_id, "patient.picture.read", ip=ip)
    return bytes(picture)


def physician_directory(session: Session) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in session.execute(
            text("""SELECT ph.id,
        COALESCE(ph.display_name, 'Physician ' || ph.registration_no) AS display_name, ph.specialty
        FROM physicians ph JOIN users u ON u.id = ph.user_id
        WHERE u.status = 'active' AND u.mfa_enabled = true
        ORDER BY display_name, ph.id LIMIT 100""")
        ).mappings()
    ]


def _connections(session: Session, patient_id: UUID) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in session.execute(
            text("""SELECT r.id, r.physician_id,
        COALESCE(ph.display_name, 'Physician ' || ph.registration_no) AS display_name,
        ph.specialty, r.consent_id, r.started_at,
        (r.status = 'active' AND r.ended_at IS NULL AND c.revoked_at IS NULL) AS active
        FROM care_relationships r JOIN physicians ph ON ph.id = r.physician_id
        JOIN consents c ON c.id = r.consent_id AND c.patient_id = r.patient_id
        WHERE r.patient_id = :id AND c.purpose = 'monitoring'
        ORDER BY r.started_at DESC"""),
            {"id": patient_id},
        ).mappings()
    ]


def list_connections(
    session: Session,
    principal: Principal,
    ip: str | None = None,
) -> list[dict[str, object]]:
    patient_id = own_patient_id(session, principal)
    result = _connections(session, patient_id)
    _audit(session, principal, patient_id, "relationship.list", "care_relationship", ip=ip)
    return result


def connect_physician(
    session: Session,
    principal: Principal,
    physician_id: UUID,
    ip: str | None = None,
) -> dict[str, object]:
    # The patient-row lock serializes retries and simultaneous clicks without duplicate consent.
    patient_id = own_patient_id(session, principal, lock=True)
    physician = session.execute(
        text("""SELECT ph.id FROM physicians ph
        JOIN users u ON u.id = ph.user_id WHERE ph.id = :id
        AND u.status = 'active' AND u.mfa_enabled = true"""),
        {"id": physician_id},
    ).scalar_one_or_none()
    if physician is None:
        raise HTTPException(status_code=404, detail="Activated physician not found")
    for connection in _connections(session, patient_id):
        if connection["physician_id"] == physician_id and connection["active"]:
            _audit(
                session,
                principal,
                patient_id,
                "relationship.read",
                "care_relationship",
                UUID(str(connection["id"])),
                ip,
            )
            return connection
    consent_id, relationship_id = uuid4(), uuid4()
    session.execute(
        text("""INSERT INTO consents (id, patient_id, purpose, version, granted_at)
        VALUES (:id, :patient, 'monitoring', 'patient-connection-v1', clock_timestamp())"""),
        {"id": consent_id, "patient": patient_id},
    )
    session.execute(
        text("""INSERT INTO care_relationships
        (id, patient_id, physician_id, consent_id, status, started_at)
        VALUES (:id, :patient, :physician, :consent, 'active', now())"""),
        {
            "id": relationship_id,
            "patient": patient_id,
            "physician": physician_id,
            "consent": consent_id,
        },
    )
    _audit(session, principal, patient_id, "consent.grant", "consent", consent_id, ip)
    _audit(
        session,
        principal,
        patient_id,
        "relationship.connect",
        "care_relationship",
        relationship_id,
        ip,
    )
    return next(row for row in _connections(session, patient_id) if row["id"] == relationship_id)


def disconnect_physician(
    session: Session,
    principal: Principal,
    relationship_id: UUID,
    ip: str | None = None,
) -> None:
    patient_id = own_patient_id(session, principal, lock=True)
    row = (
        session.execute(
            text("""SELECT id, consent_id FROM care_relationships
        WHERE id = :id AND patient_id = :patient FOR UPDATE"""),
            {"id": relationship_id, "patient": patient_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    session.execute(
        text("""UPDATE care_relationships SET status = 'ended',
        ended_at = COALESCE(ended_at, now()) WHERE id = :id"""),
        {"id": relationship_id},
    )
    revoked = session.execute(
        text("""UPDATE consents SET revoked_at = now()
        WHERE id = :id AND patient_id = :patient AND revoked_at IS NULL
          AND NOT EXISTS (SELECT 1 FROM care_relationships r
            WHERE r.consent_id = :id AND r.status = 'active' AND r.ended_at IS NULL)
        RETURNING id"""),
        {"id": row["consent_id"], "patient": patient_id},
    ).scalar_one_or_none()
    if revoked is not None:
        _audit(session, principal, patient_id, "consent.revoke", "consent", row["consent_id"], ip)
    _audit(
        session,
        principal,
        patient_id,
        "relationship.disconnect",
        "care_relationship",
        relationship_id,
        ip,
    )
