# Backtester Live-Parity Audit — Read Only

## Objective

Determine whether `intelligence/backtester.py` can faithfully reproduce the live
signal, entry, position-management, and exit lifecycle before Ron uses it to
calibrate Breakout Scanner restrictions or the break-even/profit ratchet.

This is an evidence-driven correctness and parity audit, not a request to optimize
parameters, maximize a historical equity curve, or edit production code.

## Current decision this audit must support

Breakout Scanner's repaired post-fix results are encouraging, but its average
winner/loser gap remains too narrow. Ron wants to loosen accumulated restrictions
incrementally and test delayed break-even/profit-ratchet activation without:

- allowing realized losses to exceed the intended dollar-risk envelope;
- clipping normal breakout retests and routine winners;
- destroying the occasional large right-tail breakout winner; or
- trusting results produced by a backtester that behaves differently from live code.

Do not recommend any ratchet threshold until live/backtest parity has been proved.

## Required repository scope

Use `intelligence/backtester.py` as the anchor, but trace every relevant caller and
dependency. At minimum inspect:

- `web_dashboard.py` backtest endpoints, payload parsing, strategy/symbol selection,
  progress, cancellation, and result serialization;
- `intelligence/optimizer.py`, `intelligence/opt_worker.py`, and any parameter-grid
  or subprocess boundary;
- `intelligence/candle_store.py` and all candle fetch/normalization paths used by
  backtests;
- strategy registration/discovery and parameter override routing;
- live counterparts in strategy generation, `breakout_sender.py`,
  `core/breakout_receiver.py`, `core/trade_executor.py`,
  `core/position_monitor.py`, `core/risk_manager.py`, and database trade fields;
- Breakout Scanner's actual signal/stop/target/ratchet fields and every shared layer
  that can replace, reinterpret, or preempt them;
- all scripts and dashboard tools that invoke the backtester or optimizer.

Discover additional files from imports and callers. Do not assume this list is
complete.

## Mandatory parity checks

### Data and time

- Completed-candle semantics and forming-bar exclusion at every timeframe.
- Timestamp timezone, session boundaries, extended-hours inclusion, DST, holidays,
  early closes, publication grace, missing bars, duplicate bars, and gaps.
- Cache hit, cache miss, incremental refresh, retention, and symbol/timeframe keying.
- No look-ahead through indicator windows, resampling, signal timestamps, fill
  selection, future support/resistance, or end-of-data liquidation.
- Same data convention for stocks and crypto where the live paths intentionally
  differ.

### Entry and fills

- Exact live signal predicates, condition ordering, defaults, configuration values,
  symbol normalization, long/short behavior, deduplication, cooldowns, and disabled
  strategy state.
- Entry on the same eligible candle and no same-bar knowledge unavailable live.
- Market/limit fill assumptions, next-bar versus signal-bar fills, gap behavior,
  spread, slippage, fees, rejected orders, partial fills, and quantity rounding.
- Position sizing and capital availability identical in units and meaning to live
  risk approval; no impossible capital reuse or overlapping-position behavior.

### Stops, targets, and lifecycle

- Strategy-owned absolute stop/target prices must not silently become percentages
  reapplied to a different fill unless live does exactly that.
- Intrabar ambiguity when stop and target are both touched: document the current
  ordering and require pessimistic/deterministic behavior or finer data. Never assume
  the favorable outcome without evidence.
- Gap-through-stop fills, stop slippage, broker-first versus monitor-first exits,
  partial exits, fees, and realized P&L.
- Exact parity for initial stop, structural stop, break-even activation, profit
  ratchet, trailing stop, time stop, early-loss guard, end-of-session close,
  overnight exemptions, operator exits, and any generic shared exit.
- Stop monotonicity: protection may tighten but must never loosen unless the live
  strategy explicitly and safely permits it.
- Exit precedence must match live behavior when multiple conditions are true.

### Breakout-specific experiment readiness

- Verify the backtester can record per trade: signal time, fill time/price, initial
  and final stop, every stop mutation with reason/time, target, exit reason, exit
  price, holding time, fees, slippage, MFE, MAE, and profit given back from MFE.
- Determine whether current outputs are sufficient to compare immediate break-even
  against delayed activation such as fractions of R, ATR/structure confirmation, or
  completed-bar follow-through while changing exactly one variable.
- Require a baseline-versus-candidate experiment design that preserves the initial
  hard protective stop and all broker/reconciliation/circuit-breaker protections.
- Require parameter plateaus and pessimistic friction tests, not a single optimized
  peak. Include out-of-sample or walk-forward separation.

### Known symptoms to reproduce

- Dashboard request with strategy `bmr_357`, asset type crypto, symbol `all`,
  timeframe 1h, and 30 days reportedly returned only BTC/USD. Trace whether `all`
  genuinely runs the intended universe and whether combined results are complete.
- Some strategies are or were absent from dashboard/backtester/optimizer lists even
  though present in strategy code or DB tools. Verify registry parity and parameter
  override support for every exposed strategy.
- Confirm cancellation/progress state cannot leak between concurrent or subsequent
  runs.
- Confirm the backtester does not use live database state, mutate the live database,
  alter strategy enablement, or depend on current open positions during tests.

## Proof standard

Do not accept comments, matching function names, or approximate intent as parity.
Trace executed branches and data shapes. Recompute formulas. Use read-only database
queries only when necessary, never expose credentials, and never modify the live DB.

Select several known closed paper trades if safely available and specify a deterministic
replay fixture that compares the live record against the backtester event by event:

1. signal timestamp and direction;
2. fill timestamp, price, and quantity;
3. initial stop/target;
4. every lifecycle transition;
5. final exit reason, price, fees, and P&L.

State clearly which parity claims can be proved now, which require new instrumentation,
and which cannot be reconstructed from existing records.

## Patch coordination constraint

Patch A is approved and Patch B market-data/cache work is pending. There are also
uncommitted candle-store retention changes in the working tree. This audit must be
read-only. Do not edit, stage, commit, push, revert, clean, or overwrite anything.
Identify proposed patch boundaries that minimize overlap with the pending Patch B work,
and explicitly flag any unavoidable overlap in `intelligence/candle_store.py` or related
market-data files.

## Required report conclusion

End with:

1. A verdict: `PARITY PROVED`, `PARITY NOT PROVED`, or `PARITY FAILED`.
2. A prioritized defect list separating confirmed defects from speculative concerns.
3. A live-versus-backtest behavior matrix for entry, fills, sizing, stops, ratchets,
   exits, fees, and data timing.
4. The minimum deterministic test suite required before any parameter sweep.
5. A safe patch sequence grouped by files that can share a patch.
6. A separately identified future experiment matrix for Breakout ratchet activation;
   do not present its results as known before parity fixes and validation exist.

