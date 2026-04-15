from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LoginEvent


class LoginEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, event: LoginEvent) -> LoginEvent:
        self.db.add(event)
        return event

