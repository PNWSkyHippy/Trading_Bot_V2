# Fix corrupted candle_store.db -- run AFTER stopping the bot

$botDir = "C:\Users\Linda\trading_bot_v2"

Write-Host "Removing corrupted candle_store.db files..." -ForegroundColor Yellow

# Delete corrupted active DB + WAL files
Remove-Item "$botDir\data\candle_store.db" -Force -ErrorAction SilentlyContinue
Remove-Item "$botDir\data\candle_store.db-shm" -Force -ErrorAction SilentlyContinue
Remove-Item "$botDir\data\candle_store.db-wal" -Force -ErrorAction SilentlyContinue

# Delete orphan file in logs/data
Remove-Item "$botDir\logs\data\candle_store.db" -Force -ErrorAction SilentlyContinue

Write-Host "Done. Candle DB cleared -- will rebuild fresh on next bot start." -ForegroundColor Green
Write-Host "Now run: run_bot_window.ps1" -ForegroundColor Cyan
