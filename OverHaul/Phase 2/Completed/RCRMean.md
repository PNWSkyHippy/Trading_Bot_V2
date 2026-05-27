This is the most mathematically sophisticated strategy in the batch and has the cleanest implementation overall.

My read on RCR Mean Reversion
Overall verdict: Strong incubate — genuinely original concept, mostly complete, a few important gaps
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
Same pattern.

Critical — 3) _bars_held injection needed
Same pattern.

Critical — 4) check_custom_exit() calls generate_signals() on every bar — O(N²)
This is the same problem MR-04 had, but worse here because generate_signals() includes rolling autocorrelation:

sig = generate_signals(bars, p)
_rolling_autocorr() computes a 50-bar rolling correlation on every call.

On a 365-day 1h backtest, check_custom_exit() could be called thousands of times for open trades. Each call recomputes ATR, returns, and 50-bar autocorrelation from scratch.

However, _exit_from_precomputed() exists but only handles the time stop, missing the SMA cross.

Critical — 5) _exit_from_precomputed() is incomplete
Only handles time stop:

def _exit_from_precomputed(self, i, sigs, direction, meta):
    bars_held = int(meta.get("_bars_held", 0))
    if bars_held >= p.time_stop:
        return "time_stop"
    return None
The SMA cross exit is missing from the fast path. This means:

If the backtester uses fast-path exits, trades never get SMA cross exits
Every trade goes to time stop or SL/TP instead
Important — 6) reviewer_exempt not set
Missing from __init__().

Important — 7) Missing metadata fields
Both analyze() and _analyze_from_precomputed() are missing:

structural_stop_price
preferred_initial_stop_mode
preferred_trail_mode
volume_ratio
Important — 8) crypto_candle_timeframe = "1d" — same unusual note as KDS
If intentional for daily bars, keep it. If the original Trader Dev validation was on 1h, this should be "1h".

Medium — 9) Single-symbol evidence is the main strategic concern
The impressive numbers come from one test:

LINKUSDT 1h, 180 days: PF=2.38, WR=76.7%, Sharpe=3.42
LINK is a notoriously mean-reverting crypto. These numbers may not transfer to:

BTC/ETH which are more trending
Different market regimes
Different time periods
This is not a code issue but it is the most important strategic concern.

Minor — 10) ml_exempt likely not a real framework field
Same as other strategies.

Minor — 11) Time stop of 10 bars on 1h = 10 hours
That's quite aggressive for a mean-reversion strategy. But it may be intentional based on the original results.

What is genuinely good
Autocorrelation regime detector is genuinely principled — this is not indicator soup
Edge-triggered signals prevent holding entries through extended signal periods
_precompute() and _analyze_from_precomputed() both exist and are correct
SMA cross exit logic is mathematically correct
_rolling_autocorr() uses pandas rolling corr properly
Score scales well with regime strength and Z-score depth
check_custom_exit() is implemented and mostly correct
_exit_from_precomputed() exists (just incomplete)
Claude patch prompt
Patch strategies/rcr_mean_reversion.py and register it in the bot framework.

This strategy is mostly complete. The main fixes are:
1. Registration and time-stop wiring (standard)
2. Fix the O(N²) check_custom_exit() by completing _exit_from_precomputed()
3. Add missing metadata fields
4. Fix reviewer_exempt

Do NOT change the core autocorrelation regime detector.
Do NOT change the Z-score entry logic.
Do NOT change the SMA cross exit concept.

Files to inspect and patch:
- strategies/rcr_mean_reversion.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt, ml_exempt)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add:
    "rcr_mean_reversion": ("strategies.rcr_mean_reversion", "RCRMeanReversionStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.rcr_mean_reversion import RCRMeanReversionStrategy
    RCRMeanReversionStrategy(),

3) Add rcr_mean_reversion to TIME_STOP_EXEMPT in backtester.py
Add:
    "rcr_mean_reversion",

4) Confirm _bars_held injection before exit calls
Standard injection pattern:
    _meta = dict(trade.get("entry_metadata", {}))
    _meta["_bars_held"] = i - trade["entry_idx"]

5) Fix O(N²) by completing _exit_from_precomputed() with SMA cross exit
Current _exit_from_precomputed() only checks time stop.
It must also check the SMA cross — this is the primary exit condition.

The precomputed sigs df already has "sma" and "close" columns.
The SMA cross can be read from two consecutive rows without recomputing:

    def _exit_from_precomputed(self, i: int, sigs: pd.DataFrame,
                               direction: str, meta: dict) -> Optional[str]:
        p         = self.params
        bars_held = int(meta.get("_bars_held", 0))

        # A. SMA cross exit (primary: mean reversion achieved)
        try:
            if i >= 1:
                cur_close  = float(sigs.iloc[i]["close"])
                cur_sma    = float(sigs.iloc[i]["sma"])
                prev_close = float(sigs.iloc[i - 1]["close"])
                prev_sma   = float(sigs.iloc[i - 1]["sma"])
                if not any(pd.isna(v) for v in [cur_sma, prev_sma]):
                    if direction == "long" and prev_close <= prev_sma and cur_close > cur_sma:
                        return "sma_cross_exit"
                    if direction == "short" and prev_close >= prev_sma and cur_close < cur_sma:
                        return "sma_cross_exit"
        except Exception:
            pass

        # B. Time stop (safety net)
        if bars_held >= p.time_stop:
            return "time_stop"

        return None

