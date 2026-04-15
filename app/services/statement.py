from __future__ import annotations

import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException
from app.db.session import AsyncSessionLocal
from app.models import StatementExport, User
from app.repositories.account import AccountRepository
from app.repositories.statement import StatementExportRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.statement import StatementExportCreateRequest
from app.services.audit import AuditService
from app.workers.tasks import generate_statement_export


class StatementService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)
        self.repository = StatementExportRepository(db)
        self.audit_service = audit_service

    async def create_export(
        self,
        *,
        current_user: User,
        payload: StatementExportCreateRequest,
        request,
    ) -> StatementExport:
        if payload.date_from > payload.date_to:
            raise ConflictException("date_from must be before date_to.")
        account = await self.accounts.get_by_id_for_user(payload.account_id, current_user.id)
        if account is None:
            raise NotFoundException("Account not found.")

        export = StatementExport(
            user_id=current_user.id,
            account_id=payload.account_id,
            export_format=payload.format.value,
            status="queued",
            date_from=payload.date_from,
            date_to=payload.date_to,
        )
        self.repository.add(export)
        await self.db.flush()
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="statements.export_requested",
            resource_type="statement_export",
            resource_id=str(export.id),
            description="Statement export requested.",
        )
        await self.db.commit()

        try:
            generate_statement_export.delay(str(export.id))
        except Exception:
            asyncio.create_task(generate_statement_export_for_id(str(export.id)))
        return export

    async def get_export(self, *, current_user: User, export_id: UUID) -> StatementExport:
        export = await self.repository.get_for_user(export_id, current_user.id)
        if export is None:
            raise NotFoundException("Statement export not found.")
        return export


async def generate_statement_export_for_id(export_id: str) -> None:
    async with AsyncSessionLocal() as db:
        repository = StatementExportRepository(db)
        transactions = TransactionRepository(db)
        export = await repository.get_by_id(UUID(export_id))
        if export is None:
            return
        export.status = "processing"
        await db.commit()

        try:
            rows = await transactions.list_for_export(
                account_id=export.account_id,
                date_from=export.date_from,
                date_to=export.date_to,
            )
            statement_dir = Path(settings.storage_root) / "statements"
            statement_dir.mkdir(parents=True, exist_ok=True)
            file_path = statement_dir / f"{export.id}.csv"
            with file_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["reference", "status", "amount", "currency", "created_at", "description"])
                for row in rows:
                    writer.writerow(
                        [row.reference, row.status, str(row.amount), row.currency, row.created_at.isoformat(), row.description or ""]
                    )
            export.status = "completed"
            export.file_path = str(file_path)
            export.completed_at = datetime.now(timezone.utc)
            export.error_message = None
            await db.commit()
        except Exception as exc:
            export.status = "failed"
            export.error_message = str(exc)
            await db.commit()
