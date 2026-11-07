"""Единый источник человекочитаемых подписей на русском языке.

Все пользовательские строки, которые выводятся в отчёте и в API-ответах для
интерфейса, берутся отсюда. Сырые коды (technical_document, needs_human_review,
contextualizes, claims.ambiguous_promise и т. п.) не должны попадать к пользователю.

Модуль намеренно не импортирует ничего из приложения: он состоит только из
словарей и функции ``label_for``, поэтому его безопасно использовать где угодно.
Полноту подписей относительно перечислений проверяет ``tests/test_labels_ru.py``.
"""

from __future__ import annotations

# Подпись по умолчанию для неизвестного значения: лучше нейтральное слово, чем сырой код.
UNKNOWN_LABEL = "Прочее"

# --- Маркетплейсы ---

MARKETPLACE_LABELS: dict[str, str] = {
    "ozon": "Ozon",
    "wildberries": "Wildberries",
    "demo": "Демо",
    "other": "Другой",
}

# --- Типы источников ---

SOURCE_TYPE_LABELS: dict[str, str] = {
    "product_description": "Описание товара",
    "attribute_sheet": "Таблица характеристик",
    "technical_document": "Технический документ",
    "review_export": "Отзывы",
    "user_note": "Заметка",
    "other": "Прочее",
}

# --- Статусы разбора источника ---

EXTRACTION_STATUS_LABELS: dict[str, str] = {
    "pending": "Ожидает разбора",
    "extracted": "Текст извлечён",
    "needs_ocr": "Нужно распознавание текста (OCR)",
    "empty": "Текста нет",
    "failed": "Не удалось разобрать",
}

# --- Способы извлечения ---

EXTRACTION_METHOD_LABELS: dict[str, str] = {
    "manual": "Введено вручную",
    "rule_based": "Правила",
    "mock_provider": "Встроенные правила",
    "llm_provider": "Языковая модель",
    "seeded": "Демонстрационные данные",
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

# --- Статусы оценки (confidence_status / confidence_label) ---

CONFIDENCE_STATUS_LABELS: dict[str, str] = {
    "supported_by_provided_source": "Есть подтверждение в предоставленных данных",
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

# --- Серьёзность находок ---

SEVERITY_LABELS: dict[str, str] = {
    "info": "Информация",
    "low": "Низкая",
    "medium": "Средняя",
    "high": "Высокая",
}

# --- Статусы рассмотрения находок ---

FINDING_STATUS_LABELS: dict[str, str] = {
    "open": "Открыта",
    "in_review": "На рассмотрении",
    "resolved": "Решена",
    "not_an_issue": "Не проблема",
    "insufficient_data": "Недостаточно данных",
}

# --- Типы доказательств ---

EVIDENCE_TYPE_LABELS: dict[str, str] = {
    "attribute_value": "Значение из таблицы характеристик",
    "document_statement": "Утверждение из документа",
    "review_statement": "Фрагмент отзыва",
    "description_text": "Текст описания",
    "user_note": "Заметка",
}

# --- Отношение доказательства к утверждению ---

EVIDENCE_RELATION_LABELS: dict[str, str] = {
    "supports": "подтверждает",
    "contradicts": "противоречит",
    "contextualizes": "уточняет контекст",
    "unrelated": "не связано",
    "uncertain": "неопределённо",
}

# --- Статусы запуска проверки ---

ANALYSIS_STATUS_LABELS: dict[str, str] = {
    "pending": "Ожидает запуска",
    "running": "Выполняется",
    "completed": "Завершена",
    "failed": "Завершилась ошибкой",
}

# --- Поставщики анализа ---

PROVIDER_LABELS: dict[str, str] = {
    "mock": "Встроенные правила (без языковой модели)",
    "ollama": "Ollama (локальная модель)",
    "openai_compatible": "OpenAI-совместимый сервис",
    "openrouter": "OpenRouter",
}

# --- Названия правил (rule_id → понятное имя) ---
# Ключи должны совпадать со значениями rule_id в rules/engine.py и services/analysis.py.

RULE_NAMES: dict[str, str] = {
    "numeric.attribute_comparison": "Сравнение описания с таблицей характеристик",
    "numeric.internal_consistency": "Согласованность значений внутри источников",
    "claims.ambiguous_promise": "Обещание без объективного критерия",
    "claims.unclassified": "Тип утверждения не определён",
    "evidence.missing_safety_confirmation": "Нет подтверждения заявления о безопасности",
    "evidence.missing_confirmation": "Нет подтверждения в предоставленных материалах",
    "reviews.negative_signal": "Негативный сигнал из отзывов",
    "reviews.mixed_signal": "Отзывы расходятся во мнениях",
    "reviews.numeric_mismatch": "Отзыв расходится с описанием по числу",
    "documents.scope_mismatch": "Документ относится к другой модели или версии",
    "documents.expired_or_soon": "Срок действия документа",
    "provider.suggestion": "Предложение языковой модели",
}


def label_for(mapping: dict[str, str], key: object, default: str = UNKNOWN_LABEL) -> str:
    """Подпись по ключу; для пустого или неизвестного значения возвращает ``default``.

    Сырой код в интерфейс не отдаётся никогда.
    """
    if key is None:
        return default
    value = getattr(key, "value", key)
    return mapping.get(str(value), default)


def rule_label(rule_id: str | None) -> str:
    """Понятное имя правила; для неизвестного правила — нейтральная подпись."""
    return label_for(RULE_NAMES, rule_id, "Автоматическая проверка")
