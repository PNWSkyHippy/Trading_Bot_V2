This is significantly improved from the version shown earlier in the audit — most of the earlier concerns have been addressed. The live data makes this one worth careful attention.

My read on ECB (post-audit version)
Overall verdict: Watchlist/Incubate — best-implemented new strategy, critical TIME_STOP_EXEMPT confirmed by live evidence
What was fixed since the original version
✅ Entropy collapse is now an event not a state
✅ bias_threshold configurable, direction derived from explicit threshold
✅ Re-arm logic prevents repeat entries in same low-entropy regime
✅ check_custom_exit() fully implemented with all three exits
✅ 2-bar entropy normalization prevents eager exits
✅ No fake metadata — all real values
✅ structural_stop_price in metadata
✅ Live/backtest parity via _entry_bar_time fallback
✅ Score formula improved with better spread
✅ Timeframe guard prevents 5m/15m misuse
✅ Real volume_ratio computed separately from vol_ok

Remaining issues
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT — confirmed critical by live data
The audit says explicitly:

CRITICAL BUG: time_stop_profile = "strategy_defined" was declared but position_monitor never read it. The 2hr perf stop fired on ECB trades, cutting the 24-bar thesis at bar 2 every time.

Applied fix per audit:

✅ position_monitor._check_performance_time_stop(): added ecb_strategy to TIME_STOP_EXEMPT set

But this means the fix was applied to position_monitor.py (live path).

It may not have been applied to the backtester's TIME_STOP_EXEMPT frozenset.

Need to confirm:

TIME_STOP_EXEMPT = frozenset({
    "grid_bot", "dca_accumulator",
    ...
    "ecb_strategy",   # must be here
})
Important — 3) preferred_initial_stop_mode and preferred_trail_mode missing from metadata
Both signals have structural_stop_price but neither declares:

"preferred_initial_stop_mode": "signal_structural",
"preferred_trail_mode":        "none",
Important — 4) ml_exempt likely not a real framework field
self.ml_exempt = True
Same as other strategies — check base_strategy.py.

Important — 5) Live data is too thin to draw conclusions
Current live: 27 exits, 3 longs at 0% WR, 24 shorts at 33.3% WR.

The audit correctly notes this is too thin to judge. The more important question is:

After the TIME_STOP_EXEMPT fix was applied to position_monitor, did ECB's own exits start firing?

The audit says to monitor for ecb_max_hold / ecb_entropy_reset / ecb_regime_flip appearing in live exit data. If perf_time_stop_1hr still dominates after the fix, the backtester TIME_STOP_EXEMPT fix wasn't applied.

Minor — 6) BCH concern from live data not yet resolved
BCH was the worst offender (-$79.36 stop_loss). If BCH repeatedly generates ECB shorts that blow up → add it to blacklist.

This is still an "if" — monitor in progress. No code change needed yet.

Minor — 7) check_custom_exit() recomputes rolling entropy on every call
entropy_series = rolling_entropy(bars, p.entropy_window)
This is O(N × entropy_window) per bar while in position. Since ECB holds max 24 bars and entropy_window=20, this is bounded and acceptable. Not worth fixing now.

Claude patch prompt
Patch strategies/ecb_strategy.py and register it in the bot framework.

This strategy has been significantly improved in a previous audit pass.
Fixes are minimal — registration, metadata hints, and TIME_STOP_EXEMPT verification.

Do NOT change any entry/exit logic, entropy calculations, re-arm logic,
score formula, or parameter values.

Files to inspect and patch:
- strategies/ecb_strategy.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- core/position_monitor.py (verify TIME_STOP_EXEMPT fix is also in live path)
- strategies/base_strategy.py (inspect: ml_exempt)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "ecb_strategy": ("strategies.ecb_strategy", "ECBStrategy"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.ecb_strategy import ECBStrategy
    ECBStrategy(),

3) CRITICAL: Add ecb_strategy to TIME_STOP_EXEMPT in backtester.py
The live audit confirmed that perf_time_stop_1hr was killing ECB trades at bar 2
instead of allowing the 24-bar thesis to play out.
A fix was applied to position_monitor.py for live trading.
Confirm it was ALSO applied to the backtester.

Check:
    TIME_STOP_EXEMPT = frozenset({...})

If ecb_strategy is NOT in this set, add it:
    TIME_STOP_EXEMPT = frozenset({
        "grid_bot", "dca_accumulator",
        ...,
        "ecb_strategy",
    })

If it IS already there, confirm and document.

4) Verify position_monitor.py fix is in place
The audit says:
    "✅ position_monitor._check_performance_time_stop(): added ecb_strategy
     to TIME_STOP_EXEMPT set"

