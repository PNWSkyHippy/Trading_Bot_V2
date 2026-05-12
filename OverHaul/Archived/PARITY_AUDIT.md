# PARITY AUDIT — trading_bot_v2
**Date:** 2026-05-09  
**Auditor:** Claude Code (Phase 1 — Read-Only)  
**Scope:** `intelligence/backtester.py`, `core/position_monitor.py`, `core/risk_manager.py`, `scanners/market_scanner.py`, `core/trade_executor.py`, `core/broker_manager.py`, `core/startup_reconciler.py`  
**No code was modified during this audit.**

---

## Classification Key

- **CORRECTNESS-CRITICAL** — The system is producing results that are factually wrong. Backtest and live behavior differ in ways that invalidate performance comparisons.
- **REALISM-CRITICAL** — The simulation is systematically optimistic. Results would degrade in a more realistic model.
- **STRATEGY-QUALITY-CRITICAL** — The implementation contradicts the stated or documented intent, or creates silent drift between environments.

**Proven** = directly observed in code with file:line evidence.  
**Inferred** = structurally likely but requires runtime observation to fully confirm.

---

## Section 1 — Backtest vs Live Mismatches

### ISSUE-01 — Same-Bar Two-Bar Stop Update Then Hit
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `intelligence/backtester.py` — `_check_exit_two_bar()`

```python
# Step 1: Advance trailing stop if triggered
new_stop = two_bar_engine.update_stop(df, bar_idx, trade["current_sl"], direction)
if new_stop != trade["current_sl"]:
    trade["current_sl"] = new_stop

# Step 2: Check if stop hit intrabar
if two_bar_engine.check_stop_hit(df, bar_idx, trade["current_sl"], direction):
    return "stop_loss"
```

Inside `update_stop()`, the trail trigger uses `current_bar["high"]` to detect a new N-bar high, then sets the new stop from `prior_window["low"].min()`. The updated stop is then immediately checked against the **same bar's** low.

This means: a bar that both (a) makes a new N-bar high triggering a trail advance, AND (b) has a low below the newly advanced stop, is treated as "stop advanced, then hit on same bar." OHLCV data reveals no intrabar sequence. The high could have occurred before the low (trail → hit) or the low could have occurred before the high (stop hit first, at old level, then bar continued higher). The backtester always assumes the most optimistic scenario: trail first, then check — which means it keeps the trade alive longer (old stop not hit) then exits at the new higher stop. This systematically overstates stop quality.

**The correct behavior:** a stop updated from bar `i` should only become active at bar `i+1`. The same bar that triggers the trail should not also be able to hit the updated stop.

---

### ISSUE-02 — Live Stop Model ≠ Backtest Two-Bar Stop Model
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**Files:** `core/risk_manager.py:calculate_trailing_stop()`, `intelligence/backtester.py:TwoBarStop`

**Live/paper (risk_manager.py):**
```python
def calculate_trailing_stop(self, trade, current_price):
    trailing_gap = config.TRAILING_STOP_PCT / 100
    new_sl = current_price * (1 - trailing_gap)   # percent from current price
    if new_sl > current_sl:
        updates["stop_loss"] = round(new_sl, 4)
```

**Backtest two_bar mode:**
```python
# Stop set at: lowest low of prior N bars (structural)
# Advances when: current bar high > N-bar highest high
# New stop: lowest low of prior N bars at that moment
```

These are completely different models:
| Property | Live (risk_manager) | Backtest two_bar |
|---|---|---|
| Initial stop | Entry × (1 − SL%) | Lowest low of N prior bars |
| Trail trigger | Every poll cycle if price is higher | Only when new N-bar high made |
| New stop level | Current price × (1 − TRAIL%) | Lowest low of N prior bars |
| Activation | Next polling interval | Claimed same bar (see ISSUE-01) |

The backtester's `STOP_STANDARD` mode is closer to live — both use a percentage trailing. However, standard backtester mode trails on **every bar close**, while live trails on **every polling cycle** (every 10 seconds via `position_monitor`). These produce different stop advancement cadences for multi-hour trades.

