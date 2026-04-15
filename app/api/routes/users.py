from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_user_service
from app.schemas.common import MessageResponse
from app.schemas.user import (
    ChangePasswordRequest,
    DeactivateAccountRequest,
    UserProfileResponse,
    UserUpdateRequest,
)
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def me(current_user=Depends(get_current_user), user_service: UserService = Depends(get_user_service)):
    return await user_service.get_profile(current_user)


@router.patch("/update", response_model=UserProfileResponse)
async def update_profile(
    payload: UserUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.update_profile(current_user=current_user, payload=payload, request=request)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.change_password(current_user=current_user, payload=payload, request=request)


@router.post("/deactivate", response_model=MessageResponse)
async def deactivate_account(
    payload: DeactivateAccountRequest,
    request: Request,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.deactivate_account(current_user=current_user, payload=payload, request=request)

