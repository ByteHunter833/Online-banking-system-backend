from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_notification_preference_service, get_notification_service
from app.schemas.notification import NotificationResponse
from app.schemas.notification_preferences import NotificationPreferencesResponse, NotificationPreferencesUpdateRequest
from app.services.notification import NotificationService
from app.services.notification_preference import NotificationPreferenceService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    return await notification_service.list_for_user(current_user)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    return await notification_service.mark_read(current_user, notification_id)


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user=Depends(get_current_user),
    preference_service: NotificationPreferenceService = Depends(get_notification_preference_service),
):
    return await preference_service.get_preferences(current_user)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    payload: NotificationPreferencesUpdateRequest,
    current_user=Depends(get_current_user),
    preference_service: NotificationPreferenceService = Depends(get_notification_preference_service),
):
    return await preference_service.update_preferences(user=current_user, payload=payload)
