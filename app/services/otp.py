from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import generate_numeric_otp, hash_token
from app.models import OTPCode, User
from app.repositories.otp import OTPRepository
from app.schemas.enums import NotificationChannel, OTPPurpose
from app.services.communication import CommunicationService


class OTPService:
    def __init__(self, db: AsyncSession, redis_client, communication: CommunicationService) -> None:
        self.db = db
        self.redis = redis_client
        self.repository = OTPRepository(db)
        self.communication = communication

    @staticmethod
    def _redis_key(user_id, purpose: OTPPurpose) -> str:
        return f"otp:{purpose.value}:{user_id}"

    @staticmethod
    def _message_for(purpose: OTPPurpose, code: str) -> str:
        labels = {
            OTPPurpose.email_verification: "email verification",
            OTPPurpose.password_reset: "password reset",
            OTPPurpose.transfer_sensitive: "transfer confirmation",
            OTPPurpose.change_password: "password change",
            OTPPurpose.account_deactivation: "account deactivation",
            OTPPurpose.auth_challenge: "authentication challenge",
        }
        return f"Your {labels[purpose]} code is {code}. It expires in 5 minutes."

    async def issue_otp(
        self,
        *,
        user: User,
        purpose: OTPPurpose,
        delivery_channel: NotificationChannel,
        extra_data: dict | None = None,
    ) -> tuple[str, int]:
        if delivery_channel == NotificationChannel.sms and not user.phone:
            raise ConflictException("A phone number is required to deliver SMS OTP codes.")

        existing = await self.repository.get_active_code(user.id, purpose.value)
        if existing and existing.consumed_at is None:
            existing.consumed_at = datetime.now(timezone.utc)

        ttl_seconds = (
            settings.password_reset_otp_ttl_seconds
            if purpose == OTPPurpose.password_reset
            else settings.otp_ttl_seconds
        )
        code = generate_numeric_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        otp_code = OTPCode(
            user_id=user.id,
            purpose=purpose.value,
            delivery_channel=delivery_channel.value,
            target=user.phone if delivery_channel == NotificationChannel.sms else user.email,
            code_hash=hash_token(code),
            expires_at=expires_at,
            extra_data=extra_data,
        )
        self.repository.add(otp_code)
        await self.db.flush()

        key = self._redis_key(user.id, purpose)
        payload = {"otp_id": str(otp_code.id), "code_hash": hash_token(code)}
        await self.redis.setex(key, ttl_seconds, json.dumps(payload))

        message = self._message_for(purpose, code)
        if delivery_channel == NotificationChannel.sms:
            await self.communication.send_sms(user.phone or "", message)
        else:
            await self.communication.send_email(user.email, "One-time password", message)

        return code, ttl_seconds

    async def verify_user_otp(
        self,
        *,
        user: User,
        purpose: OTPPurpose,
        otp_code: str,
        consume: bool = True,
        extra_match: dict | None = None,
    ) -> None:
        active_code = await self.repository.get_active_code(user.id, purpose.value, extra_match=extra_match)
        if active_code is None:
            raise UnauthorizedException("OTP code is missing or has expired.")

        now = datetime.now(timezone.utc)
        if active_code.expires_at <= now:
            active_code.consumed_at = now
            await self.redis.delete(self._redis_key(user.id, purpose))
            raise UnauthorizedException("OTP code has expired.")

        key = self._redis_key(user.id, purpose)
        redis_payload = await self.redis.get(key)
        expected_hash = active_code.code_hash
        if redis_payload:
            expected_hash = json.loads(redis_payload)["code_hash"]

        active_code.attempts += 1
        if hash_token(otp_code) != expected_hash:
            if active_code.attempts >= 3:
                active_code.consumed_at = now
                await self.redis.delete(key)
            await self.db.flush()
            raise UnauthorizedException("OTP code is invalid.")

        if consume:
            active_code.consumed_at = now
            await self.redis.delete(key)
        await self.db.flush()
