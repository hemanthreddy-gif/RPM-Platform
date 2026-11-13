"""Input boundaries for synthetic profiles, private pictures and self-reported sleep."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException
from PIL import Image
from pydantic import ValidationError

from app.modules.observations.schemas import ObservationCreate, TargetRequest
from app.modules.patients.schemas import ConnectionCreate, ProfileUpdate
from app.modules.patients.service import MAX_PICTURE_BYTES, age_on, normalize_picture


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (700, 350), "green").save(output, format="PNG")
    return output.getvalue()


def test_birth_date_uses_calendar_age_and_rejects_future_dates() -> None:
    assert age_on(date(2000, 11, 7), date(2026, 11, 6)) == 25
    assert age_on(date(2000, 11, 6), date(2026, 11, 6)) == 26
    assert age_on(None, date(2026, 11, 6)) is None
    with pytest.raises(ValidationError):
        ProfileUpdate(
            display_name="Fictional profile", date_of_birth=date.today() + timedelta(days=1)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("display_name", "   "),
        ("height_cm", -1),
        ("weight_kg", 0),
        ("phone", "<script>"),
        ("timezone", "No/Such_Timezone"),
        ("role", "physician"),
    ],
)
def test_profile_rejects_invalid_or_privilege_fields(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({"display_name": "Fictional profile", field: value})


def test_picture_is_reencoded_bounded_jpeg() -> None:
    result = normalize_picture(_png(), "image/png")
    with Image.open(BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.size == (512, 256)
        assert not image.getexif()


@pytest.mark.parametrize(
    "payload,content_type,status",
    [
        (b"<svg></svg>", "image/svg+xml", 415),
        (b"invalid", "image/png", 422),
        (b"", "image/jpeg", 413),
        (b"a" * (MAX_PICTURE_BYTES + 1), "image/png", 413),
    ],
)
def test_picture_rejects_untrusted_and_oversized_payloads(
    payload: bytes,
    content_type: str,
    status: int,
) -> None:
    with pytest.raises(HTTPException) as error:
        normalize_picture(payload, content_type)
    assert error.value.status_code == status


@pytest.mark.parametrize("hours", [0, 7.5, 24])
def test_sleep_accepts_hours_including_zero(hours: float) -> None:
    reading = ObservationCreate(type="sleep", value=hours, unit="h", measured_at=datetime.now(UTC))
    assert reading.value == Decimal(str(hours))


@pytest.mark.parametrize("value,unit", [(-1, "h"), (24.1, "h"), (8, "hours"), (None, "h")])
def test_sleep_rejects_invalid_duration_or_unit(value: object, unit: str) -> None:
    with pytest.raises(ValidationError):
        ObservationCreate.model_validate(
            {"type": "sleep", "value": value, "unit": unit, "measured_at": datetime.now(UTC)}
        )


def test_sleep_cannot_create_clinical_targets_or_loosen_existing_reading_bounds() -> None:
    with pytest.raises(ValidationError):
        TargetRequest.model_validate({"type": "sleep", "low": 5, "high": 10})
    with pytest.raises(ValidationError):
        ObservationCreate(type="glucose", value=0, unit="mg/dL", measured_at=datetime.now(UTC))


def test_connection_requires_explicit_consent() -> None:
    with pytest.raises(ValidationError):
        ConnectionCreate.model_validate({"physician_id": uuid4(), "consent": False})
    with pytest.raises(ValidationError):
        ConnectionCreate.model_validate({"physician_id": uuid4()})
