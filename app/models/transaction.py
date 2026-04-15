from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"

    reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    from_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id"),
        nullable=False,
        index=True,
    )
    to_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id"),
        nullable=False,
        index=True,
    )
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    transaction_type: Mapped[str] = mapped_column(String(32), default="internal_transfer", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_status: Mapped[str] = mapped_column(String(32), default="allow", nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_required_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    from_account: Mapped["BankAccount"] = relationship(
        back_populates="outgoing_transactions",
        foreign_keys=[from_account_id],
        lazy="selectin",
    )
    to_account: Mapped["BankAccount"] = relationship(
        back_populates="incoming_transactions",
        foreign_keys=[to_account_id],
        lazy="selectin",
    )
    initiated_by: Mapped["User"] = relationship(lazy="selectin")
    fraud_case: Mapped["FraudCase | None"] = relationship(back_populates="transaction", uselist=False, lazy="selectin")
    risk_events: Mapped[list["RiskEvent"]] = relationship(back_populates="transaction", lazy="selectin")
