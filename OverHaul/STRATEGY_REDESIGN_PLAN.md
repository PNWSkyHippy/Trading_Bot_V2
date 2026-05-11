# STRATEGY REDESIGN PLAN — Phase 8

**Status:** Awaiting approval before any implementation  
**Date:** 2026-05-10  
**Input documents:** CLAUDE_REBUILD_BRIEF.md · STRATEGY_STACK_REVIEW.md  
**Constraint:** No code changes until this document is explicitly approved.

---

## 1. Architecture Overview

The current stack has 11 strategies with inconsistent filter depth, overlapping coverage, three strategies exempt from safety systems, and all backtest results produced before friction was modeled. The redesign collapses this into two primary engines, two shared layers, and one support utility.

```
┌─────────────────────────────────────────────────────┐
│                  REGIME GATE                        │
│  Per-symbol: Trending / Ranging / Unknown           │
│  Routes → Engine 1, Engine 2, or Both               │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┴────────────┐
       ▼                        ▼
┌─────────────┐          ┌──────────────────┐
│  MOMENTUM   │          │  RANGE/REVERSION │
│  ENGINE     │          │  ENGINE          │
│  (Engine 1) │          │  (Engine 2)      │
│             │          │                  │
│ Mode A: 5m  │          │ Mode A: BB-entry │
│ Mode B: 1h  │          │ Mode B: Z-score  │
│ Mode C: ORB │          │ Mode C: Reversal │
│ Mode D: BB  │          │                  │
└──────┬──────┘          └────────┬─────────┘
       │                          │
       └────────────┬─────────────┘
                    ▼
          ┌─────────────────┐
          │  FILTER / VETO  │
          │  LAYER          │
          │  (strategies/   │
          │   filters.py)   │
          └────────┬────────┘
                   ▼
          ┌─────────────────┐
          │  RISK / EXIT    │
          │  LAYER          │
          │  (stop_engine,  │
          │   risk_manager, │
          │   pos_monitor)  │
          └─────────────────┘
```

**Support utility** (outside engine routing):
- `DipBuyEngine` — blue-chip pullback entries; 1h stocks; not regime-gated; tightly scoped

---

## 2. Regime Gate

### 2.1 Classification

The regime gate is computed per symbol once per scan cycle before any engine is invoked. It uses ADX(14) on the symbol's primary trading timeframe.

| ADX Value | Classification | Notes |
|---|---|---|
| ≥ 20 | **Trending** | Directional momentum present |
| < 20 | **Ranging** | Market oscillating; no clear trend |
| Unavailable | **Unknown** | Computation failed, insufficient data |

The threshold (20) matches the ADX gates already used inside Scalp Master and Grid Bot. This is not a new parameter — it canonicalizes the one already scattered across strategies.

### 2.2 Routing Rules

| Regime | Momentum Engine | Range Engine | DipBuy Utility |
|---|:-:|:-:|:-:|
| Trending | ✅ Route | ❌ Skip | ✅ Route |
| Ranging | ❌ Skip | ✅ Route | ✅ Route |
| Unknown | ⚡ Route (self-filtering) | ❌ **Skip** | ✅ Route |

**Range Engine skips on Unknown** — this is the asymmetric rule. Buying a mean-reversion in an unclassified regime risks buying a trend break. The Range Engine requires regime confidence. If the gate cannot classify, no range trades are opened.

**Momentum Engine routes on Unknown** — every Momentum Engine mode already requires ADX ≥ threshold as an internal gate. A genuine ranging or choppy market will reject at the strategy level before any position is sized. The regime gate and each strategy's internal ADX check are intentionally redundant: defense in depth against misclassification.

**Defense against misclassification:**
- Trending misclassified as Ranging → Momentum Engine does not fire. Range Engine fires but its own ADX < 20 gate rejects if the market is actually trending (ADX will be above threshold). Two-layer protection.
- Ranging misclassified as Trending → Range Engine does not fire. Momentum Engine fires but its own ADX ≥ 20 gate rejects if the market is genuinely choppy. Two-layer protection.

**Implementation note:** Each strategy's existing internal ADX check is preserved, not removed, when the regime gate is added. The gate is a routing hint. The strategy is the correctness check.

### 2.3 Regime Gate Location

The classification runs inside the scanner's per-symbol scan loop, before strategies are dispatched. The result is passed as `market_condition` (already a parameter in every strategy's `analyze()` signature). The gate replaces ad-hoc classification that currently exists piecemeal inside individual strategies.

---

## 3. Engine 1 — Momentum Engine

**Thesis:** In a trending market, enter with price, momentum, and volume all aligned in the same direction. Hold until structural stop fires, TP is reached, or time stop kills a stale position.

