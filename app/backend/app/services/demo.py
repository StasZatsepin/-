"""Демонстрационные данные.

Все примеры синтетические и явно помечены: они не относятся к реальным товарам,
документам или отзывам. Цель демо — показать работу проверок на управляемом наборе.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, settings
from app.core.security import hash_password
from app.models.enums import (
    ExtractionMethod,
    ExtractionStatus,
    Marketplace,
    SourceType,
    UserRole,
)
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import User, Workspace

logger = logging.getLogger("app.services.demo")

SAMPLE_DIR = PROJECT_ROOT / "app" / "sample_data"

DEMO_PRODUCT_NAME = "ДЕМО: беспроводные наушники X-500 (синтетические данные)"

DEMO_ATTRIBUTES = {
    "battery_life_hours": 30,
    "weight_g": 250,
    "warranty_months": 24,
    "model": "DEMO-X500",
    "material": "пластик, силиконовые амбушюры",
    "country": "Китай",
}


def _read_sample(name: str) -> str:
    path = SAMPLE_DIR / name
    if not path.exists():
        logger.warning("Демо-файл %s не найден", path)
        return ""
    return path.read_text(encoding="utf-8")


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def ensure_demo_workspace(db: Session) -> User:
    """Создаёт демонстрационное рабочее пространство и пользователя (если их нет)."""
    user = db.execute(
        select(User).where(User.email == settings.demo_user_email)
    ).scalars().first()
    if user is not None:
        return user

    workspace = Workspace(
        name=settings.demo_workspace_name,
        slug="demo-workspace",
        is_demo=True,
    )
    db.add(workspace)
    db.flush()

    user = User(
        email=settings.demo_user_email,
        password_hash=hash_password(settings.demo_user_password),
        display_name="Демо-пользователь",
        role=UserRole.USER.value,
        workspace_id=workspace.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_demo_data(db: Session, user: Optional[User] = None) -> Product:
    """Создаёт демонстрационный товар вместе с источниками и анализом."""
    if user is None:
        user = ensure_demo_workspace(db)

    existing = db.execute(
        select(Product).where(
            Product.workspace_id == user.workspace_id,
            Product.name == DEMO_PRODUCT_NAME,
        )
    ).scalars().first()
    if existing is not None:
        return existing

    description = _read_sample("demo_description.txt")
    product = Product(
        workspace_id=user.workspace_id,
        name=DEMO_PRODUCT_NAME,
        category="electronics / наушники",
        marketplace=Marketplace.DEMO.value,
        sku="DEMO-SKU-0001",
        description=description,
        attributes=DEMO_ATTRIBUTES,
        is_demo=True,
    )
    db.add(product)
    db.flush()

    _add_source(
        db,
        product,
        source_type=SourceType.TECHNICAL_DOCUMENT,
        source_name="ДЕМО-СЕРТИФИКАТ № ДЕМО-СС-001",
        text=_read_sample("demo_certificate.txt"),
        metadata={
            "document_type": "сертификат соответствия",
            "document_number": "ДЕМО-СС-001",
            "document_date": "2024-03-15",
            "valid_until": "2027-03-14",
            "applies_to_model": "DEMO-X500",
            "issuer": "ООО «Демо Электроника» (условное название)",
            "scope_note": "Синтетический документ для демонстрации.",
            "demo": True,
        },
        source_date="2024-03-15",
    )

    _add_source(
        db,
        product,
        source_type=SourceType.TECHNICAL_DOCUMENT,
        source_name="ДЕМО-ПАСПОРТ ИЗДЕЛИЯ № ДЕМО-ПИ-002",
        text=_read_sample("demo_passport_other_model.txt"),
        metadata={
            "document_type": "паспорт изделия",
            "document_number": "ДЕМО-ПИ-002",
            "document_date": "2024-06-01",
            "applies_to_model": "DEMO-X700",
            "scope_note": "Синтетический документ для другой модификации.",
            "demo": True,
        },
        source_date="2024-06-01",
    )

    reviews_text = _read_sample("demo_reviews.csv")
    _add_source(
        db,
        product,
        source_type=SourceType.REVIEW_EXPORT,
        source_name="ДЕМО-ВЫГРУЗКА ОТЗЫВОВ (синтетические отзывы)",
        text=reviews_text,
        metadata={
            "rows": _parse_demo_reviews(reviews_text),
            "demo": True,
            "note": "Отзывы вымышлены и созданы для демонстрации.",
        },
    )

    db.commit()
    db.refresh(product)

    from app.services.analysis import run_analysis

    run_analysis(db, product, user_email=user.email)
    db.commit()
    db.refresh(product)
    return product


def _add_source(
    db: Session,
    product: Product,
    source_type: str,
    source_name: str,
    text: str,
    metadata: dict,
    source_date: str | None = None,
) -> Source:
    parsed_date = None
    if source_date:
        try:
            parsed_date = datetime.strptime(source_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            parsed_date = None

    source = Source(
        product_id=product.id,
        workspace_id=product.workspace_id,
        source_type=source_type,
        source_name=source_name,
        source_date=parsed_date,
        content_hash=_hash(text),
        extraction_method=ExtractionMethod.SEEDED.value,
        extraction_status=(
            ExtractionStatus.EXTRACTED if text.strip() else ExtractionStatus.EMPTY
        ),
        extraction_note="Демонстрационные синтетические данные.",
        text_content=text,
        metadata_json=metadata,
    )
    db.add(source)
    db.flush()
    return source


def _parse_demo_reviews(text: str) -> List[dict]:
    import csv
    import io

    if not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append({(key or "").strip(): (value or "").strip() for key, value in row.items()})
    return rows
