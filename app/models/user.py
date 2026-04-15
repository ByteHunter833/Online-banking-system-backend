from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import user_roles
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    kyc_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )
    bank_accounts: Mapped[list["BankAccount"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    cards: Mapped[list["Card"]] = relationship(back_populates="user", lazy="selectin")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor", lazy="selectin")
    otp_codes: Mapped[list["OTPCode"]] = relationship(back_populates="user", lazy="selectin")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    mfa_secrets: Mapped[list["MFASecret"]] = relationship(back_populates="user", lazy="selectin")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", lazy="selectin")
    trusted_devices: Mapped[list["TrustedDevice"]] = relationship(back_populates="user", lazy="selectin")
    auth_challenges: Mapped[list["AuthChallenge"]] = relationship(back_populates="user", lazy="selectin")
    login_events: Mapped[list["LoginEvent"]] = relationship(back_populates="user", lazy="selectin")
    notification_preferences: Mapped["NotificationPreference | None"] = relationship(
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    beneficiaries: Mapped[list["Beneficiary"]] = relationship(back_populates="user", lazy="selectin")
    recurring_transfers: Mapped[list["RecurringTransfer"]] = relationship(back_populates="user", lazy="selectin")
    statement_exports: Mapped[list["StatementExport"]] = relationship(back_populates="user", lazy="selectin")
    kyc_submissions: Mapped[list["KYCSubmission"]] = relationship(
        back_populates="user",
        foreign_keys="KYCSubmission.user_id",
        lazy="selectin",
    )
    risk_events: Mapped[list["RiskEvent"]] = relationship(back_populates="user", lazy="selectin")
    fraud_cases: Mapped[list["FraudCase"]] = relationship(
        back_populates="user",
        foreign_keys="FraudCase.user_id",
        lazy="selectin",
    )
