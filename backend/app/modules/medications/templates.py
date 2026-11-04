"""Allowlisted non-advisory reminder templates and their technical provenance."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReminderTemplate:
    template_id: str
    version: str
    source: str
    text: str


_TEMPLATES = {
    "medication.reminder.safe_warning.v1": ReminderTemplate(
        template_id="medication.reminder.safe_warning.v1",
        version="1",
        source="system_allowlisted_safety_warning",
        text=(
            "Synthetic-demo medication reminder. Check your physician-authored schedule. "
            "Do not double your dose. Demo with synthetic data. Not for medical use."
        ),
    )
}


def get_reminder_template(template_id: str) -> ReminderTemplate:
    """Return only an allowlisted non-advisory template; no phrase matching is used."""
    try:
        return _TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError("Unapproved medication notification template") from exc
