from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.schemas.enums import NotificationCategory, OTPPurpose
from app.schemas.user import ChangePasswordRequest, DeactivateAccountRequest, UserUpdateRequest
from app.services.audit import AuditService
from app.services.notification import NotificationService
from app.services.otp import OTPService


class UserService:
    def __init__(
        self,
        db: AsyncSession,
        otp_service: OTPService,
        notification_service: NotificationService,
        audit_service: AuditService,
    ) -> None:
        self.db = db
        self.otp_service = otp_service
        self.notification_service = notification_service
        self.audit_service = audit_service
        self.refresh_tokens = RefreshTokenRepository(db)

    @staticmethod
    def _serialize(user: User) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "mfa_enabled": user.mfa_enabled,
            "biometric_enabled": user.biometric_enabled,
            "kyc_status": user.kyc_status,
            "roles": sorted(role.name for role in user.roles),
            "phone": user.phone,
            "date_of_birth": user.date_of_birth,
            "address_line1": user.address_line1,
            "address_line2": user.address_line2,
            "city": user.city,
            "state": user.state,
            "postal_code": user.postal_code,
            "country": user.country,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    async def get_profile(self, current_user: User) -> dict:
        return self._serialize(current_user)

    async def update_profile(
        self,
        *,
        current_user: User,
        payload: UserUpdateRequest,
        request: Request,
    ) -> dict:
        update_data = payload.model_dump(exclude_none=True)
        for field_name, value in update_data.items():
            setattr(current_user, field_name, value)

        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="users.profile_updated",
            resource_type="user",
            resource_id=str(current_user.id),
            description="User profile updated.",
        )
        await self.db.commit()
        await self.db.refresh(current_user)
        return self._serialize(current_user)

    async def change_password(
        self,
        *,
        current_user: User,
        payload: ChangePasswordRequest,
        request: Request,
    ) -> dict:
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise UnauthorizedException("Current password is invalid.")

        await self.otp_service.verify_user_otp(
            user=current_user,
            purpose=OTPPurpose.change_password,
            otp_code=payload.otp_code,
        )
        current_user.hashed_password = hash_password(payload.new_password)
        current_user.password_changed_at = datetime.now(timezone.utc)

        for token in await self.refresh_tokens.revoke_all_for_user(current_user.id):
            token.revoked_at = datetime.now(timezone.utc)

        await self.notification_service.create_notification(
            user=current_user,
            title="Password changed",
            message="Your password was updated and all sessions were revoked.",
            category=NotificationCategory.security_alert,
            send_email=True,
        )
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="users.password_changed",
            resource_type="user",
            resource_id=str(current_user.id),
            description="User changed password.",
        )
        await self.db.commit()
        return {"message": "Password updated successfully."}

    async def deactivate_account(
        self,
        *,
        current_user: User,
        payload: DeactivateAccountRequest,
        request: Request,
    ) -> dict:
        if not verify_password(payload.password, current_user.hashed_password):
            raise UnauthorizedException("Password is invalid.")

        await self.otp_service.verify_user_otp(
            user=current_user,
            purpose=OTPPurpose.account_deactivation,
            otp_code=payload.otp_code,
        )

        current_user.is_active = False
        current_user.deactivated_at = datetime.now(timezone.utc)
        for token in await self.refresh_tokens.revoke_all_for_user(current_user.id):
            token.revoked_at = datetime.now(timezone.utc)

        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="users.deactivated",
            resource_type="user",
            resource_id=str(current_user.id),
            description="User deactivated account.",
        )
        await self.db.commit()
        return {"message": "Account deactivated successfully."}

