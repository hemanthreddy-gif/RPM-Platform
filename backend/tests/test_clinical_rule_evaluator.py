from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.clinical_rules.evaluator import evaluate, evaluate_no_data, evaluate_patterns
from app.clinical_rules.loader import load_rules
from app.clinical_rules.models import Observation, PatientContext, RuleDefinition

RULES = load_rules(Path(__file__).parents[1] / "rules")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("53"), "GLU_LOW_L2"),
        (Decimal("54"), "GLU_LOW_L1"),
        (Decimal("55"), "GLU_LOW_L1"),
        (Decimal("70"), None),
        (Decimal("300"), "GLU_HIGH_URGENT"),
    ],
)
def test_glucose_boundaries(value: Decimal, expected: str | None) -> None:
    decisions = evaluate(
        Observation(type="glucose", value=value, measured_at=datetime.now(UTC)),
        PatientContext(),
        RULES,
        datetime.now(UTC),
    )
    assert (decisions[0].rule_code if decisions else None) == expected


def test_l2_suppresses_l1() -> None:
    decisions = evaluate(
        Observation(type="glucose", value=Decimal("53"), measured_at=datetime.now(UTC)),
        PatientContext(),
        RULES,
        datetime.now(UTC),
    )
    assert [decision.rule_code for decision in decisions] == ["GLU_LOW_L2"]


@pytest.mark.parametrize(
    ("components", "expected"),
    [
        ({"systolic": Decimal("179"), "diastolic": Decimal("119")}, None),
        ({"systolic": Decimal("180"), "diastolic": Decimal("80")}, "BP_CRISIS"),
        ({"systolic": Decimal("120"), "diastolic": Decimal("120")}, "BP_CRISIS"),
        ({"systolic": Decimal("89"), "diastolic": Decimal("60")}, "BP_LOW"),
    ],
)
def test_blood_pressure_boundaries(components: dict[str, Decimal], expected: str | None) -> None:
    decisions = evaluate(
        Observation(type="blood_pressure", components=components, measured_at=datetime.now(UTC)),
        PatientContext(),
        RULES,
        datetime.now(UTC),
    )
    assert (decisions[0].rule_code if decisions else None) == expected


def test_no_data_is_deterministic_at_the_configured_boundary() -> None:
    now = datetime.now(UTC)
    assert (
        evaluate_no_data(
            observation_type="glucose", last_measured_at=now, evaluation_time=now, days=3
        )
        is None
    )
    assert (
        evaluate_no_data(
            observation_type="glucose", last_measured_at=None, evaluation_time=now, days=3
        ).rule_code
        == "NO_DATA_GLUCOSE"
    )


@pytest.mark.parametrize(
    ("last_age_days", "days", "expected"),
    [(2, 3, False), (3, 3, True), (4, 3, True), (0, 0, False)],
)
def test_no_data_boundaries(last_age_days: int, days: int, expected: bool) -> None:
    now = datetime.now(UTC)
    decision = evaluate_no_data(
        observation_type="blood_pressure",
        last_measured_at=now - timedelta(days=last_age_days),
        evaluation_time=now,
        days=days,
    )
    assert (decision is not None) is expected


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ({"all": [{"field": "value", "op": "<=", "value": 10}]}, True),
        ({"all": [{"field": "value", "op": ">", "value": 10}]}, False),
        (
            {
                "any": [
                    {"field": "value", "op": ">", "value": 10},
                    {"field": "value", "op": "<=", "value": 10},
                ]
            },
            True,
        ),
        ({"all": [{"field": "missing", "op": "<", "value": 10}]}, False),
        ({"all": [{"field": "value", "op": "bad", "value": 10}]}, False),
    ],
)
def test_rule_condition_operators(condition: dict[str, object], expected: bool) -> None:
    rule = RuleDefinition(
        code="TEST",
        version=1,
        applies_to="glucose",
        severity="informational",
        condition=condition,
        message_key="test",
        dedupe_window_min=1,
        requires_clinician_approval=True,
        synthetic_demo_only=True,
    )
    decisions = evaluate(
        Observation(type="glucose", value=Decimal("10"), measured_at=datetime.now(UTC)),
        PatientContext(),
        [rule],
        datetime.now(UTC),
    )
    assert bool(decisions) is expected