**Regime:** Trending and Unknown (self-filtering on Unknown via ADX gate)  
**Asset scope:** Stocks (all modes); Crypto (Mode A and Mode D only, validated pairs)

The Momentum Engine is not a single class but a routing layer that dispatches to the correct mode based on the strategy's configured timeframe and trigger type. Modes share the same exit framework; they differ in entry trigger and candle timeframe.

---

### Mode A — Intraday Scalp (5m)
*Current implementation: Scalp Master*

**Entry (long):**
1. Symbol in validated whitelist
2. Price above VWAP (intraday directional bias)
3. EMA9 > EMA21 (short-term trend aligned)
4. ADX ≥ 20 (trending — not ranging)
5. RSI in zone 35-65 (not overbought, not oversold)
6. Volume ≥ 1.5× 20-bar average (conviction)
7. RSI hard block: < 82 (no exhausted longs)

**Entry (short):** Mirror of above. RSI hard block: > 18.

**Exit:**
- Stop: two-bar structural (Phase 3 engine)
- Take profit: per-symbol adaptive from `symbol_params.json`; default 3.0%
- Time stop: 3.5 hours (`HARD_TIME_STOP_HOURS`)
- Performance gate at 1hr (need ≥ 0.2% profit) and 3hr (need ≥ 1.5% profit)
- Trailing: structural trail on new N-bar high/low

**Candle timeframe:** 5m  
**Whitelist:** Current Scalp Master 8-stock whitelist; crypto requires Phase 5 re-validation (pairs averaging < 0.80% gross historically are NOT eligible)  
**Risk sizing:** See Section 6

---

### Mode B — VWAP Swing (1h stocks)
*Current implementation: VWAP Momentum + Swing Trader (both 1h)*

Mode B covers two entry sub-types on 1h bars that can run concurrently on different symbols but should not both fire on the same symbol in the same bar:

**Sub-type B1 — VWAP stack (VWAP Momentum pattern):**
1. Symbol in whitelist
2. Price above VWAP
3. EMA5 > EMA13 > EMA34 (full stack bullish)
4. ADX ≥ 25 (stricter than Mode A — 1h ADX threshold is higher)
5. RSI in zone 40-60 (momentum building, not at extremes)
6. Volume ≥ 1.5× average
7. RSI hard block: < 82

**Sub-type B2 — ADX pullback (Swing Trader pattern):**
1. Symbol in whitelist
2. ADX ≥ 20 (trend established)
3. Price above EMA50 (primary trend up)
4. RSI pulled back to 40-50 range (pullback within uptrend, not reversal)
5. Price bouncing from nearest support (EMA21 or recent swing low)
6. Volume not spiking on pullback (distribution signal absent)

**Exit (both sub-types):**
- Stop: two-bar structural (Phase 3 engine), using 1h bars
- Take profit: ATR-based (2× ATR, clamped 2-8%)
- Time stop: 90 minutes from `entry_time_utc` (B1) / 6 hours (B2, swing holds longer)
- Trailing: structural trail on 1h bars
- No performance time stop at 1h for sub-type B2 (swing needs room to develop)

**Candle timeframe:** 1h  
**Asset:** Stocks only (VWAP unreliable on 24/7 crypto markets)  
**Whitelist:** VWAP Momentum 17-symbol list; expand after live validation

---

### Mode C — Opening Range Breakout (5m, session-gated)
*Current implementation: ORB Breakout*

ORB fires only in the first trading session after 9:45 ET. After that window closes (~12:00 ET), no new ORB signals for the day. This is a session-gated mode, not a regime-gated mode.

**Entry (long):**
1. Symbol in ORB whitelist
2. Current time ≥ 9:45 ET (opening range complete)
3. Opening range established from 9:30-9:44 bars (ORB high and ORB low)
4. ORB range ≥ 0.3% of price (not a quiet, tight open)
5. Current bar high > ORB high (price breaks above range)
6. Price above VWAP (institutional bias confirms up)
7. Volume ≥ 1.5× 20-bar average (conviction behind breakout)

**Entry (short):** Mirror of above — current low < ORB low, price below VWAP.

**Exit:**
- Stop: opposite side of opening range (ORB low for long, ORB high for short). This is a structural, thesis-based stop — not percent-based and not two-bar trailing. If price returns inside the range, the breakout thesis is invalidated.
- Take profit: ATR-based (2× ATR, clamped 1-8%)
- Time stop: market close (no overnight ORB positions)
- Trailing: structural trail activates after profit exceeds 1× ATR

**Candle timeframe:** 5m  
**Asset:** Stocks only (requires defined market open)  
**Whitelist:** ORB_WHITELIST 15-symbol list from April 2026 backtest pass/fail

