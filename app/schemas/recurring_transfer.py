from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import RecurringFrequency, RecurringTransferStatus


class RecurringTransferCreateRequest(BaseModel):
    from_account_id: UUID
    beneficiary_id: UUID
    amount: Decimal = Field(gt=Decimal("0.00"))
    frequency: RecurringFrequency
    start_date: date
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=255)
    challenge_id: UUID


class RecurringTransferResponse(BaseModel):
    id: UUID
    from_account_id: UUID
    beneficiary_id: UUID
    amount: Decimal
    frequency: RecurringFrequency
    status: RecurringTransferStatus
    start_date: date
    end_date: date | None
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

