from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FraudCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fraud_cases"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_actions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="fraud_cases", lazy="selectin")
    transaction: Mapped["Transaction | None"] = relationship(back_populates="fraud_case", lazy="selectin")
    decided_by: Mapped["User | None"] = relationship(foreign_keys=[decided_by_user_id], lazy="selectin")
    risk_events: Mapped[list["RiskEvent"]] = relationship(back_populates="fraud_case", lazy="selectin")

