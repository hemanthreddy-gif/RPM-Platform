"""Opt-in PostgreSQL evidence for Phase 4 transactional and access-control behaviour."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clinical_rules.models import AlertDecision
from app.modules.alerts.notifications import DeliveryResult, InAppAdapter, dispatch_pending
from app.modules.alerts.service import persist_decisions, transition
from app.modules.audit.service import record
from app.workers.alert_tasks import escalate_due


def _worker(connection: Connection) -> None:
    connection.execute(text("SELECT set_config('app.role', 'worker', true)"))


def _patient(connection: Connection) -> tuple[UUID, UUID]:
    user_id, patient_id = uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'patient')"),
        {"id": user_id, "email": f"synthetic-{user_id}@example.test"},
    )
    connection.execute(
        text(
            "INSERT INTO patients (id, user_id, display_name) VALUES (:id, :user_id, 'Synthetic Test')"
        ),
        {"id": patient_id, "user_id": user_id},
    )
    return user_id, patient_id


def _observation(connection: Connection, patient_id: UUID, value: int = 53) -> UUID:
    observation_id = uuid4()
    connection.execute(
        text("""INSERT INTO observations (id, patient_id, type, value_num, unit, original_value,
          original_unit, measured_at, source, context) VALUES
          (:id, :patient_id, 'glucose', :value, 'mg/dL', :value, 'mg/dL', :now, 'manual', '{}')"""),
        {"id": observation_id, "patient_id": patient_id, "value": value, "now": datetime.now(UTC)},
    )
    return observation_id


def _decision() -> AlertDecision:
    return AlertDecision(
        rule_code="TEST_URGENT",
        rule_version=1,
        severity="urgent",
        message_key="glucose.low.urgent",
        dedupe_window_min=60,
        urgent_guidance=True,
    )


def _alert(connection: Connection, patient_id: UUID) -> UUID:
    session = Session(bind=connection)
    result = persist_decisions(
        session,
        patient_id=patient_id,
        observation_id=_observation(connection, patient_id),
        decisions=[_decision()],
        evaluation_time=datetime.now(UTC),
    )
    session.close()
    return UUID(str(result[0]["id"]))


def test_trigger_outbox_audit_are_atomic_and_deduplicated(
    integration_connection: Connection,
) -> None:
    _worker(integration_connection)
    user_id, patient_id = _patient(integration_connection)
    observation_id = _observation(integration_connection, patient_id)
    session = Session(bind=integration_connection)
    first = persist_decisions(
        session,
        patient_id=patient_id,
        observation_id=observation_id,
        decisions=[_decision()],
        evaluation_time=datetime.now(UTC),
    )
    second = persist_decisions(
        session,
        patient_id=patient_id,
        observation_id=observation_id,
        decisions=[_decision()],
        evaluation_time=datetime.now(UTC),
    )
    record(
        session,
        actor_id=user_id,
        actor_role="patient",
        action="observation.create",
        resource_type="observation",
        resource_id=observation_id,
        patient_id=patient_id,
    )
    assert first[0]["deduplicated"] is False and second[0]["deduplicated"] is True
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM alerts WHERE patient_id = :id"), {"id": patient_id}
        ).scalar_one()
        == 1
    )
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM alert_events WHERE alert_id = :id"),
            {"id": UUID(str(first[0]["id"]))},
        ).scalar_one()
        == 2
    )
    assert (
        integration_connection.execute(
            text(
                "SELECT count(*) FROM outbox_events WHERE event_type = 'AlertNotificationRequested'"
            )
        ).scalar_one()
        == 1
    )
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM audit_log WHERE patient_id = :id"), {"id": patient_id}
        ).scalar_one()
        == 1
    )
    session.close()


def test_lifecycle_enforces_legal_transitions_and_auditable_state(
    integration_connection: Connection,
) -> None:
    _worker(integration_connection)
    clinician_id, patient_id = _patient(integration_connection)
    alert_id = _alert(integration_connection, patient_id)
    session = Session(bind=integration_connection)
    with pytest.raises(ValueError, match="Illegal"):
        transition(session, alert_id=alert_id, actor_id=clinician_id, action="resolve")
    transition(session, alert_id=alert_id, actor_id=clinician_id, action="acknowledge")
    transition(session, alert_id=alert_id, actor_id=clinician_id, action="resolve")
    with pytest.raises(ValueError, match="Illegal"):
        transition(session, alert_id=alert_id, actor_id=clinician_id, action="acknowledge")
    assert (
        integration_connection.execute(
            text("SELECT status::text FROM alerts WHERE id = :id"), {"id": alert_id}
        ).scalar_one()
        == "resolved"
    )
    session.close()


class _FailingAdapter(InAppAdapter):
    def deliver(self, alert_id: UUID) -> DeliveryResult:
        del alert_id
        return DeliveryResult(delivered=False, error="synthetic failure")


def test_delivery_retries_then_dead_letters_idempotently(
    integration_connection: Connection,
) -> None:
    _worker(integration_connection)
    _, patient_id = _patient(integration_connection)
    _alert(integration_connection, patient_id)
    session = Session(bind=integration_connection)
    now = datetime.now(UTC)
    for attempt in range(3):
        dispatch_pending(
            session, adapter=_FailingAdapter(), now=now + timedelta(hours=attempt), max_attempts=3
        )
    row = integration_connection.execute(
        text("SELECT attempts, dead_lettered_at IS NOT NULL FROM job_attempts")
    ).one()
    delivery = integration_connection.execute(
        text("SELECT status, attempts FROM notification_deliveries")
    ).one()
    assert row == (3, True)
    assert delivery == ("dead_lettered", 3)
    assert (
        dispatch_pending(
            session, adapter=_FailingAdapter(), now=now + timedelta(days=1), max_attempts=3
        )
        == 0
    )
    session.close()


def test_urgent_alert_escalates_once_after_fixture_30_minute_timeline(
    integration_connection: Connection,
) -> None:
    _worker(integration_connection)
    _, patient_id = _patient(integration_connection)
    alert_id = _alert(integration_connection, patient_id)
    now = datetime.now(UTC)
    integration_connection.execute(
        text("UPDATE alerts SET created_at = :created_at WHERE id = :id"),
        {"created_at": now - timedelta(minutes=30), "id": alert_id},
    )
    session = Session(bind=integration_connection)
    assert escalate_due(session, now=now) == 1
    assert escalate_due(session, now=now + timedelta(minutes=1)) == 0
    assert integration_connection.execute(
        text("SELECT status::text, escalation_level FROM alerts WHERE id = :id"),
        {"id": alert_id},
    ).one() == ("escalated", 1)
    session.close()


def test_worker_physician_consent_and_admin_rls(integration_connection: Connection) -> None:
    _worker(integration_connection)
    _, patient_id = _patient(integration_connection)
    alert_id = _alert(integration_connection, patient_id)
    physician_user, physician_id, consent_id = uuid4(), uuid4(), uuid4()
    integration_connection.execute(
        text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'physician')"),
        {"id": physician_user, "email": f"physician-{physician_user}@example.test"},
    )
    integration_connection.execute(
        text(
            "INSERT INTO physicians (id, user_id, registration_no) VALUES (:id, :user_id, :registration_no)"
        ),
        {"id": physician_id, "user_id": physician_user, "registration_no": str(physician_id)},
    )
    integration_connection.execute(
        text(
            "INSERT INTO consents (id, patient_id, purpose, version, granted_at) VALUES (:id, :patient_id, 'monitoring', 'synthetic-v1', now())"
        ),
        {"id": consent_id, "patient_id": patient_id},
    )
    integration_connection.execute(
        text(
            "INSERT INTO care_relationships (id, patient_id, physician_id, consent_id, status, started_at) VALUES (:id, :patient_id, :physician_id, :consent_id, 'active', now())"
        ),
        {
            "id": uuid4(),
            "patient_id": patient_id,
            "physician_id": physician_id,
            "consent_id": consent_id,
        },
    )
    # The migration owner may be a local PostgreSQL superuser; exercise RLS as the restricted
    # runtime role rather than relying on owner semantics.
    integration_connection.execute(text("SET LOCAL ROLE rpm_runtime"))
    integration_connection.execute(text("SELECT set_config('app.role', 'physician', true)"))
    integration_connection.execute(
        text("SELECT set_config('app.user_id', :id, true)"), {"id": str(physician_user)}
    )
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM alerts WHERE id = :id"), {"id": alert_id}
        ).scalar_one()
        == 1
    )
    integration_connection.execute(text("SELECT set_config('app.role', 'admin', true)"))
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM alerts WHERE id = :id"), {"id": alert_id}
        ).scalar_one()
        == 0
    )


def test_correction_history_is_append_only_and_savepoint_rolls_back(
    integration_connection: Connection,
) -> None:
    _worker(integration_connection)
    _, patient_id = _patient(integration_connection)
    original = _observation(integration_connection, patient_id, value=100)
    with pytest.raises(Exception, match="immutable"):
        with integration_connection.begin_nested():
            integration_connection.execute(
                text("UPDATE observations SET value_num = 101 WHERE id = :id"), {"id": original}
            )
    corrected = uuid4()
    integration_connection.execute(
        text("""INSERT INTO observations (id, patient_id, type, value_num, unit, original_value,
          original_unit, measured_at, source, context, supersedes_id) VALUES
          (:id, :patient_id, 'glucose', 101, 'mg/dL', 101, 'mg/dL', :now, 'manual', '{}', :original)"""),
        {"id": corrected, "patient_id": patient_id, "now": datetime.now(UTC), "original": original},
    )
    assert (
        integration_connection.execute(
            text("SELECT count(*) FROM observations WHERE patient_id = :id"), {"id": patient_id}
        ).scalar_one()
        == 2
    )


def test_concurrent_idempotency_key_has_one_winner(integration_connection: Connection) -> None:
    url = getenv("DATABASE_URL", "")
    if "/rpm_test" not in url:
        pytest.skip("integration tests require rpm_test")
    actor, key = uuid4(), f"concurrent-{uuid4()}"
    engine = create_engine(url)

    def attempt() -> bool:
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO idempotency_records (id, actor_or_device_id, operation, key, request_hash) VALUES (:id, :actor, 'observation.create', :key, 'hash')"
                    ),
                    {"id": uuid4(), "actor": actor, "key": key},
                )
            return True
        except IntegrityError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt(), range(2)))
    integration_connection.execute(
        text("DELETE FROM idempotency_records WHERE actor_or_device_id = :actor AND key = :key"),
        {"actor": actor, "key": key},
    )
    engine.dispose()
    assert sorted(outcomes) == [False, True]
