"""Сводка, настройки и служебные маршруты."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.enums import SourceType
from app.models.finding import Finding
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import User
from app.providers.registry import get_provider
from app.schemas.analysis import AnalysisRunOut, OverviewStats

router = APIRouter(tags=["system"])


@router.get("/overview", response_model=OverviewStats)
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OverviewStats:
    """Сводка по рабочему пространству для главной страницы."""
    workspace_id = user.workspace_id

    products_total = db.execute(
        select(func.count()).select_from(Product).where(Product.workspace_id == workspace_id)
    ).scalar_one()
    demo_products = db.execute(
        select(func.count())
        .select_from(Product)
        .where(Product.workspace_id == workspace_id, Product.is_demo.is_(True))
    ).scalar_one()
    findings_total = db.execute(
        select(func.count())
        .select_from(Finding)
        .where(Finding.workspace_id == workspace_id, Finding.archived.is_(False))
    ).scalar_one()
    findings_open = db.execute(
        select(func.count())
        .select_from(Finding)
        .where(
            Finding.workspace_id == workspace_id,
            Finding.archived.is_(False),
            Finding.status.in_(["open", "in_review"]),
        )
    ).scalar_one()
    sources_total = db.execute(
        select(func.count())
        .select_from(Source)
        .where(Source.workspace_id == workspace_id)
    ).scalar_one()
    reviews_total = db.execute(
        select(func.count())
        .select_from(Source)
        .where(
            Source.workspace_id == workspace_id,
            Source.source_type == SourceType.REVIEW_EXPORT.value,
        )
    ).scalar_one()
    runs_total = db.execute(
        select(func.count())
        .select_from(AnalysisRun).where(AnalysisRun.workspace_id == workspace_id)
    ).scalar_one()

    findings = list(
        db.execute(
            select(Finding).where(
                Finding.workspace_id == workspace_id, Finding.archived.is_(False)
            )
        ).scalars()
    )
    by_severity: dict = {}
    by_type: dict = {}
    by_status: dict = {}
    for finding in findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        by_type[finding.finding_type] = by_type.get(finding.finding_type, 0) + 1
        by_status[finding.status] = by_status.get(finding.status, 0) + 1

    recent_runs = list(
        db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.workspace_id == workspace_id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(8)
        ).scalars()
    )

    return OverviewStats(
        products_total=int(products_total),
        findings_open=int(findings_open),
        findings_total=int(findings_total),
        sources_total=int(sources_total),
        reviews_total=int(reviews_total),
        runs_total=int(runs_total),
        findings_by_severity=by_severity,
        findings_by_type=by_type,
        findings_by_status=by_status,
        recent_runs=[AnalysisRunOut.model_validate(run) for run in recent_runs],
        demo_products=int(demo_products),
    )


@router.get("/settings/ai")
def ai_settings(user: User = Depends(get_current_user)) -> dict:
    """Состояние ИИ-провайдера и ограничения системы."""
    provider = get_provider()
    status = provider.status()
    return {
        "provider": {
            "name": status.provider,
            "model": status.model_version,
            "available": status.available,
            "message": status.message,
            "requires_api_key": status.requires_api_key,
            "external_data_transfer": status.external_data_transfer,
            "fallback": status.fallback_provider,
        },
        # Список поддерживаемых провайдеров без ключей и сетевых проверок.
        "available_providers": [
            {
                "name": "mock",
                "label": "Локальная эвристика",
                "requires_api_key": False,
                "hint": "Работает без сети. Используется по умолчанию и как резервный режим.",
            },
            {
                "name": "openrouter",
                "label": "OpenRouter (бесплатные модели)",
                "requires_api_key": True,
                "hint": "Нужен OPENROUTER_API_KEY и OPENROUTER_MODEL. Текст материалов "
                "передаётся внешнему сервису.",
            },
            {
                "name": "ollama",
                "label": "Ollama (локальные модели)",
                "requires_api_key": False,
                "hint": "Нужен запущенный сервис Ollama. Материалы не покидают компьютер.",
            },
            {
                "name": "openai_compatible",
                "label": "Другой OpenAI-совместимый API",
                "requires_api_key": True,
                "hint": "Нужны LLM_BASE_URL, LLM_API_KEY и LLM_MODEL.",
            },
        ],
        "limits": {
            "max_upload_bytes": settings.max_upload_bytes,
            "allowed_extensions": settings.allowed_upload_extensions,
            "rules_version": settings.rules_version,
            "demo_mode": settings.demo_mode,
        },
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    }


@router.post("/demo/seed")
def seed_demo(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Добавляет демонстрационный товар в текущее рабочее пространство."""
    from app.services.demo import seed_demo_data

    product = seed_demo_data(db, user)
    return {
        "message": "Демонстрационный товар сохранён.",
        "product_id": product.id,
        "product_name": product.name,
        "is_demo": product.is_demo,
    }
