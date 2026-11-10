"""Схемы утверждений, доказательств, находок и запусков анализа."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import FindingStatus, FindingType, Severity
from app.rules.suggestions import suggest_fix


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    text: str
    claim_type: str
    source_excerpt: str
    extraction_method: str
    model_version: Optional[str] = None
    confidence_label: Optional[str] = None
    confidence_status: str
    user_confirmed: bool
    is_rejected: bool
    numeric_value: Optional[float] = None
    numeric_unit: Optional[str] = None
    numeric_dimension: Optional[str] = None
    numeric_comparator: Optional[str] = None
    created_at: datetime


class ClaimUpdate(BaseModel):
    text: Optional[str] = Field(default=None, max_length=5000)
    claim_type: Optional[str] = Field(default=None, max_length=60)
    user_confirmed: Optional[bool] = None
    is_rejected: Optional[bool] = None
    confidence_status: Optional[str] = Field(default=None, max_length=60)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Текст утверждения не может быть пустым")
        return cleaned


class ClaimCreate(BaseModel):
    text: str = Field(min_length=3, max_length=5000)
    claim_type: str = Field(default="other", max_length=60)
    source_excerpt: str = Field(default="", max_length=5000)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Текст утверждения не может быть пустым")
        return cleaned


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    claim_id: Optional[str] = None
    evidence_type: str
    excerpt: str
    relation: str
    relevance_note: str
    date: Optional[datetime] = None
    created_at: datetime


class SourceRef(BaseModel):
    source_id: Optional[str] = None
    source_name: str
    excerpt: str
    relation: str
    evidence_type: str = "description_text"
    note: str = ""


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    claim_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    finding_type: str
    severity: str
    title: str
    description: str
    source_evidence_ids: List[str] = Field(default_factory=list)
    source_refs: List[SourceRef] = Field(default_factory=list)
    limitations: str
    recommended_action: str
    confidence_status: str
    status: str
    rule_id: str
    rule_version: str
    origin: str
    archived: bool
    explanation: str = ""
    explanation_provider: str = ""
    suggestion: Optional[Dict[str, str]] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _fill_suggestion(self) -> "FindingOut":
        if self.suggestion is None:
            self.suggestion = suggest_fix(self.rule_id, self.description, self.recommended_action)
        return self


class FindingUpdate(BaseModel):
    status: Optional[FindingStatus] = None
    comment: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("comment")
    @classmethod
    def _strip_comment(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip()


class ReviewActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    product_id: str
    user_id: Optional[str] = None
    user_email: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    comment: str
    created_at: datetime


class AnalysisRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    status: str
    engine_version: str
    rules_version: str
    provider_name: str
    provider_status: str
    triggered_by: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    summary: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    error_message: str


class AnalysisRunDetail(AnalysisRunOut):
    product_name: str = ""
    findings: List[FindingOut] = Field(default_factory=list)
    claims_count: int = 0
    sources_count: int = 0


class OverviewStats(BaseModel):
    products_total: int = 0
    findings_open: int = 0
    findings_total: int = 0
    sources_total: int = 0
    reviews_total: int = 0
    runs_total: int = 0
    findings_by_severity: Dict[str, int] = Field(default_factory=dict)
    findings_by_type: Dict[str, int] = Field(default_factory=dict)
    findings_by_status: Dict[str, int] = Field(default_factory=dict)
    recent_runs: List[AnalysisRunOut] = Field(default_factory=list)
    demo_products: int = 0
