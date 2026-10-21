"""Извлечение числовых утверждений из свободного текста.

Модуль полностью детерминирован: результат зависит только от входного текста.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.rules.units import Unit, find_unit, unit_alias_pattern, unit_by_key

_NUMBER = r"\d+(?:[.,]\d+)?"
_UNIT_PATTERN = unit_alias_pattern()

# Диапазон: "20-48 часов", "от 20 до 48 часов"
_RANGE_RE = re.compile(
    rf"(?P<low>{_NUMBER})\s*(?:-|–|—|до)\s*(?P<high>{_NUMBER})\s*(?P<unit>{_UNIT_PATTERN})",
    re.IGNORECASE,
)

# Одиночное число с единицей: "48 часов", "30 ч", "2.5 кг"
_SINGLE_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*(?P<unit>{_UNIT_PATTERN})",
    re.IGNORECASE,
)

# Слово-уточнение перед числом
_COMPARATORS = (
    ("up_to", ("до", "не более", "не больше", "максимум", "максимально", "up to")),
    ("from", ("от", "не менее", "минимум", "минимально", "начиная с", "from")),
    ("over", ("более", "больше", "свыше", "выше", "over")),
    ("under", ("менее", "меньше", "ниже", "under")),
    ("about", ("около", "примерно", "порядка", "≈", "~")),
)

# Границы слова: «от» внутри «работы» не должно считаться словом-уточнением.
_WORD_BOUNDARY = r"(?<![А-Яа-яЁёA-Za-z0-9])(?![А-Яа-яЁёA-Za-z])"


def _compile_marker(marker: str) -> re.Pattern:
    pattern = rf"(?<![А-Яа-яЁёA-Za-z0-9]){re.escape(marker)}(?![А-Яа-яЁёA-Za-z])"
    return re.compile(pattern, re.IGNORECASE)


_COMPARATOR_PATTERNS = tuple(
    (name, _compile_marker(marker))
    for name, markers in _COMPARATORS
    for marker in markers
)

# Условия измерения, из-за которых значения могут быть несопоставимы
_QUALIFIER_MARKERS = (
    "в режиме",
    "при полной зарядке",
    "при температуре",
    "в лабораторных условиях",
    "в тестовых условиях",
    "по результатам испытаний",
    "при использовании",
    "в среднем",
    "при стандартных условиях",
    "с учетом",
    "в зависимости от",
    "в идеальных условиях",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")


@dataclass
class NumericStatement:
    """Числовое утверждение, извлечённое из текста."""

    value: float
    unit_key: str
    dimension: str
    comparator: str = "exact"
    lower_bound: Optional[float] = None
    raw_text: str = ""
    sentence: str = ""
    start: int = 0
    end: int = 0
    qualifier: str = ""
    context: str = ""

    @property
    def has_conditions(self) -> bool:
        return bool(self.qualifier)

    @property
    def has_qualifier(self) -> bool:
        return bool(self.qualifier)

    def describe(self) -> str:
        prefix = {
            "exact": "",
            "up_to": "до ",
            "from": "от ",
            "over": "более ",
            "under": "менее ",
            "about": "около ",
            "range": "в диапазоне ",
        }.get(self.comparator, "")
        if self.comparator == "range" and self.lower_bound is not None:
            return f"{prefix}{self.lower_bound:g}–{self.value:g} {unit_display(self.unit_key)}"
        return f"{prefix}{self.value:g} {unit_display(self.unit_key)}"


@dataclass
class _Sentence:
    text: str
    offset: int


def split_sentences(text: str) -> List[_Sentence]:
    """Делит текст на предложения с сохранением смещений в исходном тексте."""
    sentences: List[_Sentence] = []
    cursor = 0
    for match in _SENTENCE_SPLIT.finditer(text):
        chunk = text[cursor : match.start()]
        stripped = chunk.strip()
        if stripped:
            sentences.append(_Sentence(text=stripped, offset=cursor + chunk.index(stripped)))
        cursor = match.end()
    tail = text[cursor:]
    stripped = tail.strip()
    if stripped:
        sentences.append(_Sentence(text=stripped, offset=cursor + tail.index(stripped)))
    return sentences


def _detect_comparator(context: str) -> str:
    """Определяет слово-уточнение перед числом (ближайшее к числу)."""
    best: Optional[tuple] = None
    for comparator, pattern in _COMPARATOR_PATTERNS:
        match = pattern.search(context)
        if match is None:
            continue
        distance = len(context) - match.end()
        if best is None or distance < best[0]:
            best = (distance, comparator)
    return best[1] if best else "exact"


def _detect_qualifier(sentence: str) -> str:
    lowered = sentence.lower()
    for marker in _QUALIFIER_MARKERS:
        if marker in lowered:
            return marker
    return ""


def find_qualifier(text: str) -> str:
    """Ищет в тексте указание на условия измерения (публичная обёртка)."""
    return _detect_qualifier(text or "")


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def extract_numeric_statements(text: str) -> List[NumericStatement]:
    """Извлекает числовые утверждения с единицами измерения из текста."""
    if not text:
        return []

    statements: List[NumericStatement] = []

    for sentence in split_sentences(text):
        raw_matches: List[tuple] = []
        covered: List[tuple] = []

        for match in _RANGE_RE.finditer(sentence.text):
            unit = find_unit(match.group("unit"))
            if unit is None:
                continue
            raw_matches.append(
                (
                    match.start(),
                    match.end(),
                    "range",
                    {
                        "value": _to_float(match.group("high")),
                        "lower_bound": _to_float(match.group("low")),
                        "unit": unit,
                        "comparator": "range",
                    },
                )
            )
            covered.append((match.start(), match.end()))

        for match in _SINGLE_RE.finditer(sentence.text):
            if any(start <= match.start() < end for start, end in covered):
                continue
            unit = find_unit(match.group("unit"))
            if unit is None:
                continue
            raw_matches.append(
                (
                    match.start(),
                    match.end(),
                    "single",
                    {
                        "value": _to_float(match.group("value")),
                        "lower_bound": None,
                        "unit": unit,
                        "comparator": None,
                    },
                )
            )

        raw_matches.sort(key=lambda item: item[0])

        for index, (start, end, _kind, data) in enumerate(raw_matches):
            # Контекст числа — текст между соседними числами предложения.
            # Так «гарантия 24 месяца» и «ответ в течение 1 часа» не смешиваются.
            previous_end = raw_matches[index - 1][1] if index > 0 else 0
            next_start = raw_matches[index + 1][0] if index + 1 < len(raw_matches) else len(sentence.text)
            context = sentence.text[previous_end:next_start]

            comparator = data["comparator"]
            if comparator is None:
                offset = start - previous_end
                comparator = _detect_comparator(context[:offset][-40:])

            statements.append(
                NumericStatement(
                    value=data["value"],
                    unit_key=data["unit"].key,
                    dimension=data["unit"].dimension,
                    comparator=comparator,
                    lower_bound=data["lower_bound"],
                    raw_text=sentence.text[start:end],
                    sentence=sentence.text,
                    start=sentence.offset + start,
                    end=sentence.offset + end,
                    qualifier=_detect_qualifier(sentence.text),
                    context=context.strip(),
                )
            )

    return statements


def find_unit_for_text(text: str) -> Optional[Unit]:
    """Первый найденный псевдоним единицы в тексте (для справки)."""
    match = _SINGLE_RE.search(text or "")
    if not match:
        return None
    return find_unit(match.group("unit"))


def unit_display(unit_key: str) -> str:
    """Человекочитаемое название единицы измерения."""
    unit = unit_by_key(unit_key)
    if unit is None:
        return unit_key
    for alias in unit.aliases:
        if alias and not alias.isascii():
            return alias
    return unit.key


CONTEXT_WINDOW = 60
