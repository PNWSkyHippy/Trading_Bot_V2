# trading_bot_v2 — Project State Summary
**Updated:** 2026-05-20  
**Purpose:** Cold-start reference for new Claude sessions. Read this first.

---

## Architecture Overview

```
BreakoutScanner.py  (external process — price momentum scanner)
    |-- HTTP POST
breakout_sender.py  -->  core/breakout_receiver.py  -->  trade_executor.py

market_scanner.py  (strategy-based scanner, 30s/60s cycles)
    |-- signals --> intelligence/claude_reviewer.py --> trade_executor.py
                                                            |
                                         core/stop_engine.py + core/position_monitor.py
                                                            |
                                                  data/trading_bot.db  (SQLite)
```

**Key config:** `config.py` — all strategy tuning, watchlists, flags  
**Live DB:** `data/trading_bot.db`  
**Backtester:** `intelligence/backtester.py` (yfinance, NOT live exchange)

---

## Strategy Suite — Current Status (May 2026)

### Apr 2026 Backtest Results (30d, 25 symbols each)

| Strategy | Asset | TF | WR | PF | Status |
|---|---|---|---|---|---|
| rsi_dip_spike_v4 | stocks | 5m | 63% | 1.196 | BEST — but stock_enabled=False (see Pending) |
| rsi_dip_spike_v4 | crypto | 1h | 44% | 1.036 | OK |
| vwap_momentum | stocks | 1h | 52% | 1.812 | Good |
| orb_breakout | stocks | 15m | 55% | 1.984 | Good |
| vwap_confirmed_orb | stocks | 15m | 50% | 1.73 | Good |
| adaptive_regime | stocks | 1h | 80% | -- | Only 5 trades; stock-only now |
| bollinger_squeeze | crypto | 1h | ~29% | ~1.1-1.3 | Low WR, 2.8 R:R; stop bug FIXED |
| grid_bot | crypto | -- | -- | -- | DISABLED (-$517 live; needs quant audit) |
| scalp_master | stocks | 5m | 0 trades | -- | FIXED (f-string crash) |
| hammer_reversal | crypto | 5m | 0 trades | -- | FIXED (whitelist expanded) |
| ecb_strategy | crypto | 5m | 8% WR | -- | FIXED (TF guard added) |
| dca_accumulator | crypto | -- | -- | -- | Disabled; stop guard applied |
| vwap_momentum | crypto | any | 0 trades | -- | By design (stock-only) |

---

## Bugs Fixed — This Session (2026-05-20)

### 1. scalp_master.py — CRITICAL f-string crash
**Bug:** `f"ADX={adx_val:.1f if adx_val else 'N/A'}"` — Python parses `:` as
format-spec separator. Format spec `.1f if adx_val else 'N/A'` is invalid,
raises ValueError at runtime. Backtester catches silently at DEBUG. Every
signal was swallowed. Zero trades 100% caused by this.  
**Fix:** Pre-computed `adx_str`/`vwap_str` variables before building reason string.
Both long + short paths fixed.  
**Also:** Added `ml_exempt = True` (was missing)

### 2. bollinger_squeeze.py — CRITICAL stop/TP decimal vs percent bug
**Bug:** `stop_loss_pct = 0.025`, `take_profit_pct = 0.070` — set as ratios, not
percentages. Framework divides by 100 at execution, so stop = 0.025% (2.5 bps).
Any signal stops out on next tick. Docstring said "stop=2.5%, tp=7.0%".  
**Fix:** Changed to `stop_loss_pct = 2.5`, `take_profit_pct = 7.0`

### 3. ecb_strategy.py — Wrong timeframe producing garbage signals
**Bug:** No timeframe guard. On 5m bars, entropy collapses every few hours of
noise (8% WR observed). 200-bar macro trend = only 16h of data on 5m bars.  
**Fix:** Bar-interval check at top of `analyze()` — auto-skips when detected
bar width < 50 minutes (3000s threshold). ECB self-skips on 5m/15m.

### 4. trade_executor.py — DCA structural stop override
**Bug:** `initial_stop_from_tail()` on oversold entries places stop at 2-bar
low, which on a local bottom is nearly at entry price. Unconditionally overrode
DCA's 2% floor. ETH opened live today with 0.26% stop.  
**Fix:** Lines ~517-522 in trade_executor.py — if structural stop would be
tighter than strategy's declared `stop_loss_pct`, use percent floor instead.
Logs [STOP GUARD] when triggered.

### 5. hammer_reversal.py — Whitelist too narrow
**Fix:** Expanded from SOL only to SOL + BTC + ADA + AVAX + DOT + LINK.
ETH stays excluded (Sharpe -3.20). New symbols on monitor status.

