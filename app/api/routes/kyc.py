from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_kyc_service
from app.schemas.kyc import KYCSubmissionCreateRequest, KYCSubmissionResponse
from app.services.kyc import KYCService

router = APIRouter(prefix="/kyc", tags=["KYC"])


@router.post("/submissions", response_model=KYCSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_kyc_submission(
    payload: KYCSubmissionCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    kyc_service: KYCService = Depends(get_kyc_service),
):
    submission = await kyc_service.submit(current_user=current_user, payload=payload, request=request)
    return {
        "submission_id": submission.id,
        "user_id": submission.user_id,
        "reviewer_user_id": submission.reviewer_user_id,
        "status": submission.status,
        "document_type": submission.document_type,
        "document_number": submission.document_number,
        "files": submission.files,
        "address_text": submission.address_text,
        "review_note": submission.review_note,
        "reviewed_at": submission.reviewed_at,
        "created_at": submission.created_at,
    }
