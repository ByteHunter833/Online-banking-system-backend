from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MFASecret(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mfa_secrets"
    __table_args__ = (
        UniqueConstraint("user_id", "status", name="uq_mfa_secrets_user_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    encrypted_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    primary_method: Mapped[str] = mapped_column(String(32), default="totp", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    recovery_code_hashes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="mfa_secrets", lazy="selectin")

