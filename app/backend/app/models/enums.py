"""Перечисления доменной модели."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Строковый enum: значение сериализуется как обычная строка."""

    def __str__(self) -> str:  # pragma: no cover - удобство вывода
        return str(self.value)


class Marketplace(StrEnum):
    OZON = "ozon"
    WILDBERRIES = "wildberries"
    DEMO = "demo"
    OTHER = "other"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class SourceType(StrEnum):
    PRODUCT_DESCRIPTION = "product_description"
    ATTRIBUTE_SHEET = "attribute_sheet"
    TECHNICAL_DOCUMENT = "technical_document"
    REVIEW_EXPORT = "review_export"
    USER_NOTE = "user_note"
    OTHER = "other"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    NEEDS_OCR = "needs_ocr"
    EMPTY = "empty"
    FAILED = "failed"


class ExtractionMethod(StrEnum):
    MANUAL = "manual"
    RULE_BASED = "rule_based"
    MOCK_PROVIDER = "mock_provider"
    LLM_PROVIDER = "llm_provider"
    SEEDED = "seeded"


class ClaimType(StrEnum):
    NUMERIC_PERFORMANCE = "numeric_performance"
    DIMENSION_OR_WEIGHT = "dimension_or_weight"
    COMPATIBILITY = "compatibility"
    MATERIAL_OR_COMPOSITION = "material_or_composition"
    CERTIFICATION_OR_COMPLIANCE = "certification_or_compliance"
    WARRANTY_OR_SERVICE = "warranty_or_service"
    SAFETY_OR_HEALTH = "safety_or_health"
    SUBJECTIVE_MARKETING = "subjective_marketing"
    OTHER = "other"


class EvidenceType(StrEnum):
    ATTRIBUTE_VALUE = "attribute_value"
    DOCUMENT_STATEMENT = "document_statement"
    REVIEW_STATEMENT = "review_statement"
    DESCRIPTION_TEXT = "description_text"
    USER_NOTE = "user_note"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXTUALIZES = "contextualizes"
    UNRELATED = "unrelated"
    UNCERTAIN = "uncertain"


class FindingType(StrEnum):
    DIRECT_CONFLICT = "direct_conflict"
    MISSING_EVIDENCE = "missing_evidence"
    REVIEW_SIGNAL = "review_signal"
    AMBIGUOUS_CLAIM = "ambiguous_claim"
    DOCUMENT_SCOPE_MISMATCH = "document_scope_mismatch"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    NOT_AN_ISSUE = "not_an_issue"
    INSUFFICIENT_DATA = "insufficient_data"


class ConfidenceStatus(StrEnum):
    SUPPORTED = "supported_by_provided_source"
    CONFLICTING = "conflicting_sources"
    INSUFFICIENT = "insufficient_evidence"
    SUBJECTIVE = "subjective_or_not_testable"
    NEEDS_REVIEW = "needs_human_review"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
