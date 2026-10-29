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


class TestRussianAttributes:
    """Тесты поддержки русских названий характеристик."""

    def test_russian_time_attributes(self):
        q = parse_attribute("время работы", 48)
        assert q is not None
        assert q.dimension == "time"
        assert q.unit_key == "hour"
        assert q.value == 48.0

    def test_russian_autonomous_time_attributes(self):
        q = parse_attribute("время автономной работы", 24)
        assert q is not None
        assert q.dimension == "time"
        assert q.unit_key == "hour"

    def test_russian_work_time_attributes(self):
        q = parse_attribute("рабочее время", 8)
        assert q is not None
        assert q.dimension == "time"
        assert q.unit_key == "hour"

    def test_russian_battery_capacity(self):
        q = parse_attribute("ёмкость аккумулятора", 5000)
        assert q is not None
        assert q.dimension == "charge"
        assert q.unit_key == "mah"
        assert q.value == 5000.0

    def test_russian_battery_capacity_yo(self):
        q = parse_attribute("емкость аккумулятора", 5000)
        assert q is not None
        assert q.dimension == "charge"
        assert q.unit_key == "mah"

    def test_russian_capacity(self):
        q = parse_attribute("емкость", 3000)
        assert q is not None
        assert q.dimension == "charge"
        assert q.unit_key == "mah"

    def test_russian_mass(self):
        q = parse_attribute("масса", 0.25)
        assert q is not None
        assert q.dimension == "mass"
        assert q.unit_key == "kg"

    def test_russian_weight(self):
        q = parse_attribute("вес", 250)
        assert q is not None
        assert q.dimension == "mass"
        assert q.unit_key == "kg"

    def test_russian_power(self):
        q = parse_attribute("мощность", 65)
        assert q is not None
        assert q.dimension == "power"
        assert q.unit_key == "w"

    def test_russian_length_attributes(self):
        q = parse_attribute("ширина", 30)
        assert q is not None
        assert q.dimension == "length"
        assert q.unit_key == "cm"

        q = parse_attribute("высота", 15)
        assert q is not None
        assert q.dimension == "length"
        assert q.unit_key == "cm"

        q = parse_attribute("глубина", 10)
        assert q is not None
        assert q.dimension == "length"
        assert q.unit_key == "cm"

    def test_russian_diagonal(self):
        q = parse_attribute("диагональ", 15.6)
        assert q is not None
        assert q.dimension == "length"
        assert q.unit_key == "cm"

    def test_russian_volume(self):
        q = parse_attribute("объём", 500)
        assert q is not None
        assert q.dimension == "volume"
        assert q.unit_key == "ml"

        q = parse_attribute("объем", 330)
        assert q is not None
        assert q.dimension == "volume"
        assert q.unit_key == "ml"

    def test_russian_voltage(self):
        q = parse_attribute("напряжение", 5)
        assert q is not None
        assert q.dimension == "voltage"
        assert q.unit_key == "v"

    def test_russian_warranty(self):
        q = parse_attribute("гарантия", 12)
        assert q is not None
        assert q.dimension == "time"
        assert q.unit_key == "month"

    def test_russian_non_numeric_skipped(self):
        assert parse_attribute("время работы", "48 часов") is None
        assert parse_attribute("масса", "пластик") is None

    def test_russian_unknown_attribute_skipped(self):
        assert parse_attribute("цвет", "красный") is None
        assert parse_attribute("материал", "пластик") is None

    def test_english_and_russian_together(self):
        parsed, skipped = parse_attributes({
            "battery_life_hours": 30,
            "время работы": 48,
            "вес": 250,
            "цвет": "черный",
        })
        assert len(parsed) == 3
        assert set(skipped) == {"цвет"}
