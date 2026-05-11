# STRATEGY STACK REVIEW — Phase 7

**Status:** Awaiting approval before any implementation  
**Date:** 2026-05-10  
**Scope:** All 11 strategies reviewed in full. No code changes made in this document.

---

## 1. Current Stack Inventory

| # | File | Class | Enabled | TF | Asset | Exemptions |
|---|------|-------|---------|-----|-------|------------|
| 1 | `rsi_momentum.py` | RSIMomentum | **False** | 5m | Both | — |
| 2 | `bollinger_breakout.py` | BollingerBreakout | **True** | 5m/1h | Both (crypto live-off) | ml_exempt, auto_disable_exempt |
| 3 | `ema_crossover.py` | EMACrossover | **False** | 5m | Both | — |
| 4 | `mean_reversion.py` | MeanReversion | **False** | 5m | Both | auto_disable_exempt |
| 5 | `scalp_master.py` | ScalpMaster | **True** | 5m | Both | — |
| 6 | `swing_trader.py` | SwingTrader | **False** | 1h | Both | — |
| 7 | `grid_bot.py` | GridBot | **True** | 1h | Both | reviewer_exempt, ml_exempt, auto_disable_exempt |
| 8 | `dca_accumulator.py` | DCAAccumulator | **True** | 1h | Blue-chip | — |
| 9 | `vwap_momentum.py` | VWAPMomentum | **False** | 1h | Stock only | — |
| 10 | `hammer_reversal.py` | HammerReversal | **True** | 5m | Crypto (SOL only) | — |
| 11 | `orb_breakout.py` | ORBBreakout | **False** | 5m | Stock only | — |

Currently enabled: 5 (Bollinger Breakout, Scalp Master, Grid Bot, DCA Accumulator, Hammer Reversal)

---

## 2. Individual Strategy Assessment

### Strategy 1 — RSI Momentum (`rsi_momentum.py`)

**Logic:** RSI crossback through oversold/overbought threshold. Two-indicator strategy (RSI crossback + close direction). No ADX, no volume, no trend.

**Classification: REMOVE**

