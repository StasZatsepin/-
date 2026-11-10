"""Готовые подсказки «что исправить» для находок.

Модуль не обращается к базе и не использует модель: подсказка строится только
из текста самой находки по правилам. Подсказка никогда не утверждает, какая из
сторон права: она предлагает действие и приводит значения из материалов.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

_QUOTE = re.compile(r"«(.+?)»", re.S)
_SPEC_LINE = re.compile(r"В таблице характеристик: (?P<label>.+?) = (?P<value>.+?)\.?\s*(?:\n|$)")


def _first_quote(text: str) -> str:
    match = _QUOTE.search(text or "")
    return match.group(1).strip() if match else ""


def _numeric_comparison(description: str) -> Optional[Dict[str, str]]:
    spec = _SPEC_LINE.search(description or "")
    quote = _first_quote(description)
    if not spec or not quote:
        return None
    label = spec.group("label").strip()
    value = spec.group("value").strip()
    return {
        "text": (
            f"Если верна таблица характеристик, замените в описании «{quote}» "
            f"на значение «{label} — {value}». Если верно обещание, исправьте "
            "характеристику и приложите документ, который его подтверждает."
        ),
        "copy_text": f"{label} — {value}",
    }


def _ambiguous(description: str) -> Optional[Dict[str, str]]:
    marker = _first_quote(description)
    if not marker:
        return None
    return {
        "text": (
            f"Замените слово «{marker}» проверяемым фактом: числом, материалом, "
            "стандартом или условием, которые можно подтвердить документом."
        ),
        "copy_text": "",
    }


def _missing(description: str, safety: bool) -> Optional[Dict[str, str]]:
    quote = _first_quote(description)
    if not quote:
        return None
    if safety:
        text = (
            f"Приложите документ (сертификат или протокол испытаний), который подтверждает "
            f"«{quote}», либо уберите эту формулировку."
        )
    else:
        text = (
            f"Приложите документ, подтверждающий «{quote}», либо замените утверждение "
            "формулировкой, которую вы можете подтвердить."
        )
    return {"text": text, "copy_text": ""}


def _review_mismatch(description: str) -> Dict[str, str]:
    return {
        "text": (
            "Покупатели называют другое значение. Проверьте, при каких условиях оно "
            "достигается, и либо укажите эти условия в описании, либо исправьте цифру."
        ),
        "copy_text": "",
    }


def suggest_fix(rule_id: str, description: str, recommended_action: str = "") -> Optional[Dict[str, str]]:
    """Возвращает {'text', 'copy_text'} или None, если для правила подсказки нет."""
    rule = (rule_id or "").strip()
    description = description or ""
    if rule == "numeric.attribute_comparison":
        return _numeric_comparison(description)
    if rule == "claims.ambiguous_promise":
        return _ambiguous(description)
    if rule == "evidence.missing_safety_confirmation":
        return _missing(description, safety=True)
    if rule == "evidence.missing_confirmation":
        return _missing(description, safety=False)
    if rule == "reviews.numeric_mismatch":
        return _review_mismatch(description)
    return None
