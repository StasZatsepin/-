<#
  Запуск backend «Обещание против реальности» в Windows PowerShell.
  Использование:  powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1
#>
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host "Виртуальное окружение не найдено. Сначала выполните: scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

Set-Location (Join-Path $root 'app\backend')

Write-Host "Backend: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Swagger: http://127.0.0.1:8000/api/docs" -ForegroundColor Cyan

& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