**Rationale:**
- Single momentum indicator with a price direction check. This is the minimum viable implementation of momentum detection, not a production strategy.
- No trend filter: fires freely in choppy markets.
- No volume confirmation: signals on low-conviction bars.
- Completely subsumed by Strategy 5 (Scalp Master), which adds VWAP, ADX, EMA9/21, and adaptive SL/TP on top of RSI. Every scenario where RSI Momentum fires, Scalp Master either also fires (with better confirmation) or correctly rejects (because volume/ADX/VWAP aren't aligned).
- All backtest results are inflated: pre-Phase-5 (no friction), pre-Phase-3 (same-bar stop optimism, intrabar stop not modeled).

---

### Strategy 2 — Bollinger Breakout (`bollinger_breakout.py`)

**Logic:** BB breakout (close outside band) + OBV trend confirmation + EMA50 trend bias + RSI directional filter. Two blacklists (symbols with poor live performance). Crypto live mode was disabled after live losses.

**Classification: KEEP (demoted — secondary breakout role, not primary coverage)**

**Rationale:**
- Four filters is a reasonable confirmation stack for a breakout strategy.
- However: the two exemptions (ml_exempt, auto_disable_exempt) mean it's invisible to both the ML layer and the performance watchdog. It can continue trading at low win rates with no corrective signal.
- The crypto live-disable after real losses is appropriate caution, but the cause was never diagnosed. The strategy stayed enabled for stocks but the root issue isn't documented.
- In the proposed stack: this becomes one of several breakout/event strategies, not the primary momentum engine.
- **Pre-implementation requirement:** Rerun with Phase 5 friction (especially crypto at 0.62% round-trip). Remove auto_disable_exempt once performance tracking is trusted.

---

### Strategy 3 — EMA Crossover (`ema_crossover.py`)

**Logic:** Fast/slow/trend triple EMA crossover. Score based on EMA spacing. Simple trend-following.

**Classification: CONVERT TO FILTER**

**Rationale:**
- Triple EMA alignment (fast > slow > trend for long) is a proven trend regime indicator, not a standalone signal. The VWAP Momentum strategy already uses the more refined EMA 5/13/34 stack from the same paradigm but with proper confirmation filters on top.
- As a standalone signal, it provides too few filters to trade confidently.
- As a regime filter ("are EMAs aligned?"), it provides genuine value — and this check already exists in a more refined form inside VWAP Momentum.
- Do not delete the file; extract the EMA alignment logic into the shared filter layer.

---

### Strategy 4 — Mean Reversion (`mean_reversion.py`)

**Logic:** Z-score deviation from rolling mean. Skips trending markets (ADX gate). Large ~80-symbol whitelist.

**Classification: KEEP (refactor required — whitelist surgery)**

**Rationale:**
- Z-score mean reversion is conceptually sound for ranging markets, and the ADX gate to skip trending markets is the right instinct.
- **The 80-symbol whitelist is the problem.** Mean reversion works on a tight basket where you've verified the instruments are actually mean-reverting (e.g., ETF pairs, blue-chip large-caps). An 80-symbol list without per-symbol validation is signal noise.
- The auto_disable_exempt protection is hiding potential underperformers.
- In the proposed stack: this becomes the range/reversion engine, but with a curated whitelist of 10-15 symbols verified to be range-bound (not trending) and with auto_disable_exempt removed.
- **Pre-implementation requirement:** Trim whitelist to validated symbols. Remove auto_disable_exempt.

---

### Strategy 5 — Scalp Master (`scalp_master.py`)

**Logic:** RSI + VWAP + ADX + EMA9/21. 8-symbol whitelist. Per-symbol adaptive SL/TP via `symbol_params.json`. 5m bars.

**Classification: KEEP (primary intraday momentum engine)**

**Rationale:**
- Most disciplined momentum strategy in the stack: five confirmation layers plus per-symbol adaptive risk parameters.
- Tight whitelist (8 symbols) based on backtested performance is the right selectivity model.
- The adaptive SL/TP approach acknowledges that volatility profiles differ across symbols — this is production thinking.
- No exemptions: it participates in auto-disable, ML scoring, and reviewer validation.
- **Performance caveat:** All historical results are inflated by pre-Phase-3 stop optimism and pre-Phase-5 friction. Rerun backtests with friction enabled and verify positive expectancy remains.

---

### Strategy 6 — Swing Trader (`swing_trader.py`)

**Logic:** ADX trend + RSI pullback entry on 1h bars. 2.5% SL, 6% TP. Wide stops appropriate for swing timeframe.

**Classification: KEEP (secondary — enable only after backtesting with new engine)**

**Rationale:**
- ADX trend strength + RSI pullback-in-trend is a textbook swing entry method. The risk ratios (2.5% SL, 6% TP = 2.4R) are appropriate for the timeframe.
- Currently disabled. The backtest results that existed pre-Phase-3 are untrustworthy. This strategy has never been tested with: (a) the correct two-bar structural stop model, (b) intrabar stop checks, or (c) realistic friction.
- Must be backtested end-to-end with the Phase 3+5 engine before enabling.
- Not a merge candidate — swing and scalp are different timeframe strategies serving different capital allocation buckets.

---

### Strategy 7 — Grid Bot (`grid_bot.py`)

**Logic:** BB + ADX — long when price near lower BB in a ranging market (ADX low), short near upper BB. 1h bars. Meme coin variants with wider SL.

**Classification: MERGE (into one range engine with Mean Reversion)**

**Rationale:**
- This and Mean Reversion are both range-trading strategies. They differ in entry trigger (BB-relative position vs. z-score) but share the same regime requirement (non-trending market), the same holding profile, and the same risk purpose.
- **The three exemptions (reviewer_exempt, ml_exempt, auto_disable_exempt) are a serious code smell.** reviewer_exempt means the standard signal validator doesn't process its output. ml_exempt means ML scoring skips it. auto_disable_exempt means it cannot be automatically disabled regardless of win rate. This strategy is running outside the normal safety system.
- The reviewer_exempt was added because ADX+BB signals were missing standard indicator metadata — this is a structural fix that was deferred, not a design decision.
- In the proposed stack: Grid Bot's BB-relative positioning entry is one mode of a unified range engine. The exemptions are removed by fixing the metadata, not by continuing to bypass validation.

---

### Strategy 8 — DCA Accumulator (`dca_accumulator.py`)

**Logic:** EMA50 dip + RSI on 1h bars. Blue-chip-only whitelist. Name implies multiple DCA entries but appears to be single entry per signal.

**Classification: KEEP (rename, clarify purpose)**

**Rationale:**
- The blue-chip whitelist is disciplined. The EMA50 dip + RSI filter is appropriate for buying quality names during pullbacks in an uptrend.
- Naming issue: "DCA Accumulator" implies staggered entries, but the code generates one signal per scan. If it's a single dip-buy entry, it should be named "DipBuy" or "PullbackEntry" to be accurate. The naming causes confusion about whether position sizing should be 1× or staged.
- This is the only strategy explicitly targeting blue-chip dip buys. It fills a real niche that neither the scalp nor the range strategies cover well.
- No exemptions — participates in all safety systems.

---

### Strategy 9 — VWAP Momentum (`vwap_momentum.py`)

**Logic:** VWAP directional filter + EMA 5/13/34 momentum stack + ADX trend + RSI zone (40-60, not oversold/overbought) + volume conviction. RSI hard blocks (>82 long, <18 short) from live IONQ experience. Stock only, 17-symbol whitelist, 1h bars.

**Classification: KEEP (enable after backtest validation with new engine)**

**Rationale:**
- This is the most thoughtfully designed momentum strategy in the stack. The RSI zone (40-60) for momentum-building rather than extremes is a deliberate design choice that separates it from mean-reversion entries. The RSI hard blocks above 82/below 18 are the direct product of a real trading loss — this is learned-from-experience code.
- The timeframe change (5m → 1h based on empirical observation that VWAP works better on 1h for stocks) shows iteration and discipline.
- Not a merge candidate with Scalp Master: Scalp Master targets 5m intraday scalps with tight adaptive SL/TP. VWAP Momentum targets 1h intraday momentum with 90-minute time stop. Different timeframes, different holding periods, different risk budgets.
- **Pre-implementation requirement:** Backtest with Phase 3+5 engine. Currently shows no `self.enabled = False` explicit assignment in `__init__` — base class default is in play. Verify the base default is False (file docstring says disabled).

---

### Strategy 10 — Hammer Reversal (`hammer_reversal.py`)

**Logic:** Five simultaneous conditions: RSI < 30 + Stochastic slowK < 20 + price below lower BB + hammer candle pattern + OBV rising for 3 consecutive bars. Wide 10% stop loss. SOL/USD only. Enabled=True.

**Classification: KEEP (with one critical flag)**

**Rationale:**
- The five-filter stack is highly selective by design. The OBV requirement is a genuine improvement over the freqtrade original — it filters out hammer candles in waterfall selloffs where volume is still flowing out.
- SOL/USD only based on actual backtest (Sharpe 1.37, Profit Factor 2.17). ETH excluded at Sharpe -3.20. This is properly evidence-based.
- Wide 10% stop is appropriate: entry already requires price below lower BB + oversold on two oscillators; the reversal thesis requires room for the initial bounce to develop.

**Critical flag — dead metadata:**
The `roi_ladder` dict in signal metadata (`{"0": 5.0, "20": 4.0, "30": 3.0, "60": 1.0}`) is passed into the signal but there is no evidence that `position_monitor.py` reads or acts on it. If the position monitor uses a fixed TP%, the tiered ladder is dead code. This needs verification: either the ladder is implemented and should be documented, or it is dead code and should be removed to avoid the false impression that tiered exits are active.

---

### Strategy 11 — ORB Breakout (`orb_breakout.py`)

**Logic:** Opening range (9:30-9:44 ET) established in first 3 bars. Breakout above/below ORB with VWAP confirmation + volume conviction. ATR-based TP (2× ATR, 1-8% clamped). Stop at opposite side of opening range. 15-symbol whitelist from backtests.

**Classification: KEEP (enable after backtest validation with new engine)**

**Rationale:**
- ORB is a widely used institutional strategy with a clear causal mechanism (stop cascade + algo triggers at range break). The thesis is sound.
- ATR-based TP is more sophisticated than fixed % and correctly adapts to session volatility.
- Stop at opposite range level is the natural invalidation point — this is the correct structural stop for an ORB thesis, not a percent stop.
- 15-symbol whitelist from actual backtest pass/fail (Apr 2026, 5 symbols excluded by name).
- **Note:** The ORB range detection (`_get_orb_levels`) falls back to `candles.iloc[:3]` when timestamp filtering fails. If the scanner is delivering bars that don't have a timezone-aware DatetimeIndex, the fallback silently uses the first 3 bars regardless of what time they represent. This is an edge case but could produce incorrect ORB levels on some bar formats.

---

## 3. Performance Claims — Inflation Risk Assessment

All strategies developed and backtested before Phase 5 (2026-05-10) were tested with:
- **Zero commissions, zero slippage** (most impactful for crypto: 0.62% round-trip cost omitted)
- **Same-bar stop optimism** (Phase 3 fix: stop could advance AND stop-out in same bar)
- **Standard mode using close price for stop checks** instead of intrabar low/high

| Strategy | Inflation Risk | Why |
|---|---|---|
| RSI Momentum | **High** | High frequency scalp-style + all three bugs active |
| Bollinger Breakout | **High (crypto)** / Medium (stock) | Crypto: 0.62% friction omitted. Stock: minimal commission impact |
| EMA Crossover | **Medium** | Stop optimism bug; lower frequency than scalp |
| Mean Reversion | **High** | 80-symbol universe × no cooldown in backtester = correlated entry duplication |
| Scalp Master | **High** | Tight SL/TP scalps × all three bugs; most sensitive to friction |
| Swing Trader | **Medium** | 1h bars, fewer trades, lower frequency = friction impact smaller but stop bug still applies |
| Grid Bot | **High** | Range-mean strategies sensitive to stop optimism; 3 exemptions mean no auto-correction |
| DCA Accumulator | **Medium** | 1h bars, blue-chip only; friction less punishing at 1h granularity |
| VWAP Momentum | **Medium** | Stock only (0.02% round-trip vs crypto 0.62%); ADX filter keeps frequency low |
| Hammer Reversal | **Medium-Low** | Very selective 5-filter; SOL only; Apr 2026 backtest likely pre-Phase-5 still |
| ORB Breakout | **Medium-Low** | ATR TP adapts to volatility; VWAP + volume filters reduce frequency; Apr 2026 backtest still pre-Phase-5 |

**Critical finding:** Any crypto strategy (Bollinger Breakout crypto side, Scalp Master crypto symbols, Grid Bot crypto symbols, Hammer Reversal) that averaged less than ~0.80% gross per trade is likely unprofitable after Kraken standard-tier fees. All such historical results should be treated as unreliable until re-run with Phase 5 friction.

---

## 4. Structural Issues Found

### 4.1 Grid Bot triple exemption
`reviewer_exempt=True`, `ml_exempt=True`, `auto_disable_exempt=True` on a single strategy means it is outside three of the four safety systems. The root cause is missing standard indicator metadata in its signals, not an intentional design exception. **Fix the metadata; remove the exemptions.** The exemptions should never have been applied as a permanent workaround.

### 4.2 Hammer Reversal ROI ladder — dead metadata
`roi_ladder: {"0": 5.0, "20": 4.0, "30": 3.0, "60": 1.0}` is embedded in signal metadata but position_monitor.py does not appear to consume it. If the tiered exit logic was never implemented, the TP is just the flat initial value (5%) regardless of how long the trade is held. The intent (kill switch at 1% after 60 bars) is good; it just may not be executing. Verify and either implement or document as removed.

### 4.3 VWAP calculation duplication
`_calc_vwap()` is defined independently in both `vwap_momentum.py` and `orb_breakout.py`. These are identical functions. Should live in a shared utility module (e.g., `strategies/indicators.py`).

### 4.4 DCA Accumulator naming mismatch
The class is named `DCAAccumulator` and generates single entry signals. If the live trading loop does not stage follow-up entries, it is functioning as a dip-buy strategy, not a DCA strategy. The name misleads anyone reading position sizes expecting staged accumulation.

### 4.5 VWAP Momentum `enabled` default unclear
`VWAPMomentum.__init__()` does not set `self.enabled`. Base class default governs. The file docstring says disabled. This should be made explicit: `self.enabled = False` in `__init__`.

### 4.6 ORB `_get_orb_levels()` timestamp fallback
Falls back to `candles.iloc[:3]` when the candle index lacks `.hour` attribute. This silently uses the first 3 available bars regardless of their real timestamps. If the bar provider gives bars starting at a time other than 9:30, the "opening range" will be wrong. The fallback should warn loudly and return `None, None` rather than silently proceeding with potentially wrong data.

---

## 5. Proposed Production Stack

This is a proposed architecture for review. **No implementation until explicitly approved.**

### Guiding principles
1. Fewer strategies with more filters beats many strategies with thin filters.
2. Every production strategy must participate in auto-disable, ML scoring, and reviewer validation (no exemptions as permanent workarounds).
3. One range engine; one momentum engine; one shared risk layer; one veto layer.
4. Each active strategy needs a post-Phase-5 backtest before enabling.

---

### Layer 0 — Regime Gate (shared, always-on)

A market condition classifier determines which engine is active per symbol per scan. Currently this result is passed into strategies individually; it should be a pre-filter that routes symbols to the appropriate engine before signal evaluation.

```
Trending  → Momentum Engine routes
Ranging   → Range Engine routes
Unknown   → Conservative filter: only allow strategies with 4+ confirmation filters
```

This is already partially implemented via the `market_condition` parameter. The gap is consistency — some strategies skip ranging, some don't check at all.

---

### Layer 1 — Momentum Engine (trending markets)

**Primary — intraday scalp (5m):** Scalp Master  
Keep as-is. Rerun backtest with Phase 5 friction. Verify positive expectancy on stock symbols. Crypto symbols need individual verification at 0.62% round-trip.

**Primary — intraday swing (1h stocks):** VWAP Momentum  
Enable after Phase 5 backtest validation. Fix the `self.enabled = False` omission. The RSI zone design (40-60 for building momentum) and hard blocks (>82/<18) should be preserved.

**Candidate — event-time breakout (5m stocks):** ORB Breakout  
Enable after Phase 5 backtest. Fix the `_get_orb_levels()` fallback to return None instead of silently using wrong bars. The ATR TP and structural stop (opposite ORB side) are production-quality.

**Candidate — volatility breakout (5m/1h both):** Bollinger Breakout  
Retain as breakout/event strategy. Remove auto_disable_exempt. Run Phase 5 crypto backtest — if expectancy is negative after 0.62% friction, disable crypto side permanently with documentation.

**Retire:** RSI Momentum (remove), EMA Crossover (convert logic to filter layer)

---

### Layer 2 — Range/Reversion Engine (ranging markets)

**Unified range engine (merge Grid Bot + Mean Reversion):**

One class with two configurable entry modes:
- Mode A: BB-relative entry (Grid Bot's logic)
- Mode B: Z-score entry (Mean Reversion's logic)

Shared: ADX gate (ADX < threshold = ranging), risk framework, whitelist management.

Grid Bot's three exemptions are removed. The metadata issue that caused reviewer_exempt is fixed. The merged engine participates in all safety systems.

Mean Reversion whitelist trimmed from ~80 to ~15 symbols: only instruments backtested to be range-bound and not trending (ETFs, index components, established crypto pairs).

---

### Layer 3 — Selective/Event Engine (tight whitelists, always-on)

**Hammer Reversal (SOL/USD, 5-filter)**  
Keep. Resolve ROI ladder status (implement or remove). Verify position_monitor consumes or explicitly ignores the ladder metadata.

**DCA Accumulator (blue-chip dip buy)**  
Keep. Rename to `DipBuyEntry` or document clearly that it is not a DCA strategy. If staging entries is desired, implement it explicitly.

**Swing Trader (1h, ADX+RSI pullback)**  
Retain disabled. Enable after Phase 3+5 backtest. Good risk ratios; fits a swing allocation bucket the other strategies don't cover.

---

### Layer 4 — Shared Risk/Execution (already partially built in Phase 3)

- `core/stop_engine.py` — Two-bar structural stops (Phase 3) ✅
- Stale structural stop at execution — **hard pre-live gate, not yet fixed** ⛔
- `core/risk_manager.py` — Position sizing, trailing stop
- `core/position_monitor.py` — Exit overlay (5m hybrid, Phase 4) ✅

No changes to this layer from this review. The pre-live gate (recompute stop at fill time) is already tracked.

---

### Layer 5 — Veto/Filter (overlay, applied universally)

Consolidate checks currently scattered across individual strategies:

| Filter | Currently In | Should Be |
|---|---|---|
| RSI hard blocks (>82 long, <18 short) | VWAP Momentum only | Universal overlay |
| Volume conviction (1.5× average) | Multiple strategies, inconsistent thresholds | Configurable per asset class |
| Market condition routing | Passed to strategies, inconsistently used | Regime Gate (Layer 0) |
| EMA alignment (fast > slow > trend) | EMA Crossover strategy | Filter helper function |
| ADX trending/ranging gate | Multiple strategies, inconsistent cutoffs | Configurable per engine |

These should be consolidated into a `strategies/filters.py` module with named functions that strategies can call instead of re-implementing independently.

---

## 6. Summary Classification Table

| # | Strategy | Classification | Action |
|---|---|---|---|
| 1 | RSI Momentum | **REMOVE** | Subsumed by Scalp Master; delete file after approval |
| 2 | Bollinger Breakout | **KEEP** (demote) | Remove auto_disable_exempt; rerun crypto backtest with friction; demote from primary coverage |
| 3 | EMA Crossover | **CONVERT TO FILTER** | Extract EMA alignment logic to filters.py; disable as standalone strategy |
| 4 | Mean Reversion | **KEEP** (refactor) | Trim whitelist to ~15 symbols; remove auto_disable_exempt; merge into range engine |
| 5 | Scalp Master | **KEEP** (primary) | Rerun backtest with Phase 5 friction; verify positive expectancy |
| 6 | Swing Trader | **KEEP** (enable after backtest) | Backtest with Phase 3+5 engine before enabling |
| 7 | Grid Bot | **MERGE** into range engine | Fix metadata → remove all 3 exemptions; merge with Mean Reversion |
| 8 | DCA Accumulator | **KEEP** (rename/clarify) | Rename or document DCA semantics; keep blue-chip discipline |
| 9 | VWAP Momentum | **KEEP** (enable after backtest) | Add explicit `self.enabled = False`; backtest with Phase 5; enable after validation |
| 10 | Hammer Reversal | **KEEP** (fix ROI ladder) | Verify/implement tiered ROI ladder or remove dead metadata; keep 5-filter stack |
| 11 | ORB Breakout | **KEEP** (enable after backtest) | Fix `_get_orb_levels()` fallback; backtest with Phase 5; enable after validation |

---

## 7. Pre-Approval Hard Gate Items (separate from strategy redesign)

These are Phase 7 cleanup items from the VERIFICATION_REPORT that must be resolved regardless of the strategy redesign decision:

| Item | File | Status |
|---|---|---|
| Stale structural stop at execution | `core/trade_executor.py` | **Hard pre-live gate** — recompute stop at broker fill time |
| ISSUE-19: reconciler queries Coinbase not Kraken | `core/startup_reconciler.py` | **Hard operational blocker** — crypto positions not reconciled |
| ISSUE-17: CoinbaseExecutor naming | `core/broker_router.py` or executor file | Misleading naming for a Kraken executor |
| ISSUE-18: duplicate cooldown block | `core/risk_manager.py` | Dead code / double-processing risk |
| ISSUE-15/16: stale 3.5hr docstring thresholds | `core/position_monitor.py` | Misleading documentation |

These should be approved and implemented independently of the strategy redesign.

---

## 8. Implementation Order (proposed, pending approval)

If the strategy redesign is approved, recommended sequence:

1. **Phase 7a — Hard gate items** (ISSUE-19, stale stop fix, ISSUE-17/18, ISSUE-15/16) — no strategy code touched
2. **Phase 7b — Cleanup** (remove RSI Momentum, add `self.enabled=False` to VWAP Momentum, fix ORB fallback, fix Grid Bot metadata, resolve Hammer ROI ladder) — surgical file-by-file, no architecture changes
3. **Phase 7c — Range engine consolidation** (merge Grid Bot + Mean Reversion into unified range engine, remove 3 exemptions) — new file, two files retired
4. **Phase 7d — Filter layer** (extract RSI hard blocks, EMA alignment, volume conviction into `strategies/filters.py`) — no behavior change, DRY refactor
5. **Phase 7e — Backtest gate** (rerun Scalp Master, Bollinger Breakout crypto, VWAP Momentum, ORB Breakout, Swing Trader with Phase 3+5 engine) — no code changes, results gate enable/disable decisions

---

*Do not implement any strategy redesign until this document is reviewed and approved.*  
*Hard gate items (Section 7) may be approved and implemented independently.*
