from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import StatementExportFormat, StatementExportStatus


class StatementExportCreateRequest(BaseModel):
    account_id: UUID
    date_from: date
    date_to: date
    format: StatementExportFormat = StatementExportFormat.csv


class StatementExportResponse(BaseModel):
    export_id: UUID
    status: StatementExportStatus
    download_url: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None

