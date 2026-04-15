from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_card_service
from app.schemas.card import (
    CardActionRequest,
    CardControlsUpdateRequest,
    CardCreateRequest,
    CardLimitUpdateRequest,
    CardResponse,
)
from app.services.card import CardService

router = APIRouter(prefix="/cards", tags=["Cards"])


@router.get("/", response_model=list[CardResponse])
async def list_cards(current_user=Depends(get_current_user), card_service: CardService = Depends(get_card_service)):
    return await card_service.list_cards(current_user)


@router.post("/", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    payload: CardCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    return await card_service.create_card(current_user=current_user, payload=payload, request=request)


@router.post("/{card_id}/freeze", response_model=CardResponse)
async def freeze_card(
    card_id: UUID,
    payload: CardActionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    return await card_service.freeze_card(
        current_user=current_user,
        card_id=card_id,
        payload=payload,
        request=request,
    )


@router.post("/{card_id}/unfreeze", response_model=CardResponse)
async def unfreeze_card(
    card_id: UUID,
    request: Request,
    current_user=Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    return await card_service.unfreeze_card(current_user=current_user, card_id=card_id, request=request)


@router.patch("/{card_id}/spending-limit", response_model=CardResponse)
async def update_spending_limit(
    card_id: UUID,
    payload: CardLimitUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    return await card_service.set_spending_limit(
        current_user=current_user,
        card_id=card_id,
        payload=payload,
        request=request,
    )


@router.patch("/{card_id}/controls", response_model=CardResponse)
async def update_card_controls(
    card_id: UUID,
    payload: CardControlsUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    return await card_service.update_controls(
        current_user=current_user,
        card_id=card_id,
        payload=payload,
        request=request,
    )
