from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models import RecurringTransfer, User
from app.repositories.account import AccountRepository
from app.repositories.beneficiary import BeneficiaryRepository
from app.repositories.recurring_transfer import RecurringTransferRepository
from app.schemas.enums import ChallengePurpose
from app.schemas.recurring_transfer import RecurringTransferCreateRequest
from app.services.audit import AuditService
from app.services.challenge import ChallengeService


class RecurringTransferService:
    def __init__(
        self,
        db: AsyncSession,
        challenge_service: ChallengeService,
        audit_service: AuditService,
    ) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)
        self.repository = RecurringTransferRepository(db)
        self.challenge_service = challenge_service
        self.audit_service = audit_service

    async def create(
        self,
        *,
        current_user: User,
        payload: RecurringTransferCreateRequest,
        request: Request,
    ) -> RecurringTransfer:
        account = await self.accounts.get_by_id_for_user(payload.from_account_id, current_user.id)
        beneficiary = await self.beneficiaries.get_for_user(payload.beneficiary_id, current_user.id)
        if account is None:
            raise NotFoundException("Source account not found.")
        if beneficiary is None:
            raise NotFoundException("Beneficiary not found.")

        challenge = await self.challenge_service.require_verified(
            current_user=current_user,
            challenge_id=payload.challenge_id,
            purpose=ChallengePurpose.recurring_transfer.value,
            context={
                "from_account_id": str(payload.from_account_id),
                "beneficiary_id": str(payload.beneficiary_id),
                "amount": str(payload.amount),
            },
            consume=True,
        )

        recurring_transfer = RecurringTransfer(
            user_id=current_user.id,
            from_account_id=account.id,
            beneficiary_id=beneficiary.id,
            amount=payload.amount,
            description=payload.description,
            frequency=payload.frequency.value,
            status="active",
            start_date=payload.start_date,
            end_date=payload.end_date,
            next_run_at=datetime.combine(payload.start_date, time(hour=9), tzinfo=timezone.utc),
        )
        self.repository.add(recurring_transfer)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="recurring_transfers.created",
            resource_type="recurring_transfer",
            resource_id=str(recurring_transfer.id),
            challenge_id=str(challenge.id),
            description="Recurring transfer scheduled.",
        )
        await self.db.commit()
        await self.db.refresh(recurring_transfer)
        return recurring_transfer

