This one is reasonably complete but has the familiar set of missing integration pieces.

My read on VWAP Momentum
Overall verdict: Incubate — mostly correct, some important gaps
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) _make_signal() missing stop_loss_pct and take_profit_pct
Both long and short signals pass:

return self._make_signal(
    symbol    = symbol,
    direction = "long",
    score     = score,
    reason    = "...",
    metadata  = {**base_metadata, "signal_type": "vwap_long"}
)
No stop_loss_pct or take_profit_pct.

The executor falls back to config.DEFAULT_STOP_LOSS_PCT and config.DEFAULT_TAKE_PROFIT_PCT, which are already set in __init__() — so this is less dangerous than bollinger_breakout, but still means the signal doesn't explicitly carry its own stop/TP values.

Critical — 3) Not in TIME_STOP_EXEMPT
Strategy uses 1h bars with stock_candle_timeframe = "1Hour".

Generic lifecycle stops on 1h bars:

EARLY_LOSS_BARS = 1 bar = 1 hour
PERF_2HR_BARS = 2 bars = 2 hours
HARD_STOP_BARS = 8 bars = 8 hours
The strategy explicitly mentions a "90-minute time-stop" via entry_time_utc metadata. But the check_custom_exit() method doesn't exist to implement it. And the generic stops will fire before or at the same time as the intended 90-minute window.

Critical — 4) 90-minute time stop in metadata but no check_custom_exit() to enforce it
"entry_time_utc": datetime.now(timezone.utc).isoformat(),
"time_stop_min":  90,
The docstring says:

Metadata includes entry_time_utc for position_monitor's 90-minute time-stop

But there is no check_custom_exit() that reads these values and fires the exit. The metadata is stored but never acted on.

Critical — 5) _bars_held injection needed
Same pattern.

Important — 6) structural_stop_price missing from metadata
Metadata has vwap, ema5, ema13, ema34, adx, rsi, volume_ratio — all real values. But it's missing:

"structural_stop_price":       ...,
"preferred_initial_stop_mode": "percent",
"preferred_trail_mode":        "percent",
Important — 7) self.logger override
self.logger = logging.getLogger("VWAPMomentum")
Same issue as other strategies.

Important — 8) stock_enabled not explicitly declared
crypto_enabled = False is set but stock_enabled is not declared. May default to whatever BaseStrategy.__init__() sets.

Important — 9) reviewer_exempt not set
Missing.

Important — 10) time_stop_profile not set
Should be "strategy_defined" since the strategy intends a 90-minute time stop.

Important — 11) ml_exempt likely not a real framework field
Same as other strategies.

Medium — 12) _calc_vwap() is a full-session cumulative VWAP
This is correct behavior for intraday VWAP. However:

The candles passed to analyze() may contain multiple sessions of data
The cumulative sum starts from the first bar in candles, not from the current session open
This means pre-market or prior-day bars pollute the VWAP calculation
The ORB strategies solve this with _session_bars() to filter to today only. This strategy doesn't do that, so the VWAP may be anchored to an earlier session.

Minor — 13) Docstring says 5-minute bars but code uses 1h
# Docstring: "Timeframe: 5-minute bars (stock market hours only)"
# Code: self.stock_candle_timeframe = "1Hour"
Comment says the strategy was moved from 5m to 1h. The docstring is outdated.

What is genuinely good
Clean multi-filter structure: VWAP + EMA triple stack + ADX + RSI zone + volume
RSI hard block for exhaustion is thoughtful and documented with a real lesson (IONQ)
Whitelist of high-liquidity momentum names is appropriate
Real metadata values — no fake RSI/ADX/EMA like VDMR
entry_time_utc for time-stop concept is correct thinking
Good logging throughout
market_condition == "ranging" check is sensible
Claude patch prompt
Patch strategies/vwap_momentum.py and register it in the bot framework.
The strategy logic is mostly sound. Fixes are integration and completeness only.

Do NOT change entry conditions, whitelist, RSI hard blocks, or parameter values.

Files to inspect and patch:
- strategies/vwap_momentum.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py
  (inspect: reviewer_exempt, ml_exempt, stock_enabled, verbose_log signature)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add:
    "vwap_momentum": ("strategies.vwap_momentum", "VWAPMomentum"),

2) Register in strategy_engine.py
Add:
    from strategies.vwap_momentum import VWAPMomentum
    VWAPMomentum(),

3) Add vwap_momentum to TIME_STOP_EXEMPT in backtester.py
On 1h bars, early_loss fires at 1 bar = 1 hour.
Strategy intends a 90-minute time stop — generic lifecycle stops kill this.
Add:
    "vwap_momentum",

4) Add stop_loss_pct and take_profit_pct to both _make_signal() calls
Both long and short currently pass no explicit stop/TP.

For both signals, add:
    stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT,
    take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT,

5) Add missing metadata fields to base_metadata dict
Current base_metadata is missing stop hints.

Add to base_metadata:
    "strategy_name":               "vwap_momentum",
    "entry_timeframe":             "1h",
    "preferred_initial_stop_mode": "percent",
    "preferred_trail_mode":        "percent",

Also compute and add:
    vol_series = candles["volume"]
    vol_ma_val = vol_series.rolling(20).mean().iloc[-1]
    # vol_ratio is already computed as cur_vol_ratio — rename or reuse:
    # "volume_ratio" is already in base_metadata as cur_vol_ratio

Add structural_stop_price as an approximate percent-based stop price:
    stop_price_long  = current_close * (1 - config.DEFAULT_STOP_LOSS_PCT / 100)
    stop_price_short = current_close * (1 + config.DEFAULT_STOP_LOSS_PCT / 100)

