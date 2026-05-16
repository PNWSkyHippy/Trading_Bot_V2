"""
adaptive_regime.py — Strategy 12: Adaptive All-Weather Regime Strategy
Trading Bot v2

Dual-mode strategy that classifies the current market regime via ADX and
applies the appropriate entry model. A single scan cycle produces at most
one signal per symbol — the regime gate decides which entry fires.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TREND MODE  (strong trend: ADX >= 22, EMA20 above/below EMA100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Long entry:  ADX >= 22  AND  EMA20 > EMA100  AND
               close > prior-bar 12-bar Donchian high  AND  RSI <= 72
  Short entry: ADX >= 22  AND  EMA20 < EMA100  AND
               close < prior-bar 12-bar Donchian low   AND  RSI >= 28

  Stop:   entry_price ± ATR × 2.5  (wider — trend trades need room)
  Target: ATR × 3.0 from entry as backstop TP; primary exit is EMA cross
  Exit:   EMA20 crosses EMA100 in adverse direction (trend has ended)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEAN REVERSION MODE  (weak/ranging: ADX <= 19)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Long entry:  ADX <= 19  AND  close >= EMA100 - ATR×0.5  AND
               close <= lower BB  AND  RSI <= 35
  Short entry: ADX <= 19  AND  close <= EMA100 + ATR×0.5  AND
               close >= upper BB  AND  RSI >= 65

  Stop:   entry_price ± ATR × 1.5  (tighter — reversion should be fast)
  Target: BB midline (primary); RSI 55 for longs / RSI 45 for shorts (secondary)
  Exit:   price reaches BB midline  OR  RSI crosses the exit threshold

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSITIONAL ZONE  (19 < ADX < 22)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  No signal — regime is ambiguous. Skip the symbol this cycle.

Stop model:
  Initial stop is ATR-based (documented exception to two-bar structural
  default — this strategy was designed and validated with ATR stops).
  Trailing uses the standard two-bar structural engine via position_monitor.
  The absolute stop price is embedded in indicators["structural_stop_price"]
  so trade_executor picks it up without a percent conversion.

Exit model:
  Strategy-specific exits are implemented in:
    position_monitor._check_adaptive_regime_exit()
  The exit mode ("trend" or "mean_rev") is stored in signal metadata and
  persisted in indicators_json so position_monitor knows which condition
  to check for each individual trade.

Timeframe: 1h for both stocks and crypto. The EMA100 and 20-bar Donchian
  channel require sufficient history to be meaningful. 5m produces too
  much noise for these slow indicators.

Assets: stocks and crypto both supported.
Whitelist: none — runs on the full watchlist. The five-condition entry
  gates (ADX regime, EMA alignment, Donchian breakout, RSI filter,
  volume check) provide selectivity without a separate whitelist.
"""

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)

# ── Parameters ───────────────────────────────────────────────────────────────
FAST_EMA          = 20
SLOW_EMA          = 100
ADX_PERIOD        = 14
RSI_PERIOD        = 14
ATR_PERIOD        = 14
BB_PERIOD         = 20
BB_DEVFACTOR      = 2.0
VOLUME_PERIOD     = 20
BREAKOUT_PERIOD   = 12     # Donchian channel lookback (bars) — loosened from 20

ADX_TREND_THRESHOLD = 22   # ADX >= this → strong trend → trend mode (loosened from 25)
ADX_RANGE_THRESHOLD = 19   # ADX <= this → weak trend  → mean rev mode (loosened from 18)
                            # 19 < ADX < 22 → transitional → no signal

STOP_ATR_MULT       = 2.5  # Trend mode initial stop distance
TRAIL_ATR_MULT      = 3.0  # Trend mode backstop TP (primary exit is EMA cross)
MEAN_STOP_ATR_MULT  = 1.5  # Mean rev mode initial stop distance

MAX_TREND_ENTRY_RSI       = 72   # Block exhausted long entries (loosened from 68)
MIN_TREND_ENTRY_RSI_SHORT = 28   # Block capitulating short entries (loosened from 32)
OVERSOLD_RSI              = 35   # Mean rev long entry (loosened from 30)
OVERBOUGHT_RSI            = 65   # Mean rev short entry (loosened from 70)
MEAN_EXIT_RSI_LONG        = 55   # RSI exit threshold for mean rev longs
MEAN_EXIT_RSI_SHORT       = 45   # RSI exit threshold for mean rev shorts
MEAN_EMA_ATR_BUFFER       = 0.5  # ATR multiplier for EMA100 bias buffer in mean-rev mode

