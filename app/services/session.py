from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.security import ip_fingerprint
from app.models import LoginEvent, TrustedDevice, User, UserSession
from app.repositories.login_event import LoginEventRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.session import SessionRepository
from app.repositories.trusted_device import TrustedDeviceRepository
from app.services.audit import AuditService


class SessionService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.trusted_devices = TrustedDeviceRepository(db)
        self.login_events = LoginEventRepository(db)
        self.audit_service = audit_service

    async def create_session(
        self,
        *,
        user: User,
        family_id: str,
        device_id: str | None,
        device_name: str | None,
        request: Request,
    ) -> tuple[UserSession, bool, str | None]:
        session = UserSession(
            user_id=user.id,
            family_id=family_id,
            device_id=device_id,
            device_name=device_name,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            status="active",
            last_seen_at=datetime.now(timezone.utc),
        )
        self.sessions.add(session)

        suspicious = False
        reason = None
        if device_id:
            trusted = await self.trusted_devices.get_for_user(user.id, device_id)
            current_ip_hash = ip_fingerprint(request.client.host if request.client else None)
            if trusted is None:
                suspicious = True
                reason = "new_device"
                trusted = TrustedDevice(
                    user_id=user.id,
                    device_id=device_id,
                    device_name=device_name,
                    last_ip_hash=current_ip_hash,
                    last_seen_at=datetime.now(timezone.utc),
                    trusted_at=datetime.now(timezone.utc),
                )
                self.trusted_devices.add(trusted)
            else:
                if trusted.last_ip_hash and trusted.last_ip_hash != current_ip_hash:
                    suspicious = True
                    reason = "new_ip"
                trusted.device_name = device_name or trusted.device_name
                trusted.last_ip_hash = current_ip_hash
                trusted.last_seen_at = datetime.now(timezone.utc)

        self.login_events.add(
            LoginEvent(
                user_id=user.id,
                email_attempted=user.email,
                device_id=device_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=True,
                suspicious=suspicious,
                reason=reason,
            )
        )
        await self.db.flush()
        return session, suspicious, reason

    async def list_sessions(self, *, current_user: User, current_session_id: str | None) -> list[dict]:
        sessions = await self.sessions.list_for_user(current_user.id)
        return [
            {
                "id": session.id,
                "family_id": session.family_id,
                "device_id": session.device_id,
                "device_name": session.device_name,
                "ip_address": session.ip_address,
                "last_seen_at": session.last_seen_at,
                "status": session.status,
                "current": str(session.id) == str(current_session_id),
            }
            for session in sessions
        ]

    async def revoke_session(
        self,
        *,
        current_user: User,
        session_id: UUID,
        request: Request,
    ) -> dict:
        session = await self.sessions.get_by_id_for_user(session_id, current_user.id)
        if session is None:
            raise NotFoundException("Session not found.")
        session.status = "revoked"
        session.revoked_at = datetime.now(timezone.utc)
        for token in await self.refresh_tokens.revoke_by_session(session.id):
            token.revoked_at = datetime.now(timezone.utc)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="security.session_revoked",
            resource_type="session",
            resource_id=str(session.id),
            session_id=str(session.id),
            description="User revoked a session.",
        )
        await self.db.commit()
        return {"message": "Session revoked."}

