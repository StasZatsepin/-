"""Импорт каталога CSV/XLSX и выгрузка в XLSX."""

from __future__ import annotations

import io

from openpyxl import Workbook, load_workbook

API = "/api/v1/products"
CSV = (
    "Название;Артикул;Площадка;Категория;Описание;Характеристики\n"
    "Наушники A;A-1;Ozon;Аудио;Работа до 48 часов;Время работы: 30 ч\n"
    "Наушники B;A-2;WB;Аудио;Описание B;\n"
    ";A-3;Ozon;Аудио;без названия;\n"
    "Наушники C;A-1;Ozon;Аудио;дубль артикула;\n"
).encode("utf-8")


def _upload(client, headers, path, content, name="catalog.csv", **data):
    return client.post(path, headers=headers, files={"file": (name, content)}, data=data)


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_preview_suggests_mapping_and_flags_problems(client, auth_headers):
    response = _upload(client, auth_headers, f"{API}/import/preview", CSV)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["headers"][0] == "Название"
    assert body["suggested_mapping"]["name"] == 0 and body["suggested_mapping"]["sku"] == 1
    assert body["summary"] == {"total": 4, "ok": 2, "error": 1, "duplicate": 1}
    assert {p["status"] for p in body["problems"]} == {"error", "duplicate"}


def test_commit_requires_skip_flag_when_rows_are_invalid(client, auth_headers):
    mapping = '{"name":0,"sku":1,"marketplace":2,"category":3,"description":4,"attributes":5}'
    refused = _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping=mapping)
    assert refused.status_code == 422
    assert client.get(API, headers=auth_headers).json() == [] or all(
        p["name"] not in ("Наушники A", "Наушники B") for p in client.get(API, headers=auth_headers).json()
    )
    ok = _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping=mapping, skip_invalid="true")
    assert ok.status_code == 200, ok.text
    assert ok.json()["created"] == 2 and ok.json()["skipped"] == 2
    names = {p["name"]: p for p in client.get(API, headers=auth_headers).json()}
    assert names["Наушники A"]["sku"] == "A-1"
    detail = client.get(f"{API}/{names['Наушники A']['id']}", headers=auth_headers).json()
    assert detail["marketplace"] == "ozon" and detail["attributes"] == {"Время работы": "30 ч"}
    assert client.get(f"{API}/{names['Наушники B']['id']}", headers=auth_headers).json()["marketplace"] == "wildberries"


def test_repeat_import_does_not_duplicate_products(client, auth_headers):
    mapping = '{"name":0,"sku":1}'
    first = _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping=mapping, skip_invalid="true")
    assert first.json()["created"] == 2
    again = _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping=mapping, skip_invalid="true")
    assert again.status_code == 422  # все строки уже есть или некорректны


def test_xlsx_import(client, auth_headers):
    data = _xlsx([["Наименование", "SKU"], ["Чайник", "K-1"], ["Тостер", "K-2"]])
    response = _upload(client, auth_headers, f"{API}/import/preview", data, name="c.xlsx")
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["ok"] == 2


def test_bad_inputs(client, auth_headers):
    assert _upload(client, auth_headers, f"{API}/import/preview", b"", name="e.csv").status_code == 422
    assert _upload(client, auth_headers, f"{API}/import/preview", b"x", name="a.pdf").status_code == 422
    assert _upload(client, auth_headers, f"{API}/import/preview", b"not xlsx", name="a.xlsx").status_code == 422
    header_only = "Название;Артикул\n".encode()
    assert _upload(client, auth_headers, f"{API}/import/preview", header_only).status_code == 422
    assert _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping='{"sku":1}').status_code == 422
    assert _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping='{"name":99}').status_code == 422
    assert _upload(client, auth_headers, f"{API}/import/commit", CSV, mapping="не json").status_code == 422


def test_many_rows_and_row_limit(client, auth_headers):
    rows = "\n".join(f"Товар {i};S-{i}" for i in range(300))
    big = f"Название;Артикул\n{rows}".encode()
    ok = _upload(client, auth_headers, f"{API}/import/commit", big, mapping='{"name":0,"sku":1}')
    assert ok.status_code == 200 and ok.json()["created"] == 300
    too_many = "Название\n" + "\n".join(f"T{i}" for i in range(2001))
    assert _upload(client, auth_headers, f"{API}/import/preview", too_many.encode()).status_code == 422


def test_export_has_three_sheets_and_cyrillic(client, auth_headers, product):
    client.post(f"/api/v1/products/{product['id']}/analysis-runs", headers=auth_headers)
    response = client.get(f"{API}/export.xlsx", headers=auth_headers)
    assert response.status_code == 200
    wb = load_workbook(io.BytesIO(response.content))
    assert wb.sheetnames == ["Сводка", "Товары", "Находки"]
    products_sheet = list(wb["Товары"].iter_rows(values_only=True))
    assert products_sheet[0][0] == "Название"
    assert any(row[0] == "Тестовый товар" for row in products_sheet[1:])
    assert wb["Находки"]["A1"].value == "Товар"


def test_export_of_empty_workspace_still_valid(client, auth_headers):
    wb = load_workbook(io.BytesIO(client.get(f"{API}/export.xlsx", headers=auth_headers).content))
    assert wb["Сводка"]["B2"].value is not None
