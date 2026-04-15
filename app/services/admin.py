from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models import User
from app.repositories.account import AccountRepository
from app.repositories.audit import AuditRepository
from app.repositories.support import SupportRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user import UserRepository
from app.schemas.enums import NotificationCategory
from app.services.audit import AuditService
from app.services.notification import NotificationService


class AdminService:
    def __init__(
        self,
        db: AsyncSession,
        notification_service: NotificationService,
        audit_service: AuditService,
    ) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)
        self.audits = AuditRepository(db)
        self.support = SupportRepository(db)
        self.notification_service = notification_service
        self.audit_service = audit_service

    async def list_users(self) -> list:
        return await self.users.list_users(limit=200)

    async def list_transactions(self) -> list:
        return await self.transactions.list_all(limit=200)

    async def freeze_account(self, *, admin_user: User, account_id, reason: str, request: Request):
        account = await self.accounts.get_by_id(account_id)
        if account is None:
            raise NotFoundException("Bank account not found.")
        account.status = "frozen"
        await self.notification_service.create_notification(
            user=account.user,
            title="Account frozen",
            message=f"Your account {account.account_number} has been frozen. Reason: {reason}",
            category=NotificationCategory.security_alert,
            send_email=True,
        )
        await self.audit_service.log(
            request=request,
            actor=admin_user,
            action="admin.account_frozen",
            resource_type="bank_account",
            resource_id=str(account.id),
            description=reason,
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def unfreeze_account(self, *, admin_user: User, account_id, reason: str, request: Request):
        account = await self.accounts.get_by_id(account_id)
        if account is None:
            raise NotFoundException("Bank account not found.")
        account.status = "active"
        await self.notification_service.create_notification(
            user=account.user,
            title="Account reactivated",
            message=f"Your account {account.account_number} has been unfrozen. Note: {reason}",
            category=NotificationCategory.security_alert,
            send_email=True,
        )
        await self.audit_service.log(
            request=request,
            actor=admin_user,
            action="admin.account_unfrozen",
            resource_type="bank_account",
            resource_id=str(account.id),
            description=reason,
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def flag_transaction(self, *, admin_user: User, transaction_id, reason: str, request: Request):
        transaction = await self.transactions.get_by_id(transaction_id)
        if transaction is None:
            raise NotFoundException("Transaction not found.")
        transaction.risk_flag = True
        transaction.failure_reason = reason
        await self.notification_service.create_notification(
            user=transaction.initiated_by,
            title="Transaction under review",
            message=f"Transaction {transaction.reference} was flagged for review. Reason: {reason}",
            category=NotificationCategory.security_alert,
            send_email=True,
        )
        await self.audit_service.log(
            request=request,
            actor=admin_user,
            action="admin.transaction_flagged",
            resource_type="transaction",
            resource_id=str(transaction.id),
            description=reason,
        )
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def list_audit_logs(self) -> list:
        return await self.audits.list_recent(limit=200)

    async def list_support_tickets(self) -> list:
        return await self.support.list_all()

