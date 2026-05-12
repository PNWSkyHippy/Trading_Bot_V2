# CLAUDE CODE — MAIN 8A
**Focus:** Historical data guardrails for backtests  
**Priority:** HIGH  
**Goal:** Prevent corrupted OHLCV data from poisoning results

---

## Context

Recent crypto backtests exposed at least one symbol with clearly corrupted yfinance history
(example pattern: normal price -> near-zero print -> normal price again within a few bars).
This creates fake returns, nonsense ADX/ATR behavior, and invalid strategy conclusions.

The backtester must prefer **rejecting bad symbol data** over silently producing garbage results.

---

## Scope

Primary file:
- `intelligence/backtester.py`

Optional only if truly needed:
- `config.py`

Do **not** modify strategy logic in this pass.

---

## Required changes

### 1. Add OHLCV validation before simulation
Create a helper in `backtester.py` and run it inside both:
- `fetch_history()`
- `fetch_history_crypto()`

Validation should check at minimum:

- required columns exist: `open high low close volume`
- dataframe not empty after cleanup
- no duplicate timestamps
- no NaN / inf in OHLC
- no non-positive `open/high/low/close`
- candle integrity:
  - `high >= max(open, close, low)`
  - `low <= min(open, close, high)`

### 2. Add corruption heuristics for absurd intraday prints
We specifically want to catch symbols like corrupted TON/TAO-style feeds.

Implement a conservative reject rule for intraday data (`5m`, `1h`) such as:

- reject if there are extreme one-bar close-to-close jumps that are not plausible for the asset/timeframe
- reject if there is a collapse-and-immediate-reversion pattern across a tiny number of bars
- reject if bad bars are repeated, not just one isolated row

You may choose exact thresholds, but keep them conservative and explain them in code comments.
The purpose is to catch obvious garbage, not normal volatility.

### 3. Prefer reject over repair
Allowed:
- dropping duplicate timestamps
- dropping rows with NaN if tiny and clearly malformed

Not allowed:
- inventing prices
- interpolating OHLC
- silently “fixing” severe corruption

If the data is suspicious beyond trivial cleanup:
- log a clear `[DATA QUALITY FAIL]` message
- return `None`
- skip the symbol

### 4. Make the skip reason visible
When a symbol is rejected for data quality:
- log the symbol
- log the reason
- log the timeframe and date span if useful

If practical without invasive changes, also show a short skipped-symbol note in the run-all summary.
If that requires bigger architecture churn, logging alone is acceptable.

### 5. Keep behavior unchanged for valid symbols
Do not change:
- signal thresholds
- stop logic
- fees/slippage
- entry timing
- strategy scoring

This pass is about **data trustworthiness only**.

---

## Hard rules

- Prefer false-negative (skip questionable symbol) over false-positive (backtest garbage)
- No strategy parameter tuning
- No indicator math changes
- No “repair” logic beyond trivial cleanup
- Keep stock and crypto validation paths consistent where possible

---

## Deliverables

1. Summary of what changed
2. Files changed
3. Any config additions (only if truly necessary)
4. Exact verification commands
5. Example of a clear reject log message
6. Short issue table:
   - corrupted data reject path
   - trivial cleanup path
   - valid symbol pass path

---

## Verification commands

### Syntax
```bash
python -m py_compile intelligence/backtester.py && echo OK
Valid stock should still run
python intelligence/backtester.py --symbol AAPL --strategy adaptive_regime --days 365 --tf 1h --asset-class stock
Valid crypto should still run
python intelligence/backtester.py --symbol BTC/USD --strategy adaptive_regime --days 365 --tf 1h --asset-class crypto
Suspect crypto symbol should reject cleanly if feed is still bad
python intelligence/backtester.py --symbol TON/USD --strategy adaptive_regime --days 365 --tf 1h --asset-class crypto
If TON/USD is no longer reproducibly bad, use the historically bad symbol currently showing corrupted data in logs.

Run-all should skip bad symbols, not crash
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class crypto
Acceptance criteria
Corrupted OHLCV does not enter _simulate()
Backtests do not produce nonsense results from broken data feeds
Valid symbols still run unchanged
Reject messages are explicit and grep-friendly