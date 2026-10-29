"""Интерфейс провайдера анализа.

Приложение полностью работоспособно без внешнего ИИ: по умолчанию
используется `MockAnalysisProvider`, который не обращается к сети.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ClaimCandidate:
    """Утверждение, передаваемое провайдеру на классификацию."""

    id: str
    text: str
    claim_type: str
    source_excerpt: str
    source_name: str
    source_type: str
    source_id: Optional[str] = None


@dataclass
class ClaimSuggestion:
    """Предложение провайдера по классификации утверждения."""

    claim_id: str
    claim_type: str
    confidence_label: str
    rationale: str
    provider: str = ""
    model_version: str = ""


@dataclass
class FindingSuggestion:
    """Предложение провайдера по находке (используется только LLM-провайдерами)."""

    finding_type: str
    severity: str
    title: str
    description: str
    claim_id: Optional[str] = None
    excerpts: List[str] = field(default_factory=list)
    limitations: str = ""
    recommended_action: str = ""


@dataclass
class ProviderResult:
    """Результат работы провайдера."""

    provider: str
    model_version: str
    status: str = "ok"
    message: str = ""
    claim_suggestions: List[ClaimSuggestion] = field(default_factory=list)
    finding_suggestions: List[FindingSuggestion] = field(default_factory=list)
    used_external_service: bool = False
    claims_rejected: int = 0
    claims_sent: int = 0


@dataclass
class ProviderStatus:
    """Состояние провайдера для страницы настроек."""

    provider: str
    model_version: str
    available: bool
    message: str
    requires_api_key: bool = False
    external_data_transfer: bool = False
    fallback_provider: str = "mock"


@dataclass
class ExtractedClaim:
    """Утверждение, извлечённое моделью из текста источника.

    `source_excerpt` обязателен: без дословного фрагмента источника
    утверждение не сохраняется.
    """

    text: str
    claim_type: str
    source_excerpt: str
    confidence_label: str = "needs_human_review"
    rationale: str = ""


@dataclass
class FindingContext:
    """Контекст находки, передаваемый модели для объяснения."""

    rule_id: str
    title: str
    description: str
    evidence_excerpts: List[str] = field(default_factory=list)
    limitations: str = ""
    key: str = ""


@dataclass
class ExplanationSuggestion:
    """Пояснение модели к находке (не меняет тип и серьёзность)."""

    rule_id: str
    explanation: str
    quotes: List[str] = field(default_factory=list)


class ClaimAnalysisProvider(abc.ABC):
    """Базовый интерфейс анализа утверждений."""

    name: str = "base"
    uses_external_service: bool = False
    requires_api_key: bool = False

    @abc.abstractmethod
    def status(self) -> ProviderStatus:
        """Возвращает текущее состояние провайдера."""

    @abc.abstractmethod
    def classify_claims(
        self, claims: List[ClaimCandidate], context: Dict[str, str]
    ) -> ProviderResult:
        """Классифицирует утверждения и при необходимости предлагает находки."""

    def extract_claims(
        self, text: str, context: Dict[str, str]
    ) -> List[ExtractedClaim]:
        """Извлекает кандидаты в утверждения из текста источника.

        Необязательный метод: провайдеры без внешней модели оставляют
        извлечение утверждений детерминированному разбору.
        """
        return []

    def explain_findings(
        self, findings: List[FindingContext], context: Dict[str, str]
    ) -> List[ExplanationSuggestion]:
        """Формулирует пояснения к находкам.

        Необязательный метод. Пояснение не меняет тип находки и её
        серьёзность: они определяются детерминированными правилами.
        """
        return []

    def describe(self) -> str:  # pragma: no cover - текстовое описание
        return f"{self.name}"
