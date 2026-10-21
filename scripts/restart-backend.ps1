<#
  Перезапуск локального backend в фоне (для разработки).
  Использование:  powershell -ExecutionPolicy Bypass -File scripts\restart-backend.ps1

  Процесс запускается полностью отсоединённым (через WMI), поэтому скрипт
  сразу возвращает управление и не держит консоль.
#>
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot

Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*' } |
    ForEach-Object {
        Write-Host "Останавливаю PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force
    }

Start-Sleep -Seconds 2

$python = Join-Path $root '.venv\Scripts\python.exe'
$backend = Join-Path $root 'app\backend'
$logDir = Join-Path $root 'app\backend\var'
$log = Join-Path $logDir 'backend.log'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$commandLine = "cmd /c cd /d `"$backend`" && `"$python`" -W ignore -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > `"$log`" 2>&1"
$created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $commandLine }

Start-Sleep -Seconds 4
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 10
    Write-Host "Backend готов: $($health.status) v$($health.version)" -ForegroundColor Green
} catch {
    Write-Host "Backend не отвечает. Смотрите $log" -ForegroundColor Red
    Get-Content $log -Tail 20
}
