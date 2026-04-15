from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card


class CardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_user(self, user_id: UUID) -> list[Card]:
        result = await self.db.execute(select(Card).where(Card.user_id == user_id))
        return list(result.scalars().unique().all())

    async def get_by_id(self, card_id: UUID) -> Card | None:
        result = await self.db.execute(select(Card).where(Card.id == card_id))
        return result.scalars().unique().first()

    async def get_by_id_for_user(self, card_id: UUID, user_id: UUID) -> Card | None:
        result = await self.db.execute(
            select(Card).where(Card.id == card_id, Card.user_id == user_id)
        )
        return result.scalars().unique().first()

    def add(self, card: Card) -> Card:
        self.db.add(card)
        return card

