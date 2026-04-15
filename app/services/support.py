from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models import SupportMessage, SupportTicket, User
from app.repositories.support_message import SupportMessageRepository
from app.repositories.support import SupportRepository
from app.schemas.enums import NotificationCategory, SupportAuthorRole, TicketStatus
from app.schemas.support import (
    SupportMessageCreateRequest,
    SupportTicketCreateRequest,
    SupportTicketUpdateRequest,
)
from app.services.audit import AuditService
from app.services.notification import NotificationService


class SupportService:
    def __init__(
        self,
        db: AsyncSession,
        notification_service: NotificationService,
        audit_service: AuditService,
    ) -> None:
        self.db = db
        self.repository = SupportRepository(db)
        self.messages = SupportMessageRepository(db)
        self.notification_service = notification_service
        self.audit_service = audit_service

    async def create_ticket(
        self,
        *,
        current_user: User,
        payload: SupportTicketCreateRequest,
        request: Request,
    ) -> SupportTicket:
        ticket = SupportTicket(
            user_id=current_user.id,
            subject=payload.subject,
            message=payload.message,
            priority=payload.priority.value,
        )
        self.repository.add(ticket)
        await self.db.flush()
        self.messages.add(
            SupportMessage(
                ticket_id=ticket.id,
                author_user_id=current_user.id,
                author_role=SupportAuthorRole.customer.value,
                message=payload.message,
            )
        )
        await self.notification_service.create_notification(
            user=current_user,
            title="Support ticket created",
            message=f"Ticket '{payload.subject}' has been submitted.",
            category=NotificationCategory.support,
        )
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="support.ticket_created",
            resource_type="support_ticket",
            description="Support ticket submitted.",
        )
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def list_tickets(self, current_user: User) -> list[SupportTicket]:
        return await self.repository.list_by_user(current_user.id)

    async def get_ticket(self, current_user: User, ticket_id: UUID) -> SupportTicket:
        ticket = await self.repository.get_by_id_for_user(ticket_id, current_user.id)
        if ticket is None:
            raise NotFoundException("Support ticket not found.")
        return ticket

    async def update_ticket_as_admin(
        self,
        *,
        admin_user: User,
        ticket_id: UUID,
        payload: SupportTicketUpdateRequest,
        request: Request,
    ) -> SupportTicket:
        ticket = await self.repository.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException("Support ticket not found.")
        if payload.status is not None:
            ticket.status = payload.status.value
            if payload.status == TicketStatus.resolved:
                ticket.resolved_at = datetime.now(timezone.utc)
        if payload.admin_note is not None:
            ticket.admin_note = payload.admin_note

        await self.audit_service.log(
            request=request,
            actor=admin_user,
            action="support.ticket_updated",
            resource_type="support_ticket",
            resource_id=str(ticket.id),
            description="Support ticket updated by admin.",
        )
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def list_messages(self, *, current_user: User, ticket_id: UUID) -> list[SupportMessage]:
        await self._ensure_ticket_access(current_user=current_user, ticket_id=ticket_id)
        return await self.messages.list_for_ticket(ticket_id)

    async def add_message(
        self,
        *,
        current_user: User,
        ticket_id: UUID,
        payload: SupportMessageCreateRequest,
        request: Request,
    ) -> SupportMessage:
        ticket = await self._ensure_ticket_access(current_user=current_user, ticket_id=ticket_id)
        role_names = {role.name for role in current_user.roles}
        author_role = SupportAuthorRole.customer.value
        if "admin" in role_names:
            author_role = SupportAuthorRole.admin.value
        elif "support" in role_names:
            author_role = SupportAuthorRole.support.value

        message = SupportMessage(
            ticket_id=ticket.id,
            author_user_id=current_user.id,
            author_role=author_role,
            message=payload.message,
        )
        self.messages.add(message)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="support.message_added",
            resource_type="support_message",
            resource_id=str(message.id),
            description="Support message added.",
        )
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def _ensure_ticket_access(self, *, current_user: User, ticket_id: UUID) -> SupportTicket:
        role_names = {role.name for role in current_user.roles}
        if role_names.intersection({"admin", "support"}):
            ticket = await self.repository.get_by_id(ticket_id)
        else:
            ticket = await self.repository.get_by_id_for_user(ticket_id, current_user.id)
        if ticket is None:
            raise NotFoundException("Support ticket not found.")
        return ticket
