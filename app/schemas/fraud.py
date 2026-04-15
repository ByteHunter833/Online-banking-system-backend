from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import FraudCaseStatus, FraudDecision


class FraudCaseDecisionRequest(BaseModel):
    decision: FraudDecision
    reason: str = Field(min_length=3, max_length=255)


class FraudCaseResponse(BaseModel):
    case_id: UUID
    transaction_id: UUID | None
    user_id: UUID
    status: FraudCaseStatus
    score: int
    reasons: list[str]
    decision: FraudDecision | None = None
    decision_reason: str | None = None
    applied_actions: list[str] | None = None
    decided_by_user_id: UUID | None = None
    decided_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
