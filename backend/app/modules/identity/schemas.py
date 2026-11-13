"""Typed API contracts for the identity module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=200)


class ProvisionRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(pattern="^(physician|admin)$")
    display_name: str | None = Field(default=None, max_length=200)
    registration_no: str | None = Field(default=None, max_length=100)
    specialty: str | None = Field(default=None, max_length=100)


class PhysicianInvitationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    registration_no: str = Field(min_length=1, max_length=100)
    specialty: str | None = Field(default=None, max_length=100)


class PhysicianInvitationResponse(BaseModel):
    invitation_token: str
    expires_at: datetime


class PhysicianProfile(BaseModel):
    id: UUID
    display_name: str
    specialty: str | None
    registration_no: str


class PhysicianOnboardingStart(BaseModel):
    invitation_token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class PhysicianEnrollmentResponse(BaseModel):
    enrollment_token: str
    provisioning_uri: str
    expires_at: datetime


class PhysicianOnboardingComplete(BaseModel):
    enrollment_token: str = Field(min_length=20, max_length=256)
    code: str = Field(pattern=r"^\d{6}$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    totp_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    mfa_required: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=12, max_length=256)


class MfaEnrollResponse(BaseModel):
    provisioning_uri: str


class MfaVerifyRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class Principal(BaseModel):
    user_id: UUID
    role: str
    mfa: bool
    expires_at: datetime
    issued_at: datetime
