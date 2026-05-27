My read on RSI Momentum
Overall verdict: Watchlist / disabled — correct logic, minimal integration, no evidence
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Missing metadata in both _make_signal() calls
Both signals pass only:

return self._make_signal(
    symbol    = symbol,
    direction = "long",
    score     = score,
    reason    = "..."
)
No stop, no TP, no metadata dict.

Important — 3) self.logger override
self.logger = logging.getLogger("RSIMomentum")
Same issue as others.

Important — 4) Missing framework flags
stock_enabled, crypto_enabled, candle_limit, reviewer_exempt, time_stop_profile all absent.

Medium — 5) No check_custom_exit()
No RSI-based exit. This strategy should exit when RSI hits overbought/oversold from the other direction. Without it, trades hold until generic stops or configured TP only.

Minor — 6) Score calculation doesn't include volume or trend context
RSI crossback alone has high noise. Adding even basic volume confirmation to the score would improve signal quality without changing entry logic.

What is genuinely good
Correct RSI crossback logic
Oversold depth and overbought height used for scoring
Properly disabled
Clean verbose logging
Claude patch prompt
Patch strategies/rsi_momentum.py and integrate it into the framework.
This strategy is disabled by default — keep it disabled after patching.
Fixes are minimal: integration wiring and metadata completeness.

Files to inspect and patch:
- strategies/rsi_momentum.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt, verbose_log signature)

========================================================
REQUIRED FIXES
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "rsi_momentum": ("strategies.rsi_momentum", "RSIMomentum"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.rsi_momentum import RSIMomentum
    RSIMomentum(),

3) Add metadata to both _make_signal() calls
For long signal:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

    return self._make_signal(
        symbol          = symbol,
        direction       = "long",
        score           = score,
        reason          = "...",
        stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT,
        take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT,
        metadata        = {
            "strategy_name":               "rsi_momentum",
            "rsi":                         round(float(current_rsi), 2),
            "rsi_prev":                    round(float(previous_rsi), 2),
            "rsi_depth":                   round(depth, 4),
            "volume_ratio":                vol_ratio,
            "preferred_initial_stop_mode": "percent",
            "preferred_trail_mode":        "percent",
        }
    )

Apply same pattern for short signal (using height instead of depth,
rsi_height instead of rsi_depth).

4) Add required framework flags to __init__
Add:
    self.stock_enabled   = True
    self.crypto_enabled  = True
    self.candle_limit    = period + 20   # RSI warmup + buffer
    self.reviewer_exempt = True
    self.time_stop_profile = "strategy_defined"

Note: period is read from config at analyze() time.
For candle_limit at init, either hardcode 30 (reasonable default)
or read config.SIGNAL_TUNING["rsi_momentum_period"] + 20.

5) Fix self.logger override
Inspect base_strategy.py for self.logger usage.
Either:
A. Remove: self.logger = logging.getLogger("RSIMomentum")
B. Rename to self._rsi_log

6) Add rsi_momentum to TIME_STOP_EXEMPT
RSI momentum trades benefit from holding through noise.
Add:
    "rsi_momentum",

7) Add simple check_custom_exit() — RSI exits when entering opposite extreme
This is optional but improves parity between entry and exit logic:

    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        if bars is None or len(bars) < 2:
            return None
        try:
            tuning = config.SIGNAL_TUNING
            period = tuning["rsi_momentum_period"]
            rsi    = ta.rsi(bars["close"], length=period)
            if rsi is None or rsi.empty:
                return None
            rsi_now = float(rsi.iloc[-1])
            import math
            if math.isnan(rsi_now):
                return None
            if direction == "long"  and rsi_now >= tuning["rsi_momentum_overbought"]:
                return "rsi_overbought_exit"
            if direction == "short" and rsi_now <= tuning["rsi_momentum_oversold"]:
                return "rsi_oversold_exit"
        except Exception:
            pass
        return None

8) Keep enabled = False
Do NOT re-enable.
Add comment:
    self.enabled = False   # no validated backtest results — enable only after testing

========================================================
DO NOT CHANGE
========================================================

- RSI crossback detection logic
- Score depth/height calculation
- Config-driven thresholds
- disabled state (enabled = False)

========================================================
VALIDATION — LIMITED

Compile:
python -m py_compile strategies/rsi_momentum.py

Optional run for first-ever baseline:
python intelligence/backtester.py --symbol BTC/USD \
    --strategy rsi_momentum --days 365 --tf 1h \
    --asset-class crypto

If run: check whether rsi_overbought_exit appears in exit breakdown.
If not, check_custom_exit injection is not wired.

Deliverables:
1. Patched strategy file
2. Patched backtester.py (registration only)
3. Patched strategy_engine.py (registration only)
4. Confirmation strategy remains disabled
5. Optional first-ever baseline result
My pre-patch classification
Concept: generic mean-reversion RSI — extremely common, thin edge by itself
Code quality: adequate but incomplete
Implementation completeness: 45% — metadata, framework flags, exits all missing
Evidence base: zero
Salvageable: yes, worth keeping as a baseline comparator
Keep disabled / watchlist — like EMA Crossover, this is a reference baseline, not a deployment candidate.

Both rsi_momentum and ema_crossover share the same situation:

they exist as a reference point
they generate trades that can be compared to your newer strategies
they should probably stay disabled unless a multi-year backtested edge is found