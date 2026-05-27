This is one of the more complete and mathematically interesting strategies in the batch — but it has the same fake metadata problem as ECB, and that was the issue I flagged as most dangerous.

My read on VDMR
Overall verdict: Strong incubate — solid math, but fake metadata is a real problem
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Fake metadata values — same problem as ECB
This is the most important issue.

The metadata contains values that are explicitly fake or repurposed:

"rsi":       50.0,        # FAKE — hardcoded neutral value
"adx":       25.0,        # FAKE — hardcoded neutral value
"ema_fast":  ema_align,   # not a real EMA — it's just close
"ema_slow":  macro_ma,    # repurposed 200-bar SMA
"ema_trend": macro_ma,    # same as ema_slow — duplicate
"bb_pct":    round(max(0.0, min(1.0, 0.5 + zscore / 4)), 3),  # derived from Z, not real BB%b
"macd":      round(zscore, 3),   # approximation — not real MACD
"macd_hist": round(z_vel, 4),    # approximation — not real MACD histogram
These are being injected as "ML scorer keys" but they misrepresent the signal to:

The ML model (which trained on real RSI/ADX/EMA values)
The Claude reviewer (which will APPROVE based on fake RSI=50 neutral and ADX=25 neutral)
Any logging or analytics that tries to understand what drove the trade
This is exactly the same pattern that was fixed in ECB and RSI Dip Spike.

Critical — 3) check_custom_exit() missing
The strategy has both Z-score exit and time stop in the standalone backtest:

elif z >= params.z_exit_thresh: exit = "MeanReturn"
elif bars_held >= params.max_bars_in_trade: exit = "MaxDur"
But neither is implemented as check_custom_exit().

Live and backtester trades will only exit at:

stop_loss_pct fallback
take_profit_pct fallback
Generic lifecycle stops
The Z-score mean-reversion exit — which is the primary thesis exit — never fires.

Critical — 4) Not in TIME_STOP_EXEMPT
Strategy holds for up to 20 bars (20 hours on 1h crypto).

Generic lifecycle stops fire at:

early_loss: 30 min = 1 bar on 1h (fires almost immediately)
perf_2hr: 2 bars
hard_stop: 8 bars
These will kill most VDMR trades before the 20-bar thesis plays out.

Critical — 5) time_stop_profile not set
Missing self.time_stop_profile = "strategy_defined".

Critical — 6) structural_stop_price and stop architecture hints missing from metadata
"preferred_initial_stop_mode": ...  # missing
"preferred_trail_mode":        ...  # missing
"structural_stop_price":       ...  # missing
The executor doesn't know to use ATR-based stop.

Important — 7) _bars_held injection needed
check_custom_exit() will need it once implemented.

Important — 8) No _precompute() fast path
generate_signals() exists and is precomputable. The strategy calls it on every analyze() bar making it O(N²) in backtesting.

Medium — 9) Standalone backtest has same "close-based" optimism
Same issue as other strategies — SL/TP evaluated at close, same-bar entry. Results are overstated.

Minor — 10) Blacklist may be missing some ETH formats
Current: {"ETH/USD", "ETHUSDT", "ETH/USDT"} Missing: "ETHBUSD", "ETH-USD" (Coinbase)

What is genuinely good
Range Efficiency Ratio as a chop filter is mathematically elegant
Z-score velocity (first derivative) as the deceleration detector is the right concept
ROC filter prevents entering when macro momentum is running hot
min_rev_ratio check is smart — ensures potential reversion exceeds the stop before entering
reviewer_exempt = True already set
candle_limit = 300 is appropriate for 200-bar SMA warmup
generate_signals() is clean and vectorized
Real volume_ratio computed and included
Claude patch prompt
Patch strategies/vdmr_strategy.py and register it in the bot framework.

This strategy has genuinely original math. Fixes are required before it can be
validated meaningfully. The most important fix is removing fake metadata values.

