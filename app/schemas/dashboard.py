from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.schemas.account import BankAccountResponse
from app.schemas.card import CardResponse
from app.schemas.transaction import TransactionResponse


class DashboardOverviewResponse(BaseModel):
    total_balance: Decimal
    unread_notifications: int
    pending_kyc_status: str | None
    alerts: list[str]
    accounts: list[BankAccountResponse]
    recent_transactions: list[TransactionResponse]
    frozen_cards: list[CardResponse]

