from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TrustedDevice


class TrustedDeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, device: TrustedDevice) -> TrustedDevice:
        self.db.add(device)
        return device

    async def get_for_user(self, user_id: UUID, device_id: str) -> TrustedDevice | None:
        result = await self.db.execute(
            select(TrustedDevice).where(TrustedDevice.user_id == user_id, TrustedDevice.device_id == device_id)
        )
        return result.scalars().unique().first()

