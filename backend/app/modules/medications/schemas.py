"""Typed medication API contracts; no medication advice is generated here."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MedicationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    strength: str | None = Field(default=None, max_length=100)
    dose: str | None = Field(default=None, max_length=100)
    route: str | None = Field(default=None, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    schedule_times: list[time] = Field(min_length=1, max_length=12)
    start_date: date
    end_date: date | None = None
    instructions: str | None = Field(default=None, max_length=2000)

    @field_validator("schedule_times")
    @classmethod
    def unique_schedule_times(cls, values: list[time]) -> list[time]:
        if len(set(values)) != len(values):
            raise ValueError("Schedule times must be unique")
        return sorted(values)

    @model_validator(mode="after")
    def valid_date_range(self) -> "MedicationRequest":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date must not precede start date")
        return self


class DoseReportRequest(BaseModel):
    status: Literal["taken", "missed", "skipped"]
    reported_at: datetime
    concern_note: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("reported_at")
    @classmethod
    def requires_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reported_at must include a UTC offset")
        return value


class MedicationResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    strength: str | None
    dose: str | None
    route: str | None
    frequency: str
    schedule_times: list[str]
    timezone: str
    start_date: date | None
    end_date: date | None
    instructions: str | None
    version: int
    authored_by: str
    provenance: Literal["physician_authored_synthetic_record"]


class DoseReportResponse(BaseModel):
    id: str
    status: Literal["taken", "missed", "skipped"]
    scheduled_for: datetime
    reported_at: datetime
    self_reported: Literal[True] = True
    concern_flagged_for_physician: bool
