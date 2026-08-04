# EMT/EAT Scanner Pipeline Health and Recovery Runbook

This is the start-to-finish operating procedure for the NinjaTrader futures data pipeline. It matches the current two-port architecture and is safe to use while paper or live strategy execution is enabled.

The health checks are read-only. They do not submit orders, inject bars, restart services, kill processes, or change strategy configuration.

## Pipeline architecture

```text
NinjaTrader market-data connection
        |
        v
PythonFuturesBridge.cs (NinjaTrader AddOn)
        |
        +--> http://127.0.0.1:8765  local scanner
        |
        +--> http://127.0.0.1:8766  Windows SSH tunnel
                                      |
                                      v
                              Hostinger 127.0.0.1:8765
                                      |
                                      v
                              emt-scanner.service
                                      |
                         EMT/EAT state, trades, web dashboard
```

The two Windows ports must remain different:

- `8765` is the local Python scanner.
- `8766` is the local entrance to the Hostinger SSH tunnel.
- The tunnel forwards Windows `127.0.0.1:8766` to Hostinger `127.0.0.1:8765`.

Do not use the old command that binds the tunnel to Windows port `8765`. That conflicts with the local scanner and lets only one process own the port.

## Fastest complete check

Open PowerShell in `C:\Users\Linda\Trading_Bot_V2` and run:

```powershell
.\Scripts\Test-EMTScannerPipeline.ps1 -Remote
```

For continuous monitoring:

```powershell
.\Scripts\Test-EMTScannerPipeline.ps1 -Remote -Watch -IntervalSeconds 30
```

`Ctrl+C` stops watch mode.

The script checks:

1. NinjaTrader is running.
2. The C# file installed in NinjaTrader matches the repository source.
3. Active contract names match between those copies.
4. The tunnel Scheduled Task is running, when PowerShell has permission.
5. Local `/health` and `/snapshot` respond.
6. Hostinger `/health` and `/snapshot` respond through port `8766`.
7. Heartbeat freshness and completed-bar freshness independently.
8. One-minute bars for every configured symbol.
9. EMT 610-tick count, phase, and status.
10. EAT phase and status.
11. With `-Remote`, the Hostinger systemd service state.

Exit severity is `0` healthy, `1` warning, or `2` failure. Run PowerShell as Administrator if Task Scheduler access is denied. Endpoint and market-data checks still work without elevation.

## Interpret the result

Heartbeat and bar flow are different signals. A heartbeat proves the AddOn, HTTP sender, tunnel, and receiver can exchange a small message. It does not prove NinjaTrader is delivering market-data callbacks.

| Local `8765` | Hostinger `8766` | Meaning | Start at |
|---|---|---|---|
| Down | Down | Local scanner unavailable; tunnel status is secondary | Local scanner |
| Heartbeat healthy, bars stale | Same | AddOn alive but Ninja subscriptions are not producing bars | Ninja connection, contracts, AddOn |
| Bars fresh | Down | Local feed works; remote route is broken | Tunnel, then VPS service |
| Bars fresh | Heartbeat only/bars stale | Small messages pass but bar delivery is delayed or dropped | Tunnel latency/queue and VPS logs |
| Bars fresh | Bars fresh | End-to-end pipeline healthy | Do not restart |

During the daily futures maintenance break or weekend closure, stale bars are expected. During an open market, ES/MES and NQ/MNQ are the best canaries.

## Step 1: Verify NinjaTrader

1. NinjaTrader must be open.
2. Its connection indicator must be green.
3. The expected simulation/data account must be connected.
4. Open **New > NinjaScript Output**.
5. Look for recent messages such as:

```text
PythonFuturesBridge HEARTBEAT ok -> local
PythonFuturesBridge HEARTBEAT ok -> hostinger
PythonFuturesBridge completed bar queued: ES ...
PythonFuturesBridge EMT completed 610t bar queued: ES ...
```

Message meanings:

- `HEARTBEAT ok` proves connectivity only.
- `completed bar queued` proves a one-minute subscription produced a completed bar.
- `EMT completed 610t bar queued` proves a 610-tick stream produced a bar.
- `silent for ...; resubscribing` means the watchdog saw no Update callback for 120 seconds and recreated that subscription.
- One illiquid symbol resubscribing may be normal. All liquid index contracts repeatedly resubscribing together indicates a Ninja connection/subscription problem.
- `queue full`, `giving up`, `dropping stale`, repeated timeouts, or repeated Hostinger failures indicate sender/tunnel pressure.

