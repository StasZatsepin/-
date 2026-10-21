"""Схемы источников данных."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SourceType


class SourceMetadata(BaseModel):
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    document_name: Optional[str] = None
    document_date: Optional[str] = None
    valid_until: Optional[str] = None
    applies_to_model: Optional[str] = None
    scope_note: Optional[str] = None
    issuer: Optional[str] = None

    @field_validator(
        "document_type",
        "document_number",
        "document_name",
        "applies_to_model",
        "scope_note",
        "issuer",
    )
    @classmethod
    def _strip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    source_type: str
    source_name: str
    source_date: Optional[datetime] = None
    source_uri: Optional[str] = None
    content_hash: str
    extraction_method: str
    extraction_status: str
    extraction_note: str
    mime_type: Optional[str] = None
    size_bytes: int
    uploaded_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    text_preview: str = ""
    text_length: int = 0


class SourceCreateManual(BaseModel):
    """Ручной ввод источника: заметка, отзыв или текст документа."""

    source_name: str = Field(min_length=1, max_length=255)
    source_type: SourceType = SourceType.USER_NOTE
    text: str = Field(min_length=1, max_length=200000)
    source_date: Optional[datetime] = None
    source_uri: Optional[str] = None
    metadata: SourceMetadata = Field(default_factory=SourceMetadata)

    @field_validator("source_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Укажите название источника")
        return cleaned
