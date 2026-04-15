from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OTPCode


class OTPRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, otp_code: OTPCode) -> OTPCode:
        self.db.add(otp_code)
        return otp_code

    async def get_active_code(self, user_id: UUID, purpose: str, extra_match: dict | None = None) -> OTPCode | None:
        result = await self.db.execute(
            select(OTPCode)
            .where(
                OTPCode.user_id == user_id,
                OTPCode.purpose == purpose,
                OTPCode.consumed_at.is_(None),
            )
            .order_by(OTPCode.created_at.desc())
        )
        codes = result.scalars().unique().all()
        now = datetime.now(timezone.utc)
        for code in codes:
            if extra_match:
                extra_data = code.extra_data or {}
                if any(extra_data.get(key) != value for key, value in extra_match.items()):
                    continue
            if code.expires_at >= now:
                return code
        return None
