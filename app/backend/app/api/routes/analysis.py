"""Запуски анализа, утверждения и доказательства."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_owned_claim,
    get_owned_product,
    get_owned_run,
)
from app.core.errors import AppError
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.claim import Claim
from app.models.enums import ExtractionMethod, FindingStatus
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import User
from app.schemas.analysis import (
    AnalysisRunDetail,
    AnalysisRunOut,
    ClaimCreate,
    ClaimOut,
    ClaimUpdate,
    EvidenceOut,
)
from app.schemas.product import ProductOut
from app.services.analysis import run_analysis

router = APIRouter(tags=["analysis"])


def _claim_out(claim: Claim, source_names: dict) -> ClaimOut:
    return ClaimOut(
        id=claim.id,
        product_id=claim.product_id,
        source_id=claim.source_id,
        source_name=source_names.get(claim.source_id),
        text=claim.text,
        claim_type=claim.claim_type,
        source_excerpt=claim.source_excerpt,
        extraction_method=claim.extraction_method,
        model_version=claim.model_version,
        confidence_label=claim.confidence_label,
        confidence_status=claim.confidence_status,
        user_confirmed=claim.user_confirmed,
        is_rejected=claim.is_rejected,
        numeric_value=claim.numeric_value,
        numeric_unit=claim.numeric_unit,
        numeric_dimension=claim.numeric_dimension,
        numeric_comparator=claim.numeric_comparator,
        created_at=claim.created_at,
    )


def _evidence_out(evidence: Evidence, source_names: dict) -> EvidenceOut:
    return EvidenceOut(
        id=evidence.id,
        product_id=evidence.product_id,
        source_id=evidence.source_id,
        source_name=source_names.get(evidence.source_id),
        claim_id=evidence.claim_id,
        evidence_type=evidence.evidence_type,
        excerpt=evidence.excerpt,
        relation=evidence.relation,
        relevance_note=evidence.relevance_note,
        date=evidence.date,
        created_at=evidence.created_at,
    )


@router.post(
    "/products/{product_id}/analysis-runs",
    response_model=AnalysisRunOut,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_run(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisRunOut:
    """Запускает проверку товара: детерминированные правила + провайдер (по умолчанию локальный)."""
    try:
        run = run_analysis(db, product, user_email=user.email)
        db.commit()
    except Exception:
        db.rollback()
        raise AppError(
            "INTERNAL_ERROR",
            "Проверка не завершилась из-за внутренней ошибки. Попробуйте ещё раз "
            "или обратитесь к разработчику.",
        )
    db.refresh(run)
    return AnalysisRunOut.model_validate(run)


@router.get("/products/{product_id}/analysis-runs", response_model=List[AnalysisRunOut])
def list_analysis_runs(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> List[AnalysisRunOut]:
    """История запусков проверок товара."""
    runs = list(
        db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.product_id == product.id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(50)
        ).scalars()
    )
    return [AnalysisRunOut.model_validate(run) for run in runs]


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunDetail)
def get_analysis_run(
    run: AnalysisRun = Depends(get_owned_run),
    db: Session = Depends(get_db),
) -> AnalysisRunDetail:
    """Статус и результат конкретного запуска проверки."""
    product = db.get(Product, run.product_id)
    findings = list(
        db.execute(
            select(Finding)
            .where(Finding.analysis_run_id == run.id)
            .order_by(Finding.severity.asc(), Finding.created_at.asc())
        ).scalars()
    )
    claims_count = db.execute(
        select(Claim).where(Claim.product_id == run.product_id)
    ).scalars().all()
    sources_count = db.execute(
        select(Source).where(Source.product_id == run.product_id)
    ).scalars().all()
    return AnalysisRunDetail(
        **AnalysisRunOut.model_validate(run).model_dump(),
        product_name=product.name if product else "",
        findings=[
            {
                "id": finding.id,
                "product_id": finding.product_id,
                "claim_id": finding.claim_id,
                "analysis_run_id": finding.analysis_run_id,
                "finding_type": finding.finding_type,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "source_evidence_ids": finding.source_evidence_ids or [],
                "source_refs": finding.source_refs or [],
                "limitations": finding.limitations or "",
                "recommended_action": finding.recommended_action or "",
                "confidence_status": finding.confidence_status,
                "status": finding.status,
                "rule_id": finding.rule_id,
                "rule_version": finding.rule_version,
                "origin": finding.origin,
                "archived": finding.archived,
                "created_at": finding.created_at,
                "updated_at": finding.updated_at,
            }
            for finding in findings
        ],
        claims_count=len(claims_count),
        sources_count=len(sources_count),
    )


@router.get("/products/{product_id}/claims", response_model=List[ClaimOut])
def list_claims(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> List[ClaimOut]:
    """Утверждения товара с привязкой к источникам."""
    claims = list(
        db.execute(
            select(Claim)
            .where(Claim.product_id == product.id)
            .order_by(Claim.created_at.asc())
        ).scalars()
    )
    source_names = {
        source.id: source.source_name
        for source in db.execute(
            select(Source).where(Source.product_id == product.id)
        ).scalars()
    }
    return [_claim_out(claim, source_names) for claim in claims]


@router.post(
    "/products/{product_id}/claims",
    response_model=ClaimOut,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    payload: ClaimCreate,
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> ClaimOut:
    """Добавляет утверждение вручную."""
    claim = Claim(
        product_id=product.id,
        workspace_id=product.workspace_id,
        source_id=None,
        text=payload.text,
        claim_type=payload.claim_type,
        source_excerpt=payload.source_excerpt or payload.text,
        extraction_method=ExtractionMethod.MANUAL.value,
        user_confirmed=True,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return _claim_out(claim, {})


@router.patch("/claims/{claim_id}", response_model=ClaimOut)
def update_claim(
    payload: ClaimUpdate,
    claim: Claim = Depends(get_owned_claim),
    db: Session = Depends(get_db),
) -> ClaimOut:
    """Редактирует утверждение: текст, тип, подтверждение пользователем."""
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is None:
            continue
        setattr(claim, field, value)
    if data.get("user_confirmed"):
        claim.confidence_status = "supported_by_provided_source"
    db.commit()
    db.refresh(claim)
    return _claim_out(claim, {})


@router.delete("/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim: Claim = Depends(get_owned_claim),
    db: Session = Depends(get_db),
) -> None:
    """Удаляет утверждение."""
    db.delete(claim)
    db.commit()


@router.get("/products/{product_id}/evidence", response_model=List[EvidenceOut])
def list_evidence(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> List[EvidenceOut]:
    """Доказательства товара."""
    evidence = list(
        db.execute(
            select(Evidence)
            .where(Evidence.product_id == product.id)
            .order_by(Evidence.created_at.asc())
        ).scalars()
    )
    source_names = {
        source.id: source.source_name
        for source in db.execute(
            select(Source).where(Source.product_id == product.id)
        ).scalars()
    }
    return [_evidence_out(item, source_names) for item in evidence]


@router.get("/products/{product_id}/summary")
def product_summary(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> dict:
    """Краткая сводка по товару для карточки."""
    findings = list(
        db.execute(
            select(Finding).where(
                Finding.product_id == product.id, Finding.archived.is_(False)
            )
        ).scalars()
    )
    sources = list(
        db.execute(select(Source).where(Source.product_id == product.id)).scalars()
    )
    by_severity: dict = {}
    by_type: dict = {}
    by_status: dict = {}
    for finding in findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        by_type[finding.finding_type] = by_type.get(finding.finding_type, 0) + 1
        by_status[finding.status] = by_status.get(finding.status, 0) + 1
    return {
        "product": ProductOut.model_validate(product).model_dump(),
        "findings_total": len(findings),
        "findings_open": sum(
            1
            for finding in findings
            if finding.status in {FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value}
        ),
        "by_severity": by_severity,
        "by_type": by_type,
        "by_status": by_status,
        "sources_total": len(sources),
    }
