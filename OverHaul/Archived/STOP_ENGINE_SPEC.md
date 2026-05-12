# STOP ENGINE SPEC — Phase 3: Unified Stop Engine

**Status:** Implemented  
**Date:** 2026-05-10  
**Affects:** backtester.py · risk_manager.py · position_monitor.py · market_scanner.py · trade_executor.py  
**New file:** core/stop_engine.py

---

## Production Stop Model

**Two-bar structural trailing stop** — identical contract across backtest, paper, and live.

### Algorithm

| Event | Action |
|---|---|
| Trade entry | Initial stop = lowest low (long) / highest high (short) of prior N closed bars |
| Each new closed bar | If bar makes new N-bar high (long) / N-bar low (short) → trail triggered |
| Trail triggered | New stop = min(prior N lows) for long / max(prior N highs) for short |
| Ratchet rule | Stop advances only in profit direction; never retracts |
| Stop hit check | Long: intrabar low ≤ stop · Short: intrabar high ≥ stop |

Default N = 2 (configurable via `TwoBarStopEngine(lookback=N)`).

---

## Bugs Fixed

### 1. Same-Bar Stop Optimism (ISSUE-02 — Critical)

**File:** `intelligence/backtester.py` — `_check_exit_two_bar()`

**Before (wrong):**
```python
# update_stop was called FIRST — allowed a single OHLCV bar to both:
#   (a) advance the trailing stop, and
#   (b) be stopped out at the newly advanced level
# This is physically impossible from OHLCV data alone.
new_stop = two_bar_engine.update_stop(df, bar_idx, trade["current_sl"], direction)
if new_stop != trade["current_sl"]:
    trade["current_sl"] = new_stop
if two_bar_engine.check_stop_hit(df, bar_idx, trade["current_sl"], direction):
    return "stop_loss"
```

**After (correct):**
```python
# Check uses the stop from the PREVIOUS bar.
# Only if the bar survives does the stop advance.
if two_bar_engine.check_stop_hit(df, bar_idx, trade["current_sl"], direction):
    return "stop_loss"
new_stop = two_bar_engine.update_stop(df, bar_idx, trade["current_sl"], direction)
if new_stop != trade["current_sl"]:
    trade["current_sl"] = new_stop
```

### 2. Standard Mode Close-Price Stop Check (ISSUE-02 — High)

**File:** `intelligence/backtester.py` — `_check_exit_standard()`

**Before:** Stop compared to `close` price — misses intrabar wicks that touched the stop.  
**After:** Stop compared to `row["low"]` (long) / `row["high"]` (short) — intrabar accuracy.

Signature changed from `(trade, price: float, ...)` to `(trade, row: pd.Series, ...)`.  
The `_simulate()` loop updated to pass `row` instead of `price`.

### 3. Stop Loss Fill Price (ISSUE-02 — High)

**File:** `intelligence/backtester.py` — `_close_trade()`

**Before:** Standard mode stop losses filled at `close` price (bar close, not stop level).  
**After:** All stop loss exits fill at `trade["current_sl"]` (the actual stop price).  
Previously only `STOP_TWO_BAR` mode had this correct behaviour; now both modes use it.

### 4. Live Stop Model Mismatch (ISSUE-01 — Critical)

**Before:** `risk_manager.calculate_trailing_stop()` used percent-trailing (`price × (1 − PCT)`), polled every 10 seconds. This never matched the two-bar structural model in the backtester.

**After:** `calculate_trailing_stop()` accepts `bars=` parameter. When bars are provided (≥ 3 closed bars), the two-bar structural model is applied via `stop_engine.check_for_trail_update()`. Percent trailing is retained as a fallback and logged at WARNING level so the mismatch is detectable.

---

## New File: `core/stop_engine.py`

Single source of truth for stop logic. Never duplicated across modules.

```
TwoBarStopEngine
  .initial_stop(df, entry_idx, direction)          → backtest entry
  .initial_stop_from_tail(bars, direction)          → live/paper entry
  .check_for_trail_update(bars, current_stop, dir)  → (triggered, new_stop)
  .is_stop_hit_intrabar(df, bar_idx, stop, dir)     → bool  (backtest)
  .is_stop_hit_price(current_price, stop, dir)      → bool  (live/paper)

stop_engine = TwoBarStopEngine(lookback=2)          # module singleton
```

---

## Component Changes

### `core/stop_engine.py` (new)
- All stop logic lives here; imported by risk_manager and scanner

