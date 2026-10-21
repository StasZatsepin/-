# Состояние реализации «Обещание против реальности»

Дата последнего обновления: 21.10.2026
Версия приложения: 0.1.0 · версия правил: `rules-2024.1`

---

## 1. Завершённые этапы

### Этап 0 — окружение и каркас ✅
- Проверены и зафиксированы версии Python, Node.js, npm, Git, PostgreSQL.
- Создана структура монорепозитория `app/backend` + `app/frontend` + `scripts` + `docs`.
- FastAPI-приложение с health-эндпоинтом (`/health` и `/api/v1/health`) и Swagger UI.
- React + TypeScript + Vite-каркас с русскоязычным интерфейсом.
- Конфигурация через `.env` / `.env.example`, `.gitignore`, Git-репозиторий.
- **Отклонение от документации:** вместо Docker Compose — PowerShell-скрипты
  (`setup.ps1`, `run-backend.ps1`, `run-frontend.ps1`, `init_db.sql`). Причина — запрет
  Docker в задании. Решения зафиксированы в `docs/DECISIONS.md` (Д1).

### Этап 1 — данные и CRUD ✅
- Модели: Workspace, User, Product, Source, Claim, Evidence, Finding, ReviewAction,
  AnalysisRun с внешними ключами и каскадами.
- Миграции Alembic: `a085d65e64a8` (начальная схема), `7ac1e79ffe5a` (контекст числа).
- Аутентификация: регистрация, вход, демо-вход, подписанные токены, изоляция по
  рабочему пространству (проверена тестами).
- CRUD товара, системные источники «Описание товара» и «Таблица характеристик».
- Тесты доступа и валидации — 15 unit/API-тестов в `tests/test_api_products.py`.

### Этап 2 — источники ✅
- Загрузка TXT, CSV, MD, XLSX, PDF (с текстовым слоем); ручной ввод источников.
- Метаданные: имя, MIME, размер, дата загрузки, SHA-256 содержимого, статус извлечения.
- Ограничения: расширения, MIME, размер (настраивается), количество полей документа.
- Файлы хранятся под случайными именами, путь наружу не отдаётся.
- Сканы без текстового слоя → понятное сообщение «нужен OCR».

### Этап 3 — правила без ИИ ✅
- Нормализация единиц: время, длина, масса, объём, заряд, память, мощность, напряжение,
  проценты, количество, шум, температура.
- Извлечение числовых утверждений с распознаванием границ («до 48», «от 20», «20–48»).
- Сопоставление с характеристиками по смысловым маркерам рядом с числом.
- Шесть типов находок, у каждой — основание, фрагмент-цитата, ограничение,
  рекомендуемое действие и статус.
- Эталонный пример в `app/sample_data` (14–15 находок разных типов).

### Этап 4 — claims/evidence workflow ✅
- Список утверждений с привязкой к источнику и фрагменту, ручное изменение типа,
  подтверждение и отклонение пользователем.
- Доказательства с отношением к утверждению (supports / contradicts / contextualizes /
  unrelated / uncertain).
- Статусы `open`, `in_review`, `resolved`, `not_an_issue`, `insufficient_data`.
- История действий: пользователь, время, предыдущий и новый статус, комментарий.

### Этап 5 — LLM-адаптер ✅
- Интерфейс `ClaimAnalysisProvider`.
- `MockAnalysisProvider` — локальная эвристика, работает без сети (по умолчанию).
- `OllamaProvider` — локальные модели с открытыми весами.
- `OpenAICompatibleProvider` — любой OpenAI-совместимый API; ключ только из `.env`.
- Fallback на `mock` с явным сообщением; структурированный ответ валидируется
  по списку допустимых типов; промпт-инъекции из документов не исполняются.

### Этап 6 — отчёт ✅
- HTML-отчёт на Jinja2 с автоэкранированием: товар, источники, утверждения, находки,
  решения пользователя, ограничения анализа.
- Дисклеймер присутствует в отчёте, на странице отчёта и на главной странице.
- Кнопка «Печать / PDF» — печать из браузера.

