from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import NotificationChannel, OTPPurpose, TransactionStatus, TransactionType


class TransferDraft(BaseModel):
    from_account_id: UUID
    recipient_account_number: str = Field(min_length=8, max_length=32)
    amount: Decimal = Field(gt=Decimal("0.00"))
    description: str | None = Field(default=None, max_length=255)


class TransferVerificationRequest(TransferDraft):
    delivery_channel: NotificationChannel = NotificationChannel.email


class TransferVerificationResponse(BaseModel):
    message: str
    purpose: OTPPurpose
    expires_in_seconds: int
    delivery_channel: NotificationChannel
    debug_otp: str | None = None


class TransferRequest(TransferDraft):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)
    otp_code: str | None = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")
    challenge_id: UUID | None = None


class TransactionResponse(BaseModel):
    id: UUID
    reference: str
    from_account_id: UUID
    to_account_id: UUID
    amount: Decimal
    fee_amount: Decimal
    currency: str
    description: str | None
    status: TransactionStatus
    transaction_type: TransactionType
    risk_flag: bool
    risk_score: int
    risk_status: str
    failure_reason: str | None
    processed_at: datetime | None
    review_required_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