## Step 2: Verify Ninja compiled the correct C# file

NinjaTrader compiles:

```text
C:\Users\Linda\OneDrive\Documents\NinjaTrader 8\bin\Custom\AddOns\PythonFuturesBridge.cs
```

Editing only this repository file does not update NinjaTrader:

```text
C:\Users\Linda\Trading_Bot_V2\ninjatrader_bridge\PythonFuturesBridge.cs
```

Compare them:

```powershell
$source = "C:\Users\Linda\Trading_Bot_V2\ninjatrader_bridge\PythonFuturesBridge.cs"
$installed = "C:\Users\Linda\OneDrive\Documents\NinjaTrader 8\bin\Custom\AddOns\PythonFuturesBridge.cs"
Get-FileHash $source
Get-FileHash $installed
code --diff $installed $source
```

When the repository copy is the intended version, install it:

```powershell
Copy-Item -LiteralPath $source -Destination $installed -Force
```

Then compile once in NinjaScript Editor. Confirm Output names the intended active contracts. Do not assume compiling a repository copy made Ninja use it.

### Mismatch found August 3, 2026

The installed AddOn was dated July 30 and still subscribed to:

```text
MGC 08-26, GC 08-26, MBT 07-26, MET 07-26
```

The newer source used:

```text
MGC 10-26, GC 10-26, MBT 08-26, MET 08-26
```

That explains MET showing a last local bar from July 31 while its heartbeat remained healthy. Always verify the installed copy after a contract roll.

## Step 3: Verify local scanner port 8765

Compact health:

```powershell
$h = Invoke-RestMethod http://127.0.0.1:8765/health -TimeoutSec 10
$h.bridge | Format-List alive, age_seconds, subscriptions, reported_time
```

Compact bars without dumping the full snapshot:

```powershell
$s = Invoke-RestMethod http://127.0.0.1:8765/snapshot -TimeoutSec 20
foreach ($symbol in "MES","ES","MNQ","NQ","MYM","YM","M2K","RTY","MGC","GC","NKD","MBT","MET") {
    $bars = @($s.bars.$symbol)
    $last = if ($bars.Count) { $bars[-1].time } else { "--" }
    "{0,-4} bars={1,4} last={2} receive_age={3}" -f $symbol, $bars.Count, $last, $s.last_received.$symbol
}
```

Expected during an open market:

- `bridge.alive` is `True` and heartbeat age stays below 75 seconds.
- Liquid symbols receive completed bars.
- Local startup history normally seeds about 90 one-minute bars.
- EMT 610-tick count grows only when 610 trades complete a bar; it need not increase each minute.

### Cleanly restart only the local scanner

Use this only if local port `8765` is down or the local scanner is wedged:

```powershell
Start-Process .\ninjatrader_bridge\kill_local_scanner.bat -Wait
Start-Process .\ninjatrader_bridge\start_local_scanner.bat
```

The start script kills leftover scanner copies first and starts exactly one using `ninja_futures_config_local.json`.

Do not restart a healthy scanner merely because a strategy says `WARMING`. Restarting discards in-memory bars and session state.

## Step 4: Verify Windows SSH tunnel port 8766

The Scheduled Task is named `EMT Hostinger Tunnel`.

From elevated PowerShell:

```powershell
Get-ScheduledTask -TaskName "EMT Hostinger Tunnel"
Get-ScheduledTaskInfo -TaskName "EMT Hostinger Tunnel" | Format-List *
```

Check Hostinger through the tunnel:

```powershell
Invoke-RestMethod http://127.0.0.1:8766/health -TimeoutSec 10 |
    Select-Object ok, bridge, symbols
```

Read its log:

```powershell
Get-Content .\logs\emt_tunnel.log -Tail 80 -Wait
```

Install or repair from elevated PowerShell:

```powershell
.\Scripts\install_emt_hostinger_tunnel.ps1
```

The hidden supervisor uses OpenSSH BatchMode, keepalives, and forward-failure detection. It forwards:

```text
Windows 127.0.0.1:8766 -> Hostinger 127.0.0.1:8765
```

If `8765/health` works but `8766/health` does not, the problem is not local Ninja data. Check the task, tunnel log, SSH key, network path, and VPS service.

