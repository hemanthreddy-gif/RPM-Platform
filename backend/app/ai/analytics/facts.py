"""Pure, non-clinical descriptive analytics with source-level traceability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import sqrt
from typing import Literal
from uuid import UUID

MINIMUM_SAMPLE_SIZE = 3


@dataclass(frozen=True)
class AnalyticObservation:
    """A normalized immutable observation supplied by a caller, not loaded here."""

    id: UUID
    measured_at: datetime
    kind: Literal["glucose", "blood_pressure"]
    value: Decimal | None = None
    systolic: Decimal | None = None
    diastolic: Decimal | None = None
    fasting: bool = False


@dataclass(frozen=True)
class DoseReport:
    """An explicitly self-reported adherence event; absence is never a missed dose."""

    id: UUID
    scheduled_for: datetime
    status: Literal["taken", "missed", "skipped"]


@dataclass(frozen=True)
class AnalyticFact:
    id: str
    label: str
    value: Decimal | None
    unit: str | None
    sample_size: int
    observation_ids: tuple[UUID, ...]
    dose_event_ids: tuple[UUID, ...] = ()
    window_start: datetime | None = None
    window_end: datetime | None = None
    insufficient_data: bool = False
    note: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "value": str(self.value) if self.value is not None else None,
            "unit": self.unit,
            "sample_size": self.sample_size,
            "observation_ids": [str(value) for value in self.observation_ids],
            "dose_event_ids": [str(value) for value in self.dose_event_ids],
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "insufficient_data": self.insufficient_data,
            "note": self.note,
        }


def _window(items: list[AnalyticObservation]) -> tuple[datetime | None, datetime | None]:
    if not items:
        return None, None
    values = [item.measured_at for item in items]
    return min(values), max(values)


def _insufficient(
    identifier: str, label: str, items: list[AnalyticObservation], note: str
) -> AnalyticFact:
    start, end = _window(items)
    return AnalyticFact(
        id=identifier,
        label=label,
        value=None,
        unit=None,
        sample_size=len(items),
        observation_ids=tuple(item.id for item in items),
        window_start=start,
        window_end=end,
        insufficient_data=True,
        note=note,
    )


def glucose_facts(
    observations: list[AnalyticObservation],
    *,
    target_low: Decimal | None,
    target_high: Decimal | None,
    minimum_sample_size: int = MINIMUM_SAMPLE_SIZE,
) -> list[AnalyticFact]:
    """Return descriptive glucose facts, never a time-weighted CGM interpretation."""
    items = sorted(
        [item for item in observations if item.kind == "glucose" and item.value is not None],
        key=lambda item: item.measured_at,
    )
    if len(items) < minimum_sample_size:
        return [
            _insufficient("glucose.mean", "Glucose mean", items, "Minimum sample size not met"),
            _insufficient(
                "glucose.sd", "Glucose standard deviation", items, "Minimum sample size not met"
            ),
            _insufficient(
                "glucose.sampled_in_target_percentage",
                "Sampled readings in physician-defined range",
                items,
                "Minimum sample size not met",
            ),
        ]
    values = [item.value for item in items if item.value is not None]
    assert len(values) == len(items)
    mean = sum(values) / Decimal(len(values))
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values))
    start, end = _window(items)
    refs = tuple(item.id for item in items)
    facts = [
        AnalyticFact(
            "glucose.mean",
            "Glucose mean",
            mean,
            "mg/dL",
            len(items),
            refs,
            window_start=start,
            window_end=end,
        ),
        AnalyticFact(
            "glucose.sd",
            "Glucose standard deviation",
            Decimal(str(sqrt(float(variance)))),
            "mg/dL",
            len(items),
            refs,
            window_start=start,
            window_end=end,
        ),
    ]
    if target_low is None or target_high is None:
        facts.append(
            AnalyticFact(
                "glucose.sampled_in_target_percentage",
                "Sampled readings in physician-defined range",
                None,
                None,
                len(items),
                refs,
                window_start=start,
                window_end=end,
                insufficient_data=True,
                note="No physician-defined range is available",
            )
        )
    else:
        in_range = sum(target_low <= value <= target_high for value in values)
        facts.append(
            AnalyticFact(
                "glucose.sampled_in_target_percentage",
                "Sampled readings in physician-defined range",
                Decimal(100 * in_range) / Decimal(len(items)),
                "percent of sampled readings",
                len(items),
                refs,
                window_start=start,
                window_end=end,
                note="This is not CGM time in range",
            )
        )
    return facts


def fasting_glucose_change(
    observations: list[AnalyticObservation], *, minimum_sample_size: int = MINIMUM_SAMPLE_SIZE
) -> AnalyticFact:
    """Describe first-to-last fasting sampled value without predicting a trend."""
    items = sorted(
        [
            item
            for item in observations
            if item.kind == "glucose" and item.fasting and item.value is not None
        ],
        key=lambda item: item.measured_at,
    )
    if len(items) < minimum_sample_size:
        return _insufficient(
            "glucose.fasting_change",
            "Fasting glucose first-to-last change",
            items,
            "Minimum fasting sample size not met",
        )
    start, end = _window(items)
    assert items[0].value is not None and items[-1].value is not None
    return AnalyticFact(
        "glucose.fasting_change",
        "Fasting glucose first-to-last change",
        items[-1].value - items[0].value,
        "mg/dL",
        len(items),
        tuple(item.id for item in items),
        window_start=start,
        window_end=end,
        note="Observed sampled change, not a prediction",
    )


def blood_pressure_facts(
    observations: list[AnalyticObservation], *, minimum_sample_size: int = MINIMUM_SAMPLE_SIZE
) -> list[AnalyticFact]:
    """Return BP component descriptives only when all required components are present."""
    items = sorted(
        [
            item
            for item in observations
            if item.kind == "blood_pressure"
            and item.systolic is not None
            and item.diastolic is not None
        ],
        key=lambda item: item.measured_at,
    )
    labels = (
        ("bp.systolic_mean", "Systolic BP mean", "systolic"),
        ("bp.diastolic_mean", "Diastolic BP mean", "diastolic"),
    )
    if len(items) < minimum_sample_size:
        return [
            _insufficient(identifier, label, items, "Minimum sample size not met")
            for identifier, label, _ in labels
        ]
    start, end = _window(items)
    refs = tuple(item.id for item in items)
    result: list[AnalyticFact] = []
    for identifier, label, component in labels:
        values = [getattr(item, component) for item in items]
        assert all(value is not None for value in values)
        result.append(
            AnalyticFact(
                identifier,
                label,
                sum(values) / Decimal(len(values)),
                "mmHg",
                len(items),
                refs,
                window_start=start,
                window_end=end,
            )
        )  # type: ignore[arg-type]
    return result


def bp_missed_dose_comparison(
    observations: list[AnalyticObservation],
    reports: list[DoseReport],
    *,
    minimum_sample_size: int = MINIMUM_SAMPLE_SIZE,
) -> AnalyticFact:
    """Compare daily systolic samples only against explicit self-reported misses."""
    bp = [
        item for item in observations if item.kind == "blood_pressure" and item.systolic is not None
    ]
    missed_dates = {item.scheduled_for.date() for item in reports if item.status == "missed"}
    reported_dates = {item.scheduled_for.date() for item in reports}
    missed = [item for item in bp if item.measured_at.date() in missed_dates]
    not_missed = [item for item in bp if item.measured_at.date() in reported_dates - missed_dates]
    all_items = missed + not_missed
    if len(missed) < minimum_sample_size or len(not_missed) < minimum_sample_size:
        return _insufficient(
            "bp.self_reported_missed_dose_difference",
            "Systolic BP difference on self-reported missed-dose days",
            all_items,
            "Minimum self-reported comparison sample size not met",
        )
    missed_values = [Decimal(str(item.systolic)) for item in missed]
    not_missed_values = [Decimal(str(item.systolic)) for item in not_missed]
    start, end = _window(all_items)
    return AnalyticFact(
        "bp.self_reported_missed_dose_difference",
        "Systolic BP difference on self-reported missed-dose days",
        sum(missed_values) / Decimal(len(missed_values))
        - sum(not_missed_values) / Decimal(len(not_missed_values)),
        "mmHg",
        len(all_items),
        tuple(item.id for item in all_items),
        tuple(item.id for item in reports if item.status == "missed"),
        start,
        end,
        note="Observed association, not cause; only explicit self-reports are included",
    )
