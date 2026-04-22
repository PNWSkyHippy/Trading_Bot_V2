"""
orb_breakout.py — Strategy 11: Opening Range Breakout (ORB)
Trading Bot v2

Classic institutional day trading strategy. The first 15 minutes of
the trading day (9:30-9:44 ET) establish the opening range. A breakout
above or below that range with VWAP confirmation and volume conviction
often leads to strong directional momentum for the rest of the session.

Why it works:
  Large institutions execute big orders at the open creating price
  imbalances. When price breaks the opening range, it triggers stop
  losses, algorithmic signals, and momentum entries simultaneously
  which accelerates the move.

Entry conditions (long):
  1. Time >= 9:45 ET (opening range complete)
  2. Price breaks above opening range high
  3. Price above VWAP (confirms institutional buying)
  4. Breakout bar volume >= 1.5x 20-bar average (conviction)
  5. Opening range not too small (avoids false breakouts on quiet days)
  6. Minimum signal score >= 0.70

Entry conditions (short): mirror of above.

Take profit:
  ATR-based (2x ATR) instead of fixed % so it adapts to the day's
  actual volatility. On a big news day a 5% move is possible. On a
  quiet day 1.5% might be the limit. ATR captures both correctly.

Stop loss:
  Opposite side of the opening range. If long, stop = ORB low.
  This is the natural invalidation point for the breakout thesis.

Whitelist:
  GO stocks only from 5m 30-day backtest (Apr 2026).
  Excluded: NVDA, INTC, NIO, APLD, MARA (TUNE verdict)

Timeframe: 5-minute bars (stock market hours, 9:30-16:00 ET)
Stock only: ORB requires a defined market open which crypto lacks.

Default: DISABLED — backtest first, enable via dashboard.
"""

import logging
from datetime import datetime, timezone, time as dt_time
from typing import Optional

import pandas as pd
import pandas_ta as ta
import numpy as np

import config
from strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)

# Opening range window: 9:30 - 9:44 ET (first 3 x 5m candles)
ORB_START_HOUR   = 9
ORB_START_MIN    = 30
ORB_END_HOUR     = 9
ORB_END_MIN      = 44

# Minimum opening range size as % of price.
# If the range is smaller than this, skip the day — too tight = false breakouts.
MIN_RANGE_PCT    = 0.003   # 0.3% minimum range

# ATR multiplier for take profit
ATR_TP_MULT      = 2.0

# Minimum signal score — all 3 filters must pass AND score >= this
MIN_SCORE        = 0.70

# GO stocks only from 5m 30-day backtest (Apr 2026)
# TUNE stocks excluded: NVDA, INTC, NIO, APLD, MARA
ORB_WHITELIST = {
    "META",  "TSLA",  "MSFT",  "AMD",   "MRVL",
    "ALAB",  "PLTR",  "CRWV",  "IREN",  "CLS",
    "AMZN",  "GOOGL", "AAPL",  "SPY",   "QQQ",
}


def _calc_vwap(candles: pd.DataFrame) -> Optional[float]:
    """Intraday VWAP anchored to available bars."""
    try:
        typical = (candles["high"] + candles["low"] + candles["close"]) / 3
        cum_tpv = (typical * candles["volume"]).cumsum()
        cum_vol = candles["volume"].cumsum()
        vwap    = cum_tpv / cum_vol.replace(0, float("nan"))
        val     = vwap.iloc[-1]
        return float(val) if not pd.isna(val) else None
    except Exception:
        return None


def _calc_atr(candles: pd.DataFrame, period: int = 14) -> Optional[float]:
    """ATR value for dynamic take profit sizing."""
    try:
        atr_series = ta.atr(
            candles["high"], candles["low"], candles["close"], length=period
        )
        if atr_series is None or atr_series.empty:
            return None
        val = atr_series.iloc[-1]
        return float(val) if not pd.isna(val) else None
    except Exception:
        return None


def _get_orb_levels(
    candles: pd.DataFrame
) -> tuple[Optional[float], Optional[float]]:
    """
    Extract opening range high and low from the first 15 minutes.
    Returns (orb_high, orb_low) or (None, None) if insufficient data.
    """
    try:
        if hasattr(candles.index, 'hour'):
            orb_mask = (
                (candles.index.hour == ORB_START_HOUR) &
                (candles.index.minute >= ORB_START_MIN)
            ) | (
                (candles.index.hour == ORB_END_HOUR) &
                (candles.index.minute <= ORB_END_MIN)
            )
            orb_candles = candles[orb_mask]
        else:
            orb_candles = candles.iloc[:3]

        if len(orb_candles) < 2:
            orb_candles = candles.iloc[:3]

        if len(orb_candles) < 2:
            return None, None

        orb_high = float(orb_candles["high"].max())
        orb_low  = float(orb_candles["low"].min())
        return orb_high, orb_low

    except Exception as e:
        logger.debug(f"ORB level calculation error: {e}")
        return None, None