**Known fix required (Phase 8b):** `_get_orb_levels()` falls back to `candles.iloc[:3]` silently when the bar index has no `.hour` attribute. Fix: return `None, None` with a logged warning instead of silently using potentially wrong bars.

---

### Mode D — Volatility Breakout (5m/1h, both assets)
*Current implementation: Bollinger Breakout*

Breakout from a Bollinger Band squeeze. Not regime-dependent — a breakout from consolidation is its own regime signal. Unlike Mode C (scheduled session breakout), this fires whenever price escapes a compression zone.

**Entry (long):**
1. Symbol not on Bollinger Breakout blacklist
2. BB squeeze detected (band width below `bb_squeeze_threshold`)
3. Close breaks above upper BB (breakout bar, not just wick)
4. OBV trending up (volume confirming breakout, not fakeout)
5. Price above EMA50 (breakout in the direction of primary trend)
6. RSI not overbought (< 65 for long)

**Entry (short):** Mirror of above.

**Exit:**
- Stop: two-bar structural stop
- Take profit: 3.0% default (no ATR adaptation in current implementation; add in redesign)
- Time stop: 4 hours
- Trailing: structural trail

**Candle timeframe:** 5m (stocks), 1h (crypto)  
**Asset:** Both. Crypto requires Phase 5 re-validation: 0.62% round-trip must be justified by average gross profit.  
**Whitelist:** Current blacklists remain. Positive selection (whitelist) preferred over negative selection (blacklist) — to be addressed in Phase 8b.  
**Exemption removal:** Remove `auto_disable_exempt=True` and `ml_exempt=True`. These were not design decisions.

---

## 4. Engine 2 — Range/Reversion Engine

**Thesis:** In a ranging market, price oscillates around a mean. Buy near the lower bound, sell near the upper bound (or mean). The trade fails fast if price doesn't return within a defined window.

**Regime:** Ranging only for Modes A and B. Mode C (Extreme Reversal) fires in any regime because it is self-gating via extreme conditions.  
**Asset scope:** Tight whitelists only. Mean reversion on arbitrary symbols is noise.

---

### Mode A — Bollinger Band Range (1h)
*Current implementation: Grid Bot*

**Entry (long — near lower band in ranging market):**
1. Symbol in range whitelist
2. ADX < 20 (ranging confirmed at engine level AND strategy level)
3. Price within bottom 20% of BB band (near lower band, not just below midline)
4. BB band width above minimum (if bands are too narrow, the "range" is a squeeze → skip; let Mode D handle it)
5. RSI < 50 (price in lower half of oscillator range)
6. Volume NOT spiking (a volume spike in a range usually signals a breakout, not a bounce)

**Entry (short — near upper band):** Mirror of above. RSI > 50, volume not spiking.

