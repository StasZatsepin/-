# Резервная копия MVP «Обещание против реальности» — версия v0.2.0

**Дата снимка:** 21.10.2026
**Версия:** `v0.2.0` (git-тег на коммите `f261801`, редизайн интерфейса)
**Проверено:** 77 backend-тестов, 20 frontend-тестов, `tsc --noEmit`, `vite build`,
28/28 проверок готовности (`scripts/verify_release.py`)

Предыдущий снимок — `backup/2026-10-21/` (версия `v0.1.0`).

---

## Состав архива

| Файл | Размер | Что это |
|---|---|---|
| `db_obeshchanie.dump` | 62 КБ | Дамп БД PostgreSQL в формате custom (`pg_dump -Fc`) |
| `db_obeshchanie.sql` | 288 КБ | Тот же дамп в виде обычного SQL-скрипта |
| `obeshchanie-v0.2.0.bundle` | 1013 КБ | Полная история Git со всеми коммитами и тегами `v0.1.0`, `v0.2.0` |
| `source-v0.2.0.zip` | 1576 КБ | Исходники проекта (файлы, отслеживаемые Git) |
| `checksums.txt` | — | Контрольные суммы SHA-256 файлов |
| `BACKUP_INFO.md` | — | Этот файл |

В дампе база **без тестовых данных**: рабочее пространство демо, 1 товар,
5 источников, 50 утверждений, 55 доказательств, 112 находок (14 активных,
остальные архивные от повторных проверок), 7 запусков анализа, 1 запись истории решений.

---

## Важно: отличие от снимка v0.1.0

В версии `v0.1.0` шаблон HTML-отчёта
(`app/backend/app/reports/templates/report.html.j2`) **не был** в репозитории:
правило `reports/` в `.gitignore` исключало любую папку с таким именем.
На копии, взятой из тега `v0.1.0`, отчёт не формируется — шаблон нужно
восстановить вручную из `backup/2026-10-21-redesign/source-v0.2.0.zip`
(путь `app/backend/app/reports/templates/report.html.j2`).

Ошибка исправлена в `v0.2.0`: правило заменено на `/reports/`, шаблон добавлен
в индекс Git. Проверка: `git check-ignore -v app/backend/app/reports/templates/report.html.j2`
должен вернуть код 1 (файл не игнорируется).

---

## Как восстановить

### Вариант 1. Только база данных

```powershell
$env:PGPASSWORD = 'oapv_local_dev'
$pgbin = "C:\Program Files\PostgreSQL\18\bin"

& "$pgbin\pg_restore.exe" -U oapv_app -h localhost -d obeshchanie `
    --clean --if-exists "D:\Control\Проект конкурса\backup\2026-10-21-redesign\db_obeshchanie.dump"
```

Через `psql` (plain SQL):

```powershell
$env:PGPASSWORD = 'oapv_local_dev'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U oapv_app -h localhost -d obeshchanie `
    -f "D:\Control\Проект конкурса\backup\2026-10-21-redesign\db_obeshchanie.sql"
```

### Вариант 2. Весь проект целиком (код + история + БД)

```powershell
cd "D:\Control\Проект конкурса"

# 1) Исходники
Expand-Archive -Path "backup\2026-10-21-redesign\source-v0.2.0.zip" -DestinationPath "D:\restore\project" -Force

# 2) История Git
cd "D:\restore\project"
git clone "D:\Control\Проект конкурса\backup\2026-10-21-redesign\obeshchanie-v0.2.0.bundle" restored-repo
cd restored-repo
git checkout v0.2.0

# 3) База
$env:PGPASSWORD = 'oapv_local_dev'
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -U oapv_app -h localhost -d obeshchanie `
    --clean --if-exists "D:\Control\Проект конкурса\backup\2026-10-21-redesign\db_obeshchanie.dump"
```

### Вариант 3. Откат в текущем репозитории (быстро)

```powershell
cd "D:\Control\Проект конкурса"

git log --oneline v0.2.0..HEAD     # что изменилось после стабильной версии
git diff --stat v0.2.0 HEAD

git reset --hard v0.2.0            # откат к редизайну
git reset --hard v0.1.0            # откат к версии до редизайна

# Откат, но с сохранением текущих изменений в отдельной ветке
git branch rescue-current
git reset --hard v0.2.0
```

Откат кода не откатывает данные в базе: если нужна и старая база —
восстановите дамп из нужного снимка (вариант 1 или 2).

---

## Проверка целостности архива

```powershell
cd "D:\Control\Проект конкурса\backup\2026-10-21-redesign"
Get-Content checksums.txt | ForEach-Object {
    $parts = $_ -split '\s+', 2
    $actual = (Get-FileHash $parts[1] -Algorithm SHA256).Hash.ToLower()
    "{0}  {1}" -f $(if ($actual -eq $parts[0]) { "OK  " } else { "FAIL" }), $parts[1]
}
```

Резервная копия проверяется на практике: дамп восстанавливается во временную базу
`obeshchanie_restore_check`, количество строк во всех таблицах сверяется с рабочей базой,
временная база удаляется.
