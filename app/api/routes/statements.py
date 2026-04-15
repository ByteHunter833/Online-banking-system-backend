from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user, rate_limit
from app.api.dependencies.services import get_statement_service
from app.schemas.statement import StatementExportCreateRequest, StatementExportResponse
from app.services.statement import StatementService

router = APIRouter(prefix="/statements", tags=["Statements"])


@router.post(
    "/exports",
    response_model=StatementExportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("statement-export", limit=5, window_seconds=3600, key_strategy="user"))],
)
async def create_statement_export(
    payload: StatementExportCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    statement_service: StatementService = Depends(get_statement_service),
):
    export = await statement_service.create_export(current_user=current_user, payload=payload, request=request)
    return {"export_id": export.id, "status": export.status}


@router.get("/exports/{export_id}", response_model=StatementExportResponse)
async def get_statement_export(
    export_id: UUID,
    current_user=Depends(get_current_user),
    statement_service: StatementService = Depends(get_statement_service),
):
    export = await statement_service.get_export(current_user=current_user, export_id=export_id)
    download_url = f"/files/statements/{export.id}.{export.export_format}" if export.file_path else None
    return {
        "export_id": export.id,
        "status": export.status,
        "download_url": download_url,
        "error_message": export.error_message,
        "completed_at": export.completed_at,
    }
