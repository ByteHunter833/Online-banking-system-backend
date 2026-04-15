from __future__ import annotations

from pydantic import BaseModel


class NotificationChannelPreference(BaseModel):
    in_app: bool = True
    email: bool = False
    sms: bool = False


class NotificationPreferencesUpdateRequest(BaseModel):
    system: NotificationChannelPreference | None = None
    security_alert: NotificationChannelPreference | None = None
    transaction: NotificationChannelPreference | None = None
    support: NotificationChannelPreference | None = None


class NotificationPreferencesResponse(BaseModel):
    system: NotificationChannelPreference
    security_alert: NotificationChannelPreference
    transaction: NotificationChannelPreference
    support: NotificationChannelPreference
