My read on Swing Trader
Overall verdict: Watchlist/enabled — correct logic, same familiar integration gaps, no evidence documented
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Missing metadata in both _make_signal() calls
Both long and short pass only symbol, direction, score, reason. No stop, TP, or metadata.

Important — 3) verbose_log() with extra= parameter
self.verbose_log(
    symbol, "ADX confirms trend...",
    trend_confirmed, adx_value, f">={adx_min}",
    extra=f"+DI={dmp_value:.2f} -DI={dmn_value:.2f}" if dmp_value and dmn_value else ""
)
Same issue as others.

Important — 4) self.logger override
self.logger = logging.getLogger("SwingTrader")
Same issue as others.

Important — 5) Missing framework flags
Not declared:

stock_enabled
crypto_enabled
reviewer_exempt
time_stop_profile
candle_limit — wait, this IS set to 200. Good.
Important — 6) enabled = True — strategy is live with no documented evidence
Unlike EMA Crossover and RSI Momentum which are correctly disabled, this is enabled without any audit or backtest evidence documented in the file. The only comment is "swing_trader shows proper trade counts and GO results" at 1hr/365 days — but no specific numbers are shown.

Medium — 7) bullish_trend = True fallback when DI data unavailable is wrong
if dmp_value is not None and dmn_value is not None:
    bullish_trend = dmp_value > dmn_value
else:
    bullish_trend = True  # Assume bullish if DI data unavailable
Defaulting to True when direction data is missing will silently generate long signals on any trending market with no DI data. Should default to False to fail safe.

Minor — 8) No check_custom_exit() or time stop
Wider SL (2.5%) and larger TP (6%) suggest swing trades are meant to run. Generic lifecycle stops may interfere, especially the 8h hard stop. Strategy needs TIME_STOP_EXEMPT.

Minor — 9) No evidence of what symbols it runs on
No whitelist, no stock_enabled/crypto_enabled. Will run on everything the engine feeds it.

What is genuinely good
ADX + DI direction is the correct approach for trend-following
RSI pullback timing within a confirmed trend is sound logic
candle_limit = 200 and stock_candle_timeframe = "1Hour" are set
stop_loss_pct = 2.5 and take_profit_pct = 6.0 match the swing trading thesis
Claude patch prompt
Patch strategies/swing_trader.py and register it in the bot framework.
The strategy is enabled but has no documented evidence — fixes are purely
integration wiring. Do NOT change any trading logic.

Files to inspect and patch:
- strategies/swing_trader.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt, verbose_log signature)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "swing_trader": ("strategies.swing_trader", "SwingTrader"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.swing_trader import SwingTrader
    SwingTrader(),

3) Add swing_trader to TIME_STOP_EXEMPT in backtester.py
Swing trades with 2.5% SL and 6% TP need room to develop.
Generic 8h hard stop will kill valid developing trades.
Add:
    "swing_trader",

4) Add metadata to both _make_signal() calls
For long signal:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

    stop_price = float(candles["close"].iloc[-1]) * (1 - self.stop_loss_pct / 100)

    return self._make_signal(
        symbol          = symbol,
        direction       = "long",
        score           = score,
        reason          = "...",
        stop_loss_pct   = self.stop_loss_pct,
        take_profit_pct = self.take_profit_pct,
        metadata        = {
            "strategy_name":               "swing_trader",
            "adx":                         round(float(adx_value), 2),
            "dmp":                         round(float(dmp_value), 2) if dmp_value else None,
            "dmn":                         round(float(dmn_value), 2) if dmn_value else None,
            "rsi":                         round(float(current_rsi), 2),
            "volume_ratio":                vol_ratio,
            "structural_stop_price":       round(stop_price, 4),
            "preferred_initial_stop_mode": "percent",
            "preferred_trail_mode":        "percent",
        }
    )

Do the same for short signal (stop_price = close * (1 + sl_pct / 100)).

5) Fix bullish_trend fallback default
Current:
    bullish_trend = True  # Assume bullish if DI data unavailable

Change to:
    bullish_trend = False  # Fail safe — don't assume direction without data

6) Fix verbose_log() extra= parameter
Check base_strategy.py verbose_log() signature.
If extra= is not valid:
    self.verbose_log(
        symbol, "ADX confirms trend",
        trend_confirmed,
        f"adx={adx_value:.1f} +DI={dmp_value:.2f} -DI={dmn_value:.2f}"
        if dmp_value and dmn_value
        else f"adx={adx_value:.1f}",
        f">={adx_min}",
    )

7) Fix self.logger override
Inspect base_strategy.py for self.logger usage.
Either:
A. Remove: self.logger = logging.getLogger("SwingTrader")
B. Rename to self._swing_log

8) Add required framework flags to __init__
Add:
    self.stock_enabled     = True
    self.crypto_enabled    = True
    self.reviewer_exempt   = True
    self.time_stop_profile = "strategy_defined"

9) Add evidence note to __init__
Near self.enabled = True, add a comment:
    self.enabled = True
    # NOTE: No backtest results documented in this file.
    # Comment says "GO results at 1hr/365 days" but no specific PF/WR/DD shown.
    # Run baseline validation before trusting live signals:
    #   python intelligence/backtester.py --all --strategy swing_trader
    #         --days 365 --tf 1h --asset-class stock

========================================================
DO NOT CHANGE
========================================================

- ADX trend confirmation logic
- +DI/-DI direction filter
- RSI pullback/extension entry timing
- Long and short signal logic
- stop_loss_pct = 2.5 and take_profit_pct = 6.0

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/swing_trader.py

Run first documented baseline:
python intelligence/backtester.py --all \
    --strategy swing_trader --days 365 --tf 1h \
    --asset-class stock

python intelligence/backtester.py --all \
    --strategy swing_trader --days 365 --tf 1h \
    --asset-class crypto

This produces the first documented baseline for this strategy.

Exit reason check:
- stop_loss and take_profit should appear
- Generic lifecycle stops (hard_time_stop) should NOT dominate
  (if they do, TIME_STOP_EXEMPT wasn't applied)

Key verification:
The bullish_trend fallback fix — confirm that the log no longer shows
long signals when DI data is unavailable.

Deliverables:
1. Patched strategy file
2. Patched backtester.py (TIME_STOP_EXEMPT + registration)
3. Patched strategy_engine.py
4. First-ever documented baseline results
5. Confirmation bullish_trend fallback now defaults to False
6. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — ADX trend + DI direction + RSI pullback timing is well-established
Code quality: adequate, missing integration pieces
Implementation completeness: 50% — metadata completely missing
Evidence base: zero documented — "GO results" mentioned but no specific numbers
Salvageable: yes — worth running the baseline backtest immediately
Watchlist — enabled but no evidence documented. The baseline backtest should be the first post-patch action. Given that it uses ADX trend confirmation + DI direction, it's structurally similar to adaptive_regime's trend mode (which was salvaged). Whether it produces better results than the simpler strategies will tell you if the ADX/DI filtering is worth the extra complexity.