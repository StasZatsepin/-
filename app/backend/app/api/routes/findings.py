"""Находки: фильтрация, изменение статуса и история решений."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_finding, get_owned_product
from app.core.errors import AppError
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.enums import FindingStatus
from app.models.finding import Finding
from app.models.product import Product
from app.models.review_action import ReviewAction
from app.models.workspace import User
from app.schemas.analysis import FindingOut, FindingUpdate, ReviewActionOut

router = APIRouter(tags=["findings"])


@router.get("/products/{product_id}/findings", response_model=List[FindingOut])
def list_findings(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity: Optional[str] = Query(default=None),
    finding_type: Optional[str] = Query(default=None, alias="type"),
    include_archived: bool = Query(default=False),
) -> List[FindingOut]:
    """Список находок с фильтрами по статусу, серьёзности и типу."""
    stmt = select(Finding).where(Finding.product_id == product.id)
    if not include_archived:
        stmt = stmt.where(Finding.archived.is_(False))
    if status_filter:
        values = [value.strip() for value in status_filter.split(",") if value.strip()]
        for value in values:
            if value not in {item.value for item in FindingStatus}:
                raise AppError(
                    "VALIDATION_ERROR",
                    "Неизвестный статус: "
                    + value
                    + ". Допустимые: "
                    + ", ".join(item.value for item in FindingStatus),
                )
        stmt = stmt.where(Finding.status.in_(values))
    if severity:
        stmt = stmt.where(Finding.severity == severity.strip())
    if finding_type:
        stmt = stmt.where(Finding.finding_type == finding_type.strip())

    findings = list(
        db.execute(
            stmt.order_by(
                Finding.archived.asc(), Finding.created_at.desc()
            )
        ).scalars()
    )
    return [FindingOut.model_validate(finding) for finding in findings]


@router.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(finding: Finding = Depends(get_owned_finding)) -> FindingOut:
    """Карточка находки."""
    return FindingOut.model_validate(finding)


@router.patch("/findings/{finding_id}", response_model=FindingOut)
def update_finding(
    payload: FindingUpdate,
    finding: Finding = Depends(get_owned_finding),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FindingOut:
    """Меняет статус находки и сохраняет запись в истории действий."""
    new_status = payload.status.value if payload.status else None
    comment = (payload.comment or "").strip()

    if new_status is not None and new_status != finding.status:
        previous = finding.status
        finding.status = new_status
        db.add(
            ReviewAction(
                finding_id=finding.id,
                product_id=finding.product_id,
                workspace_id=finding.workspace_id,
                user_id=user.id,
                user_email=user.email,
                action="status_change",
                previous_status=previous,
                new_status=new_status,
                comment=comment,
            )
        )
    elif comment:
        db.add(
            ReviewAction(
                finding_id=finding.id,
                product_id=finding.product_id,
                workspace_id=finding.workspace_id,
                user_id=user.id,
                user_email=user.email,
                action="comment",
                previous_status=finding.status,
                new_status=finding.status,
                comment=comment,
            )
        )

    db.commit()
    db.refresh(finding)
    return FindingOut.model_validate(finding)


@router.get("/findings/{finding_id}/history", response_model=List[ReviewActionOut])
def finding_history(
    finding: Finding = Depends(get_owned_finding),
    db: Session = Depends(get_db),
) -> List[ReviewActionOut]:
    """История решений по находке."""
    actions = list(
        db.execute(
            select(ReviewAction)
            .where(ReviewAction.finding_id == finding.id)
            .order_by(ReviewAction.created_at.asc())
        ).scalars()
    )
    return [ReviewActionOut.model_validate(action) for action in actions]


@router.get("/reviews/history", response_model=List[ReviewActionOut])
def workspace_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
) -> List[ReviewActionOut]:
    """История действий пользователя по всем находкам рабочего пространства."""
    actions = list(
        db.execute(
            select(ReviewAction)
            .where(ReviewAction.workspace_id == user.workspace_id)
            .order_by(ReviewAction.created_at.desc())
            .limit(limit)
        ).scalars()
    )
    return [ReviewActionOut.model_validate(action) for action in actions]


@router.get("/reviews/overview")
def reviews_overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Сводка по проверкам рабочего пространства."""
    runs = list(
        db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.workspace_id == user.workspace_id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(50)
        ).scalars()
    )
    products = {
        product.id: product.name
        for product in db.execute(
            select(Product).where(Product.workspace_id == user.workspace_id)
        ).scalars()
    }
    return {
        "runs": [
            {
                "id": run.id,
                "product_id": run.product_id,
                "product_name": products.get(run.product_id, "Товар удалён"),
                "status": run.status,
                "provider_name": run.provider_name,
                "rules_version": run.rules_version,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "summary": run.summary or {},
                "limitations": run.limitations or [],
            }
            for run in runs
        ]
    }
