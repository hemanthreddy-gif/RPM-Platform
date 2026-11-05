"""Typed contracts and non-clinical structural validation for observations."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

GLUCOSE_MGDL_PER_MMOLL = Decimal("18.016")


class ObservationCreate(BaseModel):
    type: Literal["glucose", "blood_pressure", "heart_rate", "spo2"]
    value: Decimal | None = Field(default=None, gt=0)
    unit: str = Field(min_length=1, max_length=32)
    components: dict[str, Decimal] = Field(default_factory=dict)
    measured_at: datetime
    context: dict[str, object] = Field(default_factory=dict)
    confirm_unusual: bool = False

    @model_validator(mode="after")
    def validate_shape(self) -> "ObservationCreate":
        if self.type == "blood_pressure":
            required = {"systolic", "diastolic"}
            if not required.issubset(self.components) or any(
                value <= 0 for value in self.components.values()
            ):
                raise ValueError(
                    "Blood pressure requires positive systolic and diastolic components"
                )
        elif self.value is None:
            raise ValueError("This observation type requires a positive value")
        if self.type == "blood_pressure" and self.unit != "mmHg":
            raise ValueError("Blood pressure unit must be mmHg")
        if self.type == "glucose" and self.unit not in {"mg/dL", "mmol/L"}:
            raise ValueError("Glucose unit must be mg/dL or mmol/L")
        return self


class ObservationResponse(BaseModel):
    id: str
    patient_id: str
    type: str
    value: Decimal | None
    unit: str
    original_value: Decimal | None
    original_unit: str
    components: dict[str, Decimal]
    measured_at: datetime
    recorded_at: datetime
    source: str
    quality_flag: str | None
    supersedes_id: str | None
    alerts: list[dict[str, object]] = Field(default_factory=list)
    alert_creation_latency_ms: float | None = None


class CorrectionRequest(ObservationCreate):
    pass


class TargetRequest(BaseModel):
    type: Literal["glucose", "blood_pressure", "heart_rate", "spo2"]
    context: str = Field(default="default", min_length=1, max_length=64)
    low: Decimal | None = None
    high: Decimal | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "TargetRequest":
        if self.low is not None and self.high is not None and self.low >= self.high:
            raise ValueError("Target low must be less than target high")
        return self


def canonical_value(payload: ObservationCreate) -> tuple[Decimal | None, str]:
    if payload.type == "glucose" and payload.value is not None:
        value = payload.value
        if payload.unit == "mmol/L":
            value = (value * GLUCOSE_MGDL_PER_MMOLL).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return value, "mg/dL"
    return payload.value, payload.unit
