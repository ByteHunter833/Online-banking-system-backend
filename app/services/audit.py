from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.repositories.audit import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = AuditRepository(db)

    async def log(
        self,
        *,
        request: Request | None,
        action: str,
        resource_type: str,
        actor: User | None = None,
        resource_id: str | None = None,
        status: str = "success",
        description: str | None = None,
        extra: dict | None = None,
        target_user_id: str | None = None,
        session_id: str | None = None,
        device_id: str | None = None,
        challenge_id: str | None = None,
        idempotency_key: str | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
    ) -> AuditLog:
        auth_payload = getattr(request.state, "auth_payload", {}) if request else {}
        audit = AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            target_user_id=target_user_id,
            status=status,
            request_id=getattr(request.state, "request_id", None) if request else None,
            session_id=session_id or auth_payload.get("sid"),
            device_id=device_id or auth_payload.get("device_id"),
            challenge_id=challenge_id,
            idempotency_key=idempotency_key,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            description=description,
            extra=extra,
            before_state=before_state,
            after_state=after_state,
        )
        self.repository.add(audit)
        await self.db.flush()
        return audit
