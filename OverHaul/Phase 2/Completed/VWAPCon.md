This one is the most refined ORB implementation in the batch — it has several improvements over orb_breakout.py that show clear design thinking. But it has one critical invisible bug.

My read on VWAP Confirmed ORB
Overall verdict: Strong incubate — cleaner than orb_breakout.py in several ways, one critical exit bug
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) VWAP exit never fires — strategy name mismatch
This is the most important bug.

The backtester has:

if exit_reason is None and strategy_name == "orb_breakout":
    exit_reason = _bt_orb_vwap(df, i, trade)
But this strategy uses:

self.strategy_name = "vwap_confirmed_orb"
So the VWAP cross exit never fires for this strategy in backtesting.

Every trade that would normally exit on VWAP cross instead holds until:

SL
TP
Generic lifecycle stops
Since VWAP cross is the natural mean-reversion exit for ORB trades, missing it means:

Winners that should exit cleanly at VWAP hold longer and may give back gains
Losers don't get a VWAP-warned early exit
This distorts all backtest results for this strategy.

Critical — 3) Not in TIME_STOP_EXEMPT
Same reasoning as orb_breakout but stock-specific.

On 5m bars with 2.0R target:

Generic EARLY_LOSS_BARS = 6 bars = 30 minutes
Generic PERF_2HR_BARS = 24 bars = 2 hours
Generic HARD_STOP_BARS = 96 bars = 8 hours
A 2R stock ORB target can easily take 2-4 hours to develop. The perf_time_stop will kill valid developing trades.

Critical — 4) _bars_held injection needed
Same pattern.

Important — 5) preferred_initial_stop_mode and preferred_trail_mode missing from metadata
Both signals return structural_stop_price but neither declares:

"preferred_initial_stop_mode": "signal_structural",
"preferred_trail_mode":        "none",
Important — 6) reviewer_exempt not set
Missing.

Important — 7) ml_exempt likely not a real framework field
Same as others.

Important — 8) No check_custom_exit() for live VWAP exit
If position_monitor.py checks strategy name the same way the backtester does, the VWAP exit also won't fire in live trading.

This strategy needs either:

Its name added to the backtester and live monitor VWAP check, OR
Its own check_custom_exit() with VWAP exit logic
What is genuinely good — and better than orb_breakout.py
1. Stale session guard — ORB Breakout doesn't have this
session_date = session.index[-1].date()
today = date.today()
if session_date < today:
    self.verbose_log_skip(...)
    return None
This prevents pre-market signals from using yesterday's stale ORB levels. ORB Breakout doesn't have this.

2. Max OR width filter — ORB Breakout doesn't have this
if or_width > atr * max_or_atr:
    self.verbose_log_skip(...)
    return None
Prevents entering when the ORB is so wide that the structural stop would be too large. Important safety check.

3. Stop cap — ORB Breakout doesn't have this
raw_stop    = orb_low
capped_stop = current_close * (1 - max_stop_pct / 100)
stop_price  = max(raw_stop, capped_stop)
Caps the structural stop so it never exceeds max_stop_pct. This prevents runaway losses if the ATR filter fails to catch an unusually wide ORB.

4. Breakout buffer
long_bo_threshold = orb_high * (1 + bo_buffer_pct / 100)
Requires price to clear the breakout level by a buffer before triggering. Reduces false positives from micro-breakouts and wick-through.

5. Crypto disabled intentionally
self.crypto_enabled = False   # VWAP has no reliable anchor on 24/7 crypto
The comment is correct and honest. This is a stock-first strategy.

6. Full metadata is complete for all other fields
Both long and short include structural_stop_price, orb_high, orb_low, session_vwap, volume_ratio, bars_since_breakout — all present.

Claude patch prompt
Patch strategies/vwap_confirmed_orb.py and register it in the bot framework.

This strategy is cleaner than orb_breakout.py in several ways.
The most critical fix is item 5 — the VWAP exit never fires due to strategy name mismatch.

Files to inspect and patch:
- strategies/vwap_confirmed_orb.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt, ml_exempt)
- core/position_monitor.py (inspect: VWAP exit strategy name check)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add:
    "vwap_confirmed_orb": ("strategies.vwap_confirmed_orb", "VwapConfirmedOrb"),

2) Register in strategy_engine.py
Add:
    from strategies.vwap_confirmed_orb import VwapConfirmedOrb
    VwapConfirmedOrb(),

3) Add vwap_confirmed_orb to TIME_STOP_EXEMPT in backtester.py
On 5m stock bars with 2R target, trades need 2-4 hours to develop.
Generic perf_time_stop at 2h will kill valid setups before they reach target.
Add:
    "vwap_confirmed_orb",

4) Confirm _bars_held injection before exit calls
Standard injection pattern.

5) CRITICAL: Fix VWAP exit to cover this strategy name
The backtester currently has:
    if exit_reason is None and strategy_name == "orb_breakout":
        exit_reason = _bt_orb_vwap(df, i, trade)