The two_bar mode is described as the structural stop that "won" backtests. It is not the model being traded.

---

### ISSUE-03 — Eight Live Exit Types Absent from Backtester
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `core/position_monitor.py`

The position monitor fires the following exits that have **no equivalent in backtester.py**:

| Live Exit | Trigger | Represented in Backtester? |
|---|---|---|
| EOD close | 15:45 ET | ❌ No |
| Early loss exit | 30-min window, pnl < −0.5% AND still moving wrong | ❌ No |
| Performance time stop 1 | 2hr open, pnl < 0.2% | ❌ No |
| Performance time stop 2 | 5hr open, pnl < 1.0% | ❌ No |
| Hard time stop | 8hr open regardless of profit | ❌ No |
| Pivot point break | Long breaks S1 / Short breaks R1 | ❌ No |
| Stale ADX/DI exit | 3hr open, ADX < 25 or DI crossover | ❌ No |
| ORB VWAP cross exit | Price crosses VWAP against position | ❌ No |
| Momentum rider (TP extension) | TP hit + momentum score ≥ 0.67 | ❌ No |
| Broker reconciliation close | Position gone from exchange | ❌ No |

Backtester exits:
- Standard/two_bar stop loss
- Fixed take profit
- End-of-data close
- Daily PnL halt

The live trade lifecycle has **10 exit pathways** the backtester never sees. Any strategy whose win rate depends on time stops, ADX exits, or pivot breaks will produce inflated backtest results because those same exits cannot trim losing or stagnant trades during backtesting.

---

### ISSUE-04 — Live Symbol Cooldown Absent from Backtester
**Class:** STRATEGY-QUALITY-CRITICAL | **Status:** Proven  
**File:** `core/risk_manager.py:approve_trade()`

Live enforces:
- 10-minute cooldown after a loss on a symbol
- 2-minute cooldown after a win on a symbol

Backtester only checks if already in the same direction on the symbol (`already_in` guard). There is no cooldown after a position closes. This means the backtester can re-enter a symbol 1 bar after a stop loss. A 5-minute backtester operating over 60 days will make many more trades per symbol than the live bot — producing higher trade counts and potentially inflated win rates from "revenge" setups that live would skip.

---

## Section 2 — Candle Integrity Issues

### ISSUE-05 — No Closed-Candle Contract in Scanner
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `scanners/market_scanner.py` — `StockScanner.get_bars()`, `CryptoScanner.get_ohlcv()`

Both scanner methods fetch bars and pass the result directly to strategy analysis:

```python
bars = self.get_bars(symbol, tf, limit)         # StockScanner
bars = self.get_ohlcv(symbol, tf, limit)        # CryptoScanner
```

Neither method checks whether the last returned bar is complete. Both Alpaca's bar endpoint and Kraken's `fetch_ohlcv()` include the **currently forming bar** as the last element. Strategies receive this bar and compute indicators including its close, high, and low — all of which may change before the bar closes.

For crypto scanning (every 5 minutes on 1h candles): the same forming 1h candle is re-evaluated up to 12 times before it closes. Each re-evaluation can produce different indicator readings from the same candle as intrabar price moves. This violates Principle 2 from the brief.

For stocks (scanning every 60 seconds on 1h candles): same issue — 60 re-evaluations of the same forming hourly candle.

Backtests use `yfinance`, which returns **historical closed bars only**. The signal logic has never been validated against the live behavior of operating on partially-formed candles.

---

### ISSUE-06 — Backtester Includes Current Bar in Signal Window
**Class:** REALISM-CRITICAL | **Status:** Proven  
**File:** `intelligence/backtester.py:_simulate()`

```python
window = df.iloc[max(0, i - 120): i + 1].copy()   # includes bar i (current)
signal = strategy_obj.analyze(symbol, window, "unknown")
```

```python
entry_price = price   # price = float(row["close"]) = bar i's close
```

