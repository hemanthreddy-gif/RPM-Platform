"""PostgreSQL authorization, audit, revocation and sleep transaction regressions."""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.modules.identity.schemas import Principal
from app.modules.messaging.authorization import require_thread
from app.modules.observations.router import create_observation
from app.modules.observations.schemas import ObservationCreate
from app.modules.patients import service
from app.modules.patients.authorization import set_database_identity
from app.modules.patients.schemas import ProfileUpdate


def _principal(user_id: UUID, role: str = "patient") -> Principal:
    return Principal(
        user_id=user_id,
        role=role,
        mfa=role != "patient",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def _seed(connection: Connection) -> tuple[Principal, UUID, Principal, UUID]:
    user_id, patient_id, doctor_user, doctor_id = [uuid4() for _ in range(4)]
    connection.execute(
        text("""INSERT INTO users (id, email, role, mfa_enabled)
        VALUES (:id, :email, 'patient', false), (:doctor, :doctor_email, 'physician', true)"""),
        {
            "id": user_id,
            "email": f"profile-{user_id}@example.invalid",
            "doctor": doctor_user,
            "doctor_email": f"physician-{doctor_user}@example.invalid",
        },
    )
    connection.execute(
        text("""INSERT INTO patients (id, user_id, display_name)
        VALUES (:id, :user, 'Synthetic Profile')"""),
        {"id": patient_id, "user": user_id},
    )
    connection.execute(
        text("""INSERT INTO physicians (id, user_id, registration_no, display_name)
        VALUES (:id, :user, :registration, 'Synthetic Physician')"""),
        {"id": doctor_id, "user": doctor_user, "registration": str(doctor_id)},
    )
    connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    return _principal(user_id), patient_id, _principal(doctor_user, "physician"), doctor_id


def test_ending_one_connection_preserves_another_using_shared_consent(
    integration_connection: Connection,
) -> None:
    principal, patient_id, physician, physician_id = _seed(integration_connection)
    session = Session(bind=integration_connection)
    first = service.connect_physician(session, principal, physician_id)
    integration_connection.execute(text("RESET ROLE"))
    other_user, other_physician, other_relationship = uuid4(), uuid4(), uuid4()
    session.execute(
        text(
            "INSERT INTO users (id, email, role, mfa_enabled) "
            "VALUES (:id, :email, 'physician', true)"
        ),
        {"id": other_user, "email": f"shared-{other_user}@example.invalid"},
    )
    session.execute(
        text("INSERT INTO physicians (id, user_id, registration_no) VALUES (:id, :user, :reg)"),
        {"id": other_physician, "user": other_user, "reg": str(other_physician)},
    )
    session.execute(
        text("""INSERT INTO care_relationships
        (id, patient_id, physician_id, consent_id, status, started_at)
        VALUES (:id, :patient, :physician, :consent, 'active', now())"""),
        {
            "id": other_relationship,
            "patient": patient_id,
            "physician": other_physician,
            "consent": first["consent_id"],
        },
    )
    integration_connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    service.disconnect_physician(session, principal, UUID(str(first["id"])))
    with pytest.raises(HTTPException):
        service.read_profile(session, physician, patient_id)
    assert (
        service.read_profile(session, _principal(other_user, "physician"), patient_id)["id"]
        == patient_id
    )
    assert (
        session.execute(
            text("SELECT revoked_at FROM consents WHERE id = :id"), {"id": first["consent_id"]}
        ).scalar_one()
        is None
    )
    service.disconnect_physician(session, principal, other_relationship)
    assert (
        session.execute(
            text("SELECT revoked_at FROM consents WHERE id = :id"), {"id": first["consent_id"]}
        ).scalar_one()
        is not None
    )
    session.close()


def test_profile_and_picture_are_private_audited_and_revocation_is_immediate(
    integration_connection: Connection,
) -> None:
    principal, patient_id, physician, physician_id = _seed(integration_connection)
    session = Session(bind=integration_connection)
    profile = service.update_profile(
        session,
        principal,
        ProfileUpdate(display_name="Fictional Patient", height_cm=170, weight_kg=70),
    )
    assert profile["display_name"] == "Fictional Patient"
    image = BytesIO()
    Image.new("RGB", (30, 30), "green").save(image, format="PNG")
    service.update_picture(session, principal, image.getvalue(), "image/png")
    with pytest.raises(HTTPException) as denied:
        service.read_picture(session, physician, patient_id)
    assert denied.value.status_code == 403
    connection = service.connect_physician(session, principal, physician_id)
    assert service.connect_physician(session, principal, physician_id)["id"] == connection["id"]
    assert service.read_profile(session, physician, patient_id)["height_cm"] == 170
    assert service.read_picture(session, physician, patient_id).startswith(b"\xff\xd8")
    service.disconnect_physician(session, principal, UUID(str(connection["id"])))
    assert service.list_connections(session, principal)[0]["active"] is False
    with pytest.raises(HTTPException) as revoked:
        service.read_picture(session, physician, patient_id)
    assert revoked.value.status_code == 403
    # RLS independently denies the same read, even without application authorization.
    assert (
        session.execute(
            text("SELECT profile_picture FROM patients WHERE id = :id"), {"id": patient_id}
        ).scalar_one_or_none()
        is None
    )
    with pytest.raises(HTTPException):
        service.read_profile(session, _principal(uuid4(), "admin"), patient_id)
    assert (
        integration_connection.execute(
            text("""SELECT count(*) FROM audit_log
        WHERE patient_id = :id AND action = 'patient.picture.read'"""),
            {"id": patient_id},
        ).scalar_one()
        == 1
    )
    assert (
        integration_connection.execute(
            text("""SELECT count(*) FROM care_relationships
        WHERE patient_id = :id"""),
            {"id": patient_id},
        ).scalar_one()
        == 1
    )


def test_patient_cannot_read_other_profile_or_disconnect_other_patient(
    integration_connection: Connection,
) -> None:
    principal, patient_id, _, physician_id = _seed(integration_connection)
    session = Session(bind=integration_connection)
    connection = service.connect_physician(session, principal, physician_id)
    outsider = _principal(uuid4())
    with pytest.raises(HTTPException):
        service.read_profile(session, outsider, patient_id)
    with pytest.raises(HTTPException):
        service.disconnect_physician(session, outsider, UUID(str(connection["id"])))
    assert service.list_connections(session, principal)[0]["active"] is True


def test_sleep_uses_observation_transaction_replay_and_never_calls_rules(
    integration_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal, patient_id, _, _ = _seed(integration_connection)
    session = Session(bind=integration_connection, join_transaction_mode="create_savepoint")

    def must_not_evaluate(*args: object, **kwargs: object) -> None:
        raise AssertionError("Self-reported sleep must not reach clinical rules")

    monkeypatch.setattr("app.modules.observations.router.evaluate_and_persist", must_not_evaluate)
    payload = ObservationCreate(
        type="sleep", value=0, unit="h", measured_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    request = Request({"type": "http", "client": ("127.0.0.1", 1234)})
    key = str(uuid4())
    result = create_observation(payload, request, key, principal, session)
    replay = create_observation(payload, request, key, principal, session)
    assert result["id"] == replay["id"]
    assert result["alerts"] == []
    assert (
        session.execute(
            text("SELECT count(*) FROM observations WHERE patient_id = :id"), {"id": patient_id}
        ).scalar_one()
        == 1
    )
    assert (
        session.execute(
            text("""SELECT count(*) FROM audit_log
        WHERE patient_id = :id AND action = 'observation.create'"""),
            {"id": patient_id},
        ).scalar_one()
        == 1
    )
    assert (
        session.execute(
            text("""SELECT count(*) FROM outbox_events
        WHERE event_type = 'ObservationRecorded' AND payload_ref->>'patient_id' = :id"""),
            {"id": str(patient_id)},
        ).scalar_one()
        == 1
    )
    session.close()


def test_conversation_requires_exact_participant_and_live_consent(
    integration_connection: Connection,
) -> None:
    principal, patient_id, physician, physician_id = _seed(integration_connection)
    session = Session(bind=integration_connection)
    relationship = service.connect_physician(session, principal, physician_id)
    thread_id = uuid4()
    session.execute(
        text("""INSERT INTO message_threads (id, patient_id, physician_id, relationship_id)
        VALUES (:id, :patient, :physician, :relationship)"""),
        {
            "id": thread_id,
            "patient": patient_id,
            "physician": physician_id,
            "relationship": relationship["id"],
        },
    )
    assert require_thread(session, principal, thread_id)["id"] == thread_id
    assert require_thread(session, physician, thread_id)["id"] == thread_id
    # A second physician with their own active connection still cannot read this conversation.
    integration_connection.execute(text("RESET ROLE"))
    other_user, other_physician = uuid4(), uuid4()
    session.execute(
        text("""INSERT INTO users (id, email, role, mfa_enabled)
        VALUES (:id, :email, 'physician', true)"""),
        {"id": other_user, "email": f"other-{other_user}@example.invalid"},
    )
    session.execute(
        text("""INSERT INTO physicians (id, user_id, registration_no)
        VALUES (:id, :user, :registration)"""),
        {"id": other_physician, "user": other_user, "registration": str(other_physician)},
    )
    integration_connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    service.connect_physician(session, principal, other_physician)
    with pytest.raises(HTTPException):
        require_thread(session, _principal(other_user, "physician"), thread_id)
    assert (
        session.execute(
            text("SELECT id FROM message_threads WHERE id = :id"), {"id": thread_id}
        ).scalar_one_or_none()
        is None
    )
    service.disconnect_physician(session, principal, UUID(str(relationship["id"])))
    for actor in (principal, physician):
        with pytest.raises(HTTPException):
            require_thread(session, actor, thread_id)
        set_database_identity(session, actor)
        assert (
            session.execute(
                text("SELECT id FROM message_threads WHERE id = :id"), {"id": thread_id}
            ).scalar_one_or_none()
            is None
        )
    session.close()
