"""Быстрая проверка API вручную: python scripts/smoke_test.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES = PROJECT_ROOT / "app" / "sample_data"


def show(title: str, payload) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:2500])


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=60.0)
    health = client.get("/health")
    show("health", health.json())

    demo = client.post("/api/v1/auth/demo")
    show("demo login status", demo.status_code)
    if demo.status_code != 200:
        show("demo login error", demo.json())
        return 1
    token = demo.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    create = client.post(
        "/api/v1/products",
        json={
            "name": "Тестовый товар (smoke)",
            "marketplace": "demo",
            "category": "test",
            "description": "До 48 часов работы без подзарядки. Вес 250 граммов. Подходит всем.",
            "attributes": {"battery_life_hours": 30, "weight_g": 250, "model": "SMOKE-1"},
        },
    )
    show("create product", create.json())
    product_id = create.json()["id"]

    listing = client.get("/api/v1/products")
    show("products list count", {"count": len(listing.json()), "names": [p["name"] for p in listing.json()]})

    for name in ("demo_certificate.txt", "demo_reviews.csv"):
        path = SAMPLES / name
        with path.open("rb") as handle:
            response = client.post(
                f"/api/v1/products/{product_id}/sources",
                files={"file": (name, handle, "text/plain")},
            )
        show(f"upload {name} -> {response.status_code}", response.json())

    run = client.post(f"/api/v1/products/{product_id}/analysis-runs")
    show("analysis run", run.json())

    findings = client.get(f"/api/v1/products/{product_id}/findings")
    show("findings", findings.json())

    claims = client.get(f"/api/v1/products/{product_id}/claims")
    show("claims", claims.json())

    if findings.json():
        finding_id = findings.json()[0]["id"]
        patched = client.patch(
            f"/api/v1/findings/{finding_id}",
            json={"status": "in_review", "comment": "Проверяем вручную"},
        )
        show("patch finding", patched.json())
        history = client.get(f"/api/v1/findings/{finding_id}/history")
        show("finding history", history.json())

    runs = client.get(f"/api/v1/products/{product_id}/analysis-runs")
    if runs.json():
        run_id = runs.json()[0]["id"]
        report = client.get(f"/api/v1/products/{product_id}/reports/{run_id}")
        print(f"\n=== report -> {report.status_code}, {len(report.text)} символов ===")
        print(report.text[:600])

    overview = client.get("/api/v1/overview")
    show("overview", overview.json())

    client.delete(f"/api/v1/products/{product_id}")
    print("\nТовар удалён:", client.get("/api/v1/products").json().__len__(), "осталось")
    return 0


if __name__ == "__main__":
    sys.exit(main())
