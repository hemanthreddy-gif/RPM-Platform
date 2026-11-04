"""Unit evidence for the isolated missed-report path and reminder provenance."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.clinical_rules.evaluator import evaluate_patterns
from app.clinical_rules.loader import load_rules
from app.clinical_rules.models import MedicationDoseReport, PatientContext
from app.modules.medications.schemas import DoseReportRequest, MedicationRequest
from app.modules.medications.templates import get_reminder_template


def test_missed_dose_pattern_requires_an_actual_self_report() -> None:
    rules = load_rules(Path(__file__).parents[1] / "rules")
    now = datetime(2026, 11, 4, tzinfo=UTC)
    assert evaluate_patterns(PatientContext(), rules, now) == []
    decisions = evaluate_patterns(
        PatientContext(
            medication_reports=[
                MedicationDoseReport(
                    medication_id="synthetic-medication",
                    status="missed",
                    reported_at=now,
                )
            ]
        ),
        rules,
        now,
    )
    assert [decision.rule_code for decision in decisions] == ["MED_MISSED_PATTERN"]
    assert decisions[0].message_key == "medication.missed.self_reported"


def test_reminder_uses_allowlisted_provenance_not_phrase_matching() -> None:
    template = get_reminder_template("medication.reminder.safe_warning.v1")
    assert template.source == "system_allowlisted_safety_warning"
    assert "Do not double your dose" in template.text
    with pytest.raises(ValueError, match="Unapproved"):
        get_reminder_template("medication.change-dose.advice.v1")


def test_medication_request_and_dose_report_keep_schedule_and_timestamp_typed() -> None:
    request = MedicationRequest.model_validate(
        {
            "name": "Synthetic medicine",
            "frequency": "twice daily",
            "schedule_times": ["20:00", "08:00"],
            "start_date": "2026-11-04",
        }
    )
    assert [value.isoformat(timespec="minutes") for value in request.schedule_times] == [
        "08:00",
        "20:00",
    ]
    with pytest.raises(ValueError, match="UTC offset"):
        DoseReportRequest(status="taken", reported_at=datetime(2026, 11, 4, 8, 0))
