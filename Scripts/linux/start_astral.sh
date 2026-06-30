#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/root/Trading_Bot_V2/DecentClone"
PY="/root/Trading_Bot_V2/venv312/bin/python"

cd "$APP_DIR"

if [ -x "$PY" ]; then
    exec "$PY" -m http.server 8127 --bind 0.0.0.0
fi

exec python3 -m http.server 8127 --bind 0.0.0.0


