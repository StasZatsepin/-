"""Публичная быстрая проверка: без авторизации, без сохранения данных, с лимитом."""

from __future__ import annotations

import pytest

from app.api.routes import public
from app.services.quick_check import parse_attributes_text
from tests.conftest import db_count

PAYLOAD = {
    "name": "Беспроводные наушники",
    "description": (
        "Лёгкие и удобные наушники. Время работы без подзарядки — до 48 часов. "
        "Идеально подходят для поездок. Полностью безопасны для детей."
    ),
    "attributes_text": "Время работы: 30 часов\nМасса: 250 г",
}


@pytest.fixture(autouse=True)
def _reset_limits():
    public._per_minute.reset()
    public._per_hour.reset()
    yield
    public._per_minute.reset()
    public._per_hour.reset()


def test_parse_attributes_text_accepts_common_separators():
    parsed = parse_attributes_text("Масса: 250 г\nВремя работы — 30 ч\nЦвет=чёрный\n\nпусто:")
    assert parsed == {"Масса": "250 г", "Время работы": "30 ч", "Цвет": "чёрный"}


def test_quick_check_works_without_login_and_finds_the_conflict(client):
    response = client.post("/api/v1/public/quick-check", json=PAYLOAD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(body["findings"]) >= 1
    rules = {item["rule_id"] for item in body["findings"]}
    assert "numeric.attribute_comparison" in rules
    conflict = next(i for i in body["findings"] if i["rule_id"] == "numeric.attribute_comparison")
    assert conflict["suggestion"] and "30" in conflict["suggestion"]["text"]
    assert "не сохраняются" in body["note"]


def test_quick_check_stores_nothing(client, db_session):
    before = {t: db_count(db_session, t) for t in ("workspaces", "products", "sources", "findings")}
    assert client.post("/api/v1/public/quick-check", json=PAYLOAD).status_code == 200
    after = {t: db_count(db_session, t) for t in before}
    assert after == before


def test_quick_check_validates_input(client):
    assert client.post("/api/v1/public/quick-check", json={"description": "коротко"}).status_code == 422
    huge = {"description": "а" * 9000}
    assert client.post("/api/v1/public/quick-check", json=huge).status_code == 422


def test_quick_check_is_rate_limited(client):
    statuses = [client.post("/api/v1/public/quick-check", json=PAYLOAD).status_code for _ in range(8)]
    assert statuses[:6] == [200] * 6
    assert 429 in statuses[6:]
