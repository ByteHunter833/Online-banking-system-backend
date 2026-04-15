from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_beneficiary_service
from app.schemas.beneficiary import BeneficiaryCreateRequest, BeneficiaryResponse
from app.services.beneficiary import BeneficiaryService

router = APIRouter(prefix="/beneficiaries", tags=["Beneficiaries"])


@router.post("/", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
async def create_beneficiary(
    payload: BeneficiaryCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    beneficiary_service: BeneficiaryService = Depends(get_beneficiary_service),
):
    return await beneficiary_service.create(current_user=current_user, payload=payload, request=request)


@router.get("/", response_model=list[BeneficiaryResponse])
async def list_beneficiaries(
    current_user=Depends(get_current_user),
    beneficiary_service: BeneficiaryService = Depends(get_beneficiary_service),
):
    return await beneficiary_service.list_for_user(current_user)
