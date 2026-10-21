"""Загрузка и просмотр источников."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_product, get_owned_source
from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.enums import SourceType
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import User
from app.schemas.source import SourceCreateManual, SourceOut
from app.services import ingestion

router = APIRouter(tags=["sources"])

PREVIEW_LIMIT = 600


def _to_out(source: Source) -> SourceOut:
    text = source.text_content or ""
    return SourceOut(
        id=source.id,
        product_id=source.product_id,
        source_type=source.source_type,
        source_name=source.source_name,
        source_date=source.source_date,
        source_uri=source.source_uri,
        content_hash=source.content_hash,
        extraction_method=source.extraction_method,
        extraction_status=source.extraction_status,
        extraction_note=source.extraction_note or "",
        mime_type=source.mime_type,
        size_bytes=source.size_bytes,
        uploaded_at=source.created_at,
        metadata=dict(source.metadata_json or {}),
        text_preview=text[:PREVIEW_LIMIT],
        text_length=len(text),
    )


@router.get("/products/{product_id}/sources", response_model=List[SourceOut])
def list_sources(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> List[SourceOut]:
    """Список источников товара."""
    sources = list(
        db.execute(
            select(Source)
            .where(Source.product_id == product.id)
            .order_by(Source.created_at.asc())
        ).scalars()
    )
    return [_to_out(source) for source in sources]


@router.post(
    "/products/{product_id}/sources",
    response_model=SourceOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    source_type: Optional[str] = Form(default=None),
    source_name: Optional[str] = Form(default=None),
    source_date: Optional[str] = Form(default=None),
    applies_to_model: Optional[str] = Form(default=None),
    document_number: Optional[str] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    valid_until: Optional[str] = Form(default=None),
    scope_note: Optional[str] = Form(default=None),
) -> SourceOut:
    """Загружает файл-источник: TXT, CSV, PDF (с текстом), XLSX, MD."""
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise AppError(
            "PAYLOAD_TOO_LARGE",
            f"Размер файла превышает допустимые "
            f"{settings.max_upload_bytes / (1024 * 1024):.0f} МБ.",
        )

    suffix = ingestion.validate_upload(file.filename or "", content, file.content_type)
    extracted = ingestion.extract_text(file.filename or "", content)

    declared_type = None
    if source_type:
        try:
            declared_type = SourceType(source_type).value
        except ValueError:
            raise AppError(
                "VALIDATION_ERROR",
                "Неизвестный тип источника. Допустимые значения: "
                + ", ".join(item.value for item in SourceType),
            )

    metadata = ingestion.parse_metadata_fields(
        {
            "document_type": document_type,
            "document_number": document_number,
            "valid_until": valid_until,
            "applies_to_model": applies_to_model,
            "scope_note": scope_note,
            "document_date": source_date,
        }
    )
    metadata.update(extracted.metadata or {})

    stored_path = ingestion.store_file(product.id, suffix, content)
    parsed_date = ingestion.parse_date(source_date) if source_date else None

    source = Source(
        product_id=product.id,
        workspace_id=product.workspace_id,
        source_type=ingestion.guess_source_type(file.filename or "", declared_type),
        source_name=(source_name or file.filename or "Загруженный файл")[:255],
        source_date=None,
        content_hash=ingestion.content_hash(content),
        extraction_method=extracted.method.value,
        extraction_status=extracted.status.value,
        extraction_note=extracted.note,
        file_path=stored_path,
        mime_type=file.content_type,
        size_bytes=len(content),
        text_content=extracted.text,
        metadata_json=metadata,
    )
    if parsed_date:
        source.source_date = parsed_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _to_out(source)


@router.post(
    "/products/{product_id}/sources/manual",
    response_model=SourceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_source(
    payload: SourceCreateManual,
    product: Product = Depends(get_owned_product),
    db: Session = Depends(get_db),
) -> SourceOut:
    """Создаёт источник вручную: заметка, отзыв или текст документа."""
    text = payload.text
    rows: List[dict] = []
    if payload.source_type == SourceType.REVIEW_EXPORT.value:
        rows = _split_reviews(text)

    metadata = payload.metadata.model_dump(exclude_none=True)
    metadata.update({"rows": rows} if rows else {})

    source = Source(
        product_id=product.id,
        workspace_id=product.workspace_id,
        source_type=payload.source_type.value,
        source_name=payload.source_name,
        source_date=payload.source_date,
        source_uri=payload.source_uri,
        content_hash=ingestion.content_hash(text.encode("utf-8")),
        extraction_method="manual",
        extraction_status="extracted",
        extraction_note="Источник введён вручную.",
        mime_type="text/plain",
        size_bytes=len(text.encode("utf-8")),
        text_content=text,
        metadata_json=metadata,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _to_out(source)


def _split_reviews(text: str) -> List[dict]:
    """Разбивает ручной ввод отзывов на отдельные записи."""
    reviews: List[dict] = []
    for block in (part.strip() for part in text.split("\n\n")):
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        date_value = None
        rating = None
        body_lines = list(lines)
        if "—" in lines[0] and len(lines[0].split("—")) > 1:
            head, tail = lines[0].split("—", 1)
            head = head.strip()
            tail = tail.strip()
            if head.lower().startswith("дата"):
                date_value = head.split(":", 1)[-1].strip()
                body_lines = [tail] + lines[1:]
            elif head.lower().startswith("оценка"):
                rating = head.split(":", 1)[-1].strip()
                body_lines = [tail] + lines[1:]
        reviews.append(
            {
                "text": "\n".join(body_lines),
                "date": date_value or "",
                "rating": rating or "",
            }
        )
    return reviews


@router.get("/sources/{source_id}", response_model=SourceOut)
def get_source(source: Source = Depends(get_owned_source)) -> SourceOut:
    """Метаданные источника."""
    return _to_out(source)


@router.get("/sources/{source_id}/text")
def get_source_text(source: Source = Depends(get_owned_source)) -> dict:
    """Полный извлечённый текст источника."""
    return {
        "id": source.id,
        "source_name": source.source_name,
        "text": source.text_content or "",
        "extraction_status": source.extraction_status,
        "extraction_note": source.extraction_note or "",
    }


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source: Source = Depends(get_owned_source),
    db: Session = Depends(get_db),
) -> None:
    """Удаляет источник вместе с файлом и связанными записями."""
    from app.services.sources import delete_source as remove_source

    remove_source(db, source)
    db.commit()
