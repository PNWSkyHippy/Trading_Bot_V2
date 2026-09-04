@echo off
setlocal
cd /d "%~dp0"
title Astral Drift seam lab
echo.
echo  Seam lab - local web server
echo  ---------------------------
echo  Serving this folder at http://localhost:8132/
echo  Opening tunnel_seam_lab.html (index.html is untouched).
echo.

start "" "http://localhost:8132/tunnel_seam_lab.html"

set "PY="
if exist "%~dp0..\venv312\Scripts\python.exe" set "PY=%~dp0..\venv312\Scripts\python.exe"

if defined PY (
    "%PY%" -m http.server 8132
    goto :done
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m http.server 8132
    goto :done
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -m http.server 8132 2>nul
    if %errorlevel%==0 goto :done
)

echo ERROR: Python not found. Install Python 3 or activate venv312, then rerun.
pause
:done
