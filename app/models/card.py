from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Card(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cards"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id"),
        nullable=False,
        index=True,
    )
    masked_pan: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    brand: Mapped[str] = mapped_column(String(32), default="VISA", nullable=False)
    card_type: Mapped[str] = mapped_column(String(32), default="virtual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    spending_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    online_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    atm_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contactless_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    frozen_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="cards", lazy="selectin")
    account: Mapped["BankAccount"] = relationship(back_populates="cards", lazy="selectin")
