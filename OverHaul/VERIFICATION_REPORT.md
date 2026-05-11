# VERIFICATION REPORT — trading_bot_v2 Parity Rebuild
**Date:** 2026-05-10  
**Covers:** Phases 1–5  
**Auditor:** Claude Code (Phase 6 — Read-Only Verification)  
**Source of truth:** Live code state as of this report; all claims grounded in `grep` evidence.

---

## The Central Question

> Can we honestly say the same strategy now runs under the same candle semantics and stop rules across backtest, paper, and live?

**Short answer:** Yes for candle semantics. Mostly yes for stop rules, with two documented residual gaps. No for trade lifecycle exits — live has eight exit pathways the backtester still never sees.

The system is materially more honest than before Phases 2–5. Results for backtested strategies are significantly more reliable. It is not yet at full parity.

---

## Issue-by-Issue Status

### ISSUE-01 — Same-Bar Two-Bar Stop Optimism
**Original class:** CORRECTNESS-CRITICAL  
**Status: ✅ FULLY FIXED**

**What was wrong:** `_check_exit_two_bar()` called `update_stop()` before `check_stop_hit()`. A single OHLCV bar could both advance the trailing stop AND be stopped out by the newly advanced level — physically impossible from OHLCV data. The backtest always assumed the most optimistic intrabar sequence.

**What changed:** Order swapped in `backtester._check_exit_two_bar()`. Stop is now checked against the **previous bar's** stop level. Only if the bar survives does the stop advance.

```python
# BEFORE (wrong — optimistic):
new_stop = two_bar_engine.update_stop(...)   # advance first
if two_bar_engine.check_stop_hit(...):       # then check (against new stop)

# AFTER (correct):
if two_bar_engine.check_stop_hit(...):       # check against old stop first
    return "stop_loss"
new_stop = two_bar_engine.update_stop(...)   # only advance if bar survived
```

**Residual:** None. The fix is complete and structurally correct.

---

### ISSUE-02 — Live Stop Model ≠ Backtest Stop Model
**Original class:** CORRECTNESS-CRITICAL  
**Status: ✅ FULLY FIXED**

**What was wrong:** Live/paper used percent trailing (`price × (1 − PCT)`), polled every 10 seconds. Backtest used two-bar structural (N-bar low/high, advances on new structural high). These are completely different models — the "winning" backtest stop was never the deployed stop.

**What changed:** Two-bar structural stop is now the single production model.
- `core/stop_engine.py` created as single source of truth
- `risk_manager.calculate_trailing_stop()` now accepts `bars=` parameter; uses `stop_engine.check_for_trail_update()` when bars are provided
- `position_monitor` step 12 now fetches bars and passes them
- `trade_executor` now uses `structural_stop_price` embedded in signal for initial stop
- Scanner embeds `structural_stop_price` via `stop_engine.initial_stop_from_tail()` on every signal

Percent trailing is retained only as a fallback when bars are unavailable, logged at WARNING level.

**Residual:** The initial structural stop is computed at signal time and not recomputed at fill time. If price moves adversely between signal and broker fill, the stop may be immediately hit. Documented in `STOP_ENGINE_SPEC.md` as a pre-live gate item.

---

### ISSUE-03 — Eight Live Exit Types Absent from Backtester
**Original class:** CORRECTNESS-CRITICAL  
**Status: ❌ NOT FIXED**

**What was wrong and remains wrong:**

| Live Exit | Backtester? |
|---|---|
| EOD close (15:45 ET) | ❌ Never modeled |
| Early loss exit (30-min, −0.5% + worsening) | ❌ Never modeled |
| Performance time stop 1 (2hr, <0.2%) | ❌ Never modeled |
| Performance time stop 2 (5hr, <1.0%) | ❌ Never modeled |
| Hard time stop (8hr regardless of profit) | ❌ Never modeled |
| Pivot point break (S1/R1) | ❌ Never modeled |
| Stale ADX/DI (3hr, ADX <25) | ❌ Never modeled |
| ORB VWAP cross exit | ❌ Never modeled |

The backtester exits on: stop loss, take profit, end-of-data. That is all. Any strategy whose live performance is shaped by time stops, ADX exits, or pivot breaks will produce inflated backtest results. A 1h swing trade that would be killed at 8 hours in live can run for days in backtest.

**Impact:** All comparisons between live and backtested 1h strategy performance must account for this gap. This is the largest remaining correctness-critical issue.

---

### ISSUE-04 — Symbol Cooldown Absent from Backtester
**Original class:** STRATEGY-QUALITY-CRITICAL  
**Status: ❌ NOT FIXED**

