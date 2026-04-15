from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.card import Card
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.transaction import Transaction
from app.models.user import User


class BankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bank_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    account_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    iban: Mapped[str] = mapped_column(String(34), unique=True, nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    daily_transfer_limit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    daily_transferred_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    last_transfer_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="bank_accounts", lazy="selectin")
    cards: Mapped[list["Card"]] = relationship(back_populates="account", lazy="selectin")
    outgoing_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="from_account",
        foreign_keys="Transaction.from_account_id",
    )
    incoming_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="to_account",
        foreign_keys="Transaction.to_account_id",
    )