### Этап 7 — полировка и защита ✅ (частично)
- Единый формат ошибок, понятные сообщения вместо traceback.
- Адаптивная вёрстка (ноутбук/планшет), состояния загрузки и пустые состояния.
- 77 backend-тестов и 13 frontend-тестов.
- Скриншоты интерфейса получены в браузере (см. раздел 6).
- **Не сделано:** Docker/Podman-сборка, PDF-экспорт, OCR, ручная разметка эталонного
  набора для расчёта precision/recall.

---

## 1.1. Редизайн интерфейса (этап 8)

**Статус:** завершён 21.10.2026, версия `v0.2.0`.

| Что сделано | Файлы |
|---|---|
| Дизайн-токены: цвет, типографика, отступы, радиусы, тени, длительности | `src/styles/tokens.css` |
| Базовый слой: сброс, типографика, фокус, скроллбар, появление секций | `src/styles/base.css` |
| Рабочее приложение: каркас, тёмная навигация, карточки, таблицы, вкладки, результаты | `src/styles/app.css` |
| Экран входа и деморежим | `src/styles/auth.css` |
| Публичная страница: первый экран, демонстрация, шаги, возможности, принципы, финал | `src/styles/landing.css` |
| Локальные шрифты Manrope и Inter (OFL 1.1, 32 файла woff2) | `public/fonts/`, `src/styles/fonts.css`, `scripts/fetch_fonts.py` |
| Набор из 34 штриховых SVG-иконок вместо эмодзи | `src/components/icons.tsx` |
| Знак и текстовый логотип | `src/components/Logo.tsx` |
| Появление секций с тремя механизмами проверки | `src/hooks/useReveal.ts` |
| Публичная страница продукта | `src/pages/LandingPage.tsx` |
| Переработаны все 8 страниц приложения и 4 компонента вкладок | `src/pages/*`, `src/components/*` |
| Отчёт на сервере приведён к новой палитре и типографике | `app/backend/app/reports/templates/report.html.j2` |
| Новые тесты публичной страницы и обновлённые тесты каталога и карточки результата | `src/tests/*` |

**Проверено фактически:**

* 77 backend-тестов — пройдены;
* 20 frontend-тестов — пройдены;
* `tsc --noEmit` — ошибок нет; `vite build` — успешно (108 КБ gzip);
* `scripts/verify_release.py` — 28/28 проверок пройдены;
* горизонтальная прокрутка проверена на 40 комбинациях «страница × ширина»
  (360 / 414 / 768 / 1024 / 1440) — переполнения нет;
* сценарий в браузере: демо-вход → создание товара → загрузка источника → запуск
  проверки → просмотр результата → смена статуса → запись в истории → открытие отчёта;
* мобильная навигация: боковая панель уезжает за экран, кнопка-бургер открывает её,
  подложка закрывает меню;
* видимость фокуса: контур 2 px индиго с отступом на всех интерактивных элементах.

**Найденная и исправленная ошибка:** правило `reports/` в `.gitignore` исключало
шаблон HTML-отчёта из репозитория — на чистом клоне отчёт не формировался.
Исправлено на `/reports/`, шаблон добавлен в индекс (см. `docs/DECISIONS.md`, Д16).

---

## 1.2. Контейнеризация через Podman (этап 9)

**Статус:** завершён 21.10.2026.

| Что сделано | Файлы |
|---|---|
| Compose-стек: db → migrate → backend → frontend с healthcheck и `depends_on` | `compose.yaml` |
| Образ backend: python:3.11-slim, непривилегированный пользователь, healthcheck без curl | `app/backend/Containerfile` |
| Образ frontend: сборка Vite на node:22-alpine → раздача nginx | `app/frontend/Containerfile` |
| Конфигурация nginx: статика, прокси `/api`, поддержка клиентской маршрутизации | `app/frontend/nginx.conf` |
| Динамический DNS-резолвер для nginx | `app/frontend/docker-entrypoint.sh` |
| Исключение локальных артефактов и секретов из контекста сборки | `app/.dockerignore` |
| Обёртка над `podman compose` (up/build/ps/logs/down/backup/test) | `scripts/podman.ps1` |
| Инструкция по запуску, логам, тестам и резервному копированию | `docs/PODMAN_SETUP.md` |
| Переменные контейнерной БД в примере окружения | `.env.example` |

