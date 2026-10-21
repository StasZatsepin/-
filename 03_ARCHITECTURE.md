# Архитектура MVP

## Стек

-   Frontend: React + TypeScript + Vite.
-   UI: простой адаптивный интерфейс, библиотеку компонентов выбирать
    после создания каркаса.
-   Backend: Python + FastAPI + Pydantic.
-   ORM: SQLAlchemy 2.x.
-   Database: PostgreSQL.
-   Migrations: Alembic.
-   Tests: pytest для backend; Vitest/Testing Library для frontend по
    мере необходимости.
-   Deployment/local development: Docker Compose.
-   File storage: локальная папка volume в MVP, интерфейс абстрагировать
    для последующего S3-compatible storage.

## Компоненты

1.  Web UI
2.  REST API
3.  Authentication / workspace authorization
4.  Product service
5.  Source ingestion service
6.  Claim extraction service
7.  Deterministic rule engine
8.  Optional LLM provider adapter
9.  Finding/review workflow
10. Report generator
11. PostgreSQL
12. File storage

## Принцип обработки

Upload/input -\> extract text -\> preserve source spans -\> extract
claim candidates -\> normalize structured facts -\> deterministic checks
-\> optional LLM classification -\> create findings -\> human review -\>
report.

## Архитектурные правила

-   Бизнес-логика не должна жить только в React-компонентах.
-   Внешний LLM-провайдер подключается через интерфейс, например
    `ClaimAnalysisProvider`.
-   Обязателен `MockAnalysisProvider`, чтобы тесты и demo работали без
    платного API.
-   Детерминированные проверки не должны зависеть от LLM.
-   Сохранять версию правил/модели и дату анализа.
-   Каждая операция над товаром проверяет workspace ownership.
-   Не хранить API-ключи в коде или браузере.
-   Файлы сохранять под сгенерированным идентификатором, а не исходным
    путём/именем.
-   Для MVP не нужны микросервисы, Kubernetes, блокчейн или сложная
    event streaming инфраструктура.

## Рекомендуемая структура репозитория

``` text
app/
  frontend/
    src/
      api/
      components/
      pages/
      types/
      tests/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      providers/
      rules/
      reports/
    tests/
  sample_data/
  docs/
  docker-compose.yml
  .env.example
  README.md
```

## Разделение ответственности

-   `ingestion`: чтение файлов и извлечение текста.
-   `claims`: хранение/редактирование утверждений.
-   `rules`: нормализация и проверка числовых значений.
-   `evidence`: источники и фрагменты.
-   `analysis`: координация pipeline.
-   `findings`: создание и статусная модель предупреждений.
-   `reports`: экспорт.
