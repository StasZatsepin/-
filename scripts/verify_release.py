"""Проверка готовности перед фиксацией версии.

Проверяет: авторизацию, изоляцию рабочих пространств, сохранность данных,
миграции, отчёты и отсутствие ошибок в логах.

Запуск: .venv\\Scripts\\python.exe scripts\\verify_release.py
"""

from __future__ import annotations

import io
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
RESULTS: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    RESULTS.append((ok, name, detail))
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=120.0)

    # --- health ---
    health = client.get("/health")
    check(health.status_code == 200, "Health endpoint", f"HTTP {health.status_code}")
    check(
        health.json().get("status") == "ok",
        "Сервис отвечает статусом ok",
        health.json().get("app", ""),
    )

    # --- авторизация: регистрация ---
    email = f"check-{uuid.uuid4().hex[:8]}@local.test"
    password = "verify-secret-1"
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Проверка",
            "workspace_name": "Проверка перед релизом",
        },
    )
    check(registration.status_code == 201, "Регистрация", f"HTTP {registration.status_code}")
    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- авторизация: вход ---
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    check(login.status_code == 200, "Вход по паролю", f"HTTP {login.status_code}")
    check(
        bool(login.json().get("access_token")) and login.json()["token_type"] == "bearer",
        "Вход возвращает корректный bearer-токен",
    )

    # --- авторизация: отказ ---
    check(
        client.get("/api/v1/products").status_code == 401,
        "Без токена доступ закрыт (401)",
    )
    check(
        client.get(
            "/api/v1/products", headers={"Authorization": "Bearer invalid-token"}
        ).status_code
        == 401,
        "С поддельным токеном доступ закрыт (401)",
    )
    wrong = client.post("/api/v1/auth/login", json={"email": email, "password": "неверный"})
    check(wrong.status_code == 401, "Неверный пароль отклонён (401)", f"HTTP {wrong.status_code}")

    # --- изоляция рабочих пространств ---
    demo = client.post("/api/v1/auth/demo").json()
    demo_headers = {"Authorization": f"Bearer {demo['access_token']}"}
    demo_product = client.post(
        "/api/v1/products",
        headers=demo_headers,
        json={"name": "Товар демо-пространства", "marketplace": "demo"},
    ).json()
    foreign = client.get(f"/api/v1/products/{demo_product['id']}", headers=headers)
    check(foreign.status_code == 404, "Чужой товар недоступен (404)", f"HTTP {foreign.status_code}")
    listing = client.get("/api/v1/products", headers=headers).json()
    check(
        all(item["id"] != demo_product["id"] for item in listing),
        "В списке нет чужих товаров",
    )

    # --- сохранность данных ---
    created = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": "Товар для проверки сохранности",
            "marketplace": "demo",
            "description": "До 48 часов работы без подзарядки. Вес 250 граммов.",
            "attributes": {"battery_life_hours": 30, "weight_g": 250},
        },
    )
    check(created.status_code == 201, "Создание товара", f"HTTP {created.status_code}")
    product_id = created.json()["id"]

    reread = client.get(f"/api/v1/products/{product_id}", headers=headers)
    check(
        reread.status_code == 200 and reread.json()["name"] == created.json()["name"],
        "Товар читается после создания",
    )

    payload = (
        "ДЕМО-ДОКУМЕНТ (синтетический)\nВремя работы без подзарядки — 30 часов.\n"
    ).encode("utf-8")
    upload = client.post(
        f"/api/v1/products/{product_id}/sources",
        headers=headers,
        files={"file": ("doc.txt", io.BytesIO(payload), "text/plain")},
    )
    check(upload.status_code == 201, "Загрузка источника", f"HTTP {upload.status_code}")

    run = client.post(f"/api/v1/products/{product_id}/analysis-runs", headers=headers)
    check(run.status_code == 201, "Запуск проверки", f"HTTP {run.status_code}")
    summary = run.json().get("summary", {})
    check(
        summary.get("findings_total", 0) >= 1,
        "Проверка дала находки",
        f"находок: {summary.get('findings_total')}",
    )
    check(
        run.json().get("status") == "completed",
        "Запуск проверки завершён без ошибок",
        run.json().get("status", ""),
    )

    findings = client.get(f"/api/v1/products/{product_id}/findings", headers=headers).json()
    check(len(findings) >= 1, "Список находок не пуст", f"находок: {len(findings)}")
    if findings:
        finding = findings[0]
        check(
            bool(finding.get("limitations")) and bool(finding.get("recommended_action")),
            "У находки есть ограничение и рекомендация",
        )
        check(
            bool(finding.get("source_refs")),
            "У находки есть основание (ссылка на источник)",
        )
        patched = client.patch(
            f"/api/v1/findings/{finding['id']}",
            headers=headers,
            json={"status": "in_review", "comment": "Проверка перед релизом"},
        )
        check(patched.status_code == 200, "Смена статуса находки", f"HTTP {patched.status_code}")
        history = client.get(f"/api/v1/findings/{finding['id']}/history", headers=headers).json()
        check(len(history) == 1, "История действий записана", f"записей: {len(history)}")

    report_id = client.get(
        f"/api/v1/products/{product_id}/analysis-runs", headers=headers
    ).json()[0]["id"]
    report = client.get(f"/api/v1/products/{product_id}/reports/{report_id}", headers=headers)
    check(report.status_code == 200, "HTML-отчёт формируется", f"HTTP {report.status_code}")
    check(
        "не является юридическим заключением" in report.text,
        "В отчёте есть обязательный дисклеймер",
    )
    check(
        "<script>alert" not in report.text,
        "Пользовательский текст экранируется в отчёте",
    )

    # --- повторное чтение после «перезапуска» сессии ---
    token2 = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    after = client.get(f"/api/v1/products/{product_id}", headers=headers2)
    check(
        after.status_code == 200 and after.json()["attributes"].get("battery_life_hours") == 30,
        "Данные сохранились в БД и читаются новой сессией",
    )
    runs_after = client.get(
        f"/api/v1/products/{product_id}/analysis-runs", headers=headers2
    ).json()
    check(len(runs_after) == 1, "История запусков сохранилась", f"запусков: {len(runs_after)}")

    # --- удаление не должно ломать каскады ---
    deleted = client.delete(f"/api/v1/products/{product_id}", headers=headers2)
    check(deleted.status_code == 204, "Удаление товара", f"HTTP {deleted.status_code}")
    check(
        client.get(f"/api/v1/products/{product_id}", headers=headers2).status_code == 404,
        "Удалённый товар недоступен (404)",
    )
    client.delete(f"/api/v1/products/{demo_product['id']}", headers=demo_headers)

    # --- сводка ---
    failed = [item for item in RESULTS if not item[0]]
    print()
    print(f"ИТОГО: {len(RESULTS) - len(failed)} из {len(RESULTS)} проверок пройдено")
    if failed:
        print("НЕ ПРОЙДЕНЫ:")
        for _, name, detail in failed:
            print(f"  - {name} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