vwap_confirmed_orb has a different strategy name so the VWAP exit never fires.

Two acceptable fixes:

Option A (preferred): Add this strategy name to the backtester check:
    ORB_VWAP_STRATEGIES = frozenset({"orb_breakout", "vwap_confirmed_orb"})

    if exit_reason is None and strategy_name in ORB_VWAP_STRATEGIES:
        exit_reason = _bt_orb_vwap(df, i, trade)

Option B: Add check_custom_exit() to the strategy with VWAP logic:
    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        if bars is None or len(bars) < 5:
            return None
        try:
            # Recompute session VWAP from available bars
            typical  = (bars["high"].astype(float) +
                        bars["low"].astype(float) +
                        bars["close"].astype(float)) / 3.0
            vol      = bars["volume"].astype(float)
            vol_sum  = float(vol.sum())
            if vol_sum <= 0:
                return None
            vwap = float((typical * vol).sum() / vol_sum)
            price = float(bars["close"].iloc[-1])
            if direction == "long"  and price < vwap:
                return "vwap_cross"
            if direction == "short" and price > vwap:
                return "vwap_cross"
        except Exception:
            pass
        return None

Whichever option is used, also apply the same fix to position_monitor.py
for the live trading path.

6) Add preferred_initial_stop_mode and preferred_trail_mode to both signal metadata blocks
Add to both long and short metadata:
    "preferred_initial_stop_mode": "signal_structural",
    "preferred_trail_mode":        "none",

7) Add reviewer_exempt flag
Inspect base_strategy.py.
If reviewer_exempt is a real field, add:
    self.reviewer_exempt = True

8) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not defined there, remove it.

9) Minor: Add a note about design advantages over orb_breakout.py
Near the module docstring, add a brief note:
    # Improvements over orb_breakout.py:
    # - Stale session guard (prevents pre-market using yesterday's ORB)
    # - Max OR width filter (prevents wide ORBs with oversized stops)
    # - Stop cap (structural stop capped at max_stop_pct absolute limit)
    # - Breakout buffer (price must clear ORB level by buffer %)
    # - Stock-only (crypto disabled — VWAP has no reliable 24/7 anchor)

========================================================
DO NOT CHANGE
========================================================

- All entry logic and filter conditions
- Stale session guard (unique improvement — keep it)
- Max OR width filter (unique improvement — keep it)
- Stop cap logic (unique improvement — keep it)
- Breakout buffer logic (unique improvement — keep it)
- Session VWAP implementation
- Whitelist behavior
- Crypto disabled flag and its rationale
- All parameter values
- All metadata fields already present

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/vwap_confirmed_orb.py

Run stock basket:
python intelligence/backtester.py --all \
    --strategy vwap_confirmed_orb --days 30 --tf 5m \
    --asset-class stock \
    --initial-stop signal_structural --trail-stop none

Critical VWAP exit verification:
Check exit reason breakdown after running.
Before fix: vwap_cross would NOT appear (strategy name mismatch)
After fix: vwap_cross should appear alongside stop_loss and take_profit

If vwap_cross still does not appear after the fix:
- Confirm the strategy name check was correctly updated
- Check whether the session window passed to _bt_orb_vwap has enough bars

Compare vs orb_breakout.py on same basket/period:
python intelligence/backtester.py --all --strategy orb_breakout --days 30 --tf 5m --asset-class stock
python intelligence/backtester.py --all --strategy vwap_confirmed_orb --days 30 --tf 5m --asset-class stock

Expected differences:
- vwap_confirmed_orb should have fewer signals (breakout buffer + max width filter)
- When it does signal, average quality should be higher
- Trade count will be lower but hopefully PF/WR improves

Also verify stale session guard:
Run on a weekend or before market hours.
Should produce zero trades with a clear skip log message.

Deliverables:
1. Patched strategy file
2. Patched backtester.py (VWAP exit name fix + TIME_STOP_EXEMPT + registration)
3. Patched strategy_engine.py
4. Position monitor VWAP exit fix (confirmed or added)
5. Stock basket validation
6. Confirmation vwap_cross appears in exit breakdown
7. Head-to-head comparison vs orb_breakout on same basket
8. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — same ORB foundation as the audited version but with better guards
Code quality: cleanest ORB implementation — stale guard, width filter, stop cap all valuable
Implementation completeness: 85% — VWAP exit bug is the main gap
Evidence base: none documented yet — stock-only, no explicit backtest results shown
Salvageable: yes — fixes are targeted
Strong incubate — the design improvements over orb_breakout.py are meaningful:

stale session guard prevents a real class of false signals
max width filter prevents oversized stops
stop cap prevents runaway losses
breakout buffer reduces false entries
If the VWAP exit fix is applied and the stock basket result is reasonable, this could be a clean companion to orb_breakout.py — potentially with better signal quality per trade at the cost of fewer signals.