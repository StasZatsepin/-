"""Работа с источниками товара, включая системные (описание и характеристики)."""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ExtractionMethod, ExtractionStatus, SourceType
from app.models.product import Product
from app.models.source import Source

DESCRIPTION_SOURCE_NAME = "Описание товара"
ATTRIBUTE_SOURCE_NAME = "Таблица характеристик"


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def find_system_source(
    db: Session, product_id: str, source_type: str
) -> Optional[Source]:
    stmt = select(Source).where(
        Source.product_id == product_id,
        Source.source_type == source_type,
    )
    return db.execute(stmt).scalars().first()


def sync_description_source(db: Session, product: Product) -> Source:
    """Создаёт или обновляет источник с описанием товара."""
    text = product.description or ""
    source = find_system_source(db, product.id, SourceType.PRODUCT_DESCRIPTION.value)
    if source is None:
        source = Source(
            product_id=product.id,
            workspace_id=product.workspace_id,
            source_type=SourceType.PRODUCT_DESCRIPTION.value,
            source_name=DESCRIPTION_SOURCE_NAME,
            content_hash=_hash(text),
            extraction_method=ExtractionMethod.RULE_BASED.value,
            extraction_status=(
                ExtractionStatus.EXTRACTED if text.strip() else ExtractionStatus.EMPTY
            ),
            text_content=text,
            metadata_json={"generated": True, "role": "description"},
        )
        db.add(source)
        db.flush()
        return source

    source.text_content = text
    source.content_hash = _hash(text)
    source.extraction_status = (
        ExtractionStatus.EXTRACTED if text.strip() else ExtractionStatus.EMPTY
    )
    metadata = dict(source.metadata_json or {})
    metadata.update({"generated": True, "role": "description"})
    source.metadata_json = metadata
    db.flush()
    return source


def sync_attribute_source(db: Session, product: Product) -> Source:
    """Создаёт или обновляет источник с таблицей характеристик."""
    attributes: Dict[str, object] = dict(product.attributes or {})
    lines = [f"{key}: {value}" for key, value in attributes.items()]
    text = "\n".join(lines)
    source = find_system_source(db, product.id, SourceType.ATTRIBUTE_SHEET.value)
    if source is None:
        source = Source(
            product_id=product.id,
            workspace_id=product.workspace_id,
            source_type=SourceType.ATTRIBUTE_SHEET.value,
            source_name=ATTRIBUTE_SOURCE_NAME,
            content_hash=_hash(text),
            extraction_method=ExtractionMethod.RULE_BASED.value,
            extraction_status=(
                ExtractionStatus.EXTRACTED if text.strip() else ExtractionStatus.EMPTY
            ),
            text_content=text,
            metadata_json={"generated": True, "role": "attributes", "attributes": attributes},
        )
        db.add(source)
        db.flush()
        return source

    source.text_content = text
    source.content_hash = _hash(text)
    source.extraction_status = (
        ExtractionStatus.EXTRACTED if text.strip() else ExtractionStatus.EMPTY
    )
    metadata = dict(source.metadata_json or {})
    metadata.update({"generated": True, "role": "attributes", "attributes": attributes})
    source.metadata_json = metadata
    db.flush()
    return source


def sync_system_sources(db: Session, product: Product) -> List[Source]:
    """Приводит системные источники товара в актуальное состояние."""
    description = sync_description_source(db, product)
    attributes = sync_attribute_source(db, product)
    return [description, attributes]


def delete_source(db: Session, source: Source) -> None:
    """Удаляет источник и его файл."""
    from app.services.ingestion import delete_file

    file_path = source.file_path
    db.delete(source)
    db.flush()
    delete_file(file_path)