**Проверено фактически:**

* `podman compose build` — оба образа собраны;
* `podman compose up -d` — порядок соблюдён: `db` здоров → `migrate` применил
  обе ревизии → `backend` здоров → `frontend` поднялся;
* из Windows: `/` → 200, `/health` → 200, `/api/v1/health` → 200,
  `/app/products` (глубокая ссылка SPA) → 200;
* полный сценарий через nginx: демо-вход → создание товара → загрузка
  источника → проверка → 14 находок всех типов → смена статуса → история →
  HTML-отчёт → сводка → удаление;
* 77 backend-тестов **внутри контейнера** (отдельная база `obeshchanie_test`);
* 20 frontend-тестов **внутри контейнера** (этап `test` образа);
* изоляция БД: контейнерный backend использует `db:5432/obeshchanie`,
  локальная БД на 5432 сохранила свои данные (1 товар, 3 пространства);
* персистентность: `podman compose down` + `up` — товар, 14 находок, 6
  источников, 2 запуска и 31 загруженный файл остались на месте;
* нативный режим не сломан: `run-backend.ps1` и `run-frontend.ps1` работают,
  backend использует локальную БД `localhost:5432/obeshchanie`;
* в браузере: публичная страница и обзор отрисовываются с контейнерного
  frontend, шрифты подключены, переполнения по ширине нет.

**Найденная и исправленная ошибка:** `tests/test_migrations.py` содержал
захардкоженный URL локальной БД — тесты миграций падали в контейнере.
Теперь URL берётся из конфигурации окружения (см. `docs/DECISIONS.md`, Д17).

---

## 2. Установленные инструменты и версии

| Инструмент | Версия | Как установлен |
|---|---|---|
| Python | 3.11.9 (Microsoft Store) | уже был в системе; venv создан в `.venv` |
| Python (альтернатива) | 3.14.6 (`C:\Python314`) | уже был в системе |
| Node.js | 24.17.0 | уже был в системе |
| npm | 11.13.0 | уже был в системе |
| Git | 2.50.0.windows.2 | уже был в системе |
| PostgreSQL | 18.6 (служба `postgresql-x64-18`, работает) | уже был в системе; создана роль и 2 базы |
| pypdf | 6.21.1 | `pip install` |
| openpyxl | 3.1.5 | `pip install` |

Зависимости backend (зафиксированы в `app/backend/requirements.txt`): fastapi 0.156.4,
uvicorn 0.54.0, sqlalchemy 2.1.5, alembic 1.20.0, psycopg 3.3.6, pydantic 2.14.1,
pydantic-settings 2.16.1, python-multipart 0.0.32, jinja2 3.1.6, pytest 9.1.1, httpx 0.28.1.

Зависимости frontend: react 19.3.1, react-dom 19.3.1, react-router-dom 7.18.4,
vite 7.3.7, typescript 5.9.3, vitest 3.2.7, @testing-library/react 16.3.0, jsdom 27.

**Ничего не устанавливалось в систему глобально.** Docker и Ollama не устанавливались.

---

## 3. Команды, которые выполнялись

