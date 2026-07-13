# NinjaTrader → Python Futures Scanner

This proof of concept is read-only. NinjaTrader sends completed one-minute bars
for the MES/ES, MNQ/NQ, MYM/YM, M2K/RTY, and MGC/QO/GC families to a Python process
bound to `127.0.0.1`. There is no
order endpoint.

## 1. Choose a shared secret

Replace `change-this-local-secret` with the same long random value in:

- `PythonFuturesBridge.cs`
- `ninja_futures_config.json`

Do not commit the personalized secret.

## 2. Start Python

From PowerShell in the repository:

```powershell
venv312\Scripts\python.exe ninjatrader_bridge\ninja_futures_scanner.py
```

The initial display will show `STALE` until NinjaTrader publishes bars.

## 3. Install the NinjaTrader AddOn

1. Copy `PythonFuturesBridge.cs` to
   `Documents\NinjaTrader 8\bin\Custom\AddOns\PythonFuturesBridge.cs`.
2. In NinjaTrader Desktop, open **New → NinjaScript Editor**.
3. Right-click in the editor and choose **Compile** (or press F5).
4. Keep NinjaTrader connected to the real-time simulation data feed.
5. Check the NinjaScript Output window for three `subscribed` messages.

If NinjaTrader cannot resolve `##-##`, replace each entry in the AddOn's
`instruments` list with the exact active contract names displayed by your
platform.

## Safety and interpretation

- The dashboard is advisory and the starter score is deliberately simple; it
  proves transport, freshness detection, aggregation readiness, and ranking.
- A contract becomes `STALE` after 150 seconds without a completed bar.
- `WARMING` lasts until 45 completed bars arrive. The AddOn
  requests historical bars, but this first version emits live completed bars
  only, so startup warm-up is intentionally conservative. Python derives
  three-minute setup bars and 15-minute trend/support-resistance context.
- NinjaTrader must remain open and connected.
- Exchange data is kept on the same computer and is not redistributed.

## Health check

While the scanner runs:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```
