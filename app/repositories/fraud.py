from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FraudCase, RiskEvent


class FraudRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add_case(self, case: FraudCase) -> FraudCase:
        self.db.add(case)
        return case

    def add_event(self, event: RiskEvent) -> RiskEvent:
        self.db.add(event)
        return event

    async def list_cases(self, *, status: str | None = None, score_gte: int | None = None) -> list[FraudCase]:
        filters = []
        if status is not None:
            filters.append(FraudCase.status == status)
        if score_gte is not None:
            filters.append(FraudCase.score >= score_gte)
        result = await self.db.execute(select(FraudCase).where(*filters).order_by(FraudCase.created_at.desc()))
        return list(result.scalars().unique().all())

    async def get_case(self, case_id: UUID) -> FraudCase | None:
        result = await self.db.execute(select(FraudCase).where(FraudCase.id == case_id))
        return result.scalars().unique().first()
