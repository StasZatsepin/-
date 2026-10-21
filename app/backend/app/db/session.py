"""Подключение к базе данных и фабрика сессий SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Dict

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_connect_args: Dict[str, Any] = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # pragma: no cover
    """Включает внешние ключи для SQLite-режима."""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Iterator[Session]:
    """FastAPI-зависимость: сессия на запрос с корректным закрытием."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
