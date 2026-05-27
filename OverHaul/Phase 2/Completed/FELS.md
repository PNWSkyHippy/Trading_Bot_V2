My read on FELS
Overall verdict: Watchlist (Reject classification needs update) — clean concept, missing TP exit and preferred_initial_stop_mode
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
16-bar max hold on 1h. Same pattern.

Critical — 3) check_custom_exit() is too minimal — TP exit never fires
Current check_custom_exit() only implements the time stop:

def check_custom_exit(self, symbol, bars, direction, entry_metadata=None):
    meta = entry_metadata or {}
    bars_held = int(meta.get("_bars_held", 0))
    if bars_held >= self.params.max_bars_hold:
        return "fels_max_hold"
    return None
The thesis exit — reaching the TP midpoint price — never fires. The executor will use the static tp_pct for TP (which is computed dynamically from sweep range in analyze()). That's actually fine since tp_pct is passed to _make_signal(). But there's a subtlety: if the TP dynamic computation produces a different TP price than what the executor uses (because the executor may be applying tp_pct as a static percentage from entry), the intended sweep-range based TP won't be honored exactly.

For correctness, the TP should fire via the executor's built-in logic since tp_pct is set. The time stop in check_custom_exit() is the only custom exit needed. This is actually okay — unlike ECB where the Z-score exit was the primary thesis exit, here the TP exit is just a percentage target that the executor can handle.

However — worth adding a note about this.

Critical — 4) _bars_held injection needed
Same pattern.

Important — 5) preferred_initial_stop_mode missing from metadata
Has preferred_trail_mode but not preferred_initial_stop_mode.

Important — 6) TP calculation may produce negative values for degenerate cases
sweep_range = high_ - prior_high.loc[last] if not pd.isna(prior_high.loc[last]) else atr_
tp_price    = cls - sweep_range * p.tp_revert_pct - atr_ * 0.5
tp_pct      = round((cls - tp_price) / cls * 100, 3)
If sweep_range is very small (breakout barely pierced the high), tp_pct could be tiny or even negative before the max(tp_pct, 0.3) guard catches it. The guard at the end helps but the TP price itself could still be wrong.

Important — 7) Volume spike check references the breakout bar specifically
vol_spike = df["volume"] >= vol_ma * p.vol_spike_min
This checks if current bar volume is elevated — not the breakout bar volume specifically. If the signal fires on the breakout bar, this is correct. But worth noting.

Important — 8) ml_exempt likely not a real framework field
Same as others.

Medium — 9) volume_ratio missing from metadata
Minor — 10) Classification says "Reject v1" but v1 exits were broken
Same issue as RARE. The Python version has correct exits (time stop). Should be reclassified as Watchlist.

What is genuinely good
Concept is sound — failed extension / liquidity sweep rejection is a real institutional pattern
ATR-normalized breakout failure threshold is clean
Volume spike confirmation on the breakout bar is appropriate
Stop beyond the wick extreme is the correct structural stop for this pattern
TP at midpoint of sweep is the natural reversion target
ADX ranging filter is appropriate for this type of entry
structural_stop_price in metadata
_entry_bar_time fallback for live parity
Claude patch prompt
Patch strategies/fels_strategy.py and register it in the bot framework.

This strategy is mostly complete. Fixes are standard plus one structural note.
Do NOT change the failed breakout detection logic or ADX filter.

Files to inspect and patch:
- strategies/fels_strategy.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: ml_exempt)

========================================================
REQUIRED FIXES
========================================================

1) Register in backtester.py strategy_map
Add:
    "fels_strategy": ("strategies.fels_strategy", "FELSStrategy"),

2) Register in strategy_engine.py
Add:
    from strategies.fels_strategy import FELSStrategy
    FELSStrategy(),

3) Add fels_strategy to TIME_STOP_EXEMPT in backtester.py
16-bar max hold on 1h. Generic lifecycle stops will fire first.
Add:
    "fels_strategy",

4) Confirm _bars_held injection before check_custom_exit()
Standard injection pattern.

5) Add preferred_initial_stop_mode to metadata
Add:
    "preferred_initial_stop_mode": "signal_structural",

6) Add volume_ratio to metadata
Compute before the signal blocks:
    vol_series = candles["volume"]
    vol_ma_20 = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma_20), 3) if vol_ma_20 > 0 else None

Add to metadata:
    "volume_ratio": vol_ratio,

7) Note on TP exit mechanism
The FELS thesis exit (reaching TP midpoint price) is handled by the executor
via the static tp_pct passed to _make_signal(). The check_custom_exit() only
needs the time stop. This is acceptable — add a comment for clarity:

    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        """
        Time stop only. TP is handled by executor using tp_pct from analyze().
        The TP target (sweep midpoint) is encoded in tp_pct at signal generation.
        """
        meta = entry_metadata or {}
        bars_held = int(meta.get("_bars_held", 0))
        if bars_held >= self.params.max_bars_hold:
            return "fels_max_hold"
        return None

8) Update classification in docstring
Change:
    Classification : Reject v1 (Trader Dev result: PF 1.11, exits broken)
To:
    Classification : Watchlist (v1 Trader Dev exits broken; v2 Python
                     exits correct — first validation pending)

9) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not recognized, remove it.

========================================================
DO NOT CHANGE
========================================================

- Failed breakout detection (swept_high, close_near_level_high, vol_spike)
- Stop price calculation (wick + ATR buffer)
- TP price calculation (sweep range fraction)
- ADX ranging filter
- Volume spike confirmation
- Score formula
- All FELSParams default values

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/fels_strategy.py

First-ever run with correct exits:
python intelligence/backtester.py --all \
    --strategy fels_strategy --days 365 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Exit reason check:
- take_profit should appear (executor handles this via tp_pct)
- stop_loss should appear occasionally
- fels_max_hold should appear for slow trades
- Generic lifecycle stops should NOT dominate

Target: PF > 1.0 with correct exits
Original v1 broken PF was 1.11 — correct exits may improve or worsen this.

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. First-ever basket results with correct exits
5. Exit reason breakdown
6. Updated classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — failed extension / liquidity sweep rejection is a well-documented pattern in institutional trading
Code quality: clean, correct breakout detection, good structural stop placement
Implementation completeness: 85% — just missing metadata hints and registration
Evidence base: none with correct exits — v1 was broken
Salvageable: yes
Watchlist — the concept has practitioner backing (institutional stop hunt dynamics are real). Whether the ATR-normalized failed breakout filter provides enough selectivity on crypto 1h will be the key question.