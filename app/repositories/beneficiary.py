from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Beneficiary


class BeneficiaryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, beneficiary: Beneficiary) -> Beneficiary:
        self.db.add(beneficiary)
        return beneficiary

    async def list_for_user(self, user_id: UUID) -> list[Beneficiary]:
        result = await self.db.execute(
            select(Beneficiary).where(Beneficiary.user_id == user_id).order_by(Beneficiary.created_at.desc())
        )
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: UUID) -> int:
        return len(await self.list_for_user(user_id))

    async def get_for_user(self, beneficiary_id: UUID, user_id: UUID) -> Beneficiary | None:
        result = await self.db.execute(
            select(Beneficiary).where(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id)
        )
        return result.scalars().unique().first()

