"""Быстрая проверка карточки без регистрации.

Данные не сохраняются: проверка выполняется во временной транзакции, которая
всегда откатывается. Используются только встроенные правила, текст не передаётся
внешним сервисам.
"""

from __future__ import annotations

import re
import uuid
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.enums import ExtractionMethod, ExtractionStatus, Marketplace, SourceType
from app.models.finding import Finding
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import Workspace
from app.providers.mock import MockAnalysisProvider
from app.rules.suggestions import suggest_fix
from app.schemas.quick_check import QuickCheckRequest, QuickCheckResult, QuickFinding
from app.schemas.analysis import SourceRef
from app.services.analysis import run_analysis
from app.services.sources import _hash

MAX_ATTRIBUTE_LINES = 40
_SEPARATORS = (":", "\t", " — ", " – ", " - ", "=")

NOTE = (
    "Проверка выполнена встроенными правилами по тексту, который вы ввели. "
    "Данные не сохраняются. Результат не является юридическим заключением: "
    "решение остаётся за вами."
)


def parse_attributes_text(text: str) -> Dict[str, str]:
    """Разбирает строки «Ключ: значение» в словарь характеристик."""
    attributes: Dict[str, str] = {}
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for separator in _SEPARATORS:
            if separator in line:
                key, _, value = line.partition(separator)
                key, value = key.strip(" -•*"), value.strip()
                if key and value:
                    attributes[key[:80]] = value[:200]
                break
        if len(attributes) >= MAX_ATTRIBUTE_LINES:
            break
    return attributes


def _add_source(db: Session, product: Product, source_type: str, name: str, text: str, metadata=None) -> None:
    db.add(
        Source(
            product_id=product.id,
            workspace_id=product.workspace_id,
            source_type=source_type,
            source_name=name,
            content_hash=_hash(text),
            extraction_method=ExtractionMethod.RULE_BASED.value,
            extraction_status=ExtractionStatus.EXTRACTED.value,
            text_content=text,
            metadata_json=metadata or {},
        )
    )


def run_quick_check(db: Session, payload: QuickCheckRequest) -> QuickCheckResult:
    """Выполняет анализ во временной транзакции и откатывает её."""
    try:
        workspace = Workspace(
            name="Быстрая проверка", slug=f"quick-{uuid.uuid4().hex}", is_demo=True
        )
        db.add(workspace)
        db.flush()

        product = Product(
            workspace_id=workspace.id,
            name=payload.name or "Товар без названия",
            marketplace=Marketplace.OTHER.value,
            description=payload.description,
            attributes=parse_attributes_text(payload.attributes_text),
            is_demo=True,
        )
        db.add(product)
        db.flush()

        if payload.document_text:
            _add_source(
                db, product, SourceType.TECHNICAL_DOCUMENT.value, "Документ", payload.document_text
            )
        if payload.reviews_text:
            rows = [
                {"text": line.strip()}
                for line in payload.reviews_text.splitlines()
                if line.strip()
            ][:100]
            _add_source(
                db,
                product,
                SourceType.REVIEW_EXPORT.value,
                "Отзывы",
                payload.reviews_text,
                {"rows": rows},
            )
        db.flush()

        run = run_analysis(db, product, "quick-check", provider=MockAnalysisProvider())
        findings: List[Finding] = list(
            db.execute(
                select(Finding).where(
                    Finding.analysis_run_id == run.id, Finding.archived.is_(False)
                )
            ).scalars()
        )
        claims_count = len(
            list(db.execute(select(Claim.id).where(Claim.product_id == product.id)).all())
        )

        items = [
            QuickFinding(
                finding_type=finding.finding_type,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                source_refs=[SourceRef(**ref) for ref in (finding.source_refs or [])],
                limitations=finding.limitations or "",
                recommended_action=finding.recommended_action or "",
                rule_id=finding.rule_id or "",
                suggestion=suggest_fix(
                    finding.rule_id, finding.description, finding.recommended_action
                ),
            )
            for finding in findings
        ]
        by_severity: Dict[str, int] = {}
        for item in items:
            by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
        return QuickCheckResult(
            findings=items,
            total=len(items),
            by_severity=by_severity,
            claims_count=claims_count,
            note=NOTE,
        )
    finally:
        db.rollback()
