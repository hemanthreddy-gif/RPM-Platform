"""Alert orchestration; deterministic decisions arrive from the isolated rules package."""

from datetime import datetime, timedelta
from json import dumps
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clinical_rules.evaluator import evaluate
from app.clinical_rules.loader import load_rules
from app.clinical_rules.models import AlertDecision, Observation, PatientContext
from app.core.config import get_settings

_RULES = load_rules(Path(__file__).parents[3] / "rules")
_MESSAGES = {
    "glucose.low.urgent": "Urgent synthetic-demo alert. This app is not an emergency service.",
    "glucose.high.urgent": "Urgent synthetic-demo alert. This app is not an emergency service.",
    "bp.crisis.urgent": "Urgent synthetic-demo alert. This app is not an emergency service.",
    "bp.low.attention": "Synthetic-demo attention alert. This is not clinical guidance.",
    "glucose.low.attention": "Synthetic-demo attention alert. This is not clinical guidance.",
    "spo2.low.attention": "Synthetic-demo attention alert. This is not clinical guidance.",
    "spo2.low.urgent": "Urgent synthetic-demo alert. This app is not an emergency service.",
    "glucose.fasting_pattern.attention": "Synthetic-demo target-pattern alert. This is not clinical guidance.",
    "bp.target_average.attention": "Synthetic-demo target-pattern alert. This is not clinical guidance.",
    "no_data.informational": "Synthetic-demo no-data alert. This is not clinical guidance.",
    "medication.missed.self_reported": (
        "Synthetic-demo notice of a self-reported missed dose. This is not medication advice."
    ),
}


def evaluate_and_persist(
    session: Session,
    *,
    patient_id: UUID,
    observation_id: UUID,
    observation: Observation,
    evaluation_time: datetime,
) -> list[dict[str, object]]:
    """Persist decisions/events/outbox work in the caller's observation transaction."""
    if not get_settings().synthetic_demo_rules_enabled:
        return []
    decisions = evaluate(observation, PatientContext(), _RULES, evaluation_time)
    return persist_decisions(
        session,
        patient_id=patient_id,
        observation_id=observation_id,
        decisions=decisions,
        evaluation_time=evaluation_time,
    )


def persist_decisions(
    session: Session,
    *,
    patient_id: UUID,
    observation_id: UUID | None,
    decisions: list[AlertDecision],
    evaluation_time: datetime,
) -> list[dict[str, object]]:
    """Persist already-made pure decisions inside the caller's existing transaction.

    The per-patient/rule transaction advisory lock makes the open-episode check safe under
    concurrent workers. Exact dedupe-window boundaries start a new episode (strict `>`).
    """
    alerts: list[dict[str, object]] = []
    for decision in decisions:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"alert:{patient_id}:{decision.rule_code}"},
        )
        cutoff = evaluation_time - timedelta(minutes=decision.dedupe_window_min)
        dedupe_key = f"{patient_id}:{decision.rule_code}"
        existing = (
            session.execute(
                text("""SELECT id, severity::text FROM alerts WHERE patient_id = :patient_id
              AND rule_code = :rule_code AND status <> 'resolved' AND created_at > :cutoff
              ORDER BY created_at DESC LIMIT 1"""),
                {"patient_id": patient_id, "rule_code": decision.rule_code, "cutoff": cutoff},
            )
            .mappings()
            .one_or_none()
        )
        if existing is None:
            alert_id = uuid4()
            session.execute(
                text("""INSERT INTO alerts (id, patient_id, rule_code, rule_version, observation_id, severity, dedupe_key)
                  VALUES (:id, :patient_id, :rule_code, :rule_version, :observation_id,
                  CAST(:severity AS alert_severity), :dedupe_key)"""),
                {
                    "id": alert_id,
                    "patient_id": patient_id,
                    "rule_code": decision.rule_code,
                    "rule_version": decision.rule_version,
                    "observation_id": observation_id,
                    "severity": decision.severity,
                    "dedupe_key": dedupe_key,
                },
            )
            event_type = "triggered"
        else:
            alert_id = existing["id"]
            event_type = "deduplicated_trigger"
        session.execute(
            text("""INSERT INTO alert_events (id, alert_id, event_type, severity, details)
              VALUES (:id, :alert_id, :event_type, CAST(:severity AS alert_severity), CAST(:details AS jsonb))"""),
            {
                "id": uuid4(),
                "alert_id": alert_id,
                "event_type": event_type,
                "severity": decision.severity,
                "details": dumps({"observation_id": str(observation_id)}),
            },
        )
        if event_type == "triggered":
            session.execute(
                text("""INSERT INTO outbox_events (id, event_type, payload_ref)
                  VALUES (:id, 'AlertNotificationRequested', CAST(:payload AS jsonb))"""),
                {
                    "id": uuid4(),
                    "payload": dumps({"alert_id": str(alert_id), "patient_id": str(patient_id)}),
                },
            )
        alerts.append(
            {
                "id": str(alert_id),
                "rule_code": decision.rule_code,
                "severity": decision.severity,
                "guidance": _MESSAGES.get(
                    decision.message_key, "Synthetic-demo alert. This is not clinical guidance."
                ),
                "deduplicated": event_type != "triggered",
            }
        )
    return alerts


def transition(session: Session, *, alert_id: UUID, actor_id: UUID, action: str) -> None:
    """Enforce the documented clinician lifecycle; notifications remain delivery-state separate."""
    row = (
        session.execute(text("SELECT status::text FROM alerts WHERE id = :id"), {"id": alert_id})
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ValueError("Alert not found")
    allowed = {"acknowledge": {"open", "notified", "escalated"}, "resolve": {"acknowledged"}}
    if action not in allowed or row["status"] not in allowed[action]:
        raise ValueError("Illegal alert state transition")
    status = "acknowledged" if action == "acknowledge" else "resolved"
    field = "acknowledged_at" if action == "acknowledge" else "resolved_at"
    session.execute(
        text(
            f"UPDATE alerts SET status = CAST(:status AS alert_status), {field} = now(), acknowledged_by = :actor_id WHERE id = :id"
        ),
        {"status": status, "actor_id": actor_id, "id": alert_id},
    )
    session.execute(
        text("""INSERT INTO alert_events (id, alert_id, event_type, actor_id)
      VALUES (:id, :alert_id, :event_type, :actor_id)"""),
        {"id": uuid4(), "alert_id": alert_id, "event_type": status, "actor_id": actor_id},
    )
