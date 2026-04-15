from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import (
    build_totp_uri,
    decrypt_value,
    encrypt_value,
    generate_base32_secret,
    generate_recovery_codes,
    hash_token,
    verify_password,
    verify_totp_code,
)
from app.models import MFASecret, User
from app.repositories.mfa import MFARepository
from app.schemas.enums import MFASecretStatus
from app.services.audit import AuditService


class MFAService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.repository = MFARepository(db)
        self.audit_service = audit_service

    async def setup_totp(self, *, current_user: User, password: str, request: Request) -> dict:
        if not verify_password(password, current_user.hashed_password):
            raise UnauthorizedException("Password is invalid.")

        existing = await self.repository.get_active_for_user(current_user.id)
        if existing is not None:
            raise ConflictException("TOTP MFA is already enabled.")

        secret = generate_base32_secret()
        setup = MFASecret(
            user_id=current_user.id,
            encrypted_secret=encrypt_value(secret),
            primary_method="totp",
            status="pending",
        )
        self.repository.add(setup)
        await self.db.flush()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.mfa_setup_ttl_seconds)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="security.mfa_totp_setup_started",
            resource_type="mfa_secret",
            resource_id=str(setup.id),
            description="User started TOTP MFA setup.",
        )
        await self.db.commit()
        return {
            "mfa_setup_id": setup.id,
            "secret_base32": secret,
            "otpauth_url": build_totp_uri(secret, current_user.email),
            "expires_at": expires_at,
        }

    async def confirm_totp(self, *, current_user: User, setup_id, code: str, request: Request) -> dict:
        setup = await self.repository.get_pending(current_user.id, setup_id)
        if setup is None:
            raise ForbiddenException("MFA setup request not found.")
        if setup.created_at + timedelta(seconds=settings.mfa_setup_ttl_seconds) <= datetime.now(timezone.utc):
            setup.status = "disabled"
            await self.db.commit()
            raise ForbiddenException("MFA setup request expired. Start setup again.")

        secret = decrypt_value(setup.encrypted_secret)
        if not verify_totp_code(secret, code):
            raise UnauthorizedException("Invalid TOTP code.")

        recovery_codes = generate_recovery_codes()
        setup.recovery_code_hashes = [hash_token(item) for item in recovery_codes]
        setup.status = "active"
        setup.confirmed_at = datetime.now(timezone.utc)
        current_user.mfa_enabled = True

        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="security.mfa_totp_enabled",
            resource_type="mfa_secret",
            resource_id=str(setup.id),
            description="User enabled TOTP MFA.",
        )
        await self.db.commit()
        return {
            "mfa_enabled": True,
            "status": MFASecretStatus.active,
            "recovery_codes": recovery_codes,
        }

    async def verify_for_user(self, user: User, *, totp_code: str | None, recovery_code: str | None) -> None:
        active = await self.repository.get_active_for_user(user.id)
        if active is None:
            raise ForbiddenException("MFA is not configured.")
        if totp_code:
            secret = decrypt_value(active.encrypted_secret)
            if not verify_totp_code(secret, totp_code):
                raise UnauthorizedException("Invalid TOTP code.")
            active.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()
            return
        if recovery_code:
            hashed = hash_token(recovery_code.upper())
            recovery_hashes = active.recovery_code_hashes or []
            if hashed not in recovery_hashes:
                raise UnauthorizedException("Invalid recovery code.")
            active.recovery_code_hashes = [item for item in recovery_hashes if item != hashed]
            active.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()
            return
        raise ForbiddenException("A TOTP or recovery code is required.")
