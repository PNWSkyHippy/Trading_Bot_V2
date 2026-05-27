My read on RARE
Overall verdict: Watchlist (Reject classification pending fresh validation) — concept is sound but O(N²) autocorrelation and v1 exits were broken
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
24-bar max hold on 1h. Same pattern.

Critical — 3) _bars_held injection needed
Same pattern.

Critical — 4) rolling_autocorr() is O(N²) — severe performance issue
def rolling_autocorr(series: pd.Series, window: int) -> pd.Series:
    result = series.rolling(window).apply(
        lambda x: pd.Series(x).autocorr(lag=1) if len(x) >= p.min_obs else np.nan,
        raw=False
    )
    return result
pd.Series(x).autocorr(lag=1) called inside .rolling(window).apply() with raw=False means:

For each window of 20 bars, it creates a new pandas Series and computes autocorrelation
This is O(N × window) total
On 365d 1h = 8760 bars per symbol, that's ~175,000 autocorr computations per backtest run
This is worse than RCR's O(N²) issue
This will make backtesting extremely slow.

Important — 5) preferred_initial_stop_mode missing from metadata
Same as CBAE. Has preferred_trail_mode but not preferred_initial_stop_mode.

Important — 6) ml_exempt likely not a real framework field
Same as others.

Important — 7) Classification says "Reject v1" — but v1 exits were broken
The header says:

Classification : Reject v1 (Trader Dev result: PF 1.12, exits broken)
And the note says this Python version implements correct exits. So this should be reclassified as "Watchlist (pending first validation with correct exits)" rather than "Reject" since the rejection was for a broken implementation.

Medium — 8) No volume_ratio in metadata
Same as other strategies.

What is genuinely good
Autocorrelation regime flip is the same concept as RCR but focused on the sign change event rather than a persistent state
check_custom_exit() is correctly implemented with Z-score reversion exit
z_exit_thresh stored in metadata so the exit logic can reference it
_entry_bar_time fallback for live parity
structural_stop_price in metadata
Concept is sound — lag-1 autocorrelation regime is statistically principled
The "Reject v1" label is honest about why it was rejected
Claude patch prompt
Patch strategies/rare_strategy.py and register it in the bot framework.

This strategy is clean but has a severe O(N²) performance issue in the
autocorrelation computation. The core fix is a faster autocorrelation.

Files to inspect and patch:
- strategies/rare_strategy.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: ml_exempt)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add:
    "rare_strategy": ("strategies.rare_strategy", "RAREStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.rare_strategy import RAREStrategy
    RAREStrategy(),

3) Add rare_strategy to TIME_STOP_EXEMPT in backtester.py
24-bar max hold on 1h. Generic lifecycle stops kill the thesis.
Add:
    "rare_strategy",

4) Confirm _bars_held injection before check_custom_exit()
Standard injection pattern.

5) CRITICAL: Fix O(N²) rolling autocorrelation
Current implementation:
    result = series.rolling(window).apply(
        lambda x: pd.Series(x).autocorr(lag=1) if len(x) >= p.min_obs else np.nan,
        raw=False
    )

This is O(N × window) with Python overhead per window — very slow on large datasets.

Replace with a vectorized numpy implementation:
    def rolling_autocorr(series: pd.Series, window: int, lag: int = 1) -> pd.Series:
        """
        Fast vectorized rolling lag-1 autocorrelation using pandas rolling corr.
        Equivalent to pd.Series(x).autocorr(lag=1) but O(N) not O(N²).
        """
        lagged = series.shift(lag)
        return series.rolling(window).corr(lagged)

This uses pandas built-in rolling correlation which is implemented in C.
On 8760 bars, this should be 50-100x faster than the lambda approach.

Also update the inner call to use the function:
    autocorr = rolling_autocorr(ret, p.autocorr_window)

6) Add preferred_initial_stop_mode to metadata
Add:
    "preferred_initial_stop_mode": "signal_structural",

7) Add volume_ratio to metadata
Compute:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

Add to metadata:
    "volume_ratio": vol_ratio,

8) Update classification comment in docstring
Change:
    Classification : Reject v1 (Trader Dev result: PF 1.12, exits broken)
To:
    Classification : Watchlist (v1 Trader Dev exits broken; v2 Python exits correct
                     — first validation pending)

9) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not recognized, remove it.

========================================================
DO NOT CHANGE
========================================================

- Regime flip detection (ac_prev > 0 and autocorr < 0)
- Z-score entry and exit conditions
- ADX declining confirmation
- Direction assignment (fade the displacement)
- check_custom_exit() rare_z_revert and rare_max_hold
- Score formula
- All RAREParams default values

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/rare_strategy.py

Performance timing test:
python intelligence/backtester.py --symbol BTC/USD \
    --strategy rare_strategy --days 365 --tf 1h \
    --asset-class crypto
Note how long it takes before and after the autocorrelation fix.
Should be significantly faster (10-50 seconds vs potentially minutes).

Exit reason check:
- rare_z_revert should be dominant exit
- rare_max_hold should appear for slow reversions
- stop_loss for catastrophic events
- Generic lifecycle stops should NOT dominate

This is first-ever validation with correct exits (v1 was broken).

Target: PF > 1.0 with correct exits
If PF is still < 1.0 even with fixed exits → hypothesis may be weak
If PF > 1.0 → document as first valid evidence

Deliverables:
1. Patched strategy file with vectorized autocorrelation
2. Patched backtester.py
3. Patched strategy_engine.py
4. Performance timing comparison (before/after autocorr fix)
5. First-ever basket results with correct exits
6. Exit reason breakdown
7. Updated classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — autocorrelation regime detection with Z-score entry is principled
Code quality: clean except for the O(N²) autocorrelation
Implementation completeness: 85% — the autocorrelation fix is the most important change
Evidence base: none with correct exits — v1 was broken
Salvageable: yes
Watchlist — the concept is similar to RCR (which also uses autocorrelation) but focuses on the regime flip event rather than a persistent negative autocorrelation state. Worth validating to see if the flip event provides better timing than persistent state detection.

The performance fix is required before you can realistically run this on a basket. Send me the remaining 3.