"""Unit-тесты нормализации единиц и извлечения чисел."""

from __future__ import annotations

from app.rules.attributes import parse_attribute, parse_attributes
from app.rules.numeric import extract_numeric_statements
from app.rules.units import convert, find_unit


class TestUnits:
    def test_known_aliases_resolve(self):
        assert find_unit("часов").dimension == "time"
        assert find_unit("кг").dimension == "mass"
        assert find_unit("мАч").dimension == "charge"
        assert find_unit("GB").dimension == "storage"

    def test_unknown_alias_returns_none(self):
        assert find_unit("кгз") is None

    def test_conversion_between_compatible_units(self):
        assert convert(2, "hour", "minute") == 120
        assert convert(1, "kg", "g") == 1000
        assert convert(60, "minute", "hour") == 1

    def test_conversion_between_incompatible_units_returns_none(self):
        assert convert(1, "hour", "kg") is None

    def test_single_letter_unit_does_not_match_inside_words(self):
        # «м» внутри слова не должно распознаваться как метр.
        statements = extract_numeric_statements("Модель рассчитана на 5 пользователей.")
        assert statements == []


class TestNumericExtraction:
    def test_simple_value_with_unit(self):
        statements = extract_numeric_statements("Вес наушников 250 граммов.")
        assert len(statements) == 1
        assert statements[0].value == 250
        assert statements[0].dimension == "mass"
        assert statements[0].comparator == "exact"

    def test_upper_bound_comparator(self):
        statements = extract_numeric_statements("До 48 часов работы без подзарядки.")
        assert statements[0].value == 48
        assert statements[0].comparator == "up_to"

    def test_lower_bound_comparator(self):
        statements = extract_numeric_statements("Гарантия от 12 месяцев.")
        assert statements[0].comparator == "from"

    def test_range(self):
        statements = extract_numeric_statements("Время работы 20-48 часов.")
        assert statements[0].comparator == "range"
        assert statements[0].lower_bound == 20
        assert statements[0].value == 48

    def test_decimal_comma(self):
        statements = extract_numeric_statements("Масса 0,25 кг.")
        assert statements[0].value == 0.25
        assert statements[0].dimension == "mass"

    def test_empty_text(self):
        assert extract_numeric_statements("") == []

    def test_text_without_units(self):
        assert extract_numeric_statements("Просто описание без чисел.") == []

    def test_measurement_conditions_are_detected(self):
        statements = extract_numeric_statements(
            "При полной зарядке время работы составляет 30 часов."
        )
        assert statements[0].has_qualifier is True


class TestAttributes:
    def test_attribute_with_explicit_unit_suffix(self):
        quantity = parse_attribute("battery_life_hours", 30)
        assert quantity is not None
        assert quantity.dimension == "time"
        assert quantity.unit_key == "hour"

    def test_attribute_with_unit_in_key(self):
        quantity = parse_attribute("weight_g", 250)
        assert quantity is not None
        assert quantity.dimension == "mass"
        assert quantity.unit_key == "g"

    def test_attribute_by_key_word(self):
        quantity = parse_attribute("power", 65)
        assert quantity is not None
        assert quantity.dimension == "power"

    def test_non_numeric_attribute_skipped(self):
        assert parse_attribute("material", "пластик") is None

    def test_unknown_attribute_skipped(self):
        assert parse_attribute("model", "TEST-1") is None

    def test_price_attribute_skipped(self):
        assert parse_attribute("price", 1990) is None

    def test_parse_attributes_reports_skipped(self):
        parsed, skipped = parse_attributes({"weight_g": 250, "model": "X", "color": "red"})
        assert len(parsed) == 1
        assert set(skipped) == {"model", "color"}
