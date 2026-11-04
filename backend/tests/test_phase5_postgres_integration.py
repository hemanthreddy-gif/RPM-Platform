"""Opt-in PostgreSQL evidence for Phase 5 medication scheduling protections."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.workers.medication_tasks import generate_scheduled_doses, mark_overdue_unknown


def _worker(connection: Connection) -> None:
    connection.execute(text("SELECT set_config('app.role', 'worker', true)"))


def _seed_schedule(connection: Connection, *, timezone: str = "Asia/Kolkata") -> tuple[UUID, UUID]:
    user_id, patient_id, medication_id, schedule_id = uuid4(), uuid4(), uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'patient')"),
        {"id": user_id, "email": f"phase5-{user_id}@example.test"},
    )
    connection.execute(
        text("""INSERT INTO patients (id, user_id, display_name, timezone)
          VALUES (:id, :user_id, 'Synthetic Phase 5', :timezone)"""),
        {"id": patient_id, "user_id": user_id, "timezone": timezone},
    )
    connection.execute(
        text("""INSERT INTO medications
          (id, patient_id, name, frequency, start_date, version)
          VALUES (:id, :patient_id, 'Synthetic medication', 'once daily', :start_date, 1)"""),
        {"id": medication_id, "patient_id": patient_id, "start_date": date(2026, 11, 4)},
    )
    connection.execute(
        text("""INSERT INTO medication_schedules
          (id, medication_id, timezone, schedule, effective_from)
          VALUES (:id, :medication_id, :timezone,
          '{"times": ["08:00"], "reminder_template_id": "medication.reminder.safe_warning.v1"}', :effective_from)"""),
        {
            "id": schedule_id,
            "medication_id": medication_id,
            "timezone": timezone,
            "effective_from": datetime(2026, 11, 3, tzinfo=UTC),
        },
    )
    return medication_id, schedule_id


def test_generation_is_idempotent_and_uses_asia_kolkata_offset(
    integration_connection: Connection,
) -> None:
    medication_id, _ = _seed_schedule(integration_connection)
    _worker(integration_connection)
    session = Session(bind=integration_connection)
    now = datetime(2026, 11, 4, 0, tzinfo=UTC)
    assert generate_scheduled_doses(session, now=now) == 7
    assert generate_scheduled_doses(session, now=now) == 0
    rows = (
        integration_connection.execute(
            text(
                "SELECT scheduled_for FROM dose_events WHERE medication_id = :id ORDER BY scheduled_for"
            ),
            {"id": medication_id},
        )
        .scalars()
        .all()
    )
    assert len(rows) == 7
    assert rows[0] == datetime(2026, 11, 4, 2, 30, tzinfo=UTC)
    session.close()


def test_schedule_change_supersedes_future_pending_events_without_marking_missed(
    integration_connection: Connection,
) -> None:
    medication_id, old_schedule_id = _seed_schedule(integration_connection)
    _worker(integration_connection)
    session = Session(bind=integration_connection)
    now = datetime(2026, 11, 4, 0, tzinfo=UTC)
    assert generate_scheduled_doses(session, now=now) == 7
    integration_connection.execute(
        text("UPDATE medication_schedules SET effective_to = :now WHERE id = :id"),
        {"now": now, "id": old_schedule_id},
    )
    integration_connection.execute(
        text("""UPDATE dose_events SET schedule_state = 'superseded'
          WHERE medication_id = :id AND status = 'pending'"""),
        {"id": medication_id},
    )
    new_schedule_id = uuid4()
    integration_connection.execute(
        text("""INSERT INTO medication_schedules
          (id, medication_id, timezone, schedule, effective_from)
          VALUES (:id, :medication_id, 'Asia/Kolkata',
          '{"times": ["20:00"], "reminder_template_id": "medication.reminder.safe_warning.v1"}', :now)"""),
        {"id": new_schedule_id, "medication_id": medication_id, "now": now},
    )
    assert generate_scheduled_doses(session, now=now) == 7
    statuses = integration_connection.execute(
        text("SELECT schedule_state, status::text FROM dose_events WHERE medication_id = :id"),
        {"id": medication_id},
    ).all()
    assert statuses.count(("superseded", "pending")) == 7
    assert statuses.count(("active", "pending")) == 7
    session.close()


def test_overdue_dose_becomes_unknown_not_missed(integration_connection: Connection) -> None:
    medication_id, schedule_id = _seed_schedule(integration_connection)
    event_id = uuid4()
    now = datetime(2026, 11, 4, 0, tzinfo=UTC)
    _worker(integration_connection)
    integration_connection.execute(
        text("""INSERT INTO dose_events (id, medication_id, schedule_id, scheduled_for)
          VALUES (:id, :medication_id, :schedule_id, :scheduled_for)"""),
        {
            "id": event_id,
            "medication_id": medication_id,
            "schedule_id": schedule_id,
            "scheduled_for": now - timedelta(minutes=31),
        },
    )
    session = Session(bind=integration_connection)
    assert mark_overdue_unknown(session, now=now, late_window_minutes=30) == 1
    assert (
        integration_connection.execute(
            text("SELECT status::text FROM dose_events WHERE id = :id"), {"id": event_id}
        ).scalar_one()
        == "unknown"
    )
    session.close()


def test_patient_cannot_create_medication_directly(integration_connection: Connection) -> None:
    _, patient_id = uuid4(), uuid4()
    patient_user_id = uuid4()
    integration_connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'patient')"),
        {"id": patient_user_id, "email": f"deny-{patient_user_id}@example.test"},
    )
    integration_connection.execute(
        text("INSERT INTO patients (id, user_id, display_name) VALUES (:id, :user_id, 'Denied')"),
        {"id": patient_id, "user_id": patient_user_id},
    )
    integration_connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    integration_connection.execute(text("SELECT set_config('app.role', 'patient', true)"))
    integration_connection.execute(
        text("SELECT set_config('app.user_id', :id, true)"), {"id": str(patient_user_id)}
    )
    integration_connection.execute(
        text("SELECT set_config('app.patient_id', :id, true)"), {"id": str(patient_id)}
    )
    with pytest.raises(DatabaseError):
        integration_connection.execute(
            text("""INSERT INTO medications (id, patient_id, name, frequency, start_date, version)
              VALUES (:id, :patient_id, 'Denied', 'daily', :start_date, 1)"""),
            {"id": uuid4(), "patient_id": patient_id, "start_date": date(2026, 11, 4)},
        )


def test_patient_cannot_edit_medication_directly(integration_connection: Connection) -> None:
    medication_id, _ = _seed_schedule(integration_connection)
    patient = integration_connection.execute(
        text("SELECT patient_id FROM medications WHERE id = :id"), {"id": medication_id}
    ).scalar_one()
    patient_user_id = integration_connection.execute(
        text("SELECT user_id FROM patients WHERE id = :id"), {"id": patient}
    ).scalar_one()
    integration_connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    integration_connection.execute(text("SELECT set_config('app.role', 'patient', true)"))
    integration_connection.execute(
        text("SELECT set_config('app.user_id', :id, true)"), {"id": str(patient_user_id)}
    )
    integration_connection.execute(
        text("SELECT set_config('app.patient_id', :id, true)"), {"id": str(patient)}
    )
    with pytest.raises(DatabaseError):
        integration_connection.execute(
            text("UPDATE medications SET name = 'Patient edit' WHERE id = :id"),
            {"id": medication_id},
        )
