from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import hash_token
from app.models import AuthChallenge, User
from app.repositories.auth_challenge import AuthChallengeRepository
from app.schemas.enums import MFAMethod, NotificationChannel, OTPPurpose
from app.schemas.security import ChallengeCreateRequest
from app.services.audit import AuditService
from app.services.mfa import MFAService
from app.services.otp import OTPService


class ChallengeService:
    def __init__(
        self,
        db: AsyncSession,
        otp_service: OTPService,
        mfa_service: MFAService,
        audit_service: AuditService,
    ) -> None:
        self.db = db
        self.repository = AuthChallengeRepository(db)
        self.otp_service = otp_service
        self.mfa_service = mfa_service
        self.audit_service = audit_service

    @staticmethod
    def _context_hash(context: dict | None) -> str:
        return hash_token(json.dumps(context or {}, sort_keys=True, default=str))

    async def create_challenge(
        self,
        *,
        current_user: User,
        payload: ChallengeCreateRequest,
        request: Request,
    ) -> AuthChallenge:
        allowed_methods = [MFAMethod.totp.value]
        if current_user.email:
            allowed_methods.append(MFAMethod.email_otp.value)

        challenge = AuthChallenge(
            user_id=current_user.id,
            purpose=payload.purpose.value,
            preferred_method=payload.preferred_method.value,
            allowed_methods=allowed_methods,
            status="pending",
            context=payload.context,
            context_hash=self._context_hash(payload.context),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.challenge_ttl_seconds),
        )
        self.repository.add(challenge)
        await self.db.flush()

        if payload.preferred_method == MFAMethod.email_otp:
            await self.otp_service.issue_otp(
                user=current_user,
                purpose=OTPPurpose.auth_challenge,
                delivery_channel=NotificationChannel.email,
                extra_data={"challenge_id": str(challenge.id)},
            )

        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="security.challenge_created",
            resource_type="auth_challenge",
            resource_id=str(challenge.id),
            description=f"Challenge created for {payload.purpose.value}.",
        )
        await self.db.commit()
        return challenge

    async def verify_challenge(
        self,
        *,
        current_user: User,
        challenge_id: UUID,
        method: MFAMethod,
        code: str,
        request: Request,
    ) -> AuthChallenge:
        challenge = await self.repository.get_for_user(challenge_id, current_user.id)
        if challenge is None:
            raise ForbiddenException("Challenge was not found.")
        if challenge.expires_at <= datetime.now(timezone.utc):
            challenge.status = "expired"
            await self.db.commit()
            raise ForbiddenException("Challenge expired.")

        try:
            if method == MFAMethod.totp:
                await self.mfa_service.verify_for_user(current_user, totp_code=code, recovery_code=None)
            elif method == MFAMethod.recovery_code:
                await self.mfa_service.verify_for_user(current_user, totp_code=None, recovery_code=code)
            else:
                await self.otp_service.verify_user_otp(
                    user=current_user,
                    purpose=OTPPurpose.auth_challenge,
                    otp_code=code,
                    extra_match={"challenge_id": str(challenge.id)},
                )
        except Exception:
            challenge.failure_count += 1
            await self.db.commit()
            raise

        challenge.status = "verified"
        challenge.verified_method = method.value
        challenge.verified_at = datetime.now(timezone.utc)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="security.challenge_verified",
            resource_type="auth_challenge",
            resource_id=str(challenge.id),
            challenge_id=str(challenge.id),
            description=f"Challenge verified via {method.value}.",
        )
        await self.db.commit()
        return challenge

    async def require_verified(
        self,
        *,
        current_user: User,
        challenge_id: UUID,
        purpose: str,
        context: dict | None = None,
        consume: bool = False,
    ) -> AuthChallenge:
        challenge = await self.repository.get_verified(challenge_id, current_user.id, purpose)
        if challenge is None:
            raise ForbiddenException("A verified challenge is required.")
        if self._context_hash(context) != challenge.context_hash:
            raise ForbiddenException("Challenge context does not match this request.")
        if consume:
            challenge.status = "used"
            challenge.used_at = datetime.now(timezone.utc)
            await self.db.flush()
        return challenge