Live enforces a 10-minute cooldown after a loss and a 2-minute cooldown after a win on the same symbol. The backtester can re-enter 1 bar after a stop loss. On 5m bars this produces more re-entries per symbol than live would permit, potentially inflating trade counts and overstating exposure to momentum setups.

---

### ISSUE-05 — No Closed-Candle Contract in Scanner
**Original class:** CORRECTNESS-CRITICAL  
**Status: ✅ FULLY FIXED**

**What was wrong:** Both `StockScanner.get_bars()` and `CryptoScanner.get_ohlcv()` passed the currently-forming bar to strategy analysis. Live signals were evaluated on incomplete candles; backtests used yfinance historical (all closed). The same strategy fired on fundamentally different data.

**What changed** (Phase 2):
- `_strip_forming_bar()` strips the last bar when `now_utc < bar_start + timeframe_seconds`
- `get_bars()` and `get_ohlcv()` both fetch `limit+1` and strip before returning
- `_last_bar_evaluated` cache prevents re-evaluating the same closed bar across scan cycles

Both Alpaca (tz-aware UTC) and Kraken CCXT (ms-epoch naive UTC) timestamp formats handled.

**Residual:** None. Scanner and backtester now both operate exclusively on closed bars.

---

### ISSUE-06 — Entry at Signal Bar Close (Execution Lookahead)
**Original class:** REALISM-CRITICAL  
**Status: ❌ DOCUMENTED, NOT FIXED**

The backtester generates a signal at bar `i` close and enters at bar `i` close. In live trading, the signal fires at bar `i` close and the order fills at bar `i+1` open (which may gap). This is execution lookahead bias. It remains in the code and is documented in `BACKTEST_REALISM_NOTES.md` as a structural change deferred beyond Phase 5.

---

### ISSUE-07 — Standard Backtest Stop Fill at Close, Not Stop Price
**Original class:** REALISM-CRITICAL  
**Status: ✅ FULLY FIXED**

**What was wrong:** Standard mode stopped at `close` price even though the stop may have been touched intrabar at a much better level. Two-bar mode correctly filled at `trade["current_sl"]`.

**What changed** (Phase 3):
- `_check_exit_standard()` now takes `row: pd.Series` and checks `row["low"] <= sl` (long) / `row["high"] >= sl` (short) — intrabar accuracy
- `_close_trade()` now fills all stop-loss exits at `trade["current_sl"]` for both stop modes
- `_simulate()` passes `row` not `price` to `_check_exit_standard()`

---

### ISSUE-08 — Live Stop Polling vs Backtest Intrabar Logic
**Original class:** CORRECTNESS-CRITICAL  
**Status: ⚠️ PARTIALLY ADDRESSED**

**What was wrong:** Backtest detects stop hits using bar low/high (intrabar). Live detects them by comparing `current_price` to stop_loss every 10 seconds. If price briefly touches the stop and recovers between two polls, live misses the stop.

**What changed:** The trailing stop *advancement* mechanism is now closed-bar-based in both environments (structural model). The *hit detection* mechanism is unchanged:
- Backtest: intrabar `low <= stop` ✅
- Live: tick poll `current_price <= stop` ⚠️ — brief touches may be missed

**Residual:** The polling gap is inherent to live execution and cannot be eliminated without real-time order book access. This is an honest execution fidelity difference: live stops are slightly less reliable than backtested stops. The direction of error is conservative (live holds a position longer if the stop is only briefly touched). This asymmetry is not fixable at the application layer.

---

### ISSUE-09 — No Originating Timeframe Stored with Trade
**Original class:** CORRECTNESS-CRITICAL  
**Status: ✅ FULLY FIXED**

**What changed** (Phase 4):
- `entry_timeframe` column added to `trades` table in SQLite schema (with `ALTER TABLE` migration for existing DBs)
- `trade_executor.execute_signal()` writes `entry_timeframe` from `signal.indicators.get("timeframe", "5Min")`
- `strategy_engine.run_strategies_multi_tf()` injects `timeframe` into `ss.indicators` at signal time
- `position_monitor._process_position()` reads `entry_timeframe` from the trade record and logs it on every monitor cycle

---

### ISSUE-10 — Position Monitor Bars Hardcoded to 5-Minute
**Original class:** CORRECTNESS-CRITICAL  
**Status: ⚠️ PARTIALLY FIXED — intentional hybrid design for overlay checks**

**What changed** (Phase 4):
- `_get_bars()` now accepts a `timeframe` parameter
- **Trailing stop (step 12):** fetches bars at `entry_timeframe`. A 1h trade trails on 1h bars. A 5m trade trails on 5m bars. This is the structurally correct change — the two-bar structural stop was defined in terms of the entry timeframe's N-bar highs/lows.