### `intelligence/backtester.py`
- `_check_exit_two_bar()`: check before update (same-bar bug fixed)
- `_check_exit_standard()`: signature takes `row: pd.Series`; uses intrabar low/high
- `_close_trade()`: stop loss fills at stop price for both modes
- `_simulate()`: passes `row` to `_check_exit_standard()`

### `core/risk_manager.py`
- `calculate_trailing_stop()`: new `bars=None` parameter; two-bar structural when bars provided; percent trailing fallback logged as WARNING

### `core/position_monitor.py`
- Step 12: fetches `limit=25` bars via `_get_bars()` and passes to `calculate_trailing_stop(bars=...)`

### `scanners/market_scanner.py`
- Imports `stop_engine` from `core.stop_engine`
- After each strategy signal: embeds `signal.indicators["structural_stop_price"]` via `stop_engine.initial_stop_from_tail()`
- Applied to both stock and crypto scan loops

### `core/trade_executor.py`
- `execute_signal()`: reads `structural_stop_price` from signal indicators; uses it as initial stop when present; falls back to percent-based only when absent

---

## Data Flow After Phase 3

```
Scanner fetches N+1 closed bars
    ↓
Forming bar stripped (Phase 2)
    ↓
Strategy engine evaluates → signal with direction + indicators
    ↓
stop_engine.initial_stop_from_tail() → structural_stop_price embedded in indicators
    ↓
TradeExecutor: stop_loss = structural_stop_price (not entry × pct)
    ↓
Position open; stop in DB trade record
    ↓
PositionMonitor every 10s:
    fetches 25 closed bars
    risk_manager.calculate_trailing_stop(bars=bars)
        → stop_engine.check_for_trail_update()
        → stop ratchets only on new N-bar high/low on a CLOSED bar
    ↓
Backtester: identical algorithm via TwoBarStop (check before update)
```

---

## Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | `stop_engine.py` exists; no stop logic duplicated elsewhere | ✅ |
| 2 | `_check_exit_two_bar()`: check precedes update on every bar | ✅ |
| 3 | `_check_exit_standard()`: uses intrabar low/high, not close | ✅ |
| 4 | Stop loss fills at stop price, not close price | ✅ |
| 5 | `calculate_trailing_stop()` accepts `bars`; structural when provided | ✅ |
| 6 | `position_monitor` passes bars to trailing stop | ✅ |
| 7 | `structural_stop_price` embedded in signal by scanner | ✅ |
| 8 | `trade_executor` uses structural stop when available | ✅ |
| 9 | Percent trailing fallback logged at WARNING | ✅ |

---

## Known Limitation: Stale Structural Stop at Execution

**`structural_stop_price` is computed at signal generation time and is not recalculated at execution.**

`trade_executor.execute_signal()` reads the value from `signal.indicators` — the dict frozen when the scanner produced the signal. The executor correctly uses the actual broker fill price for `entry_price` and `take_profit`, but the structural stop is never refreshed to reflect any price movement that occurred during the signal-to-fill gap (reviewer pipeline → `approve_trade()` → broker submission → fill confirmation).

**Why two-bar structural stops are more vulnerable than percent stops:**  
A percent stop automatically scales to the fill price. A structural stop is an absolute price level (the N-bar low/high at signal time). If the fill price differs from `signal.current_price`, the stop's risk distance is wrong — no automatic adjustment occurs.

**Failure modes:**
- Fill higher than signal price (long, favorable): stop is now further below entry than modelled. Conservatively wide, not dangerous.
- Fill lower than signal price (long, adverse): stop may be at or above the fill price → immediate stop-out on the first monitor cycle.

**Severity:** Low for paper trading (fills are near-instantaneous). **Must be resolved before live deployment.**

**Proposed fix (Phase 7 or pre-live gate):** In `trade_executor.execute_signal()`, after obtaining `entry_price` from the broker fill, fetch fresh bars and call `stop_engine.initial_stop_from_tail()` to recompute the structural stop against the actual fill price. Guard against the immediate-stop-out case with a minimum distance check.

---

## Scope Boundaries

These issues are explicitly **out of scope for Phase 3** and deferred:

| Issue | Phase |
|---|---|
| ISSUE-10: position monitor hardcodes 5Min timeframe | Phase 4 |
| ISSUE-06/14: entry execution lag (signal+fill both at bar i close) | Phase 5 |
| ISSUE-12: no fees or slippage model in backtester | Phase 5 |
| Stale structural stop at execution (see Known Limitation above) | Phase 7 / pre-live gate |
| ISSUE-19: startup reconciler uses Coinbase instead of Kraken | Phase 7 |
| Percent trailing is still used when bars are unavailable | Phase 4 (timeframe fix will improve bar availability) |
