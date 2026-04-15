from __future__ import annotations

from fastapi import Depends

from app.core.redis import get_redis
from app.db.session import get_db
from app.services.account import AccountService
from app.services.admin import AdminService
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.beneficiary import BeneficiaryService
from app.services.card import CardService
from app.services.challenge import ChallengeService
from app.services.communication import CommunicationService
from app.services.dashboard import DashboardService
from app.services.fraud import FraudService
from app.services.kyc import KYCService
from app.services.mfa import MFAService
from app.services.notification import NotificationService
from app.services.notification_preference import NotificationPreferenceService
from app.services.otp import OTPService
from app.services.recurring_transfer import RecurringTransferService
from app.services.session import SessionService
from app.services.statement import StatementService
from app.services.support import SupportService
from app.services.transaction import TransactionService
from app.services.user import UserService
from app.services.webhook import WebhookService


def get_communication_service() -> CommunicationService:
    return CommunicationService()


def get_webhook_service() -> WebhookService:
    return WebhookService()


def get_audit_service(db=Depends(get_db)) -> AuditService:
    return AuditService(db)


def get_notification_service(
    db=Depends(get_db),
    communication: CommunicationService = Depends(get_communication_service),
) -> NotificationService:
    return NotificationService(db, communication)


def get_notification_preference_service(db=Depends(get_db)) -> NotificationPreferenceService:
    return NotificationPreferenceService(db)


async def get_otp_service(
    db=Depends(get_db),
    redis=Depends(get_redis),
    communication: CommunicationService = Depends(get_communication_service),
) -> OTPService:
    return OTPService(db, redis, communication)


def get_mfa_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> MFAService:
    return MFAService(db, audit_service)


def get_session_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> SessionService:
    return SessionService(db, audit_service)


async def get_challenge_service(
    db=Depends(get_db),
    otp_service: OTPService = Depends(get_otp_service),
    mfa_service: MFAService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ChallengeService:
    return ChallengeService(db, otp_service, mfa_service, audit_service)


def get_dashboard_service(
    db=Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service),
) -> DashboardService:
    return DashboardService(db, notification_service)


def get_beneficiary_service(
    db=Depends(get_db),
    challenge_service: ChallengeService = Depends(get_challenge_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> BeneficiaryService:
    return BeneficiaryService(db, challenge_service, audit_service)


def get_kyc_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> KYCService:
    return KYCService(db, audit_service)


def get_statement_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> StatementService:
    return StatementService(db, audit_service)


def get_fraud_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> FraudService:
    return FraudService(db, audit_service)


def get_recurring_transfer_service(
    db=Depends(get_db),
    challenge_service: ChallengeService = Depends(get_challenge_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> RecurringTransferService:
    return RecurringTransferService(db, challenge_service, audit_service)


async def get_auth_service(
    db=Depends(get_db),
    otp_service: OTPService = Depends(get_otp_service),
    notification_service: NotificationService = Depends(get_notification_service),
    audit_service: AuditService = Depends(get_audit_service),
    webhook_service: WebhookService = Depends(get_webhook_service),
    mfa_service: MFAService = Depends(get_mfa_service),
    session_service: SessionService = Depends(get_session_service),
) -> AuthService:
    return AuthService(
        db,
        otp_service,
        notification_service,
        audit_service,
        webhook_service,
        mfa_service,
        session_service,
    )


async def get_user_service(
    db=Depends(get_db),
    otp_service: OTPService = Depends(get_otp_service),
    notification_service: NotificationService = Depends(get_notification_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> UserService:
    return UserService(db, otp_service, notification_service, audit_service)


def get_account_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> AccountService:
    return AccountService(db, audit_service)


async def get_transaction_service(
    db=Depends(get_db),
    otp_service: OTPService = Depends(get_otp_service),
    notification_service: NotificationService = Depends(get_notification_service),
    audit_service: AuditService = Depends(get_audit_service),
    webhook_service: WebhookService = Depends(get_webhook_service),
    challenge_service: ChallengeService = Depends(get_challenge_service),
    fraud_service: FraudService = Depends(get_fraud_service),
) -> TransactionService:
    return TransactionService(
        db,
        otp_service,
        notification_service,
        audit_service,
        webhook_service,
        challenge_service,
        fraud_service,
    )


def get_card_service(
    db=Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> CardService:
    return CardService(db, audit_service)


def get_support_service(
    db=Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> SupportService:
    return SupportService(db, notification_service, audit_service)


def get_admin_service(
    db=Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AdminService:
    return AdminService(db, notification_service, audit_service)
