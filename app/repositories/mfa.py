from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MFASecret


class MFARepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, secret: MFASecret) -> MFASecret:
        self.db.add(secret)
        return secret

    async def get_pending(self, user_id: UUID, setup_id: UUID) -> MFASecret | None:
        result = await self.db.execute(
            select(MFASecret).where(
                MFASecret.id == setup_id,
                MFASecret.user_id == user_id,
                MFASecret.status == "pending",
            )
        )
        return result.scalars().unique().first()

    async def get_active_for_user(self, user_id: UUID) -> MFASecret | None:
        result = await self.db.execute(
            select(MFASecret).where(MFASecret.user_id == user_id, MFASecret.status == "active")
        )
        return result.scalars().unique().first()

