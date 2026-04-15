from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    target_user_id: UUID | None
    status: str
    request_id: str | None
    session_id: str | None
    device_id: str | None
    challenge_id: str | None
    idempotency_key: str | None
    ip_address: str | None
    user_agent: str | None
    description: str | None
    extra: dict | None
    before_state: dict | None
    after_state: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
