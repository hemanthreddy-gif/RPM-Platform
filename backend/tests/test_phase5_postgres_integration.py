"""Opt-in PostgreSQL evidence for Phase 5 medication scheduling protections."""

from datetime import UTC, date, datetime, time, timedelta
from json import dumps
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.modules.medications.schemas import MedicationRequest
from app.modules.medications.service import (
    adherence_summary,
    create_version,
    list_current,
    report_dose,
)
from app.workers.medication_tasks import (
    MedicationInAppAdapter,
    dispatch_medication_reminders,
    generate_scheduled_doses,
    mark_overdue_unknown,
)


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


def _physician_access(connection: Connection, patient_id: UUID) -> UUID:
    user_id, physician_id, consent_id = uuid4(), uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'physician')"),
        {"id": user_id, "email": f"physician-{user_id}@example.test"},
    )
    connection.execute(
        text("""INSERT INTO physicians (id, user_id, registration_no)
          VALUES (:id, :user_id, :registration_no)"""),
        {"id": physician_id, "user_id": user_id, "registration_no": str(physician_id)},
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
    connection.execute(text("SELECT set_config('app.role', 'physician', true)"))
    connection.execute(text("SELECT set_config('app.user_id', :id, true)"), {"id": str(user_id)})
    return user_id


def _request(schedule_time: time = time(8)) -> MedicationRequest:
    return MedicationRequest(
        name="Synthetic medication",
        strength="10 mg",
        dose="one tablet",
        route="oral",
        frequency="daily",
        schedule_times=[schedule_time],
        start_date=date(2026, 11, 4),
        instructions="Synthetic physician-authored instructions.",
    )


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


def test_version_reporting_adherence_and_concern_provenance(
    integration_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, schedule_id = _seed_schedule(integration_connection)
    patient_id = integration_connection.execute(
        text(
            "SELECT patient_id FROM medications WHERE id = (SELECT medication_id FROM medication_schedules WHERE id = :id)"
        ),
        {"id": schedule_id},
    ).scalar_one()
    physician_user_id = _physician_access(integration_connection, patient_id)
    session = Session(bind=integration_connection)
    created = create_version(
        session,
        patient_id=patient_id,
        actor_id=physician_user_id,
        payload=_request(),
    )
    assert UUID(str(created["id"]))
    assert created["provenance"] == "physician_authored_synthetic_record"
    assert list_current(session, patient_id=patient_id)[-1]["authored_by"] == str(physician_user_id)
    _worker(integration_connection)
    now = datetime(2026, 11, 4, 0, tzinfo=UTC)
    assert generate_scheduled_doses(session, now=now) == 7
    dose_event_id, reported_medication_id = integration_connection.execute(
        text("SELECT id, medication_id FROM dose_events ORDER BY scheduled_for LIMIT 1")
    ).one()
    patient_user_id = integration_connection.execute(
        text("SELECT user_id FROM patients WHERE id = :id"), {"id": patient_id}
    ).scalar_one()
    integration_connection.execute(text("SELECT set_config('app.role', 'patient', true)"))
    integration_connection.execute(
        text("SELECT set_config('app.user_id', :id, true)"), {"id": str(patient_user_id)}
    )
    integration_connection.execute(
        text("SELECT set_config('app.patient_id', :id, true)"), {"id": str(patient_id)}
    )
    monkeypatch.setattr(
        "app.modules.medications.service.get_settings",
        lambda: SimpleNamespace(synthetic_demo_rules_enabled=True),
    )
    response, response_patient_id = report_dose(
        session,
        dose_event_id=dose_event_id,
        patient_user_id=patient_user_id,
        status="missed",
        reported_at=now,
        concern_note="Synthetic concern for physician review.",
    )
    assert response_patient_id == patient_id
    assert response["self_reported"] is True
    assert response["concern_flagged_for_physician"] is True
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM medication_concern_flags WHERE patient_id = :id"),
            {"id": patient_id},
        ).scalar_one()
        == 1
    )
    assert (
        integration_connection.execute(
            text(
                "SELECT count(*) FROM alerts WHERE patient_id = :id AND rule_code = 'MED_MISSED_PATTERN'"
            ),
            {"id": patient_id},
        ).scalar_one()
        == 1
    )
    summary = adherence_summary(session, patient_id=patient_id, days=7, now=now + timedelta(days=1))
    assert summary["self_reported"] is True
    assert summary["percentage"] == 0
    assert summary["missed_dose_pattern"] == [
        {"medication_id": str(reported_medication_id), "self_reported_missed_count": 1}
    ]
    session.close()


def test_reminder_dispatch_preserves_sent_and_expired_delivery_evidence(
    integration_connection: Connection,
) -> None:
    medication_id, schedule_id = _seed_schedule(integration_connection)
    _worker(integration_connection)
    session = Session(bind=integration_connection)
    now = datetime(2026, 11, 4, 0, tzinfo=UTC)
    for scheduled_for, template_id in (
        (now, "medication.reminder.safe_warning.v1"),
        (now - timedelta(minutes=31), "medication.reminder.safe_warning.v1"),
    ):
        dose_event_id = uuid4()
        session.execute(
            text("""INSERT INTO dose_events (id, medication_id, schedule_id, scheduled_for)
              VALUES (:id, :medication_id, :schedule_id, :scheduled_for)"""),
            {
                "id": dose_event_id,
                "medication_id": medication_id,
                "schedule_id": schedule_id,
                "scheduled_for": scheduled_for,
            },
        )
        session.execute(
            text("""INSERT INTO outbox_events (id, event_type, payload_ref)
              VALUES (:id, 'MedicationReminderRequested', CAST(:payload AS jsonb))"""),
            {
                "id": uuid4(),
                "payload": dumps(
                    {
                        "dose_event_id": str(dose_event_id),
                        "scheduled_for": scheduled_for.isoformat(),
                        "template_id": template_id,
                    }
                ),
            },
        )
    assert MedicationInAppAdapter().channel == "in_app"
    assert (
        dispatch_medication_reminders(
            session,
            adapter=MedicationInAppAdapter(),
            now=now,
            late_window_minutes=30,
            max_attempts=3,
        )
        == 1
    )
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM medication_reminder_deliveries WHERE status = 'sent'")
        ).scalar_one()
        == 1
    )
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM medication_reminder_deliveries WHERE status = 'expired'")
        ).scalar_one()
        == 1
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
    result = integration_connection.execute(
        text("UPDATE medications SET name = 'Patient edit' WHERE id = :id"),
        {"id": medication_id},
    )
    assert result.rowcount == 0
