"""Формулировки находок: без дублей значений и без точки внутри кавычек."""

from __future__ import annotations

from app.rules.engine import _quote, _value_note


def test_quote_moves_trailing_period_outside_the_quotes():
    assert _quote("Время работы без подзарядки — 30 часов.") == "«Время работы без подзарядки — 30 часов»"
    assert _quote("  Вес   250  граммов!  ") == "«Вес 250 граммов»"


def test_quote_never_leaves_period_before_closing_quote():
    for raw in ("Текст.", "Текст...", "Текст .", "Текст;"):
        assert ".»" not in _quote(raw)
        assert ";»" not in _quote(raw)


def test_value_note_is_skipped_when_value_is_already_in_the_quote():
    assert _value_note("Время работы без подзарядки — 30 часов.", "30 часов") == ""
    assert _value_note("Батарея держится 20 часов, а не 48", "20 часов") == ""


def test_value_note_is_added_when_value_is_missing_from_the_quote():
    assert _value_note("Работает очень долго", "30 часов") == " (30 часов)"


def test_resulting_sentence_has_no_duplicate_value():
    text = "Время работы без подзарядки — 30 часов."
    sentence = "В описании товара: " + _quote(text) + _value_note(text, "30 часов") + "."
    assert sentence == "В описании товара: «Время работы без подзарядки — 30 часов»."
    assert sentence.count("30 часов") == 1
