# Запуск через Podman (Linux-контейнеры на Windows)

Документ описывает контейнерный запуск проекта «Обещание против реальности»
на Windows через **Podman** и совместимый Compose-провайдер. Docker Desktop не
используется и не требуется.

Нативный запуск через PowerShell по-прежнему поддерживается — см.
[README.md](../README.md), раздел «Запуск».

---

## 1. Что получится

| Сервис | Что внутри | Порт на Windows | Внутренний адрес |
|---|---|---|---|
| `db` | PostgreSQL 16-alpine | `127.0.0.1:55432` | `db:5432` |
| `migrate` | одноразовый прогон Alembic | — | — |
| `backend` | FastAPI + uvicorn | `127.0.0.1:8000` | `backend:8000` |
| `frontend` | nginx + собранный бандл Vite | `127.0.0.1:8080` | `frontend:80` |

* Браузер: **<http://localhost:8080>**
* API напрямую: <http://localhost:8000/health>
* Готовность backend через frontend: <http://localhost:8080/health>

**Контейнерная база изолирована от локального PostgreSQL.** У неё свои
учётные данные, свой именованный том и порт `55432` (на машине заняты `5432`
и `5433`). Локальная база, её данные и файл `.env` не затрагиваются.

---

## 2. Требования

| Компонент | Версия | Проверено |
|---|---|---|
| Podman | 4+ | 6.1.4 (Windows, WSL2-машина) |
| Compose-провайдер | любой совместимый | `podman-compose` 1.6.0 (в venv проекта) |
| Docker Compose | опционально | v5.6.1 — требует именованного канала `\\.\pipe\podman-machine-default` |

Проверка окружения:

```powershell
podman --version
podman machine list
podman compose version
```

### Compose-провайдер

На Windows команда `podman compose` подключает внешний провайдер. В проекте
используется **podman-compose**: он обращается к CLI Podman напрямую и не
требует Docker API в именованном канале, поэтому работает одинаково на любой
машине и после перезагрузки WSL.

```powershell
# Установлен в виртуальное окружение проекта, не глобально
.\.venv\Scripts\python.exe -m pip install podman-compose
```

Скрипт `scripts/podman.ps1` сам подставляет провайдер в `PATH` и
`PODMAN_COMPOSE_PROVIDER`. Для прямых вызовов сделайте то же самое:

```powershell
$env:PATH = "D:\Control\Проект конкурса\.venv\Scripts;$env:PATH"
$env:PODMAN_COMPOSE_PROVIDER = 'podman-compose'
podman compose up -d --build
```

Альтернатива — Docker Compose (`docker-compose.exe`), который был до этого
использован в проекте. Он работает, если Podman создаёт именованный канал
`\\.\pipe\podman-machine-default`; при его отсутствии выдаётся понятная ошибка
`failed to connect to the docker API at npipe:////./pipe/podman-machine-default`.

> `compose.yaml` не содержит полей, специфичных для одного провайдера:
> `Containerfile` лежит в корне контекста сборки каждого сервиса, поэтому
> файл понимают и `podman-compose`, и `docker-compose`.

Если машина Podman ещё не создана:

```powershell
podman machine init --cpus 4 --memory 4096 --disk-size 60
podman machine start
```

> **Рекомендация по памяти.** На машине с 2 ГБ сборка образа Node и запуск
> PostgreSQL могут упереться в нехватку памяти. Для комфортной работы
> увеличьте объём: `podman machine stop` → `podman machine set --memory 4096`
> → `podman machine start`. Увеличение памяти безопасно: данные машины и
> тома сохраняются.

---

## 3. Быстрый старт

```powershell
cd "D:\Control\Проект конкурса"

podman compose up -d --build     # сборка образов и запуск стека
podman compose ps               # состояние контейнеров
podman compose logs -f          # логи
podman compose down             # остановка (тома с данными сохраняются)
```

Если в вашей системе `podman compose` подключает Docker Compose и тот не может
достучаться до Docker API, подключите podman-compose (см. раздел 2):

```powershell
$env:PATH = "D:\Control\Проект конкурса\.venv\Scripts;$env:PATH"
$env:PODMAN_COMPOSE_PROVIDER = 'podman-compose'
podman compose up -d --build
```

