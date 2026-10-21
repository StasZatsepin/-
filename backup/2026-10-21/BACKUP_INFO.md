# Резервная копия MVP «Обещание против реальности»

**Дата снимка:** 21.10.2026
**Версия:** `v0.1.0` (git-тег на коммите `2e27313`)
**Проверено:** 28/28 проверок готовности, 77 backend-тестов, 13 frontend-тестов

---

## Состав архива

| Файл | Размер | Что это |
|---|---|---|
| `db_obeshchanie.dump` | 62 КБ | Дамп БД PostgreSQL в формате custom (`pg_dump -Fc`) |
| `db_obeshchanie.sql` | 287 КБ | Тот же дамп в виде обычного SQL-скрипта |
| `obeshchanie-v0.1.0.bundle` | 220 КБ | Полная история Git (`git bundle`) со всеми коммитами и тегом |
| `source-v0.1.0.zip` | 227 КБ | Исходники проекта (только файлы, отслеживаемые Git) |
| `checksums.txt` | — | Контрольные суммы SHA-256 файлов |
| `../README.txt` | — | Краткая справка по бэкапу |

В дампе база **без тестовых данных**: рабочее пространство демо, 1 товар,
5 источников, 50 утверждений, 55 доказательств, 112 находок (из них 14 активных,
остальные архивные от повторных проверок), 7 запусков анализа, 1 запись истории решений.

---

## Как восстановить

### Вариант 1. Только база данных

```powershell
$env:PGPASSWORD = 'oapv_local_dev'
$pgbin = "C:\Program Files\PostgreSQL\18\bin"

# Восстановить поверх текущей базы (старое содержимое будет заменено)
& "$pgbin\pg_restore.exe" -U oapv_app -h localhost -d obeshchanie `
    --clean --if-exists "D:\Control\Проект конкурса\backup\2026-10-21\db_obeshchanie.dump"
```

Через `psql` (plain SQL):

```powershell
$env:PGPASSWORD = 'oapv_local_dev'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U oapv_app -h localhost -d obeshchanie `
    -f "D:\Control\Проект конкурса\backup\2026-10-21\db_obeshchanie.sql"
```

### Вариант 2. Весь проект целиком (код + история + БД)

```powershell
cd "D:\Control\Проект конкурса"

# 1) Исходники
Expand-Archive -Path "backup\2026-10-21\source-v0.1.0.zip" -DestinationPath "D:\restore\project" -Force

# 2) История Git
cd "D:\restore\project"
git clone "D:\Control\Проект конкурса\backup\2026-10-21\obeshchanie-v0.1.0.bundle" restored-repo
cd restored-repo
git checkout v0.1.0

# 3) База
$env:PGPASSWORD = 'oapv_local_dev'
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -U oapv_app -h localhost -d obeshchanie `
    --clean --if-exists "D:\Control\Проект конкурса\backup\2026-10-21\db_obeshchanie.dump"
```

### Вариант 3. Откат в текущем репозитории (быстро)

```powershell
cd "D:\Control\Проект конкурса"

# Посмотреть, что изменилось после стабильной версии
git log --oneline v0.1.0..HEAD
git diff --stat v0.1.0 HEAD

# Откатить рабочую копию к стабильной версии
git reset --hard v0.1.0

# Откат, но с сохранением текущих изменений в отдельной ветке
git branch rescue-current
git reset --hard v0.1.0

# Только посмотреть стабильную версию, ничего не меняя
git checkout v0.1.0
```

Откат кода не откатывает данные в базе: если нужна и старая база —
восстановите дамп из этого архива (вариант 1 или 2).

---

## Проверка целостности архива

```powershell
cd "D:\Control\Проект конкурса\backup\2026-10-21"
Get-Content checksums.txt | ForEach-Object {
    $parts = $_ -split '\s+', 2
    $actual = (Get-FileHash $parts[1] -Algorithm SHA256).Hash.ToLower()
    "{0}  {1}" -f $(if ($actual -eq $parts[0]) { "OK  " } else { "FAIL" }), $parts[1]
}
```

Резервная копия уже проверена на практике: дамп восстановлен во временную базу
`obeshchanie_restore_check`, количество строк во всех таблицах совпало с рабочей базой,
временная база затем удалена.
