from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSession


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, session: UserSession) -> UserSession:
        self.db.add(session)
        return session

    async def get_by_id_for_user(self, session_id: UUID, user_id: UUID) -> UserSession | None:
        result = await self.db.execute(
            select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id)
        )
        return result.scalars().unique().first()

    async def get_by_family_id(self, family_id: str) -> UserSession | None:
        result = await self.db.execute(select(UserSession).where(UserSession.family_id == family_id))
        return result.scalars().unique().first()

    async def list_for_user(self, user_id: UUID) -> list[UserSession]:
        result = await self.db.execute(
            select(UserSession).where(UserSession.user_id == user_id).order_by(UserSession.created_at.desc())
        )
        return list(result.scalars().unique().all())

