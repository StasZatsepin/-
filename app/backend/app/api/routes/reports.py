"""Отчёты по результатам проверки."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_owned_product, get_owned_run
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.product import Product
from app.services.reports import DISCLAIMER, render_report

router = APIRouter(tags=["reports"])


@router.get("/products/{product_id}/reports")
def list_reports(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> dict:
    """Список доступных отчётов по товару."""
    runs = list(
        db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.product_id == product.id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(50)
        ).scalars()
    )
    return {
        "disclaimer": DISCLAIMER,
        "reports": [
            {
                "id": run.id,
                "status": run.status,
                "created_at": run.created_at,
                "finished_at": run.finished_at,
                "rules_version": run.rules_version,
                "provider_name": run.provider_name,
                "findings_total": (run.summary or {}).get("findings_total", 0),
            }
            for run in runs
        ],
    }


@router.get("/products/{product_id}/reports/{run_id}")
def get_report(
    run_id: str,
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> Response:
    """HTML-отчёт по конкретному запуску проверки."""
    run = db.get(AnalysisRun, run_id)
    if run is None or run.workspace_id != product.workspace_id or run.product_id != product.id:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "Отчёт не найден.")

    html = render_report(db, product, run)
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="report-{product.id}.html"',
            "X-Content-Type-Options": "nosniff",
        },
    )
