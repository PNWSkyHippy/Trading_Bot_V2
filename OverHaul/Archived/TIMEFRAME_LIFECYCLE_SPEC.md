# TIMEFRAME LIFECYCLE SPEC — Phase 4: Timeframe-Aware Trade Lifecycle

**Status:** Implemented  
**Date:** 2026-05-10  
**Affects:** strategy_engine.py · trade_executor.py · data/database.py · core/position_monitor.py  

---

## Problem Being Solved

Before Phase 4, every trade in the position monitor was managed on 5m bars — regardless of what timeframe generated the entry signal. A DCA Accumulator trade entered on a 1h signal was trailed using 5m structural stops. The two-bar stop would fire on every minor 5m high/low, not on meaningful 1h structural breaks. This was silent, untraceable, and incorrect.

Root cause: `position_monitor._get_bars()` hardcoded `timeframe="5Min"` for stocks and `timeframe="5m"` for crypto on every call, and the trade record had no `entry_timeframe` field to check anyway.

---

## How Entry Timeframe is Now Stored

### Signal generation — `strategy_engine.run_strategies_multi_tf()`

Each strategy declares its candle timeframe via `stock_candle_timeframe` / `crypto_candle_timeframe`. The scanner groups strategies by timeframe and builds a `bar_cache`. The engine already logged `tf=` in each signal line; it now also writes it into the signal's indicators dict:

```python
indicators = {**(trade_signal.metadata or {}), "timeframe": tf_key}
```

`tf_key` is the exact Alpaca/CCXT timeframe string the strategy used (e.g. `"1Hour"`, `"5Min"`, `"1h"`, `"5m"`).

### Trade record — `trade_executor.execute_signal()`

```python
"entry_timeframe": signal.indicators.get("timeframe", "5Min"),
```

`entry_timeframe` is written into the `trade_record` dict and persisted to the database.

### Database — `data/database.py`

New column added to the `trades` table:
```sql
entry_timeframe  TEXT DEFAULT '5Min'
```

Existing databases are migrated on startup via the existing safe-migration pattern:
```python
"ALTER TABLE trades ADD COLUMN entry_timeframe  TEXT    DEFAULT '5Min'",
```

`open_trade()` writes the field explicitly. `get_open_trades()` returns it via `SELECT *`.

---

## How the Monitor Uses Entry Timeframe

### Local variable at cycle start

At the top of the main trade check function, `entry_timeframe` is extracted once and reused:

```python
entry_timeframe = trade.get("entry_timeframe") or (
    "5Min" if asset_class == "stock" else "5m"
)
```

The fallback preserves previous behaviour for any trades opened before Phase 4.

### Log line

Every monitor cycle now logs the originating timeframe:

```
AAPL [1Hour]: price=$185.42 | SL=$183.10 | TP=$189.20 | P&L: +0.82% | Age: 1.4hr
BTC/USD [1h]: price=$62441.00 | SL=$61200.00 | TP=$65000.00 | P&L: +1.21% | Age: 0.8hr
```

This makes 1h trades immediately visible in logs and distinguishable from 5m trades.

### `_get_bars()` — new `timeframe=` parameter

```python
def _get_bars(self, symbol, asset_class, limit=25, timeframe=None):
    tf = timeframe or ("5Min" if asset_class == "stock" else "5m")
    ...
```

Callers that omit `timeframe` get the 5m overlay (unchanged behaviour). Callers that pass `timeframe=entry_timeframe` get entry-timeframe bars.

### Step 12: Trailing stop — uses `entry_timeframe`

```python
_trail_bars = self._get_bars(symbol, asset_class, limit=25, timeframe=entry_timeframe)
updates = risk_manager.calculate_trailing_stop(trade, current_price, bars=_trail_bars)
```

A 1h trade now trails on 1h bars. The two-bar structural stop advances only when a 1h bar makes a new 2-bar high/low — exactly as the backtest modelled it.

---

## Intentional Hybrid Design

Several exit checks remain on the 5m bar overlay regardless of entry timeframe. This is a deliberate design choice, not an oversight.

| Exit check | Bars used | Rationale |
|---|---|---|
| Early loss (20-min) | 5m | Confirms short-term momentum still adverse; 1h resolution is too coarse for a 20-min window |
| Pivot break (S1/R1) | 5m | Intraday structure check; 1h resolution misses intraday pivot breaks |
| VWAP cross (ORB) | 5m | VWAP is an intraday construct; only meaningful at 5m resolution |
| ADX/DI stale (3hr) | 5m | Short-term trend confirmation; 1h ADX lags too much for a 3hr stale check |
| Momentum score | 5m | Short-term momentum assessment; used for momentum rider extension |
| **Trailing stop (step 12)** | **entry_timeframe** | **Structural stop must match entry timeframe** |

The 5m overlay exits are valid monitoring signals for any position duration — they detect when the short-term environment has turned hostile, regardless of whether the entry was on a 5m or 1h signal. Mixing timeframes here is intentional: coarse entry timeframe + fine monitoring granularity is a common intraday risk management pattern.

If a future phase decides that 1h trades should skip the 20-min early loss check (since 20 minutes is sub-candle for a 1h strategy), that is a strategy policy change and belongs in Phase 6 (live exit representation), not Phase 4.

---

## Files Changed

| File | Change |
|---|---|
| `strategies/strategy_engine.py` | `run_strategies_multi_tf()` embeds `"timeframe": tf_key` into signal indicators |
| `core/trade_executor.py` | `execute_signal()` writes `"entry_timeframe"` into trade record |
| `data/database.py` | `trades` table: new `entry_timeframe TEXT DEFAULT '5Min'` column + safe migration + `open_trade()` updated |
| `core/position_monitor.py` | `_get_bars()` accepts `timeframe=` param; `entry_timeframe` extracted at cycle start; step 12 trailing stop fetches bars with `timeframe=entry_timeframe`; debug log includes `[entry_timeframe]` |

---

## Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | Every trade record has `entry_timeframe` in the DB | ✅ |
| 2 | Logs show each trade's originating timeframe on every monitor cycle | ✅ |
| 3 | 1h entries trail on 1h bars, not 5m bars | ✅ |
| 4 | Monitoring overlay exits (early loss, pivot, ADX, VWAP) remain on 5m — documented as hybrid | ✅ |
| 5 | Timeframe behaviour is deterministic and documented | ✅ |
| 6 | Existing trades (no `entry_timeframe` in DB) fall back to 5m — same as before Phase 4 | ✅ |
| 7 | No strategy thresholds changed | ✅ |

---

## Scope Boundaries

| Issue | Phase |
|---|---|
| Whether 1h trades should skip the 20-min early loss check (sub-candle window) | Phase 6 |
| Stale structural stop at execution (signal-to-fill gap) | Phase 7 / pre-live gate |
| ISSUE-19: startup reconciler Coinbase→Kraken | Phase 7 |
