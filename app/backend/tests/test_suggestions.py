"""Подсказки «что исправить»: строятся из текста находки и не выдумывают фактов."""

from __future__ import annotations

from app.rules.suggestions import suggest_fix

NUMERIC = (
    "В описании товара указано: «Время работы без подзарядки — до 48 часов» (Описание товара).\n"
    "В таблице характеристик: Время работы = 30 ч.\n"
    "Расхождение: 18 ч (значение обещания выше)."
)


def test_numeric_conflict_names_both_values_and_does_not_pick_a_side():
    result = suggest_fix("numeric.attribute_comparison", NUMERIC)
    assert result is not None
    assert "до 48 часов" in result["text"]
    assert "30 ч" in result["text"]
    assert "Если верна таблица" in result["text"] and "Если верно обещание" in result["text"]
    assert result["copy_text"] == "Время работы — 30 ч"


def test_ambiguous_promise_points_at_the_marker_word():
    description = "В тексте найдена формулировка «идеально»: «Идеально подходит для поездок»."
    result = suggest_fix("claims.ambiguous_promise", description)
    assert result is not None and "«идеально»" in result["text"]


def test_missing_evidence_variants():
    description = "В описании товара есть утверждение: «Полностью безопасен для детей»."
    safety = suggest_fix("evidence.missing_safety_confirmation", description)
    plain = suggest_fix("evidence.missing_confirmation", description)
    assert safety and "сертификат" in safety["text"]
    assert plain and "сертификат" not in plain["text"]


def test_review_mismatch_has_a_generic_hint():
    assert suggest_fix("reviews.numeric_mismatch", "что угодно")["text"]


def test_unknown_rule_or_unparsable_text_gives_none():
    assert suggest_fix("provider.suggestion", NUMERIC) is None
    assert suggest_fix("numeric.attribute_comparison", "текст без разбора") is None
    assert suggest_fix("", "") is None
