from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models import Notification, User
from app.repositories.notification import NotificationRepository
from app.repositories.notification_preference import NotificationPreferenceRepository
from app.schemas.enums import NotificationCategory
from app.services.communication import CommunicationService
from app.workers.tasks import send_email_notification, send_sms_notification


class NotificationService:
    def __init__(self, db: AsyncSession, communication: CommunicationService) -> None:
        self.db = db
        self.repository = NotificationRepository(db)
        self.preferences = NotificationPreferenceRepository(db)
        self.communication = communication

    async def _channel_allowed(self, user: User, category: NotificationCategory, channel: str) -> bool:
        preference = await self.preferences.get_for_user(user.id)
        if preference is None:
            return channel != "sms"
        prefix = category.value if category.value != "security_alert" else "security_alert"
        return bool(getattr(preference, f"{prefix}_{channel}", False))

    async def create_notification(
        self,
        *,
        user: User,
        title: str,
        message: str,
        category: NotificationCategory = NotificationCategory.system,
        payload: dict | None = None,
        send_email: bool = False,
        send_sms: bool = False,
    ) -> Notification:
        notification = Notification(
            user_id=user.id,
            title=title,
            message=message,
            category=category.value,
            channel="in_app",
            payload=payload,
        )
        self.repository.add(notification)
        await self.db.flush()

        if send_email and await self._channel_allowed(user, category, "email"):
            try:
                send_email_notification.delay(user.email, title, message)
            except Exception:
                await self.communication.send_email(user.email, title, message)
        if send_sms and user.phone and await self._channel_allowed(user, category, "sms"):
            try:
                send_sms_notification.delay(user.phone, message)
            except Exception:
                await self.communication.send_sms(user.phone, message)

        return notification

    async def list_for_user(self, user: User) -> list[Notification]:
        return await self.repository.list_by_user(user.id)

    async def unread_count(self, user: User) -> int:
        return await self.repository.count_unread(user.id)

    async def mark_read(self, user: User, notification_id: UUID) -> Notification:
        notification = await self.repository.get_by_id_for_user(notification_id, user.id)
        if notification is None:
            raise NotFoundException("Notification not found.")
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification
