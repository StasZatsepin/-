"""Сопоставление ключей характеристик с измерениями и единицами измерения."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from app.rules.units import Unit, find_unit, unit_by_key

# Токены ключа -> (измерение, единица по умолчанию)
TOKEN_HINTS: Dict[str, Tuple[str, str]] = {
    "battery_life": ("time", "hour"),
    "battery": ("time", "hour"),
    "runtime": ("time", "hour"),
    "work_time": ("time", "hour"),
    "time": ("time", "hour"),
    "charging": ("time", "hour"),
    "warranty": ("time", "month"),
    "service": ("time", "month"),
    "lifetime": ("time", "hour"),
    "weight": ("mass", "kg"),
    "mass": ("mass", "kg"),
    "capacity_weight": ("mass", "kg"),
    "length": ("length", "cm"),
    "width": ("length", "cm"),
    "height": ("length", "cm"),
    "depth": ("length", "cm"),
    "thickness": ("length", "mm"),
    "diameter": ("length", "mm"),
    "dimension": ("length", "cm"),
    "size": ("length", "cm"),
    "power": ("power", "w"),
    "watts": ("power", "w"),
    "voltage": ("voltage", "v"),
    "battery_capacity": ("charge", "mah"),
    "capacity": ("charge", "mah"),
    "storage": ("storage", "gb"),
    "rom": ("storage", "gb"),
    "ram": ("storage", "gb"),
    "memory": ("storage", "gb"),
    "volume": ("volume", "ml"),
    "noise": ("level", "db"),
    "temperature": ("temperature", "c"),
    "count": ("count", "pcs"),
    "quantity": ("count", "pcs"),
    "package": ("count", "pcs"),
}

# Ключи, для которых сравнение невозможно даже при наличии числа.
NON_COMPARABLE_TOKENS = (
    "price",
    "cost",
    "rating",
    "reviews",
    "review_count",
    "sku",
    "id",
    "article",
    "color",
    "цвет",
    "material_name",
)


@dataclass(frozen=True)
class AttributeQuantity:
    """Нормализованная числовая характеристика."""

    key: str
    value: float
    unit_key: str
    dimension: str
    raw_value: Any
    label: str


def normalize_key(key: str) -> str:
    lowered = (key or "").strip().lower().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", "_", lowered).strip("_")


def _unit_from_key_suffix(key: str) -> Optional[Unit]:
    """Ищет единицу измерения в суффиксе ключа (`battery_life_hours`)."""
    parts = key.split("_")
    for candidate in reversed(parts):
        unit = find_unit(candidate)
        if unit is not None:
            return unit
    return None


def _unit_from_hint(key: str) -> Optional[Unit]:
    for token, (_dimension, unit_key) in TOKEN_HINTS.items():
        if token in key:
            unit = unit_by_key(unit_key)
            if unit is not None:
                return unit
    return None


def parse_attribute(key: str, value: Any) -> Optional[AttributeQuantity]:
    """Превращает пару «ключ — значение» в нормализованную величину.

    Возвращает None, если значение не числовое или ключ не сопоставляется
    ни с одним поддерживаемым измерением.
    """
    normalized = normalize_key(key)
    if not normalized:
        return None
    if any(token in normalized for token in NON_COMPARABLE_TOKENS):
        return None
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if numeric <= 0:
        return None

    unit = _unit_from_key_suffix(normalized) or _unit_from_hint(normalized)
    if unit is None:
        return None

    return AttributeQuantity(
        key=normalized,
        value=numeric,
        unit_key=unit.key,
        dimension=unit.dimension,
        raw_value=value,
        label=normalized.replace("_", " "),
    )


def parse_attributes(attributes: Dict[str, Any]) -> Tuple[list, list]:
    """Возвращает (нормализованные величины, пропущенные ключи)."""
    parsed = []
    skipped = []
    for key, value in (attributes or {}).items():
        quantity = parse_attribute(key, value)
        if quantity is None:
            skipped.append(key)
        else:
            parsed.append(quantity)
    return parsed, skipped
