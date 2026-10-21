"""Выбор провайдера анализа и безопасный fallback на локальную эвристику.

Провайдер выбирается конфигурацией (`LLM_PROVIDER`). Никакая конкретная
модель в коде не зашита: идентификатор приходит из окружения, поэтому
смена модели не требует изменения программы.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from app.core.config import settings
from app.providers.base import ClaimAnalysisProvider, ProviderResult
from app.providers.mock import MockAnalysisProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.openrouter import OpenRouterProvider

logger = logging.getLogger("app.providers.registry")

_MOCK = MockAnalysisProvider()

# Схожие названия, которые люди обычно используют в конфигурации
_ALIASES = {
    "mock": "mock",
    "local": "mock",
    "heuristic": "mock",
    "ollama": "ollama",
    "openai_compatible": "openai_compatible",
    "openai": "openai_compatible",
    "compatible": "openai_compatible",
    "openrouter": "openrouter",
    "open_router": "openrouter",
}


def build_provider() -> ClaimAnalysisProvider:
    """Создаёт провайдера согласно настройкам окружения."""
    provider_name = (settings.llm_provider or "mock").strip().lower()
    resolved = _ALIASES.get(provider_name, "mock")
    if resolved == "ollama":
        return OllamaProvider()
    if resolved == "openai_compatible":
        return OpenAICompatibleProvider()
    if resolved == "openrouter":
        return OpenRouterProvider()
    return _MOCK


def get_provider() -> ClaimAnalysisProvider:
    """Возвращает активный провайдера (создаётся заново при смене настроек)."""
    return build_provider()


def run_provider(
    provider: ClaimAnalysisProvider, claims, context
) -> Tuple[ProviderResult, bool]:
    """Выполняет классификацию с автоматическим fallback на mock.

    Возвращает (результат, был_ли_использован_внешний_провайдер).
    """
    try:
        result = provider.classify_claims(claims, context)
    except Exception as exc:  # pragma: no cover - защита от сбоя провайдера
        logger.warning("Провайдер %s завершился ошибкой: %s", provider.name, type(exc).__name__)
        result = ProviderResult(
            provider=provider.name,
            model_version="",
            status="error",
            message="Провайдер завершился ошибкой, применена локальная эвристика.",
        )

    if result.status in {"ok", "empty"}:
        return result, result.used_external_service

    # Внешний провайдер недоступен — молча не деградируем, а явно сообщаем.
    fallback = _MOCK.classify_claims(claims, context)
    fallback.message = (
        f"{result.message} Применена локальная эвристика вместо внешней модели."
    )
    return fallback, False


def provider_chain() -> List[ClaimAnalysisProvider]:
    """Список провайдеров в порядке убывания предпочтения.

    Используется в сравнительных замерах: один и тот же набор данных
    прогоняется через локальную эвристику и через внешнюю модель.
    """
    chain: List[ClaimAnalysisProvider] = [_MOCK]
    provider_name = (settings.llm_provider or "mock").strip().lower()
    resolved = _ALIASES.get(provider_name, "mock")
    if resolved == "ollama":
        chain.append(OllamaProvider())
    elif resolved == "openai_compatible":
        chain.append(OpenAICompatibleProvider())
    elif resolved == "openrouter":
        chain.append(OpenRouterProvider())
    return chain
