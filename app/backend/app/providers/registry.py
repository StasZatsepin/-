"""Выбор провайдера анализа и безопасный fallback на локальную эвристику."""

from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.providers.base import ClaimAnalysisProvider, ProviderResult
from app.providers.mock import MockAnalysisProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger("app.providers.registry")

_MOCK = MockAnalysisProvider()


def build_provider() -> ClaimAnalysisProvider:
    """Создаёт провайдера согласно настройкам окружения."""
    provider_name = (settings.llm_provider or "mock").strip().lower()
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name in {"openai_compatible", "openai", "compatible"}:
        return OpenAICompatibleProvider()
    return _MOCK


def get_provider() -> ClaimAnalysisProvider:
    """Возвращает активный провайдер (создаётся заново при смене настроек)."""
    return build_provider()


def run_provider(
    provider: ClaimAnalysisProvider, claims, context
) -> tuple[ProviderResult, bool]:
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
