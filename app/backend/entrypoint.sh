#!/bin/sh
# Точка входа backend: дождаться базы, применить миграции и запустить сервер.
# На Render порт передаётся через переменную окружения PORT (по умолчанию 8000).
set -eu

PORT="${PORT:-8000}"

/usr/local/bin/wait-for-db.sh 60 2

# Применяем миграции перед стартом (идемпотентно)
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers
