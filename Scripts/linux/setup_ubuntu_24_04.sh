#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/trading_bot_v2}"
APP_USER="${APP_USER:-$USER}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

echo "== Trading Bot V2 Ubuntu 24.04 setup =="
echo "APP_DIR=$APP_DIR"
echo "APP_USER=$APP_USER"

sudo apt-get update
sudo apt-get install -y \
  ca-certificates curl git jq tmux htop ripgrep \
  python3.12 python3.12-venv python3-pip \
  nodejs npm

if [ ! -d "$APP_DIR" ]; then
  echo "Creating $APP_DIR"
  sudo mkdir -p "$APP_DIR"
  sudo chown "$APP_USER":"$APP_USER" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -d "venv312" ]; then
  "$PYTHON_BIN" -m venv venv312
fi

./venv312/bin/python -m pip install --upgrade pip wheel setuptools
if [ -f requirements.txt ]; then
  ./venv312/bin/python -m pip install -r requirements.txt
fi

mkdir -p logs reports data

echo
echo "Core OS/Python setup complete."
echo "Next:"
echo "  1. Put .env in $APP_DIR"
echo "  2. Install Codex/Claude CLI if wanted:"
echo "     curl -fsSL https://chatgpt.com/codex/install.sh | sh"
echo "     curl -fsSL https://claude.ai/install.sh | bash"
echo "  3. Copy systemd units from deploy/systemd/ to /etc/systemd/system/"
echo "  4. sudo systemctl daemon-reload"
