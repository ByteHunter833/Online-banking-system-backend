from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import BeneficiaryStatus


class BeneficiaryCreateRequest(BaseModel):
    account_number: str = Field(min_length=8, max_length=32)
    nickname: str = Field(min_length=2, max_length=120)
    challenge_id: UUID | None = None


class BeneficiaryResponse(BaseModel):
    id: UUID
    account_number: str
    nickname: str
    status: BeneficiaryStatus
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

