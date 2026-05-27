My read on EMA Ribbon Breakout
Overall verdict: Strong incubate — almost identical issues to BTC V6 Chandelier
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
Same pattern.

Critical — 3) _bars_held injection needed
Same pattern.

Critical — 4) structural_stop_price missing from metadata
Exact same issue as BTC V6 Chandelier.

Metadata says:

"preferred_initial_stop_mode": "signal_structural",
"preferred_trail_mode":        "chandelier",
But no structural_stop_price key.

The executor reads structural_stop_price — not finding it, falls back to percent stop.

Initial chandelier position:

chan_dist = atr * p.atr_mult
Absolute stop price should be:

Long: close - chan_dist
Short: close + chan_dist
Critical — 5) preferred_trail_mode = "chandelier" — same conflict as BTC V6
Same issue. The backtester doesn't know "chandelier".

Should be "none" — the chandelier is fully handled by check_custom_exit() and _exit_from_precomputed().

Important — 6) check_custom_exit() recomputes ATR on every call — O(N²)
atr_s = _atr(bars, p.atr_length)
Same issue as BTC V6. Fix with entry_atr from metadata.

Important — 7) reviewer_exempt not set
Missing.

Important — 8) Missing metadata: volume_ratio, structural_stop_price
Medium — 9) No validated backtest numbers
Author: Quant Engineering Session 2026-05-24
This is a designed-from-scratch strategy with no documented backtest results. First validation results will be fully unknown.

Minor — 10) fresh_bull logic may be too strict
The fresh cross condition:

fresh_bull = above_ribbon & ~above_ribbon.shift(1, fill_value=False)
This fires only when price was not above the fastest EMA on the prior bar.

But if the full ribbon is perfectly ordered and price was already above EMA8, a fresh cross can't fire even if the ribbon just aligned. Consider whether you want:

Edge trigger on price entering above the fastest EMA (current)
OR edge trigger on ribbon first becoming fully aligned (alternative)
Both are valid but they produce different signal frequency.

Minor — 11) candle_limit of 200 is correct for EMA55
55-bar EMA + ADX warmup. 200 is generous enough.

What is genuinely good
Chandelier implementation is complete and correct in both paths — same quality as BTC V6
Fibonacci EMA spacing is well-motivated and documented
_precompute(), _analyze_from_precomputed(), _exit_from_precomputed() all exist
Score uses both ADX strength and ribbon width — both meaningful
Works both long and short
generate_signals() is clean and vectorized
Claude patch prompt
Because this strategy has nearly identical issues to BTC V6 Chandelier, I'll keep this brief with just the differences noted.

Patch strategies/ema_ribbon_breakout.py and register it in the bot framework.

This strategy has nearly identical structure to btc_v6_chandelier.py.
Apply the same fixes with EMA ribbon-specific adjustments.

Files to inspect and patch:
- strategies/ema_ribbon_breakout.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt)

========================================================
REQUIRED FIXES
========================================================

1) Register in backtester.py strategy_map
Add:
    "ema_ribbon_breakout": ("strategies.ema_ribbon_breakout", "EMARibbonBreakoutStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.ema_ribbon_breakout import EMARibbonBreakoutStrategy
    EMARibbonBreakoutStrategy(),

3) Add ema_ribbon_breakout to TIME_STOP_EXEMPT in backtester.py
Add:
    "ema_ribbon_breakout",

4) Confirm _bars_held injection before exit calls
Standard injection pattern.

5) CRITICAL: Add structural_stop_price to metadata
In both analyze() and _analyze_from_precomputed(), compute:

    sl_price = (close - chan_dist if direction == "long"
                else close + chan_dist)

Add to metadata:
    "structural_stop_price": round(sl_price, 6),

Keep existing metadata fields — just add this one.

6) CRITICAL: Fix preferred_trail_mode
Change in metadata from:
    "preferred_trail_mode": "chandelier",
To:
    "preferred_trail_mode": "none",

The chandelier is fully managed by check_custom_exit() and
_exit_from_precomputed(). No built-in backtester trailing needed.

7) Cache entry_atr to fix O(N) ATR in check_custom_exit()
Same fix as btc_v6_chandelier:

In analyze() and _analyze_from_precomputed(), add to metadata:
    "entry_atr": round(atr, 6),

In check_custom_exit(), replace:
    atr_s = _atr(bars, p.atr_length)
    cur_atr = float(atr_s.iloc[-1])

With:
    cur_atr = float(meta.get("entry_atr", float(bars["close"].iloc[-1]) * 0.02))

8) Add reviewer_exempt flag
Add to __init__:
    self.reviewer_exempt = True

9) Add volume_ratio to metadata
Standard computation:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

Add to metadata:
    "volume_ratio": vol_ratio,

Also add in _analyze_from_precomputed() using df["volume"].

10) Add missing metadata: entry_timeframe
Add to metadata in both paths:
    "entry_timeframe": "1d",

11) Add documentation note — no backtest results exist yet
Add near the top of the class docstring or header:
    # NOTE: No validated backtest results exist yet for this strategy.
    # First run after registration will produce new evidence.
    # Benchmark against ema_crossover or adaptive_regime trend strategies.

========================================================
DO NOT CHANGE
========================================================

- generate_signals() ribbon alignment logic
- Fibonacci EMA spacing (8/13/21/34/55)
- fresh_bull / fresh_bear edge-trigger logic
- ADX filter
- Chandelier logic in check_custom_exit() and _exit_from_precomputed()
- Score calculation (adx_norm + ribbon_score)
- _precompute() and _analyze_from_precomputed() structure
- Long and short enabled

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/ema_ribbon_breakout.py

Run basket (this is a first-ever run — no prior results exist):
python intelligence/backtester.py --all \
    --strategy ema_ribbon_breakout --days 365 --tf 1d \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Run stocks:
python intelligence/backtester.py --all \
    --strategy ema_ribbon_breakout --days 365 --tf 1d \
    --asset-class stock \
    --initial-stop signal_structural --trail-stop none

Exit reason check:
- chandelier_stop should appear
- stop_loss (hard fallback) should appear occasionally
- Generic lifecycle stops should NOT appear

Check initial stop:
sl_pct should be ATR × 3.0 / close × 100
On daily crypto that's typically 3-6%.
If sl_pct is showing 6.0 (the hard fallback), structural_stop_price
was not applied correctly.

Compare vs btc_v6_chandelier on same basket/period:
- Both use chandelier exits
- EMA ribbon has more demanding entry (5 EMAs aligned vs 3 indicators)
- Expect fewer trades but potentially higher quality

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. First-ever validation results (this has never been backtested)
5. Comparison vs btc_v6_chandelier trade count and quality
6. Final classification: Reject / Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — ribbon alignment is a reasonable multi-timeframe confirmation proxy
Code quality: same level as BTC V6 — clean precompute pattern, correct chandelier
Implementation completeness: 80% — same gaps as BTC V6
Evidence base: zero — never been backtested
Salvageable: yes
Strong incubate — the EMA ribbon concept is well-established in trend trading and the Fibonacci spacing is a thoughtful design choice. Given that BTC V6 Chandelier uses similar entry + chandelier exit, these two should be compared head-to-head after both are patched.

This is the last of the batch from the quant session — ready for the next one whenever you are.