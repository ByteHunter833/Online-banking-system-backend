from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import AccountStatus


class BankAccountCreateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    initial_deposit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_primary: bool = False


class BankAccountResponse(BaseModel):
    id: UUID
    account_number: str
    iban: str
    nickname: str | None
    currency: str
    status: AccountStatus
    is_primary: bool
    balance: Decimal
    available_balance: Decimal
    daily_transfer_limit: Decimal
    daily_transferred_amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BankAccountPreferencesUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=100)
    is_primary: bool | None = None
