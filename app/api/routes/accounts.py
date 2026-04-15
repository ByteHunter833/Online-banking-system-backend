from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_account_service
from app.schemas.account import (
    BankAccountCreateRequest,
    BankAccountPreferencesUpdateRequest,
    BankAccountResponse,
)
from app.services.account import AccountService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: BankAccountCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
):
    return await account_service.create_account(current_user=current_user, payload=payload, request=request)


@router.get("/", response_model=list[BankAccountResponse])
async def list_accounts(
    current_user=Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
):
    return await account_service.list_accounts(current_user)


@router.get("/{account_id}", response_model=BankAccountResponse)
async def get_account(
    account_id: UUID,
    current_user=Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
):
    return await account_service.get_account(current_user, account_id)


@router.patch("/{account_id}/preferences", response_model=BankAccountResponse)
async def update_account_preferences(
    account_id: UUID,
    payload: BankAccountPreferencesUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
):
    return await account_service.update_preferences(
        current_user=current_user,
        account_id=account_id,
        payload=payload,
        request=request,
    )