MIN_BARS = max(SLOW_EMA, ADX_PERIOD, RSI_PERIOD, ATR_PERIOD,
               BB_PERIOD, VOLUME_PERIOD, BREAKOUT_PERIOD + 1) + 10


class AdaptiveRegime(BaseStrategy):
    """
    Adaptive All-Weather Regime Strategy.
    Trend mode (Donchian breakout) and Mean Reversion mode (BB touch)
    selected automatically by ADX regime classification.
    Stocks and crypto, 1h bars.
    """

    def __init__(self):
        super().__init__()
        self.strategy_name   = "adaptive_regime"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT   # fallback only
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT  # fallback only

        # 1h bars for both asset classes — EMA100 and Donchian need history
        self.stock_candle_timeframe  = "1Hour"
        self.crypto_candle_timeframe = "1h"
        self.candle_limit            = 150   # EMA100 needs ~100 + buffer

        self.stock_enabled  = False
        self.crypto_enabled = False
        self.enabled        = False  # DISABLED — pending backtest validation
                                     # 23.1% WR on 13 trades, -$46. Re-enable after
                                     # backtest-expert confirms edge. Use quant
                                     # backtest-fix-retest loop before live exposure.

        self.time_stop_profile           = "strategy_defined"
        self.preferred_initial_stop_mode = "signal_structural"
        self.preferred_trail_mode        = "two_bar"

        self._reset_diagnostics()

        logger.info(
            f"[{self.strategy_name}] Initialized — dual-mode adaptive regime. "
            f"Trend threshold ADX>={ADX_TREND_THRESHOLD}, "
            f"Range threshold ADX<={ADX_RANGE_THRESHOLD}, "
            f"Donchian={BREAKOUT_PERIOD}. 1h bars."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DIAGNOSTICS  (lightweight counters — no effect on strategy behaviour)
    # ─────────────────────────────────────────────────────────────────────────

    def _reset_diagnostics(self):
        """Zero all per-run counters.  Called by backtester before each symbol."""
        self.diagnostics = {
            # Regime bar distribution
            "bars_analyzed":     0,
            "trend_bars":        0,   # ADX >= 25
            "range_bars":        0,   # ADX <= 18
            "transition_bars":   0,   # 18 < ADX < 25 — no signal zone
            # Trend-mode signal counts
            "trend_long":        0,
            "trend_short":       0,
            # Trend-mode blocker counts (first blocker only — mutually exclusive order)
            "trend_vol_fail":    0,   # volume_ratio < 1.0
            "trend_ema_fail":    0,   # EMA alignment unclear (flat market)
            "trend_don_fail":    0,   # price did not break Donchian channel
            "trend_rsi_fail":    0,   # RSI exhausted / not confirmed
            # Mean-rev signal counts
            "mean_long":         0,
            "mean_short":        0,
            # Mean-rev blocker counts
            "mean_vol_fail":     0,   # volume_ratio < 0.5
            "mean_bb_fail":      0,   # price did not touch BB band
            "mean_rsi_fail":     0,   # RSI not extreme enough
        }

    def get_diagnostics(self) -> dict:
        """Return a copy of the current diagnostic counters."""
        return dict(self.diagnostics)

    # ─────────────────────────────────────────────────────────────────────────
    # INDICATOR HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _calc_adx(self, high: pd.Series, low: pd.Series,
                  close: pd.Series) -> Optional[float]:
        try:
            adx_df = ta.adx(high, low, close, length=ADX_PERIOD)
            if adx_df is None or adx_df.empty:
                return None
            col = [c for c in adx_df.columns if c.startswith("ADX_")]
            if not col:
                return None
            val = adx_df[col[0]].iloc[-1]
            return float(val) if not pd.isna(val) else None
        except Exception:
            return None

    def _calc_atr(self, high: pd.Series, low: pd.Series,
                  close: pd.Series) -> Optional[float]:
        try:
            atr_s = ta.atr(high, low, close, length=ATR_PERIOD)
            if atr_s is None or atr_s.empty:
                return None
            val = atr_s.iloc[-1]
            return float(val) if not pd.isna(val) else None
        except Exception:
            return None

    def _calc_rsi(self, close: pd.Series) -> Optional[float]:
        try:
            rsi_s = ta.rsi(close, length=RSI_PERIOD)
            if rsi_s is None or rsi_s.empty:
                return None
            val = rsi_s.iloc[-1]
            return float(val) if not pd.isna(val) else None
        except Exception:
            return None

    def _calc_bb(self, close: pd.Series):
        """Returns (bb_lower, bb_mid, bb_upper) or (None, None, None)."""
        try:
            bb = ta.bbands(close, length=BB_PERIOD, std=BB_DEVFACTOR)
            if bb is None or bb.empty:
                return None, None, None
            low_col = [c for c in bb.columns if "BBL" in c]
            mid_col = [c for c in bb.columns if "BBM" in c]
            upp_col = [c for c in bb.columns if "BBU" in c]
            if not (low_col and mid_col and upp_col):
                return None, None, None
            return (
                float(bb[low_col[0]].iloc[-1]),
                float(bb[mid_col[0]].iloc[-1]),
                float(bb[upp_col[0]].iloc[-1]),
            )
        except Exception:
            return None, None, None

    def _calc_macd_hist(self, close: pd.Series) -> Optional[float]:
        """Return MACD histogram value (fast=12, slow=26, signal=9)."""
        try:
            macd_df  = ta.macd(close, fast=12, slow=26, signal=9)
            if macd_df is None or macd_df.empty:
                return None
            hist_col = [c for c in macd_df.columns if "MACDh" in c]
            if not hist_col:
                return None
            val = macd_df[hist_col[0]].iloc[-1]
            return round(float(val), 6) if not pd.isna(val) else None
        except Exception:
            return None

    def _calc_bb_pct(self, close: float, bb_lower: float, bb_upper: float) -> float:
        """
        Bollinger percent-b: position of close within the band (0 = lower, 1 = upper).
        Clamped to [-0.5, 1.5] so extreme overshoots don't break downstream code.
        """
        span = bb_upper - bb_lower
        if span <= 0:
            return 0.5
        return round(max(-0.5, min(1.5, (close - bb_lower) / span)), 4)

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        if not self._check_enough_candles(symbol, candles, MIN_BARS):
            return None

        close  = candles["close"].astype(float)
        high   = candles["high"].astype(float)
        low    = candles["low"].astype(float)
        volume = candles["volume"].astype(float)
        current_close = float(close.iloc[-1])

        # ── Regime classification via ADX ────────────────────────────────────
        adx = self._calc_adx(high, low, close)
        if adx is None:
            self.verbose_log_skip(symbol, "ADX unavailable")
            return None

        strong_trend = adx >= ADX_TREND_THRESHOLD
        weak_trend   = adx <= ADX_RANGE_THRESHOLD

        # ── Regime bar counter (diagnostics only) ───────────────────────────
        _d = self.diagnostics
        _d["bars_analyzed"] += 1
        if strong_trend:
            _d["trend_bars"] += 1
        elif weak_trend:
            _d["range_bars"] += 1
        else:
            _d["transition_bars"] += 1

        if not strong_trend and not weak_trend:
            self.verbose_log_skip(
                symbol,
                f"Transitional ADX={adx:.1f} — between {ADX_RANGE_THRESHOLD} "
                f"and {ADX_TREND_THRESHOLD}, skipping"
            )
            return None

        # ── EMA fast / slow alignment ────────────────────────────────────────
        try:
            ema_fast_s = ta.ema(close, length=FAST_EMA)
            ema_slow_s = ta.ema(close, length=SLOW_EMA)
            if ema_fast_s is None or ema_slow_s is None:
                self.verbose_log_skip(symbol, "EMA calculation failed")
                return None
            ema_fast = float(ema_fast_s.iloc[-1])
            ema_slow = float(ema_slow_s.iloc[-1])
        except Exception as ex:
            self.verbose_log_skip(symbol, f"EMA error: {ex}")
            return None

        trend_up   = ema_fast > ema_slow
        trend_down = ema_fast < ema_slow

        # ── Shared metrics — computed once, used in both modes and metadata ────
        vol_sma      = float(volume.iloc[-VOLUME_PERIOD:].mean())
        current_vol  = float(volume.iloc[-1])
        volume_ratio = round(current_vol / vol_sma, 3) if vol_sma > 0 else 1.0

        # Compute MACD histogram once — included in metadata for Claude reviewer.
        macd_hist = self._calc_macd_hist(close)

        # NOTE: volume threshold is mode-specific (applied inside each block):
        #   Trend mode    : >= 1.1× avg — confirming volume expands on breakout
        #   Mean-rev mode : >= 0.5× avg — just exclude completely dead markets
        #                   (high volume is NOT required for mean reversion)

        # ── ATR for dynamic stop sizing ──────────────────────────────────────
        atr = self._calc_atr(high, low, close)
        if atr is None or atr <= 0:
            self.verbose_log_skip(symbol, "ATR unavailable")
            return None

        # ── RSI ──────────────────────────────────────────────────────────────
        rsi = self._calc_rsi(close)
        if rsi is None:
            self.verbose_log_skip(symbol, "RSI unavailable")
            return None

        # ─────────────────────────────────────────────────────────────────────
        # TREND MODE
        # ─────────────────────────────────────────────────────────────────────
        if strong_trend:
            # Donchian channel: prior bar's N-bar high/low
            # [-2] = one closed bar before the current bar — correct breakout level
            don_high = float(high.rolling(BREAKOUT_PERIOD).max().iloc[-2])
            don_low  = float(low.rolling(BREAKOUT_PERIOD).min().iloc[-2])

            # Volume gate: trend entries require at least average volume on the breakout.
            # A ratio < 1.0 means volume is below the recent average —
            # not enough participation to confirm a genuine breakout.
            if volume_ratio < 1.0:
                _d["trend_vol_fail"] += 1
                self.verbose_log_skip(
                    symbol,
                    f"Trend mode: volume_ratio={volume_ratio:.3f} < 1.0 — "
                    f"no breakout volume confirmation"
                )
                return None

            # ── Trend-mode blocker diagnostics (counted before signal checks) ─
            # Parallel checks — do not alter control flow.
            if not trend_up and not trend_down:
                _d["trend_ema_fail"] += 1
            else:
                if trend_up:
                    if current_close <= don_high:
                        _d["trend_don_fail"] += 1
                    elif rsi > MAX_TREND_ENTRY_RSI:
                        _d["trend_rsi_fail"] += 1
                if trend_down:
                    if current_close >= don_low:
                        _d["trend_don_fail"] += 1
                    elif rsi < MIN_TREND_ENTRY_RSI_SHORT:
                        _d["trend_rsi_fail"] += 1

            # BB %b — trend entry logic doesn't use it, but the reviewer and ML
            # scorer both expect it in metadata to gauge where price sits in the band.
            _bb_lo, _bb_mi, _bb_hi = self._calc_bb(close)
            bb_pct = (
                self._calc_bb_pct(current_close, _bb_lo, _bb_hi)
                if _bb_lo is not None else None
            )

            # ── TREND LONG ───────────────────────────────────────────────────
            if trend_up and current_close > don_high and rsi <= MAX_TREND_ENTRY_RSI:
                _d["trend_long"] += 1
                stop_price = current_close - (atr * STOP_ATR_MULT)
                if stop_price >= current_close:
                    self.verbose_log_skip(symbol, "Trend long: ATR stop above entry")
                    return None

                sl_pct = (current_close - stop_price) / current_close * 100
                tp_pct = (atr * TRAIL_ATR_MULT) / current_close * 100
                tp_pct = max(1.0, min(15.0, tp_pct))   # backstop TP; real exit is EMA cross

                score = min(1.0, 0.72 + (adx - ADX_TREND_THRESHOLD) * 0.002)
                self.verbose_log_score(symbol, score, 0.65)

                logger.info(
                    f"[AdaptiveRegime] {symbol}: TREND LONG | "
                    f"close={current_close:.4f} > don_high={don_high:.4f} | "
                    f"ADX={adx:.1f} EMA_fast={ema_fast:.4f}>EMA_slow={ema_slow:.4f} | "
                    f"RSI={rsi:.1f} ATR={atr:.4f} SL=${stop_price:.4f}"
                )
                return self._make_signal(
                    symbol          = symbol,
                    direction       = "long",
                    score           = round(score, 3),
                    reason          = (
                        f"Adaptive trend long: close {current_close:.4f} > "
                        f"Donchian {don_high:.4f} | ADX={adx:.1f} | "
                        f"EMA{FAST_EMA}>EMA{SLOW_EMA} | RSI={rsi:.1f}"
                    ),
                    stop_loss_pct   = round(sl_pct, 3),
                    take_profit_pct = round(tp_pct, 3),
                    metadata        = {
                        "adaptive_exit_mode":    "trend",
                        "structural_stop_price": round(stop_price, 6),
                        "adx":                   round(adx, 2),
                        "ema_fast":              round(ema_fast, 4),
                        "ema_slow":              round(ema_slow, 4),
                        "donchian_high":         round(don_high, 4),
                        "atr":                   round(atr, 6),
                        "rsi":                   round(rsi, 2),
                        "regime":                "trend",
                        "entry_timeframe":       "1h",
                        "volume_ratio":          volume_ratio,
                        "bb_pct":                bb_pct,
                        "macd_hist":             macd_hist,
                    }
                )

            # ── TREND SHORT ──────────────────────────────────────────────────
            if trend_down and current_close < don_low and rsi >= MIN_TREND_ENTRY_RSI_SHORT:
                _d["trend_short"] += 1
                stop_price = current_close + (atr * STOP_ATR_MULT)
                if stop_price <= current_close:
                    self.verbose_log_skip(symbol, "Trend short: ATR stop below entry")
                    return None

                sl_pct = (stop_price - current_close) / current_close * 100
                tp_pct = (atr * TRAIL_ATR_MULT) / current_close * 100
                tp_pct = max(1.0, min(15.0, tp_pct))

                score = min(1.0, 0.72 + (adx - ADX_TREND_THRESHOLD) * 0.002)
                self.verbose_log_score(symbol, score, 0.65)

                logger.info(
                    f"[AdaptiveRegime] {symbol}: TREND SHORT | "
                    f"close={current_close:.4f} < don_low={don_low:.4f} | "
                    f"ADX={adx:.1f} EMA_fast={ema_fast:.4f}<EMA_slow={ema_slow:.4f} | "
                    f"RSI={rsi:.1f} ATR={atr:.4f} SL=${stop_price:.4f}"
                )
                return self._make_signal(
                    symbol          = symbol,
                    direction       = "short",
                    score           = round(score, 3),
                    reason          = (
                        f"Adaptive trend short: close {current_close:.4f} < "
                        f"Donchian {don_low:.4f} | ADX={adx:.1f} | "
                        f"EMA{FAST_EMA}<EMA{SLOW_EMA} | RSI={rsi:.1f}"
                    ),
                    stop_loss_pct   = round(sl_pct, 3),
                    take_profit_pct = round(tp_pct, 3),
                    metadata        = {
                        "adaptive_exit_mode":    "trend",
                        "structural_stop_price": round(stop_price, 6),
                        "adx":                   round(adx, 2),
                        "ema_fast":              round(ema_fast, 4),
                        "ema_slow":              round(ema_slow, 4),
                        "donchian_low":          round(don_low, 4),
                        "atr":                   round(atr, 6),
                        "rsi":                   round(rsi, 2),
                        "regime":                "trend",
                        "entry_timeframe":       "1h",
                        "volume_ratio":          volume_ratio,
                        "bb_pct":                bb_pct,
                        "macd_hist":             macd_hist,
                    }
                )

        # ─────────────────────────────────────────────────────────────────────
        # MEAN REVERSION MODE
        # ─────────────────────────────────────────────────────────────────────
        if weak_trend:
            bb_lower, bb_mid, bb_upper = self._calc_bb(close)
            if bb_lower is None:
                self.verbose_log_skip(symbol, "Bollinger Bands unavailable")
                return None

            # Volume gate: exclude completely dead/illiquid markets.
            # Mean reversion does NOT require above-average volume — the signal
            # is a price extreme, not a breakout — but a ratio below 0.5 suggests
            # the symbol is dormant and the BB touch may be meaningless.
            if volume_ratio < 0.5:
                _d["mean_vol_fail"] += 1
                self.verbose_log_skip(
                    symbol,
                    f"Mean-rev mode: volume_ratio={volume_ratio:.3f} < 0.5 — "
                    f"market too illiquid for mean reversion"
                )
                return None

            # BB %b — position of close within the band (0 = lower, 1 = upper).
            bb_pct = self._calc_bb_pct(current_close, bb_lower, bb_upper)

            # ── Mean-rev blocker diagnostics (counted before signal checks) ──
            # Iteration 1 change: EMA100 proximity gate removed — it created a
            # geometric impossibility (BB_lower AND near-EMA100 simultaneously
            # in a ranging market). BB band touch + RSI extreme is sufficient.
            if current_close > bb_lower:          # potential long: BB not touched
                _d["mean_bb_fail"] += 1
            elif rsi > OVERSOLD_RSI:              # BB touched, RSI not extreme
                _d["mean_rsi_fail"] += 1
            if current_close < bb_upper:          # potential short: BB not touched
                _d["mean_bb_fail"] += 1
            elif rsi < OVERBOUGHT_RSI:            # BB touched, RSI not extreme
                _d["mean_rsi_fail"] += 1

            # ── MEAN REV LONG ────────────────────────────────────────────────
            # EMA100 proximity gate removed (iter 1) — BB touch + RSI is sufficient.
            if (current_close <= bb_lower and
                    rsi <= OVERSOLD_RSI):
                _d["mean_long"] += 1
                stop_price = current_close - (atr * MEAN_STOP_ATR_MULT)
                if stop_price >= current_close:
                    self.verbose_log_skip(symbol, "Mean rev long: ATR stop above entry")
                    return None

                sl_pct = (current_close - stop_price) / current_close * 100
                # TP at BB midline — this is where position_monitor will exit
                # Store as pct from current price; position_monitor checks BB_mid directly
                tp_pct = max(0.5, (bb_mid - current_close) / current_close * 100)
                tp_pct = min(tp_pct, 8.0)

                score = min(1.0, 0.70 + (OVERSOLD_RSI - rsi) * 0.005)
                self.verbose_log_score(symbol, score, 0.65)

                logger.info(
                    f"[AdaptiveRegime] {symbol}: MEAN REV LONG | "
                    f"close={current_close:.4f} <= BB_low={bb_lower:.4f} | "
                    f"ADX={adx:.1f} RSI={rsi:.1f} BB_mid={bb_mid:.4f}"
                )
                return self._make_signal(
                    symbol          = symbol,
                    direction       = "long",
                    score           = round(score, 3),
                    reason          = (
                        f"Adaptive mean-rev long: close {current_close:.4f} "
                        f"<= BB_low {bb_lower:.4f} | ADX={adx:.1f} | RSI={rsi:.1f} "
                        f"| BB_mid={bb_mid:.4f}"
                    ),
                    stop_loss_pct   = round(sl_pct, 3),
                    take_profit_pct = round(tp_pct, 3),
                    metadata        = {
                        "adaptive_exit_mode":    "mean_rev",
                        "structural_stop_price": round(stop_price, 6),
                        "adx":                   round(adx, 2),
                        "ema_slow":              round(ema_slow, 4),
                        "bb_lower":              round(bb_lower, 4),
                        "bb_mid":                round(bb_mid, 4),
                        "atr":                   round(atr, 6),
                        "rsi":                   round(rsi, 2),
                        "regime":                "mean_rev",
                        "entry_timeframe":       "1h",
                        "volume_ratio":          volume_ratio,
                        "bb_pct":                bb_pct,
                        "macd_hist":             macd_hist,
                    }
                )

            # ── MEAN REV SHORT ───────────────────────────────────────────────
            # EMA100 proximity gate removed (iter 1).
            if (current_close >= bb_upper and
                    rsi >= OVERBOUGHT_RSI):
                _d["mean_short"] += 1
                stop_price = current_close + (atr * MEAN_STOP_ATR_MULT)
                if stop_price <= current_close:
                    self.verbose_log_skip(symbol, "Mean rev short: ATR stop below entry")
                    return None

                sl_pct = (stop_price - current_close) / current_close * 100
                tp_pct = max(0.5, (current_close - bb_mid) / current_close * 100)
                tp_pct = min(tp_pct, 8.0)

                score = min(1.0, 0.70 + (rsi - OVERBOUGHT_RSI) * 0.005)
                self.verbose_log_score(symbol, score, 0.65)

                logger.info(
                    f"[AdaptiveRegime] {symbol}: MEAN REV SHORT | "
                    f"close={current_close:.4f} >= BB_up={bb_upper:.4f} | "
                    f"ADX={adx:.1f} RSI={rsi:.1f} BB_mid={bb_mid:.4f}"
                )
                return self._make_signal(
                    symbol          = symbol,
                    direction       = "short",
                    score           = round(score, 3),
                    reason          = (
                        f"Adaptive mean-rev short: close {current_close:.4f} "
                        f">= BB_up {bb_upper:.4f} | ADX={adx:.1f} | RSI={rsi:.1f} "
                        f"| BB_mid={bb_mid:.4f}"
                    ),
                    stop_loss_pct   = round(sl_pct, 3),
                    take_profit_pct = round(tp_pct, 3),
                    metadata        = {
                        "adaptive_exit_mode":    "mean_rev",
                        "structural_stop_price": round(stop_price, 6),
                        "adx":                   round(adx, 2),
                        "ema_slow":              round(ema_slow, 4),
                        "bb_upper":              round(bb_upper, 4),
                        "bb_mid":                round(bb_mid, 4),
                        "atr":                   round(atr, 6),
                        "rsi":                   round(rsi, 2),
                        "regime":                "mean_rev",
                        "entry_timeframe":       "1h",
                        "volume_ratio":          volume_ratio,
                        "bb_pct":                bb_pct,
                        "macd_hist":             macd_hist,
                    }
                )

        logger.debug(
            f"[AdaptiveRegime] {symbol}: no signal — "
            f"ADX={adx:.1f} trend_up={trend_up} trend_down={trend_down} "
            f"RSI={rsi:.1f} close={current_close:.4f}"
        )
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # CUSTOM EXIT HOOK  (called by backtester on every bar while in position)
    # ─────────────────────────────────────────────────────────────────────────

    def check_custom_exit(
        self,
        symbol: str,
        bars: pd.DataFrame,
        direction: str,
        entry_metadata: dict = None
    ):
        """
        Replicate live position_monitor._check_adaptive_regime_exit() logic
        inside the backtester so simulated trades use the same exit conditions
        that would fire in production.

        Trend mode:
          Exit when EMA20 crosses EMA100 in the adverse direction.
          Long:  EMA20 <= EMA100  →  "adaptive_ema_cross_exit"
          Short: EMA20 >= EMA100  →  "adaptive_ema_cross_exit"

        Mean-rev mode (first condition that fires wins):
          1. Price reaches BB midline (SMA20)  →  "adaptive_bb_midline_exit"
          2. RSI ≥ 55 for longs / RSI ≤ 45 for shorts  →  "adaptive_rsi_exit"

        Returns exit reason string or None to hold.
        """
        exit_mode = (entry_metadata or {}).get("adaptive_exit_mode")
        if exit_mode not in ("trend", "mean_rev"):
            return None

        if bars is None or len(bars) < 30:
            return None

        try:
            closes       = bars["close"].astype(float)
            current_price = float(closes.iloc[-1])

            # EMA20 and EMA100 — used by both modes
            ema20_s  = closes.ewm(span=FAST_EMA,  adjust=False).mean()
            ema100_s = closes.ewm(span=SLOW_EMA, adjust=False).mean()
            ema20    = float(ema20_s.iloc[-1])
            ema100   = float(ema100_s.iloc[-1])

            # ── TREND EXIT: EMA cross in adverse direction ──────────────────
            if exit_mode == "trend":
                if direction == "long"  and ema20 <= ema100:
                    return "adaptive_ema_cross_exit"
                if direction == "short" and ema20 >= ema100:
                    return "adaptive_ema_cross_exit"
                return None

            # ── MEAN REV EXIT 1: price reaches BB midline (SMA20) ──────────
            bb_mid = float(closes.rolling(BB_PERIOD).mean().iloc[-1])
            if direction == "long"  and current_price >= bb_mid:
                return "adaptive_bb_midline_exit"
            if direction == "short" and current_price <= bb_mid:
                return "adaptive_bb_midline_exit"

            # ── MEAN REV EXIT 2: RSI threshold ─────────────────────────────
            rsi = self._calc_rsi(closes)
            if rsi is not None:
                if direction == "long"  and rsi >= MEAN_EXIT_RSI_LONG:
                    return "adaptive_rsi_exit"
                if direction == "short" and rsi <= MEAN_EXIT_RSI_SHORT:
                    return "adaptive_rsi_exit"

            return None

        except Exception:
            return None