```powershell
# Подготовка БД
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -v ON_ERROR_STOP=1 -f scripts\init_db.sql

# Python-окружение
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r app\backend\requirements.txt

# Миграции
cd app\backend; ..\..\.venv\Scripts\python.exe -m alembic upgrade head

# Запуск
powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1     # http://127.0.0.1:8000
powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1    # http://127.0.0.1:5173

# Тесты
cd app\backend; ..\..\.venv\Scripts\python.exe -m pytest -q        # 77 passed
cd app\frontend; npm test                                          # 13 passed
cd app\frontend; npm run build                                     # сборка без ошибок
cd app\frontend; npx tsc --noEmit                                  # ошибок типов нет

# Смоук-тест по работающему API
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

---

## 4. Результаты тестов

| Набор | Команда | Результат |
|---|---|---|
| Backend (pytest) | `python -m pytest tests\ -q` | **77 passed** за ~39 с |
| Frontend (Vitest) | `npm test` | **13 passed** за ~8 с |
| Типы TypeScript | `npx tsc --noEmit` | ошибок нет |
| Сборка frontend | `npm run build` | успешно, 328 КБ JS (99 КБ gzip) |
| Смоук-тест API | `scripts/smoke_test.py` | успешно (health → demo-вход → CRUD → загрузка → анализ → находки → статус → история → отчёт) |

### Покрытые обязательные тест-кейсы из `08_TEST_PLAN.md`

| # | Кейс | Где проверяется |
|---|---|---|
| 1 | Одинаковые число и единица — нет конфликта | `test_api_analysis.py::test_same_value_and_unit_has_no_direct_conflict` |
| 2 | Расхождение — находка с обоими источниками | `test_conflicting_values_produce_finding_with_both_sources` |
| 3 | Разные единицы — корректная конвертация | `test_unit_conversion_is_applied`, `test_incompatible_units_are_not_compared` |
| 4 | Разные условия испытаний → `needs_human_review` | `test_different_measurement_conditions_require_human_review` |
| 5 | Нет документа → «нет подтверждения», а не «ложь» | `test_missing_document_gives_insufficient_evidence_not_accusation` |
| 6 | Один негативный отзыв — сигнал, не доказательство | `test_single_negative_review_is_a_signal_only` |
| 7 | Отзывы с разными мнениями | `test_mixed_reviews_are_reported_as_mixed` |
| 8 | Документ для другой модели | `test_document_for_another_model_is_flagged` |
| 9 | PDF без текстового слоя — понятное сообщение | `test_api_sources.py::test_pdf_without_text_layer_reports_needs_ocr` |
| 10 | Слишком большой / неподдерживаемый файл | `test_oversized_file_is_rejected`, `test_unsupported_extension_is_rejected` |
| 11 | Доступ к чужому workspace запрещён | `test_security.py::TestWorkspaceIsolation` (4 теста) |
| 12 | Инструкция в документе — недоверенные данные | `test_prompt_injection_in_document_is_treated_as_data` |
| 13 | HTML/JS не исполняется в отчёте | `test_html_in_product_text_is_escaped_in_report` |
| 14 | В отчёте есть дисклеймер и ссылки на источники | `test_report_contains_disclaimer_and_sources` |
| 15 | ИИ-провайдер недоступен — правила работают | `test_deterministic_checks_work_without_external_provider` |

---

## 5. Изменённые и созданные файлы

Создано 126 файлов (репозиторий создан заново, Git-история — один коммит).
Основные группы:

* **Документация:** `README.md`, `docs/DECISIONS.md`, `IMPLEMENTATION_STATUS.md`,
  копии `01`–`11` из стартового комплекта.
* **Backend (Python):** 45 файлов в `app/backend/app` — `api/` (7 маршрутов + deps),
  `core/` (конфигурация, безопасность, токены, ошибки, логирование), `db/`,
  `models/` (10 сущностей + перечисления), `providers/` (интерфейс + 3 реализации),
  `rules/` (единицы, числа, паттерны, атрибуты, движок находок), `services/`
  (ingestion, claims, analysis, sources, demo, reports), `schemas/`,
  шаблон отчёта `app/reports/templates/report.html.j2`.
* **Миграции:** `alembic.ini`, `alembic/env.py`, `script.py.mako`, 2 ревизии.
* **Тесты backend:** `tests/conftest.py` + 6 тестовых модулей.
* **Frontend (TypeScript):** 30 файлов — `api/`, `components/`, `pages/`, `context/`,
  `styles.css`, `vite.config.ts`, `tsconfig.json`, `index.html`, `package.json`.
* **Тесты frontend:** `src/tests/setup.ts` + 3 тестовых файла.
* **Демо-данные:** `app/sample_data/` — описание, сертификат, паспорт другой модели, отзывы.
* **Скрипты:** `scripts/setup.ps1`, `run-backend.ps1`, `run-frontend.ps1`,
  `restart-backend.ps1`, `init_db.sql`, `smoke_test.py`.
* **Конфигурация:** `.env`, `.env.example`, `.gitignore`, `app/backend/requirements.txt`.

Изменённые существующие файлы: `README.md` (переписан как основной), остальные
документы `01`–`11` перенесены без изменений.

---

## 6. Ручная проверка в браузере

Выполнено на реальном стеке (Vite + FastAPI + PostgreSQL):

1. Открыт <http://127.0.0.1:5173/> → страница входа с кнопкой демо-режима.
2. «Войти в демонстрационном режиме» → главная страница со сводкой
   (товары, находки по типам, серьёзности и статусам, последние проверки).
3. Список товаров → создан товар через форму (название, категория, описание,
   характеристика `battery_life_hours = 25`).
4. Кнопка «Проверить карточку» → 5 находок, среди них прямое расхождение
   «до 40 часов» против характеристики «25 часов» с двумя основаниями.
5. Вкладка «Находки» → фильтры по статусу/типу/серьёзности, карточки с цитатами,
   ограничением, рекомендацией и управлением статусом.
6. Вкладка «Запуски» → история проверок и переход к отчёту.
7. Отчёт → HTML с дисклеймером, источниками, утверждениями, находками и пометкой
   «демонстрационные синтетические данные».
8. Перезагрузка страницы → товар и находки сохранились (данные в PostgreSQL).

---

## 7. Известные ограничения и проблемы

| Проблема | Статус |
|---|---|
| `PDF-экспорт` отчёта не реализован | вне MVP (FR-09 допускает HTML) |
| `OCR` для сканов и изображений не реализован | вне MVP, есть понятное сообщение |
| Метрики precision/recall не рассчитаны | ручная разметка эталонного набора не проведена |
| Числовые правила покрывают ограниченный набор величин | осознанное ограничение MVP |
| Тесты требуют запущенного PostgreSQL | тестовая БД `obeshchanie_test` создаётся скриптом |
| `.env` содержит локальный пароль БД | для рабочей среды нужно заменить `SECRET_KEY` и пароль |
| Модель `MiniMax M3.1 Flash` из OpenCode **не** подключена к приложению | в приложении используется интерфейс провайдера; по умолчанию — локальная эвристика |

---

## 8. Следующий конкретный шаг

1. **Ручная разметка эталонного набора** (20–30 примеров) и расчёт precision/recall
   по формам из `08_TEST_PLAN.md` — это единственный способ честно говорить о
   качестве правил.
2. **Подключение локальной модели через Ollama** (`LLM_PROVIDER=ollama`) и проверка
   реального улучшения классификации утверждений относительно `mock`.
3. **PDF-экспорт отчёта** (P2) — печать из браузера уже работает, нужен файловый экспорт.
4. **Скрипты установки в один шаг** (`scripts/setup.ps1` уже есть — стоит проверить
   его на чистой машине и добавить проверку версий).
5. **Пакет для конкурса:** скриншоты, демо-сценарий, описание методики оценки качества.

---

## 9. Как запустить прямо сейчас

```powershell
cd "D:\Control\Проект конкурса"

# 1) БД (один раз)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -v ON_ERROR_STOP=1 -f scripts\init_db.sql

# 2) Зависимости (один раз)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 3) Миграции
cd app\backend; ..\..\.venv\Scripts\python.exe -m alembic upgrade head; cd ..\..

# 4) Backend (окно 1)
powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1

# 5) Frontend (окно 2)
powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1
```

Открыть <http://127.0.0.1:5173/> → «Войти в демонстрационном режиме».