**What remains on 5m (intentional):** All monitoring overlay checks continue to use 5m bars regardless of entry timeframe:

| Exit Check | Timeframe | Rationale |
|---|---|---|
| Early loss (30-min) | 5m | Checking short-term momentum continuation — 5m granularity required |
| Pivot point break | 5m | Intraday S1/R1 structure — 5m is appropriate resolution |
| ADX/DI stale (3hr) | 5m | Sensitivity requires fine-grained bars; 1h ADX lags too much |
| VWAP cross exit | 5m | VWAP is an intraday concept; 1h bars would miss the cross |
| Momentum scoring | 5m | Short-term momentum signal |

This is documented as **hybrid design** in `TIMEFRAME_LIFECYCLE_SPEC.md`: the structural exit (trailing stop) uses the entry timeframe; the monitoring overlays are intentionally timeframe-agnostic and use 5m bars for all trades. This is a deliberate design choice, not an oversight.

**Residual gap:** For 1h trades, the early loss check examines 3 consecutive 5m bars (15 minutes of data) to declare "still moving wrong." This is a coarse signal — it works as a momentum check but is not structurally derived from the entry timeframe. Acceptable for now.

---

### ISSUE-11 — Time Stops Not in Backtester; Stale 3.5hr Comments
**Original class:** CORRECTNESS-CRITICAL  
**Status: ❌ NOT FIXED**

Time stops are not modeled in the backtester (see ISSUE-03). Additionally, the stale comments confirmed still present in live code:

```python
# position_monitor.py line 354 (docstring):
# "After 3.5 hours: hard kill regardless of profit"

# line 373 (inline comment):
# "── Hard time stop: 3.5 hours ─────────────────"

# line 377 (logger):
# f"3.5hr max reached | P&L {pnl_pct:+.2f}% | closing"
```

The actual constant: `HARD_TIME_STOP_SEC = 8 * 60 * 60` (8 hours). These three stale references remain in the codebase. Anyone reading logs or code will believe they are seeing a 3.5-hour stop when it is an 8-hour stop.

The full docstring mismatch (ISSUE-16) also remains: every threshold in `_check_performance_time_stop()`'s docstring cites the old values (20min/−0.3%/1hr/0.5%/3hr/1.5%/3.5hr). The actual constants are 30min/−0.5%/2hr/0.2%/5hr/1.0%/8hr.

---

### ISSUE-12 — No Spread, Slippage, or Commission Model
**Original class:** REALISM-CRITICAL  
**Status: ✅ FULLY FIXED**

**What changed** (Phase 5):
- 4 constants added to `config.py`: `BT_COMMISSION_STOCK_PCT`, `BT_COMMISSION_CRYPTO_PCT`, `BT_SLIPPAGE_STOCK_PCT`, `BT_SLIPPAGE_CRYPTO_PCT`
- Round-trip cost `= position_value × (commission + slippage) / 100 × 2` deducted from PnL at every trade close
- Applied to both normal exits and `backtest_end` forced closes
- `BacktestTrade.fees` and `BacktestResult.fees_paid` track friction per-trade and in aggregate
- Report shows explicit FRICTION block with per-leg rates, round-trip rate, total fees paid, avg per trade
- `--no-fees` CLI flag produces zero-friction baseline for direct comparison

Default values: stocks 0.01% slippage (Alpaca commission-free); crypto 0.26% commission + 0.05% slippage = 0.31% per leg / 0.62% round-trip (Kraken standard taker).

---

### ISSUE-13 — Portfolio Summary Is Not a Portfolio Test
**Original class:** REALISM-CRITICAL  
**Status: ✅ FULLY FIXED**

`run_all()` still runs each symbol with full starting capital independently. `print_portfolio_summary()` now says so explicitly:

```
  ISOLATED SYMBOL RESULTS — 12 symbol(s)
  NOTE: Each symbol ran with full starting capital independently.
        This is NOT a shared-capital portfolio simulation.
        Averages below do not represent a real portfolio return.
```

The misleading "PORTFOLIO SUMMARY" heading is gone. The caveat appears on every invocation.

---

### ISSUE-14 — Entry at Bar i Close (Duplicate of ISSUE-06)
**Status: ❌ DOCUMENTED, NOT FIXED** — see ISSUE-06.

---

### ISSUE-15 — Hard Time Stop Comment Says 3.5hr, Code Says 8hr
**Status: ❌ NOT FIXED** — see ISSUE-11. Three stale references confirmed in live code.

---

