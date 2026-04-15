from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import ChallengePurpose, ChallengeStatus, MFAMethod, MFASecretStatus, SessionStatus


class TOTPSetupRequest(BaseModel):
    password: str


class TOTPSetupResponse(BaseModel):
    mfa_setup_id: UUID
    secret_base32: str
    otpauth_url: str
    expires_at: datetime


class TOTPConfirmRequest(BaseModel):
    mfa_setup_id: UUID
    code: str = Field(min_length=6, max_length=8)


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    status: MFASecretStatus
    recovery_codes: list[str] | None = None


class ChallengeCreateRequest(BaseModel):
    purpose: ChallengePurpose
    preferred_method: MFAMethod = MFAMethod.totp
    context: dict | None = None


class ChallengeResponse(BaseModel):
    challenge_id: UUID
    purpose: ChallengePurpose
    allowed_methods: list[MFAMethod]
    status: ChallengeStatus
    expires_at: datetime


class ChallengeVerifyRequest(BaseModel):
    method: MFAMethod
    code: str = Field(min_length=6, max_length=64)


class ChallengeVerifyResponse(BaseModel):
    status: ChallengeStatus
    verified_at: datetime
    verified_method: MFAMethod


class SessionResponse(BaseModel):
    id: UUID
    family_id: str
    device_id: str | None
    device_name: str | None
    ip_address: str | None
    last_seen_at: datetime | None
    status: SessionStatus
    current: bool

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    items: list[SessionResponse]