Signal is generated using the close of bar `i`, and entry is also at bar `i`'s close. In real trading, you observe the close of bar `i` and can only enter at bar `i+1`'s open — which may gap. This is **execution lookahead bias**: the backtest assumes perfect knowledge of the closing price at the moment of entry.

For 1h candles this can be a meaningful gap. For 5m candles on volatile crypto, even small gaps compound across hundreds of trades.

---

## Section 3 — Stop-Loss and Trailing-Stop Mismatches

### ISSUE-07 — Standard Backtest Stop Fill at Close Price, Not Stop Price
**Class:** REALISM-CRITICAL | **Status:** Proven  
**File:** `intelligence/backtester.py:_check_exit_standard()`, `_close_trade()`

In standard mode:
```python
if price <= sl:              # price = bar close
    return "stop_loss"
...
# In _close_trade:
if reason == "stop_loss" and stop_mode == STOP_TWO_BAR:
    exit_price = trade["current_sl"]   # uses stop price for two_bar
else:
    exit_price = price                 # uses CLOSE PRICE for standard mode
```

In standard mode, a stop loss fills at the **bar close price**, even if the stop level was breached midbar. If the bar opened above the stop and the close was well below it, the fill is at the close — which is typically worse than the stop price. If the bar gapped below the stop, the fill is also at close, not the gap price. This produces inconsistent fill assumptions that neither model real market behavior accurately.

Two-bar mode correctly fills at the stop price (`trade["current_sl"]`). Standard mode should do the same.

---

### ISSUE-08 — Live Stop Polling vs Backtest Intrabar Logic
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**Files:** `core/position_monitor.py:_process_position()`, `intelligence/backtester.py:check_stop_hit()`

Live stop check (position monitor runs every 10 seconds):
```python
sl_exit = risk_manager.check_sl_exit(trade, current_price)
# check_sl_exit: if current_price <= sl: return "stop_loss"
```
`current_price` is fetched via ticker — a single price snapshot.

Backtest two_bar stop check:
```python
def check_stop_hit(self, df, bar_idx, stop_price, direction):
    bar = df.iloc[bar_idx]
    if direction == "long":
        return float(bar["low"]) <= stop_price   # bar low (intrabar)
```

The backtest uses the bar's low to detect if the stop was hit intrabar (correct). Live uses the most recently polled price. If the market briefly touches the stop and recovers between two 10-second polls, the live bot **misses the stop**. This is a legitimate difference in execution fidelity that makes live stops less reliable than backtested stops — in the opposite direction from optimism (live can hold a losing trade longer if the stop is only briefly touched).

---

## Section 4 — Timeframe Lifecycle Mismatches

### ISSUE-09 — No Originating Timeframe Stored with Trade
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `core/trade_executor.py:execute_signal()`

```python
trade_record = {
    "trade_id":       trade_id,
    "symbol":         signal.symbol,
    "asset_class":    signal.asset_class,
    "direction":      signal.direction,
    "entry_time":     datetime.now().isoformat(),
    "entry_price":    round(entry_price, 6),
    "quantity":       approval.quantity,
    "strategy_name":  signal.indicators.get("strategy_name", "original"),
    # ... no entry_timeframe field
}
```

The originating strategy timeframe is never stored. The signal carries the timeframe through `strategy.stock_candle_timeframe` or `strategy.crypto_candle_timeframe` attributes, but this is not captured in the trade record. The position monitor has no way to retrieve this information.

---

### ISSUE-10 — All Position Monitor Bars Hardcoded to 5-Minute
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `core/position_monitor.py:_get_bars()`

```python
def _get_bars(self, symbol, asset_class, limit=25):
    sc = self._get_scanner()
    if asset_class == "stock":
        return sc.stock_scanner.get_bars(symbol, timeframe="5Min", limit=limit)
    else:
        return sc.crypto_scanner.get_ohlcv(symbol, timeframe="5m", limit=limit)
```

Every exit check in the position monitor uses 5-minute bars, regardless of the originating trade timeframe:

