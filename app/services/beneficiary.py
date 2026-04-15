from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models import Beneficiary, User
from app.repositories.account import AccountRepository
from app.repositories.beneficiary import BeneficiaryRepository
from app.schemas.enums import ChallengePurpose
from app.schemas.beneficiary import BeneficiaryCreateRequest
from app.services.audit import AuditService
from app.services.challenge import ChallengeService


class BeneficiaryService:
    def __init__(
        self,
        db: AsyncSession,
        challenge_service: ChallengeService,
        audit_service: AuditService,
    ) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.repository = BeneficiaryRepository(db)
        self.challenge_service = challenge_service
        self.audit_service = audit_service

    async def create(
        self,
        *,
        current_user: User,
        payload: BeneficiaryCreateRequest,
        request: Request,
    ) -> Beneficiary:
        recipient = await self.accounts.get_by_account_number(payload.account_number)
        if recipient is None:
            raise NotFoundException("Recipient account not found.")
        if recipient.user_id == current_user.id:
            raise ConflictException("You cannot save your own account as a beneficiary.")

        challenge = None
        if await self.repository.count_for_user(current_user.id) == 0:
            if payload.challenge_id is None:
                raise ConflictException("A verified challenge is required for the first beneficiary.")
            challenge = await self.challenge_service.require_verified(
                current_user=current_user,
                challenge_id=payload.challenge_id,
                purpose=ChallengePurpose.beneficiary_create.value,
                context={"account_number": payload.account_number},
                consume=True,
            )

        beneficiary = Beneficiary(
            user_id=current_user.id,
            account_id=recipient.id,
            account_number=payload.account_number,
            nickname=payload.nickname,
            status="active",
            created_by_challenge_id=challenge.id if challenge else None,
            last_used_at=datetime.now(timezone.utc),
        )
        self.repository.add(beneficiary)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="beneficiaries.created",
            resource_type="beneficiary",
            description=f"Saved beneficiary {payload.nickname}.",
            challenge_id=str(challenge.id) if challenge else None,
        )
        await self.db.commit()
        await self.db.refresh(beneficiary)
        return beneficiary

    async def list_for_user(self, current_user: User) -> list[Beneficiary]:
        return await self.repository.list_for_user(current_user.id)

