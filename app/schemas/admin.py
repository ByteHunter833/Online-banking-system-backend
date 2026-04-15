from __future__ import annotations

from pydantic import BaseModel, Field


class AdminReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)

