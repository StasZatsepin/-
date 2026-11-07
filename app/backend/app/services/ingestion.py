"""Загрузка и разбор источников: проверка файла, извлечение текста, метаданные."""

from __future__ import annotations

import csv
import hashlib
import io
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.errors import AppError
from app.models.enums import ExtractionMethod, ExtractionStatus, SourceType

logger = logging.getLogger("app.services.ingestion")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv"}

# Синонимы названий источников (для автоматического определения типа)
DOCUMENT_NAME_HINTS = (
    ("сертифик", SourceType.TECHNICAL_DOCUMENT),
    ("декларац", SourceType.TECHNICAL_DOCUMENT),
    ("паспорт", SourceType.TECHNICAL_DOCUMENT),
    ("инструкц", SourceType.TECHNICAL_DOCUMENT),
    ("руководств", SourceType.TECHNICAL_DOCUMENT),
    ("техническ", SourceType.TECHNICAL_DOCUMENT),
    ("отзыв", SourceType.REVIEW_EXPORT),
    ("review", SourceType.REVIEW_EXPORT),
    ("отзывы", SourceType.REVIEW_EXPORT),
    ("выгрузка", SourceType.REVIEW_EXPORT),
)

DOCUMENT_METADATA_FIELDS = (
    "document_type",
    "document_number",
    "document_name",
    "document_date",
    "valid_until",
    "applies_to_model",
    "scope_note",
    "issuer",
)


@dataclass
class ExtractedContent:
    """Результат разбора файла."""

    text: str = ""
    status: ExtractionStatus = ExtractionStatus.EXTRACTED
    method: ExtractionMethod = ExtractionMethod.RULE_BASED
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


def _decode_bytes(raw: bytes) -> str:
    """Декодирует байты с безопасным откатом на cp1251."""
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def validate_upload(filename: str, content: bytes, mime_type: Optional[str]) -> str:
    """Проверяет расширение, MIME-тип и размер. Возвращает безопасное расширение."""
    suffix = Path(filename or "").suffix.lower()
    if not suffix:
        raise AppError(
            "VALIDATION_ERROR",
            "У файла нет расширения. Поддерживаются: "
            + ", ".join(sorted(settings.allowed_upload_extensions)),
        )
    if suffix in IMAGE_EXTENSIONS:
        raise AppError(
            "UNSUPPORTED_MEDIA_TYPE",
            "Изображения пока не обрабатываются: требуется отдельный этап OCR. "
            "Загрузите текстовый файл, PDF с текстовым слоем или введите данные вручную.",
        )
    if suffix not in settings.allowed_upload_extensions:
        raise AppError(
            "UNSUPPORTED_MEDIA_TYPE",
            f"Формат «{suffix}» не поддерживается. Допустимые форматы: "
            + ", ".join(sorted(settings.allowed_upload_extensions))
            + ".",
        )
    if len(content) == 0:
        raise AppError("VALIDATION_ERROR", "Файл пустой, загружать нечего.")
    if len(content) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes / (1024 * 1024)
        raise AppError(
            "PAYLOAD_TOO_LARGE",
            f"Размер файла превышает допустимые {limit_mb:.0f} МБ.",
        )
    if mime_type and mime_type.lower() not in settings.allowed_upload_mimetypes:
        # MIME от клиента не доверяем, но и не отвергаем: решение по расширению.
        logger.info("Необычный MIME-тип %s для файла %s", mime_type, filename)
    return suffix


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def guess_source_type(filename: str, declared: Optional[str] = None) -> str:
    """Определяет тип источника по имени файла или по запросу пользователя."""
    if declared:
        return declared
    lowered = (filename or "").lower()
    for marker, source_type in DOCUMENT_NAME_HINTS:
        if marker in lowered:
            return source_type.value
    suffix = Path(lowered).suffix
    if suffix == ".csv":
        return SourceType.REVIEW_EXPORT.value
    if suffix in {".txt", ".md"}:
        return SourceType.TECHNICAL_DOCUMENT.value
    return SourceType.OTHER.value


