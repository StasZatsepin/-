"""Справочник единиц измерения и их нормализация.

Поддерживается ограниченный набор величин. Величины из разных измерений
никогда не сравниваются между собой (см. `rules.engine`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Базовые единицы по измерению
BASE_UNIT: Dict[str, str] = {
    "time": "second",
    "length": "mm",
    "mass": "g",
    "volume": "ml",
    "charge": "mah",
    "storage": "mb",
    "power": "w",
    "voltage": "v",
    "percent": "percent",
    "count": "pcs",
    "level": "db",
    "temperature": "c",
}


@dataclass(frozen=True)
class Unit:
    key: str
    dimension: str
    factor: float  # множитель к базовой единице измерения
    aliases: Tuple[str, ...]


UNITS: Tuple[Unit, ...] = (
    # --- время ---
    Unit("second", "time", 1.0, ("секунда", "секунды", "секунд", "сек", "с", "s", "sec")),
    Unit("minute", "time", 60.0, ("минута", "минуты", "минут", "мин", "min")),
    Unit("hour", "time", 3600.0, ("часов", "часа", "час", "ч", "h", "hr", "hours", "hour")),
    Unit("day", "time", 86400.0, ("суток", "сутки", "день", "дня", "дней", "day", "days")),
    Unit("week", "time", 604800.0, ("недель", "недели", "неделю", "неделя", "week", "weeks")),
    Unit("month", "time", 2592000.0, ("месяцев", "месяца", "месяц", "мес", "month", "months")),
    Unit("year", "time", 31536000.0, ("лет", "года", "год", "year", "years")),
    # --- длина ---
    Unit("mm", "length", 1.0, ("мм", "millimeter", "millimetre")),
    Unit("cm", "length", 10.0, ("см", "сантиметр", "сантиметров", "cm")),
    Unit("m", "length", 1000.0, ("метр", "метров", "м", "m")),
    Unit("inch", "length", 25.4, ("дюйм", "дюйма", "дюймов", "дюймы", "inch", "inches", '"')),
    # --- масса ---
    Unit("mg", "mass", 0.001, ("мг", "миллиграмм", "mg")),
    Unit("g", "mass", 1.0, ("грамм", "граммов", "гр", "г", "g", "gram")),
    Unit("kg", "mass", 1000.0, ("кг", "килограмм", "килограммов", "kg")),
    # --- объём ---
    Unit("ml", "volume", 1.0, ("мл", "миллилитр", "миллилитров", "ml")),
    Unit("l", "volume", 1000.0, ("литр", "литра", "литров", "л", "l")),
    # --- заряд ---
    Unit("mah", "charge", 1.0, ("мач", "мАч", "mah")),
    Unit("ah", "charge", 1000.0, ("ач", "Ач", "ah")),
    # --- память ---
    Unit("mb", "storage", 1.0, ("мб", "mb")),
    Unit("gb", "storage", 1024.0, ("гб", "gb")),
    Unit("tb", "storage", 1024.0 * 1024, ("тб", "tb")),
    # --- прочие ---
    Unit("w", "power", 1.0, ("ватт", "вт", "w")),
    Unit("v", "voltage", 1.0, ("вольт", "в", "v")),
    Unit("percent", "percent", 1.0, ("%", "процент", "процентов", "процента")),
    Unit("pcs", "count", 1.0, ("шт", "штук", "штука", "pcs", "pc")),
    Unit("db", "level", 1.0, ("дб", "децибел", "db")),
    Unit("c", "temperature", 1.0, ("°c", "℃", "градусов цельсия", "c")),
)

_ALIAS_INDEX: Dict[str, Unit] = {}
for _unit in UNITS:
    # Канонический ключ единицы тоже является допустимым псевдонимом.
    _ALIAS_INDEX.setdefault(_unit.key.lower(), _unit)
    for _alias in _unit.aliases:
        _ALIAS_INDEX.setdefault(_alias.lower(), _unit)


def find_unit(alias: str) -> Optional[Unit]:
    """Возвращает единицу по псевдониму или None."""
    return _ALIAS_INDEX.get(alias.strip().lower())


def unit_by_key(key: str) -> Optional[Unit]:
    return _ALIAS_INDEX.get(key.strip().lower())


def to_base(value: float, unit_key: str) -> Tuple[float, str]:
    """Приводит значение к базовой единице измерения."""
    unit = unit_by_key(unit_key)
    if unit is None:
        raise ValueError(f"Неизвестная единица измерения: {unit_key}")
    return value * unit.factor, BASE_UNIT[unit.dimension]


def convert(value: float, from_key: str, to_key: str) -> Optional[float]:
    """Переводит значение между единицами одного измерения."""
    source = unit_by_key(from_key)
    target = unit_by_key(to_key)
    if source is None or target is None:
        return None
    if source.dimension != target.dimension:
        return None
    base_value, _ = to_base(value, source.key)
    return base_value / target.factor


def dimensions() -> List[str]:
    return sorted({unit.dimension for unit in UNITS})


def unit_alias_pattern() -> str:
    """Регулярное выражение для поиска единиц в свободном тексте.

    Однобуквенные псевдонимы («м», «г», «в», «с», «ч») требуют, чтобы перед
    ними не было буквы/цифры, а после — не было буквы. Это снижает число
    ложных срабатываний на обычных словах.
    """
    aliases = sorted({alias for unit in UNITS for alias in unit.aliases}, key=len, reverse=True)
    long_aliases = [re.escape(alias) for alias in aliases if len(alias) >= 2]
    short_aliases = [re.escape(alias) for alias in aliases if len(alias) == 1]

    parts: List[str] = []
    if long_aliases:
        parts.append("(?:" + "|".join(long_aliases) + ")")
    if short_aliases:
        parts.append(
            r"(?<![0-9A-Za-zА-Яа-яЁё])(?:" + "|".join(short_aliases) + r")(?![A-Za-zА-Яа-яЁё])"
        )
    return "|".join(parts)
