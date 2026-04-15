from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_support_service
from app.schemas.support import (
    SupportMessageCreateRequest,
    SupportMessageResponse,
    SupportTicketCreateRequest,
    SupportTicketResponse,
)
from app.services.support import SupportService

router = APIRouter(prefix="/support", tags=["Support"])


@router.post("/", response_model=SupportTicketResponse)
async def create_ticket(
    payload: SupportTicketCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    support_service: SupportService = Depends(get_support_service),
):
    return await support_service.create_ticket(current_user=current_user, payload=payload, request=request)


@router.get("/", response_model=list[SupportTicketResponse])
async def list_tickets(
    current_user=Depends(get_current_user),
    support_service: SupportService = Depends(get_support_service),
):
    return await support_service.list_tickets(current_user)


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
async def get_ticket(
    ticket_id: UUID,
    current_user=Depends(get_current_user),
    support_service: SupportService = Depends(get_support_service),
):
    return await support_service.get_ticket(current_user, ticket_id)


@router.get("/{ticket_id}/messages", response_model=list[SupportMessageResponse])
async def list_ticket_messages(
    ticket_id: UUID,
    current_user=Depends(get_current_user),
    support_service: SupportService = Depends(get_support_service),
):
    return await support_service.list_messages(current_user=current_user, ticket_id=ticket_id)


@router.post("/{ticket_id}/messages", response_model=SupportMessageResponse)
async def create_ticket_message(
    ticket_id: UUID,
    payload: SupportMessageCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    support_service: SupportService = Depends(get_support_service),
):
    return await support_service.add_message(
        current_user=current_user,
        ticket_id=ticket_id,
        payload=payload,
        request=request,
    )
