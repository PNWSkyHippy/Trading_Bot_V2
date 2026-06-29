# Hostinger Ubuntu 24.04 Server Migration

This deploy pack assumes the repo lives at:

```bash
/opt/trading_bot_v2
```

If you use another path, edit the `WorkingDirectory` and `ExecStart` paths in `deploy/systemd/*.service`, or set `APP_DIR` when running the setup script.

## Current State

Linda already cloned the repo, created the Python venv, and installed Python dependencies on the virtual server. The remaining server work is:

- install Codex CLI and Claude Code CLI locally
- copy `.env` securely
- install systemd service units
- start and verify services
- later: IBKR Gateway Linux install/watchdog hardening

## Install Codex CLI

Official Linux install command:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Unattended install:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh
```

Then authenticate:

```bash
codex
```

Codex user config is normally at:

```bash
~/.codex/config.toml
```

## Install Claude Code CLI

Official native Linux install command:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Alternative npm install, if Node.js 18+ is present:

```bash
npm install -g @anthropic-ai/claude-code
```

Then authenticate:

```bash
claude
```

Claude settings are normally at:

```bash
~/.claude/settings.json
```

## One-Time Ubuntu Setup

From the repo root:

```bash
chmod +x Scripts/linux/*.sh
APP_DIR=/opt/trading_bot_v2 ./Scripts/linux/setup_ubuntu_24_04.sh
```

This installs OS packages, ensures `venv312`, installs `requirements.txt`, and creates `logs/`, `reports/`, and `data/`.

## Environment File

Copy the Windows `.env` to the server repo root:

```bash
/opt/trading_bot_v2/.env
```

Keep it out of git. Confirm it is readable only by the server user:

```bash
chmod 600 /opt/trading_bot_v2/.env
```

## Install systemd Services

```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-bot.service web-dashboard.service breakout-scanner.service
```

Do not enable `ibkr-watchdog.service` until IBKR Gateway is installed and tested on Linux:

```bash
sudo systemctl enable ibkr-watchdog.service
```

## Start Services

```bash
sudo systemctl start trading-bot.service
sudo systemctl start web-dashboard.service
sudo systemctl start breakout-scanner.service
```

When IBKR Gateway is ready:

```bash
sudo systemctl start ibkr-watchdog.service
```

## Check Status

```bash
./Scripts/linux/status.sh
```

Or directly:

```bash
sudo systemctl status trading-bot.service
sudo systemctl status web-dashboard.service
sudo systemctl status breakout-scanner.service
sudo journalctl -u trading-bot.service -f
```

## Ports

- Dashboard: `8125`
- Bot API / breakout receiver: `8181`

Firewall example:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8125/tcp
sudo ufw allow 8181/tcp
sudo ufw enable
```

For production, prefer a reverse proxy with HTTPS and basic auth instead of exposing raw app ports.

## Logs

The scripts preserve the repo's normal log paths:

```bash
logs/bot.log
logs/scanner_signals.log
logs/watchdog_ibkr.log
```

Systemd logs are available with:

```bash
sudo journalctl -u trading-bot.service -n 200 --no-pager
```

## IBKR Gateway Notes

Linux IBKR Gateway is the remaining broker-specific setup item. Keep `IBKR_TRADE_ENABLED=False` until:

- Gateway starts reliably on the server
- API port and client ID are confirmed
- account mode is confirmed
- watchdog restart behavior is tested
- manual order lockout/safety is verified

The service unit currently calls:

```bash
/opt/trading_bot_v2/venv312/bin/python /opt/trading_bot_v2/Scripts/watchdog_ibkr.py --live
```

Adjust this after Gateway install if the Linux path or startup method differs.

## Safer First Boot Order

1. Start `web-dashboard.service`.
2. Start `trading-bot.service` with trading disabled/safe.
3. Check dashboard and logs.
4. Start `breakout-scanner.service`.
5. Install/test IBKR Gateway.
6. Start `ibkr-watchdog.service`.

## Sources

- Codex CLI install: https://developers.openai.com/codex/cli
- Codex config path: https://developers.openai.com/codex/config-basic
- Claude Code install: https://docs.anthropic.com/en/docs/claude-code/overview
- Claude Code npm install: https://docs.anthropic.com/en/docs/claude-code/setup
