"""Генерация HTML-отчёта по результатам проверки."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.labels_ru import (
    ANALYSIS_STATUS_LABELS,
    CLAIM_TYPE_LABELS,
    CONFIDENCE_STATUS_LABELS,
    EVIDENCE_RELATION_LABELS,
    EXTRACTION_STATUS_LABELS,
    FINDING_STATUS_LABELS,
    FINDING_TYPE_LABELS,
    MARKETPLACE_LABELS,
    PROVIDER_LABELS,
    SEVERITY_LABELS,
    SOURCE_TYPE_LABELS,
    label_for,
    rule_label,
)
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


def _format_date(value, with_time: bool = True) -> str:
    """Дата для отчёта. Полночь (00:00) означает «время не задано» и не выводится."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        if with_time and (value.hour or value.minute):
            return value.strftime("%d.%m.%Y %H:%M")
        return value.strftime("%d.%m.%Y")
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
    context = build_report_context(product, run, sources, claims, findings, actions)
    return ENVIRONMENT.get_template("report.html.j2").render(**context)


def build_report_context(
    product,
    run,
    sources: List,
    claims: List,
    findings: List,
    actions: List,
) -> Dict:
    """Собирает данные для шаблона отчёта.

    Функция не обращается к базе данных. Все коды (типы, статусы, отношения,
    идентификаторы правил) переводятся в русские подписи через ``labels_ru``:
    пользователь не должен видеть технических значений.
    """
    source_names = {source.id: source.source_name for source in sources}

    return {
        "generated_at": _format_date(datetime.now(timezone.utc)),
        "disclaimer": DISCLAIMER,
        "product": product,
        "marketplace_label": label_for(MARKETPLACE_LABELS, product.marketplace),
        "run": run,
        "provider_label": label_for(PROVIDER_LABELS, run.provider_name if run else None, "—"),
        "analysis_status_label": label_for(
            ANALYSIS_STATUS_LABELS, getattr(run, "status", None) if run else None, "—"
        ),
        "sources": [
            {
                "name": source.source_name,
                "type": label_for(SOURCE_TYPE_LABELS, source.source_type),
                "date": _format_date(source.source_date),
                "uploaded_at": _format_date(source.created_at),
                "hash": source.content_hash[:16],
                "extraction_status": label_for(EXTRACTION_STATUS_LABELS, source.extraction_status),
                "extraction_note": source.extraction_note or "",
                "size_bytes": source.size_bytes,
                "is_demo": bool((source.metadata_json or {}).get("demo")),
            }
            for source in sources
        ],
        "claims": [
            {
                "text": claim.text,
                "type": label_for(CLAIM_TYPE_LABELS, claim.claim_type),
                "source": source_names.get(claim.source_id, "Ручной ввод"),
                "confidence_status": label_for(
                    CONFIDENCE_STATUS_LABELS, claim.confidence_status, "Нужна проверка человеком"
                ),
                "confirmed": claim.user_confirmed,
            }
            for claim in claims
            if not claim.is_rejected
        ],
        "findings": [
            {
                "title": finding.title,
                "type": label_for(FINDING_TYPE_LABELS, finding.finding_type),
                "type_raw": finding.finding_type,
                "severity": label_for(SEVERITY_LABELS, finding.severity),
                "severity_raw": finding.severity,
                "status": label_for(FINDING_STATUS_LABELS, finding.status),
                "status_raw": finding.status,
                "description": finding.description,
                "limitations": finding.limitations,
                "recommended_action": finding.recommended_action,
                "confidence_status": label_for(
                    CONFIDENCE_STATUS_LABELS, finding.confidence_status, "Нужна проверка человеком"
                ),
                "rule_name": rule_label(finding.rule_id),
                # Технические данные: выводятся мелким шрифтом в самом конце находки.
                "rule_technical": f"{finding.rule_id}, версия {finding.rule_version}",
                "sources": [
                    {
                        "name": ref.get("source_name", ""),
                        "excerpt": ref.get("excerpt", ""),
                        "relation": label_for(
                            EVIDENCE_RELATION_LABELS, ref.get("relation"), "связь не определена"
                        ),
                    }
                    for ref in (finding.source_refs or [])
                ],
            }
            for finding in findings
        ],
        "decisions": [
            {
                "created_at": _format_date(action.created_at),
                "user": action.user_email,
                "previous": label_for(FINDING_STATUS_LABELS, action.previous_status, "—")
                if action.previous_status
                else "—",
                "new": label_for(FINDING_STATUS_LABELS, action.new_status, "—")
                if action.new_status
                else "—",
                "comment": action.comment,
                "finding_title": next(
                    (finding.title for finding in findings if finding.id == action.finding_id),
                    "Находка",
                ),
            }
            for action in actions
        ],
        "limitations": (run.limitations if run else [])
        or ["Анализ выполнен по предоставленным материалам."],
        "summary": (run.summary if run else {}) or {},
    }
