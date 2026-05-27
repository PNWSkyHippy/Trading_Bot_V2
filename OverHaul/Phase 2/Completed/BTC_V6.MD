This one is conceptually solid and well-implemented — the chandelier stop logic is properly handled in both fast and slow paths, which is more than most strategies in this batch can say.

My read on BTC V6 Chandelier
Overall verdict: Strong incubate — mostly complete, a few targeted fixes needed
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
Same pattern.

Critical — 3) _bars_held injection needed
Same pattern.

Critical — 4) structural_stop_price missing from metadata despite preferred_initial_stop_mode = "signal_structural"
This is a real execution bug.

Metadata says:

"chandelier_init":             round(chan_init, 6),
"preferred_initial_stop_mode": "signal_structural",
But the executor reads structural_stop_price — not chandelier_init.

So the executor will see preferred_initial_stop_mode = "signal_structural", look for structural_stop_price, find nothing, and fall back to percent-based stop.

The chandelier initial position is computed correctly:

chan_init = close - atr * p.atr_mult
It just needs to also be stored as structural_stop_price.

Critical — 5) preferred_trail_mode = "chandelier" may conflict with backtester trail logic
The backtester understands these trail modes:

two_bar
percent
none
auto
If it encounters "chandelier" it may either ignore it or silently fall back to a default trail.

The chandelier trailing IS handled correctly by check_custom_exit() and _exit_from_precomputed(). So the right approach is probably:

Set preferred_trail_mode = "none" so the backtester doesn't apply any built-in trailing
The chandelier stop then fires purely from the custom exit hook
Currently the risk is: backtester applies its own percent-trailing AND chandelier stop fires, creating double-trailing behavior.

Important — 6) reviewer_exempt not set
Missing from __init__().

Important — 7) check_custom_exit() recomputes ATR on every bar
atr_s = _atr(bars, p.atr_length)
This is O(N) per call. The _exit_from_precomputed() fast path reads directly from precomputed sigs, so if the backtester uses the fast path, this is less painful. But the slow path is still O(N²) for open trades.

Minor mitigation: chandelier stops tend to fire quickly so most trades are short, limiting damage.

Important — 8) No validated backtest numbers documented
The docstring lists Pine parameters but no actual WR/PF numbers for the current tuned version. You know this was derived from a TraderDev strategy, but the current version has been retuned:

rsi_thresh: 43 → 45
atr_mult: 5.5 → 4.0
Those are significant changes. The original numbers don't apply.

Medium — 9) ADX uses atr_length parameter instead of a dedicated adx_length
out["adx"] = _adx(out, p.atr_length)   # uses atr_length for ADX period too
Both default to 14 so this works. But if someone changes atr_length, ADX period changes too. Should either add a separate adx_length param or add a comment explaining this is intentional.

Medium — 10) volume_ratio missing from metadata
Minor — 11) candle_limit = 230 is tight for 200-bar vol reference
out["ref_atr"] = out["norm_atr"].rolling(200).mean()
200-bar rolling + 55-bar EMA warmup + ATR warmup = really needs ~250 bars. 230 is technically enough but very tight.

What is genuinely good
Chandelier logic is correct in both fast and slow paths — unique in this batch
_exit_from_precomputed() correctly reads from precomputed sigs without recomputation
_precompute() and _analyze_from_precomputed() are complete
Vol mult and sig mult computations are clean
"chandelier_init" preserved in metadata for debugging
time_stop_profile = "strategy_defined" set
Score scales meaningfully with vol and signal multipliers
Long-only design matches the trend-following thesis
Claude patch prompt
Patch strategies/btc_v6_chandelier.py and register it in the bot framework.

Fixes are targeted — the core logic is correct.
The most important fix is items 5 and 6 — without them the initial stop
placement and trail behavior are both wrong.

Files to inspect and patch:
- strategies/btc_v6_chandelier.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add:
    "btc_v6_chandelier": ("strategies.btc_v6_chandelier", "BTCV6ChandelierStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.btc_v6_chandelier import BTCV6ChandelierStrategy
    BTCV6ChandelierStrategy(),

3) Add btc_v6_chandelier to TIME_STOP_EXEMPT in backtester.py
This strategy uses a chandelier trailing stop.
Generic lifecycle stops must not fire before the chandelier exit.
Add:
    "btc_v6_chandelier",

4) Confirm _bars_held injection before exit calls
Standard injection pattern:
    _meta = dict(trade.get("entry_metadata", {}))
    _meta["_bars_held"] = i - trade["entry_idx"]

5) CRITICAL: Add structural_stop_price to metadata
Current metadata has chandelier_init but NOT structural_stop_price.
The executor reads structural_stop_price — not chandelier_init.
Without it, the initial stop falls back to percent-based.

In both analyze() and _analyze_from_precomputed(), add:
    "structural_stop_price": round(chan_init, 6),

Keep chandelier_init too for debugging — both fields should be present.

6) CRITICAL: Fix preferred_trail_mode to prevent double-trailing
Current:
    "preferred_trail_mode": "chandelier",

The backtester does not understand "chandelier" as a trail mode.
It may either ignore it or apply a default trailing on top of
the chandelier check_custom_exit — creating double-trailing behavior.

