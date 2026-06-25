@echo off
setlocal
cd /d "%~dp0"
title Astral Drift local server
echo.
echo  Astral Drift - local web server
echo  --------------------------------
echo  Chrome blocks textures on file:// (same as three.min.js).
echo  Serving this folder at http://localhost:8131/
echo.
echo  NOTE: Saved maps are per-origin. file:// and localhost:8131
echo  use separate storage. Export Library Backup in Shift+R before
echo  switching, or copy backup to data\map_library_bundle.json
echo.
echo  Opening browser... leave this window open while you play.
echo  Press Ctrl+C here to stop the server.
echo.

start "" "http://localhost:8131/tunnel_test.html"

set "PY="
if exist "%~dp0..\..\..\venv312\Scripts\python.exe" set "PY=%~dp0..\..\..\venv312\Scripts\python.exe"

if defined PY (
    "%PY%" -m http.server 8131
    goto :done
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m http.server 8131
    goto :done
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -m http.server 8131 2>nul
    if %errorlevel%==0 goto :done
)

echo ERROR: Python not found. Install Python 3 or activate venv312, then rerun.
pause
:done
