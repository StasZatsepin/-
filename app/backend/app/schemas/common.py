"""Схемы API: общие типы и ответы с ошибками."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    type: str = "value_error"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class MessageResponse(BaseModel):
    message: str
    detail: Optional[Dict[str, Any]] = None


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int
