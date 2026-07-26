#!/usr/bin/env bash
set -euo pipefail

SERVICES=(
  trading-bot.service
  web-dashboard.service
  breakout-scanner.service
  ibkr-watchdog.service
  astral-drift.service
  astral-exploration-api.service
  emt-scanner.service
  emt-watchdog.service
  emt-watchdog.timer
)

echo "== systemd service state =="
for svc in "${SERVICES[@]}"; do
  if systemctl list-unit-files "$svc" >/dev/null 2>&1; then
    systemctl --no-pager --full status "$svc" || true
  else
    echo "$svc: not installed"
  fi
  echo
done

echo "== listening ports =="
ss -ltnp 2>/dev/null | grep -E ':(8125|8181)\b' || true

echo
echo "== recent bot logs =="
tail -n 80 logs/bot.log 2>/dev/null || true

