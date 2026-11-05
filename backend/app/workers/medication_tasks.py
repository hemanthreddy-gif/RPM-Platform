"""Timezone-aware synthetic medication scheduling and non-advisory reminders."""

from datetime import UTC, date, datetime, time, timedelta
from json import dumps, loads
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.alerts.notifications import DeliveryResult
from app.modules.medications.templates import ReminderTemplate, get_reminder_template
from app.workers.alert_tasks import _set_worker_identity
from app.workers.celery_app import celery_app


class MedicationInAppAdapter:
    """Local delivery sink; only the allowlisted warning is rendered in the synthetic demo."""

    channel = "in_app"

    def deliver(self, dose_event_id: UUID, template: ReminderTemplate) -> DeliveryResult:
        del dose_event_id, template
        return DeliveryResult(delivered=True)


def _as_object(value: object) -> dict[str, object]:
    if isinstance(value, str):
        loaded = loads(value)
        if not isinstance(loaded, dict):
            raise ValueError("Expected an object payload")
        return loaded
    if isinstance(value, dict):
        return value
    raise ValueError("Expected an object payload")


def generate_scheduled_doses(session: Session, *, now: datetime) -> int:
    """Generate the upcoming seven local calendar days, idempotently per schedule/time."""
    rows = (
        session.execute(
            text("""SELECT m.id AS medication_id, m.patient_id, m.start_date, m.end_date,
          s.id AS schedule_id, s.timezone, s.schedule
          FROM medications m JOIN medication_schedules s ON s.medication_id = m.id
          WHERE s.effective_to IS NULL AND s.effective_from <= :now"""),
            {"now": now},
        )
        .mappings()
        .all()
    )
    created = 0
    for row in rows:
        timezone = ZoneInfo(row["timezone"])
        schedule = _as_object(row["schedule"])
        values = schedule.get("times")
        template_id = schedule.get("reminder_template_id")
        if not isinstance(values, list) or not isinstance(template_id, str):
            continue
        local_today = now.astimezone(timezone).date()
        first = max(local_today, row["start_date"])
        last = min(local_today + timedelta(days=6), row["end_date"] or date.max)
        for offset in range((last - first).days + 1):
            scheduled_date = first + timedelta(days=offset)
            for value in values:
                if not isinstance(value, str):
                    continue
                scheduled_local = datetime.combine(
                    scheduled_date, time.fromisoformat(value), timezone
                )
                scheduled_for = scheduled_local.astimezone(UTC)
                if scheduled_for < now:
                    continue
                dose_event_id = uuid4()
                inserted = session.execute(
                    text("""INSERT INTO dose_events
                      (id, medication_id, schedule_id, scheduled_for) VALUES
                      (:id, :medication_id, :schedule_id, :scheduled_for)
                      ON CONFLICT (schedule_id, scheduled_for) WHERE schedule_id IS NOT NULL DO NOTHING
                      RETURNING id"""),
                    {
                        "id": dose_event_id,
                        "medication_id": row["medication_id"],
                        "schedule_id": row["schedule_id"],
                        "scheduled_for": scheduled_for,
                    },
                ).scalar_one_or_none()
                if inserted is None:
                    continue
                session.execute(
                    text("""INSERT INTO outbox_events (id, event_type, payload_ref)
                      VALUES (:id, 'MedicationReminderRequested', CAST(:payload AS jsonb))"""),
                    {
                        "id": uuid4(),
                        "payload": dumps(
                            {
                                "dose_event_id": str(dose_event_id),
                                "patient_id": str(row["patient_id"]),
                                "scheduled_for": scheduled_for.isoformat(),
                                "template_id": template_id,
                                "template_source": "system_allowlisted_safety_warning",
                            }
                        ),
                    },
                )
                created += 1
    return created


def mark_overdue_unknown(session: Session, *, now: datetime, late_window_minutes: int) -> int:
    """Label unresolved past doses unknown, never missed, after the configured late window."""
    result = session.execute(
        text("""UPDATE dose_events SET status = 'unknown'
          WHERE schedule_state = 'active' AND status = 'pending'
            AND scheduled_for + CAST(:late_window AS interval) <= :now"""),
        {"late_window": f"{late_window_minutes} minutes", "now": now},
    )
    return int(getattr(result, "rowcount", 0) or 0)


def _record_delivery(
    session: Session,
    *,
    dose_event_id: UUID,
    status: str,
    attempts: int,
    now: datetime,
    error: str | None,
) -> None:
    session.execute(
        text("""INSERT INTO medication_reminder_deliveries
          (id, dose_event_id, channel, status, attempts, sent_at, last_error)
          VALUES (gen_random_uuid(), :dose_event_id, 'in_app', :status, :attempts, :sent_at, :error)
          ON CONFLICT (dose_event_id, channel) DO UPDATE SET status = EXCLUDED.status,
          attempts = EXCLUDED.attempts, sent_at = EXCLUDED.sent_at, last_error = EXCLUDED.last_error"""),
        {
            "dose_event_id": dose_event_id,
            "status": status,
            "attempts": attempts,
            "sent_at": now if status == "sent" else None,
            "error": error,
        },
    )


