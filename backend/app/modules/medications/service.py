"""Medication versioning and self-reported adherence services."""

from datetime import UTC, datetime, timedelta
from json import dumps, loads
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clinical_rules.evaluator import evaluate_patterns
from app.clinical_rules.loader import load_rules
from app.clinical_rules.models import MedicationDoseReport, PatientContext
from app.core.config import get_settings
from app.modules.alerts.service import persist_decisions
from app.modules.medications.schemas import MedicationRequest

_RULES = load_rules(Path(__file__).parents[3] / "rules")
_REMINDER_TEMPLATE_ID = "medication.reminder.safe_warning.v1"


def _patient_timezone(session: Session, patient_id: UUID) -> str:
    timezone = session.execute(
        text("SELECT timezone FROM patients WHERE id = :patient_id"), {"patient_id": patient_id}
    ).scalar_one()
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Patient timezone is not supported") from exc
    return str(timezone)


def _payload(payload: MedicationRequest, actor_id: UUID) -> str:
    return dumps(
        {
            **payload.model_dump(mode="json"),
            "provenance": "physician_authored_synthetic_record",
            "authored_by": str(actor_id),
        }
    )


def _schedule(payload: MedicationRequest) -> str:
    return dumps(
        {
            "times": [value.isoformat(timespec="minutes") for value in payload.schedule_times],
            "reminder_template_id": _REMINDER_TEMPLATE_ID,
        }
    )


def create_version(
    session: Session,
    *,
    patient_id: UUID,
    actor_id: UUID,
    payload: MedicationRequest,
    medication_id: UUID | None = None,
) -> dict[str, object]:
    """Append a physician-authored medication version and one effective schedule version."""
    timezone = _patient_timezone(session, patient_id)
    prescriber_id = session.execute(
        text("SELECT id FROM physicians WHERE user_id = :user_id"), {"user_id": actor_id}
    ).scalar_one_or_none()
    if prescriber_id is None:
        raise ValueError("Physician profile is required")
    now = datetime.now(UTC)
    if medication_id is None:
        medication_id = uuid4()
        version = 1
        session.execute(
            text("""INSERT INTO medications
              (id, patient_id, name, strength, dose, route, frequency, start_date, end_date, prescriber_id, instructions, version)
              VALUES (:id, :patient_id, :name, :strength, :dose, :route, :frequency, :start_date, :end_date, :prescriber_id, :instructions, :version)"""),
            {
                "id": medication_id,
                "patient_id": patient_id,
                "name": payload.name,
                "strength": payload.strength,
                "dose": payload.dose,
                "route": payload.route,
                "frequency": payload.frequency,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "prescriber_id": prescriber_id,
                "instructions": payload.instructions,
                "version": version,
            },
        )
    else:
        current = (
            session.execute(
                text("SELECT patient_id, version FROM medications WHERE id = :id FOR UPDATE"),
                {"id": medication_id},
            )
            .mappings()
            .one_or_none()
        )
        if current is None:
            raise ValueError("Medication not found")
        if current["patient_id"] != patient_id:
            raise ValueError("Medication patient does not match")
        version = int(current["version"]) + 1
        session.execute(
            text("""UPDATE medications SET name = :name, strength = :strength, dose = :dose,
              route = :route, frequency = :frequency, start_date = :start_date, end_date = :end_date,
              prescriber_id = :prescriber_id, instructions = :instructions, version = :version WHERE id = :id"""),
            {
                "id": medication_id,
                "name": payload.name,
                "strength": payload.strength,
                "dose": payload.dose,
                "route": payload.route,
                "frequency": payload.frequency,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "prescriber_id": prescriber_id,
                "instructions": payload.instructions,
                "version": version,
            },
        )
        session.execute(
            text("""UPDATE medication_schedules SET effective_to = :now
              WHERE medication_id = :medication_id AND effective_to IS NULL"""),
            {"now": now, "medication_id": medication_id},
        )
        # Previously generated future events remain as provenance but are not reminders or doses
        # on the revised schedule. A self-report is never overwritten.
        session.execute(
            text("""UPDATE dose_events SET schedule_state = 'superseded'
              WHERE medication_id = :medication_id AND schedule_state = 'active'
                AND status IN ('pending', 'unknown') AND scheduled_for > :now"""),
            {"medication_id": medication_id, "now": now},
        )
    session.execute(
        text("""INSERT INTO medication_versions (id, medication_id, version, effective_from, payload)
          VALUES (:id, :medication_id, :version, :effective_from, CAST(:payload AS jsonb))"""),
        {
            "id": uuid4(),
            "medication_id": medication_id,
            "version": version,
            "effective_from": now,
            "payload": _payload(payload, actor_id),
        },
    )
    schedule_id = uuid4()
    session.execute(
        text("""INSERT INTO medication_schedules
          (id, medication_id, timezone, schedule, effective_from, created_by)
          VALUES (:id, :medication_id, :timezone, CAST(:schedule AS jsonb), :effective_from, :created_by)"""),
        {
            "id": schedule_id,
            "medication_id": medication_id,
            "timezone": timezone,
            "schedule": _schedule(payload),
            "effective_from": now,
            "created_by": actor_id,
        },
    )
    return {
        "id": str(medication_id),
        "patient_id": str(patient_id),
        "name": payload.name,
        "strength": payload.strength,
        "dose": payload.dose,
        "route": payload.route,
        "frequency": payload.frequency,
        "schedule_times": [value.isoformat(timespec="minutes") for value in payload.schedule_times],
        "timezone": timezone,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "instructions": payload.instructions,
        "version": version,
        "authored_by": str(actor_id),
        "provenance": "physician_authored_synthetic_record",
    }


