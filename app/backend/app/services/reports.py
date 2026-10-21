"""Генерация HTML-отчёта по результатам проверки."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun
from app.models.claim import Claim
from app.models.finding import Finding
from app.models.product import Product
from app.models.review_action import ReviewAction
from app.models.source import Source

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "reports" / "templates"

DISCLAIMER = (
    "Автоматический анализ помогает выявлять возможные несоответствия "
    "и не является юридическим заключением или независимым испытанием товара."
)

ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(default_for_string=True, default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)

SEVERITY_LABELS = {
    "info": "Информация",
    "low": "Низкая",
    "medium": "Средняя",
    "high": "Высокая",
}

FINDING_TYPE_LABELS = {
    "direct_conflict": "Прямое расхождение",
    "missing_evidence": "Нет подтверждения",
    "review_signal": "Сигнал из отзывов",
    "ambiguous_claim": "Неоднозначное утверждение",
    "document_scope_mismatch": "Область применения документа",
    "needs_human_review": "Требуется проверка человеком",
}

STATUS_LABELS = {
    "open": "Открыта",
    "in_review": "На рассмотрении",
    "resolved": "Решена",
    "not_an_issue": "Не является проблемой",
    "insufficient_data": "Недостаточно данных",
}

CLAIM_TYPE_LABELS = {
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


def _format_date(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M")
    return str(value)


def render_report(db: Session, product: Product, run: AnalysisRun) -> str:
    """Возвращает HTML-отчёт по проверке товара."""
    sources = list(
        db.execute(
            select(Source)
            .where(Source.product_id == product.id)
            .order_by(Source.created_at.asc())
        ).scalars()
    )
    claims = list(
        db.execute(
            select(Claim).where(Claim.product_id == product.id).order_by(Claim.created_at.asc())
        ).scalars()
    )
    findings = list(
        db.execute(
            select(Finding)
            .where(Finding.product_id == product.id, Finding.archived.is_(False))
            .order_by(Finding.severity.asc(), Finding.created_at.asc())
        ).scalars()
    )
    actions = list(
        db.execute(
            select(ReviewAction)
            .where(ReviewAction.product_id == product.id)
            .order_by(ReviewAction.created_at.asc())
        ).scalars()
    )
    source_names = {source.id: source.source_name for source in sources}

    template = ENVIRONMENT.get_template("report.html.j2")
    return template.render(
        generated_at=_format_date(datetime.now(timezone.utc)),
        disclaimer=DISCLAIMER,
        product=product,
        run=run,
        sources=[
            {
                "name": source.source_name,
                "type": source.source_type,
                "date": _format_date(source.source_date),
                "uploaded_at": _format_date(source.created_at),
                "hash": source.content_hash[:16],
                "extraction_status": source.extraction_status,
                "extraction_note": source.extraction_note or "",
                "size_bytes": source.size_bytes,
                "is_demo": bool((source.metadata_json or {}).get("demo")),
            }
            for source in sources
        ],
        claims=[
            {
                "text": claim.text,
                "type": CLAIM_TYPE_LABELS.get(claim.claim_type, claim.claim_type),
                "source": source_names.get(claim.source_id, "Ручной ввод"),
                "confidence": claim.confidence_label or "—",
                "confidence_status": claim.confidence_status,
                "confirmed": claim.user_confirmed,
            }
            for claim in claims
            if not claim.is_rejected
        ],
        findings=[
            {
                "title": finding.title,
                "type": FINDING_TYPE_LABELS.get(finding.finding_type, finding.finding_type),
                "type_raw": finding.finding_type,
                "severity": SEVERITY_LABELS.get(finding.severity, finding.severity),
                "severity_raw": finding.severity,
                "status": STATUS_LABELS.get(finding.status, finding.status),
                "status_raw": finding.status,
                "description": finding.description,
                "limitations": finding.limitations,
                "recommended_action": finding.recommended_action,
                "confidence_status": finding.confidence_status,
                "rule": f"{finding.rule_id} ({finding.rule_version})",
                "sources": [
                    {
                        "name": ref.get("source_name", ""),
                        "excerpt": ref.get("excerpt", ""),
                        "relation": ref.get("relation", ""),
                    }
                    for ref in (finding.source_refs or [])
                ],
            }
            for finding in findings
        ],
        decisions=[
            {
                "created_at": _format_date(action.created_at),
                "user": action.user_email,
                "previous": STATUS_LABELS.get(action.previous_status or "", action.previous_status or "—"),
                "new": STATUS_LABELS.get(action.new_status or "", action.new_status or "—"),
                "comment": action.comment,
                "finding_title": next(
                    (
                        finding.title
                        for finding in findings
                        if finding.id == action.finding_id
                    ),
                    "Находка",
                ),
            }
            for action in actions
        ],
        limitations=(run.limitations if run else [])
        or ["Анализ выполнен по предоставленным материалам."],
        summary=(run.summary if run else {}) or {},
    )
