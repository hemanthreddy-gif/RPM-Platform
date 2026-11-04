"""Pure input/output contracts for deterministic clinical-rule evaluation."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class Observation(BaseModel):
    type: Literal["glucose", "blood_pressure", "heart_rate", "spo2"]
    value: Decimal | None = None
    components: dict[str, Decimal] = Field(default_factory=dict)
    context: dict[str, object] = Field(default_factory=dict)
    measured_at: datetime


class MedicationDoseReport(BaseModel):
    """A patient-authored medication status fact supplied to the pure evaluator."""

    medication_id: str
    status: Literal["taken", "missed", "skipped"]
    reported_at: datetime


class PatientContext(BaseModel):
    targets: dict[str, tuple[Decimal | None, Decimal | None]] = Field(default_factory=dict)
    symptoms: set[str] = Field(default_factory=set)
    history: list[Observation] = Field(default_factory=list)
    medication_reports: list[MedicationDoseReport] = Field(default_factory=list)


class RuleDefinition(BaseModel):
    code: str
    version: int
    applies_to: str
    severity: Literal["informational", "attention", "urgent"]
    condition: dict[str, object]
    message_key: str
    dedupe_window_min: int = Field(gt=0)
    requires_clinician_approval: bool
    synthetic_demo_only: bool
    pattern: dict[str, object] | None = None


class AlertDecision(BaseModel):
    rule_code: str
    rule_version: int
    severity: Literal["informational", "attention", "urgent"]
    message_key: str
    dedupe_window_min: int
    urgent_guidance: bool = False
