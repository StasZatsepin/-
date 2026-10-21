# Предварительный API-контракт

Все маршруты под `/api/v1`. Формы окончательно уточняются при
реализации, но не меняются без обновления документации и тестов.

## Products

-   `GET /products` --- список товаров текущего workspace.
-   `POST /products` --- создать товар.
-   `GET /products/{product_id}` --- получить товар.
-   `PATCH /products/{product_id}` --- изменить поля товара.
-   `DELETE /products/{product_id}` --- удалить товар и связанные
    пользовательские данные согласно выбранной политике.

Пример POST:

``` json
{
  "name": "Демонстрационные беспроводные наушники",
  "marketplace": "demo",
  "category": "electronics",
  "description": "До 48 часов работы без подзарядки",
  "attributes": {
    "battery_life_hours": 30,
    "model": "DEMO-100"
  }
}
```

Пример явно демонстрационный; не относится к реальному товару.

## Sources

-   `POST /products/{product_id}/sources` --- загрузить источник.
-   `GET /products/{product_id}/sources` --- список источников.
-   `GET /sources/{source_id}` --- метаданные источника.
-   `DELETE /sources/{source_id}` --- удалить источник с учётом
    связанных записей.

Первый этап: TXT, CSV; PDF с извлекаемым текстом --- после проверки
библиотеки. MIME type и размер проверяются сервером.

## Analysis

-   `POST /products/{product_id}/analysis-runs` --- запустить анализ.
-   `GET /products/{product_id}/analysis-runs` --- история запусков.
-   `GET /analysis-runs/{run_id}` --- статус и результат.

Результат содержит `claims`, `findings`, `source_refs`, `limitations`,
`engine_version`.

## Findings

-   `GET /products/{product_id}/findings` --- фильтрация по
    status/severity/type.
-   `PATCH /findings/{finding_id}` --- обновить статус и комментарий.
-   `GET /findings/{finding_id}/history` --- история решений.

## Reports

-   `GET /products/{product_id}/reports/{analysis_run_id}` ---
    HTML-отчёт.
-   PDF --- опциональный P1/P2.

## Ошибки

Единый формат:

``` json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Проверьте заполненные поля",
    "details": []
  }
}
```

Не возвращать traceback, SQL, секреты, содержимое чужих документов или
stack trace в production response.
