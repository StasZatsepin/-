"""Извлечение кандидатов в утверждения из источников товара."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.models.enums import (
    ClaimType,
    ExtractionMethod,
    SourceType,
)
from app.rules.attributes import parse_attribute
from app.rules.numeric import NumericStatement, extract_numeric_statements, split_sentences
from app.rules.patterns import classify_claim_type

logger = logging.getLogger("app.services.claims")

# Поля отзыва, которые чаще всего содержат текст
_REVIEW_TEXT_FIELDS = ("text", "отзыв", "текст", "comment", "review", "body", "content")
_REVIEW_DATE_FIELDS = ("date", "дата", "created_at", "time")
_REVIEW_RATING_FIELDS = ("rating", "оценка", "score", "stars")


@dataclass
class ClaimDraft:
    """Черновик утверждения до сохранения в базе."""

    text: str
    claim_type: str
    source_excerpt: str
    extraction_method: str = ExtractionMethod.RULE_BASED.value
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    model_version: Optional[str] = None
    confidence_label: Optional[str] = None
    numeric_value: Optional[float] = None
    numeric_unit: Optional[str] = None
    numeric_dimension: Optional[str] = None
    numeric_comparator: Optional[str] = None
    numeric_context: Optional[str] = None


def _numeric_fields(statement: NumericStatement) -> Dict[str, Any]:
    return {
        "numeric_value": statement.value,
        "numeric_unit": statement.unit_key,
        "numeric_dimension": statement.dimension,
        "numeric_comparator": statement.comparator,
        "numeric_context": statement.context or None,
    }


def claims_from_text(
    text: str,
    source_type: str,
    extraction_method: str = ExtractionMethod.RULE_BASED.value,
) -> List[ClaimDraft]:
    """Строит черновики утверждений из текста источника."""
    drafts: List[ClaimDraft] = []
    if not text or not text.strip():
        return drafts

    for sentence in split_sentences(text):
        if len(sentence.text.strip()) < 8:
            continue
        statements = extract_numeric_statements(sentence.text)
        if statements:
            for statement in statements:
                drafts.append(
                    ClaimDraft(
                        text=sentence.text.strip(),
                        claim_type=classify_claim_type(sentence.text).value,
                        source_excerpt=sentence.text.strip(),
                        extraction_method=extraction_method,
                        start_offset=sentence.offset,
                        end_offset=sentence.offset + len(sentence.text),
                        **_numeric_fields(statement),
                    )
                )
        else:
            drafts.append(
                ClaimDraft(
                    text=sentence.text.strip(),
                    claim_type=classify_claim_type(sentence.text).value,
                    source_excerpt=sentence.text.strip(),
                    extraction_method=extraction_method,
                    start_offset=sentence.offset,
                    end_offset=sentence.offset + len(sentence.text),
                )
            )
    return drafts


def claims_from_attributes(attributes: Dict[str, Any]) -> List[ClaimDraft]:
    """Строит утверждения из структурированных характеристик товара."""
    drafts: List[ClaimDraft] = []
    for key, value in (attributes or {}).items():
        if value is None:
            continue
        text = f"{key}: {value}"
        quantity = parse_attribute(key, value)
        drafts.append(
            ClaimDraft(
                text=text,
                claim_type=_attribute_claim_type(key),
                source_excerpt=text,
                extraction_method=ExtractionMethod.RULE_BASED.value,
                numeric_value=quantity.value if quantity else None,
                numeric_unit=quantity.unit_key if quantity else None,
                numeric_dimension=quantity.dimension if quantity else None,
                numeric_comparator="exact" if quantity else None,
                numeric_context=text if quantity else None,
            )
        )
    return drafts


def _attribute_claim_type(key: str) -> str:
    normalized = (key or "").lower()
    if any(token in normalized for token in ("weight", "вес", "масс", "размер", "длина", "width", "height")):
        return ClaimType.DIMENSION_OR_WEIGHT.value
    if any(token in normalized for token in ("battery", "ёмк", "емк", "capacity", "мощност", "power")):
        return ClaimType.NUMERIC_PERFORMANCE.value
    if any(token in normalized for token in ("material", "материал", "состав", "composition")):
        return ClaimType.MATERIAL_OR_COMPOSITION.value
    if any(token in normalized for token in ("warranty", "гарант")):
        return ClaimType.WARRANTY_OR_SERVICE.value
    return ClaimType.OTHER.value


def claims_from_reviews(source_text: str, rows: List[Dict[str, Any]]) -> List[ClaimDraft]:
    """Строит утверждения из отзывов (источник пользовательских сигналов)."""
    drafts: List[ClaimDraft] = []
    if rows:
        for row in rows:
            text = ""
            for field_name in _REVIEW_TEXT_FIELDS:
                value = row.get(field_name)
                if value:
                    text = str(value).strip()
                    break
            if not text:
                continue
            for sentence in split_sentences(text):
                if len(sentence.text.strip()) < 8:
                    continue
                statements = extract_numeric_statements(sentence.text)
                if statements:
                    for statement in statements:
                        drafts.append(
                            ClaimDraft(
                                text=sentence.text.strip(),
                                claim_type=ClaimType.OTHER.value,
                                source_excerpt=sentence.text.strip(),
                                extraction_method=ExtractionMethod.RULE_BASED.value,
                                **_numeric_fields(statement),
                            )
                        )
                else:
                    drafts.append(
                        ClaimDraft(
                            text=sentence.text.strip(),
                            claim_type=ClaimType.OTHER.value,
                            source_excerpt=sentence.text.strip(),
                            extraction_method=ExtractionMethod.RULE_BASED.value,
                        )
                    )
        return drafts

    return claims_from_text(source_text, SourceType.REVIEW_EXPORT.value)


def claims_for_source(
    source_type: str, source_text: str, metadata: Dict[str, Any]
) -> List[ClaimDraft]:
    """Выбирает способ извлечения утверждений в зависимости от типа источника."""
    metadata = metadata or {}
    if source_type == SourceType.ATTRIBUTE_SHEET.value:
        return claims_from_attributes(metadata.get("attributes") or {})
    if source_type == SourceType.REVIEW_EXPORT.value:
        return claims_from_reviews(source_text, metadata.get("rows") or [])
    if source_type == SourceType.PRODUCT_DESCRIPTION.value:
        return claims_from_text(source_text, source_type)
    if source_type == SourceType.USER_NOTE.value:
        return claims_from_text(source_text, source_type)
    return claims_from_text(source_text, source_type)
