from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SupportTicket


class SupportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, ticket: SupportTicket) -> SupportTicket:
        self.db.add(ticket)
        return ticket

    async def list_by_user(self, user_id: UUID) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket)
            .where(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
        )
        return list(result.scalars().unique().all())

    async def get_by_id_for_user(self, ticket_id: UUID, user_id: UUID) -> SupportTicket | None:
        result = await self.db.execute(
            select(SupportTicket).where(
                SupportTicket.id == ticket_id,
                SupportTicket.user_id == user_id,
            )
        )
        return result.scalars().unique().first()

    async def get_by_id(self, ticket_id: UUID) -> SupportTicket | None:
        result = await self.db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        return result.scalars().unique().first()

    async def list_all(self) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket).order_by(SupportTicket.created_at.desc())
        )
        return list(result.scalars().unique().all())

