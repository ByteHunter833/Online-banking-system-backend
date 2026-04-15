from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthChallenge


class AuthChallengeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, challenge: AuthChallenge) -> AuthChallenge:
        self.db.add(challenge)
        return challenge

    async def get_for_user(self, challenge_id: UUID, user_id: UUID) -> AuthChallenge | None:
        result = await self.db.execute(
            select(AuthChallenge).where(
                AuthChallenge.id == challenge_id,
                AuthChallenge.user_id == user_id,
            )
        )
        return result.scalars().unique().first()

    async def get_verified(self, challenge_id: UUID, user_id: UUID, purpose: str | None = None) -> AuthChallenge | None:
        filters = [
            AuthChallenge.id == challenge_id,
            AuthChallenge.user_id == user_id,
            AuthChallenge.status == "verified",
            AuthChallenge.expires_at >= datetime.now(timezone.utc),
            AuthChallenge.used_at.is_(None),
        ]
        if purpose is not None:
            filters.append(AuthChallenge.purpose == purpose)
        result = await self.db.execute(select(AuthChallenge).where(*filters))
        return result.scalars().unique().first()

