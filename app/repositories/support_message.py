from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SupportMessage


class SupportMessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, message: SupportMessage) -> SupportMessage:
        self.db.add(message)
        return message

    async def list_for_ticket(self, ticket_id: UUID) -> list[SupportMessage]:
        result = await self.db.execute(
            select(SupportMessage).where(SupportMessage.ticket_id == ticket_id).order_by(SupportMessage.created_at.asc())
        )
        return list(result.scalars().unique().all())

