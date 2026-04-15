from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import CardStatus, CardType


class CardCreateRequest(BaseModel):
    account_id: UUID
    card_type: CardType = CardType.virtual
    spending_limit: Decimal | None = None


class CardLimitUpdateRequest(BaseModel):
    spending_limit: Decimal


class CardActionRequest(BaseModel):
    reason: str | None = None


class CardControlsUpdateRequest(BaseModel):
    online_enabled: bool | None = None
    atm_enabled: bool | None = None
    contactless_enabled: bool | None = None
    spending_limit: Decimal | None = None


class CardResponse(BaseModel):
    id: UUID
    account_id: UUID
    masked_pan: str
    last4: str
    brand: str
    card_type: CardType
    status: CardStatus
    spending_limit: Decimal | None
    online_enabled: bool
    atm_enabled: bool
    contactless_enabled: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
