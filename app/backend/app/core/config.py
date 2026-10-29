"""Конфигурация приложения через переменные окружения и файл `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, List

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# app/backend/app/core/config.py -> app/backend/app/core -> ... -> корень проекта
PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Настройки MVP. Все значения можно переопределить переменными окружения."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Обещание против реальности"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = False

    # Секрет для подписи токенов сессий. В production обязательно заменить.
    secret_key: str = "dev-secret-change-me"

    database_url: str = (
        "postgresql+psycopg://oapv_app:oapv_local_dev@localhost:5432/obeshchanie"
    )
    database_echo: bool = False

    # Хранилище загруженных файлов (вне репозитория, путь генерируется сервером).
    storage_dir: Path = PROJECT_ROOT / "app" / "backend" / "var" / "storage"

    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_upload_extensions: Annotated[List[str], NoDecode] = [
        ".txt",
        ".csv",
        ".md",
        ".pdf",
        ".xlsx",
    ]
    allowed_upload_mimetypes: Annotated[List[str], NoDecode] = [
        "text/plain",
        "text/csv",
        "text/markdown",
        "text/x-markdown",
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
        "",
    ]

    # Демо-режим: вход в заранее подготовленное рабочее пространство.
    demo_mode: bool = True
    demo_workspace_name: str = "Демонстрационное пространство"
    demo_user_email: str = "demo@local.test"
    demo_user_password: str = "demo12345"

    # Провайдер ИИ. По умолчанию mock: приложение полностью работоспособно
    # без внешних API и без платных ключей.
    llm_provider: str = "mock"  # mock | ollama | openai_compatible | openrouter
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_timeout_seconds: float = 90.0
    llm_max_chars: int = 12000

    # --- Ollama: локальные модели ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 180.0

    # --- OpenRouter: бесплатные модели с открытым API ---
    # Ключ хранится как SecretStr: случайная печать или сериализация
    # настроек не покажут его содержимое.
    openrouter_api_key: SecretStr = SecretStr("")
    # Идентификатор модели задаётся конфигурацией: бизнес-логика не знает
    # ни о какой конкретной модели и о том, какие из них бесплатны.
    openrouter_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 60.0
    openrouter_max_retries: int = 2
    openrouter_retry_backoff_seconds: float = 2.0
    openrouter_max_tokens: int = 1500
    # Резервные модели: используются только при 429 и только из этого списка.
    openrouter_fallback_models: Annotated[List[str], NoDecode] = []
    # HTTP-Referer и X-Title: OpenRouter рекомендует их для атрибуции
    # запросов в личном кабинете. Не являются секретами.
    openrouter_http_referer: str = ""
    openrouter_app_title: str = "Обещание против реальности"

    cors_origins: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    token_ttl_hours: int = 24 * 14

    rules_version: str = "rules-2024.1"

    @field_validator("allowed_upload_extensions", mode="before")
    @classmethod
    def _split_extensions(cls, value):
        if isinstance(value, str):
            items = [item.strip().lower() for item in value.split(",") if item.strip()]
            return [item if item.startswith(".") else f".{item}" for item in items]
        return value

    @field_validator("allowed_upload_mimetypes", "cors_origins", "openrouter_fallback_models", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("storage_dir", mode="before")
    @classmethod
    def _expand_path(cls, value):
        if isinstance(value, str):
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            return path
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def secret_value(value: object) -> str:
    """Безопасно получает значение секрета.

    Принимает как `SecretStr`, так и обычную строку: значение может быть
    подставлено программно (тесты, скрипты) в обход настроек.
    """
    if value is None:
        return ""
    getter = getattr(value, "get_secret_value", None)
    if callable(getter):
        return str(getter() or "")
    return str(value)
