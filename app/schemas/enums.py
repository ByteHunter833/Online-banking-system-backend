from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    customer = "customer"
    admin = "admin"
    support = "support"
    compliance = "compliance"
    auditor = "auditor"


class KYCStatus(str, Enum):
    pending = "pending"
    under_review = "under_review"
    more_info_required = "more_info_required"
    verified = "verified"
    rejected = "rejected"


class AccountStatus(str, Enum):
    active = "active"
    frozen = "frozen"
    closed = "closed"


class TransactionStatus(str, Enum):
    pending = "pending"
    pending_review = "pending_review"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TransactionType(str, Enum):
    internal_transfer = "internal_transfer"


class CardStatus(str, Enum):
    active = "active"
    frozen = "frozen"
    expired = "expired"


class CardType(str, Enum):
    physical = "physical"
    virtual = "virtual"


class NotificationCategory(str, Enum):
    system = "system"
    security_alert = "security_alert"
    transaction = "transaction"
    support = "support"


class NotificationChannel(str, Enum):
    in_app = "in_app"
    email = "email"
    sms = "sms"


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class OTPPurpose(str, Enum):
    email_verification = "email_verification"
    password_reset = "password_reset"
    transfer_sensitive = "transfer_sensitive"
    change_password = "change_password"
    account_deactivation = "account_deactivation"
    auth_challenge = "auth_challenge"


class MFAMethod(str, Enum):
    totp = "totp"
    email_otp = "email_otp"
    recovery_code = "recovery_code"


class MFASecretStatus(str, Enum):
    pending = "pending"
    active = "active"
    disabled = "disabled"


class ChallengePurpose(str, Enum):
    transfer = "transfer"
    beneficiary_create = "beneficiary_create"
    session_revoke = "session_revoke"
    password_change = "password_change"
    recurring_transfer = "recurring_transfer"


class ChallengeStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    used = "used"
    expired = "expired"
    failed = "failed"


class SessionStatus(str, Enum):
    active = "active"
    revoked = "revoked"


class BeneficiaryStatus(str, Enum):
    active = "active"
    archived = "archived"


class RecurringFrequency(str, Enum):
    weekly = "weekly"
    monthly = "monthly"


class RecurringTransferStatus(str, Enum):
    active = "active"
    paused = "paused"
    cancelled = "cancelled"


class StatementExportFormat(str, Enum):
    csv = "csv"
    pdf = "pdf"


class StatementExportStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SupportAuthorRole(str, Enum):
    customer = "customer"
    support = "support"
    admin = "admin"
    system = "system"


class FraudCaseStatus(str, Enum):
    open = "open"
    in_review = "in_review"
    resolved = "resolved"


class FraudDecision(str, Enum):
    approve_transfer = "approve_transfer"
    reject_transfer = "reject_transfer"
    freeze_account = "freeze_account"


class RiskDecision(str, Enum):
    allow = "allow"
    challenge_required = "challenge_required"
    queue_review = "queue_review"
    block = "block"
    freeze_account = "freeze_account"
