#!/bin/sh
# Точка входа backend: дождаться базы и запустить сервер.
set -eu

/usr/local/bin/wait-for-db.sh 60 2

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
