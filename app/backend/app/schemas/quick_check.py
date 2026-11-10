"""Схемы публичной быстрой проверки (без регистрации и без сохранения данных)."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.analysis import SourceRef


class QuickCheckRequest(BaseModel):
    name: str = Field(default="Товар без названия", max_length=200)
    description: str = Field(min_length=10, max_length=8000)
    attributes_text: str = Field(default="", max_length=4000)
    document_text: str = Field(default="", max_length=12000)
    reviews_text: str = Field(default="", max_length=8000)

    @field_validator("name", "description", "attributes_text", "document_text", "reviews_text")
    @classmethod
    def _strip(cls, value: str) -> str:
        return (value or "").strip()


class QuickFinding(BaseModel):
    finding_type: str
    severity: str
    title: str
    description: str
    source_refs: List[SourceRef] = Field(default_factory=list)
    limitations: str = ""
    recommended_action: str = ""
    rule_id: str = ""
    suggestion: Optional[Dict[str, str]] = None


class QuickCheckResult(BaseModel):
    findings: List[QuickFinding]
    total: int
    by_severity: Dict[str, int]
    claims_count: int
    note: str
