"""Массовые операции с каталогом: импорт CSV/XLSX и выгрузка результатов в XLSX."""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.finding import Finding
from app.models.product import Product
from app.models.workspace import User
from app.services import catalog_import as ci
from app.services import sources as source_service

router = APIRouter(prefix="/products", tags=["catalog"])

SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1, "info": 0}
SEVERITY_RU = {"high": "Высокая", "medium": "Средняя", "low": "Низкая", "info": "Информация"}
STATUS_RU = {
    "open": "Открыта",
    "in_review": "На проверке",
    "resolved": "Исправлена",
    "not_an_issue": "Не является проблемой",
    "insufficient_data": "Недостаточно данных",
}


async def _read_upload(file: UploadFile) -> bytes:
    raw = await file.read(ci.MAX_FILE_BYTES + 1)
    return raw


def _existing_skus(db: Session, user: User) -> set:
    rows = db.execute(
        select(Product.sku).where(Product.workspace_id == user.workspace_id, Product.sku != "")
    ).scalars()
    return {str(sku).strip().lower() for sku in rows}


def _parse_mapping(raw: str, width: int) -> Dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        raise AppError("IMPORT_BAD_MAPPING", "Сопоставление столбцов передано в неверном формате.", 422)
    if not isinstance(data, dict):
        raise AppError("IMPORT_BAD_MAPPING", "Сопоставление столбцов передано в неверном формате.", 422)
    return ci.validate_mapping(data, width)


def _row_out(row: ci.ImportRow) -> Dict[str, Any]:
    return {
        "line": row.line,
        "status": row.status,
        "messages": row.messages,
        "name": (row.data or {}).get("name", ""),
        "sku": (row.data or {}).get("sku", ""),
    }


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    mapping: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Читает файл, предлагает сопоставление столбцов и проверяет строки. Ничего не сохраняет."""
    parsed = ci.parse_file(file.filename or "", await _read_upload(file))
    suggested = ci.suggest_mapping(parsed.headers)
    chosen = _parse_mapping(mapping, len(parsed.headers)) if mapping else suggested
    result: Dict[str, Any] = {
        "headers": parsed.headers,
        "sample": parsed.rows[: ci.PREVIEW_ROWS],
        "suggested_mapping": suggested,
        "mapping": chosen,
        "rows_total": len(parsed.rows),
    }
    if chosen.get("name") is not None:
        rows = ci.build_rows(parsed, chosen, _existing_skus(db, user))
        result["summary"] = ci.summarize(rows)
        result["problems"] = [_row_out(r) for r in rows if r.status != "ok"][:100]
    else:
        result["summary"] = None
        result["problems"] = []
    return result


@router.post("/import/commit")
async def import_commit(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    skip_invalid: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Создаёт товары из корректных строк. При ошибках без skip_invalid не создаёт ничего."""
    parsed = ci.parse_file(file.filename or "", await _read_upload(file))
    chosen = _parse_mapping(mapping, len(parsed.headers))
    rows = ci.build_rows(parsed, chosen, _existing_skus(db, user))
    summary = ci.summarize(rows)
    if summary["ok"] == 0:
        raise AppError("IMPORT_NOTHING", "Нет ни одной корректной строки для импорта.", 422)
    if summary["ok"] < summary["total"] and not skip_invalid:
        raise AppError(
            "IMPORT_HAS_INVALID",
            "В файле есть некорректные или повторяющиеся строки. Исправьте их или импортируйте только корректные.",
            422,
        )
    created: List[str] = []
    for row in rows:
        if row.status != "ok" or row.data is None:
            continue
        product = Product(workspace_id=user.workspace_id, is_demo=False, **row.data)
        db.add(product)
        db.flush()
        source_service.sync_system_sources(db, product)
        created.append(product.id)
    db.commit()
    return {"created": len(created), "skipped": summary["total"] - len(created), "product_ids": created}


@router.get("/export.xlsx")
def export_xlsx(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Выгрузка результатов аудита: листы «Сводка», «Товары», «Находки»."""
    from openpyxl import Workbook

    products = list(
        db.execute(
            select(Product).where(Product.workspace_id == user.workspace_id).order_by(Product.name)
        ).scalars()
    )
    findings = list(
        db.execute(
            select(Finding).where(Finding.workspace_id == user.workspace_id, Finding.archived.is_(False))
        ).scalars()
    )
    last_runs: Dict[str, Any] = {}
    for run in db.execute(
        select(AnalysisRun).where(AnalysisRun.workspace_id == user.workspace_id)
    ).scalars():
        current = last_runs.get(run.product_id)
        if current is None or run.created_at > current.created_at:
            last_runs[run.product_id] = run

    by_product: Dict[str, List[Finding]] = {}
    for finding in findings:
        by_product.setdefault(finding.product_id, []).append(finding)
    names = {p.id: p for p in products}

    wb = Workbook()
    summary = wb.active
    summary.title = "Сводка"
    checked = sum(1 for p in products if p.id in last_runs)
    attention = sum(1 for p in products if by_product.get(p.id))
    summary.append(["Показатель", "Значение"])
    for label, value in (
        ("Товаров всего", len(products)),
        ("Проверено", checked),
        ("Ожидают проверки", len(products) - checked),
        ("Товаров с находками", attention),
        ("Находок всего", len(findings)),
        ("Высокая серьёзность", sum(1 for f in findings if f.severity == "high")),
    ):
        summary.append([label, value])

    sheet = wb.create_sheet("Товары")
    sheet.append(["Название", "Артикул", "Маркетплейс", "Категория", "Статус проверки", "Находок", "Наиболее серьёзная", "Последняя проверка"])
    for product in products:
        items = by_product.get(product.id, [])
        top = max(items, key=lambda f: SEVERITY_ORDER.get(f.severity, 0), default=None)
        run = last_runs.get(product.id)
        sheet.append(
            [
                product.name,
                product.sku,
                product.marketplace,
                product.category,
                "Проверен" if run else "Ожидает проверки",
                len(items),
                SEVERITY_RU.get(top.severity, top.severity) if top else "",
                run.created_at.strftime("%Y-%m-%d %H:%M") if run else "",
            ]
        )

    sheet = wb.create_sheet("Находки")
    sheet.append(["Товар", "Артикул", "Серьёзность", "Статус", "Находка", "Описание", "Основание (цитаты)", "Ограничения", "Рекомендация"])
    ordered = sorted(findings, key=lambda f: -SEVERITY_ORDER.get(f.severity, 0))
    for finding in ordered:
        product = names.get(finding.product_id)
        quotes = "\n".join(
            f"[{ref.get('source_name', '')}] {' '.join(str(ref.get('excerpt', '')).split())}"
            for ref in (finding.source_refs or [])
        )
        sheet.append(
            [
                product.name if product else "",
                product.sku if product else "",
                SEVERITY_RU.get(finding.severity, finding.severity),
                STATUS_RU.get(finding.status, finding.status),
                finding.title,
                finding.description,
                quotes,
                finding.limitations,
                finding.recommended_action,
            ]
        )

    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        for column in ws.columns:
            width = max((len(str(c.value)) for c in list(column)[:50] if c.value is not None), default=8)
            ws.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 60)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="audit.xlsx"'},
    )