### 6. vwap_momentum.py — Missing ml_exempt
**Fix:** Added `ml_exempt = True`

---

## Bugs Fixed — Previous Sessions (May 2026)

- adaptive_regime: added `time_stop_profile`, `preferred_initial_stop_mode`,
  `preferred_trail_mode` — converted to stock-specialist only after parallel chat refactor.
  `auto_disable_exempt = True`, `ml_exempt = True`
- dca_accumulator: `ml_exempt = True` + `reviewer_exempt = True` — was generating
  signals but ML collapsed all scores; Claude reviewer rejected 100% (DCA metadata
  doesn't match Haiku's expected RSI/MACD/BB% schema)
- hammer_reversal, orb_breakout, vwap_confirmed_orb: all got `ml_exempt = True`
- backtester.py: added "adaptive_regime" to TIME_STOP_EXEMPT frozenset
- config.py: VERBOSE_MODE currently True (revert to False when done diagnosing)
- grid_bot (parallel chat): ADX 20->15, 8 symbols blacklisted, crypto shorts disabled

---

## Critical Architecture Facts

### ml_exempt Flag
Grid bot has 1507 trades in ML training set; all others have <10.
Without `ml_exempt = True`, ML blending collapses scores below 0.65 threshold.
**Rule: Every strategy except grid_bot needs ml_exempt = True.**  
ML weights: <50 trades = 100% rule-based; 50-200 = 70/30; 200+ = 40/60 ML

### reviewer_exempt Flag
Skips per-signal Claude Haiku review. DCA needs this because its metadata
doesn't match Haiku's RSI/MACD/BB% schema (rejects 100%).
`get_morning_context()` can block 60-90s on Massive API call after reboot.

### Stop Engine
`initial_stop_from_tail()` = min(low) of prior N bars.
Problematic on oversold entries — prior bars also at lows.
Minimum-distance guard now in trade_executor.py enforces strategy's stop_loss_pct as floor.
TIME_STOP_EXEMPT in backtester.py: {grid_bot, dca_accumulator, ecb_strategy,
rsi_dip_spike_v4, adaptive_regime}

### Candle Bar Cache
`_last_bar_evaluated` — timestamps of last evaluated closed bar per symbol/tf.
"no bars available" between bar closes = cache hit, NOT a data error.
Other strategies not evaluating = normal between hourly bar closes.

### Backtester vs Live Scanner Gap
Backtester does NOT check `stock_enabled` / `crypto_enabled` flags.
Scanner DOES check them. So a strategy's backtest results may include
asset classes it would never trade live. rsi_dip_spike_v4 is the main case.

### Symbol Whitelist Matching
`_symbol_variants()` in base_strategy.py: "SOL/USD" expands to
{"SOL/USD", "SOL-USD", "SOL", ...}. Whitelist checks are fuzzy.
`BYPASS_STRATEGY_WHITELIST_FOR_INJECTED_SYMBOLS = True` in config.

---

## Pending Work (Prioritized)

### High — Do Next
1. **Enable rsi_dip_spike_v4 on stocks** — `stock_enabled = False` but 63% WR
   on stocks 5m in backtest. Change to `True`, set `stock_candle_timeframe = "5Min"`.
   Highest-ROI action right now.
2. **Re-enable DCA accumulator** — stop guard is in place. Test small size first.
3. **VERBOSE_MODE** — revert to False in config.py when done diagnosing.

### Medium
4. **Backtester stock/crypto_enabled gap** — add flag check to backtester
   `run_strategy()` so results match live behavior.
5. **Bollinger squeeze signal frequency** — legitimately rare event. Run 90-day
   backtest for meaningful sample. Consider relaxing squeeze_thr from 0.06 -> 0.07.
6. **Hammer whitelist expanded** — consider relaxing OBV window 3->2 bars for more signals.
7. **Double "Signals after ML/filter" log** — `_process_signals()` called twice
   on same batch. Minor bug.

### Low
8. **scalp_master ADX filter** — adx_min=20 may be too tight after f-string fix.
   Watch live results; consider 15 if signals still rare.

---

## Quant Auditor Roadmap

Run `/quant-strategy-auditor-refiner` on each strategy below after today's
bug-fix results are observed (give it a few days of live data first).
Audit in this order — worst performers first.

| Order | Strategy | Main issue to audit |
|---|---|---|
| 1 | grid_bot | -$517 live; market-making logic, ADX filter, symbol selection |
| 2 | ecb_strategy | 8% WR on wrong TF; re-evaluate 1h edge hypothesis |
| 3 | hammer_reversal | Too selective (0 trades/30d); relax conditions or expand symbols |
| 4 | bollinger_squeeze | Near-zero signals; is squeeze_thr too tight? signal quality post-stop-fix? |
| 5 | scalp_master | Just fixed crash — audit signal quality and ADX filter after live data |
| 6 | adaptive_regime | Only 5 trades; entry conditions too tight for stock-only mode? |

