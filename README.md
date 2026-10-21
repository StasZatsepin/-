# «Обещание против реальности»

Веб-приложение для продавцов маркетплейсов: оно сопоставляет заявления в карточке
товара, структурированные характеристики, загруженные документы и отзывы покупателей,
находит **потенциальные** противоречия, показывает основание каждого вывода и
оставляет финальное решение за человеком.

Работает локально на Windows, без Docker и без платных внешних API.

---

## 1. Что уже реализовано

| Возможность | Состояние |
|---|---|
| Публичная страница продукта с живой демонстрацией проверки | ✅ |
| Регистрация, вход, демо-режим, изоляция по рабочему пространству | ✅ |
| CRUD товара: название, категория, маркетплейс, SKU, описание, характеристики | ✅ |
| Загрузка источников: TXT, CSV, MD, XLSX, PDF с текстовым слоем | ✅ |
| Ручной ввод источника (заметка, отзывы, текст документа) | ✅ |
| Извлечение утверждений с привязкой к фрагменту источника | ✅ |
| Детерминированная проверка чисел с нормализацией единиц | ✅ |
| Учёт области применения документов, дат и сроков действия | ✅ |
| Импорт и классификация отзывов | ✅ |
| Находки 6 типов с основанием, ограничением и рекомендацией | ✅ |
| Статусы рассмотрения и история действий | ✅ |
| HTML-отчёт с дисклеймером и ссылками на источники | ✅ |
| Демонстрационный набор синтетических данных | ✅ |
| Провайдер ИИ: `mock` (по умолчанию), `ollama`, `openai_compatible` | ✅ |
| Тесты backend (77) и frontend (20) | ✅ |
| OCR, PDF-экспорт отчёта, импорт по URL | ❌ не входит в MVP |

