from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException
from app.models import FraudCase, RiskEvent, Transaction, User
from app.repositories.account import AccountRepository
from app.repositories.fraud import FraudRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.enums import FraudDecision, RiskDecision
from app.services.audit import AuditService


class FraudService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)
        self.repository = FraudRepository(db)
        self.audit_service = audit_service

    async def evaluate_transfer(
        self,
        *,
        current_user: User,
        sender_account_id: UUID,
        recipient_account_id: UUID,
        amount: Decimal,
    ) -> tuple[RiskDecision, int, list[str]]:
        score = 0
        reasons: list[str] = []
        if current_user.kyc_status != "verified":
            score += 25
            reasons.append("kyc_not_verified")
        if amount >= settings.sensitive_transfer_threshold:
            score += 50
            reasons.append("high_amount")
        prior_exists = await self.transactions.has_previous_transfer(sender_account_id, recipient_account_id)
        if not prior_exists:
            score += 20
            reasons.append("first_time_recipient")
        if score >= settings.risk_queue_threshold:
            return RiskDecision.queue_review, score, reasons
        if score >= settings.risk_challenge_threshold:
            return RiskDecision.challenge_required, score, reasons
        return RiskDecision.allow, score, reasons

    async def create_case_for_transaction(
        self,
        *,
        user: User,
        transaction: Transaction,
        score: int,
        reasons: list[str],
    ) -> FraudCase:
        case = FraudCase(
            user_id=user.id,
            transaction_id=transaction.id,
            status="open",
            score=score,
            reasons=reasons,
        )
        self.repository.add_case(case)
        for reason in reasons:
            self.repository.add_event(
                RiskEvent(
                    user_id=user.id,
                    transaction_id=transaction.id,
                    fraud_case=case,
                    rule_name=reason,
                    score=score,
                    decision="queue_review",
                    details={"transaction_reference": transaction.reference},
                )
            )
        await self.db.flush()
        return case

    async def list_cases(self, *, status: str | None = None, score_gte: int | None = None) -> list[FraudCase]:
        return await self.repository.list_cases(status=status, score_gte=score_gte)

    async def decide_case(
        self,
        *,
        admin_user: User,
        case_id: UUID,
        decision: FraudDecision,
        reason: str,
        request: Request,
    ) -> FraudCase:
        case = await self.repository.get_case(case_id)
        if case is None:
            raise NotFoundException("Fraud case not found.")
        if case.transaction is None:
            raise ConflictException("Fraud case has no associated transaction.")

        applied_actions: list[str] = []
        transaction = case.transaction
        if decision == FraudDecision.reject_transfer:
            transaction.status = "failed"
            transaction.failure_reason = reason
            applied_actions.append("transaction_rejected")
        elif decision == FraudDecision.freeze_account:
            sender = await self.accounts.get_by_id(transaction.from_account_id)
            if sender is not None:
                sender.status = "frozen"
                applied_actions.append("account_frozen")
            transaction.status = "failed"
            transaction.failure_reason = reason
        else:
            if transaction.status != "pending_review":
                raise ConflictException("Only pending review transactions can be approved.")
            locked = await self.accounts.lock_accounts([transaction.from_account_id, transaction.to_account_id])
            accounts_by_id = {item.id: item for item in locked}
            sender = accounts_by_id[transaction.from_account_id]
            recipient = accounts_by_id[transaction.to_account_id]
            if Decimal(sender.available_balance) < Decimal(transaction.amount):
                raise ConflictException("Sender no longer has enough available balance.")
            sender.balance = Decimal(sender.balance) - Decimal(transaction.amount)
            sender.available_balance = Decimal(sender.available_balance) - Decimal(transaction.amount)
            sender.daily_transferred_amount = Decimal(sender.daily_transferred_amount) + Decimal(transaction.amount)
            recipient.balance = Decimal(recipient.balance) + Decimal(transaction.amount)
            recipient.available_balance = Decimal(recipient.available_balance) + Decimal(transaction.amount)
            transaction.status = "completed"
            transaction.processed_at = datetime.now(timezone.utc)
            applied_actions.append("transaction_completed")

        case.status = "resolved"
        case.decision = decision.value
        case.decision_reason = reason
        case.decided_by_user_id = admin_user.id
        case.decided_at = datetime.now(timezone.utc)
        case.applied_actions = applied_actions
        await self.audit_service.log(
            request=request,
            actor=admin_user,
            action="fraud.case_decided",
            resource_type="fraud_case",
            resource_id=str(case.id),
            target_user_id=str(case.user_id),
            description=f"Fraud case decision: {decision.value}",
            after_state={"decision": decision.value, "applied_actions": applied_actions},
        )
        await self.db.commit()
        await self.db.refresh(case)
        return case