Inspect core/position_monitor.py.
Confirm ecb_strategy is in the TIME_STOP_EXEMPT equivalent.
If missing, add it.

Add a comment near the time stop logic in position_monitor.py:
    # ecb_strategy: 24-bar max hold — perf_time_stop kills thesis if not exempt
    # Fix applied 2026-05-20 per live audit (27 exits showed perf_time_stop at bar 2)

5) Add preferred_initial_stop_mode and preferred_trail_mode to metadata
In analyze(), add to the metadata dict:
    "preferred_initial_stop_mode": "signal_structural",
    "preferred_trail_mode":        "none",

These tell the executor to use structural_stop_price (already in metadata)
and not apply any built-in trailing.

6) Confirm _bars_held injection before check_custom_exit()
Standard injection pattern in backtester:
    _meta = dict(trade.get("entry_metadata", {}))
    _meta["_bars_held"] = i - trade["entry_idx"]

If already done from prior patches, confirm and document.
ECB's check_custom_exit() has a fallback via _entry_bar_time for live,
but backtester injection is still the primary clean path.

7) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not defined there, remove it.
reviewer_exempt = True is already correctly set — keep it.

8) Optional: Monitor live exit reason confirmation
After the TIME_STOP_EXEMPT fix:
Add a check that the exit breakdown shows:
- ecb_max_hold
- ecb_entropy_reset
- ecb_regime_flip

If perf_time_stop_1hr still appears after the fix is in place in both
backtester and position_monitor, there is a third code path that needs
investigation.

========================================================
DO NOT CHANGE
========================================================

- entropy_collapse event detection (not state)
- bias_threshold directional filter
- Re-arm logic (_entropy_rearm dict and entropy_reset check)
- check_custom_exit() — all three exits: regime flip, entropy normalization, max hold
- 2-bar entropy normalization requirement
- Score formula (entropy_depth + bias_score + vol_ok bonus)
- Timeframe guard (< 1h bars are skipped)
- All ECBParams default values
- All metadata fields already present
- Live/backtest parity via _entry_bar_time

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/ecb_strategy.py

Run BTC (primary validated symbol):
python intelligence/backtester.py --symbol BTC/USD \
    --strategy ecb_strategy --days 365 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

CRITICAL exit reason check:
Before TIME_STOP_EXEMPT fix:
  - perf_time_stop_1hr dominated (confirmed by live audit)
  - ecb_max_hold / ecb_entropy_reset / ecb_regime_flip NEVER appeared

After fix:
  - ecb_max_hold should appear (24-bar primary exit)
  - ecb_entropy_reset should appear (entropy normalization)
  - ecb_regime_flip should appear occasionally
  - stop_loss and take_profit should appear (catastrophic guards)
  - perf_time_stop_1hr should NOT appear

If perf_time_stop_1hr still appears:
  - Backtester TIME_STOP_EXEMPT is not set correctly
  - Fix item 3 and rerun

Target metrics vs documented baseline:
BTC 2024: PF ~2.59, WR ~63.6%, Sharpe ~0.87, Trades ~22

Run cross-symbol basket:
python intelligence/backtester.py --all \
    --strategy ecb_strategy --days 365 --tf 1h \
    --asset-class crypto

Expected ranking (from original cross-symbol results):
DOGE > BNB > ETH > BTC > XRP > (SOL borderline)

Confirm SOL blacklist is not hardcoded:
SOL appears borderline (PF=0.95) in original — no permanent exclusion needed yet.
Let results confirm.

Deliverables:
1. Patched strategy file (minimal changes)
2. Patched backtester.py (TIME_STOP_EXEMPT + registration)
3. Patched strategy_engine.py
4. position_monitor.py TIME_STOP_EXEMPT confirmation
5. Basket results — key check is exit reason breakdown
6. Confirmation ecb_max_hold fires instead of perf_time_stop_1hr
7. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: genuinely original — Shannon entropy of candle direction as directional commitment signal
Code quality: best in the batch after this audit pass — all patches applied correctly
Implementation completeness: 90% — registration and metadata hints are the only gaps
Evidence base: 27 live exits (thin), 22 BTC backtest trades with reasonable PF
Salvageable: yes — already mostly done
Strong incubate — the most important validation step is confirming that after both the backtester and position_monitor TIME_STOP_EXEMPT fixes, ECB's own exits (ecb_max_hold, ecb_entropy_reset) start dominating instead of perf_time_stop_1hr. That single change in the live path is what the entire June monitoring period is testing.

