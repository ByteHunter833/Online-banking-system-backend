from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models import Card, User
from app.repositories.account import AccountRepository
from app.repositories.card import CardRepository
from app.schemas.card import CardActionRequest, CardControlsUpdateRequest, CardCreateRequest, CardLimitUpdateRequest
from app.services.audit import AuditService
from app.utils.account_numbers import generate_masked_pan


class CardService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.cards = CardRepository(db)
        self.accounts = AccountRepository(db)
        self.audit_service = audit_service

    async def list_cards(self, current_user: User) -> list[Card]:
        return await self.cards.list_by_user(current_user.id)

    async def create_card(
        self,
        *,
        current_user: User,
        payload: CardCreateRequest,
        request: Request,
    ) -> Card:
        account = await self.accounts.get_by_id_for_user(payload.account_id, current_user.id)
        if account is None:
            raise NotFoundException("Linked bank account not found.")
        if account.status != "active":
            raise ConflictException("Cards can only be created for active accounts.")

        masked_pan, last4 = generate_masked_pan()
        card = Card(
            user_id=current_user.id,
            account_id=account.id,
            masked_pan=masked_pan,
            last4=last4,
            brand="VISA",
            card_type=payload.card_type.value,
            status="active",
            spending_limit=payload.spending_limit,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365 * 3),
            provider_reference=f"provider-{last4}",
        )
        self.cards.add(card)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="cards.created",
            resource_type="card",
            description=f"{payload.card_type.value.title()} card created.",
        )
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def freeze_card(
        self,
        *,
        current_user: User,
        card_id: UUID,
        payload: CardActionRequest,
        request: Request,
    ) -> Card:
        card = await self.cards.get_by_id_for_user(card_id, current_user.id)
        if card is None:
            raise NotFoundException("Card not found.")
        card.status = "frozen"
        card.frozen_reason = payload.reason
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="cards.frozen",
            resource_type="card",
            resource_id=str(card.id),
            description=payload.reason or "Card frozen by user.",
        )
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def unfreeze_card(self, *, current_user: User, card_id: UUID, request: Request) -> Card:
        card = await self.cards.get_by_id_for_user(card_id, current_user.id)
        if card is None:
            raise NotFoundException("Card not found.")
        card.status = "active"
        card.frozen_reason = None
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="cards.unfrozen",
            resource_type="card",
            resource_id=str(card.id),
            description="Card unfrozen by user.",
        )
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def set_spending_limit(
        self,
        *,
        current_user: User,
        card_id: UUID,
        payload: CardLimitUpdateRequest,
        request: Request,
    ) -> Card:
        card = await self.cards.get_by_id_for_user(card_id, current_user.id)
        if card is None:
            raise NotFoundException("Card not found.")
        card.spending_limit = payload.spending_limit
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="cards.limit_updated",
            resource_type="card",
            resource_id=str(card.id),
            description=f"Spending limit updated to {payload.spending_limit}.",
        )
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def update_controls(
        self,
        *,
        current_user: User,
        card_id: UUID,
        payload: CardControlsUpdateRequest,
        request: Request,
    ) -> Card:
        card = await self.cards.get_by_id_for_user(card_id, current_user.id)
        if card is None:
            raise NotFoundException("Card not found.")
        update_data = payload.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(card, key, value)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="cards.controls_updated",
            resource_type="card",
            resource_id=str(card.id),
            description="Card controls updated.",
            after_state=update_data,
        )
        await self.db.commit()
        await self.db.refresh(card)
        return card
