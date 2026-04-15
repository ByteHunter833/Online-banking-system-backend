from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import TransactionStatus, TransactionType


class TransferRequest(BaseModel):
    from_account_id: UUID
    recipient_account_number: str = Field(min_length=8, max_length=32)
    amount: Decimal = Field(gt=Decimal("0.00"))
    description: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)
    otp_code: str | None = None
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