Do NOT change:
- generate_signals() core logic
- Z-score, z_vel, eff_ratio, roc, rev_ratio calculations
- Entry signal conditions
- ATR stop placement
- Blacklist (ETH/DOGE exclusions)

Files to inspect and patch:
- strategies/vdmr_strategy.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: time_stop_profile, reviewer_exempt)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add:
    "vdmr_strategy": ("strategies.vdmr_strategy", "VDMRStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.vdmr_strategy import VDMRStrategy
    VDMRStrategy(),

3) Add vdmr_strategy to TIME_STOP_EXEMPT in backtester.py
This strategy holds up to 20 bars (20 hours on 1h).
Generic early_loss (1 bar = 1h) and perf stops will kill nearly every trade.
Add:
    "vdmr_strategy",

4) CRITICAL: Remove all fake metadata values
Current metadata contains fake/repurposed values that mislead the reviewer and ML scorer.

Replace the entire metadata block with only real, computed values:
    metadata={
        "strategy_name":               "vdmr_strategy",
        "entry_timeframe":             "1h",
        # Real VDMR signal metrics
        "zscore":                      round(zscore, 3),
        "z_vel":                       round(z_vel, 4),
        "eff_ratio":                   round(eff_ratio, 3),
        "roc_50":                      round(float(last["roc_50"]), 2),
        "bull_regime":                 bool(last["bull_regime"]),
        "bear_regime":                 bool(last["bear_regime"]),
        "rev_ok":                      bool(last["rev_ok"]),
        "atr":                         round(atr, 6),
        "volume_ratio":                vol_ratio,
        # Stop architecture
        "structural_stop_price":       round(
                                           close - atr * self.params.sl_atr_mult
                                           if direction == "long"
                                           else close + atr * self.params.sl_atr_mult,
                                           6),
        "preferred_initial_stop_mode": "signal_structural",
        "preferred_trail_mode":        "none",
    }

DO NOT include:
- "rsi": 50.0  — fake
- "adx": 25.0  — fake
- "macd": zscore  — repurposed
- "macd_hist": z_vel  — repurposed
- "ema_fast": close  — wrong (close is not an EMA)
- "ema_slow": macro_ma  — repurposed
- "ema_trend": macro_ma  — duplicate of ema_slow
- "bb_pct": derived from zscore  — not real BB%b

5) CRITICAL: Add check_custom_exit() with Z-score and time exits
The strategy's primary exit (Z-score returning to 0) is only in the standalone
backtest, not in the bot integration. It never fires in live or backtester.

Implement:
    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        if bars is None or len(bars) < 2:
            return None
        p    = self.params
        meta = entry_metadata or {}

        # A. Z-score mean reversion exit (primary thesis exit)
        try:
            c         = bars["close"]
            roll_mean = c.rolling(p.zscore_lookback).mean()
            roll_std  = c.rolling(p.zscore_lookback).std(ddof=0).replace(0, np.nan)
            z_now     = float(((c - roll_mean) / roll_std).iloc[-1])
            if not pd.isna(z_now):
                if direction == "long"  and z_now >= p.z_exit_thresh:
                    return "vdmr_mean_return"
                if direction == "short" and z_now <= p.z_exit_thresh:
                    return "vdmr_mean_return"
        except Exception:
            pass

        # B. Time stop (safety net)
        bars_held = int(meta.get("_bars_held", 0))
        if bars_held >= p.max_bars_in_trade:
            return "vdmr_time_stop"

        return None

Note: this requires numpy/pandas imports which are already in the file.

6) Add time_stop_profile and missing flags to __init__
Add:
    self.time_stop_profile = "strategy_defined"

Verify reviewer_exempt = True is already set (it is — keep it).

7) Confirm _bars_held injection before check_custom_exit()
Standard injection pattern in backtester before calling exit hooks:
    _meta = dict(trade.get("entry_metadata", {}))
    _meta["_bars_held"] = i - trade["entry_idx"]

