"""Opt-in PostgreSQL acceptance evidence for Phase 9 authorization and device idempotency."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID, uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.modules.devices.schemas import DeviceReadingRequest
from app.modules.devices.service import _hash, authenticate_device, record_device_reading


def _identity(
    connection: Connection, role: str, user_id: UUID, patient_id: UUID | None = None
) -> None:
    connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    connection.execute(text("SELECT set_config('app.role', :role, true)"), {"role": role})
    connection.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"), {"user_id": str(user_id)}
    )
    if patient_id is not None:
        connection.execute(
            text("SELECT set_config('app.patient_id', :patient_id, true)"),
            {"patient_id": str(patient_id)},
        )


def _patient(connection: Connection) -> tuple[UUID, UUID]:
    user_id, patient_id = uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'patient')"),
        {"id": user_id, "email": f"phase9-{user_id}@example.test"},
    )
    connection.execute(
        text(
            "INSERT INTO patients (id, user_id, display_name) VALUES (:id, :user_id, 'Phase 9 Synthetic')"
        ),
        {"id": patient_id, "user_id": user_id},
    )
    return user_id, patient_id


def test_device_duplicate_is_replayed_and_device_source_is_retained(
    integration_connection: Connection,
) -> None:
    user_id, patient_id = _patient(integration_connection)
    device_id, token = uuid4(), token_urlsafe(32)
    _identity(integration_connection, "patient", user_id, patient_id)
    integration_connection.execute(
        text("""INSERT INTO devices
      (id, patient_id, kind, vendor, status, pairing_token_hash, paired_at, created_by)
      VALUES (:id, :patient_id, 'glucose_meter', 'Synthetic', 'active', :token_hash, now(), :user_id)"""),
        {"id": device_id, "patient_id": patient_id, "token_hash": _hash(token), "user_id": user_id},
    )
    session = Session(bind=integration_connection)
    assert authenticate_device(session, device_id=device_id, token=token) == patient_id
    payload = DeviceReadingRequest(
        type="glucose", value=100, unit="mg/dL", measured_at=datetime.now(UTC)
    )
    first = record_device_reading(
        session,
        device_id=device_id,
        patient_id=patient_id,
        payload=payload,
        idempotency_key="synthetic-duplicate",
        now=datetime.now(UTC),
    )
    second = record_device_reading(
        session,
        device_id=device_id,
        patient_id=patient_id,
        payload=payload,
        idempotency_key="synthetic-duplicate",
        now=datetime.now(UTC),
    )
    assert first["id"] == second["id"]
    older = record_device_reading(
        session,
        device_id=device_id,
        patient_id=patient_id,
        payload=DeviceReadingRequest(
            type="glucose",
            value=99,
            unit="mg/dL",
            measured_at=datetime.now(UTC) - timedelta(minutes=10),
        ),
        idempotency_key="synthetic-out-of-order",
        now=datetime.now(UTC),
    )
    assert older["id"] != first["id"]
    _identity(integration_connection, "patient", user_id, patient_id)
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM observations WHERE device_id = :id AND source = 'device'"),
            {"id": device_id},
        ).scalar_one()
        == 2
    )


def test_unrelated_physician_cannot_read_message_thread(integration_connection: Connection) -> None:
    patient_user, patient_id = _patient(integration_connection)
    physician_user, physician_id = uuid4(), uuid4()
    unrelated_user, unrelated_physician = uuid4(), uuid4()
    integration_connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'physician')"),
        {"id": physician_user, "email": f"phase9-md-{physician_user}@example.test"},
    )
    integration_connection.execute(
        text(
            "INSERT INTO physicians (id, user_id, registration_no) VALUES (:id, :user_id, :registration_no)"
        ),
        {"id": physician_id, "user_id": physician_user, "registration_no": str(physician_id)},
    )
    integration_connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'physician')"),
        {"id": unrelated_user, "email": f"phase9-other-{unrelated_user}@example.test"},
    )
    integration_connection.execute(
        text(
            "INSERT INTO physicians (id, user_id, registration_no) VALUES (:id, :user_id, :registration_no)"
        ),
        {
            "id": unrelated_physician,
            "user_id": unrelated_user,
            "registration_no": str(unrelated_physician),
        },
    )
    consent_id, relationship_id, thread_id = uuid4(), uuid4(), uuid4()
    integration_connection.execute(
        text(
            "INSERT INTO consents (id, patient_id, purpose, version, granted_at) VALUES (:id, :patient_id, 'monitoring', 'phase9', now())"
        ),
        {"id": consent_id, "patient_id": patient_id},
    )
    integration_connection.execute(
        text(
            "INSERT INTO care_relationships (id, patient_id, physician_id, consent_id, status, started_at) VALUES (:id, :patient_id, :physician_id, :consent_id, 'active', now())"
        ),
        {
            "id": relationship_id,
            "patient_id": patient_id,
            "physician_id": physician_id,
            "consent_id": consent_id,
        },
    )
    _identity(integration_connection, "patient", patient_user, patient_id)
    integration_connection.execute(
        text(
            "INSERT INTO message_threads (id, patient_id, physician_id, relationship_id) VALUES (:id, :patient_id, :physician_id, :relationship_id)"
        ),
        {
            "id": thread_id,
            "patient_id": patient_id,
            "physician_id": physician_id,
            "relationship_id": relationship_id,
        },
    )
    _identity(integration_connection, "physician", unrelated_user)
    assert (
        integration_connection.execute(
            text("SELECT id FROM message_threads WHERE id = :id"), {"id": thread_id}
        ).scalar_one_or_none()
        is None
    )


def test_authenticated_fhir_patient_observation_and_bundle_round_trip(
    integration_connection: Connection,
) -> None:
    user_id, patient_id = _patient(integration_connection)
    observation_id = uuid4()
    integration_connection.execute(
        text("""INSERT INTO observations
          (id, patient_id, type, value_num, unit, original_value, original_unit, measured_at, source, context)
          VALUES (:id, :patient_id, 'glucose', 101, 'mg/dL', 101, 'mg/dL', now(), 'manual',
          '{"fhir":{"system":"http://loinc.org","code":"2339-0","specimen":"blood"}}')"""),
        {"id": observation_id, "patient_id": patient_id},
    )
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "patient",
            "mfa": False,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    def session_override():
        yield Session(bind=integration_connection)

    app.dependency_overrides[get_session] = session_override
    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        patient = client.get(f"/api/v1/fhir/Patient/{patient_id}", headers=headers)
        observations = client.get(f"/api/v1/fhir/Observation?patient={patient_id}", headers=headers)
        exported = client.get(f"/api/v1/fhir/Patient/{patient_id}/$everything", headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert patient.status_code == 200
    assert patient.json()["resourceType"] == "Patient"
    assert patient.json()["id"] == str(patient_id)
    assert observations.status_code == 200
    assert observations.json()["resourceType"] == "Bundle"
    assert observations.json()["entry"][0]["resource"]["id"] == str(observation_id)
    assert exported.status_code == 200
    assert exported.json()["resourceType"] == "Bundle"
    assert exported.json()["entry"][0]["resource"]["id"] == str(patient_id)