Через вспомогательный скрипт (он подставляет провайдер сам):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 up
powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 ps
powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 logs
powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 down
```

После старта откройте <http://localhost:8080> и нажмите «Попробовать демо».

---

## 4. Порядок запуска и готовность

`compose.yaml` задаёт зависимости явно:

```
db (healthcheck: pg_isready)
   └─> migrate (alembic upgrade head, одноразовый)
          └─> backend (healthcheck: /health)
                 └─> frontend (healthcheck: wget /)
```

* `db` поднимается и ждёт готовности PostgreSQL;
* `migrate` применяет миграции и завершается;
* `backend` стартует только после успешного завершения `migrate`;
* `frontend` стартует только после того, как `backend` станет здоровым.

Проверить готовность вручную:

```powershell
podman compose ps
podman exec obeshchanie-backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

Миграции применяются **автоматически** при каждом старте. Повторный запуск
безопасен: Alembic применит только новые ревизии.

---

## 5. Устройство контейнеров

### Backend

```
/srv/app/backend/          код приложения, alembic.ini, alembic/, requirements.txt
/srv/app/sample_data/      синтетические демо-материалы
/srv/app/backend/var/storage/   загруженные пользователями файлы (том obeshchanie-storage)
```

Структура повторяет проект на диске: корневой каталог вычисляется от
расположения файлов, поэтому демо-данные находятся там же, где и при
нативном запуске.

Контейнер работает от непривилегированного пользователя `appuser` (uid 10001).
Проверка готовности выполняется штатной библиотекой Python — в образе нет
`curl`.

Точка входа ждёт готовности базы (`wait-for-db.sh`, до 60 попыток с паузой
2 с) и только затем запускает uvicorn. Это делает запуск независимым от того,
умеет ли compose-провайдер ждать `healthcheck` зависимости.

### Frontend

Vite собирает статику на этапе сборки образа, nginx раздаёт её и проксирует
API:

```
/usr/share/nginx/html/      собранный бандл (tsc -b && vite build)
/etc/nginx/templates/default.conf.template   конфигурация с плейсхолдером резолвера
```

* клиентская маршрутизация поддержана: любой путь отдаёт `index.html`,
  поэтому перезагрузка страницы `/app/products/...` не даёт 404;
* `index.html` не кэшируется, `/assets/` — кэшируется на 30 дней;
* адрес DNS-резолвера подставляет точка входа
  `app/frontend/docker-entrypoint.sh`: в compose-сети Podman адрес
  DNS-сервера не фиксирован (в этой сети — `10.89.0.1`, а не `127.0.0.11`),
  и жёстко прописанный резолвер приводил к зависанию проксирования.

### Отдельная тестовая база

Тесты backend используют базу `obeshchanie_test` внутри того же контейнерного
PostgreSQL — рабочая база приложения при этом не затрагивается.

---

## 6. Переменные окружения

Значения по умолчанию заданы в `compose.yaml` и не требуют настройки.
Переопределить можно переменными окружения PowerShell **до** запуска compose:

```powershell
$env:POSTGRES_PASSWORD = 'другой-пароль'
$env:FRONTEND_HOST_PORT = '8090'
$env:BACKEND_HOST_PORT = '8010'
podman compose up -d --build
```

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `POSTGRES_USER` | `oapv` | пользователь контейнерной БД |
| `POSTGRES_PASSWORD` | `oapv_container_local` | пароль контейнерной БД |
| `POSTGRES_DB` | `obeshchanie` | имя базы приложения |
| `DB_HOST_PORT` | `55432` | порт БД на Windows |
| `BACKEND_HOST_PORT` | `8000` | порт API на Windows |
| `FRONTEND_HOST_PORT` | `8080` | порт интерфейса на Windows |
| `SECRET_KEY` | из `.env`, иначе `dev-secret-change-me` | подпись токенов сессии |
| `LLM_PROVIDER` | `mock` | `mock` / `ollama` / `openai_compatible` |
| `DEMO_MODE` | `true` | вход в демонстрационное пространство |

Файл `.env` в корне проекта используется compose только для подстановки
значений по умолчанию. Переменная `DATABASE_URL` из `.env` **не** попадает в
контейнеры: адрес базы внутри сети задаётся явно как `db:5432`. Локальный
`.env` не изменяется.

> Секреты не выводятся в логи и не коммитятся. Для рабочего окружения
> задайте `SECRET_KEY` явно, а не полагайтесь на значение из `.env`.

---

## 7. Логи и диагностика

