from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.observations.schemas import (
    GLUCOSE_MGDL_PER_MMOLL,
    ObservationCreate,
    TargetRequest,
    canonical_value,
)


def test_glucose_mmol_is_canonicalised_to_mgdl() -> None:
    payload = ObservationCreate(
        type="glucose", value=Decimal("5"), unit="mmol/L", measured_at=datetime.now(UTC)
    )
    value, unit = canonical_value(payload)
    assert unit == "mg/dL"
    assert value == Decimal("90.08")
    assert GLUCOSE_MGDL_PER_MMOLL == Decimal("18.016")


def test_glucose_rejects_unknown_unit() -> None:
    with pytest.raises(ValidationError, match="Glucose unit"):
        ObservationCreate(
            type="glucose", value=Decimal("90"), unit="grams", measured_at=datetime.now(UTC)
        )


def test_blood_pressure_requires_positive_components() -> None:
    with pytest.raises(ValidationError, match="systolic"):
        ObservationCreate(
            type="blood_pressure",
            unit="mmHg",
            components={"systolic": Decimal("120")},
            measured_at=datetime.now(UTC),
        )


def test_target_requires_an_ordered_range() -> None:
    with pytest.raises(ValidationError, match="less than"):
        TargetRequest(type="glucose", low=Decimal("100"), high=Decimal("100"))


def test_blood_pressure_uses_component_values_and_mmhg() -> None:
    payload = ObservationCreate(
        type="blood_pressure",
        unit="mmHg",
        components={"systolic": 120, "diastolic": 80},
        measured_at=datetime.now(UTC),
    )
    assert payload.value is None
    assert canonical_value(payload) == (None, "mmHg")
    with pytest.raises(ValidationError, match="mmHg"):
        ObservationCreate(
            type="blood_pressure",
            unit="bpm",
            components=payload.components,
            measured_at=datetime.now(UTC),
        )
