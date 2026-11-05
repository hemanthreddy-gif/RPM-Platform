"""Device pairing and ingestion contracts for the synthetic demo."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DeviceCreateRequest(BaseModel):
    kind: Literal["glucose_meter", "blood_pressure_monitor"]
    vendor: str = Field(min_length=1, max_length=100)
    serial: str | None = Field(default=None, min_length=1, max_length=100)


class DeviceCreateResponse(BaseModel):
    id: UUID
    pairing_token: str
    status: str


class DeviceReadingRequest(BaseModel):
    type: Literal["glucose", "blood_pressure"]
    value: Decimal | None = Field(default=None, gt=0)
    unit: str = Field(min_length=1, max_length=32)
    components: dict[str, Decimal] = Field(default_factory=dict)
    measured_at: datetime
    context: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shape(self) -> "DeviceReadingRequest":
        if self.type == "blood_pressure":
            if not {"systolic", "diastolic"}.issubset(self.components):
                raise ValueError("Blood pressure requires systolic and diastolic components")
        elif self.value is None:
            raise ValueError("This observation type requires a value")
        if self.type == "glucose" and self.unit not in {"mg/dL", "mmol/L"}:
            raise ValueError("Glucose unit must be mg/dL or mmol/L")
        return self


class DeviceResponse(BaseModel):
    id: UUID
    kind: str
    vendor: str
    serial: str | None
    status: str
    last_sync_at: datetime | None
    last_received_at: datetime | None