| Exit Check | Uses | Problem |
|---|---|---|
| `_check_early_loss()` | 5m bars, 3-bar consecutive move | 1h trade: 3 bars = 15 minutes, not meaningful |
| `_check_pivot_break()` | 5m bars, 20-bar lookback (100min) | 1h trade: pivot from 100min window ≠ daily structure |
| `_check_stale_position()` | 5m bars, 50-bar ADX | 1h trade: ADX from ~4hr of 5m data |
| `_score_momentum()` | 5m bars, 25-bar window | 1h trade: momentum from 2hr of 5m data |
| `_check_vwap_cross_exit()` | 5m bars, 50-bar VWAP | 1h trade: VWAP resets intraday |

Without ISSUE-09 being fixed (timeframe stored in trade), this cannot be corrected. Both issues must be resolved together.

---

## Section 5 — Extra Live Exits Not in Backtester

See ISSUE-03 above for the full table. Expanding on the most impactful:

### ISSUE-11 — Time-Based Exits Cannot Be Compared Across Environments
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `core/position_monitor.py`

Time-based exits represent a **completely different trade management philosophy** that is not represented in the backtester:

- 2-hour check: close if profit < 0.2% (kills "going nowhere" trades)
- 5-hour check: close if profit < 1.0%
- 8-hour hard stop: close everything

A backtested swing trade on 1h bars that holds for 12 bars (12 hours) would be cut at the 8-hour mark in live. The backtest shows this trade as potentially exiting at take profit or stop. Live would kill it at 8 hours regardless. This makes 1h strategy live performance categorically incomparable to backtested performance.

**The 8-hour hard stop also conflicts with the comment/log message:**
```python
HARD_TIME_STOP_SEC = 8 * 60 * 60   # correctly 8 hours in constant

# But the internal comment and logger say:
# "Hard time stop: 3.5 hours"
# logger: "3.5hr max reached"
```
The constant is 8 hours. The comment and log message say 3.5 hours. This is a documentation bug that will cause operational confusion.

---

## Section 6 — Execution Realism Issues

### ISSUE-12 — No Spread, Slippage, or Commission Model
**Class:** REALISM-CRITICAL | **Status:** Proven  
**File:** `intelligence/backtester.py`

The backtester has zero friction modeling:
- No bid/ask spread applied to entry or exit prices
- No slippage on market orders
- No commission per trade

For intraday crypto strategies on 5m bars this is especially problematic. Kraken charges ~0.2% maker / 0.26% taker per trade. A round trip costs ~0.4–0.52% in fees alone. Strategies showing a 0.3% average win are **net losers** in reality. No backtest result for a crypto strategy can be trusted without fee modeling.

For stocks on 5m bars, Alpaca charges $0 commission but has spread and slippage on market orders. Bracket orders may fill at different prices than assumed.

---

### ISSUE-13 — Portfolio Summary Is Not a Portfolio Test
**Class:** REALISM-CRITICAL | **Status:** Proven  
**File:** `intelligence/backtester.py:run_all()`, `print_portfolio_summary()`

`run_all()` runs each symbol in isolation with the full `starting_capital`:
```python
for sym in symbols:
    r = self.run(sym, days, starting_capital, ...)
```

`print_portfolio_summary()` then aggregates and labels the result "PORTFOLIO SUMMARY." This is **not** a portfolio test. It is N independent per-symbol tests, each with full capital, summed post-hoc. Implications:

- Capital contention not modeled (5 simultaneous positions each with 100% capital = 500% theoretical allocation)
- No shared drawdown across concurrent positions
- Correlation and regime exposure not modeled
- "PORTFOLIO SUMMARY" heading implies shared-capital portfolio behavior that does not exist

---

### ISSUE-14 — Entry at Signal Bar Close (No Next-Bar Execution Lag)
**Class:** REALISM-CRITICAL | **Status:** Proven  
**File:** `intelligence/backtester.py:_simulate()`

Already noted in ISSUE-06. Separate classification because this is distinct from the candle data problem — it is an **order execution timing assumption** that would remain even after fixing closed-candle signal generation. The backtester should enter at bar `i+1` open, not bar `i` close.

