from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction


class TransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        return transaction

    async def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        result = await self.db.execute(select(Transaction).where(Transaction.id == transaction_id))
        return result.scalars().unique().first()

    async def get_by_reference(self, reference: str) -> Transaction | None:
        result = await self.db.execute(select(Transaction).where(Transaction.reference == reference))
        return result.scalars().unique().first()

    async def list_for_user(self, user_id: UUID) -> list[Transaction]:
        result = await self.db.execute(
            select(Transaction).where(
                or_(
                    Transaction.initiated_by_user_id == user_id,
                    Transaction.from_account.has(user_id=user_id),
                    Transaction.to_account.has(user_id=user_id),
                )
            )
            .order_by(Transaction.created_at.desc())
        )
        return list(result.scalars().unique().all())

    async def list_recent_for_user(self, user_id: UUID, *, limit: int = 5) -> list[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(
                or_(
                    Transaction.initiated_by_user_id == user_id,
                    Transaction.from_account.has(user_id=user_id),
                    Transaction.to_account.has(user_id=user_id),
                )
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def user_can_access(self, transaction_id: UUID, user_id: UUID) -> Transaction | None:
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id).where(
                or_(
                    Transaction.initiated_by_user_id == user_id,
                    Transaction.from_account.has(user_id=user_id),
                    Transaction.to_account.has(user_id=user_id),
                )
            )
        )
        return result.scalars().unique().first()

    async def has_previous_transfer(self, from_account_id: UUID, to_account_id: UUID) -> bool:
        result = await self.db.execute(
            select(Transaction.id).where(
                Transaction.from_account_id == from_account_id,
                Transaction.to_account_id == to_account_id,
                Transaction.status == "completed",
            )
        )
        return result.scalar_one_or_none() is not None

    async def paginate_for_user(
        self,
        *,
        user_id: UUID,
        account_id: UUID | None = None,
        status: str | None = None,
        direction: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        filters = [
            or_(
                Transaction.initiated_by_user_id == user_id,
                Transaction.from_account.has(user_id=user_id),
                Transaction.to_account.has(user_id=user_id),
            )
        ]
        if account_id is not None:
            filters.append(or_(Transaction.from_account_id == account_id, Transaction.to_account_id == account_id))
        if status is not None:
            filters.append(Transaction.status == status)
        if direction == "debit":
            filters.append(Transaction.from_account.has(user_id=user_id))
        elif direction == "credit":
            filters.append(Transaction.to_account.has(user_id=user_id))
        if date_from is not None:
            filters.append(Transaction.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
        if date_to is not None:
            filters.append(Transaction.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))

        query = select(Transaction).where(*filters)
        count_query = select(func.count()).select_from(Transaction).where(*filters)
        result = await self.db.execute(
            query.order_by(Transaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        total = await self.db.scalar(count_query)
        return list(result.scalars().unique().all()), int(total or 0)

    async def list_for_export(
        self,
        *,
        account_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(
                or_(Transaction.from_account_id == account_id, Transaction.to_account_id == account_id),
                Transaction.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc),
                Transaction.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc),
            )
            .order_by(Transaction.created_at.asc())
        )
        return list(result.scalars().unique().all())
