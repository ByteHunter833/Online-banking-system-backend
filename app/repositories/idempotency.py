from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, key: IdempotencyKey) -> IdempotencyKey:
        self.db.add(key)
        return key

    async def get_key(self, user_id: UUID, operation: str, key: str) -> IdempotencyKey | None:
        result = await self.db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.operation == operation,
                IdempotencyKey.key == key,
            )
        )
        return result.scalars().unique().first()

