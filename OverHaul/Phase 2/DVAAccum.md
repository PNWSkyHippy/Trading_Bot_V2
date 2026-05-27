My read on DCA Accumulator
Overall verdict: Watchlist/Healthy — live evidence is best so far, familiar integration gaps
Issues I found
Critical — 1) Not registered
Last one. Same as all others.

Critical — 2) Missing metadata in _make_signal()
return self._make_signal(
    symbol    = symbol,
    direction = "long",
    score     = score,
    reason    = "..."
)
No stop, TP, or metadata dict.

Critical — 3) Not in TIME_STOP_EXEMPT — but this one is already there
From the backtester code seen earlier:

TIME_STOP_EXEMPT = frozenset({"grid_bot", "dca_accumulator"})
Already exempt. No change needed. Just confirm.

Critical — 4) verbose_log() with extra= parameter
self.verbose_log(
    symbol, f"Price is {dip_pct*100:.1f}%+ below EMA{ema_period}...",
    below_ema,
    price_vs_ema,
    f"<={required_dip:.4f}",
    "long",
    extra=f"price={current_price:.4f} EMA{ema_period}={ema_value:.4f}"
)
Same issue as several other strategies.

Important — 5) self.logger override
self.logger = logging.getLogger("DCAAccumulator")
Same issue as others.

Important — 6) stock_enabled and crypto_enabled not explicitly declared
stock_candle_timeframe and crypto_candle_timeframe are set, but stock_enabled and crypto_enabled are not. The engine may not know which asset classes are active.

Important — 7) ml_exempt and auto_disable_exempt — likely not real framework fields
auto_disable_exempt is not set in __init__() at all — it's referenced in the comments but the attribute doesn't exist in the code. The code has:

# NEVER auto-disable mean_reversion — 2nd best backtested strategy
self.auto_disable_exempt = True
Wait, that's in mean_reversion.py. In dca_accumulator.py, auto_disable_exempt is referenced in the comments but NOT declared in __init__. This is a bug — the protection that the comment describes doesn't actually exist.

Important — 8) candle_limit is set to 200 but required in analyze uses ema_period + 5
ema_period defaults to 50 from config, so required = 55. candle_limit = 200 is generous. This is fine — but means the first ~145 bars are used for warmup context beyond what's strictly needed.

Medium — 9) Pivot exit conflict documented but not addressed in code
The audit correctly identifies that pivot_break_s1 acts as a ~0.13% effective stop instead of the designed 2% stop. This is a position_monitor issue, not a strategy code issue. The "next steps" say to either widen pivot bars or add a pivot_exempt flag for DCA — neither has been implemented yet.

Minor — 10) volume_ratio missing from metadata
What is genuinely good
Best P&L of all audited strategies — +$36.30 with 47% WR, 13.7pp above breakeven
Honest audit documentation — pivot exit conflict identified and explained
RSI tightening from 45→35 is evidence-based from 92-combo sweep
Long-only with documented rationale — correct for DCA concept
reviewer_exempt = True correctly set with clear reasoning
stop_loss_pct = 2.0 and take_profit_pct = 5.0 correctly set in __init__() — these will be the fallback since metadata doesn't pass stop/TP yet
Whitelist is well-maintained with crypto symbols
Claude patch prompt
Patch strategies/dca_accumulator.py and register it in the bot framework.

This is the best-performing audited strategy (+$36.30 live, 47% WR).
Fixes are minimal — do NOT change any trading logic.

Files to inspect and patch:
- strategies/dca_accumulator.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py
  (inspect: reviewer_exempt, ml_exempt, auto_disable_exempt, verbose_log signature)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "dca_accumulator": ("strategies.dca_accumulator", "DCAAccumulator"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.dca_accumulator import DCAAccumulator
    DCAAccumulator(),

3) Confirm dca_accumulator is in TIME_STOP_EXEMPT in backtester.py
Verify:
    TIME_STOP_EXEMPT = frozenset({"grid_bot", "dca_accumulator", ...})

If it IS already there, confirm and leave it.
If NOT there, add it immediately — DCA holds positions longer than generic stops.

4) CRITICAL: Add auto_disable_exempt to __init__
The code COMMENTS say "NEVER auto-disable" but the attribute is never declared.
The protection described in the comment doesn't actually exist.

Inspect base_strategy.py:
If auto_disable_exempt IS a recognized attribute:
    Add to __init__: self.auto_disable_exempt = True
If NOT recognized:
    Add it with a comment documenting the intent:
        # auto_disable_exempt = True
        # INTENT: Do not auto-disable based on stale pre-RSI35-sweep data
        # Current live: 17 trades, 47% WR (above 33.4% breakeven) — healthy
        # TODO: Add auto_disable_exempt to base_strategy.py with engine support
        self.auto_disable_exempt = True