**Exit:**
- Stop: two-bar structural stop (tighter, because range trades have a clear thesis)
- Take profit: opposite BB band (midline as first target; full opposite band as second)
- Time stop: 2 hours (shorter than momentum — if it hasn't bounced, the range is breaking)
- Trailing: NOT used. Range trades target the opposite band as a fixed exit. Structural trail would move the stop in the wrong direction for a reversion thesis.

**Candle timeframe:** 1h  
**Whitelist:** ~15 instruments verified to be range-bound (see Section 4.4)  
**Exemption removal:** Grid Bot's `reviewer_exempt=True`, `ml_exempt=True`, `auto_disable_exempt=True` are removed by fixing the missing indicator metadata.

---

### Mode B — Z-Score Reversion (5m or 1h)
*Current implementation: Mean Reversion*

**Entry (long — below mean):**
1. Symbol in range whitelist
2. ADX < 20 (ranging)
3. Z-score ≤ -1.5 standard deviations from rolling mean (price statistically low)
4. Price not in a new structural downtrend (EMA50 not sharply declining)
5. RSI < 40 (confirming oversold without requiring RSI < 30 extreme)
6. Volume normal or below average (no distribution on the move down)

**Entry (short — above mean):** Z-score ≥ +1.5, RSI > 60, volume normal.

**Exit:**
- Stop: two-bar structural stop
- Take profit: z-score return to -0.5 standard deviations from mean (partial reversion, not full)
- Time stop: 3 hours (5m) / 6 hours (1h)
- Trailing: NOT used (reversion targets a fixed mean, not an open-ended trend)

**Candle timeframe:** Configurable per symbol (5m for higher-frequency instruments, 1h for lower-frequency)  
**Whitelist:** Same 15-instrument range whitelist as Mode A

---

### Mode C — Extreme Reversal (5m, crypto)
*Current implementation: Hammer Reversal*

**Regime note:** Mode C fires in ANY regime classification because the five simultaneous conditions (RSI < 30 + Stochastic < 20 + below lower BB + hammer candle + OBV rising) constitute their own regime signal. Requiring all five simultaneously is self-gating: in a trending down market, OBV will not be rising even if RSI is oversold. The regime gate does not suppress Mode C.

**Entry (long only — longs only, no short mirror):**
1. Symbol in reversal whitelist (SOL/USD only initially)
2. RSI(14) < 30 (oversold)
3. Stochastic slowK(14) < 20 (confirming oversold on a different oscillator)
4. Close < lower Bollinger Band (price statistically extreme below mean)
5. Hammer candlestick detected (body ≤ 30% of range, upper shadow ≤ 10% range, lower shadow ≥ 2× body, body in upper 40% of bar)
6. OBV rising for last 3 consecutive bars (buyers absorbing sell pressure)

All six must be true. No score-based entry — this is binary.

**Exit:**
- Stop: two-bar structural stop. Given the hammer entry point (already near the low), this will naturally place the stop just below the recent structural low, which is the correct invalidation.
- Take profit: tiered ROI ladder (currently in signal metadata but NOT implemented in position_monitor):
  - Bars 0-19: exit at +5.0%
  - Bars 20-29: exit at +4.0%
  - Bars 30-59: exit at +3.0%
  - Bars 60+: exit at +1.0% (kill switch — take any profit and exit)
- **This ladder must be implemented in position_monitor as part of Phase 8b. Until it is, the TP is fixed at 5.0% (no degradation). The dead metadata must either become live code or be removed before this strategy runs again.**
- Time stop: 24 hours (crypto reversal — no intraday session constraint)
- Trailing: NOT used until profit exceeds the first tier threshold (5%). Once a tiered TP fires, position is exited entirely.

**Candle timeframe:** 5m  
**Asset:** Crypto only  
**Whitelist:** SOL/USD (SOL/USDT) only. BTC/USD reinstatement pending: SOL must show WR ≥ 55% over ≥ 20 live trades.

---

### 4.4 Range Whitelist — Selection Criteria

The ~80-symbol Mean Reversion whitelist is trimmed to ~15 instruments. Selection criteria:

1. **Demonstrated range-bound behavior:** rolling 30-day ADX should average < 20 more often than not. Instruments with long trending periods are excluded even if they occasionally range.
2. **Sufficient liquidity:** fills must not move the market. Volume floor: ≥ $10M daily dollar volume.
3. **No binary event risk in backtest window:** exclude stocks during earnings, crypto during protocol upgrade windows.
4. **Category diversity:** include at least one ETF (SPY, QQQ, IWM), at least one blue-chip stock, at least one crypto pair.

Proposed seed whitelist (to be validated by Phase 5 backtest before enabling):

| Symbol | Type | Rationale |
|---|---|---|
| SPY | ETF | Highly liquid; oscillates around daily VWAP frequently |
| QQQ | ETF | Similar to SPY |
| IWM | ETF | Small-cap index, tighter ranges |
| GLD | ETF | Gold; long-running oscillating tendency |
| MSFT | Stock | Mega-cap; often ranges between earnings |
| AAPL | Stock | Mega-cap; similar |
| JPM | Stock | Large-cap bank; ranges between macro events |
| BAC | Stock | Similar to JPM |
| BTC/USD | Crypto | Ranges between breakouts; liquid enough for z-score |
| ETH/USD | Crypto | Similar to BTC |

Final list must be confirmed by backtesting with Phase 5 friction enabled. Starting smaller (10) is safer than starting at 80.

---

## 5. Support Utility — DipBuy (1h, stocks, blue-chip)
*Current implementation: DCA Accumulator (renamed)*

**Not an engine in the regime gate sense.** This fires in any regime because the conditions themselves confirm the setup (uptrend + pullback).

**Entry (long only):**
1. Symbol in blue-chip whitelist
2. Price above EMA50 (primary uptrend intact)
3. Current close < previous close (pullback in progress)
4. RSI < 45 (dip — not just a pause in a parabolic move)
5. RSI not below 25 (if RSI < 25 this is a breakdown, not a dip — skip)
6. ADX < 35 (if trend is very strong, the "dip" may be structural; skip)

**Exit:**
- Stop: two-bar structural stop (1h bars)
- Take profit: 3.0% (fixed; blue-chip dips don't need ATR adaptation)
- Time stop: 48 hours (dip buy needs room; held through the session)
- Trailing: structural trail on 1h bars

**Naming:** Rename class from `DCAAccumulator` to `DipBuyEntry`. Update `strategy_name` attribute to `"dip_buy"`. Add docstring clarification that this is a single entry per signal, not staged DCA. If staged accumulation is desired later, it requires explicit implementation, not just a name implication.

**Asset:** Stocks only  
**Whitelist:** Current DCA blue-chip whitelist (AAPL, MSFT, GOOGL, AMZN, NVDA, META, etc.)

---

## 6. Filter / Veto Layer

**File to create:** `strategies/filters.py`  
**Pattern:** Pure functions, no state, no database access. Each function takes a small set of inputs and returns a bool (True = vetoed, blocked) or a float (metric value).

### 6.1 Veto Functions

```
rsi_hard_block(rsi: float, direction: str) -> bool
    Returns True (block) if:
    - direction == "long" and rsi > 82
    - direction == "short" and rsi < 18
    Learned from IONQ at RSI 98. Applied universally across all engines.

adx_trending(adx: float, threshold: float = 20) -> bool
    Returns True if adx >= threshold (market is trending).

adx_ranging(adx: float, threshold: float = 20) -> bool
    Returns True if adx < threshold (market is ranging).

ema_stack_aligned(e_fast, e_mid, e_slow, direction: str) -> bool
    Returns True if EMA stack is bullish (long) or bearish (short).
    Bullish: e_fast > e_mid > e_slow
    Bearish: e_fast < e_mid < e_slow

volume_conviction(current_vol: float, avg_vol: float, min_ratio: float = 1.5) -> bool
    Returns True if current_vol / avg_vol >= min_ratio and avg_vol > 0.

volume_spike(current_vol: float, avg_vol: float, spike_ratio: float = 1.5) -> bool
    Returns True if volume is spiking. Used as a NEGATIVE filter in range strategies
    (spike in a range = possible breakout → skip range entry).

bb_squeeze(band_width: float, threshold: float = 0.04) -> bool
    Returns True if band_width < threshold (Bollinger squeeze detected).

vwap_bias(price: float, vwap: float, direction: str) -> bool
    Returns True if price is on the correct side of VWAP for the signal direction.
    Long: price > vwap. Short: price < vwap.

hammer_candle(open_, high, low, close) -> bool
    Returns True if the bar is a hammer pattern:
    body ≤ 30% of range, upper shadow ≤ 10% of range,
    lower shadow ≥ 2× body, body in upper 40% of bar.
    (Extracted from HammerReversal._detect_hammer)

orb_range_valid(orb_high, orb_low, min_range_pct: float = 0.003) -> bool
    Returns True if the opening range is wide enough to be meaningful.
```

### 6.2 Metric Functions

```
calc_vwap(candles: DataFrame) -> Optional[float]
    Intraday VWAP from available bars. Currently duplicated in
    vwap_momentum.py and orb_breakout.py — merge here.

calc_adx(candles: DataFrame, period: int = 14) -> Optional[float]
    ADX from pandas_ta. Currently duplicated in multiple strategies.

calc_zscore(series: Series, period: int = 20) -> Optional[float]
    Z-score of current value relative to rolling mean and std.

calc_obv(closes: Series, volumes: Series) -> Series
    On-balance volume. Extracted from HammerReversal._calc_obv.

calc_atr(candles: DataFrame, period: int = 14) -> Optional[float]
    ATR from pandas_ta. Currently only in ORBBreakout.
```

### 6.3 Application Pattern

Engines call filter functions in a standard order:
1. Whitelist check (fastest — database lookup)
2. Regime gate pass-through (already determined; just check)
3. RSI hard block (scalar check — near-zero cost)
4. ADX check (already computed for regime gate; reuse value)
5. Indicator computation (EMA, BB, VWAP, volume — heavier)
6. Entry condition evaluation
7. Score computation and threshold check

Failing any earlier step short-circuits the remaining steps. This ordering minimizes unnecessary computation on the majority of symbols that will be rejected early.

---

## 7. Risk Controls

### 7.1 Position Sizing — Per Engine

The current `MAX_POSITION_PCT = 2.0` applies universally. The redesign differentiates by engine based on stop width and conviction level:

| Engine | Position Size | Rationale |
|---|---|---|
| Momentum Mode A (Scalp) | 1.5-2.0% | Tight structural stop; 5m granularity; per-symbol adaptive TP |
| Momentum Mode B (Swing) | 1.0-1.5% | Wider stop on 1h bars; fewer open simultaneously |
| Momentum Mode C (ORB) | 1.0-2.0% | Stop at ORB opposite side = known max loss; size accordingly |
| Momentum Mode D (BB Breakout) | 1.0-1.5% | Breakouts can fail fast; conservative until validated |
| Range Mode A (BB Range) | 0.75-1.0% | Range trades have lower conviction per entry |
| Range Mode B (Z-Score) | 0.75-1.0% | Same reasoning |
| Range Mode C (Hammer) | 0.5-1.0% | Wide stop (10%); size small to limit absolute risk |
| DipBuy | 1.0-1.5% | Blue-chip names; lower volatility than momentum plays |

### 7.2 Crypto Position Reduction

Because crypto round-trip costs are 0.62% vs. stocks at 0.02%, the same position size in crypto commits proportionally more of its gross profit to friction. Apply a 0.5× multiplier to all crypto positions relative to stock positions at the same engine mode. This is not a config change — it is a sizing rule in the risk manager that checks `asset_class == "crypto"`.

Example: If Mode A stock sizing is 1.5%, Mode A crypto sizing is 0.75%.

### 7.3 Circuit Breakers (unchanged from current config)

These apply across all engines with no per-engine override:

| Breaker | Value |
|---|---|
| Max daily loss | 15.0% (`MAX_DAILY_LOSS_PCT`) |
| Max consecutive losses | 10 (`MAX_CONSECUTIVE_LOSSES`) |
| Max open positions | 30 (`MAX_OPEN_POSITIONS`) |
| Min signal confidence | 0.65 (`MIN_SIGNAL_CONFIDENCE`) |

### 7.4 Per-Engine Concurrent Position Limits (proposed new config)

To prevent one engine from consuming all available position slots:

| Engine | Max concurrent positions |
|---|---|
| Momentum (all modes) | 15 |
| Range/Reversion (all modes) | 8 |
| DipBuy | 5 |
| Total (shared ceiling) | 30 (existing config) |

These limits enforce that a trending day with many momentum signals cannot crowd out range capacity, and vice versa.

---

## 8. Exit Logic — Unified Specification

All engines use the same exit framework. Per-engine differences are in parameter values, not in architecture.

### 8.1 Stop Loss

**All engines:** Two-bar structural stop (Phase 3 `stop_engine.py`).

Exception — Momentum Mode C (ORB): the stop is placed at the opposite ORB level (ORB low for longs, ORB high for shorts). This is a thesis-based structural stop that is fixed at entry, not trailing. The two-bar engine does not apply at ORB open because the ORB levels define the natural invalidation. After the first trailing trigger fires, the structural trail takes over.

### 8.2 Take Profit

| Engine Mode | TP Logic |
|---|---|
| Momentum A (Scalp) | Per-symbol adaptive (symbol_params.json); default 3.0% |
| Momentum B (Swing) | ATR-based: 2× ATR, clamped 2-8% |
| Momentum C (ORB) | ATR-based: 2× ATR, clamped 1-8% |
| Momentum D (BB Breakout) | ATR-based: add in redesign (currently fixed 3%); clamped 1.5-6% |
| Range A (BB Range) | Midline of BB (first target); opposite band (second target) |
| Range B (Z-Score) | Z-score of -0.5 (not full return to 0; partial reversion is safer) |
| Range C (Hammer/Reversal) | Tiered ROI ladder: 5% → 4% → 3% → 1% (must be implemented) |
| DipBuy | Fixed 3.0% |

### 8.3 Time Stops

| Engine Mode | Time Stop | Notes |
|---|---|---|
| Momentum A (Scalp) | 3.5 hours | `HARD_TIME_STOP_HOURS` |
| Momentum B — B1 VWAP | 90 minutes | Intraday swing; clock from entry |
| Momentum B — B2 Swing | 6 hours | Swing allows more room |
| Momentum C (ORB) | Market close | No overnight ORB positions |
| Momentum D (BB Breakout) | 4 hours | Current implementation |
| Range A (BB Range) | 2 hours | Short — range thesis fails fast or not at all |
| Range B (Z-Score) | 3h (5m) / 6h (1h) | Timeframe-dependent |
| Range C (Hammer) | 24 hours | Crypto; no session constraint |
| DipBuy | 48 hours | Held through the session and next open |

### 8.4 Performance Time Stop

The existing `PERF_TIME_STOP_ENABLED` with 1hr and 3hr gates applies to Momentum Modes A and B. It does not apply to Range modes (range trades can look negative briefly before reverting — penalizing unrealized drawdown at 1hr would close range entries too early) or to Hammer Reversal (wide stop, infrequent entry, patience required). DipBuy should also skip the performance gate at 1hr — a 48hr holding period means the position needs room.

### 8.5 Trailing Stop

**Momentum A, B, D:** Structural trail activates after the first closed bar moves the stop in the profit direction. Uses `entry_timeframe` bars (Phase 4 behavior preserved).

**Momentum C (ORB):** Structural trail activates after profit exceeds 1× ATR (give the initial ORB move room before tightening).

**Range A and B:** No trailing stop. Range trades target a fixed exit (opposite band or mean return). Trailing in a range strategy creates asymmetric exit behavior — profits trail up but losses have a fixed stop, which can turn a correctly-identified range trade into an unintended trend trade.

**Range C (Hammer):** No trailing. Tiered TP ladder is the exit mechanism.

**DipBuy:** Structural trail on 1h bars.

---

## 9. Migration Path

### 9.1 File Disposition — Complete Map

| Current File | Status | Action |
|---|---|---|
| `strategies/rsi_momentum.py` | **DELETE** | No migration. Remove from `strategy_engine.py` registry. |
| `strategies/ema_crossover.py` | **RETIRE** | Disable (`self.enabled = False`). Extract EMA alignment logic to `filters.py`. Delete class after filter layer is verified. |
| `strategies/grid_bot.py` | **ABSORB** | Mode A of new `range_engine.py`. File retired after merge is verified. |
| `strategies/mean_reversion.py` | **ABSORB** | Mode B of new `range_engine.py`. File retired after merge. Whitelist trimmed from ~80 to ~15. |
| `strategies/scalp_master.py` | **KEEP** | Becomes canonical Momentum Mode A. Refactor internal VWAP/ADX calls to use `filters.py`. |
| `strategies/bollinger_breakout.py` | **KEEP** | Becomes Momentum Mode D. Remove `auto_disable_exempt` and `ml_exempt`. Refactor internal functions to use `filters.py`. |
| `strategies/swing_trader.py` | **KEEP** | Becomes Momentum Mode B sub-type B2. Keep disabled until Phase 5 backtest. |
| `strategies/dca_accumulator.py` | **KEEP (rename)** | Rename class to `DipBuyEntry`, `strategy_name` to `"dip_buy"`. Update docstring to remove DCA implication. |
| `strategies/vwap_momentum.py` | **KEEP** | Becomes Momentum Mode B sub-type B1. Add explicit `self.enabled = False`. Refactor VWAP/ADX to `filters.py`. |
| `strategies/hammer_reversal.py` | **KEEP (fix)** | Becomes Range Mode C. Implement tiered ROI ladder in position_monitor or remove dead metadata. |
| `strategies/orb_breakout.py` | **KEEP (fix)** | Becomes Momentum Mode C. Fix `_get_orb_levels()` fallback. Keep `self.enabled = False` until Phase 5 backtest. |

### 9.2 New Files

| File | Purpose |
|---|---|
| `strategies/filters.py` | Shared veto functions and metric helpers. No state, no DB access. |
| `strategies/range_engine.py` | Unified range/reversion engine. Modes A (BB) and B (z-score). Replaces `grid_bot.py` and `mean_reversion.py`. |

### 9.3 Modified Files

| File | Change |
|---|---|
| `strategies/strategy_engine.py` | Add `range_engine.py` to registry. Remove `rsi_momentum.py`. Remove `ema_crossover.py` after filter extraction. Update Grid Bot and Mean Reversion references. |
| `core/position_monitor.py` | Implement tiered ROI ladder (Hammer Reversal Mode C). Read `roi_ladder` from trade metadata and apply to TP logic. |
| `config.py` | Add per-engine position sizing defaults. Add per-engine time stop values (currently only `HARD_TIME_STOP_HOURS` exists globally). |

### 9.4 Unchanged Files (this phase)

`core/stop_engine.py`, `core/risk_manager.py`, `core/trade_executor.py`, `core/database.py`, `intelligence/backtester.py`, all scanner files, all broker files. The hard gate items (ISSUE-19, stale structural stop) are handled in Phase 8a, independently.

---

## 10. Phase Execution Order

If this plan is approved, implementation sequence:

### Phase 8a — Hard Gate Items (independent, no strategy code)
1. ISSUE-19: Rewrite `startup_reconciler._reconcile_crypto()` to query Kraken (not Coinbase)
2. Stale structural stop at execution: recompute `initial_stop_from_tail()` in `trade_executor` after broker fill
3. ISSUE-17: CoinbaseExecutor rename
4. ISSUE-18: Duplicate cooldown block removal in `risk_manager`
5. ISSUE-15/16: Stale 3.5hr docstring corrections in `position_monitor`

### Phase 8b — Strategy File Surgery (no architecture changes)
1. Remove `rsi_momentum.py` from registry and delete
2. Add `self.enabled = False` to `VWAPMomentum.__init__()`
3. Fix `orb_breakout._get_orb_levels()` silent fallback
4. Fix Grid Bot metadata (add missing standard indicator fields) → remove all 3 exemptions
5. Resolve Hammer Reversal ROI ladder: implement in `position_monitor` or remove dead metadata

### Phase 8c — Filter Layer
1. Create `strategies/filters.py` with all functions from Section 6
2. Extract `_calc_vwap()` from `vwap_momentum.py` and `orb_breakout.py` → use `filters.calc_vwap()`
3. Update calling strategies to use `filters.*` functions (no behavior change, DRY refactor)
4. Verify tests pass (if any); verify strategies still signal correctly on a paper scan

### Phase 8d — Range Engine Consolidation
1. Create `strategies/range_engine.py` (Modes A and B from Grid Bot + Mean Reversion)
2. Whitelist trimmed to ~15 instruments from Section 4.4
3. All 3 exemptions absent from new file (exemptions were metadata workarounds, not design decisions)
4. Register `range_engine.py` in `strategy_engine.py`
5. Disable `grid_bot.py` (`self.enabled = False`) — do not delete yet
6. Disable `mean_reversion.py` (`self.enabled = False`) — do not delete yet
7. Run 48-hour paper comparison: confirm range_engine produces similar or identical signals to what grid_bot + mean_reversion produced on the same symbols
8. Delete retired files after comparison is confirmed

### Phase 8e — Regime Gate Wire-up
1. Add regime classification (ADX-based) to scanner's per-symbol scan loop
2. Pass `market_condition` with `"trending"` / `"ranging"` / `"unknown"` (existing parameter name)
3. Enforce Range Engine skip on Unknown (add check at top of `range_engine.analyze()`)
4. Each Momentum Engine strategy retains its own internal ADX check (defense in depth)
5. Log regime classification per symbol per scan at DEBUG level

### Phase 8f — DipBuy Rename
1. Rename `DCAAccumulator` → `DipBuyEntry`; update `strategy_name`
2. Update `strategy_engine.py` registry
3. Update any logging or reporting that references `dca_accumulator`

### Phase 8g — Backtest Validation Gate
Rerun with Phase 5 friction for each newly enabled or unvalidated strategy. No code changes — results gate enable/disable decisions.

| Strategy | Validation Required Before Enable |
|---|---|
| Scalp Master (stock) | Re-run with Phase 3+5 engine. Verify positive expectancy after friction. |
| Scalp Master (crypto) | Individual pair validation. Any pair averaging < 0.80% gross = disable that pair. |
| Bollinger Breakout (crypto) | Phase 5 re-run. If negative expectancy after 0.62% round-trip, disable crypto side permanently. |
| VWAP Momentum | Phase 5 backtest. Enable only after confirmed positive expectancy per symbol. |
| ORB Breakout | Phase 5 backtest. Verify ORB level detection with real timestamp data before live. |
| Swing Trader | Phase 3+5 backtest. Enable only after confirmed positive expectancy. |
| Range Engine | Phase 5 backtest per whitelist symbol. Enable only for symbols showing confirmed range-bound behavior. |

---

## 11. Acceptance Criteria

| # | Criterion | Verified By |
|---|---|---|
| 1 | RSI Momentum removed from registry and codebase | No RSI Momentum signals in paper logs |
| 2 | EMA Crossover extracted to filter layer; not generating standalone entries | No EMA Crossover signals in paper logs |
| 3 | Grid Bot and Mean Reversion absorbed into range_engine.py; retired files disabled | range_engine generates equivalent signals on identical inputs |
| 4 | Grid Bot exemptions (reviewer, ML, auto-disable) removed | Strategy metadata passes reviewer; ML scorer processes it; auto-disable active |
| 5 | Hammer Reversal ROI ladder implemented or explicitly removed | position_monitor either executes tiered exits or metadata field is absent |
| 6 | ORB `_get_orb_levels()` returns None on timestamp failure, not silent fallback | Log warning visible; no incorrect ORB levels in signals |
| 7 | VWAP Momentum has explicit `self.enabled = False` | Strategy never activates without manual enable |
| 8 | DipBuy renamed; docstring clarifies single-entry behavior | `strategy_name == "dip_buy"` in all trade records; no DCA staging implication |
| 9 | `strategies/filters.py` exists with all functions from Section 6 | At least two strategies import from it (not duplicating locally) |
| 10 | Regime gate produces "trending" / "ranging" / "unknown" per symbol per scan | Logs show regime classification; Range Engine logs skip on unknown |
| 11 | Range Engine skips on unknown regime; Momentum Engine still routes | Confirmed by scan logs on a mixed symbol set |
| 12 | Per-engine concurrent position limits enforced | Max 15 momentum + 8 range + 5 dipbuy never exceeds 30 total |
| 13 | Crypto position sizing 0.5× relative to stock at same engine mode | Verified in risk_manager sizing output |
| 14 | All Phase 5 backtest re-runs completed before any newly enabled strategy goes live | Backtest results document exists per strategy per asset class |
| 15 | CLAUDE_REBUILD_BRIEF.md acceptance standard met: same strategy in backtest, paper, and live | Stated explicitly in updated VERIFICATION_REPORT.md |

---

*Awaiting explicit approval before any Phase 8 implementation begins.*  
*Phase 8a (hard gate items) may be approved and started independently of this redesign plan.*