---

## Section 7 — Code vs Comment/Doc Mismatches

### ISSUE-15 — Hard Time Stop Comment Says 3.5hr, Code Says 8hr
**Class:** STRATEGY-QUALITY-CRITICAL | **Status:** Proven  
**File:** `core/position_monitor.py`

```python
HARD_TIME_STOP_SEC = 8 * 60 * 60    # 8 hours — hard kill (was 3.5hr)

# Inside _check_performance_time_stop():
# comment: "── Hard time stop: 3.5 hours ─────────────────"
# logger:  "3.5hr max reached"
```

The constant is correct (8 hours). The internal comment header and the logger message both say "3.5hr." Anyone reading the log will believe they are seeing a 3.5-hour stop triggering when it is actually an 8-hour stop.

---

### ISSUE-16 — _check_performance_time_stop Docstring Thresholds Do Not Match Constants
**Class:** STRATEGY-QUALITY-CRITICAL | **Status:** Proven  
**File:** `core/position_monitor.py:_check_performance_time_stop()`

The docstring says:
```
- After 20 min: if pnl < -0.3% AND still moving wrong → early exit
- After 1 hour: if pnl < 0.5% → going nowhere, free up capital
- After 3 hours: if pnl < 1.5% → too slow for a day trade
- After 3.5 hours: hard kill regardless of profit
```

The actual constants:
```python
EARLY_LOSS_CHECK_SEC   = 30 * 60   # 30 min (docstring says 20 min)
EARLY_LOSS_MIN_PCT     = -0.5      # (docstring says -0.3%)
PERF_CHECK_1HR_SEC     = 2 * 60 * 60   # 2 hours (docstring says 1 hour)
PERF_CHECK_1HR_MIN_PCT = 0.2       # (docstring says 0.5%)
PERF_CHECK_3HR_SEC     = 5 * 60 * 60   # 5 hours (docstring says 3 hours)
PERF_CHECK_3HR_MIN_PCT = 1.0       # (docstring says 1.5%)
HARD_TIME_STOP_SEC     = 8 * 60 * 60   # 8 hours (docstring says 3.5 hours)
```

Every single threshold in the docstring is wrong. The thresholds were updated (loosened) but the docstring was never updated. The exit priority list at the top of the class file also references old thresholds. Anyone reading the documentation to understand system behavior will have completely incorrect expectations.

---

### ISSUE-17 — CoinbaseExecutor Class Uses Kraken Internally
**Class:** STRATEGY-QUALITY-CRITICAL | **Status:** Proven  
**File:** `core/trade_executor.py:CoinbaseExecutor`

```python
class CoinbaseExecutor:
    """Executes crypto trades via Coinbase Advanced Trade."""
    def __init__(self):
        self.exchange = ccxt.kraken({          # uses Kraken, not Coinbase
            "apiKey": config.KRAKEN_API_KEY,
            "secret": config.KRAKEN_SECRET_KEY,
```

The class name, docstring, and the `TradeExecutor` docstring ("Crypto: Coinbase → Kraken → paper simulation") all reference Coinbase as a real layer. The actual implementation uses Kraken. `CoinbaseExecutor` is effectively a dead alias. This is not exercised in the critical path (`_submit()` does not call `self.coinbase`), but the naming creates confusion about the broker chain.

---

### ISSUE-18 — Duplicate Symbol Cooldown Block in risk_manager.approve_trade
**Class:** STRATEGY-QUALITY-CRITICAL | **Status:** Proven  
**File:** `core/risk_manager.py:approve_trade()`

The symbol cooldown check block appears **twice** with identical code, back to back (~lines 170 and 185). The second block always evaluates after the first; since the first block returns on a cooldown match, the second block is always dead code. This is a copy-paste artifact that should be removed.

---

### ISSUE-19 — Startup Reconciler Queries Coinbase for Kraken Positions
**Class:** CORRECTNESS-CRITICAL | **Status:** Proven  
**File:** `core/startup_reconciler.py:_reconcile_crypto()`

