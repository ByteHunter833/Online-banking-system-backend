from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationPreference, User
from app.repositories.notification_preference import NotificationPreferenceRepository
from app.schemas.notification_preferences import (
    NotificationChannelPreference,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
)


class NotificationPreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = NotificationPreferenceRepository(db)

    async def get_or_create(self, user: User) -> NotificationPreference:
        preference = await self.repository.get_for_user(user.id)
        if preference is None:
            preference = NotificationPreference(user_id=user.id)
            self.repository.add(preference)
            await self.db.flush()
        return preference

    @staticmethod
    def _serialize(preference: NotificationPreference) -> NotificationPreferencesResponse:
        return NotificationPreferencesResponse(
            system=NotificationChannelPreference(
                in_app=preference.system_in_app,
                email=preference.system_email,
                sms=preference.system_sms,
            ),
            security_alert=NotificationChannelPreference(
                in_app=preference.security_alert_in_app,
                email=preference.security_alert_email,
                sms=preference.security_alert_sms,
            ),
            transaction=NotificationChannelPreference(
                in_app=preference.transaction_in_app,
                email=preference.transaction_email,
                sms=preference.transaction_sms,
            ),
            support=NotificationChannelPreference(
                in_app=preference.support_in_app,
                email=preference.support_email,
                sms=preference.support_sms,
            ),
        )

    async def update_preferences(
        self,
        *,
        user: User,
        payload: NotificationPreferencesUpdateRequest,
    ) -> NotificationPreferencesResponse:
        preference = await self.get_or_create(user)
        for category in ("system", "security_alert", "transaction", "support"):
            value = getattr(payload, category)
            if value is None:
                continue
            setattr(preference, f"{category}_in_app", value.in_app)
            setattr(preference, f"{category}_email", value.email)
            setattr(preference, f"{category}_sms", value.sms)
        await self.db.commit()
        await self.db.refresh(preference)
        return self._serialize(preference)

    async def get_preferences(self, user: User) -> NotificationPreferencesResponse:
        preference = await self.get_or_create(user)
        await self.db.commit()
        return self._serialize(preference)

