"""Общие фикстуры тестов: отдельная тестовая база и клиент API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Тесты работают на отдельной базе, чтобы не трогать рабочие данные.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://oapv_app:oapv_local_dev@localhost:5432/obeshchanie_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("LLM_PROVIDER", "mock")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
import app.models  # noqa: F401,E402

TEST_DATABASE_URL = settings.database_url


def run_alembic(url: str, action: str, revision: str = "head") -> None:
    """Запускает миграции Alembic на указанной базе."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    if action == "upgrade":
        command.upgrade(config, revision)
    else:
        command.downgrade(config, revision)


@pytest.fixture(scope="session")
def engine():
    """Движок тестовой базы: схема создаётся миграциями Alembic."""
    run_alembic(TEST_DATABASE_URL, "upgrade", "head")
    connectable = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, future=True)
    Base.metadata.create_all(connectable)
    yield connectable
    connectable.dispose()


@pytest.fixture()
def db_session(engine):
    """Сессия с очисткой данных между тестами."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False, future=True)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    """HTTP-клиент FastAPI с подменённой зависимостью БД."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Токен демо-пользователя для запросов к API."""
    response = client.post("/api/v1/auth/demo")
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def workspace(client, auth_headers):
    """Демо-рабочее пространство."""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    return response.json()["workspace"]


@pytest.fixture()
def product(client, auth_headers):
    """Тестовый товар."""
    response = client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "Тестовый товар",
            "marketplace": "demo",
            "description": "До 48 часов работы без подзарядки. Вес 250 граммов.",
            "attributes": {"battery_life_hours": 30, "weight_g": 250, "model": "TEST-1"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def db_count(db_session, table: str) -> int:
    return db_session.execute(text(f"select count(*) from {table}")).scalar_one()
