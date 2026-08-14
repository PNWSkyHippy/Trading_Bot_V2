# NinjaTrader → Python Futures Scanner

This proof of concept is read-only. NinjaTrader sends completed one-minute bars
for the MES/ES, MNQ/NQ, MYM/YM, M2K/RTY, and MGC/GC families to a Python process
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
The bridge also sends a small authenticated heartbeat every 30 seconds. This
appears separately as `BRIDGE ALIVE`; it does not create synthetic bars or
change a stale market-data status.

After the receiver is running, the optional click-driven desktop frontend is:

```powershell
venv312\Scripts\python.exe ninjatrader_bridge\ninja_futures_gui.py
```

It shows all symbols and states on the left; selecting one fills the main
panel with its indicators, support/resistance, and per-contract plus
quantity-adjusted ATR risk. PREP and READY transitions flash, sound, and stay
latched in recent-alert history. It remains read-only and has no order controls.
The configured manual profit goal is displayed prominently. Raw ATR remains
visible as volatility context, but the generic ATR stop/2R dollar plan is not
shown because it is neither a forecast nor the user's ATM order preset.

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

- The dashboard is advisory and the original trend score remains visible in
  the `TREND`/`T-SCR` columns as the fast straight-up/straight-down trend
  signal. The separate confluence `STATE`/`SCORE` combines EMA 8/20, VWAP,
  ADX, RSI, MACD, ATR, choppiness, support/resistance, and 1m/3m/15m trend.
- Suggested ATR stop/target distances are shown in both points and dollars
  per contract. They are advisory calculations only.
- An audible alert fires only when a symbol transitions into `READY`, not on
  every two-second screen refresh. Terminal state labels are color-coded;
  both behaviors can be disabled under `signal_engine` in the JSON config.
- A contract becomes `STALE` after 150 seconds without a completed bar.
- The fast `TREND` signal begins after 45 completed bars. The strict
  confluence `STATE` waits for at least 105 one-minute bars so MACD, ADX, and
  six completed 15-minute buckets have real history. The AddOn sends up to 90
  historical bars at startup, so `TREND` works immediately while confluence
  normally spends about 15 additional minutes in `WARMING`.
- NinjaTrader must remain open and connected.
- Exchange data is kept on the same computer and is not redistributed.

## Health check

While the scanner runs:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

The response includes a `bridge` object with heartbeat age, subscription
count, and an `alive` flag. `alive` becomes false after 75 seconds without a
heartbeat, while each contract's bar freshness remains independently tracked.
