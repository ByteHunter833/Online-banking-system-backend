from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_strength
from app.schemas.enums import NotificationChannel, OTPPurpose
from app.schemas.user import UserSummary


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str | None = None
    device_name: str | None = None
    totp_code: str | None = None
    recovery_code: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp_code: str


class OTPRequest(BaseModel):
    purpose: OTPPurpose
    delivery_channel: NotificationChannel = NotificationChannel.email


class OTPVerifyRequest(BaseModel):
    purpose: OTPPurpose
    otp_code: str


class OTPDispatchResponse(BaseModel):
    message: str
    purpose: OTPPurpose
    expires_in_seconds: int
    delivery_channel: NotificationChannel
    debug_otp: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_in: int
    refresh_token_expires_in: int
    user: UserSummary


class RegisterResponse(BaseModel):
    message: str
    email_verification_required: bool = True
    debug_otp: str | None = None
