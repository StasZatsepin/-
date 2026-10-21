"""Тесты миграций Alembic: чистая база, повторный прогон, сохранность данных."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from tests.conftest import TEST_DATABASE_URL, run_alembic

TABLES = (
    "workspaces",
    "users",
    "products",
    "sources",
    "claims",
    "evidence",
    "findings",
    "review_actions",
    "analysis_runs",
)


def test_migrations_create_all_tables():
    """Чистая база: после `upgrade head` все таблицы созданы."""
    run_alembic(TEST_DATABASE_URL, "downgrade", "base")
    run_alembic(TEST_DATABASE_URL, "upgrade", "head")

    engine = create_engine(TEST_DATABASE_URL, future=True)
    try:
        with engine.connect() as connection:
            for table in TABLES:
                count = connection.execute(
                    text("select count(*) from information_schema.tables where table_name = :name"),
                    {"name": table},
                ).scalar_one()
                assert count == 1, f"Отсутствует таблица {table}"
    finally:
        engine.dispose()


def test_repeated_upgrade_does_not_destroy_data():
    """Повторный прогон миграций не удаляет существующие данные."""
    engine = create_engine(TEST_DATABASE_URL, future=True)
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "insert into workspaces (id, name, slug, is_demo, created_at, updated_at) "
                    "values (:id, 'Рабочее пространство', 'mig-test-ws', false, now(), now()) "
                    "on conflict (id) do nothing"
                ),
                {"id": "00000000-0000-4000-8000-000000000001"},
            )
            connection.commit()
    finally:
        engine.dispose()

    run_alembic(TEST_DATABASE_URL, "upgrade", "head")

    engine = create_engine(TEST_DATABASE_URL, future=True)
    try:
        with engine.connect() as connection:
            count = connection.execute(
                text("select count(*) from workspaces where slug = 'mig-test-ws'")
            ).scalar_one()
            assert count == 1, "Данные не должны пропадать при обновлении схемы"
    finally:
        engine.dispose()


def test_alembic_version_is_tracked():
    engine = create_engine(TEST_DATABASE_URL, future=True)
    try:
        with engine.connect() as connection:
            version = connection.execute(
                text("select version_num from alembic_version")
            ).scalar_one()
            assert version
    finally:
        engine.dispose()
