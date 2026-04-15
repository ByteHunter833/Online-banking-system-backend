from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.account import AccountRepository
from app.repositories.card import CardRepository
from app.repositories.transaction import TransactionRepository
from app.services.notification import NotificationService


class DashboardService:
    def __init__(self, db: AsyncSession, notification_service: NotificationService) -> None:
        self.accounts = AccountRepository(db)
        self.cards = CardRepository(db)
        self.transactions = TransactionRepository(db)
        self.notification_service = notification_service

    async def overview(self, current_user: User) -> dict:
        accounts = await self.accounts.list_by_user(current_user.id)
        cards = await self.cards.list_by_user(current_user.id)
        transactions = await self.transactions.list_recent_for_user(current_user.id, limit=5)
        unread = await self.notification_service.unread_count(current_user)
        alerts: list[str] = []
        if current_user.kyc_status != "verified":
            alerts.append("complete_kyc")
        if any(card.status == "frozen" for card in cards):
            alerts.append("frozen_cards")
        return {
            "total_balance": sum((Decimal(account.balance) for account in accounts), Decimal("0.00")),
            "unread_notifications": unread,
            "pending_kyc_status": current_user.kyc_status,
            "alerts": alerts,
            "accounts": accounts,
            "recent_transactions": transactions,
            "frozen_cards": [card for card in cards if card.status == "frozen"],
        }

