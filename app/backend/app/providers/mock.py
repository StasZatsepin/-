"""Провайдер без внешнего ИИ: детерминированная эвристика.

Используется по умолчанию и как fallback, если внешний провайдер недоступен.
Никаких сетевых запросов не выполняет.
"""

from __future__ import annotations

from typing import Dict, List

from app.models.enums import ClaimType
from app.providers.base import (
    ClaimAnalysisProvider,
    ClaimCandidate,
    ClaimSuggestion,
    ProviderResult,
    ProviderStatus,
)
from app.rules.patterns import classify_claim_type, is_ambiguous_claim

# Утверждения, которые нельзя классифицировать автоматически по ключевым словам.
_NEEDS_REVIEW = "Требуется проверка человеком: тип не распознан автоматически."


class MockAnalysisProvider(ClaimAnalysisProvider):
    """Локальный провайдер без внешних зависимостей."""

    name = "mock"
    uses_external_service = False
    requires_api_key = False

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            provider=self.name,
            model_version="mock-rules-1",
            available=True,
            message=(
                "Работает встроенная эвристическая классификация. "
                "Внешние сервисы не используются, данные никуда не передаются."
            ),
            requires_api_key=False,
            external_data_transfer=False,
            fallback_provider="mock",
        )

    def classify_claims(
        self, claims: List[ClaimCandidate], context: Dict[str, str]
    ) -> ProviderResult:
        suggestions: List[ClaimSuggestion] = []
        for claim in claims:
            if claim.claim_type != ClaimType.OTHER.value:
                continue
            detected = classify_claim_type(claim.text)
            if detected == ClaimType.OTHER:
                suggestions.append(
                    ClaimSuggestion(
                        claim_id=claim.id,
                        claim_type=ClaimType.OTHER.value,
                        confidence_label="needs_human_review",
                        rationale=_NEEDS_REVIEW,
                        provider=self.name,
                        model_version="mock-rules-1",
                    )
                )
                continue

            if detected == ClaimType.SUBJECTIVE_MARKETING or is_ambiguous_claim(claim.text):
                rationale = "Формулировка оценочная или абсолютная, объективно не проверяется."
                confidence = "subjective_or_not_testable"
            else:
                rationale = "Тип определён по ключевым словам в тексте утверждения."
                confidence = "heuristic_classification"

            suggestions.append(
                ClaimSuggestion(
                    claim_id=claim.id,
                    claim_type=detected.value,
                    confidence_label=confidence,
                    rationale=rationale,
                    provider=self.name,
                    model_version="mock-rules-1",
                )
            )

        return ProviderResult(
            provider=self.name,
            model_version="mock-rules-1",
            status="ok",
            message="Классификация выполнена локальной эвристикой.",
            claim_suggestions=suggestions,
            finding_suggestions=[],
            used_external_service=False,
        )
