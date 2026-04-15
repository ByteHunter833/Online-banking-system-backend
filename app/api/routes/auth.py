from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user, rate_limit
from app.api.dependencies.services import get_auth_service
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    OTPDispatchResponse,
    OTPRequest,
    OTPVerifyRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth-register", key_strategy="ip_email"))],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.register(payload, request)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("auth-verify-email", key_strategy="ip_email"))],
)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.verify_email(payload, request)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth-login", limit=5, window_seconds=60, key_strategy="ip_email"))],
)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.login(payload, request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.refresh(payload, request)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    request: Request,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.logout(current_user, payload, request)


@router.post(
    "/forgot-password",
    response_model=OTPDispatchResponse,
    dependencies=[Depends(rate_limit("auth-forgot-password", key_strategy="ip_email"))],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.forgot_password(payload, request)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("auth-reset-password", key_strategy="ip_email"))],
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.reset_password(payload, request)


@router.post(
    "/otp/request",
    response_model=OTPDispatchResponse,
    dependencies=[Depends(rate_limit("auth-otp-request", limit=3, window_seconds=600, key_strategy="user_purpose"))],
)
async def request_otp(
    payload: OTPRequest,
    request: Request,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.request_authenticated_otp(
        current_user=current_user,
        payload=payload,
        request=request,
    )


@router.post(
    "/otp/verify",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("auth-otp-verify", limit=5, window_seconds=600, key_strategy="user_purpose"))],
)
async def verify_otp(
    payload: OTPVerifyRequest,
    request: Request,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.verify_authenticated_otp(
        current_user=current_user,
        payload=payload,
        request=request,
    )
