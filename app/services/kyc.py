from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models import KYCSubmission, User
from app.repositories.kyc import KYCRepository
from app.schemas.kyc import KYCSubmissionCreateRequest, KYCSubmissionReviewRequest
from app.services.audit import AuditService


class KYCService:
    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        self.db = db
        self.repository = KYCRepository(db)
        self.audit_service = audit_service

    async def submit(
        self,
        *,
        current_user: User,
        payload: KYCSubmissionCreateRequest,
        request: Request,
    ) -> KYCSubmission:
        submission = KYCSubmission(
            user_id=current_user.id,
            status="under_review",
            document_type=payload.document_type,
            document_number=payload.document_number,
            files=payload.files,
            address_text=payload.address_text,
        )
        current_user.kyc_status = "under_review"
        self.repository.add(submission)
        await self.audit_service.log(
            request=request,
            actor=current_user,
            action="kyc.submitted",
            resource_type="kyc_submission",
            resource_id=str(submission.id),
            description="KYC submission created.",
        )
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def list_submissions(self) -> list[KYCSubmission]:
        return await self.repository.list_all()

    async def review(
        self,
        *,
        admin_user: User,
        submission_id: UUID,
        payload: KYCSubmissionReviewRequest,
        request: Request,
    ) -> KYCSubmission:
        submission = await self.repository.get(submission_id)
        if submission is None:
            raise NotFoundException("KYC submission not found.")
        submission.status = payload.status.value
        submission.review_note = payload.review_note
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.reviewer_user_id = admin_user.id
        submission.user.kyc_status = payload.status.value
        await self.audit_service.log(
            request=request,
            actor=admin_user,
            action="kyc.reviewed",
            resource_type="kyc_submission",
            resource_id=str(submission.id),
            target_user_id=str(submission.user_id),
            description=f"KYC marked {payload.status.value}.",
            after_state={"status": payload.status.value},
        )
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

