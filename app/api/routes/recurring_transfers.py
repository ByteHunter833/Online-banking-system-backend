from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_recurring_transfer_service
from app.schemas.recurring_transfer import RecurringTransferCreateRequest, RecurringTransferResponse
from app.services.recurring_transfer import RecurringTransferService

router = APIRouter(prefix="/recurring-transfers", tags=["Recurring Transfers"])


@router.post("/", response_model=RecurringTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring_transfer(
    payload: RecurringTransferCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    recurring_transfer_service: RecurringTransferService = Depends(get_recurring_transfer_service),
):
    return await recurring_transfer_service.create(current_user=current_user, payload=payload, request=request)