class ORBBreakout(BaseStrategy):
    """
    Opening Range Breakout — Strategy 11.
    5m bars, stock only, VWAP + volume filtered.
    GO stocks only whitelist from 5m backtest.
    """

    def __init__(self):
        super().__init__()
        self.strategy_name   = "orb_breakout"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT
        self.enabled         = False   # Disabled by default — backtest first

        logger.info(
            "[ORBBreakout] Strategy 11 initialized — DISABLED. "
            "Enable via dashboard after reviewing backtest results."
        )

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        # ── Whitelist: GO stocks only ────────────────────────────────────
        if symbol.upper() not in ORB_WHITELIST:
            self.verbose_log_skip(symbol, "Not in ORB GO whitelist")
            return None

        if not self._check_enough_candles(symbol, candles, 20):
            return None

        close  = candles["close"]
        high   = candles["high"]
        low    = candles["low"]
        volume = candles["volume"]
        current_close = float(close.iloc[-1])
        current_high  = float(high.iloc[-1])
        current_low   = float(low.iloc[-1])

        # ── Opening range ────────────────────────────────────────────────
        orb_high, orb_low = _get_orb_levels(candles)
        if orb_high is None or orb_low is None:
            self.verbose_log_skip(symbol, "Could not establish opening range")
            return None

        orb_range = orb_high - orb_low
        orb_range_pct = orb_range / orb_low if orb_low > 0 else 0

        if orb_range_pct < MIN_RANGE_PCT:
            self.verbose_log_skip(
                symbol,
                f"Opening range too small: {orb_range_pct:.3%} < {MIN_RANGE_PCT:.3%}"
            )
            return None

        if len(candles) < 4:
            self.verbose_log_skip(symbol, "Not enough candles past opening range")
            return None

        # ── VWAP filter ──────────────────────────────────────────────────
        vwap_val = _calc_vwap(candles)
        if vwap_val is None:
            self.verbose_log_skip(symbol, "VWAP unavailable")
            return None
        price_above_vwap = current_close > vwap_val

        # ── Volume conviction ────────────────────────────────────────────
        avg_vol     = float(volume.iloc[-20:].mean())
        current_vol = float(volume.iloc[-1])
        vol_ratio   = current_vol / avg_vol if avg_vol > 0 else 0
        volume_ok   = vol_ratio >= 1.5

        if not volume_ok:
            logger.debug(f"[ORB] {symbol}: SKIP — volume {vol_ratio:.2f}x < 1.5x")
            return None

        # ── ATR dynamic take profit ──────────────────────────────────────
        atr_val = _calc_atr(candles)
        if atr_val is None or atr_val <= 0:
            tp_pct = config.DEFAULT_TAKE_PROFIT_PCT
        else:
            tp_pct = (atr_val * ATR_TP_MULT / current_close) * 100
            tp_pct = max(1.0, min(8.0, tp_pct))

        # ── LONG: breaks above ORB high + above VWAP + volume ────────────
        if current_high > orb_high and price_above_vwap:

            sl_pct = ((current_close - orb_low) / current_close) * 100
            sl_pct = max(0.5, min(5.0, sl_pct))

            score = min(1.0, MIN_SCORE + (vol_ratio - 1.5) * 0.05)

            if score < MIN_SCORE:
                return None

            reason = (
                f"ORB long: price {current_close:.4f} > ORB high {orb_high:.4f} "
                f"| VWAP {vwap_val:.4f} ✓ "
                f"| vol {vol_ratio:.2f}x "
                f"| range {orb_range_pct:.2%} "
                f"| ATR TP {tp_pct:.1f}%"
            )

            logger.info(f"[ORB] LONG signal: {symbol} | {reason}")

            return self._make_signal(
                symbol          = symbol,
                direction       = "long",
                score           = round(score, 3),
                reason          = reason,
                stop_loss_pct   = round(sl_pct, 2),
                take_profit_pct = round(tp_pct, 2),
                metadata        = {
                    "orb_high":       round(orb_high, 4),
                    "orb_low":        round(orb_low, 4),
                    "orb_range_pct":  round(orb_range_pct * 100, 3),
                    "vwap":           round(vwap_val, 4),
                    "volume_ratio":   round(vol_ratio, 2),
                    "atr":            round(atr_val, 4) if atr_val else None,
                    "atr_tp_pct":     round(tp_pct, 2),
                    "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                }
            )

        # ── SHORT: breaks below ORB low + below VWAP + volume ───────────
        if current_low < orb_low and not price_above_vwap:

            sl_pct = ((orb_high - current_close) / current_close) * 100
            sl_pct = max(0.5, min(5.0, sl_pct))

            score = min(1.0, MIN_SCORE + (vol_ratio - 1.5) * 0.05)

            if score < MIN_SCORE:
                return None

            reason = (
                f"ORB short: price {current_close:.4f} < ORB low {orb_low:.4f} "
                f"| VWAP {vwap_val:.4f} ✓ "
                f"| vol {vol_ratio:.2f}x "
                f"| range {orb_range_pct:.2%} "
                f"| ATR TP {tp_pct:.1f}%"
            )

            logger.info(f"[ORB] SHORT signal: {symbol} | {reason}")

            return self._make_signal(
                symbol          = symbol,
                direction       = "short",
                score           = round(score, 3),
                reason          = reason,
                stop_loss_pct   = round(sl_pct, 2),
                take_profit_pct = round(tp_pct, 2),
                metadata        = {
                    "orb_high":       round(orb_high, 4),
                    "orb_low":        round(orb_low, 4),
                    "orb_range_pct":  round(orb_range_pct * 100, 3),
                    "vwap":           round(vwap_val, 4),
                    "volume_ratio":   round(vol_ratio, 2),
                    "atr":            round(atr_val, 4) if atr_val else None,
                    "atr_tp_pct":     round(tp_pct, 2),
                    "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                }
            )

        logger.debug(
            f"[ORB] {symbol}: no signal — "
            f"price={current_close:.4f} ORB={orb_low:.4f}-{orb_high:.4f} "
            f"above_vwap={price_above_vwap}"
        )
        return None
