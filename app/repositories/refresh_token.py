from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        return token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.scalars().unique().first()

    async def revoke_family(self, family_id: str) -> list[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return list(result.scalars().unique().all())

    async def revoke_all_for_user(self, user_id: UUID) -> list[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return list(result.scalars().unique().all())

    async def revoke_by_session(self, session_id: UUID) -> list[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return list(result.scalars().unique().all())
