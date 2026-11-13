"""Typed patient profile and explicit monitoring-connection contracts."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal["female", "male", "non_binary", "other", "prefer_not_to_say"]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=200)
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=24, pattern=r"^[+0-9 ()-]+$")
    height_cm: Decimal | None = Field(default=None, gt=0, le=300, max_digits=5, decimal_places=2)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=700, max_digits=5, decimal_places=2)
    timezone: str = "Asia/Kolkata"
    has_hypertension: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def past_birth_date(cls, value: date | None) -> date | None:
        if value is not None and (value > datetime.now(UTC).date() or value.year < 1900):
            raise ValueError("Birth date must be between 1900 and today")
        return value

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Choose a valid IANA timezone") from exc
        return value


class PatientProfile(ProfileUpdate):
    id: UUID
    age: int | None = None
    has_profile_picture: bool = False
    profile_picture_updated_at: datetime | None = None


class PhysicianDirectoryItem(BaseModel):
    id: UUID
    display_name: str
    specialty: str | None


class ConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    physician_id: UUID
    consent: Literal[True]


class PatientConnection(BaseModel):
    id: UUID
    physician_id: UUID
    display_name: str
    specialty: str | None
    consent_id: UUID
    started_at: datetime
    active: bool
