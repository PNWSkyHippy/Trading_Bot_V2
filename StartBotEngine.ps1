$ErrorActionPreference = "Continue"

Set-Location -LiteralPath $PSScriptRoot

Write-Host "============================================================"
Write-Host "  TRADING BOT ENGINE"
Write-Host "============================================================"
Write-Host "Working directory: $(Get-Location)"
Write-Host ""

$activate = Join-Path $PSScriptRoot "venv312\Scripts\Activate.ps1"
if (-not (Test-Path -LiteralPath $activate)) {
  Write-Host "ERROR: venv312\Scripts\Activate.ps1 was not found." -ForegroundColor Red
  Read-Host "Press Enter to close this window"
  exit 1
}

. $activate
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Python path:"
python -c "import sys; print(sys.executable)"
Write-Host ""
Write-Host "Starting bot_engine.py..."
Write-Host ""

python .\bot_engine.py

Write-Host ""
Write-Host "bot_engine.py exited with code $LASTEXITCODE."
Read-Host "Press Enter to close this window"
