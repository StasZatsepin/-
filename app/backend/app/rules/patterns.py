"""Классификация утверждений по ключевым словам и поиск размытых обещаний.

Все правила детерминированы и не требуют внешней модели.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from app.models.enums import ClaimType

# --- ключевые слова по типам утверждений -----------------------------------

CLAIM_KEYWORDS: Dict[ClaimType, Tuple[str, ...]] = {
    ClaimType.NUMERIC_PERFORMANCE: (
        "час",
        "минут",
        "дней",
        "месяц",
        "лет",
        "ёмк",
        "емк",
        "мощност",
        "производительност",
        "скорост",
        "заряд",
        "автономност",
        "время работы",
        "наработк",
    ),
    ClaimType.DIMENSION_OR_WEIGHT: (
        "размер",
        "габарит",
        "вес",
        "масса",
        "длина",
        "ширина",
        "высота",
        "толщин",
        "диаметр",
        "объем",
        "объём",
        "см",
        "мм",
        "кг",
    ),
    ClaimType.COMPATIBILITY: (
        "совмест",
        "совместим",
        "подходит для",
        "подойдет для",
        "подойдёт для",
        "работает с",
        "аналог",
        "заменяет",
        "для iphone",
        "для samsung",
        "для android",
        "для windows",
        "тип соединения",
        "разъём",
        "разъем",
    ),
    ClaimType.MATERIAL_OR_COMPOSITION: (
        "материал",
        "состав",
        "изготовлен из",
        "изготовлена из",
        "сделан из",
        "сделана из",
        "хлопок",
        "полиэстер",
        "нержавеющая сталь",
        "алюминий",
        "пластик",
        "силикон",
        "дерево",
        "%",
    ),
    ClaimType.CERTIFICATION_OR_COMPLIANCE: (
        "сертифиц",
        "сертификат",
        "деклараци",
        "соответств",
        "гост",
        "т р тс",
        "тр тс",
        "eac",
        "рст",
        "ce mark",
        "паспорт изделия",
        "руководств",
        "инструкци",
        "охрана труда",
        "питание",
    ),
    ClaimType.WARRANTY_OR_SERVICE: (
        "гаранти",
        "гарантийный срок",
        "обслуживан",
        "техподдержк",
        "техническ",
        "сервис",
        "поддержк",
        "ремонт",
        "замен",
        "срок службы",
    ),
    ClaimType.SAFETY_OR_HEALTH: (
        "безопаст",
        "нет побочн",
        "не вредит",
        "гипоаллерген",
        "лечебн",
        "медицинск",
        "терапевт",
        "противопоказ",
        "беременн",
        "аллерг",
        "нетоксич",
        "сертифицирован",
    ),
    ClaimType.SUBJECTIVE_MARKETING: (
        "лучш",
        "профессиональн",
        "комфортн",
        "премиум",
        "идеальн",
        "уникальн",
        "незаменим",
        "вершина",
        "топов",
        "превосходн",
        "высококачественн",
        "качественный",
    ),
}

# --- размытые/абсолютные обещания -------------------------------------------

AMBIGUOUS_MARKERS: Tuple[str, ...] = (
    "подходит всем",
    "подойдет всем",
    "подойдёт всем",
    "для всех",
    "всем без исключения",
    "полностью безопаст",
    "абсолютно безопаст",
    "полностью безвред",
    "на все случаи",
    "на любой случай",
    "всегда работает",
    "никогда не",
    "гарантированно",
    "100%",
    "100 %",
    "полностью исключает",
    "идеальный",
    "идеально",
    "лучший",
    "лучшая",
    "самое лучшее",
    "№1",
    "номер один",
    "вечный",
    "не подведет",
    "не подведёт",
    "безупречный",
    "максимально эффективный",
    "единственный",
    "никаких",
    "не имеет значения",
)

# Фразы, где «ярлык недобросовестности» был бы недопустим.
PROHIBITED_LABELS: Tuple[str, ...] = (
    "мошенник",
    "мошеннический",
    "недобросовестный",
    "подделка",
    "поддельный",
    "контрафакт",
    "фальшив",
    "обман",
    "вводит в заблуждение",
    "лжец",
)

# --- сигналы из отзывов ------------------------------------------------------

REVIEW_NEGATIVE_MARKERS: Tuple[str, ...] = (
    "не соответствует",
    "не совпадает",
    "отличается от",
    "меньше чем",
    "меньше, чем",
    "короче",
    "не работает",
    "не работало",
    "сломалось",
    "перестал",
    "разочарован",
    "обман",
    "неправда",
    "не соответствует описанию",
    "описанию не соответствует",
    "запах",
    "неудобн",
    "плохое качество",
    "не соответствует заявленному",
    "заявленному не соответствует",
    "не как в описании",
    "разочарова",
    "а не",
    "не хватает",
    "не подтвержда",
    "заявленн",
    "ожидал",
    "недостаточно",
    "закончил",
    "разрядил",
)

REVIEW_POSITIVE_MARKERS: Tuple[str, ...] = (
    "соответствует описанию",
    "всё как в описании",
    "все как описано",
    "хорошее качество",
    "рекомендую",
    "доволен",
    "довольна",
    "отличный товар",
    "полностью соответствует",
    "заказал бы снова",
)

# --- условия применения документа -------------------------------------------

SCOPE_KEYWORDS: Tuple[str, ...] = (
    "модель",
    "артикул",
    "модификация",
    "версия",
    "партия",
    "серия",
    "применимо",
    "рассчитан",
    "предназначен",
    "для изделия",
)


def _compile_marker(marker: str) -> "re.Pattern[str]":
    """Компилирует маркер с границами слова.

    Границы нужны, чтобы короткие слова («от», «до») не срабатывали внутри
    других слов («работы», «подходит»).
    """
    pattern = rf"(?<![А-Яа-яЁёA-Za-z0-9]){re.escape(marker)}(?![А-Яа-яЁёA-Za-z])"
    return re.compile(pattern, re.IGNORECASE)


def _compile_markers(markers) -> tuple:
    return tuple(_compile_marker(marker) for marker in markers)


_AMBIGUOUS_PATTERNS = _compile_markers(AMBIGUOUS_MARKERS)
_PROHIBITED_PATTERNS = _compile_markers(PROHIBITED_LABELS)
_REVIEW_NEGATIVE_PATTERNS = _compile_markers(REVIEW_NEGATIVE_MARKERS)
_REVIEW_POSITIVE_PATTERNS = _compile_markers(REVIEW_POSITIVE_MARKERS)
_SCOPE_PATTERNS = _compile_markers(SCOPE_KEYWORDS)


def _contains_any(text: str, markers) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in markers)


def _matches_any(text: str, patterns) -> bool:
    """Проверяет наличие маркера с учётом границ слова."""
    return any(pattern.search(text or "") for pattern in patterns)


def classify_claim_type(text: str) -> ClaimType:
    """Определяет тип утверждения по ключевым словам.

    Возвращает `ClaimType.OTHER`, если подходящих маркеров не найдено.
    """
    lowered = (text or "").lower()
    if not lowered.strip():
        return ClaimType.OTHER

    scores: Dict[ClaimType, int] = {}
    for claim_type, keywords in CLAIM_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in lowered:
                # Более длинный маркер — более сильный сигнал.
                score += len(keyword)
        if score:
            scores[claim_type] = score

    if not scores:
        return ClaimType.OTHER

    # Безопасность и здоровье имеют приоритет: такие формулировки
    # нельзя проверять автоматически.
    for priority in (
        ClaimType.SAFETY_OR_HEALTH,
        ClaimType.CERTIFICATION_OR_COMPLIANCE,
        ClaimType.WARRANTY_OR_SERVICE,
        ClaimType.COMPATIBILITY,
        ClaimType.MATERIAL_OR_COMPOSITION,
        ClaimType.DIMENSION_OR_WEIGHT,
        ClaimType.NUMERIC_PERFORMANCE,
        ClaimType.SUBJECTIVE_MARKETING,
    ):
        if priority in scores:
            best = max(scores.values())
            if scores[priority] == best:
                return priority
            # Оценка на 2 балла ниже максимума — считаем маркер слишком слабым.
            if best - scores[priority] < 2:
                return priority
    return ClaimType.OTHER


def is_ambiguous_claim(text: str) -> bool:
    """Проверяет наличие абсолютных или непроверяемых обещаний."""
    return _matches_any(text, _AMBIGUOUS_PATTERNS)


def find_ambiguous_marker(text: str) -> Optional[str]:
    """Возвращает найденный маркер неоднозначного обещания (для цитирования)."""
    for pattern in _AMBIGUOUS_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(0)
    return None


def contains_prohibited_label(text: str) -> bool:
    """Проверяет, не содержит ли текст запрещённых ярлыков о продавце."""
    return _matches_any(text, _PROHIBITED_PATTERNS)


def review_sentiment(text: str) -> str:
    """Классифицирует отзыв как negative / positive / mixed / unclear."""
    negative = sum(1 for pattern in _REVIEW_NEGATIVE_PATTERNS if pattern.search(text or ""))
    positive = sum(1 for pattern in _REVIEW_POSITIVE_PATTERNS if pattern.search(text or ""))
    if negative and positive:
        return "mixed"
    if negative:
        return "negative"
    if positive:
        return "positive"
    return "unclear"


def mentions_scope(text: str) -> bool:
    """Есть ли в тексте указание на область применения документа."""
    return _matches_any(text, _SCOPE_PATTERNS)


def normalize_text(text: str) -> str:
    """Приводит текст к нормализованному виду для сравнения."""
    lowered = (text or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", lowered).strip()
