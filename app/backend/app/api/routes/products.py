"""CRUD товаров."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_product
from app.core.errors import AppError
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.enums import FindingStatus, SourceType
from app.models.finding import Finding
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import User
from app.schemas.product import ProductCreate, ProductOut, ProductSummary, ProductUpdate
from app.services import sources as source_service

router = APIRouter(prefix="/products", tags=["products"])


def _product_summary(db: Session, product: Product) -> ProductSummary:
    findings_total = db.execute(
        select(func.count())
        .select_from(Finding)
        .where(Finding.product_id == product.id, Finding.archived.is_(False))
    ).scalar_one()
    findings_open = db.execute(
        select(func.count())
        .select_from(Finding)
        .where(
            Finding.product_id == product.id,
            Finding.archived.is_(False),
            Finding.status.in_([FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value]),
        )
    ).scalar_one()
    sources_total = db.execute(
        select(func.count())
        .select_from(Source)
        .where(Source.product_id == product.id)
    ).scalar_one()
    last_run = db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.product_id == product.id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    ).scalars().first()

    return ProductSummary(
        id=product.id,
        name=product.name,
        category=product.category,
        marketplace=product.marketplace,
        sku=product.sku,
        is_demo=product.is_demo,
        created_at=product.created_at,
        updated_at=product.updated_at,
        findings_total=int(findings_total),
        findings_open=int(findings_open),
        sources_total=int(sources_total),
        last_run_at=last_run.created_at if last_run else None,
        last_run_status=last_run.status if last_run else None,
    )


@router.get("", response_model=List[ProductSummary])
def list_products(
    search: Optional[str] = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[ProductSummary]:
    """Список товаров рабочего пространства."""
    stmt = select(Product).where(Product.workspace_id == user.workspace_id)
    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Product.name).like(pattern)
            | func.lower(func.coalesce(Product.sku, "")).like(pattern)
            | func.lower(func.coalesce(Product.category, "")).like(pattern)
        )
    stmt = stmt.order_by(Product.updated_at.desc()).limit(limit).offset(offset)
    products = list(db.execute(stmt).scalars())
    return [_product_summary(db, product) for product in products]


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Product:
    """Создаёт товар и синхронизирует системные источники."""
    product = Product(
        workspace_id=user.workspace_id,
        name=payload.name,
        category=payload.category,
        marketplace=payload.marketplace.value,
        sku=payload.sku,
        description=payload.description,
        attributes=payload.attributes,
        is_demo=False,
    )
    db.add(product)
    db.flush()
    source_service.sync_system_sources(db, product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product: Product = Depends(get_owned_product),
) -> Product:
    """Карточка товара."""
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    payload: ProductUpdate,
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> Product:
    """Изменяет поля товара и обновляет связанные источники."""
    data = payload.model_dump(exclude_unset=True)
    if "marketplace" in data and data["marketplace"] is not None:
        data["marketplace"] = payload.marketplace.value
    for field, value in data.items():
        if value is None and field not in {"attributes"}:
            continue
        setattr(product, field, value)
    db.flush()
    source_service.sync_system_sources(db, product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> None:
    """Удаляет товар вместе с источниками, находками и файлами."""
    from app.services.ingestion import delete_file

    files = list(
        db.execute(select(Source).where(Source.product_id == product.id)).scalars()
    )
    for source in files:
        delete_file(source.file_path)
    db.delete(product)
    db.commit()
