from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class NotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    system_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    system_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    system_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    security_alert_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    security_alert_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    security_alert_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transaction_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    transaction_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    transaction_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    support_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    support_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    support_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="notification_preferences", lazy="selectin")

