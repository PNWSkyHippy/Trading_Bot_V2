$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot "venv312\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  $python = "python"
}

Write-Host "Starting HTML dashboard bridge..."
Write-Host "Open this URL in your browser: http://localhost:8125"
Write-Host "Leave this window open while using the dashboard."
Write-Host ""

try {
  & $python ".\web_dashboard.py"
}
catch {
  Write-Host ""
  Write-Host "Web dashboard stopped with an error:" -ForegroundColor Red
  Write-Host $_
}
finally {
  Write-Host ""
  Read-Host "Press Enter to close this window"
}
