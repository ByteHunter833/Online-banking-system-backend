from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.core.security import hash_password, validate_password_strength
from app.db.session import AsyncSessionLocal
from app.models import User
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository


async def bootstrap_roles_and_admin() -> None:
    async with AsyncSessionLocal() as session:
        role_repository = RoleRepository(session)
        user_repository = UserRepository(session)
        roles = await role_repository.ensure_defaults()

        if settings.initial_admin_email and settings.initial_admin_password:
            validate_password_strength(settings.initial_admin_password)

            admin_user = await user_repository.get_by_email(settings.initial_admin_email)
            if admin_user is None:
                admin_user = User(
                    email=settings.initial_admin_email.lower(),
                    full_name="Platform Administrator",
                    hashed_password=hash_password(settings.initial_admin_password),
                    is_email_verified=True,
                    is_active=True,
                    mfa_enabled=False,
                    biometric_enabled=False,
                    kyc_status="verified",
                    password_changed_at=datetime.now(timezone.utc),
                )
                admin_user.roles.append(roles["admin"])
                user_repository.add(admin_user)
            elif roles["admin"] not in admin_user.roles:
                admin_user.roles.append(roles["admin"])

        await session.commit()
