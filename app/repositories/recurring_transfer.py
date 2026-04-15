from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecurringTransfer


class RecurringTransferRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, recurring_transfer: RecurringTransfer) -> RecurringTransfer:
        self.db.add(recurring_transfer)
        return recurring_transfer

