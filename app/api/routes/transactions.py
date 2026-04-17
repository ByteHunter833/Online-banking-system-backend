from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.dependencies.auth import get_current_user, rate_limit
from app.api.dependencies.services import get_transaction_service
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    TransactionResponse,
    TransferRequest,
    TransferVerificationRequest,
    TransferVerificationResponse,
)
from app.services.transaction import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "/verify-transfer",
    response_model=TransferVerificationResponse,
    dependencies=[
        Depends(rate_limit("transactions-verify-transfer", limit=3, window_seconds=600, key_strategy="user"))
    ],
)
async def request_transfer_verification(
    payload: TransferVerificationRequest,
    request: Request,
    current_user=Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    return await transaction_service.request_transfer_verification(
        current_user=current_user,
        payload=payload,
        request=request,
    )


@router.post(
    "/transfer",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("transactions-transfer", limit=10, window_seconds=300, key_strategy="user"))],
)
async def transfer(
    payload: TransferRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user=Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    return await transaction_service.transfer(
        current_user=current_user,
        payload=payload,
        request=request,
        idempotency_key_header=idempotency_key,
    )


@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def paginated_transactions(
    account_id: UUID | None = None,
    status: str | None = None,
    direction: str | None = Query(default=None, pattern="^(debit|credit)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    items, total = await transaction_service.paginate_history(
        current_user=current_user,
        account_id=account_id,
        status=status,
        direction=direction,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "meta": {"page": page, "page_size": page_size, "total": total}}


@router.get("/history", response_model=list[TransactionResponse])
async def history(
    current_user=Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    return await transaction_service.list_history(current_user)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def transaction_detail(
    transaction_id: UUID,
    current_user=Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    return await transaction_service.get_transaction(current_user, transaction_id)
