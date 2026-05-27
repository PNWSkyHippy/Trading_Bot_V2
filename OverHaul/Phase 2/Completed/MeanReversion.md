My read on Mean Reversion
Overall verdict: Watchlist/disabled — long-only with evidence, familiar integration gaps
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Missing metadata completely
Both signals pass:

return self._make_signal(
    symbol    = symbol,
    direction = "long",
    score     = score,
    reason    = "..."
)
No stop, TP, or metadata. Same issue as RSI Momentum and EMA Crossover.

Important — 3) verbose_log() with extra= parameter
self.verbose_log(
    symbol, "Z-score deviation from mean",
    abs(zscore) >= zscore_entry,
    zscore, f">={zscore_entry} or <=-{zscore_entry}",
    extra=f"mean={mean:.4f} std={std:.4f}"
)
Same issue as other strategies.

Important — 4) self.logger override
self.logger = logging.getLogger("MeanReversion")
Same issue as others.

Important — 5) reviewer_exempt not set
Missing.

Important — 6) auto_disable_exempt and ml_exempt — likely not real framework fields
Neither declared but auto_disable_exempt is set to True. Same concern as grid_bot.

Important — 7) candle_limit not set
period from config is used for z-score calculation. Need at least period + 10 bars. Not declared.

Important — 8) stock_candle_timeframe not declared
crypto_enabled = False and stock_enabled = True are set but stock_candle_timeframe is not declared. The engine may default to something unexpected.

Important — 9) time_stop_profile not set
No time stop declared. Generic lifecycle stops will fire.

Medium — 10) enabled = False — keep disabled
self.enabled = False
The strategy is disabled. Comments say "2nd best backtested strategy" but no specific numbers are shown for when it was last run with current config. Keep disabled until validated.

Minor — 11) Whitelist has 100+ symbols from a 5m/30day backtest
The original whitelist from 2yr 1h backtest had 7 symbols. Then 80+ were added from a 5m/30day test. These are different:

Timeframe: 5m vs 1h
Duration: 30 days vs 2 years
A 30-day test on 5m bars has the same sample size concerns as everywhere else in this audit. The 80-symbol addition from a single 30-day test is likely overfitting.

What is genuinely good
Short side is properly disabled with a clear documented reason
Whitelist concept is sound
Z-score calculation is correct
Market condition filter for trending markets
Long-only decision is evidence-based (structural upward drift in equities)
Claude patch prompt
Patch strategies/mean_reversion.py and integrate it into the framework.
This strategy is disabled by default — keep it disabled after patching.
Fixes are minimal: integration wiring and metadata completeness.

Do NOT change the Z-score logic, whitelist, or disabled state.

Files to inspect and patch:
- strategies/mean_reversion.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py
  (inspect: reviewer_exempt, auto_disable_exempt, verbose_log signature)

========================================================
REQUIRED FIXES
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "mean_reversion": ("strategies.mean_reversion", "MeanReversion"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.mean_reversion import MeanReversion
    MeanReversion(),

3) Add mean_reversion to TIME_STOP_EXEMPT
Mean reversion with no custom exit needs time for thesis to play out.
Add:
    "mean_reversion",

4) Add metadata to _make_signal() call
Compute before signal:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

    stop_price = float(current_price) * (1 - config.DEFAULT_STOP_LOSS_PCT / 100)

Add to signal:
    stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT,
    take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT,
    metadata        = {
        "strategy_name":               "mean_reversion",
        "zscore":                      round(float(zscore), 3),
        "z_mean":                      round(float(mean), 4),
        "z_std":                       round(float(std), 4),
        "volume_ratio":                vol_ratio,
        "structural_stop_price":       round(stop_price, 4),
        "preferred_initial_stop_mode": "percent",
        "preferred_trail_mode":        "percent",
    }

5) Add required framework flags to __init__
Add:
    self.stock_candle_timeframe = "1Hour"  # 1h bars for z-score calculation
    self.candle_limit           = 55       # period (default 20) + 35 buffer
    self.reviewer_exempt        = True
    self.time_stop_profile      = "strategy_defined"

6) Fix self.logger override
Inspect base_strategy.py.
Either:
A. Remove: self.logger = logging.getLogger("MeanReversion")
B. Rename to self._mr_log

7) Fix verbose_log() extra= parameter
Check base_strategy.py verbose_log() signature.
If extra= is not valid:
    self.verbose_log(
        symbol, "Z-score deviation from mean",
        abs(zscore) >= zscore_entry,
        f"z={zscore:.3f} [mean={mean:.4f} std={std:.4f}]",
        f"±{zscore_entry}",
    )

8) Verify auto_disable_exempt
Inspect base_strategy.py.
If auto_disable_exempt is NOT a recognized attribute:
- Add comment explaining intent
- Do NOT remove it silently

9) Keep enabled = False
Add comment:
    self.enabled = False   # no validated backtest under current config — enable only after testing

Note: whitelist includes 80+ symbols from a 5m/30day test mixed with the
original 2yr/1h set. Consider separating into two whitelists and only
enabling the 2yr/1h validated set initially.

========================================================
DO NOT CHANGE
========================================================

- Z-score calculation
- Long-only design (shorts disabled by design)
- Whitelist structure
- Market condition filter
- disabled state (enabled = False)

========================================================
VALIDATION — LIMITED

Compile:
python -m py_compile strategies/mean_reversion.py

Optional baseline run (requires temporarily enabling):
python intelligence/backtester.py --symbol NVDA \
    --strategy mean_reversion --days 180 --tf 1h \
    --asset-class stock

Deliverables:
1. Patched strategy file
2. Patched backtester.py (registration only)
3. Patched strategy_engine.py (registration only)
4. Confirmation strategy stays disabled
5. Optional: first-ever baseline on NVDA/PLTR against original 2yr/1h claim
My pre-patch classification
Concept: solid — Z-score mean reversion on volatile individual stocks is well-motivated
Code quality: adequate but incomplete integration
Implementation completeness: 45% — metadata completely missing
Evidence base: 7 original symbols with 2yr/1h backtest + 80 symbols from 30-day 5m (mixed quality)
Salvageable: yes, but whitelist should be split
Keep disabled / watchlist — like EMA Crossover and RSI Momentum, this is a baseline candidate. The long-only design is the right call, and the 7-symbol 2yr/1h validated whitelist is real evidence. The 80-symbol expansion from a 30-day test is the concern.