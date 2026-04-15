from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_challenge_service, get_mfa_service, get_session_service
from app.schemas.common import MessageResponse
from app.schemas.security import (
    ChallengeCreateRequest,
    ChallengeResponse,
    ChallengeVerifyRequest,
    ChallengeVerifyResponse,
    MFAStatusResponse,
    SessionListResponse,
    TOTPConfirmRequest,
    TOTPSetupRequest,
    TOTPSetupResponse,
)
from app.services.challenge import ChallengeService
from app.services.mfa import MFAService
from app.services.session import SessionService

router = APIRouter(prefix="/security", tags=["Security"])


@router.post("/mfa/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    payload: TOTPSetupRequest,
    request: Request,
    current_user=Depends(get_current_user),
    mfa_service: MFAService = Depends(get_mfa_service),
):
    return await mfa_service.setup_totp(current_user=current_user, password=payload.password, request=request)


@router.post("/mfa/totp/confirm", response_model=MFAStatusResponse)
async def confirm_totp(
    payload: TOTPConfirmRequest,
    request: Request,
    current_user=Depends(get_current_user),
    mfa_service: MFAService = Depends(get_mfa_service),
):
    return await mfa_service.confirm_totp(
        current_user=current_user,
        setup_id=payload.mfa_setup_id,
        code=payload.code,
        request=request,
    )


@router.post("/challenges", response_model=ChallengeResponse)
async def create_challenge(
    payload: ChallengeCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    challenge_service: ChallengeService = Depends(get_challenge_service),
):
    challenge = await challenge_service.create_challenge(current_user=current_user, payload=payload, request=request)
    return {
        "challenge_id": challenge.id,
        "purpose": challenge.purpose,
        "allowed_methods": challenge.allowed_methods,
        "status": challenge.status,
        "expires_at": challenge.expires_at,
    }


@router.post("/challenges/{challenge_id}/verify", response_model=ChallengeVerifyResponse)
async def verify_challenge(
    challenge_id: UUID,
    payload: ChallengeVerifyRequest,
    request: Request,
    current_user=Depends(get_current_user),
    challenge_service: ChallengeService = Depends(get_challenge_service),
):
    challenge = await challenge_service.verify_challenge(
        current_user=current_user,
        challenge_id=challenge_id,
        method=payload.method,
        code=payload.code,
        request=request,
    )
    return {
        "status": challenge.status,
        "verified_at": challenge.verified_at,
        "verified_method": challenge.verified_method,
    }


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    current_user=Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    auth_payload = getattr(request.state, "auth_payload", {})
    items = await session_service.list_sessions(
        current_user=current_user,
        current_session_id=auth_payload.get("sid"),
    )
    return {"items": items}


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    request: Request,
    current_user=Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    return await session_service.revoke_session(current_user=current_user, session_id=session_id, request=request)
