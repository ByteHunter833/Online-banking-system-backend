from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KYCSubmission


class KYCRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, submission: KYCSubmission) -> KYCSubmission:
        self.db.add(submission)
        return submission

    async def list_all(self) -> list[KYCSubmission]:
        result = await self.db.execute(select(KYCSubmission).order_by(KYCSubmission.created_at.desc()))
        return list(result.scalars().unique().all())

    async def get(self, submission_id: UUID) -> KYCSubmission | None:
        result = await self.db.execute(select(KYCSubmission).where(KYCSubmission.id == submission_id))
        return result.scalars().unique().first()