def dispatch_medication_reminders(
    session: Session,
    *,
    adapter: MedicationInAppAdapter,
    now: datetime,
    late_window_minutes: int,
    max_attempts: int,
) -> int:
    """Send due reminders only in their late window and retain retry/dead-letter evidence."""
    events = (
        session.execute(
            text("""SELECT e.id, e.payload_ref, COALESCE(j.attempts, 0) AS attempts
          FROM outbox_events e LEFT JOIN job_attempts j ON j.outbox_event_id = e.id
          WHERE e.event_type = 'MedicationReminderRequested' AND e.published_at IS NULL
            AND (j.next_retry_at IS NULL OR j.next_retry_at <= :now) AND j.dead_lettered_at IS NULL
          ORDER BY e.created_at FOR UPDATE OF e SKIP LOCKED LIMIT 100"""),
            {"now": now},
        )
        .mappings()
        .all()
    )
    delivered = 0
    for event in events:
        payload = _as_object(event["payload_ref"])
        dose_event_id = UUID(str(payload["dose_event_id"]))
        scheduled_for = datetime.fromisoformat(str(payload["scheduled_for"]))
        if scheduled_for.tzinfo is None:
            raise ValueError("Reminder payload must carry an offset")
        due_until = scheduled_for + timedelta(minutes=late_window_minutes)
        dose = (
            session.execute(
                text("SELECT status::text, schedule_state FROM dose_events WHERE id = :id"),
                {"id": dose_event_id},
            )
            .mappings()
            .one_or_none()
        )
        if dose is None or dose["status"] != "pending" or dose["schedule_state"] != "active":
            session.execute(
                text("UPDATE outbox_events SET published_at = :now WHERE id = :id"),
                {"now": now, "id": event["id"]},
            )
            continue
        if now < scheduled_for:
            continue
        if now > due_until:
            _record_delivery(
                session,
                dose_event_id=dose_event_id,
                status="expired",
                attempts=int(event["attempts"]),
                now=now,
                error="configured late window elapsed",
            )
            session.execute(
                text("UPDATE outbox_events SET published_at = :now WHERE id = :id"),
                {"now": now, "id": event["id"]},
            )
            continue
        attempt = int(event["attempts"]) + 1
        try:
            template = get_reminder_template(str(payload["template_id"]))
            result = adapter.deliver(dose_event_id, template)
        except Exception as exc:  # noqa: BLE001 - adapter/template failures must remain durable
            result = DeliveryResult(delivered=False, error=f"{type(exc).__name__}: delivery failed")
        if result.delivered:
            _record_delivery(
                session,
                dose_event_id=dose_event_id,
                status="sent",
                attempts=attempt,
                now=now,
                error=None,
            )
            session.execute(
                text("UPDATE outbox_events SET published_at = :now WHERE id = :id"),
                {"now": now, "id": event["id"]},
            )
            session.execute(
                text("""INSERT INTO job_attempts (id, outbox_event_id, attempts)
                  VALUES (gen_random_uuid(), :event_id, :attempts)
                  ON CONFLICT (outbox_event_id) DO UPDATE SET attempts = EXCLUDED.attempts,
                  next_retry_at = NULL, dead_lettered_at = NULL, last_error = NULL"""),
                {"event_id": event["id"], "attempts": attempt},
            )
            delivered += 1
            continue
        terminal = attempt >= max_attempts
        _record_delivery(
            session,
            dose_event_id=dose_event_id,
            status="dead_lettered" if terminal else "failed",
            attempts=attempt,
            now=now,
            error=result.error or "delivery failed",
        )
        session.execute(
            text("""INSERT INTO job_attempts
              (id, outbox_event_id, attempts, next_retry_at, dead_lettered_at, last_error)
              VALUES (gen_random_uuid(), :event_id, :attempts, :next_retry_at, :dead_lettered_at, :error)
              ON CONFLICT (outbox_event_id) DO UPDATE SET attempts = EXCLUDED.attempts,
              next_retry_at = EXCLUDED.next_retry_at, dead_lettered_at = EXCLUDED.dead_lettered_at,
              last_error = EXCLUDED.last_error"""),
            {
                "event_id": event["id"],
                "attempts": attempt,
                "next_retry_at": None if terminal else now + timedelta(minutes=2 ** (attempt - 1)),
                "dead_lettered_at": now if terminal else None,
                "error": result.error or "delivery failed",
            },
        )
        if terminal:
            session.execute(
                text("UPDATE outbox_events SET published_at = :now WHERE id = :id"),
                {"now": now, "id": event["id"]},
            )
    return delivered


@celery_app.task(
    name="medications.generate_scheduled_doses",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def generate_scheduled_doses_task() -> int:
    with SessionLocal() as session:
        _set_worker_identity(session)
        generated = generate_scheduled_doses(session, now=datetime.now(UTC))
        session.commit()
        return generated


@celery_app.task(
    name="medications.dispatch_reminders",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def dispatch_medication_reminders_task() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        _set_worker_identity(session)
        delivered = dispatch_medication_reminders(
            session,
            adapter=MedicationInAppAdapter(),
            now=datetime.now(UTC),
            late_window_minutes=settings.medication_reminder_late_window_minutes,
            max_attempts=settings.notification_max_attempts,
        )
        session.commit()
        return delivered


@celery_app.task(
    name="medications.mark_overdue_unknown",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def mark_overdue_unknown_task() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        _set_worker_identity(session)
        changed = mark_overdue_unknown(
            session,
            now=datetime.now(UTC),
            late_window_minutes=settings.medication_reminder_late_window_minutes,
        )
        session.commit()
        return changed
