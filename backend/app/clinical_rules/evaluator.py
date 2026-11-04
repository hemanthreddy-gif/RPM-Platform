"""Pure deterministic evaluator: no I/O, database, clock, or AI dependencies."""

from datetime import datetime, timedelta
from decimal import Decimal

from .models import AlertDecision, Observation, PatientContext, RuleDefinition


def _field_value(observation: Observation, field: str) -> Decimal | None:
    if field == "value_mg_dl" or field == "value":
        return observation.value
    return observation.components.get(field)


def _matches(condition: dict[str, object], observation: Observation) -> bool:
    clauses = condition.get("all") or condition.get("any", [])
    if not isinstance(clauses, list):
        return False
    match_any = "any" in condition
    matched: list[bool] = []
    for clause in clauses:
        if not isinstance(clause, dict):
            return False
        value = _field_value(observation, str(clause.get("field")))
        threshold = Decimal(str(clause.get("value")))
        operator = clause.get("op")
        if value is None:
            matched.append(False)
        elif operator == "<":
            matched.append(value < threshold)
        elif operator == "<=":
            matched.append(value <= threshold)
        elif operator == ">":
            matched.append(value > threshold)
        elif operator == ">=":
            matched.append(value >= threshold)
        else:
            return False
    return any(matched) if match_any else all(matched)


def _pattern_int(pattern: dict[str, object], key: str) -> int | None:
    value = pattern.get(key)
    if isinstance(value, int):
        return value
    return None


def evaluate(
    observation: Observation,
    patient_context: PatientContext,
    rule_set: list[RuleDefinition],
    evaluation_time: datetime,
) -> list[AlertDecision]:
    """Evaluate supplied input only; ``evaluation_time`` is explicit for caller auditability."""
    del evaluation_time
    decisions = [
        AlertDecision(
            rule_code=rule.code,
            rule_version=rule.version,
            severity=rule.severity,
            message_key=rule.message_key,
            dedupe_window_min=rule.dedupe_window_min,
            urgent_guidance=rule.severity == "urgent",
        )
        for rule in rule_set
        if rule.pattern is None
        and rule.applies_to == observation.type
        and _matches(rule.condition, observation)
    ]
    # L2 must suppress L1 for the same glucose event.
    if any(decision.rule_code == "GLU_LOW_L2" for decision in decisions):
        decisions = [decision for decision in decisions if decision.rule_code != "GLU_LOW_L1"]
    return decisions


def evaluate_patterns(
    patient_context: PatientContext,
    rule_set: list[RuleDefinition],
    evaluation_time: datetime,
) -> list[AlertDecision]:
    """Evaluate configured target patterns from supplied history and targets only.

    A target is an input fact set by a physician.  Missing target facts deliberately produce no
    decision: this package never manufactures target values or reads a clock/database.
    """
    decisions: list[AlertDecision] = []
    for rule in rule_set:
        pattern = rule.pattern
        if pattern is None:
            continue
        kind = pattern.get("kind")
        if kind == "fasting_above_target_count":
            if rule.applies_to != "glucose":
                continue
            target = patient_context.targets.get("glucose.fasting")
            count = _pattern_int(pattern, "count")
            sample_size = _pattern_int(pattern, "sample_size")
            if target is None or target[1] is None or count is None or sample_size is None:
                continue
            target_high = target[1]
            if count <= 0 or sample_size <= 0:
                continue
            fasting = [
                item
                for item in sorted(
                    patient_context.history, key=lambda item: item.measured_at, reverse=True
                )
                if item.type == "glucose"
                and item.context.get("fasting") is True
                and item.value is not None
                and item.measured_at <= evaluation_time
            ][:sample_size]
            if (
                len(fasting) == sample_size
                and sum(item.value is not None and item.value > target_high for item in fasting)
                >= count
            ):
                decisions.append(_pattern_decision(rule))
        elif kind == "bp_target_average":
            if rule.applies_to != "blood_pressure":
                continue
            days = _pattern_int(pattern, "days")
            minimum = _pattern_int(pattern, "minimum_readings")
            components = pattern.get("components")
            if (
                days is None
                or minimum is None
                or days <= 0
                or minimum <= 0
                or not isinstance(components, list)
            ):
                continue
            cutoff = evaluation_time - timedelta(days=days)
            readings = [
                item
                for item in patient_context.history
                if item.type == "blood_pressure" and cutoff <= item.measured_at <= evaluation_time
            ]
            if len(readings) < minimum:
                continue
            for component in components:
                if not isinstance(component, str):
                    continue
                target = patient_context.targets.get(f"blood_pressure.{component}")
                values = [item.components.get(component) for item in readings]
                numeric_values = [value for value in values if value is not None]
                if target is not None and target[1] is not None and len(numeric_values) >= minimum:
                    target_high = target[1]
                    if sum(numeric_values) / len(numeric_values) > target_high:
                        decisions.append(_pattern_decision(rule))
                        break
        elif kind == "self_reported_missed_dose":
            # This is a provenance signal, not a threshold: an alert can only follow an actual
            # patient-reported missed dose supplied by the caller.
            if any(
                report.status == "missed" and report.reported_at <= evaluation_time
                for report in patient_context.medication_reports
            ):
                decisions.append(_pattern_decision(rule))
    return decisions


def _pattern_decision(rule: RuleDefinition) -> AlertDecision:
    return AlertDecision(
        rule_code=rule.code,
        rule_version=rule.version,
        severity=rule.severity,
        message_key=rule.message_key,
        dedupe_window_min=rule.dedupe_window_min,
        urgent_guidance=rule.severity == "urgent",
    )


def evaluate_no_data(
    *,
    observation_type: str,
    last_measured_at: datetime | None,
    evaluation_time: datetime,
    days: int,
) -> AlertDecision | None:
    """Pure scheduled decision using explicit facts and time supplied by its caller."""
    if days <= 0:
        return None
    if last_measured_at is not None and evaluation_time - last_measured_at < timedelta(days=days):
        return None
    return AlertDecision(
        rule_code=f"NO_DATA_{observation_type.upper()}",
        rule_version=1,
        severity="informational",
        message_key="no_data.informational",
        dedupe_window_min=24 * 60,
    )
