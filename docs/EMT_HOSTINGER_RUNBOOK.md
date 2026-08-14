# EMT Hostinger Runbook

The EMT receiver runs on Hostinger and stays bound to `127.0.0.1:8765`.
NinjaTrader reaches it through an SSH tunnel, so the authenticated order-signal
receiver is not exposed to the public internet.

## Trading specification

- Instrument: one `ESU6` contract (`ES 09-26` in NinjaTrader)
- Opening range: 6:30–6:45 AM Pacific / 9:30–9:45 AM Eastern
- Entry window: 6:45–7:45 AM Pacific / 9:45–10:45 AM Eastern
- Chart: 610 tick
- Entry: opening-range breakout with both price and Keltner EMA outside the
  range, retracement to the EMA, then one-tick continuation confirmation
- Repeat: after a completed bracket, re-arm from the newest low for shorts or
  newest high for longs
- Protection: 2 points (8 ES ticks) stop and 2 points target, submitted as a
  Tradovate server-side multi-bracket

## Required Hostinger environment

Add these to `/opt/trading_bot_v2/.env` and keep the file mode at `600`:

```dotenv
EMT_EXECUTION_MODE=paper
EMT_LIVE_TRADING=DISABLED
TRADOVATE_ENVIRONMENT=demo
TRADOVATE_ACCESS_TOKEN=
TRADOVATE_USERNAME=<Tradovate login>
TRADOVATE_PASSWORD=<Tradovate password>
TRADOVATE_APP_ID=EMT Hostinger
TRADOVATE_APP_VERSION=1.0
TRADOVATE_CID=<API key client id>
TRADOVATE_SEC=<API key secret>
TRADOVATE_DEVICE_ID=<stable UUID for this Hostinger installation>
TRADOVATE_ACCOUNT_ID=<numeric account id>
TRADOVATE_ACCOUNT_SPEC=<account name>
NINJA_BRIDGE_SECRET=<same long random value used by both Ninja bridges>
```

Use official Tradovate API-key credentials with the appropriate account and
API subscription. The service acquires a fresh access token at startup and may
re-authenticate once after a confirmed 401. Do not copy credentials into JSON,
Python, C#, Git, or systemd unit files.

## Install and start

```bash
sudo cp deploy/systemd/emt-scanner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now emt-scanner.service
sudo systemctl status emt-scanner.service
```

## NinjaTrader-to-Hostinger tunnel

On the Windows NinjaTrader machine, run this before the bridges start:

```powershell
ssh -N -L 8765:127.0.0.1:8765 ronh@187.127.248.52
```

Both Ninja bridge endpoints remain `http://127.0.0.1:8765`. The opening-range
bridge and EMT 610-tick bridge must use exactly the same secret as
`NINJA_BRIDGE_SECRET`.

Check from Windows while the tunnel is open:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

## Activation sequence

1. Run with `EMT_EXECUTION_MODE=paper` and verify both one-minute and 610-tick
   data arrive during a full session.
2. Use a demo account token with `TRADOVATE_ENVIRONMENT=demo` and set
   `EMT_EXECUTION_MODE=live`; verify accepted entry, stop, target, completion,
   and re-arm behavior.
3. Confirm the account is flat and has no working ES strategy.
4. For real orders only, use a live-account token and set exactly:

```dotenv
EMT_EXECUTION_MODE=live
EMT_LIVE_TRADING=I_UNDERSTAND_LIVE_ORDERS
TRADOVATE_ENVIRONMENT=live
```

5. Restart and inspect logs:

```bash
sudo systemctl restart emt-scanner.service
sudo journalctl -u emt-scanner.service -n 200 --no-pager
```

The process refuses a live startup without the exact acknowledgement, refuses
an account/token mismatch, and refuses an entry if the account already has an
ES position or working ES order strategy. An ambiguous order timeout halts new
entries and is never retried automatically.
