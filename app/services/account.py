from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException
from app.models import BankAccount, User
from app.repositories.account import AccountRepository
from app.schemas.account import BankAccountCreateRequest, BankAccountPreferencesUpdateRequest
from app.services.audit import AuditService
from app.utils.account_numbers import generate_account_number, generate_iban


class AccountService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.repository = AccountRepository(db)
        self.audit_service = audit_service

    async def _unique_account_identifiers(self) -> tuple[str, str]:
        for _ in range(10):
            account_number = generate_account_number()
            iban = generate_iban(account_number)
            if not await self.repository.account_number_exists(account_number) and not await self.repository.iban_exists(iban):
                return account_number, iban
        raise ConflictException("Unable to allocate a unique account number. Try again.")

    async def create_account(
        self,
        *,
        current_user: User,
        payload: BankAccountCreateRequest,
        request: Request,
    ) -> BankAccount:
        currency = payload.currency.upper()
        account_number, iban = await self._unique_account_identifiers()

        existing_accounts = await self.repository.list_by_user(current_user.id)
        if payload.is_primary:
            for account in existing_accounts:
                account.is_primary = False

        account = BankAccount(
            user_id=current_user.id,
            account_number=account_number,
            iban=iban,
            nickname=payload.nickname,
            currency=currency,
            status="active",
            is_primary=payload.is_primary if existing_accounts else True,
            balance=payload.initial_deposit,
            available_balance=payload.initial_deposit,
            daily_transfer_limit=settings.default_daily_transfer_limit,
            daily_transferred_amount=0,
            last_transfer_reset_at=datetime.now(timezone.utc),
        )
        self.repository.add(account)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="accounts.created",
            resource_type="bank_account",
            description=f"Account created in {currency}.",
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def list_accounts(self, current_user: User) -> list[BankAccount]:
        return await self.repository.list_by_user(current_user.id)

    async def get_account(self, current_user: User, account_id) -> BankAccount:
        account = await self.repository.get_by_id_for_user(account_id, current_user.id)
        if account is None:
            raise NotFoundException("Bank account not found.")
        return account

    async def update_preferences(
        self,
        *,
        current_user: User,
        account_id,
        payload: BankAccountPreferencesUpdateRequest,
        request: Request,
    ) -> BankAccount:
        account = await self.repository.get_by_id_for_user(account_id, current_user.id)
        if account is None:
            raise NotFoundException("Bank account not found.")
        if payload.nickname is not None:
            account.nickname = payload.nickname
        if payload.is_primary is True:
            for existing in await self.repository.list_by_user(current_user.id):
                existing.is_primary = existing.id == account.id
        elif payload.is_primary is False and account.is_primary:
            raise ConflictException("At least one primary account must remain selected.")

        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="accounts.preferences_updated",
            resource_type="bank_account",
            resource_id=str(account.id),
            description="Account preferences updated.",
            after_state={"nickname": account.nickname, "is_primary": account.is_primary},
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account
