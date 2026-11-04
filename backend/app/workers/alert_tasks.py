"""Persistent outbox delivery and escalation workers; no AI or rule loading occurs here."""

from datetime import UTC, datetime, timedelta
from json import dumps
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clinical_rules.evaluator import evaluate_no_data, evaluate_patterns
from app.clinical_rules.loader import load_rules
from app.clinical_rules.models import Observation, PatientContext
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.alerts.notifications import InAppAdapter, dispatch_pending
from app.modules.alerts.service import persist_decisions
from app.workers.celery_app import celery_app


def _set_worker_identity(session: object) -> None:
    """Only server-launched workers may establish this transaction-local worker identity."""
    session.execute(text("SELECT set_config('app.role', 'worker', true)"))  # type: ignore[attr-defined]


@celery_app.task(name="alerts.dispatch_outbox")
def dispatch_outbox() -> int:
    """Deliver pending alert outbox rows at-least-once with persistent retry state."""
    with SessionLocal() as session:
        _set_worker_identity(session)
        delivered = dispatch_pending(
            session,
            adapter=InAppAdapter(),
            now=datetime.now(UTC),
            max_attempts=get_settings().notification_max_attempts,
        )
        session.commit()
    return delivered


@celery_app.task(name="alerts.escalate_unacknowledged")
def escalate_unacknowledged() -> int:
    """Escalate synthetic urgent alerts after the reviewed-fixture timeline (30 minutes)."""
    with SessionLocal() as session:
        _set_worker_identity(session)
        escalated = escalate_due(session, now=datetime.now(UTC))
        session.commit()
        return escalated


def escalate_due(session: Session, *, now: datetime) -> int:
    """Persist one escalation event and request per due urgent alert."""
    cutoff = now - timedelta(minutes=30)
    rows = (
        session.execute(
            text("""SELECT id, patient_id FROM alerts WHERE severity = 'urgent'
              AND status IN ('open', 'notified') AND created_at <= :cutoff FOR UPDATE SKIP LOCKED"""),
            {"cutoff": cutoff},
        )
        .mappings()
        .all()
    )
    for row in rows:
        session.execute(
            text(
                "UPDATE alerts SET status = 'escalated', escalation_level = escalation_level + 1 WHERE id = :id"
            ),
            {"id": row["id"]},
        )
        session.execute(
            text("""INSERT INTO alert_events (id, alert_id, event_type, severity, details)
              VALUES (:id, :alert_id, 'escalated', 'urgent', '{}')"""),
            {"id": uuid4(), "alert_id": row["id"]},
        )
        session.execute(
            text("""INSERT INTO outbox_events (id, event_type, payload_ref)
              VALUES (:id, 'AlertNotificationRequested', CAST(:payload AS jsonb))"""),
            {
                "id": uuid4(),
                "payload": '{"alert_id": "'
                + str(row["id"])
                + '", "patient_id": "'
                + str(row["patient_id"])
                + '"}',
            },
        )
    return len(rows)


@celery_app.task(name="alerts.check_no_data")
def check_no_data() -> int:
    """Schedule synthetic-demo no-data notices using the configured explicit intervals."""
    settings = get_settings()
    if not settings.synthetic_demo_rules_enabled:
        return 0
    now = datetime.now(UTC)
    created = 0
    with SessionLocal() as session:
        _set_worker_identity(session)
        patients = session.execute(text("SELECT id FROM patients")).scalars().all()
        for observation_type, days in (
            ("glucose", settings.synthetic_demo_no_data_glucose_days),
            ("blood_pressure", settings.synthetic_demo_no_data_bp_days),
        ):
            for patient_id in patients:
                last = session.execute(
                    text("""SELECT max(measured_at) FROM observations WHERE patient_id = :patient_id
                      AND type = CAST(:type AS observation_type)"""),
                    {"patient_id": patient_id, "type": observation_type},
                ).scalar_one()
                decision = evaluate_no_data(
                    observation_type=observation_type,
                    last_measured_at=last,
                    evaluation_time=now,
                    days=days,
                )
                if decision is None:
                    continue
                exists = session.execute(
                    text(
                        "SELECT 1 FROM alerts WHERE patient_id = :patient_id AND rule_code = :code AND status <> 'resolved'"
                    ),
                    {"patient_id": patient_id, "code": decision.rule_code},
                ).scalar()
                if exists:
                    continue
                alert_id = uuid4()
                session.execute(
                    text(
                        "INSERT INTO alerts (id, patient_id, rule_code, rule_version, severity, dedupe_key) VALUES (:id, :patient_id, :code, 1, 'informational', :dedupe_key)"
                    ),
                    {
                        "id": alert_id,
                        "patient_id": patient_id,
                        "code": decision.rule_code,
                        "dedupe_key": f"{patient_id}:{decision.rule_code}",
                    },
                )
                session.execute(
                    text(
                        "INSERT INTO alert_events (id, alert_id, event_type, severity, details) VALUES (:id, :alert_id, 'triggered', 'informational', '{}')"
                    ),
                    {"id": uuid4(), "alert_id": alert_id},
                )
                session.execute(
                    text("""INSERT INTO outbox_events (id, event_type, payload_ref)
                      VALUES (:id, 'AlertNotificationRequested', CAST(:payload AS jsonb))"""),
                    {
                        "id": uuid4(),
                        "payload": dumps(
                            {"alert_id": str(alert_id), "patient_id": str(patient_id)}
                        ),
                    },
                )
                created += 1
        session.commit()
    return created


@celery_app.task(name="alerts.check_target_patterns")
def check_target_patterns() -> int:
    """Evaluate only explicit physician targets and immutable observation facts."""
    settings = get_settings()
    if not settings.synthetic_demo_rules_enabled:
        return 0
    now = datetime.now(UTC)
    created = 0
    rules = load_rules(Path(__file__).parents[2] / "rules")
    with SessionLocal() as session:
        _set_worker_identity(session)
        for patient_id in session.execute(text("SELECT id FROM patients")).scalars():
            target_rows = session.execute(
                text("""SELECT DISTINCT ON (type, context) type::text, context, low, high
              FROM monitoring_targets WHERE patient_id = :patient_id
              ORDER BY type, context, version DESC"""),
                {"patient_id": patient_id},
            ).mappings()
            targets = {
                f"{row['type']}.{row['context']}": (row["low"], row["high"]) for row in target_rows
            }
            history_rows = session.execute(
                text("""SELECT type::text, value_num, components, context, measured_at
              FROM observations o WHERE patient_id = :patient_id
              AND NOT EXISTS (SELECT 1 FROM observations child WHERE child.supersedes_id = o.id)
              AND measured_at >= :cutoff ORDER BY measured_at DESC"""),
                {"patient_id": patient_id, "cutoff": now - timedelta(days=7)},
            ).mappings()
            history = [
                Observation(
                    type=row["type"],
                    value=row["value_num"],
                    components=row["components"],
                    context=row["context"],
                    measured_at=row["measured_at"],
                )
                for row in history_rows
            ]
            decisions = evaluate_patterns(
                PatientContext(targets=targets, history=history), rules, now
            )
            created += sum(
                not item["deduplicated"]
                for item in persist_decisions(
                    session,
                    patient_id=patient_id,
                    observation_id=None,
                    decisions=decisions,
                    evaluation_time=now,
                )
            )
        session.commit()
    return created
