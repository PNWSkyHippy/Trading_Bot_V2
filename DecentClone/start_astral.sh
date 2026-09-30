#!/bin/bash

# Get the absolute path of the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_URI[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "Astral Drift - local web server"
echo "--------------------------------"
echo "Chrome blocks textures on file:// (same as three.min.js)."
echo "Serving this folder at http://localhost:8127/"
echo ""
echo "NOTE: Saved maps are per-origin. file:// and localhost:8127"
echo "use separate storage. Export Library Backup in Shift+R before"
echo "switching, or copy backup to data/map_library_bundle.json"
echo ""
echo "Opening browser... leave this window open while you play."
echo "Press Ctrl+C here to stop the server."
echo ""

# Open the browser automatically on Ubuntu
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:8127/index.html" &
fi

# Check for Python Virtual Environment (adjust path for Linux layout)
PY=""
if [ -f "$SCRIPT_DIR/../venv312/bin/python" ]; then
    PY="$SCRIPT_DIR/../venv312/bin/python"
fi

if [ -n "$PY" ]; then
    "$PY" -m http.server 8127
    exit 0
fi

# Fallback to system-level python3
if command -v python3 > /dev/null; then
    python3 -m http.server 8127
    exit 0
fi

# Fallback to generic python command
if command -v python > /dev/null; then
    python -m http.server 8127
    exit 0
fi

echo "ERROR: Python not found. Install Python 3 or activate venv312, then rerun."
read -p "Press Enter to exit..."