In long signal metadata: add "structural_stop_price": round(stop_price_long, 4)
In short signal metadata: add "structural_stop_price": round(stop_price_short, 4)

6) Add check_custom_exit() with 90-minute time stop
The metadata stores entry_time_utc and time_stop_min but nothing reads them.

Implement:
    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        if bars is None or len(bars) < 1:
            return None
        meta      = entry_metadata or {}
        bars_held = int(meta.get("_bars_held", 0))

        # 90-minute time stop on 1h bars = ~1.5 bars
        # Use bars_held for consistency with other strategies
        time_stop_min  = int(meta.get("time_stop_min", 90))
        bars_for_stop  = max(1, time_stop_min // 60)  # 90min on 1h = 1.5 → round to 2
        if bars_held >= bars_for_stop:
            return "vwap_mom_time_stop"

        return None

Note: the entry_time_utc approach is more precise but requires timezone handling.
For simplicity, use bars_held with the above formula.
If you want exact time-based logic:
    entry_utc = meta.get("entry_time_utc")
    if entry_utc:
        from datetime import datetime, timezone
        try:
            entry_dt  = datetime.fromisoformat(entry_utc)
            elapsed   = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 60
            if elapsed >= time_stop_min:
                return "vwap_mom_time_stop"
        except Exception:
            pass  # fall through to bars_held fallback

7) Add required framework flags to __init__
Add:
    self.stock_enabled     = True      # explicitly declare
    self.reviewer_exempt   = True
    self.time_stop_profile = "strategy_defined"

8) Fix self.logger override
Inspect base_strategy.py for self.logger usage.
Either:
A. Remove: self.logger = logging.getLogger("VWAPMomentum")
   and use inherited self.logger throughout
B. Rename to self._vwap_log

Update all self.logger. calls accordingly.

9) Verify ml_exempt flag
Inspect base_strategy.py.
If ml_exempt is not recognized, remove it.

10) Fix VWAP session anchoring
Current _calc_vwap() computes a cumulative VWAP from the first bar in candles.
If candles contain multiple sessions, the VWAP is anchored to an earlier session.

Two options:

Option A (minimal): Add a comment noting the limitation and that candle_limit=200
limits how far back the VWAP anchor goes. On 1h bars, 200 bars = ~25 trading days
which does make the VWAP less meaningful as an intraday anchor. Accept this
limitation and document it.

Option B (proper): Extract today's session bars using the same _session_bars()
pattern from orb_breakout.py or vwap_confirmed_orb.py, and compute VWAP
from today's session only.

Recommendation: Option B if the session bar extraction can be cleanly added.
Option A if it risks introducing bugs.

If Option B is implemented:
    def _session_bars(self, candles: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Return today's session bars only for proper VWAP anchoring."""
        df = candles.copy()
        idx = pd.DatetimeIndex(df.index)
        try:
            if idx.tz is not None:
                from zoneinfo import ZoneInfo
                idx = idx.tz_convert(ZoneInfo("America/New_York")).tz_localize(None)
                df.index = idx
        except Exception:
            pass
        try:
            df = df.between_time("09:30", "16:00")
        except Exception:
            pass
        if df.empty:
            return None
        session_date = df.index[-1].date()
        df = df[df.index.date == session_date]
        return df if not df.empty else None

Then in analyze():
    session = self._session_bars(candles)
    vwap_val = _calc_vwap(session) if session is not None else _calc_vwap(candles)

11) Fix outdated docstring
The module docstring says "Timeframe: 5-minute bars" but code uses 1h.
Update the docstring:
    # Timeframe: 1h bars (stock market hours)
    # Note: originally designed for 5m but moved to 1h for better signal quality
    # VWAP on 1h is a less precise intraday anchor — session-level filter applies

========================================================
DO NOT CHANGE
========================================================

- Entry conditions (VWAP + EMA triple stack + ADX + RSI zone + volume)
- RSI hard block thresholds (82/18)
- Whitelist membership
- RSI momentum zone concept (40-60 for building momentum)
- market_condition ranging check
- All tuning-driven config parameters
- Crypto disabled (keep crypto_enabled = False)

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/vwap_momentum.py

Run stock basket:
python intelligence/backtester.py --all \
    --strategy vwap_momentum --days 365 --tf 1h \
    --asset-class stock \
    --initial-stop signal_structural --trail-stop none

Check exit reason breakdown:
- vwap_mom_time_stop should appear
- stop_loss and take_profit should appear
- Generic lifecycle stops (early_loss, perf_time_stop, hard_time_stop)
  should NOT dominate

Confirm VWAP value is reasonable:
In logs, check that VWAP values are close to recent price levels.
If VWAP is showing values from weeks ago, session anchoring is broken.

Whitelist check:
Only VWAP_MOM_WHITELIST symbols should produce signals.
Run with an unlisted symbol (e.g. INTV) — should produce zero trades.

Deliverables:
1. Patched strategy file
2. Patched backtester.py
3. Patched strategy_engine.py
4. VWAP session anchoring decision (Option A or B) documented
5. Stock basket validation results
6. Confirmation vwap_mom_time_stop fires in exit breakdown
7. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — VWAP momentum is well-established for intraday stocks
Code quality: good — clean filter stack, good logging, real metadata
Implementation completeness: 70% — check_custom_exit, stop hints, framework flags all missing
Evidence base: limited — no specific PF/WR/DD numbers documented, just that 1h was moved to from 5m
Salvageable: yes
Incubate — the strategy concept is sound but it needs post-patch validation to establish a real performance baseline. The VWAP anchoring concern is the most interesting open question: if VWAP is anchored to a stale day, the whole filter is unreliable.