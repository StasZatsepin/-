"""Единый источник человекочитаемых подписей на русском языке.

Все пользовательские строки, которые выводятся в интерфейсе и в отчётах,
берутся отсюда. Сырые коды enum (например, technical_document, needs_human_review,
contextualizes) не должны попадать к пользователю.
"""

from __future__ import annotations

from app.models.enums import (
    AnalysisStatus,
    ClaimType,
    ClaimExtractionMethod,
    ClaimExtractionStatus,
    ConfidenceStatus,
    EvidenceRelation,
    EvidenceType,
    ExtractionMethod,
    ExtractionStatus,
    FindingStatus,
    FindingType,
    SourceType,
)

# --- Типы источников ---

SOURCE_TYPE_LABELS: dict[str, str] = {
    "product_description": "Описание товара",
    "attribute_sheet": "Таблица характеристик",
    "technical_document": "Технический документ",
    "review_export": "Отзывы",
    "user_note": "Заметка",
    "other": "Прочее",
}


# --- Типы утверждений ---

CLAIM_TYPE_LABELS: dict[str, str] = {
    "numeric_performance": "Числовая характеристика",
    "dimension_or_weight": "Размер или вес",
    "compatibility": "Совместимость",
    "material_or_composition": "Материал или состав",
    "certification_or_compliance": "Сертификация",
    "warranty_or_service": "Гарантия и сервис",
    "safety_or_health": "Безопасность и здоровье",
    "subjective_marketing": "Оценочный маркетинг",
    "other": "Прочее",
}

# --- Статусы извлечения ---

EXTRACTION_STATUS_LABELS: dict[str, str] = {
    "pending": "В ожидании",
    "extracted": "Извлечено",
    "needs_ocr": "Нужен OCR",
    "empty": "Пусто",
    "failed": "Ошибка разбора",
}

# --- Методы извлечения ---

EXTRACTION_METHOD_LABELS: dict[str, str] = {
    "manual": "Введено вручную",
    "rule_based": "Извлечено правилами",
    "mock_provider": "Мок-провайдер",
    "llm_provider": "Языковая модель",
    "seeded": "Сидирование",
}

# --- Статусы уверенности ---

CONFIDENCE_STATUS_LABELS: dict[str, str] = {
    "supported_by_provided_source": "Подтверждено предоставленным источником",
    "conflicting_sources": "Источники расходятся",
    "insufficient_evidence": "Недостаточно данных",
    "subjective_or_not_testable": "Нет объективного критерия",
    "needs_human_review": "Нужна проверка человеком",
}

# --- Типы находок ---

FINDING_TYPE_LABELS: dict[str, str] = {
    "direct_conflict": "Прямое расхождение",
    "missing_evidence": "Нет подтверждения",
    "review_signal": "Сигнал из отзывов",
    "ambiguous_claim": "Неоднозначное утверждение",
    "document_scope_mismatch": "Область применения документа",
    "needs_human_review": "Нужна проверка человеком",
}

# --- Статусы находок ---

FINDING_STATUS_LABELS: dict[str, str] = {
    "open": "Открыта",
    "in_review": "На рассмотрении",
    "resolved": "Решена",
    "not_an_issue": "Не проблема",
    "insufficient_data": "Недостаточно данных",
}

# --- Типы отношений evidence ---

EVIDENCE_RELATION_LABELS: dict[str, str] = {
    "supports": "подтверждает",
    "contradicts": "противоречит",
    "contextualizes": "контекст",
    "unrelated": "не связано",
    "uncertain": "неопределённо",
}

# --- Названия правил (rule_id -> человеческое имя) ---

RULE_NAMES: dict[str, str] = {
    "numeric.direct_conflict": "Прямое числовое расхождение",
    "internal_conflict": "Внутриконфликтное утверждение",
    "ambiguous_claim": "Неоднозначное утверждение",
    "missing_evidence": "Нет подтверждения",
    "review_signal": "Сигнал из отзывов",
    "document_scope_mismatch": "Несовпадение области документа",
    "provider.suggestion": "Предложение модели",
}

# --- Серьёзность находок ---

SEVERITY_LABELS: dict[str, str] = {
    "info": "Информация",
    "low": "Низкая",
    "medium": "Средняя",
    "high": "Высокая",
}

# --- Статусы статусов находок ---

FINDING_STATUS_LABELS: dict[str, str] = {
    "open": "Открыта",
    "in_review": "На рассмотрении",
    "resolved": "Решена",
    "not_an_issue": "Не проблема",
    "insufficient_data": "Недостаточно данных",
}

# --- Статусы запуска анализа ---

ANALYSIS_STATUS_LABELS: dict[str, str] = {
    "pending": "В ожидании",
    "running": "Выполняется",
    "completed": "Завершена",
    "failed": "Ошибка",
}


def label_for(mapping: dict[str, str], key: str | None, default: str = "Прочее") -> str:
    """Возвращает человекочитаемую подпись по ключу.

    Если ключа нет в словаре — возвращает значение по умолчанию
    (обычно «Прочее»), а не сырой код.
    """
    if key is None:
        return default
    return mapping.get(key, default)


def all_claim_types_have_labels() -> bool:
    """Проверяет, что все значения ClaimType имеют человеческие подписи."""
    from app.models.enums import ClaimType

    for claim_type in ClaimType:
        if claim_type.value not in CLAIM_TYPE_LABELS:
            return False
    return True


def all_finding_types_have_labels() -> bool:
    """Проверяет, что все значения FindingType имеют человеческие подписи."""
    from app.models.enums import FindingType

    for finding_type in FindingType:
        if finding_type.value not in FINDING_TYPE_LABELS:
            return False
    return True


def all_source_types_have_labels() -> bool:
    """Проверяет, что все значения SourceType имеют человеческие подписи."""
    from app.models.enums import SourceType

    for source_type in SourceType:
        if source_type.value not in SOURCE_TYPE_LABELS:
            return False
    return True


def all_confidence_statuses_have_labels() -> bool:
    """Проверяет, что все значения ConfidenceStatus имеют человеческие подписи."""
    from app.models.enums import ConfidenceStatus

    for status in ConfidenceStatus:
        if status.value not in CONFIDENCE_STATUS_LABELS:
            return False
    return True


def all_evidence_types_have_labels() -> bool:
    """Проверяет, что все значения EvidenceType имеют человеческие подписи."""
    from app.models.enums import EvidenceType

    for evidence_type in EvidenceType:
        if evidence_type.value not in SOURCE_TYPE_LABELS:
            return False
    return True


def all_relation_labels_have_labels() -> bool:
    """Проверяет, что все значения EvidenceRelation имеют человеческие подписи."""
    from app.models.enums import EvidenceRelation

    for relation in EvidenceRelation:
        if relation.value not in EVIDENCE_RELATION_LABELS:
            return False
    return True


def all_finding_statuses_have_labels() -> bool:
    """Проверяет, что все значения FindingStatus имеют человеческие подписи."""
    from app.models.enums import FindingStatus

    for status in FindingStatus:
        if status.value not in FINDING_STATUS_LABELS:
            return False
    return True