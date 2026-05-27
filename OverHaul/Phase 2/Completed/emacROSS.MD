My read on EMA Crossover
Overall verdict: Minimal viable — correct logic, incomplete integration, but evidence-free and kept disabled for good reason
Issues I found
Critical — 1) Not registered
self.enabled = False
It's disabled, but still needs to be registered for backtesting.

Critical — 2) Missing metadata completely
Both signals call _make_signal() without any metadata dict:

return self._make_signal(
    symbol    = symbol,
    direction = "long",
    score     = score,
    reason    = "..."
)
No stop/TP/structural stop/indicators passed.

This means:

Executor gets no stop price hint — uses default percent stop
Reviewer gets nothing useful to evaluate
No preferred_initial_stop_mode or preferred_trail_mode
Critical — 3) verbose_log() with extra= parameter at the end
self.verbose_log(
    symbol, "No EMA crossover (no signal)",
    False,
    f"fast={fast_now:.4f}",
    f"slow={slow_now:.4f}",
    extra=f"trend={trend_now:.4f}"
)
Same issue as other strategies — if verbose_log() doesn't accept extra=, this throws TypeError on every skipped bar.

Important — 4) self.logger override
self.logger = logging.getLogger("EMACrossover")
Same issue as scalp_master and bollinger_squeeze. May break framework logging.

Important — 5) stock_enabled, crypto_enabled, candle_limit, reviewer_exempt not set
Missing all of these.

Important — 6) No check_custom_exit() or time stop
No custom exit logic. Relies entirely on generic stops.

Medium — 7) Score calculation looks fragile
separation = abs(fast_now - slow_now) / slow_now if slow_now != 0 else 0
score = min(1.0, min_score + separation * 10)
For typical EMA crossovers:

EMA separation might be 0.1-0.5% on most assets
separation * 10 would be 0.01-0.05
So score barely moves above min_score. Fine functionally but a bit dead.

Medium — 8) No time_stop_profile set
Generic lifecycle stops will fire.

What is genuinely good
Logic is correct and clean
Crossover detection is proper (checks prev and current)
Separation bonus is reasonable
Trend filter is sensible
Correctly disabled by default
No fake metadata (it's just completely absent rather than fake)
Claude patch prompt
This one is short because the strategy is basic and disabled by default.

Patch strategies/ema_crossover.py and integrate it into the framework.
This strategy is disabled by default — keep it disabled after patching.
Fixes are minimal: integration wiring and metadata completeness.

Files to inspect and patch:
- strategies/ema_crossover.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt, verbose_log signature)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "ema_crossover": ("strategies.ema_crossover", "EMACrossover"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.ema_crossover import EMACrossover
    EMACrossover(),

3) Add metadata to both _make_signal() calls
Both golden cross and death cross signals currently send no metadata.

For golden cross (long):
    stop_price = float(close.iloc[-1]) * (1 - config.DEFAULT_STOP_LOSS_PCT / 100)
    return self._make_signal(
        symbol          = symbol,
        direction       = "long",
        score           = score,
        reason          = "...",
        stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT,
        take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT,
        metadata        = {
            "strategy_name":               "ema_crossover",
            "ema_fast":                    round(float(fast_now), 4),
            "ema_slow":                    round(float(slow_now), 4),
            "ema_trend":                   round(float(trend_now), 4),
            "price_above_trend":           bool(above_trend),
            "separation_pct":              round(separation * 100, 4),
            "preferred_initial_stop_mode": "percent",
            "preferred_trail_mode":        "percent",
        }
    )

Do the same for short (death cross) with appropriate field names.

Also compute and include volume_ratio:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

Add to metadata:
    "volume_ratio": vol_ratio,

4) Add required framework flags to __init__
Add:
    self.stock_enabled  = True
    self.crypto_enabled = True
    self.candle_limit   = trend_period + 20  # EMA trend warmup + buffer
    self.reviewer_exempt = True
    self.time_stop_profile = "strategy_defined"

Note: candle_limit needs the trend period value — either hardcode 70
or access config.SIGNAL_TUNING["ema_trend_period"] if available at init time.

5) Fix self.logger override
Same issue as bollinger_squeeze and scalp_master.
Inspect base_strategy.py for self.logger usage.
Either:
A. Remove: self.logger = logging.getLogger("EMACrossover")
   and use inherited self.logger throughout
B. Rename to self._ema_log to avoid overriding base class field

6) Fix verbose_log() extra= parameter
The no-signal verbose_log call uses extra= which may not be a valid parameter.
Check base_strategy.py verbose_log() signature.
If extra= is not valid:
- Remove the extra= argument
- Inline the trend info into the value string:
    self.verbose_log(
        symbol, "No EMA crossover (no signal)",
        False,
        f"fast={fast_now:.4f} trend={trend_now:.4f}",
        f"slow={slow_now:.4f}",
    )

7) Add ema_crossover to TIME_STOP_EXEMPT
EMA crossover is a trend-following strategy that can hold trades for
multiple sessions. Generic 8h hard stop is inappropriate.
Add:
    "ema_crossover",

8) Keep enabled = False
Do NOT re-enable this strategy.
It has no validated backtest results and was disabled before this audit.
Leave:
    self.enabled = False

Add a comment:
    self.enabled = False   # no validated backtest results — enable only after testing

========================================================
DO NOT CHANGE
========================================================

- EMA crossover detection logic (golden/death cross)
- Trend filter (price above/below trend EMA)
- Separation-based score calculation
- Timeframe/period source from config.SIGNAL_TUNING
- disabled state (enabled = False)

========================================================
VALIDATION — LIMITED

Since this strategy is disabled, validation is just compile check
and confirming metadata appears when forced on test symbols.

Compile:
python -m py_compile strategies/ema_crossover.py

Optional backtester run (requires temporarily enabling):
python intelligence/backtester.py --symbol BTC/USD \
    --strategy ema_crossover --days 365 --tf 1h \
    --asset-class crypto

This provides the first-ever evidence baseline.
If PF < 1.0 it confirms why it was disabled.
If PF > 1.0 it warrants closer testing.

Deliverables:
1. Patched strategy file
2. Patched backtester.py (registration only)
3. Patched strategy_engine.py (registration only)
4. Short note confirming strategy stays disabled
5. Optional: first-ever baseline backtest result if run
My pre-patch classification
Concept: generic — EMA crossover is the most common strategy in trading; the edge is thin at best
Code quality: adequate but incomplete
Implementation completeness: 50% — metadata completely missing
Evidence base: zero — no backtest results, kept disabled by design
Salvageable: yes, but only worth testing as a baseline reference
Keep disabled / watchlist — this is a useful baseline comparator to measure other strategies against, not a deployment candidate.