### ISSUE-16 — _check_performance_time_stop Docstring Thresholds All Wrong
**Status: ❌ NOT FIXED** — see ISSUE-11. All seven threshold values in the docstring are stale.

---

### ISSUE-17 — CoinbaseExecutor Uses Kraken Internally
**Original class:** STRATEGY-QUALITY-CRITICAL  
**Status: ❌ NOT FIXED** — Phase 7 scope.

`CoinbaseExecutor` class name, docstring, and broker chain description all say Coinbase; the implementation uses `ccxt.kraken()` with Kraken credentials. Not in the critical execution path but creates real operational confusion.

---

### ISSUE-18 — Duplicate Symbol Cooldown Block
**Original class:** STRATEGY-QUALITY-CRITICAL  
**Status: ❌ NOT FIXED** — Phase 7 scope. The second identical block is dead code (first block returns on match). No behavioral impact but adds noise.

---

### ISSUE-19 — Startup Reconciler Queries Coinbase for Kraken Positions
**Original class:** CORRECTNESS-CRITICAL  
**Status: ❌ NOT FIXED** — Phase 7 scope.

On bot restart, `_reconcile_crypto()` queries `ccxt.coinbase()` with Coinbase credentials. All live crypto positions are on Kraken. Any Kraken position opened before a crash will not be found by the reconciler. High operational risk on live deployment.

---

## Summary Table

| Issue | Description | Status |
|---|---|---|
| ISSUE-01 | Same-bar two_bar stop optimism | ✅ Fixed |
| ISSUE-02 | Live stop model ≠ backtest model | ✅ Fixed |
| ISSUE-03 | 8 live exits absent from backtester | ❌ Open |
| ISSUE-04 | Symbol cooldown absent from backtester | ❌ Open |
| ISSUE-05 | No closed-candle contract in scanner | ✅ Fixed |
| ISSUE-06 | Entry at bar i close (execution lag) | ❌ Open (documented) |
| ISSUE-07 | Standard stop fill at close, not stop price | ✅ Fixed |
| ISSUE-08 | Live tick polling vs backtest intrabar | ⚠️ Improved (trail advancement); hit detection gap remains |
| ISSUE-09 | No entry_timeframe stored with trade | ✅ Fixed |
| ISSUE-10 | Monitor bars hardcoded to 5m | ⚠️ Improved (trailing stop fixed); overlays intentionally 5m |
| ISSUE-11 | Time stops not in backtester | ❌ Open |
| ISSUE-12 | No fees or slippage model | ✅ Fixed |
| ISSUE-13 | Portfolio summary mislabeled | ✅ Fixed |
| ISSUE-14 | Entry timing lag (same as ISSUE-06) | ❌ Open (documented) |
| ISSUE-15 | Hard stop comment says 3.5hr | ❌ Open |
| ISSUE-16 | Docstring thresholds all wrong | ❌ Open |
| ISSUE-17 | CoinbaseExecutor uses Kraken | ❌ Open (Phase 7) |
| ISSUE-18 | Duplicate cooldown block | ❌ Open (Phase 7) |
| ISSUE-19 | Reconciler queries wrong exchange | ❌ Open (Phase 7) |

**7 fully fixed · 2 improved with residual gaps · 10 open**

---

## Honest Assessment by Environment Pair

### Backtest ↔ Live/Paper: Candle Semantics
**Aligned? Yes.**  
Scanner strips forming bars (Phase 2). Backtester uses yfinance historical (always closed). Both environments now evaluate the same closed-bar signal data. The `_last_bar_evaluated` cache prevents the live scanner from re-firing on the same bar across polling cycles.

### Backtest ↔ Live/Paper: Stop Rules
**Aligned for advancement logic. Residual gap in hit detection.**  
The two-bar structural stop is now implemented identically in both environments: initial stop = N-bar structural low/high; trail triggers on new N-bar high/low on a closed bar; ratchets up only. This is the main correctness win of Phase 3.

The residual gap: backtest detects a stop hit using bar low/high (intrabar). Live detects it via tick poll every 10 seconds. A stop briefly touched and recovered between polls is missed live. This is an execution fidelity difference that favors the live system being slightly more lenient — trades may survive brief stop touches that backtesting would close.

### Backtest ↔ Live/Paper: Trade Lifecycle
**Not aligned. This is the largest remaining gap.**  
Live has eight exit pathways the backtester never models (time stops, ADX stale, pivot break, VWAP cross, early loss). A 1h swing strategy backtested for 365 days will show trades running 2–3 days; in live the same trade is killed at 8 hours. Any performance comparison between backtest and live for 1h strategies must treat this as a known bias.

