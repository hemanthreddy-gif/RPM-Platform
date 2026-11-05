"""Unit safety tests for the Phase 9 device and explicitly limited FHIR subset."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.devices.schemas import DeviceReadingRequest
from app.modules.fhir.service import bundle, observation_resource, validate_r4_subset
from app.modules.messaging.schemas import MessageCreateRequest


def _row(kind: str) -> dict[str, object]:
    return {
        "id": uuid4(),
        "patient_id": uuid4(),
        "type": kind,
        "value": 101,
        "unit": "mg/dL",
        "components": {},
        "context": {},
        "measured_at": datetime(2026, 10, 1, tzinfo=UTC),
        "recorded_at": datetime(2026, 10, 1, tzinfo=UTC),
    }


def test_glucose_fhir_requires_explicit_recorded_blood_specimen_coding() -> None:
    with pytest.raises(ValueError, match="explicit recorded"):
        observation_resource(_row("glucose"))

    row = _row("glucose")
    row["context"] = {"fhir": {"system": "http://loinc.org", "code": "2339-0", "specimen": "blood"}}
    resource = observation_resource(row)

    assert resource["valueQuantity"] == {
        "value": 101,
        "unit": "mg/dL",
        "system": "http://unitsofmeasure.org",
        "code": "mg/dL",
    }
    validate_r4_subset(resource)


def test_bp_fhir_has_required_panel_and_component_shape() -> None:
    row = _row("blood_pressure")
    row["components"] = {"systolic": 120, "diastolic": 80}
    resource = observation_resource(row)

    assert resource["code"]["coding"][0]["code"] == "85354-9"  # type: ignore[index]
    assert len(resource["component"]) == 2  # type: ignore[arg-type]
    validate_r4_subset(bundle([resource]))


def test_device_payload_reuses_glucose_unit_and_bp_component_safety_shape() -> None:
    with pytest.raises(ValidationError, match="Glucose unit"):
        DeviceReadingRequest(
            type="glucose", value=1, unit="arbitrary", measured_at=datetime.now(UTC)
        )
    with pytest.raises(ValidationError, match="systolic"):
        DeviceReadingRequest(type="blood_pressure", unit="mmHg", measured_at=datetime.now(UTC))


def test_message_body_cannot_be_blank_before_any_database_write() -> None:
    with pytest.raises(ValidationError):
        MessageCreateRequest(body="")