This is O(1) per bar instead of O(N) because it reads from the precomputed df.

6) Fix check_custom_exit() to NOT recompute all signals on every call
Current check_custom_exit() calls generate_signals(bars, p) every bar.
This is O(N) per call → O(N²) total.

Replace with a lightweight computation:

    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        if bars is None or len(bars) < 2:
            return None
        p         = self.params
        meta      = entry_metadata or {}
        bars_held = int(meta.get("_bars_held", 0))

        # Time stop
        if bars_held >= p.time_stop:
            return "time_stop"

        # SMA cross exit — compute only the SMA on current bars window
        # This is O(sma_length) not O(N) like calling generate_signals()
        try:
            close_series = bars["close"]
            sma_now      = close_series.rolling(p.sma_length).mean()
            cur_close    = float(close_series.iloc[-1])
            cur_sma      = float(sma_now.iloc[-1])
            prev_close   = float(close_series.iloc[-2])
            prev_sma     = float(sma_now.iloc[-2])

            if not any(pd.isna(v) for v in [cur_sma, prev_sma]):
                if direction == "long" and prev_close <= prev_sma and cur_close > cur_sma:
                    return "sma_cross_exit"
                if direction == "short" and prev_close >= prev_sma and cur_close < cur_sma:
                    return "sma_cross_exit"
        except Exception:
            pass

        return None

Key change: only compute SMA (O(window)) not all signals including autocorrelation (O(N)).

7) Add missing metadata fields to both analyze() and _analyze_from_precomputed()
For both methods, compute:

    sl_price = (close - atr * p.stop_atr_k if direction == "long"
                else close + atr * p.stop_atr_k)

Add to metadata dict:
    "structural_stop_price":       round(sl_price, 6),
    "preferred_initial_stop_mode": "signal_structural",
    "preferred_trail_mode":        "none",

Also add:
    vol_series = candles["volume"]   # (use df["volume"] in precomputed path)
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None
    "volume_ratio": vol_ratio,

8) Add reviewer_exempt flag
Add to __init__:
    self.reviewer_exempt = True

9) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not a recognized field, remove it.

10) Clarify crypto_candle_timeframe
Current: self.crypto_candle_timeframe = "1d"
The original Trader Dev source was "LINKUSDT 1h".

Check: is this strategy intended for daily or hourly bars?
- If 1h was the validated configuration, change to "1h" and update candle_limit to 150
- If 1d is intentional (daily bars), keep it and add a comment explaining why

Do not change without clarifying intent.

11) Multi-symbol validation note
The impressive original result (PF=2.38, WR=76.7%) comes from
one symbol (LINKUSDT, 180 days). This may not generalize.

Add a comment near the backtest results:
    # NOTE: Single-symbol validation only (LINKUSDT 1h 180d).
    # Cross-symbol validation required before deployment.
    # LINK is known for mean-reverting behaviour — results may not transfer
    # to BTC/ETH which are more trending.

========================================================
DO NOT CHANGE
========================================================

- _rolling_autocorr() implementation
- generate_signals() core logic (autocorrelation, Z-score, edge-triggered signals)
- All parameter values
- Score calculation (ac_score + z_score combination)
- SMA cross exit concept
- _precompute() and _analyze_from_precomputed() structure

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/rcr_mean_reversion.py

Run primary test — LINK which is the validated symbol:
python intelligence/backtester.py --symbol LINK/USD \
    --strategy rcr_mean_reversion --days 180 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Target result:
WR ~76%, PF ~2.3, Sharpe ~3.4 — compare to original Trader Dev claim.
If your backtester produces materially different numbers, investigate why.

Cross-symbol test to check generalization:
python intelligence/backtester.py --all \
    --strategy rcr_mean_reversion --days 365 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Check exit reason breakdown:
- sma_cross_exit should be the dominant exit (was missing before fix)
- time_stop should appear on slow reversions
- stop_loss should appear occasionally
- Generic lifecycle stops should NOT appear

Performance check:
With the O(N²) fix, the basket should complete noticeably faster.
Time the run before and after the patch if possible.

Check whether sma_cross_exit now appears:
- Before the fix: time_stop would dominate (because _exit_from_precomputed was incomplete)
- After the fix: sma_cross_exit should dominate

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. LINK 180d result — comparison to original claim
5. Cross-symbol basket result
6. Confirmation sma_cross_exit now fires in exit breakdown
7. Final classification: Reject / Watchlist / Incubate / Candidate
My pre-patch classification
Concept: best in the batch — autocorrelation regime detection is statistically principled
Code quality: good — precompute path exists, SMA exit concept is correct
Implementation completeness: 80% — _exit_from_precomputed incomplete is the main gap
Evidence base: single-symbol, 180 days, impressive numbers — needs cross-validation
Salvageable: yes — fixes are surgical
Strong incubate — potentially the most interesting strategy you have.

If LINK result reproduces in your backtester and even 3-4 other symbols show positive PF, this could be a genuine candidate. The autocorrelation regime detector is a real edge over naive RSI mean reversion.

One thing worth testing right after patching:

# Does the regime filter actually help?
# Run with ac_thresh = 1.0 (disable regime filter) vs ac_thresh = -0.05 (normal)
# If numbers collapse without the filter, the edge is real
# If they stay similar, the filter is cosmetic
That one comparison will tell you more than 10 symbol tests.