```powershell
podman compose logs -f                       # все сервисы
podman compose logs backend                  # только backend
podman compose logs migrate                  # миграции
podman compose logs frontend                 # nginx
podman logs obeshchanie-backend --tail 100  # напрямую через podman

podman exec obeshchanie-backend python -c "from app.core.config import settings; print(settings.database_url)"
podman exec obeshchanie-db psql -U oapv -d obeshchanie -c "\dt"
```

---

## 8. Тесты

Тесты backend в контейнере (с отдельной тестовой базой):

```powershell
podman exec `
  -e 'DATABASE_URL=postgresql+psycopg://oapv:oapv_container_local@db:5432/obeshchanie_test' `
  -e 'SECRET_KEY=container-test-secret' `
  obeshchanie-backend python -m pytest tests -q
```

Тесты frontend — отдельный этап образа:

```powershell
podman build --target test -f app/frontend/Containerfile -t obeshchanie/frontend-test:local app/frontend
```

Или одной командой:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 test
```

Нативный запуск тестов на Windows остаётся доступным и ничего не ломает:

```powershell
cd app\backend; ..\..\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend; npm test
```

---

## 9. Резервное копирование

### Дамп контейнерной базы

```powershell
powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 backup
```

Файл попадает в `backup/container/obeshchanie-container-<метка>.sql`.

Вручную:

```powershell
New-Item -ItemType Directory -Force backup\container | Out-Null
podman exec obeshchanie-db pg_dump -U oapv -d obeshchanie --clean --if-exists > backup\container\obeshchanie.sql
```

### Восстановление

```powershell
Get-Content backup\container\obeshchanie.sql -Raw | podman exec -i obeshchanie-db psql -U oapv -d obeshchanie
```

### Копирование загруженных файлов

```powershell
podman run --rm -v obeshchanie-storage:/data -v "${PWD}\backup\container\files:/out" `
  docker.io/library/alpine:3.20 tar czf /out/storage.tar.gz -C /data .
```

### Полное удаление (необратимо)

Выполняйте только если данные не нужны:

```powershell
podman compose down
podman volume rm obeshchanie-pgdata obeshchanie-storage
```

Команды `podman volume prune`, `podman system reset` в проекте не используются
и не рекомендуются.

---

## 10. Остановка

```powershell
podman compose down        # контейнеры и сеть удаляются, тома с данными остаются
```

После `down` данные сохраняются: именованные тома `obeshchanie-pgdata`
(база) и `obeshchanie-storage` (загруженные файлы) не удаляются.
Это проверено: после `down` и повторного `up` товар, находки, запуски
анализа и загруженные файлы остались на месте.

Остановить машину целиком (контейнеры остановятся, данные сохранены):

```powershell
podman machine stop
```

---

## 11. Оба режима одновременно

Нативный и контейнерный режимы используют разные базы и разные порты,
поэтому конфликта нет:

| | Нативный | Контейнерный |
|---|---|---|
| Интерфейс | <http://localhost:5173> | <http://localhost:8080> |
| API | <http://localhost:8000> | <http://localhost:8000> (тот же порт — запускайте что-то одно) |
| База | PostgreSQL в Windows, `localhost:5432` | PostgreSQL в контейнере, `localhost:55432` |

Порт `8000` общий: чтобы поднять оба режима одновременно, запустите
контейнерный backend на другом порту:

```powershell
$env:BACKEND_HOST_PORT = '8010'
podman compose up -d --build
```

---

## 12. Известные ограничения

* **Образы собираются из локального кода.** Нет реестра образов: `podman compose
  build` использует Dockerfile-файлы из проекта.
* **Секреты** передаются через переменные окружения compose. В `compose.yaml`
  нет значений по умолчанию для `SECRET_KEY`, если он есть в `.env` — берётся
  оттуда; иначе используется непригодное для работы значение
  `dev-secret-change-me`.
* **Compose-провайдер.** `podman compose` на Windows использует внешний
  `docker-compose.exe`; при первом запуске выводится соответствующее
  уведомление — это ожидаемо. Docker Desktop при этом не нужен: контейнеры
  запускает Podman.
* **Ресурсы машины.** 2 ГБ RAM — минимум для сборки Node-образа. При ошибках
  нехватки памяти увеличьте объём (раздел 2).
* **PDF/OCR и экспорт отчёта в PDF** не реализованы в самом продукте —
  контейнеризация этого не меняет.
