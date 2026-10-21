<#
  Обёртка над podman compose для проекта «Обещание против реальности».

  Использование:
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 up
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 build
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 ps
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 logs
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 down
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 backup
    powershell -ExecutionPolicy Bypass -File scripts\podman.ps1 test

  Команды:
    up      — собрать образы и поднять стек (db, migrate, backend, frontend)
    build   — только пересобрать образы
    ps      — состояние контейнеров
    logs    — логи всех сервисов (follow)
    down    — остановить и удалить контейнеры (тома с данными сохраняются)
    backup  — дамп базы из контейнера в backup\container
    test    — прогнать тесты backend и frontend в контейнерах
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'build', 'ps', 'logs', 'down', 'backup', 'test', 'shell')]
    [string]$Command = 'ps',

    [switch]$Follow
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Compose-провайдер: podman-compose из venv проекта не требует Docker API
# в именованном канале и работает одинаково на любой машине.
$venvScripts = Join-Path $root '.venv\Scripts'
if (Test-Path (Join-Path $venvScripts 'podman-compose.exe')) {
    $env:PATH = "$venvScripts;$env:PATH"
    $env:PODMAN_COMPOSE_PROVIDER = 'podman-compose'
}

function Invoke-Compose {
    & podman compose @args
}

switch ($Command) {
    'up' {
        Invoke-Compose up -d --build
        Write-Host ''
        Write-Host 'Запуск завершён. Интерфейс:  http://localhost:8080' -ForegroundColor Green
        Write-Host 'API напрямую:      http://localhost:8000/health' -ForegroundColor Green
        Write-Host 'Логи:               podman compose logs -f' -ForegroundColor DarkGray
    }
    'build' { Invoke-Compose build }
    'ps' { Invoke-Compose ps }
    'logs' {
        if ($Follow) { Invoke-Compose logs -f } else { Invoke-Compose logs --tail 100 }
    }
    'down' {
        Invoke-Compose down
        Write-Host ''
        Write-Host 'Контейнеры остановлены. Данные в томах obeshchanie-pgdata и obeshchanie-storage сохранены.' -ForegroundColor Yellow
        Write-Host 'Полностью удалить тома (необратимо): podman volume rm obeshchanie-pgdata obeshchanie-storage' -ForegroundColor DarkYellow
    }
    'backup' {
        $target = Join-Path $root 'backup\container'
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        $stamp = Get-Date -Format 'yyyy-MM-dd-HHmmss'
        $file = Join-Path $target "obeshchanie-container-$stamp.sql"

        Write-Host 'Снимаю дамп базы из контейнера...' -ForegroundColor Cyan
        & podman exec obeshchanie-db pg_dump -U oapv -d obeshchanie --clean --if-exists > $file
        if ($LASTEXITCODE -ne 0) {
            throw "Не удалось снять дамп (код $LASTEXITCODE)"
        }
        Write-Host ("Готово: " + $file) -ForegroundColor Green
    }
    'test' {
        Write-Host 'Тесты backend в контейнере...' -ForegroundColor Cyan
        & podman exec `
            -e 'DATABASE_URL=postgresql+psycopg://oapv:oapv_container_local@db:5432/obeshchanie_test' `
            -e 'SECRET_KEY=container-test-secret' `
            obeshchanie-backend python -m pytest tests -q

        Write-Host ''
        Write-Host 'Тесты frontend (этап test образа)...' -ForegroundColor Cyan
        & podman build --target test -f app/frontend/Containerfile -t obeshchanie/frontend-test:local app
    }
    'shell' {
        Write-Host 'Контейнеры: obeshchanie-db, obeshchanie-backend, obeshchanie-frontend' -ForegroundColor DarkGray
        & podman exec -it obeshchanie-backend sh
    }
}
