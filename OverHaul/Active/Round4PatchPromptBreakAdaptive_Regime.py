Patch strategies/adaptive_regime.py.

Problem The strategy implementation is structurally sound, but live/backtest diagnostics show the entry gates are too restrictive:

Observed behavior

zero or near-zero long trades across broad 1h stock tests
mean_reversion branch is effectively dormant
total trade count is too low for a 1h multi-symbol strategy
when trades do occur, many die early before developing
This suggests the issue is not exits but entry calibration:

ADX trend threshold too high
Donchian breakout lookback too long
trend RSI filters too tight
mean-reversion EMA100 bias filter is too strict
mean-reversion RSI thresholds are too extreme for 1h bars
Required fix Loosen the entry filters modestly without changing the overall architecture.

Make these parameter changes

Change:
ADX_TREND_THRESHOLD from 25 to 22
ADX_RANGE_THRESHOLD from 18 to 19
Change:
BREAKOUT_PERIOD from 20 to 12
Change:
MAX_TREND_ENTRY_RSI from 68 to 72
MIN_TREND_ENTRY_RSI_SHORT from 32 to 28
Add a new constant:
MEAN_EMA_ATR_BUFFER = 0.5
Use it to relax the mean-reversion EMA100 bias filter:

mean-rev long should allow: current_close >= ema_slow - (atr * MEAN_EMA_ATR_BUFFER) instead of strict current_close > ema_slow
mean-rev short should allow: current_close <= ema_slow + (atr * MEAN_EMA_ATR_BUFFER) instead of strict current_close < ema_slow
Relax mean-reversion RSI thresholds slightly:
OVERSOLD_RSI from 30 to 35
OVERBOUGHT_RSI from 70 to 65
Relax trend-mode volume gate slightly:
current code rejects trend mode when volume_ratio < 1.1
change that threshold to 1.0
Implementation details

Keep the same dual-mode structure
Keep the same custom exit logic
Keep ATR-based structural stop logic unchanged
Keep diagnostics counters intact
Update any blocker-diagnostic checks so they reflect the new relaxed conditions
Do not remove diagnostics
Do not change metadata field names
Important This is a calibration patch, not a redesign. Do NOT:

remove ADX regime logic
remove Donchian breakout logic
remove Bollinger mean-reversion logic
change custom exit behavior
change signal metadata schema
Optional cleanup Update the top-of-file docstring if needed so it no longer references the wrong original source filename.

Verify

python -m py_compile strategies/adaptive_regime.py
run: python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar
run: python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar --side long
run: python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar --mode mean_rev
Expected

long trades should no longer be zero / near-zero
mean-reversion mode should begin producing at least some trades
total trade count should increase
diagnostics should still show which blockers dominate