**Note:** rsi_dip_spike_v4, vwap_momentum, orb_breakout, vwap_confirmed_orb
are performing well and do NOT need auditing yet.

---

## Breakout Pipeline — Plan Status

**BreakoutScanner is the #1 priority for the whole server.**
It generates the largest wins AND largest losses. Strategy suite work is
secondary — get the breakout pipeline airtight first.

**Full spec:** `breakout_pipeline_plan.md` (read that file before implementing)

### COMPLETED (2026-05-19/20 overhaul session)
- **Direction flip logic** — LONG->SHORT / SHORT->LONG reversal when price
  drifts against signal. `core/breakout_receiver.py`. DONE.
- **Re-entry after profitable close** — win callback → 125s timer →
  synthetic signal injected back through receiver checklist.
  `position_monitor.py` + `market_scanner.py` + `bot_engine.py`. DONE.
- **Faster signal delivery** — signals generating faster (likely min_esc
  lowered and/or dedup bypass for escalation re-sends). DONE.
- **Other bug fixes** from that session — READ BreakoutScanner.py,
  breakout_sender.py, breakout_receiver.py before touching anything.
  State is ahead of breakout_pipeline_plan.md.

### STILL PENDING — verify against current code first
- Fix 3: Refresh enrichment on escalation re-sends (90s-stale RSI/OHLC) — `BreakoutScanner.py`
- Add `bars_since_breakout` to EscalationTracker — `BreakoutScanner.py`
- Add `breakout_level` + `distance_from_breakout_pct` — `BreakoutScanner.py`
- Add `structural_stop_price` to `_build_enrichment()` — `BreakoutScanner.py`
- `market_pct_change` for stocks (needs SPY seed) — `BreakoutScanner.py`
- `source_broker/price/timestamp` audit fields — `breakout_sender.py`

### Skip
- sma200 — requires raising history_length 50->200; not worth it

### Key facts for breakout pipeline
- `payload["timestamp"]` = send moment (not detect moment); TTL check cannot fail normally
- Signal age at esc=2 fire = ~0.5s after 90s wait; passes 60s TTL
- Enrichment (RSI/OHLC) is from T=0, 90s stale at esc=2 fire — still unfixed
- Dedup race is theoretical only (single-threaded scan) — harmless for now

---

## File Map

```
config.py                         -- all tuning, watchlists, flags
core/
  exchange_capabilities.py        -- can_short(symbol, broker) — Kraken margin check, Alpaca ETB
strategies/
  base_strategy.py                -- BaseStrategy ABC, whitelist logic
  strategy_engine.py              -- loads all strategies, routes signals
  scalp_master.py                 -- stocks 5m RSI scalp [f-string FIXED]
  hammer_reversal.py              -- crypto 5m reversal [whitelist EXPANDED]
  bollinger_squeeze.py            -- crypto 1h squeeze release [stop scale FIXED]
  bollinger_breakout.py           -- crypto breakout (different from squeeze)
  rsi_dip_spike_v4.py             -- BEST performer; crypto only live [stock_enabled=False!]
  vwap_momentum.py                -- stocks 1h VWAP momentum [ml_exempt added]
  orb_breakout.py                 -- stocks 15m opening range
  vwap_confirmed_orb.py           -- stocks 15m ORB + VWAP
  adaptive_regime.py              -- stocks 1h trend/mean-rev [stock-only now]
  dca_accumulator.py              -- crypto DCA [disabled; stop guard applied]
  ecb_strategy.py                 -- crypto 1h entropy collapse [TF guard added]
  grid_bot.py                     -- crypto grid [ADX/shorts patched]
intelligence/
  backtester.py                   -- yfinance; does NOT check stock/crypto_enabled flags
  claude_reviewer.py              -- Haiku review; BRIEFING_TIMEOUT=30s
core/
  trade_executor.py               -- order execution; structural stop guard ~line 517
  stop_engine.py                  -- initial_stop_from_tail(), two-bar trailing stop
  position_monitor.py             -- monitors open positions
  breakout_receiver.py            -- receives HTTP signals from BreakoutScanner
scanners/
  market_scanner.py               -- main scan loop; checks stock/crypto_enabled flags
breakout_sender.py                -- sends signals from BreakoutScanner to bot
BreakoutScanner.py                -- external process; price momentum scanner
data/trading_bot.db               -- SQLite; all trades/signals/history
```
