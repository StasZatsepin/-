"""Импорт каталога товаров из CSV и XLSX.

Файл разбирается в память и не сохраняется. Сопоставление столбцов задаёт
пользователь; сервис лишь предлагает вариант по названиям столбцов.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from app.core.errors import AppError
from app.models.enums import Marketplace
from app.services.quick_check import parse_attributes_text

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 2000
MAX_COLUMNS = 60
PREVIEW_ROWS = 5

FIELDS = ("name", "sku", "marketplace", "category", "description", "attributes")

# Подсказки для автоматического сопоставления: нижний регистр, без пробелов по краям.
_HINTS: Dict[str, Iterable[str]] = {
    "name": ("название", "наименование", "товар", "name", "title"),
    "sku": ("sku", "артикул", "арт", "код товара", "article"),
    "marketplace": ("маркетплейс", "площадка", "marketplace"),
    "category": ("категория", "category", "раздел"),
    "description": ("описание", "description", "аннотация"),
    "attributes": ("характеристики", "атрибуты", "attributes", "свойства"),
}

_MARKETPLACES = {
    "ozon": Marketplace.OZON.value,
    "озон": Marketplace.OZON.value,
    "wildberries": Marketplace.WILDBERRIES.value,
    "wb": Marketplace.WILDBERRIES.value,
    "вайлдберриз": Marketplace.WILDBERRIES.value,
    "вайлдберис": Marketplace.WILDBERRIES.value,
}


@dataclass
class ParsedFile:
    headers: List[str]
    rows: List[List[str]]


@dataclass
class ImportRow:
    line: int
    status: str  # ok | error | duplicate
    messages: List[str] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AppError("IMPORT_BAD_FILE", "Не удалось определить кодировку CSV. Сохраните файл в UTF-8.", 422)


def _parse_csv(raw: bytes) -> ParsedFile:
    text = _decode(raw)
    if not text.strip():
        raise AppError("IMPORT_EMPTY", "Файл пустой.", 422)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    table = [[_cell(c) for c in row] for row in csv.reader(io.StringIO(text), dialect)]
    return _to_parsed(table)


def _parse_xlsx(raw: bytes) -> ParsedFile:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:  # повреждённый или не-XLSX файл
        raise AppError("IMPORT_BAD_FILE", "Не удалось прочитать XLSX: файл повреждён или имеет другой формат.", 422) from exc
    try:
        sheet = workbook.worksheets[0]
        table: List[List[str]] = []
        for row in sheet.iter_rows(values_only=True):
            table.append([_cell(c) for c in row])
            if len(table) > MAX_ROWS + 1:
                break
    finally:
        workbook.close()
    return _to_parsed(table)


def _to_parsed(table: List[List[str]]) -> ParsedFile:
    table = [row for row in table if any(cell for cell in row)]
    if not table:
        raise AppError("IMPORT_EMPTY", "В файле нет данных.", 422)
    headers = [h or f"Столбец {i + 1}" for i, h in enumerate(table[0])]
    if len(headers) > MAX_COLUMNS:
        raise AppError("IMPORT_TOO_WIDE", f"Слишком много столбцов (максимум {MAX_COLUMNS}).", 422)
    rows = table[1:]
    if not rows:
        raise AppError("IMPORT_EMPTY", "В файле есть только заголовок, строк с товарами нет.", 422)
    if len(rows) > MAX_ROWS:
        raise AppError("IMPORT_TOO_MANY_ROWS", f"Слишком много строк (максимум {MAX_ROWS}). Разделите файл.", 422)
    width = len(headers)
    rows = [(row + [""] * width)[:width] for row in rows]
    return ParsedFile(headers=headers, rows=rows)


def parse_file(filename: str, raw: bytes) -> ParsedFile:
    if len(raw) > MAX_FILE_BYTES:
        raise AppError("IMPORT_TOO_LARGE", "Файл больше 5 МБ.", 413)
    if not raw:
        raise AppError("IMPORT_EMPTY", "Файл пустой.", 422)
    name = (filename or "").lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        return _parse_csv(raw)
    if name.endswith(".xlsx"):
        return _parse_xlsx(raw)
    raise AppError("IMPORT_BAD_FORMAT", "Поддерживаются только файлы CSV и XLSX.", 422)


def suggest_mapping(headers: List[str]) -> Dict[str, Optional[int]]:
    """Предлагает индекс столбца для каждого поля по названию столбца."""
    mapping: Dict[str, Optional[int]] = {name: None for name in FIELDS}
    used: Set[int] = set()
    for name in FIELDS:
        for index, header in enumerate(headers):
            if index in used:
                continue
            lowered = header.strip().lower()
            if any(lowered == hint or hint in lowered for hint in _HINTS[name]):
                mapping[name] = index
                used.add(index)
                break
    return mapping


def normalize_marketplace(value: str, default: str) -> str:
    key = (value or "").strip().lower()
    if not key:
        return default
    return _MARKETPLACES.get(key, Marketplace.OTHER.value)


def validate_mapping(mapping: Dict[str, Any], width: int) -> Dict[str, Optional[int]]:
    clean: Dict[str, Optional[int]] = {}
    for name in FIELDS:
        value = mapping.get(name)
        if value in (None, "", -1):
            clean[name] = None
            continue
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < width:
            raise AppError("IMPORT_BAD_MAPPING", f"Неверный номер столбца для поля «{name}».", 422)
        clean[name] = value
    if clean["name"] is None:
        raise AppError("IMPORT_BAD_MAPPING", "Укажите столбец с названием товара.", 422)
    return clean


def build_rows(
    parsed: ParsedFile,
    mapping: Dict[str, Optional[int]],
    existing_skus: Set[str],
    default_marketplace: str = Marketplace.OTHER.value,
) -> List[ImportRow]:
    """Проверяет строки: обязательные поля, длины, дубликаты внутри файла и в базе."""
    result: List[ImportRow] = []
    seen_skus: Set[str] = set()
    seen_names: Set[str] = set()

    def get(row: List[str], name: str) -> str:
        index = mapping.get(name)
        return row[index].strip() if index is not None else ""

    for offset, row in enumerate(parsed.rows):
        line = offset + 2  # строка 1 — заголовок
        name, sku = get(row, "name"), get(row, "sku")
        messages: List[str] = []
        if not name:
            messages.append("Не указано название товара.")
        if len(name) > 255:
            messages.append("Название длиннее 255 символов.")
        if len(sku) > 120:
            messages.append("Артикул длиннее 120 символов.")
        description = get(row, "description")
        if len(description) > 20000:
            messages.append("Описание длиннее 20 000 символов.")
        if messages:
            result.append(ImportRow(line, "error", messages))
            continue

        sku_key = sku.lower()
        name_key = name.lower()
        if sku and (sku_key in existing_skus or sku_key in seen_skus):
            where = "уже есть в рабочем пространстве" if sku_key in existing_skus else "повторяется в файле"
            result.append(ImportRow(line, "duplicate", [f"Артикул «{sku}» {where}."]))
            continue
        if not sku and name_key in seen_names:
            result.append(ImportRow(line, "duplicate", ["Товар без артикула с таким названием уже есть выше в файле."]))
            continue
        if sku:
            seen_skus.add(sku_key)
        else:
            seen_names.add(name_key)

        result.append(
            ImportRow(
                line,
                "ok",
                [],
                {
                    "name": name,
                    "sku": sku,
                    "marketplace": normalize_marketplace(get(row, "marketplace"), default_marketplace),
                    "category": get(row, "category")[:255],
                    "description": description,
                    "attributes": parse_attributes_text(get(row, "attributes")),
                },
            )
        )
    return result


def summarize(rows: List[ImportRow]) -> Dict[str, int]:
    return {
        "total": len(rows),
        "ok": sum(1 for r in rows if r.status == "ok"),
        "error": sum(1 for r in rows if r.status == "error"),
        "duplicate": sum(1 for r in rows if r.status == "duplicate"),
    }
