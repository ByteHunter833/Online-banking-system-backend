from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import SupportAuthorRole, TicketPriority, TicketStatus


class SupportTicketCreateRequest(BaseModel):
    subject: str = Field(min_length=4, max_length=150)
    message: str = Field(min_length=10, max_length=1000)
    priority: TicketPriority = TicketPriority.medium


class SupportTicketUpdateRequest(BaseModel):
    status: TicketStatus | None = None
    admin_note: str | None = Field(default=None, max_length=1000)


class SupportTicketResponse(BaseModel):
    id: UUID
    subject: str
    message: str
    status: TicketStatus
    priority: TicketPriority
    admin_note: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupportMessageCreateRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)


class SupportMessageResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author_user_id: UUID | None
    author_role: SupportAuthorRole
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