def extract_text(filename: str, content: bytes) -> ExtractedContent:
    """Извлекает текст из поддерживаемых форматов."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return _extract_text_file(content, suffix)
    if suffix == ".pdf":
        return _extract_pdf(content)
    if suffix == ".xlsx":
        return _extract_xlsx(content)
    return ExtractedContent(
        status=ExtractionStatus.FAILED,
        note="Для этого формата нет средства извлечения текста.",
    )


def _extract_text_file(content: bytes, suffix: str = "") -> ExtractedContent:
    text = _decode_bytes(content)
    metadata: Dict[str, Any] = {}
    note = ""
    status = ExtractionStatus.EXTRACTED

    if suffix == ".csv" or _looks_like_csv(text):
        rows = _parse_csv(text)
        metadata["rows"] = rows
        metadata["row_count"] = len(rows)
        note = "Файл разобран как CSV: строки сохранены для проверки."

    if not text.strip():
        status = ExtractionStatus.EMPTY
        note = note or "Файл не содержит текста."

    return ExtractedContent(
        text=text, status=status, method=ExtractionMethod.RULE_BASED, note=note, metadata=metadata
    )


def _looks_like_csv(text: str) -> bool:
    sample = "\n".join(text.splitlines()[:5])
    if not sample.strip():
        return False
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return False
    return len(dialect.delimiter) == 1


def _parse_csv(text: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    try:
        dialect = csv.Sniffer().sniff("\n".join(text.splitlines()[:20]), delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    for row in reader:
        rows.append(
            {
                (key or "").strip(): ("" if value is None else str(value).strip())
                for key, value in row.items()
            }
        )
    return rows[:2000]


def _extract_pdf(content: bytes) -> ExtractedContent:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - зависимость ставится в requirements
        return ExtractedContent(
            status=ExtractionStatus.FAILED,
            note="Библиотека pypdf не установлена, текст PDF извлечь не удалось.",
        )
    try:
        reader = PdfReader(io.BytesIO(content))
        pages: List[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n\n".join(pages).strip()
        metadata = {"page_count": len(reader.pages)}
        if not text:
            return ExtractedContent(
                text="",
                status=ExtractionStatus.NEEDS_OCR,
                note=(
                    "В PDF нет текстового слоя (вероятно, это скан). "
                    "Требуется отдельный этап OCR — сейчас текст документа недоступен."
                ),
                method=ExtractionMethod.RULE_BASED,
                metadata=metadata,
            )
        return ExtractedContent(
            text=text,
            status=ExtractionStatus.EXTRACTED,
            method=ExtractionMethod.RULE_BASED,
            note=f"Извлечено страниц: {len(reader.pages)}.",
            metadata=metadata,
        )
    except Exception as exc:  # pragma: no cover - зависит от содержимого файла
        logger.warning("Не удалось прочитать PDF: %s", type(exc).__name__)
        return ExtractedContent(
            status=ExtractionStatus.FAILED,
            note="PDF не удалось прочитать: возможно, файл повреждён или защищён паролем.",
        )


def _extract_xlsx(content: bytes) -> ExtractedContent:
    try:
        from openpyxl import load_workbook
    except ImportError:  # pragma: no cover
        return ExtractedContent(
            status=ExtractionStatus.FAILED,
            note="Библиотека openpyxl не установлена, XLSX не обработан.",
        )
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        lines: List[str] = []
        sheet_names: List[str] = []
        for sheet in workbook.worksheets:
            sheet_names.append(sheet.title)
            lines.append(f"# Лист: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                values = ["" if cell is None else str(cell) for cell in row]
                if any(value.strip() for value in values):
                    lines.append(" | ".join(values))
        text = "\n".join(lines).strip()
        metadata = {"sheets": sheet_names}
        if not text:
            return ExtractedContent(
                status=ExtractionStatus.EMPTY,
                note="Книга пуста или содержит только пустые ячейки.",
                metadata=metadata,
            )
        return ExtractedContent(
            text=text,
            status=ExtractionStatus.EXTRACTED,
            method=ExtractionMethod.RULE_BASED,
            note=f"Обработано листов: {len(sheet_names)}.",
            metadata=metadata,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Не удалось прочитать XLSX: %s", type(exc).__name__)
        return ExtractedContent(
            status=ExtractionStatus.FAILED,
            note="XLSX не удалось прочитать: возможно, файл повреждён или защищён паролем.",
        )


def store_file(product_id: str, suffix: str, content: bytes) -> Optional[str]:
    """Сохраняет файл под сгенерированным именем (исходное имя не используется).

    Если ``STORE_ORIGINAL_FILES=false`` (облачное демо с непостоянным диском), файл
    на диск не пишется и возвращается ``None``: извлечённый текст, хеш и метаданные
    всё равно сохраняются в базе, и анализ работает как обычно.
    """
    if not settings.store_original_files:
        return None

    import uuid

    directory = settings.storage_dir / product_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    path = directory / filename
    path.write_bytes(content)
    return str(path)


def delete_file(file_path: Optional[str]) -> None:
    """Удаляет файл с диска, если он существует."""
    if not file_path:
        return
    try:
        Path(file_path).unlink(missing_ok=True)
    except OSError:  # pragma: no cover
        logger.warning("Не удалось удалить файл %s", file_path)


def parse_metadata_fields(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Приводит произвольные метаданные документа к ожидаемым полям."""
    result: Dict[str, Any] = {}
    for field_name in DOCUMENT_METADATA_FIELDS:
        value = (raw or {}).get(field_name)
        if value in (None, ""):
            continue
        if field_name in {"document_date", "valid_until"}:
            parsed = parse_date(value)
            if parsed:
                result[field_name] = parsed.isoformat()
            continue
        result[field_name] = str(value)[:1000]
    return result


def parse_date(value: Any) -> Optional[date]:
    """Пытается разобрать дату из строки."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None
