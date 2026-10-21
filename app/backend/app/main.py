"""Точка входа FastAPI-приложения «Обещание против реальности»."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("app.main")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Система доказательной проверки товарных утверждений для продавцов "
        "маркетплейсов. Автоматический анализ помогает выявлять возможные "
        "несоответствия и не является юридическим заключением."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
def health() -> dict:
    """Проверка готовности backend."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "rules_version": settings.rules_version,
        "database": settings.database_url.split("@")[-1],
    }


@app.get("/api/v1/health", tags=["system"])
def health_v1() -> dict:
    """Проверка готовности backend по версионированному пути."""
    return health()


@app.on_event("startup")
def on_startup() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "%s v%s запущено. Провайдер ИИ: %s",
        settings.app_name,
        settings.app_version,
        settings.llm_provider,
    )
