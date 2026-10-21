<#
  Первичная установка проекта «Обещание против реальности» (Windows PowerShell).
  Использование:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "1/4 Проверка Python..." -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { throw "Python не найден. Установите Python 3.11+ и повторите." }
& python --version

Write-Host "2/4 Создание виртуального окружения .venv..." -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $root '.venv\Scripts\python.exe'))) {
    py -3.11 -m venv .venv
    if (-not (Test-Path (Join-Path $root '.venv\Scripts\python.exe'))) {
        python -m venv .venv
    }
}
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip

Write-Host "3/4 Установка зависимостей backend..." -ForegroundColor Cyan
& $venvPython -m pip install -r (Join-Path $root 'app\backend\requirements.txt')

Write-Host "4/4 Установка зависимостей frontend..." -ForegroundColor Cyan
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Push-Location (Join-Path $root 'app\frontend')
    try { npm install } finally { Pop-Location }
} else {
    Write-Host "npm не найден: пропускаю установку frontend-зависимостей." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Готово. Дальше:" -ForegroundColor Green
Write-Host "  1) Создайте БД:        psql -U postgres -h localhost -f scripts\init_db.sql"
Write-Host "  2) Примените миграции:  cd app\backend; ..\..\.venv\Scripts\python.exe -m alembic upgrade head"
Write-Host "  3) Запустите backend:   powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1"
Write-Host "  4) Запустите frontend:  powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1"
