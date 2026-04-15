from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import NotificationCategory, NotificationChannel


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    message: str
    category: NotificationCategory
    channel: NotificationChannel
    is_read: bool
    read_at: datetime | None
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}

