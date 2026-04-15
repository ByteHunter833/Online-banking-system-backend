from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_jti,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import LoginEvent, RefreshToken, User
from app.repositories.login_event import LoginEventRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    OTPRequest,
    OTPVerifyRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.enums import NotificationCategory, NotificationChannel, OTPPurpose
from app.services.audit import AuditService
from app.services.mfa import MFAService
from app.services.notification import NotificationService
from app.services.otp import OTPService
from app.services.session import SessionService
from app.services.webhook import WebhookService


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        otp_service: OTPService,
        notification_service: NotificationService,
        audit_service: AuditService,
        webhook_service: WebhookService,
        mfa_service: MFAService,
        session_service: SessionService,
    ) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.login_events = LoginEventRepository(db)
        self.otp_service = otp_service
        self.notification_service = notification_service
        self.audit_service = audit_service
        self.webhook_service = webhook_service
        self.mfa_service = mfa_service
        self.session_service = session_service

    @staticmethod
    def _role_names(user: User) -> list[str]:
        return sorted(role.name for role in user.roles)

    def _serialize_user(self, user: User) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "mfa_enabled": user.mfa_enabled,
            "biometric_enabled": user.biometric_enabled,
            "kyc_status": user.kyc_status,
            "roles": self._role_names(user),
        }

    async def _record_unknown_login(self, payload: LoginRequest, request: Request) -> None:
        self.login_events.add(
            LoginEvent(
                user_id=None,
                email_attempted=payload.email.lower(),
                device_id=payload.device_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=False,
                suspicious=False,
                reason="unknown_email",
            )
        )
        await self.audit_service.log(
            request=request,
            actor=None,
            action="auth.login_failed",
            resource_type="user",
            status="failure",
            description="Unknown email address.",
        )
        await self.db.commit()

    async def _issue_tokens(
        self,
        *,
        user: User,
        request: Request,
        device_id: str | None,
        device_name: str | None,
        family_id: str | None = None,
        session_id: str | None = None,
    ) -> tuple[str, str, str, str | None]:
        roles = self._role_names(user)
        family = family_id or generate_jti()
        refresh_jti = generate_jti()

        session = None
        suspicious = False
        suspicious_reason = None
        if session_id is None:
            session, suspicious, suspicious_reason = await self.session_service.create_session(
                user=user,
                family_id=family,
                device_id=device_id,
                device_name=device_name,
                request=request,
            )
            session_identifier = str(session.id)
        else:
            session_identifier = session_id

        access_token = create_access_token(
            str(user.id),
            roles,
            device_id=device_id,
            session_id=session_identifier,
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            device_id=device_id,
            jti=refresh_jti,
            family_id=family,
            session_id=session_identifier,
        )

        refresh_record = RefreshToken(
            user_id=user.id,
            jti=refresh_jti,
            family_id=family,
            session_id=UUID(session_identifier),
            token_hash=hash_token(refresh_token),
            device_id=device_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
        self.refresh_tokens.add(refresh_record)
        await self.db.flush()

        return access_token, refresh_token, session_identifier, suspicious_reason if suspicious else None

    async def _revoke_refresh_tokens(self, user: User) -> None:
        now = datetime.now(timezone.utc)
        for token in await self.refresh_tokens.revoke_all_for_user(user.id):
            token.revoked_at = now

    def _token_response(self, user: User, access_token: str, refresh_token: str) -> dict:
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_token_expires_in": settings.access_token_expire_minutes * 60,
            "refresh_token_expires_in": settings.refresh_token_expire_days * 24 * 60 * 60,
            "user": self._serialize_user(user),
        }

    async def register(self, payload: RegisterRequest, request: Request) -> dict:
        existing_user = await self.users.get_by_email(payload.email)
        if existing_user is not None:
            raise ConflictException("A user with this email already exists.")

        roles = await self.roles.ensure_defaults()
        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            phone=payload.phone,
            hashed_password=hash_password(payload.password),
            password_changed_at=datetime.now(timezone.utc),
            is_email_verified=False,
            is_active=True,
            kyc_status="pending",
        )
        user.roles.append(roles["customer"])
        self.users.add(user)
        await self.db.flush()

        debug_otp, _ = await self.otp_service.issue_otp(
            user=user,
            purpose=OTPPurpose.email_verification,
            delivery_channel=NotificationChannel.email,
        )
        await self.notification_service.create_notification(
            user=user,
            title="Welcome to Example Bank",
            message="Your profile has been created. Verify your email to activate online access.",
            category=NotificationCategory.system,
        )
        await self.audit_service.log(
            request=request,
            actor=user,
            action="auth.register",
            resource_type="user",
            resource_id=str(user.id),
            description="Customer registered successfully.",
        )
        await self.db.commit()

        return {
            "message": "Registration successful. Verify your email with the OTP code that was sent.",
            "email_verification_required": True,
            "debug_otp": debug_otp if settings.debug else None,
        }

    async def verify_email(self, payload: VerifyEmailRequest, request: Request) -> dict:
        user = await self.users.get_by_email(payload.email)
        if user is None:
            raise UnauthorizedException("Invalid verification request.")

        await self.otp_service.verify_user_otp(
            user=user,
            purpose=OTPPurpose.email_verification,
            otp_code=payload.otp_code,
        )
        user.is_email_verified = True
        await self.audit_service.log(
            request=request,
            actor=user,
            action="auth.verify_email",
            resource_type="user",
            resource_id=str(user.id),
            description="Email verification completed.",
        )
        await self.db.commit()
        return {"message": "Email verified successfully."}

    async def _record_failed_login(self, *, user: User, request: Request, reason: str, payload: LoginRequest) -> None:
        now = datetime.now(timezone.utc)
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.account_lock_minutes)

        self.login_events.add(
            LoginEvent(
                user_id=user.id,
                email_attempted=user.email,
                device_id=payload.device_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=False,
                suspicious=False,
                reason=reason,
            )
        )
        await self.audit_service.log(
            request=request,
            actor=user,
            action="auth.login_failed",
            resource_type="user",
            resource_id=str(user.id),
            status="failure",
            description=reason,
            extra={"failed_login_attempts": user.failed_login_attempts},
        )
        await self.db.commit()

    async def login(self, payload: LoginRequest, request: Request, *, admin_only: bool = False) -> dict:
        user = await self.users.get_by_email(payload.email)
        if user is None:
            await self._record_unknown_login(payload, request)
            raise UnauthorizedException("Invalid credentials.")

        now = datetime.now(timezone.utc)
        if user.locked_until and user.locked_until > now:
            raise ForbiddenException("Account is temporarily locked due to repeated failed logins.")
        if user.deactivated_at or not user.is_active:
            raise ForbiddenException("Account is deactivated.")
        if not verify_password(payload.password, user.hashed_password):
            await self._record_failed_login(user=user, request=request, reason="Invalid password.", payload=payload)
            raise UnauthorizedException("Invalid credentials.")
        if not user.is_email_verified:
            raise ForbiddenException("Verify your email before signing in.")

        role_names = set(self._role_names(user))
        if admin_only and "admin" not in role_names:
            await self.audit_service.log(
                request=request,
                actor=user,
                action="auth.admin_login_denied",
                resource_type="user",
                resource_id=str(user.id),
                status="failure",
                description="User does not have the admin role.",
            )
            await self.db.commit()
            raise ForbiddenException("Admin access is required.")

        if user.mfa_enabled:
            await self.mfa_service.verify_for_user(
                user,
                totp_code=payload.totp_code,
                recovery_code=payload.recovery_code,
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        device_id = payload.device_id or payload.device_name
        access_token, refresh_token, session_id, suspicious_reason = await self._issue_tokens(
            user=user,
            request=request,
            device_id=device_id,
            device_name=payload.device_name,
        )

        message = "A new login to your banking profile was recorded."
        if suspicious_reason:
            message = f"A suspicious login was detected: {suspicious_reason}."
        await self.notification_service.create_notification(
            user=user,
            title="Successful sign-in",
            message=message,
            category=NotificationCategory.security_alert,
            send_email=True,
        )
        await self.audit_service.log(
            request=request,
            actor=user,
            action="auth.login",
            resource_type="session",
            resource_id=session_id,
            session_id=session_id,
            device_id=device_id,
            description="User login completed.",
            extra={"device_id": payload.device_id, "device_name": payload.device_name, "suspicious_reason": suspicious_reason},
        )
        await self.db.commit()
        await self.webhook_service.publish_event(
            "auth.login",
            {"user_id": str(user.id), "device_id": payload.device_id, "admin_only": admin_only},
        )
        return self._token_response(user, access_token, refresh_token)

    async def refresh(self, payload: RefreshTokenRequest, request: Request) -> dict:
        try:
            token_payload = decode_token(payload.refresh_token)
        except ValueError as exc:
            raise UnauthorizedException(str(exc)) from exc

        if token_payload.get("token_type") != "refresh":
            raise UnauthorizedException("A refresh token is required.")

        jti = token_payload.get("jti")
        family_id = token_payload.get("family_id")
        subject = token_payload.get("sub")
        device_id = token_payload.get("device_id")
        session_id = token_payload.get("sid")
        if not all([jti, family_id, subject]):
            raise UnauthorizedException("Refresh token payload is malformed.")

        refresh_record = await self.refresh_tokens.get_by_jti(jti)
        if refresh_record is None or refresh_record.token_hash != hash_token(payload.refresh_token):
            raise UnauthorizedException("Refresh token is invalid.")

        if refresh_record.revoked_at is not None:
            now = datetime.now(timezone.utc)
            for token in await self.refresh_tokens.revoke_family(family_id):
                token.revoked_at = now
            await self.db.commit()
            raise UnauthorizedException("Refresh token reuse detected. Login again.")

        if refresh_record.expires_at <= datetime.now(timezone.utc):
            refresh_record.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise UnauthorizedException("Refresh token has expired.")

        user = await self.users.get_by_id(UUID(subject))
        if user is None or user.deactivated_at or not user.is_active:
            raise UnauthorizedException("User session is no longer valid.")

        refresh_record.revoked_at = datetime.now(timezone.utc)
        refresh_record.replaced_by_jti = generate_jti()
        refresh_record.last_used_at = datetime.now(timezone.utc)
        if refresh_record.session is not None:
            refresh_record.session.last_seen_at = datetime.now(timezone.utc)
            refresh_record.session.ip_address = request.client.host if request.client else None
            refresh_record.session.user_agent = request.headers.get("user-agent")

        access_token = create_access_token(
            str(user.id),
            self._role_names(user),
            device_id=device_id,
            session_id=session_id,
        )
        new_refresh_token = create_refresh_token(
            subject=str(user.id),
            device_id=device_id,
            jti=refresh_record.replaced_by_jti,
            family_id=family_id,
            session_id=session_id,
        )
        self.refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                jti=refresh_record.replaced_by_jti,
                family_id=family_id,
                session_id=refresh_record.session_id,
                token_hash=hash_token(new_refresh_token),
                device_id=device_id,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        await self.audit_service.log(
            request=request,
            actor=user,
            action="auth.refresh",
            resource_type="session",
            resource_id=str(session_id),
            session_id=str(session_id) if session_id else None,
            description="Refresh token rotated successfully.",
        )
        await self.db.commit()
        return self._token_response(user, access_token, new_refresh_token)

    async def logout(self, current_user: User, payload: LogoutRequest, request: Request) -> dict:
        try:
            token_payload = decode_token(payload.refresh_token)
        except ValueError as exc:
            raise UnauthorizedException(str(exc)) from exc

        if token_payload.get("sub") != str(current_user.id):
            raise ForbiddenException("Refresh token does not belong to the current user.")

        session_id = token_payload.get("sid")
        if session_id:
            for token in await self.refresh_tokens.revoke_by_session(UUID(session_id)):
                token.revoked_at = datetime.now(timezone.utc)
        else:
            jti = token_payload.get("jti")
            refresh_record = await self.refresh_tokens.get_by_jti(jti)
            if refresh_record is not None:
                refresh_record.revoked_at = datetime.now(timezone.utc)

        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="auth.logout",
            resource_type="session",
            resource_id=str(session_id) if session_id else token_payload.get("jti"),
            session_id=str(session_id) if session_id else None,
            description="User logged out successfully.",
        )
        await self.db.commit()
        return {"message": "Logged out successfully."}

    async def forgot_password(self, payload: ForgotPasswordRequest, request: Request) -> dict:
        user = await self.users.get_by_email(payload.email)
        debug_otp = None

        if user is not None:
            debug_otp, ttl_seconds = await self.otp_service.issue_otp(
                user=user,
                purpose=OTPPurpose.password_reset,
                delivery_channel=NotificationChannel.email,
            )
            await self.audit_service.log(
                request=request,
                actor=user,
                action="auth.password_reset_requested",
                resource_type="user",
                resource_id=str(user.id),
                description="Password reset OTP issued.",
            )
            await self.db.commit()
        else:
            ttl_seconds = settings.password_reset_otp_ttl_seconds

        return {
            "message": "If the email exists, a password reset code has been sent.",
            "purpose": OTPPurpose.password_reset,
            "expires_in_seconds": ttl_seconds,
            "delivery_channel": NotificationChannel.email,
            "debug_otp": debug_otp if settings.debug else None,
        }

    async def reset_password(self, payload: ResetPasswordRequest, request: Request) -> dict:
        user = await self.users.get_by_email(payload.email)
        if user is None:
            raise UnauthorizedException("Invalid password reset request.")

        await self.otp_service.verify_user_otp(
            user=user,
            purpose=OTPPurpose.password_reset,
            otp_code=payload.otp_code,
        )
        user.hashed_password = hash_password(payload.new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        await self._revoke_refresh_tokens(user)

        await self.notification_service.create_notification(
            user=user,
            title="Password changed",
            message="Your banking password was changed. If this was not you, contact support immediately.",
            category=NotificationCategory.security_alert,
            send_email=True,
        )
        await self.audit_service.log(
            request=request,
            actor=user,
            action="auth.password_reset_completed",
            resource_type="user",
            resource_id=str(user.id),
            description="Password reset completed.",
        )
        await self.db.commit()
        return {"message": "Password has been reset successfully."}

    async def request_authenticated_otp(
        self,
        *,
        current_user: User,
        payload: OTPRequest,
        request: Request,
    ) -> dict:
        if payload.purpose in {OTPPurpose.email_verification, OTPPurpose.password_reset, OTPPurpose.auth_challenge}:
            raise ForbiddenException("Use the dedicated flow for this OTP purpose.")

        debug_otp, ttl_seconds = await self.otp_service.issue_otp(
            user=current_user,
            purpose=payload.purpose,
            delivery_channel=payload.delivery_channel,
        )
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="auth.otp_requested",
            resource_type="otp",
            description=f"OTP requested for {payload.purpose.value}.",
        )
        await self.db.commit()
        return {
            "message": "OTP code sent.",
            "purpose": payload.purpose,
            "expires_in_seconds": ttl_seconds,
            "delivery_channel": payload.delivery_channel,
            "debug_otp": debug_otp if settings.debug else None,
        }

    async def verify_authenticated_otp(
        self,
        *,
        current_user: User,
        payload: OTPVerifyRequest,
        request: Request,
    ) -> dict:
        if payload.purpose in {OTPPurpose.email_verification, OTPPurpose.password_reset, OTPPurpose.auth_challenge}:
            raise ForbiddenException("Use the dedicated flow for this OTP purpose.")

        await self.otp_service.verify_user_otp(
            user=current_user,
            purpose=payload.purpose,
            otp_code=payload.otp_code,
        )
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="auth.otp_verified",
            resource_type="otp",
            description=f"OTP verified for {payload.purpose.value}.",
        )
        await self.db.commit()
        return {"message": "OTP verified successfully."}