## Step 5: Verify Hostinger directly

Connect:

```powershell
ssh -i "$env:USERPROFILE\.ssh\emt_tunnel_key" ronh@187.127.248.52
```

On Hostinger:

```bash
date
systemctl is-active emt-scanner.service
systemctl status emt-scanner.service --no-pager
systemctl show emt-scanner.service \
  -p MainPID -p NRestarts -p ActiveEnterTimestamp
curl -sS --max-time 10 http://127.0.0.1:8765/health | python3 -m json.tool
journalctl -u emt-scanner.service --since "30 minutes ago" --no-pager
```

Follow logs live:

```bash
journalctl -fu emt-scanner.service
```

Healthy logs show current status/events and increasing bar information, not only heartbeats.

Restart the VPS scanner only when inactive, crashed, or demonstrably wedged:

```bash
sudo systemctl restart emt-scanner.service
sudo systemctl status emt-scanner.service --no-pager
```

Important: Ninja startup history is sent to the local scanner only. Hostinger receives live bars. Restarting `emt-scanner.service` clears in-memory history and makes EMT/EAT rebuild from new live bars. A needless restart can cost much of a session.

## Step 6: Prove bars are moving

Run twice at least 70 seconds apart:

```powershell
.\Scripts\Test-EMTScannerPipeline.ps1
Start-Sleep 70
.\Scripts\Test-EMTScannerPipeline.ps1
```

During an active market, ES/MNQ last-bar time or receive age should advance on both endpoints. Counts may be capped by a rolling window, so timestamp and receive age matter more than total count.

Do not POST a fake production bar. It can alter opening ranges, indicator state, and automatic trading decisions.

## Safe recovery order

Use the first applicable step and stop when healthy:

1. Confirm the market is open and Ninja is connected.
2. Confirm installed AddOn contracts and source match.
3. If local `8765` is down, restart the local scanner.
4. If local is fresh but `8766` is down, repair the tunnel task.
5. If the tunnel connects but systemd is inactive, restart only `emt-scanner.service`.
6. Recompile only for installed-source mismatch or persistent subscription failure. Verify Output.
7. Re-run `Test-EMTScannerPipeline.ps1 -Remote`.

Avoid restarting everything at once. That destroys evidence of where failure began and resets remote warm-up data.

## Common failure signatures

### Heartbeats arrive but no bars

Check Ninja data entitlement, expired contract months, wrong AddOns copy, repeated resubscribe messages on liquid contracts, and absence of `completed bar queued` messages.

### Local bars fresh but Hostinger stale

Check `8766/health`, `logs/emt_tunnel.log`, Hostinger latency, systemd, and Ninja Output for timeouts, queue saturation, stale drops, or retries giving up.

### Hostinger has only a few bars after restart

Expected under the current design: historical seeds are local-only and Hostinger rebuilds from live traffic. Avoid remote restarts during a session.

### Only MET, MBT, gold, or NKD stale

Verify active contract month first, then liquidity/session hours. Do not condemn the whole pipeline when ES/MNQ are fresh at both endpoints.

### `/snapshot` slow but `/health` fast

The snapshot contains bars, overlays, Keltner arrays, and strategy state. It is much larger. Persistent multi-second or timed-out responses on `8766` indicate tunnel/VPS pressure even if heartbeat succeeds.

## Files involved

| Purpose | File |
|---|---|
| Ninja AddOn source | `ninjatrader_bridge/PythonFuturesBridge.cs` |
| Installed Ninja AddOn | `OneDrive/Documents/NinjaTrader 8/bin/Custom/AddOns/PythonFuturesBridge.cs` |
| Local scanner config | `ninjatrader_bridge/ninja_futures_config_local.json` |
| Hostinger scanner config | `ninjatrader_bridge/ninja_futures_config.json` |
| Scanner/HTTP receiver | `ninjatrader_bridge/ninja_futures_scanner.py` |
| Local scanner start/stop | `ninjatrader_bridge/start_local_scanner.bat`, `kill_local_scanner.bat` |
| Tunnel install/supervisor | `Scripts/install_emt_hostinger_tunnel.ps1`, `run_emt_hostinger_tunnel.ps1` |
| Tunnel log | `logs/emt_tunnel.log` |
| Hostinger unit | `deploy/systemd/emt-scanner.service` |
| Automated checker | `Scripts/Test-EMTScannerPipeline.ps1` |