The chandelier is already handled entirely by check_custom_exit() and
_exit_from_precomputed(). No additional trailing from the backtester is needed.

Change to:
    "preferred_trail_mode": "none",

This tells the backtester: no built-in trailing — the strategy manages its own exits.

7) Fix check_custom_exit() O(N) ATR recomputation
Current:
    atr_s = _atr(bars, p.atr_length)

This recomputes ATR over the entire bars window on every call.
When the backtester uses the _exit_from_precomputed() fast path, this is
skipped — but the slow path fallback still has the issue.

Replace with a lightweight Wilder EWM over only the recent bars:
    atr_s = bars["close"].ewm(span=p.atr_length, adjust=False).mean()
    # approximate but much faster than full _atr() recalculation
    cur_atr = float(atr_s.iloc[-1])

Better alternative: cache the last ATR in entry_metadata:
    cur_atr = float(meta.get("entry_atr", _atr(bars, p.atr_length).iloc[-1]))

Then in analyze() add to metadata:
    "entry_atr": round(atr, 6),

And use it in check_custom_exit():
    cur_atr = float(meta.get("entry_atr", float(bars["close"].iloc[-1]) * 0.02))

Note: using entry ATR for chandelier is actually more stable than recomputing
each bar — it prevents the chandelier from widening if vol increases mid-trade.
Decide which behavior you want and be consistent.
If you want dynamic ATR (wilder), add proper warmup.
If you want entry-time ATR (simpler, more stable), use entry_atr from metadata.

For now: use entry_atr from metadata for simplicity and consistency.

8) Add reviewer_exempt flag
Inspect base_strategy.py to confirm reviewer_exempt is the correct field.
If yes, add to __init__:
    self.reviewer_exempt = True

9) Add volume_ratio to metadata
In analyze():
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

Add to metadata dict:
    "volume_ratio": vol_ratio,

Do the same in _analyze_from_precomputed() using df["volume"].

10) Fix ADX parameter naming for clarity
Current:
    out["adx"] = _adx(out, p.atr_length)

This uses atr_length for ADX too — both default to 14 so it works.
Add a comment to make this explicit:
    out["adx"] = _adx(out, p.atr_length)  # both ATR and ADX use same lookback (14)

Optional: add adx_length parameter to BTCV6ChandelierParams so they can
be tuned independently:
    adx_length: int = 14   # currently same as atr_length

11) Bump candle_limit from 230 to 250
The 200-bar vol reference requires 200+ bars + EMA55 warmup.
230 is tight — 250 gives more reliable early-bar indicator quality.

12) Add post-tuning backtest note to docstring
The strategy was retuned on 2026-05-25:
    rsi_thresh: 43 → 45
    atr_mult:   5.5 → 4.0

These are significant changes from the original Pine parameters.
Add a note near the parameters section:
    # v3 matrix sweep 2026-05-25: rsi_thresh tuned 43→45, atr_mult tuned 5.5→4.0
    # Original Trader Dev results DO NOT apply to these parameters.
    # Re-validate with bot backtester.

========================================================
DO NOT CHANGE
========================================================

- generate_signals() core logic
- RSI + EMA trend + ADX entry stack
- Chandelier logic in check_custom_exit() and _exit_from_precomputed()
- Vol mult and sig mult computations
- _precompute() and _analyze_from_precomputed() structure
- Score calculation
- Long-only design

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/btc_v6_chandelier.py

Run BTC first (primary intended symbol):
python intelligence/backtester.py --symbol BTC/USD \
    --strategy btc_v6_chandelier --days 365 --tf 1d \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Key things to verify:
1. sl_pct should be ~4% (atr_mult=4.0 × ATR on daily BTC) not 9% fallback
   If sl_pct is 9%, structural_stop_price is still not being used correctly
2. chandelier_stop should appear in exit breakdown
3. Generic lifecycle stops should NOT appear

Run basket:
python intelligence/backtester.py --all \
    --strategy btc_v6_chandelier --days 365 --tf 1d \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Exit reason check:
- chandelier_stop should dominate
- stop_loss (hard stop fallback) should appear rarely
- Generic lifecycle stops should NOT appear

Compare initial stop placement:
Before fix: sl_pct would use percent-based fallback (~9% hard_sl_pct)
After fix: sl_pct should be around ATR × 4.0 / close × 100
On daily BTC, ATR × 4.0 is typically 5-8% depending on regime.

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. Confirmation chandelier_stop fires in exit breakdown
5. Confirmation sl_pct is ATR-derived not 9% fallback
6. Basket validation results
7. Final classification: Reject / Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid trend-following with chandelier trailing — well-established methodology
Code quality: best exit implementation in the batch — both fast and slow paths correct
Implementation completeness: 80% — structural_stop_price and trail_mode conflict are the critical gaps
Evidence base: none confirmed for tuned version — needs fresh validation
Salvageable: yes
Strong incubate — the chandelier implementation is the cleanest in the batch, which matters because trailing exits are the hardest to get right. If the tuned parameters produce reasonable results on daily BTC (which is the natural fit for a Chandelier strategy), this could move to candidate quickly.