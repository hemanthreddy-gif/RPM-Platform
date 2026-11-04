"""Idempotent delivery adapters and durable outbox delivery state."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from json import loads
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    error: str | None = None


class InAppAdapter:
    """Local synthetic-demo sink. A durable DB delivery record is the visible notification."""

    channel = "in_app"

    def deliver(self, alert_id: UUID) -> DeliveryResult:
        del alert_id
        return DeliveryResult(delivered=True)


def dispatch_pending(
    session: Session,
    *,
    adapter: InAppAdapter,
    now: datetime,
    max_attempts: int,
) -> int:
    """Claim and deliver due requests once, preserving failure and dead-letter evidence.

    A successful `(alert, channel)` delivery is unique. Failure attempts update one delivery row
    and one job-attempt row, so retries cannot create duplicate sent notifications.  A terminal
    failure marks the request published because it has been deliberately dead-lettered.
    """
    delivered = 0
    events = (
        session.execute(
            text("""SELECT e.id, e.payload_ref, COALESCE(j.attempts, 0) AS attempts
              FROM outbox_events e
              LEFT JOIN job_attempts j ON j.outbox_event_id = e.id
              WHERE e.event_type = 'AlertNotificationRequested' AND e.published_at IS NULL
                AND (j.next_retry_at IS NULL OR j.next_retry_at <= :now)
                AND j.dead_lettered_at IS NULL
              ORDER BY e.created_at FOR UPDATE OF e SKIP LOCKED LIMIT 100"""),
            {"now": now},
        )
        .mappings()
        .all()
    )
    for event in events:
        payload = event["payload_ref"]
        if isinstance(payload, str):
            payload = loads(payload)
        alert_id = UUID(str(payload["alert_id"]))
        already_sent = session.execute(
            text(
                "SELECT 1 FROM notification_deliveries WHERE alert_id = :alert_id AND channel = :channel AND status = 'sent'"
            ),
            {"alert_id": alert_id, "channel": adapter.channel},
        ).scalar()
        if already_sent:
            session.execute(
                text("UPDATE outbox_events SET published_at = :now WHERE id = :id"),
                {"now": now, "id": event["id"]},
            )
            continue
        try:
            result = adapter.deliver(alert_id)
        except Exception as exc:  # noqa: BLE001 - adapter failures become durable retry state
            result = DeliveryResult(delivered=False, error=f"{type(exc).__name__}: delivery failed")
        attempt = int(event["attempts"]) + 1
        if result.delivered:
            session.execute(
                text("""INSERT INTO notification_deliveries (id, alert_id, channel, status, attempts, sent_at, last_error)
                  VALUES (gen_random_uuid(), :alert_id, :channel, 'sent', :attempts, :now, NULL)
                  ON CONFLICT (alert_id, channel) DO UPDATE SET status = 'sent', attempts = EXCLUDED.attempts,
                    sent_at = EXCLUDED.sent_at, last_error = NULL"""),
                {"alert_id": alert_id, "channel": adapter.channel, "attempts": attempt, "now": now},
            )
            session.execute(
                text(
                    "UPDATE alerts SET status = CASE WHEN status = 'open' THEN 'notified'::alert_status ELSE status END WHERE id = :id"
                ),
                {"id": alert_id},
            )
            session.execute(
                text("UPDATE outbox_events SET published_at = :now WHERE id = :id"),
                {"now": now, "id": event["id"]},
            )
            session.execute(
                text("""INSERT INTO job_attempts
                  (id, outbox_event_id, attempts, next_retry_at, dead_lettered_at, last_error)
                  VALUES (gen_random_uuid(), :event_id, :attempts, NULL, NULL, NULL)
                  ON CONFLICT (outbox_event_id) DO UPDATE SET attempts = EXCLUDED.attempts,
                    next_retry_at = NULL, dead_lettered_at = NULL, last_error = NULL"""),
                {"event_id": event["id"], "attempts": attempt},
            )
            delivered += 1
            continue
        terminal = attempt >= max_attempts
        status = "dead_lettered" if terminal else "failed"
        session.execute(
            text("""INSERT INTO notification_deliveries (id, alert_id, channel, status, attempts, last_error)
              VALUES (gen_random_uuid(), :alert_id, :channel, :status, :attempts, :error)
              ON CONFLICT (alert_id, channel) DO UPDATE SET status = EXCLUDED.status,
                attempts = EXCLUDED.attempts, last_error = EXCLUDED.last_error"""),
            {
                "alert_id": alert_id,
                "channel": adapter.channel,
                "status": status,
                "attempts": attempt,
                "error": result.error or "delivery failed",
            },
        )
        session.execute(
            text("""INSERT INTO job_attempts (id, outbox_event_id, attempts, next_retry_at, dead_lettered_at, last_error)
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
