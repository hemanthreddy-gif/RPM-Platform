"""Opt-in PostgreSQL evidence for private meal-photo review authorization."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import ProgrammingError


def _seed_reviewable_meal(connection: Connection) -> tuple[UUID, UUID, UUID, UUID]:
    patient_user_id, patient_id = uuid4(), uuid4()
    physician_user_id, physician_id = uuid4(), uuid4()
    consent_id, meal_id = uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'patient')"),
        {"id": patient_user_id, "email": f"phase7-patient-{patient_user_id}@example.test"},
    )
    connection.execute(
        text(
            "INSERT INTO patients (id, user_id, display_name) VALUES "
            "(:id, :user_id, 'Phase 7 synthetic')"
        ),
        {"id": patient_id, "user_id": patient_user_id},
    )
    connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'physician')"),
        {"id": physician_user_id, "email": f"phase7-physician-{physician_user_id}@example.test"},
    )
    connection.execute(
        text(
            "INSERT INTO physicians (id, user_id, registration_no) VALUES "
            "(:id, :user_id, :registration_no)"
        ),
        {"id": physician_id, "user_id": physician_user_id, "registration_no": str(physician_id)},
    )
    connection.execute(
        text("""INSERT INTO consents (id, patient_id, purpose, version, granted_at)
          VALUES (:id, :patient_id, 'monitoring', 'synthetic-v1', now())"""),
        {"id": consent_id, "patient_id": patient_id},
    )
    connection.execute(
        text("""INSERT INTO care_relationships
          (id, patient_id, physician_id, consent_id, status, started_at)
          VALUES (:id, :patient_id, :physician_id, :consent_id, 'active', now())"""),
        {
            "id": uuid4(),
            "patient_id": patient_id,
            "physician_id": physician_id,
            "consent_id": consent_id,
        },
    )
    connection.execute(
        text("""INSERT INTO meals
          (id, patient_id, eaten_at, image_key, status, uploaded_at, image_sha256,
           image_content_type, image_size_bytes)
          VALUES (:id, :patient_id, :eaten_at, :image_key, 'submitted', :uploaded_at,
            :digest, 'image/jpeg', 4)"""),
        {
            "id": meal_id,
            "patient_id": patient_id,
            "eaten_at": datetime.now(UTC),
            "uploaded_at": datetime.now(UTC),
            "image_key": f"meal-photos/{meal_id}.jpg",
            "digest": "a" * 64,
        },
    )
    return patient_user_id, patient_id, physician_user_id, meal_id


def _runtime_identity(
    connection: Connection, *, role: str, user_id: UUID, patient_id: UUID | None = None
) -> None:
    connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    connection.execute(text("SELECT set_config('app.role', :role, true)"), {"role": role})
    connection.execute(text("SELECT set_config('app.user_id', :id, true)"), {"id": str(user_id)})
    if patient_id is not None:
        connection.execute(
            text("SELECT set_config('app.patient_id', :id, true)"), {"id": str(patient_id)}
        )


def test_meal_photo_patient_cannot_mutate_and_authorized_physician_comment_is_append_only(
    integration_connection: Connection,
) -> None:
    patient_user_id, patient_id, physician_user_id, meal_id = _seed_reviewable_meal(
        integration_connection
    )
    _runtime_identity(
        integration_connection, role="patient", user_id=patient_user_id, patient_id=patient_id
    )
    assert (
        integration_connection.execute(
            text("SELECT id FROM meals WHERE id = :id"), {"id": meal_id}
        ).scalar_one()
        == meal_id
    )
    assert (
        integration_connection.execute(
            text("UPDATE meals SET note = 'mutated' WHERE id = :id"), {"id": meal_id}
        ).rowcount
        == 0
    )

    _runtime_identity(integration_connection, role="physician", user_id=physician_user_id)
    comment_id = integration_connection.execute(
        text("""INSERT INTO meal_photo_comments (id, meal_id, author_id, body)
          VALUES (:id, :meal_id, :author_id, 'Synthetic non-clinical review') RETURNING id"""),
        {"id": uuid4(), "meal_id": meal_id, "author_id": physician_user_id},
    ).scalar_one()
    assert isinstance(comment_id, UUID)
    with pytest.raises(ProgrammingError, match="permission denied"):
        integration_connection.execute(
            text("UPDATE meal_photo_comments SET body = 'changed' WHERE id = :id"),
            {"id": comment_id},
        )


def test_unrelated_physician_cannot_read_a_meal_photo(integration_connection: Connection) -> None:
    _, _, _, meal_id = _seed_reviewable_meal(integration_connection)
    unrelated_user_id, unrelated_physician_id = uuid4(), uuid4()
    integration_connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'physician')"),
        {"id": unrelated_user_id, "email": f"phase7-unrelated-{unrelated_user_id}@example.test"},
    )
    integration_connection.execute(
        text(
            "INSERT INTO physicians (id, user_id, registration_no) VALUES "
            "(:id, :user_id, :registration_no)"
        ),
        {
            "id": unrelated_physician_id,
            "user_id": unrelated_user_id,
            "registration_no": str(unrelated_physician_id),
        },
    )
    _runtime_identity(integration_connection, role="physician", user_id=unrelated_user_id)
    assert (
        integration_connection.execute(
            text("SELECT id FROM meals WHERE id = :id"), {"id": meal_id}
        ).scalar_one_or_none()
        is None
    )