```python
exchange = ccxt.coinbase({
    "apiKey":  config.COINBASE_API_KEY,
    "secret":  config.COINBASE_SECRET_KEY,
```

The live crypto executor uses Kraken. The startup reconciler queries Coinbase. All crypto positions opened via Kraken will never be found by the reconciler's exchange query. The reconciler falls back to checking current price vs SL/TP — but uses the Coinbase price feed, not Kraken. Prices may differ between exchanges.

Furthermore, the crypto reconciler does **not** call `exchange.fetch_positions()` or equivalent — it only checks current price vs the stored SL/TP. If Kraken closed a position at a price different from stored SL/TP (slippage, partial fill, manual close), the reconciler will not detect it.

---

## Section 8 — Portfolio Simulation Limitations

1. **No shared capital model.** All backtests allocate full `starting_capital` to each symbol independently. A true portfolio test would allocate a fraction to each concurrent position.
2. **No capital contention.** If 5 positions are simultaneously open in backtest, each uses the full capital. In live, `MAX_OPEN_POSITIONS` caps real exposure. The backtest does enforce `MAX_OPEN_POSITIONS = 5` but this is a local constant in `backtester.py` that may differ from `config.MAX_OPEN_POSITIONS`.
3. **No correlation modeling.** Multiple correlated symbols (e.g., BTC and ETH on the same 1h bar) can both signal and both be entered in backtest with no dependency. In live, the second might be blocked by `MAX_OPEN_POSITIONS`.
4. **No realistic intraday capital flow.** The backtester does not model T+1 settlement for stocks or Kraken margin. Capital freed from one closed trade may not be immediately available for the next in live.

---

## Section 9 — Highest-Priority Fixes (Ordered)

| Priority | Issue | Classification | Reason |
|---|---|---|---|
| 1 | ISSUE-01 — Same-bar two_bar stop optimism | CORRECTNESS-CRITICAL | All two_bar backtest results are inflated |
| 2 | ISSUE-03 — 8 live exits absent from backtester | CORRECTNESS-CRITICAL | Makes all performance comparisons unreliable |
| 3 | ISSUE-02 — Stop model mismatch (live % vs backtest structural) | CORRECTNESS-CRITICAL | The winning stop model is not the deployed model |
| 4 | ISSUE-05 — No closed-candle contract in scanner | CORRECTNESS-CRITICAL | Live signals fire on forming candles; backtests use closed candles |
| 5 | ISSUE-09 — No originating timeframe stored with trade | CORRECTNESS-CRITICAL | Required prerequisite for fixing ISSUE-10 |
| 6 | ISSUE-10 — All monitor bars hardcoded to 5m | CORRECTNESS-CRITICAL | 1h trades managed as 5m trades |
| 7 | ISSUE-11 — Time stops in live not in backtest (+ stale comment) | CORRECTNESS-CRITICAL | 8hr hard stop kills 1h swing trades; backtest never models this |
| 8 | ISSUE-06 / ISSUE-14 — Same-bar entry (no execution lag) | REALISM-CRITICAL | Systematic entry lookahead across all strategies |
| 9 | ISSUE-12 — No spread/slippage/commission | REALISM-CRITICAL | Crypto strategies may be net losers after fees |
| 10 | ISSUE-19 — Startup reconciler queries wrong exchange | CORRECTNESS-CRITICAL | Kraken positions not verified on startup |

---

## Section 10 — Phased Implementation Recommendation