def list_current(session: Session, *, patient_id: UUID) -> list[dict[str, object]]:
    """Read the current physician-authored version for each medication."""
    rows = (
        session.execute(
            text("""SELECT m.id, m.patient_id, m.name, m.strength, m.dose, m.route, m.frequency,
          m.start_date, m.end_date, m.instructions, m.version, s.timezone, s.schedule, s.created_by
          FROM medications m JOIN medication_schedules s ON s.medication_id = m.id
          AND s.effective_to IS NULL WHERE m.patient_id = :patient_id ORDER BY m.name"""),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )
    result: list[dict[str, object]] = []
    for row in rows:
        schedule = row["schedule"]
        if isinstance(schedule, str):
            schedule = loads(schedule)
        result.append(
            {
                "id": str(row["id"]),
                "patient_id": str(row["patient_id"]),
                "name": row["name"],
                "strength": row["strength"],
                "dose": row["dose"],
                "route": row["route"],
                "frequency": row["frequency"],
                "schedule_times": list(schedule["times"]),
                "timezone": row["timezone"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "instructions": row["instructions"],
                "version": row["version"],
                "authored_by": str(row["created_by"]),
                "provenance": "physician_authored_synthetic_record",
            }
        )
    return result


def report_dose(
    session: Session,
    *,
    dose_event_id: UUID,
    patient_user_id: UUID,
    status: str,
    reported_at: datetime,
    concern_note: str | None,
) -> tuple[dict[str, object], UUID]:
    """Persist one patient self-report, and route an actual missed report to the pure rule path."""
    row = (
        session.execute(
            text("""SELECT d.id, d.medication_id, d.scheduled_for, d.status::text, m.patient_id FROM dose_events d
          JOIN medications m ON m.id = d.medication_id WHERE d.id = :id AND d.schedule_state = 'active'
          FOR UPDATE"""),
            {"id": dose_event_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ValueError("Active dose event not found")
    if row["status"] not in {"pending", "unknown"}:
        raise ValueError("Dose event already has a self-report")
    updated = (
        session.execute(
            text("""UPDATE dose_events SET status = CAST(:status AS dose_status), recorded_at = :reported_at,
          reported_by = :reported_by, reported_note = :reported_note WHERE id = :id
          RETURNING id, status::text, scheduled_for, recorded_at"""),
            {
                "id": dose_event_id,
                "status": status,
                "reported_at": reported_at,
                "reported_by": patient_user_id,
                "reported_note": concern_note,
            },
        )
        .mappings()
        .one()
    )
    patient_id = row["patient_id"]
    if concern_note is not None:
        session.execute(
            text("""INSERT INTO medication_concern_flags
              (id, dose_event_id, patient_id, reported_by, note)
              VALUES (:id, :dose_event_id, :patient_id, :reported_by, :note)"""),
            {
                "id": uuid4(),
                "dose_event_id": dose_event_id,
                "patient_id": patient_id,
                "reported_by": patient_user_id,
                "note": concern_note,
            },
        )
    if status == "missed" and get_settings().synthetic_demo_rules_enabled:
        decisions = evaluate_patterns(
            PatientContext(
                medication_reports=[
                    MedicationDoseReport(
                        medication_id=str(row["medication_id"]),
                        status="missed",
                        reported_at=reported_at,
                    )
                ]
            ),
            _RULES,
            reported_at,
        )
        persist_decisions(
            session,
            patient_id=patient_id,
            observation_id=None,
            decisions=decisions,
            evaluation_time=reported_at,
        )
    return (
        {
            "id": str(updated["id"]),
            "status": updated["status"],
            "scheduled_for": updated["scheduled_for"],
            "reported_at": updated["recorded_at"],
            "self_reported": True,
            "concern_flagged_for_physician": concern_note is not None,
        },
        patient_id,
    )


def adherence_summary(
    session: Session, *, patient_id: UUID, days: int, now: datetime
) -> dict[str, object]:
    """Calculate reporting statistics without equating absent reports with missed doses."""
    cutoff = now - timedelta(days=days)
    rows = (
        session.execute(
            text("""SELECT d.medication_id, d.status::text, d.scheduled_for, d.recorded_at
          FROM dose_events d JOIN medications m ON m.id = d.medication_id
          WHERE m.patient_id = :patient_id AND d.schedule_state = 'active'
            AND d.scheduled_for >= :cutoff AND d.scheduled_for < :now"""),
            {"patient_id": patient_id, "cutoff": cutoff, "now": now},
        )
        .mappings()
        .all()
    )
    reported = [row for row in rows if row["status"] in {"taken", "missed", "skipped"}]
    taken = sum(row["status"] == "taken" for row in reported)
    missed = [row for row in reported if row["status"] == "missed"]
    denominator = len(reported)
    patterns: dict[str, int] = {}
    for row in missed:
        medication_id = str(row["medication_id"])
        patterns[medication_id] = patterns.get(medication_id, 0) + 1
    return {
        "days": days,
        "self_reported": True,
        "percentage": (100 * taken / denominator) if denominator else None,
        "reported_dose_count": denominator,
        "scheduled_dose_count": len(rows),
        "pending_or_unknown_count": len(rows) - denominator,
        "missed_dose_pattern": [
            {"medication_id": medication_id, "self_reported_missed_count": count}
            for medication_id, count in sorted(patterns.items())
        ],
    }
