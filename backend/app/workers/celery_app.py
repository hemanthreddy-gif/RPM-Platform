"""Celery application shell. No task is allowed to make a clinical decision."""

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "rpm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.alert_tasks", "app.workers.medication_tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_publish_retry=True,
    broker_connection_retry_on_startup=True,
    task_default_retry_delay=30,
)
celery_app.conf.beat_schedule = {
    "dispatch-alert-outbox": {"task": "alerts.dispatch_outbox", "schedule": 30.0},
    "escalate-unacknowledged-alerts": {"task": "alerts.escalate_unacknowledged", "schedule": 60.0},
    "check-no-data": {"task": "alerts.check_no_data", "schedule": 3600.0},
    "check-target-patterns": {"task": "alerts.check_target_patterns", "schedule": 3600.0},
    "generate-scheduled-doses": {
        "task": "medications.generate_scheduled_doses",
        "schedule": 3600.0,
    },
    "dispatch-medication-reminders": {"task": "medications.dispatch_reminders", "schedule": 30.0},
    "mark-overdue-dose-events-unknown": {
        "task": "medications.mark_overdue_unknown",
        "schedule": 300.0,
    },
}
