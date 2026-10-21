<#
  Перезапуск локального backend (для разработки).
  Использование:  powershell -ExecutionPolicy Bypass -File scripts\restart-backend.ps1

  Останавливает ранее запущенный экземпляр и стартует новый в текущем окне
  (логи uvicorn идут в консоль). Для фонового запуска используйте
  scripts\run-backend.ps1 в отдельном окне.
#>
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot

$existing = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -like 'python*' -and
        ($_.CommandLine -like '*uvicorn*app.main:app*' -or $_.CommandLine -like '*multiprocessing.spawn*')
    }
foreach ($process in $existing) {
    Write-Host "Останавливаю предыдущий backend (PID $($process.ProcessId))"
    Stop-Process -Id $process.ProcessId -Force
}
Start-Sleep -Seconds 3

$ErrorActionPreference = 'Stop'
$python = Join-Path $root '.venv\Scripts\python.exe'
$backend = Join-Path $root 'app\backend'

if (-not (Test-Path $python)) {
    throw "Виртуальное окружение не найдено. Сначала выполните scripts\setup.ps1"
}

Set-Location $backend
Write-Host "Backend: http://127.0.0.1:8000" -ForegroundColor Cyan
& $python -W ignore -m uvicorn app.main:app --host 127.0.0.1 --port 8000
