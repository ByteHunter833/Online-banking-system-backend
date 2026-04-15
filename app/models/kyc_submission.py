from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KYCSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kyc_submissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="under_review", nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_number: Mapped[str] = mapped_column(String(120), nullable=False)
    files: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    address_text: Mapped[str] = mapped_column(String(500), nullable=False)
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="kyc_submissions",
        lazy="selectin",
    )
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewer_user_id], lazy="selectin")

