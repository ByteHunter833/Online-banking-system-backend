from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models import IdempotencyKey, Transaction, User
from app.repositories.account import AccountRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.enums import ChallengePurpose, NotificationCategory, OTPPurpose, RiskDecision
from app.schemas.transaction import TransferDraft, TransferRequest, TransferVerificationRequest
from app.services.audit import AuditService
from app.services.challenge import ChallengeService
from app.services.fraud import FraudService
from app.services.notification import NotificationService
from app.services.otp import OTPService
from app.services.webhook import WebhookService
from app.utils.idempotency import build_request_hash


class TransactionService:
    def __init__(
        self,
        db: AsyncSession,
        otp_service: OTPService,
        notification_service: NotificationService,
        audit_service: AuditService,
        webhook_service: WebhookService,
        challenge_service: ChallengeService,
        fraud_service: FraudService,
    ) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)
        self.idempotency = IdempotencyRepository(db)
        self.otp_service = otp_service
        self.notification_service = notification_service
        self.audit_service = audit_service
        self.webhook_service = webhook_service
        self.challenge_service = challenge_service
        self.fraud_service = fraud_service

    @staticmethod
    def _generate_reference() -> str:
        now = datetime.now(timezone.utc)
        return f"TRX-{now.strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _normalize_amount(amount: Decimal) -> str:
        return format(amount.normalize(), "f")

    @classmethod
    def _transfer_otp_context(cls, payload: TransferDraft) -> dict[str, str]:
        return {
            "from_account_id": str(payload.from_account_id),
            "recipient_account_number": payload.recipient_account_number,
            "amount": cls._normalize_amount(payload.amount),
        }

    @staticmethod
    def _reset_daily_amount_if_needed(account) -> None:
        now = datetime.now(timezone.utc)
        if account.last_transfer_reset_at.date() != now.date():
            account.last_transfer_reset_at = now
            account.daily_transferred_amount = Decimal("0.00")

    @staticmethod
    def _current_daily_transferred_amount(account) -> Decimal:
        now = datetime.now(timezone.utc)
        if account.last_transfer_reset_at.date() != now.date():
            return Decimal("0.00")
        return Decimal(account.daily_transferred_amount)

    async def _validate_transfer_draft(
        self,
        *,
        current_user: User,
        payload: TransferDraft,
        check_balance: bool = False,
    ) -> None:
        sender = await self.accounts.get_by_id_for_user(payload.from_account_id, current_user.id)
        recipient = await self.accounts.get_by_account_number(payload.recipient_account_number)
        if sender is None:
            raise NotFoundException("Source account not found.")
        if recipient is None:
            raise NotFoundException("Recipient account not found.")
        if sender.id == recipient.id:
            raise ConflictException("You cannot transfer money to the same account.")

        if sender.status != "active":
            raise ForbiddenException("Source account is not active.")
        if recipient.status != "active":
            raise ForbiddenException("Recipient account is not active.")
        if sender.currency != recipient.currency:
            raise ConflictException("Currency mismatch between the selected accounts.")

        projected_total = self._current_daily_transferred_amount(sender) + payload.amount
        if projected_total > Decimal(sender.daily_transfer_limit):
            raise ForbiddenException("Daily transfer limit exceeded.")
        if check_balance and Decimal(sender.available_balance) < payload.amount:
            raise ForbiddenException("Insufficient available balance.")

    async def _require_transfer_confirmation(
        self,
        *,
        current_user: User,
        payload: TransferRequest,
    ) -> str | None:
        context = self._transfer_otp_context(payload)
        if payload.challenge_id is not None:
            challenge = await self.challenge_service.require_verified(
                current_user=current_user,
                challenge_id=payload.challenge_id,
                purpose=ChallengePurpose.transfer.value,
                context=context,
                consume=True,
            )
            return str(challenge.id)
        if payload.otp_code:
            await self.otp_service.verify_user_otp(
                user=current_user,
                purpose=OTPPurpose.transfer_sensitive,
                otp_code=payload.otp_code,
                extra_match=context,
            )
            return None
        raise ForbiddenException("A transfer verification code is required for this transfer.")

    async def request_transfer_verification(
        self,
        *,
        current_user: User,
        payload: TransferVerificationRequest,
        request: Request,
    ) -> dict:
        await self._validate_transfer_draft(
            current_user=current_user,
            payload=payload,
            check_balance=True,
        )
        debug_otp, ttl_seconds = await self.otp_service.issue_otp(
            user=current_user,
            purpose=OTPPurpose.transfer_sensitive,
            delivery_channel=payload.delivery_channel,
            extra_data=self._transfer_otp_context(payload),
        )
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="transactions.transfer_verification_requested",
            resource_type="otp",
            description="Transfer verification code requested.",
            extra=self._transfer_otp_context(payload),
        )
        await self.db.commit()
        return {
            "message": "Transfer verification code sent.",
            "purpose": OTPPurpose.transfer_sensitive,
            "expires_in_seconds": ttl_seconds,
            "delivery_channel": payload.delivery_channel,
            "debug_otp": debug_otp if settings.debug else None,
        }

    async def transfer(
        self,
        *,
        current_user: User,
        payload: TransferRequest,
        request: Request,
        idempotency_key_header: str | None = None,
    ) -> Transaction:
        idempotency_key_value = idempotency_key_header or payload.idempotency_key
        if not idempotency_key_value:
            raise ConflictException("An idempotency key is required.")

        request_hash = build_request_hash(
            payload.model_dump(exclude={"otp_code", "challenge_id", "idempotency_key"}, mode="json")
        )
        existing_key = await self.idempotency.get_key(current_user.id, "transfer", idempotency_key_value)
        if existing_key is not None:
            if existing_key.request_hash != request_hash:
                raise ConflictException("Idempotency key was already used with a different request payload.")
            if existing_key.resource_id:
                existing_transaction = await self.transactions.get_by_id(UUID(existing_key.resource_id))
                if existing_transaction:
                    return existing_transaction
            if existing_key.state != "failed":
                raise ConflictException("This transfer request is already being processed.")
            existing_key.state = "processing"
            existing_key.resource_id = None
            existing_key.response_code = None
            existing_key.expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.idempotency_ttl_hours)
            idempotency_key = existing_key
        else:
            idempotency_key = IdempotencyKey(
                user_id=current_user.id,
                operation="transfer",
                key=idempotency_key_value,
                request_hash=request_hash,
                state="processing",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.idempotency_ttl_hours),
            )
            self.idempotency.add(idempotency_key)
            try:
                await self.db.flush()
            except IntegrityError as exc:
                await self.db.rollback()
                raise ConflictException("This transfer request is already being processed.") from exc

        event_payload: dict | None = None
        try:
            async with self.db.begin_nested():
                sender = await self.accounts.get_by_id_for_user(payload.from_account_id, current_user.id)
                recipient = await self.accounts.get_by_account_number(payload.recipient_account_number)
                if sender is None:
                    raise NotFoundException("Source account not found.")
                if recipient is None:
                    raise NotFoundException("Recipient account not found.")
                if sender.id == recipient.id:
                    raise ConflictException("You cannot transfer money to the same account.")

                if sender.status != "active":
                    raise ForbiddenException("Source account is not active.")
                if recipient.status != "active":
                    raise ForbiddenException("Recipient account is not active.")
                if sender.currency != recipient.currency:
                    raise ConflictException("Currency mismatch between the selected accounts.")

                self._reset_daily_amount_if_needed(sender)
                projected_total = Decimal(sender.daily_transferred_amount) + payload.amount
                if projected_total > Decimal(sender.daily_transfer_limit):
                    raise ForbiddenException("Daily transfer limit exceeded.")

                risk_decision, risk_score, reasons = await self.fraud_service.evaluate_transfer(
                    current_user=current_user,
                    sender_account_id=sender.id,
                    recipient_account_id=recipient.id,
                    amount=payload.amount,
                )
                challenge_id = await self._require_transfer_confirmation(
                    current_user=current_user,
                    payload=payload,
                )

                transaction = Transaction(
                    reference=self._generate_reference(),
                    from_account_id=sender.id,
                    to_account_id=recipient.id,
                    initiated_by_user_id=current_user.id,
                    transaction_type="internal_transfer",
                    status="pending_review" if risk_decision == RiskDecision.queue_review else "pending",
                    amount=payload.amount,
                    fee_amount=Decimal("0.00"),
                    currency=sender.currency,
                    description=payload.description,
                    risk_flag=risk_score > 0,
                    risk_score=risk_score,
                    risk_status=risk_decision.value,
                    review_required_at=datetime.now(timezone.utc) if risk_decision == RiskDecision.queue_review else None,
                    extra_data={
                        "idempotency_key": idempotency_key_value,
                        "challenge_id": challenge_id,
                        "risk_reasons": reasons,
                    },
                )
                self.transactions.add(transaction)
                await self.db.flush()

                if risk_decision == RiskDecision.queue_review:
                    await self.fraud_service.create_case_for_transaction(
                        user=current_user,
                        transaction=transaction,
                        score=risk_score,
                        reasons=reasons,
                    )
                    await self.notification_service.create_notification(
                        user=current_user,
                        title="Transfer queued for review",
                        message=f"Transfer {transaction.reference} is pending fraud review.",
                        category=NotificationCategory.security_alert,
                        send_email=True,
                    )
                    await self.audit_service.log(
                        request=request,
                        actor=current_user,
                        action="transactions.transfer_review_queued",
                        resource_type="transaction",
                        resource_id=str(transaction.id),
                        description="Transfer queued for fraud review.",
                        challenge_id=challenge_id,
                        idempotency_key=idempotency_key_value,
                        extra={"risk_score": risk_score, "reasons": reasons},
                    )
                else:
                    locked_accounts = await self.accounts.lock_accounts([sender.id, recipient.id])
                    accounts_by_id = {account.id: account for account in locked_accounts}
                    sender = accounts_by_id[sender.id]
                    recipient = accounts_by_id[recipient.id]
                    if Decimal(sender.available_balance) < payload.amount:
                        raise ForbiddenException("Insufficient available balance.")

                    sender.balance = Decimal(sender.balance) - payload.amount
                    sender.available_balance = Decimal(sender.available_balance) - payload.amount
                    sender.daily_transferred_amount = projected_total

                    recipient.balance = Decimal(recipient.balance) + payload.amount
                    recipient.available_balance = Decimal(recipient.available_balance) + payload.amount

                    transaction.status = "completed"
                    transaction.processed_at = datetime.now(timezone.utc)
                    await self.notification_service.create_notification(
                        user=current_user,
                        title="Transfer completed",
                        message=(
                            f"Transfer {transaction.reference} completed successfully for "
                            f"{payload.amount} {transaction.currency}."
                        ),
                        category=NotificationCategory.transaction,
                    )
                    if recipient.user_id != current_user.id:
                        await self.notification_service.create_notification(
                            user=recipient.user,
                            title="Incoming transfer received",
                            message=(
                                f"You received {payload.amount} {transaction.currency} "
                                f"from {current_user.full_name}."
                            ),
                            category=NotificationCategory.transaction,
                        )
                    await self.audit_service.log(
                        request=request,
                        actor=current_user,
                        action="transactions.transfer",
                        resource_type="transaction",
                        resource_id=str(transaction.id),
                        description="Internal transfer completed.",
                        challenge_id=challenge_id,
                        idempotency_key=idempotency_key_value,
                        extra={"risk_score": risk_score, "reference": transaction.reference, "reasons": reasons},
                    )
                    event_payload = {
                        "transaction_id": str(transaction.id),
                        "reference": transaction.reference,
                        "amount": str(transaction.amount),
                        "currency": transaction.currency,
                        "risk_flag": transaction.risk_flag,
                    }

                idempotency_key.state = "completed"
                idempotency_key.resource_id = str(transaction.id)
                idempotency_key.response_code = "201"
        except Exception as exc:
            idempotency_key.state = "failed"
            idempotency_key.response_code = "400"
            await self.db.commit()
            raise exc

        await self.db.commit()
        transaction = await self.transactions.get_by_id(UUID(idempotency_key.resource_id or "00000000-0000-0000-0000-000000000000"))
        if transaction is None:
            raise NotFoundException("Transaction could not be loaded after processing.")
        if event_payload is not None:
            await self.webhook_service.publish_event("transactions.transfer.completed", event_payload)
        return transaction

    async def list_history(self, current_user: User) -> list[Transaction]:
        return await self.transactions.list_for_user(current_user.id)

    async def paginate_history(
        self,
        *,
        current_user: User,
        account_id: UUID | None = None,
        status: str | None = None,
        direction: str | None = None,
        date_from=None,
        date_to=None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        return await self.transactions.paginate_for_user(
            user_id=current_user.id,
            account_id=account_id,
            status=status,
            direction=direction,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    async def get_transaction(self, current_user: User, transaction_id: UUID) -> Transaction:
        transaction = await self.transactions.user_can_access(transaction_id, current_user.id)
        if transaction is None:
            raise NotFoundException("Transaction not found.")
        return transaction
