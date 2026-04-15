from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.enums import KYCStatus


class UserSummary(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_email_verified: bool
    mfa_enabled: bool
    biometric_enabled: bool
    kyc_status: KYCStatus
    roles: list[str]

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserSummary):
    phone: str | None = None
    date_of_birth: date | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    mfa_enabled: bool | None = None
    biometric_enabled: bool | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    otp_code: str


class DeactivateAccountRequest(BaseModel):
    password: str
    otp_code: str