5) Add metadata to _make_signal() call
Compute:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None
    stop_price = float(current_price) * (1 - self.stop_loss_pct / 100)

Add to signal:
    stop_loss_pct   = self.stop_loss_pct,
    take_profit_pct = self.take_profit_pct,
    metadata        = {
        "strategy_name":               "dca_accumulator",
        "ema_value":                   round(float(ema_value), 4),
        "price_vs_ema_pct":            round(float(price_vs_ema) * 100, 3),
        "rsi":                         round(float(current_rsi), 2),
        "dip_depth":                   round(float(dip_depth), 3),
        "rsi_depth":                   round(float(rsi_depth), 3),
        "volume_ratio":                vol_ratio,
        "structural_stop_price":       round(stop_price, 4),
        "preferred_initial_stop_mode": "percent",
        "preferred_trail_mode":        "percent",
    }

6) Add explicit stock_enabled and crypto_enabled flags to __init__
Add:
    self.stock_enabled   = True
    self.crypto_enabled  = True

7) Fix self.logger override
Inspect base_strategy.py for self.logger usage.
Either:
A. Remove: self.logger = logging.getLogger("DCAAccumulator")
B. Rename to self._dca_log

8) Fix verbose_log() extra= parameter
Check base_strategy.py verbose_log() signature.
If extra= is not valid:
    self.verbose_log(
        symbol, f"Price {dip_pct*100:.1f}%+ below EMA{ema_period}",
        below_ema,
        f"{price_vs_ema:.4f} [price={current_price:.4f} ema={ema_value:.4f}]",
        f"<={required_dip:.4f}",
        "long",
    )

9) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not defined there, remove it.
reviewer_exempt = True is already correctly set — keep it.

10) Document pivot exit conflict concern
Near the audit section in the docstring or in a comment near stop_loss_pct, add:

    # OPEN ISSUE: pivot_break_s1 exit acts as ~0.13% effective stop instead of
    # designed 2% stop. DCA enters at dip → pivot S1 sits just below entry.
    # Fix options: increase PIVOT_EXIT_BARS 20→40 OR add pivot_exempt in position_monitor
    # Track: 8/17 live trades (47%) exited via pivot_break_s1 at -0.134% avg

========================================================
DO NOT CHANGE
========================================================

- EMA dip logic
- RSI oversold filter (already updated to rsi_max=35 per sweep)
- Long-only design
- Whitelist membership
- stop_loss_pct = 2.0
- take_profit_pct = 5.0
- candle_limit = 200
- All audit documentation and iteration changelog

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/dca_accumulator.py

Confirm TIME_STOP_EXEMPT includes dca_accumulator:
Check backtester.py — should already be there.

Run crypto basket under RSI35 config:
python intelligence/backtester.py --all \
    --strategy dca_accumulator --days 90 --tf 1h \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Note: RSI<35 fires rarely — expect low trade count on 90d basket.
That's expected. Compare trade count before/after RSI45→35 change.

Stock basket:
python intelligence/backtester.py --all \
    --strategy dca_accumulator --days 90 --tf 1h \
    --asset-class stock

Note: Audit says stocks have been dormant in May 2026 uptrend.
Low or zero stock trades is expected behavior, not a bug.

Verify metadata appears in logs:
- ema_value, price_vs_ema_pct, rsi should all be present
- rsi should be <= 35 for any signal that fires

Target comparison:
Live baseline: 47% WR (17 trades, RSI45 config)
New RSI35 target: fewer trades but WR >= 42% (breakeven is 33.4%)

Deliverables:
1. Patched strategy file
2. Patched backtester.py (registration + TIME_STOP_EXEMPT confirmation)
3. Patched strategy_engine.py
4. auto_disable_exempt status confirmed or added
5. Crypto basket results under RSI35 config
6. Stock basket results (expect dormant in uptrend)
7. Confirmation metadata appears in logs
8. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — EMA dip + RSI oversold for systematic accumulation is well-motivated
Code quality: adequate, familiar gaps
Implementation completeness: 60% — metadata completely missing, auto_disable_exempt not actually declared
Evidence base: best in the batch alongside grid_bot — 17 live exits with clear P&L attribution
Salvageable: yes — already the best-performing audited strategy
Watchlist/Healthy — the most important post-patch step is confirming auto_disable_exempt is actually protecting the strategy (the comment exists but the attribute never gets declared), and then monitoring whether RSI35 maintains the 47% WR over 50+ trades.

