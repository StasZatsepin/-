"""Экспорт моделей домена для Alembic и импортов по коротким путям."""

from app.db.base import Base
from app.models.analysis_run import AnalysisRun
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.enums import (
    AnalysisStatus,
    ClaimType,
    ConfidenceStatus,
    EvidenceRelation,
    EvidenceType,
    ExtractionMethod,
    ExtractionStatus,
    FindingStatus,
    FindingType,
    Marketplace,
    Severity,
    SourceType,
    UserRole,
)
from app.models.finding import Finding
from app.models.product import Product
from app.models.review_action import ReviewAction
from app.models.source import Source
from app.models.workspace import User, Workspace

__all__ = [
    "Base",
    "AnalysisRun",
    "AnalysisStatus",
    "Claim",
    "ClaimType",
    "ConfidenceStatus",
    "Evidence",
    "EvidenceRelation",
    "EvidenceType",
    "ExtractionMethod",
    "ExtractionStatus",
    "Finding",
    "FindingStatus",
    "FindingType",
    "Marketplace",
    "Product",
    "ReviewAction",
    "Severity",
    "Source",
    "SourceType",
    "User",
    "UserRole",
    "Workspace",
]
