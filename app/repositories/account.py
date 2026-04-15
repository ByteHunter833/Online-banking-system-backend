from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BankAccount


class AccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_user(self, user_id: UUID) -> list[BankAccount]:
        result = await self.db.execute(
            select(BankAccount)
            .where(BankAccount.user_id == user_id)
            .order_by(BankAccount.created_at.desc())
        )
        return list(result.scalars().unique().all())

    async def get_by_id(self, account_id: UUID) -> BankAccount | None:
        result = await self.db.execute(select(BankAccount).where(BankAccount.id == account_id))
        return result.scalars().unique().first()

    async def get_by_id_for_user(self, account_id: UUID, user_id: UUID) -> BankAccount | None:
        result = await self.db.execute(
            select(BankAccount).where(BankAccount.id == account_id, BankAccount.user_id == user_id)
        )
        return result.scalars().unique().first()

    async def get_by_account_number(self, account_number: str) -> BankAccount | None:
        result = await self.db.execute(
            select(BankAccount).where(BankAccount.account_number == account_number)
        )
        return result.scalars().unique().first()

    async def lock_accounts(self, account_ids: list[UUID]) -> list[BankAccount]:
        statement: Select[tuple[BankAccount]] = (
            select(BankAccount)
            .where(BankAccount.id.in_(account_ids))
            .with_for_update()
        )
        result = await self.db.execute(statement)
        return list(result.scalars().unique().all())

    async def account_number_exists(self, account_number: str) -> bool:
        return await self.get_by_account_number(account_number) is not None

    async def iban_exists(self, iban: str) -> bool:
        result = await self.db.execute(select(BankAccount).where(BankAccount.iban == iban))
        return result.scalars().first() is not None

    def add(self, account: BankAccount) -> BankAccount:
        self.db.add(account)
        return account

