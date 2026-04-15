from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import KYCStatus


class KYCSubmissionCreateRequest(BaseModel):
    document_type: str = Field(min_length=2, max_length=64)
    document_number: str = Field(min_length=3, max_length=120)
    files: list[str] = Field(min_length=1)
    address_text: str = Field(min_length=5, max_length=500)


class KYCSubmissionReviewRequest(BaseModel):
    status: KYCStatus
    review_note: str | None = Field(default=None, max_length=1000)


class KYCSubmissionResponse(BaseModel):
    submission_id: UUID
    user_id: UUID
    reviewer_user_id: UUID | None
    status: KYCStatus
    document_type: str
    document_number: str
    files: list[str]
    address_text: str
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