Подробное состояние разработки — в [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

---

## 2. Требования

| Компонент | Версия | Проверено на |
|---|---|---|
| Python | 3.11+ | 3.11.9 (venv), также работает на 3.14 |
| Node.js + npm | 18+ / 9+ | Node 24.17, npm 11.13 |
| PostgreSQL | 14+ | 18.6 (Windows) |
| Git | любой | 2.50 |

Docker не требуется и не используется.

---

## 3. Установка (Windows PowerShell)

### 3.1. База данных

Если PostgreSQL ещё не установлен — установите его с официального сайта
<https://www.postgresql.org/download/windows/> и запустите службу. Затем:

```powershell
cd "D:\Control\Проект конкурса"

# Создаёт роль oapv_app и базы obeshchanie + obeshchanie_test (идемпотентно)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -v ON_ERROR_STOP=1 -f scripts\init_db.sql
```

> Скрипт не удаляет и не пересоздаёт существующие базы: только создаёт их при первом запуске.
> Если `psql` не в `PATH`, укажите полный путь к нему, как выше.

### 3.2. Python-окружение и зависимости

```powershell
cd "D:\Control\Проект конкурса"

# Вариант A: автоматическая установка (venv + pip + npm install)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# Вариант B: вручную
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r app\backend\requirements.txt
cd app\frontend; npm install; cd ..\..
```

### 3.3. Конфигурация

```powershell
Copy-Item .env.example .env   # значения по умолчанию уже подходят для локального запуска
```

В `.env` обязательно замените `SECRET_KEY` для рабочей среды:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3.4. Миграции

```powershell
cd app\backend
..\..\.venv\Scripts\python.exe -m alembic upgrade head
cd ..\..
```

---

## 4. Запуск

Два отдельных окна PowerShell.

**Окно 1 — backend:**

```powershell
cd "D:\Control\Проект конкурса"
powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1
```

- API: <http://127.0.0.1:8000>
- Swagger: <http://127.0.0.1:8000/api/docs>
- Проверка готовности: <http://127.0.0.1:8000/health>

**Окно 2 — frontend:**

```powershell
cd "D:\Control\Проект конкурса"
powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1
```

- Интерфейс: <http://127.0.0.1:5173>

Vite проксирует `/api` на backend, поэтому CORS-проблем нет.

### Первый вход

На странице входа нажмите **«Войти в демонстрационном режиме»** — откроется рабочее
пространство с синтетическим товаром. Демо-данные можно добавить в любой момент
из разделов «Обзор» или «Настройки».

Либо зарегистрируйте собственное рабочее пространство на вкладке «Регистрация».

### Запуск через Podman (контейнеры)

Полная инструкция — в [docs/PODMAN_SETUP.md](docs/PODMAN_SETUP.md).

```powershell
cd "D:\Control\Проект конкурса"
podman compose up -d --build     # db + migrate + backend + frontend
podman compose ps
podman compose logs -f
podman compose down
```

Интерфейс контейнерного стенда — <http://localhost:8080>, API — <http://localhost:8000>,
PostgreSQL — <http://localhost:55432> (отдельная база, локальная не затрагивается).

---

## 5. Проверка работоспособности

```powershell
# Тесты backend (77 шт.) — используют отдельную базу obeshchanie_test
cd app\backend
..\..\.venv\Scripts\python.exe -m pytest -q

# Тесты frontend (20 шт.)
cd ..\frontend
npm test

# Сборка production-бандла и проверка типов
npm run build
```

Дополнительно есть сквозной смоук-тест по работающему API:

```powershell
cd "D:\Control\Проект конкурса"
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

И проверка готовности перед релизом (28 проверок: авторизация, изоляция, сохранность
данных, находки, отчёт):

```powershell
.\.venv\Scripts\python.exe scripts\verify_release.py
```

### Маршруты интерфейса

| Адрес | Что открывается |
|---|---|
| `/` | публичная страница продукта |
| `/login` | вход, регистрация и демо-режим |
| `/app` | обзор рабочего пространства |
| `/app/products` | каталог товаров |
| `/app/products/:id` | карточка товара: источники, утверждения, результаты, доказательства, запуски |
| `/app/products/:id/report/:runId` | отчёт по проверке |
| `/app/checks` | история запусков анализа |
| `/app/history` | история решений пользователя |
| `/app/settings` | настройки, состояние провайдера, демо-данные |

---

## 6. Структура проекта

```text
app/
  backend/
    app/
      api/routes/     # REST-маршруты (products, sources, analysis, findings, reports)
      core/           # конфигурация, безопасность, токены, ошибки, логирование
      db/             # подключение и базовые классы SQLAlchemy
      models/         # Workspace, User, Product, Source, Claim, Evidence, Finding, ...
      providers/      # интерфейс анализа + mock / Ollama / OpenAI-совместимый
      rules/          # детерминированные проверки: единицы, числа, паттерны, движок
      services/       # ingestion, claims, analysis, sources, demo, reports
      reports/        # шаблон HTML-отчёта
    alembic/          # миграции
    tests/            # pytest
  frontend/
    public/fonts/     # Manrope и Inter локально (OFL 1.1)
    src/
      api/            # клиент REST и типы
      components/     # карточка результата, вкладки источников/утверждений, иконки, логотип
      hooks/          # useReveal — появление секций
      pages/          # Landing, Login, Обзор, Товары, Товар, Проверки, История, Настройки, Отчёт
      styles/         # tokens, base, app, auth, landing, fonts
      tests/          # Vitest + Testing Library
  sample_data/        # синтетические демо-материалы
docs/                 # решения, статус реализации
scripts/              # PowerShell-скрипты установки и запуска
```

---

## 7. Как работает проверка

```text
описание товара + характеристики + файлы
        ↓
   извлечение текста (TXT/CSV/MD/XLSX/PDF) → источник с хешем и датой
        ↓
   извлечение утверждений (детерминированно, с фрагментом-цитатой)
        ↓
   нормализация чисел и единиц измерения
        ↓
   детерминированные правила → находки с основанием и ограничением
        ↓
   (опционально) ИИ-провайдер уточняет типы утверждений
        ↓
   решение человека: статус + комментарий → история действий
        ↓
   HTML-отчёт с дисклеймером
```

Типы находок: `direct_conflict`, `missing_evidence`, `review_signal`,
`ambiguous_claim`, `document_scope_mismatch`, `needs_human_review`.

### Принципы, заложенные в правила

* Отсутствие документа — это `missing_evidence`, а не доказательство обмана.
* Единичный отзыв — пользовательский сигнал, а не доказательство.
* «Подходит всем» и «полностью безопасен» — `ambiguous_claim`: объективно не проверяется.
* Если условия измерения неизвестны, вывод понижается до `needs_human_review`.
* Документ для другой модели — `document_scope_mismatch`, а не «противоречие».
* Система никогда не называет продавца мошенником и не выдумывает цитаты и источники.

---

## 8. ИИ-провайдеры

По умолчанию `LLM_PROVIDER=mock`: локальная эвристическая классификация без сети.
Приложение полностью работоспособно без ключей API.

```env
# Локальная модель с открытыми весами через Ollama
LLM_PROVIDER=ollama
LLM_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=qwen2.5:3b

# Любой OpenAI-совместимый API (ключ только в .env, в браузер не попадает)
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=some-model
LLM_API_KEY=...
```

Если внешний провайдер недоступен или не настроен, система явно сообщает об этом и
продолжает работу на детерминированных правилах (fallback на `mock`).

Загруженный текст считается недоверенными данными: он не может изменить системную
инструкцию, у модели нет доступа к shell, базе и внешним URL.

---

## 9. Переменные окружения

Полный список — в [.env.example](.env.example). Основные:

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://oapv_app:...@localhost:5432/obeshchanie` | подключение к БД |
| `SECRET_KEY` | — | подпись токенов сессии, **заменить** |
| `STORAGE_DIR` | `app/backend/var/storage` | папка загруженных файлов |
| `MAX_UPLOAD_BYTES` | `10485760` | лимит размера файла |
| `ALLOWED_UPLOAD_EXTENSIONS` | `.txt,.csv,.md,.pdf,.xlsx` | разрешённые форматы |
| `DEMO_MODE` | `true` | вход в демонстрационное пространство |
| `LLM_PROVIDER` | `mock` | `mock` / `ollama` / `openai_compatible` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | источники frontend |

---

## 10. Документы проекта

| Файл | Содержание |
|---|---|
| [01_PRODUCT_BRIEF.md](01_PRODUCT_BRIEF.md) | цель и границы продукта |
| [02_PRD.md](02_PRD.md) | требования к MVP и критерии приёмки |
| [03_ARCHITECTURE.md](03_ARCHITECTURE.md) | техническая архитектура |
| [04_CLAIM_EVIDENCE_MODEL.md](04_CLAIM_EVIDENCE_MODEL.md) | модель утверждений и доказательств |
| [05_API_CONTRACT.md](05_API_CONTRACT.md) | API-контракт |
| [06_UX_FLOWS.md](06_UX_FLOWS.md) | пользовательские сценарии |
| [07_SECURITY_PRIVACY.md](07_SECURITY_PRIVACY.md) | безопасность и приватность |
| [08_TEST_PLAN.md](08_TEST_PLAN.md) | тест-план |
| [09_IMPLEMENTATION_PLAN.md](09_IMPLEMENTATION_PLAN.md) | этапы разработки |
| [10_AI_DEVELOPER_RULES.md](10_AI_DEVELOPER_RULES.md) | правила работы для ИИ-разработчика |
| [11_MASTER_PROMPT.md](11_MASTER_PROMPT.md) | стартовый запрос |
| [docs/DECISIONS.md](docs/DECISIONS.md) | принятые архитектурные решения и отклонения |
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | состояние реализации |

---

## 11. Стабильная версия и резервная копия

| Что | Где |
|---|---|
| Git-тег стабильной версии | `v0.2.0` (редизайн интерфейса), `v0.1.0` (MVP до редизайна) |
| Резервная копия | `backup/2026-10-21-redesign/` — дамп БД, git bundle, архив исходников, контрольные суммы |
| Предыдущий снимок | `backup/2026-10-21/` (версия `v0.1.0`) |
| Инструкция по восстановлению | `backup/2026-10-21-redesign/BACKUP_INFO.md` |
| Скрипт проверки готовности | `scripts/verify_release.py` (28 проверок) |

Откат к стабильной версии:

```powershell
cd "D:\Control\Проект конкурса"
git log --oneline v0.2.0..HEAD     # что изменилось после
git reset --hard v0.2.0            # откат кода
```

Откат кода не откатывает данные: при необходимости база восстанавливается из
`backup/2026-10-21-redesign/db_obeshchanie.dump` (см. `BACKUP_INFO.md`).

Проверка перед следующими изменениями:

```powershell
.\.venv\Scripts\python.exe scripts\verify_release.py
```

---

## 12. Ограничения MVP

* Проверка выполняется только по материалам, которые вы сами загрузили: документы не
  сверяются с государственными реестрами, сертификаты не проверяются на действительность.
* Числовые правила работают для ограниченного набора величин (время, длина, масса,
  объём, заряд, память, мощность, напряжение, проценты, количество, шум, температура).
* Сканированные PDF и изображения не распознаются: нужен отдельный этап OCR.
* Экспорт отчёта — HTML (печать в PDF из браузера); выгрузка в PDF-файл не реализована.
* Скрейпинг маркетплейсов не выполняется и не планируется: используются только
  загруженные файлы и ручной ввод.
* Метрики качества (precision/recall) не заявляются: ручная разметка эталонного набора
  ещё не проведена.
