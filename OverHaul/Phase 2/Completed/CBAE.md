Ha — so we're at 28 of 32 total. Let me audit CBAE and keep the last 4 ready.

My read on CBAE
Overall verdict: Watchlist — interesting concept, clean implementation, registration and one metadata gap
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
Holds up to 20 bars (20 hours on 1h). Same pattern as ECB.

Critical — 3) _bars_held injection needed
check_custom_exit() reads meta.get("_bars_held", 0) but also has the _entry_bar_time fallback. Same pattern as ECB.

Important — 4) preferred_initial_stop_mode missing from metadata
"preferred_trail_mode":   "none",
preferred_trail_mode is present but preferred_initial_stop_mode is missing. The executor needs both.

Important — 5) No validated post-Trader Dev cross-symbol results
The header says:

Classification : Watchlist (original Trader Dev result: PF 1.27, not swept cross-symbol)
NOTE: Parameters are UNTUNED first-pass defaults.
This is honest. PF 1.27 on one symbol with no parameter sweep is weak evidence. Post-patch validation is required before promoting.

Important — 6) ml_exempt likely not a real framework field
Same as others.

Medium — 7) body_sum is stored in metadata but entry_sum reads it by key
check_custom_exit() reads:

entry_sum = float(meta.get("body_sum", 0.0))
This correctly matches the metadata key "body_sum" — good.

Minor — 8) volume_ratio missing from metadata
Same as other strategies.

What is genuinely good
Concept is original — signed cumulative body ratio as commitment accumulation is not a standard indicator
check_custom_exit() is correctly implemented with body-sum revert exit
structural_stop_price in metadata
_entry_bar_time fallback for live/backtest parity (borrowed from ECB)
time_stop_profile = "strategy_defined" set
reviewer_exempt = True set
ATR stops are correctly computed
Score uses exhaustion depth and ADX headroom
candle_limit is correctly computed
No fake metadata
Claude patch prompt
Patch strategies/cbae_strategy.py and register it in the bot framework.

This strategy is clean and mostly complete. Fixes are minimal.
Do NOT change the body asymmetry logic, absorption detection, or exit conditions.

Files to inspect and patch:
- strategies/cbae_strategy.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: ml_exempt)

========================================================
REQUIRED FIXES
========================================================

1) Register in backtester.py strategy_map
Add:
    "cbae_strategy": ("strategies.cbae_strategy", "CBAEStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.cbae_strategy import CBAEStrategy
    CBAEStrategy(),

3) Add cbae_strategy to TIME_STOP_EXEMPT in backtester.py
This strategy holds up to 20 bars (20 hours on 1h).
Generic lifecycle stops will kill trades before the body-sum revert exit.
Add:
    "cbae_strategy",

4) Confirm _bars_held injection before check_custom_exit()
Standard injection pattern in backtester.
CBAE has an _entry_bar_time fallback for live path.
Confirm backtester injection also applies here.

5) Add preferred_initial_stop_mode to metadata
Current metadata has preferred_trail_mode but not preferred_initial_stop_mode.
Add:
    "preferred_initial_stop_mode": "signal_structural",

6) Add volume_ratio to metadata
Compute:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

Add to metadata:
    "volume_ratio": vol_ratio,

7) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not defined there, remove it.

========================================================
DO NOT CHANGE
========================================================

- Body ratio computation
- Signed accumulation (body_sum)
- Absorption detection (shrink_factor)
- ADX regime filter
- Macro trend direction gate (bull_regime/bear_regime)
- check_custom_exit() cbae_sum_revert and cbae_max_hold
- Score formula
- All CBAEParams default values

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/cbae_strategy.py

First-ever baseline run:
python intelligence/backtester.py --all \
    --strategy cbae_strategy --days 365 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Exit reason check:
- cbae_sum_revert should be dominant exit
- cbae_max_hold should appear occasionally
- stop_loss for catastrophic events
- Generic lifecycle stops should NOT dominate

Target comparison:
Original Trader Dev single-symbol result: PF 1.27
Bot backtester may differ due to realistic execution (next-bar fill, fees).
If PF is still above 1.0 on basket, document as first cross-symbol evidence.

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. First-ever cross-symbol basket results
5. Exit reason breakdown confirming cbae_sum_revert fires
6. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: interesting — signed cumulative body ratio as commitment detector is non-standard
Code quality: clean, exit logic correct, borrowed good patterns from ECB
Implementation completeness: 88% — just missing preferred_initial_stop_mode and registration
Evidence base: one symbol, no parameter sweep, untuned — very thin
Salvageable: yes, worth validating
Watchlist — honest about its limitations, first validation will establish whether the concept has cross-symbol edge.

Send me the remaining 4 and I'll keep the same pace.