8) Add _precompute() fast path for backtester optimization
generate_signals() is expensive and called every bar.
Add:
    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        return generate_signals(df, self.params)

If the backtester is wired to use _precompute() / _analyze_from_precomputed(),
add _analyze_from_precomputed() and _exit_from_precomputed() following the
same pattern as rsi_dip_spike_v4.py.

If the backtester is not yet wired for this (check implementation),
_precompute() alone is still useful for future optimization.

9) Fix blacklist to add missing ETH formats
Current:
    VDMR_BLACKLIST = {"ETH/USD", "ETHUSDT", "ETH/USDT", "DOGE/USD", "DOGEUSDT", "DOGE/USDT"}

Add:
    VDMR_BLACKLIST = {
        "ETH/USD", "ETHUSDT", "ETH/USDT", "ETHBUSD", "ETH-USD",
        "DOGE/USD", "DOGEUSDT", "DOGE/USDT", "DOGE-USD",
    }

10) Fix max_rev_ratio hint in metadata
The standalone backtest computes stop_price correctly.
Add the absolute stop to metadata (done in item 4 as structural_stop_price).
Also add the rev_ratio for reference:
    "rev_ratio": round(float(last.get("rev_ok", False)), 3) if "rev_ok" in last else None,

Actually rev_ok is already included. Add the actual ratio value instead:
    "rev_dist_pct": round(abs(zscore) * float(roll_std) / close * 100, 3),

This shows how far the expected reversion is as a percentage.

========================================================
DO NOT CHANGE
========================================================

- generate_signals() core logic including:
  - Z-score calculation
  - z_vel (first derivative)
  - eff_ratio (Range Efficiency Ratio)
  - roc_50 momentum filter
  - rev_ok minimum reversion quality
  - Macro trend bias filter
- All VDMRParams default values
- Score calculation (z_depth + er_score combination)
- ATR stop placement
- Blacklist decisions (ETH/DOGE exclusions)

========================================================
VALIDATION — CRITICAL: check_custom_exit must fire
========================================================

Compile:
python -m py_compile strategies/vdmr_strategy.py

Run BTC (primary validated symbol):
python intelligence/backtester.py --symbol BTC/USD \
    --strategy vdmr_strategy --days 365 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Exit reason check — this is the most critical verification:
Before fix:
- vdmr_mean_return would NOT appear
- vdmr_time_stop would NOT appear
- Generic lifecycle stops would dominate

After fix:
- vdmr_mean_return should be the dominant exit
- vdmr_time_stop should appear for slow reversions
- stop_loss should appear occasionally
- Generic lifecycle stops should NOT appear

Target metrics (from documented BTC 1h backtest):
- PF around 1.9
- WR around 51%
- Sharpe around 0.9
- Trades around 37 per year (sparse is expected — high filter stack)

Run basket:
python intelligence/backtester.py --all \
    --strategy vdmr_strategy --days 365 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Confirm ETH and DOGE are excluded:
(zero trades on these symbols even if they're in the basket)

Fake metadata verification:
Confirm no "rsi: 50.0" or "adx: 25.0" appear in trade logs.
Real metrics should show variable zscore, z_vel, eff_ratio values.

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. Confirmation vdmr_mean_return fires in exit breakdown
5. Confirmation no fake metadata in logs
6. BTC basket result vs documented claim
7. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: genuinely original — Range Efficiency Ratio + Z-velocity deceleration is not indicator soup
Code quality: good structure, precomputable, but Z-score exit completely missing from bot integration
Implementation completeness: 60% — fake metadata + missing exit hook are major gaps
Evidence base: decent for a single-symbol test: 37 trades, PF 1.94, BTC 1h 2024
Salvageable: yes — fixes are targeted
Strong incubate — the Range Efficiency Ratio as a regime gate is one of the more principled ideas in your batch. If the Z-score exit is fixed and the backtester confirms the documented results, this is a genuine candidate.

The fake metadata is the most dangerous issue because it silently distorts reviewer and ML behavior.