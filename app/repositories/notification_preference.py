from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationPreference


class NotificationPreferenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, preference: NotificationPreference) -> NotificationPreference:
        self.db.add(preference)
        return preference

    async def get_for_user(self, user_id: UUID) -> NotificationPreference | None:
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalars().unique().first()

