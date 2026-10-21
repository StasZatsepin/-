"""Регрессия качества классификации на фиксированном наборе.

Набор один и тот же для всех провайдеров, поэтому числа можно сравнивать
между версиями и между провайдерами (scripts/compare_providers.py).
"""

from __future__ import annotations

from app.benchmarks import benchmark_metadata, load_benchmark
from app.models.enums import ClaimType
from app.providers.base import ClaimCandidate
from app.providers.mock import MockAnalysisProvider

# Порог совпадения типов для локальной эвристики. Снижение ниже 0.6 означает
# регрессию правил и требует разбора.
MOCK_TYPE_ACCURACY_FLOOR = 0.6


def _candidates():
    return [
        ClaimCandidate(
            id=case.id,
            text=case.text,
            claim_type=ClaimType.OTHER.value,
            source_excerpt=case.text,
            source_name="Фиксированный набор",
            source_type="user_note",
        )
        for case in load_benchmark()
    ]


def test_benchmark_is_not_empty():
    cases = load_benchmark()
    assert len(cases) >= 10
    assert benchmark_metadata()["version"]


def test_mock_provider_accuracy_is_above_floor():
    cases = load_benchmark()
    result = MockAnalysisProvider().classify_claims(_candidates(), {})
    suggestions = {item.claim_id: item for item in result.claim_suggestions}

    hits = sum(
        1
        for case in cases
        if suggestions.get(case.id)
        and suggestions[case.id].claim_type == case.expected_type
    )
    accuracy = hits / len(cases)
    assert accuracy >= MOCK_TYPE_ACCURACY_FLOOR, (
        f"Качество локальной эвристики упало: {accuracy:.1%} < {MOCK_TYPE_ACCURACY_FLOOR:.0%}"
    )


def test_mock_provider_answers_every_case():
    cases = load_benchmark()
    result = MockAnalysisProvider().classify_claims(_candidates(), {})
    assert len(result.claim_suggestions) == len(cases)


def test_benchmark_covers_all_claim_types():
    cases = load_benchmark()
    covered = {case.expected_type for case in cases}
    expected = {
        item.value
        for item in ClaimType
        if item.value
        in {
            "numeric_performance",
            "dimension_or_weight",
            "compatibility",
            "material_or_composition",
            "certification_or_compliance",
            "warranty_or_service",
            "safety_or_health",
            "subjective_marketing",
        }
    }
    assert expected <= covered