### Phase 2 — Candle Integrity (implement first, lowest risk)
Fix ISSUE-05. Add a `is_bar_closed()` utility. In `get_bars()` and `get_ohlcv()`, strip the last bar if its timestamp indicates it is still forming (current bar's expected close time > now). Deliver `CANDLE_INTEGRITY_SPEC.md`.

**Prerequisite for:** everything else. Candle integrity must be in place before stop engine changes are meaningful.

---

### Phase 3 — Unified Stop Engine (high risk, high value)
Fix ISSUE-01, ISSUE-02, ISSUE-07, ISSUE-08.  
**Decision required first:** pick ONE production stop model.

- **Option A — Commit to percent trailing:** Update backtest standard mode to fill stops at stop price (not close). Validate trailing cadence in backtest (every bar) vs live (every 10s poll). Remove two_bar mode or clearly label it "experimental/not-deployed."
- **Option B — Commit to two_bar structural:** Fix same-bar optimism (update takes effect bar+1). Implement two_bar logic in `risk_manager` and `position_monitor` replacing the percent trailing. Both environments now use structural stops.

Do not run both in parallel without a clear split by strategy name.

---

### Phase 4 — Timeframe-Aware Trade Lifecycle
Fix ISSUE-09 and ISSUE-10 together.  
Add `entry_timeframe` field to trade record in `trade_executor.execute_signal()`. Update `position_monitor._get_bars()` to use `trade.get("entry_timeframe", "5m")`. Update all exit checks to use the correct timeframe bars. Deliver `TIMEFRAME_LIFECYCLE_SPEC.md`.

---

### Phase 5 — Backtest Realism Hardening
Fix ISSUE-12, ISSUE-13, ISSUE-14.  
Add configurable fee/slippage model. Fix entry timing (bar+1 open). Add a proper portfolio simulation mode (shared capital pool, position count cap applied across symbols simultaneously). Deliver `BACKTEST_REALISM_NOTES.md`.

---

### Phase 6 — Live Lifecycle Representation in Backtest
Fix ISSUE-03, ISSUE-04, ISSUE-11.  
Add time stops, cooldowns, and ADX stale logic to the backtester. These must match the live thresholds exactly (not the stale docstring values). Fix all stale comments (ISSUE-15, ISSUE-16).

---

### Phase 7 — Cleanup and Reconciler Fix
Fix ISSUE-17, ISSUE-18, ISSUE-19.  
Remove duplicate cooldown block. Rename or remove `CoinbaseExecutor`. Rewrite crypto startup reconciler to query Kraken positions (not Coinbase price vs SL/TP).

---

## Section 11 — Performance Claims That Must Be Treated as Unreliable

The following claims cannot be trusted until the above phases are complete:

| Claim | Why Unreliable |
|---|---|
| Any win rate from two_bar backtest mode | ISSUE-01: same-bar optimism inflates results |
| Any return from crypto strategies | ISSUE-12: zero-friction backtest; fees alone may erase returns |
| Any 1h strategy comparison between backtest and live | ISSUE-03, ISSUE-10, ISSUE-11: live has 8-hour hard stop and 5m monitoring that backtests never see |
| "Portfolio" return from `run_all()` | ISSUE-13: it is not a portfolio test |
| Any strategy where scanner timing matters | ISSUE-05: live operates on forming candles, backtest on closed candles |
| Win rate comparisons between strategies run at different timeframes | ISSUE-10: all are managed identically at 5m regardless of entry timeframe |
| Any performance claim based on live paper trading vs backtest | ISSUE-02: the stop model is different; the paper trades are not running the backtested stop |

**Until Phases 2–4 are complete, no backtest result for any strategy should be used to justify live capital allocation decisions.**

---

## Appendix — Non-Issues (Examined and Cleared)

- `risk_manager.approve_trade()` max position check: correctly queries DB. No issue.
- `TwoBarStop.initial_stop()`: correctly excludes the current entry bar from the lookback window (uses `entry_idx` exclusive). No lookahead at entry. Issue is only in `update_stop` → `check_stop_hit` same-bar sequence (ISSUE-01).
- Daily loss halt in backtester: the `trading_halted` flag resets each day, consistent with the session-based live reset. Acceptable.
- IBKR fallback chain in `trade_executor.py`: the dual-broker fallback is operational complexity but not a parity bug.
- `MAX_OPEN_POSITIONS` in backtester: local constant is 5, should verify matches `config.MAX_OPEN_POSITIONS` — minor, not audit-critical.

---

*End of PARITY_AUDIT.md — Phase 1 complete. Awaiting approval before any implementation begins.*