### Backtest ↔ Live/Paper: Cost Model
**Now aligned in direction; live is still more costly than the model.**  
Backtester now deducts Kraken taker fees (0.26%) and an assumed 0.05% slippage per leg. Live Kraken fees vary by volume tier (standard 0.26%, higher tiers 0.10%–0.20%). The model uses the conservative standard tier. Real costs should be equal to or lower than the backtested friction. This is the correct direction.

### Backtest ↔ Live/Paper: Timeframe Handling
**Aligned for trailing stop. Hybrid for monitoring overlays.**  
The structural trailing stop now uses the entry timeframe bars in both environments. The five monitoring overlays (early loss, pivot, ADX, VWAP, momentum) use 5m bars in live and are absent in backtest. This is a documented hybrid design, not an accidental inconsistency.

---

## What Remains Before Live Deployment

The following gaps must be resolved before live capital allocation:

| Gap | Risk Level | Phase |
|---|---|---|
| ISSUE-03/11: Live exit types not in backtester | HIGH — backtest results are optimistic for any 1h strategy | Pending |
| ISSUE-06/14: Execution lag (bar i entry) | MEDIUM — systematic entry lookahead | Pending |
| ISSUE-19: Startup reconciler queries wrong exchange | HIGH — Kraken positions not verified on restart | Phase 7 |
| Stale structural stop at execution (Phase 3 known limitation) | MEDIUM — adverse fill may hit stop immediately | Phase 7 pre-live gate |
| ISSUE-15/16: Stale time stop comments | LOW — operational confusion in logs | Phase 7 |

---

## Terminal Summary

```
VERIFICATION REPORT — trading_bot_v2 — 2026-05-10
══════════════════════════════════════════════════════════════
  ISSUE-01  [✅ GREEN ] Same-bar two_bar stop optimism — FIXED
  ISSUE-02  [✅ GREEN ] Live stop model ≠ backtest model — FIXED
  ISSUE-03  [❌ RED   ] 8 live exits absent from backtester — OPEN
  ISSUE-04  [❌ RED   ] Symbol cooldown absent from backtester — OPEN
  ISSUE-05  [✅ GREEN ] No closed-candle contract in scanner — FIXED
  ISSUE-06  [❌ RED   ] Entry at bar i close (execution lag) — OPEN
  ISSUE-07  [✅ GREEN ] Standard stop fill at close price — FIXED
  ISSUE-08  [⚠️ YELLOW] Live tick poll vs backtest intrabar — IMPROVED
  ISSUE-09  [✅ GREEN ] No entry_timeframe in trade record — FIXED
  ISSUE-10  [⚠️ YELLOW] Monitor bars hardcoded to 5m — IMPROVED (hybrid)
  ISSUE-11  [❌ RED   ] Time stops not in backtester — OPEN
  ISSUE-12  [✅ GREEN ] No fee/slippage model — FIXED
  ISSUE-13  [✅ GREEN ] Portfolio summary mislabeled — FIXED
  ISSUE-14  [❌ RED   ] Entry timing lag (same as ISSUE-06) — OPEN
  ISSUE-15  [❌ RED   ] Hard stop comment says 3.5hr — OPEN
  ISSUE-16  [❌ RED   ] Docstring thresholds all wrong — OPEN
  ISSUE-17  [❌ RED   ] CoinbaseExecutor uses Kraken — OPEN (Phase 7)
  ISSUE-18  [❌ RED   ] Duplicate cooldown block — OPEN (Phase 7)
  ISSUE-19  [❌ RED   ] Reconciler queries wrong exchange — OPEN (Phase 7)
══════════════════════════════════════════════════════════════
  7 GREEN (fully fixed)
  2 YELLOW (improved, residual gaps documented)
  10 RED (open — 3 Phase 7 cleanup, 7 substantive)
══════════════════════════════════════════════════════════════

  CANDLE SEMANTICS:  ✅ ALIGNED — scanner + backtester both on closed bars
  STOP RULES:        ⚠️ MOSTLY ALIGNED — structural model consistent;
                        hit detection: backtest intrabar vs live tick poll
  TRADE LIFECYCLE:   ❌ NOT ALIGNED — 8 live exit types absent from backtest
  COST MODEL:        ✅ ALIGNED — friction model in place (conservative)
  TIMEFRAME:         ⚠️ HYBRID — trailing stop aligned; overlays intentionally 5m

══════════════════════════════════════════════════════════════
  READY FOR LIVE DEPLOYMENT? NO
  Blocking: ISSUE-03 (lifecycle exits), ISSUE-19 (reconciler)
  Conditional: ISSUE-06/14 (execution lag) acceptable for paper
══════════════════════════════════════════════════════════════
```
