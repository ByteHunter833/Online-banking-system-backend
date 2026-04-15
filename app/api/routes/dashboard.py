from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_dashboard_service
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview(
    current_user=Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
):
    return await dashboard_service.overview(current_user)
