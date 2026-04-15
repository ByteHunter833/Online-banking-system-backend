from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StatementExport


class StatementExportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, export: StatementExport) -> StatementExport:
        self.db.add(export)
        return export

    async def get_by_id(self, export_id: UUID) -> StatementExport | None:
        result = await self.db.execute(select(StatementExport).where(StatementExport.id == export_id))
        return result.scalars().unique().first()

    async def get_for_user(self, export_id: UUID, user_id: UUID) -> StatementExport | None:
        result = await self.db.execute(
            select(StatementExport).where(
                StatementExport.id == export_id,
                StatementExport.user_id == user_id,
            )
        )
        return result.scalars().unique().first()
