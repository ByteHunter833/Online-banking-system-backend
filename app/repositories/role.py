from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role
from app.schemas.enums import RoleName


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalars().first()

    async def ensure_defaults(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for role_name in RoleName:
            role = await self.get_by_name(role_name.value)
            if role is None:
                role = Role(name=role_name.value, description=f"System role: {role_name.value}")
                self.db.add(role)
                await self.db.flush()
            roles[role_name.value] = role
        return roles
