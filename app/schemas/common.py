from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class AuditMetadata(ORMModel):
    created_at: datetime
    updated_at: datetime


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta
