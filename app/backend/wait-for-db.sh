#!/bin/sh
# Ожидание готовности PostgreSQL.
#
# Нужно, потому что не все compose-провайдеры умеют ждать healthcheck
# зависимости. Скрипт используется и сервисом миграций, и backend'ом:
# оба стартуют только когда база отвечает.
#
# Использование: wait-for-db.sh [попыток] [пауза_сек]

set -eu

ATTEMPTS="${1:-60}"
PAUSE="${2:-2}"
URL="${DATABASE_URL:-}"

if [ -z "$URL" ]; then
    echo "[wait-for-db] DATABASE_URL не задан, пропускаю ожидание" >&2
    exit 0
fi

attempt=1
while [ "$attempt" -le "$ATTEMPTS" ]; do
    if python - <<'PY' >/dev/null 2>&1
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
with engine.connect() as connection:
    connection.execute(text("select 1"))
PY
    then
        echo "[wait-for-db] база готова (попытка ${attempt})" >&2
        exit 0
    fi
    echo "[wait-for-db] база недоступна, попытка ${attempt}/${ATTEMPTS}" >&2
    attempt=$((attempt + 1))
    sleep "$PAUSE"
done

echo "[wait-for-db] база не ответила за отведённое время" >&2
exit 1
