<#
  Запуск frontend «Обещание против реальности» в Windows PowerShell.
  Использование:  powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1
#>
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'app\frontend'

if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host "Зависимости frontend не установлены. Выполните: cd app\frontend; npm install" -ForegroundColor Yellow
    exit 1
}

Set-Location $frontend

Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "API проксируется на http://127.0.0.1:8000" -ForegroundColor Cyan

npm run dev