def test_fasting_pattern_requires_three_of_latest_five_and_an_explicit_target() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    history = [
        Observation(
            type="glucose",
            value=Decimal(value),
            context={"fasting": True},
            measured_at=now - timedelta(days=index),
        )
        for index, value in enumerate(("101", "99", "102", "98", "103"))
    ]
    context = PatientContext(targets={"glucose.fasting": (None, Decimal("100"))}, history=history)
    decisions = evaluate_patterns(context, RULES, now)
    assert [decision.rule_code for decision in decisions] == ["GLU_FASTING_PATTERN"]
    assert evaluate_patterns(PatientContext(history=history), RULES, now) == []


def test_fasting_pattern_excludes_future_readings_and_counts_latest_window() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    history = [
        Observation(
            type="glucose",
            value=Decimal(value),
            context={"fasting": True},
            measured_at=now + timedelta(minutes=1) if index == 0 else now - timedelta(days=index),
        )
        for index, value in enumerate(("110", "101", "102", "99", "98", "97"))
    ]
    context = PatientContext(targets={"glucose.fasting": (None, Decimal("100"))}, history=history)
    assert evaluate_patterns(context, RULES, now) == []


def test_bp_average_pattern_needs_four_recent_readings_and_component_target() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    history = [
        Observation(
            type="blood_pressure",
            components={"systolic": Decimal(value), "diastolic": Decimal("70")},
            measured_at=now - timedelta(days=index),
        )
        for index, value in enumerate(("131", "129", "132", "130"))
    ]
    context = PatientContext(
        targets={"blood_pressure.systolic": (None, Decimal("125"))}, history=history
    )
    decisions = evaluate_patterns(context, RULES, now)
    assert [decision.rule_code for decision in decisions] == ["BP_ABOVE_TARGET_PATTERN"]
    assert (
        evaluate_patterns(PatientContext(targets=context.targets, history=history[:3]), RULES, now)
        == []
    )


def test_bp_average_pattern_is_strictly_above_target_and_uses_explicit_window() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    history = [
        Observation(
            type="blood_pressure",
            components={"systolic": Decimal("130"), "diastolic": Decimal("70")},
            measured_at=now - timedelta(days=1),
        ),
        Observation(
            type="blood_pressure",
            components={"systolic": Decimal("120"), "diastolic": Decimal("70")},
            measured_at=now - timedelta(days=8),
        ),
    ]
    context = PatientContext(
        targets={"blood_pressure.systolic": (None, Decimal("130"))}, history=history
    )
    assert evaluate_patterns(context, RULES, now) == []


def test_malformed_conditions_and_pattern_configuration_are_safe_no_matches() -> None:
    now = datetime.now(UTC)
    observation = Observation(type="glucose", value=Decimal("10"), measured_at=now)
    base: dict[str, object] = {
        "version": 1,
        "applies_to": "glucose",
        "severity": "attention",
        "condition": {"all": "not-a-list"},
        "message_key": "test",
        "dedupe_window_min": 1,
        "requires_clinician_approval": True,
        "synthetic_demo_only": True,
    }
    malformed_clause = RuleDefinition(code="BAD_CLAUSE", **(base | {"condition": {"all": ["x"]}}))
    malformed_list = RuleDefinition(code="BAD_LIST", **base)
    assert evaluate(observation, PatientContext(), [malformed_clause, malformed_list], now) == []
    invalid_count = RuleDefinition(
        code="BAD_PATTERN",
        **(
            base
            | {
                "pattern": {
                    "kind": "fasting_above_target_count",
                    "count": "3",
                    "sample_size": 5,
                }
            }
        ),
    )
    invalid_zero = RuleDefinition(
        code="ZERO_PATTERN",
        **(
            base
            | {
                "pattern": {
                    "kind": "fasting_above_target_count",
                    "count": 0,
                    "sample_size": 5,
                }
            }
        ),
    )
    invalid_bp = RuleDefinition(
        code="BAD_BP",
        **(
            base
            | {
                "applies_to": "blood_pressure",
                "pattern": {
                    "kind": "bp_target_average",
                    "days": 7,
                    "minimum_readings": 4,
                    "components": [9],
                },
            }
        ),
    )
    assert (
        evaluate_patterns(
            PatientContext(targets={"glucose.fasting": (None, Decimal("100"))}),
            [invalid_count, invalid_zero, invalid_bp],
            now,
        )
        == []
    )
