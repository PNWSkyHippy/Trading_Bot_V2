@echo off
rem Explorer sets the working directory to this folder when you double-click
rem it, but anything else that launches this .bat (the watchdog, Task
rem Scheduler, etc.) may not -- and ninja_futures_scanner.py's --config path
rem is relative, so it silently crashes if the cwd is wrong. Force it.
cd /d "%~dp0"
set NINJA_BRIDGE_SECRET=okay-so-i-changed-secret
rem Kill any leftover ninja_futures_scanner.py instance first. Restarting used
rem to just launch a second copy alongside whatever was already running;
rem whichever one won the port 8765 race got the live data while the other
rem sat there as an invisible orphan and the visible window kept showing
rem stale/no data. This guarantees exactly one copy going forward.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*ninja_futures_scanner.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul
"%~dp0..\venv312\Scripts\python.exe" "%~dp0ninja_futures_scanner.py" --config ninja_futures_config_local.json
