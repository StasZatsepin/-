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

    def describe(self) -> str:  # pragma: no cover - текстовое описание
        return f"{self.name}"
