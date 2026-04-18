"""
=============================================================
  MARKET CONDITION DETECTOR  (Phase 3)
  Identifies whether the market is:
    - TRENDING (strong directional movement)
    - RANGING  (sideways, choppy)
    - VOLATILE (high uncertainty, erratic moves)

  The bot adjusts behavior based on condition:
    - Trending:  full position size, follow momentum
    - Ranging:   reduce size, fade extremes only
    - Volatile:  minimum size or pause entirely
=============================================================
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MarketCondition(Enum):
    TRENDING_UP   = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING       = "ranging"
    VOLATILE      = "volatile"
    UNKNOWN       = "unknown"


@dataclass
class ConditionReport:
    condition:       MarketCondition
    confidence:      float          # 0.0 - 1.0
    position_scalar: float          # Multiply position size by this
    should_trade:    bool
    reason:          str
    adx:             float = 0.0    # Trend strength (>25 = trending)
    atr_pct:         float = 0.0    # Volatility as % of price
    bb_width:        float = 0.0    # Bollinger Band width


class MarketConditionDetector:
    """
    Analyses price data to classify market regime.
    Called before each trade to adjust sizing and strategy.
    """

    ADX_TREND_THRESHOLD    = 25.0
    ADX_STRONG_THRESHOLD   = 40.0
    ATR_VOLATILE_THRESHOLD = 0.03
    ATR_CALM_THRESHOLD     = 0.008
    BB_WIDE_THRESHOLD      = 0.06
    BB_NARROW_THRESHOLD    = 0.02

    def _adx(self, high: pd.Series, low: pd.Series,
             close: pd.Series, period: int = 14) -> pd.Series:
        """Average Directional Index — measures trend strength, not direction."""
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs()
        ], axis=1).max(axis=1)

        dm_plus  = (
            ((high - high.shift()) > (low.shift() - low)).astype(float)
            * (high - high.shift()).clip(lower=0)
        )
        dm_minus = (
            ((low.shift() - low) > (high - high.shift())).astype(float)
            * (low.shift() - low).clip(lower=0)
        )

        atr      = tr.ewm(span=period, adjust=False).mean()
        di_plus  = (
            100 * dm_plus.ewm(span=period, adjust=False).mean()
            / atr.replace(0, np.nan)
        )
        di_minus = (
            100 * dm_minus.ewm(span=period, adjust=False).mean()
            / atr.replace(0, np.nan)
        )
        dx = (
            100 * (di_plus - di_minus).abs()
            / (di_plus + di_minus).replace(0, np.nan)
        )
        return dx.ewm(span=period, adjust=False).mean()

    def _atr_pct(self, high: pd.Series, low: pd.Series,
                 close: pd.Series, period: int = 14) -> float:
        """ATR as percentage of current price."""
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return atr / close.iloc[-1]

    def _bb_width(self, close: pd.Series,
                  period: int = 20, std: float = 2.0) -> float:
        """Bollinger Band width as fraction of mid band."""
        mid   = close.rolling(period).mean()
        sigma = close.rolling(period).std()
        upper = mid + std * sigma
        lower = mid - std * sigma
        width = (upper - lower) / mid
        return float(width.iloc[-1])

    def analyse(self, df: pd.DataFrame) -> ConditionReport:
        """
        Full market condition analysis.
        df must have columns: open, high, low, close, volume
        """
        if df is None or len(df) < 30:
            return ConditionReport(
                condition       = MarketCondition.UNKNOWN,
                confidence      = 0.0,
                position_scalar = 0.5,
                should_trade    = False,
                reason          = "Insufficient data for condition analysis"
            )

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        try:
            adx_series = self._adx(high, low, close)
            adx        = float(adx_series.iloc[-1])
            atr_pct    = self._atr_pct(high, low, close)
            bb_width   = self._bb_width(close)
        except Exception as e:
            logger.debug(f"Indicator calc error in condition detector: {e}")
            return ConditionReport(
                condition       = MarketCondition.UNKNOWN,
                confidence      = 0.5,
                position_scalar = 0.75,
                should_trade    = True,
                reason          = "Could not calculate condition indicators — using defaults"
            )

        # VOLATILE: High ATR and widening Bollinger Bands
        if (atr_pct > self.ATR_VOLATILE_THRESHOLD
                and bb_width > self.BB_WIDE_THRESHOLD):
            return ConditionReport(
                condition       = MarketCondition.VOLATILE,
                confidence      = min(atr_pct / 0.05, 1.0),
                position_scalar = 0.5,
                should_trade    = atr_pct < 0.06,
                reason          = (
                    f"Volatile market: ATR={atr_pct*100:.2f}%, "
                    f"BB width={bb_width*100:.2f}%"
                ),
                adx      = round(adx, 1),
                atr_pct  = round(atr_pct * 100, 2),
                bb_width = round(bb_width * 100, 2)
            )

        # STRONG TREND
        if adx > self.ADX_STRONG_THRESHOLD:
            trend_up  = close.iloc[-1] > close.iloc[-5]
            condition = (
                MarketCondition.TRENDING_UP
                if trend_up else MarketCondition.TRENDING_DOWN
            )
            return ConditionReport(
                condition       = condition,
                confidence      = min(adx / 60, 1.0),
                position_scalar = 1.0,
                should_trade    = True,
                reason          = (
                    f"Strong trend: ADX={adx:.1f} "
                    f"({'up' if trend_up else 'down'})"
                ),
                adx      = round(adx, 1),
                atr_pct  = round(atr_pct * 100, 2),
                bb_width = round(bb_width * 100, 2)
            )

        # MODERATE TREND
        if adx > self.ADX_TREND_THRESHOLD:
            trend_up  = close.iloc[-1] > close.iloc[-5]
            condition = (
                MarketCondition.TRENDING_UP
                if trend_up else MarketCondition.TRENDING_DOWN
            )
            return ConditionReport(
                condition       = condition,
                confidence      = min((adx - 25) / 15, 1.0),
                position_scalar = 0.85,
                should_trade    = True,
                reason          = f"Moderate trend: ADX={adx:.1f}",
                adx      = round(adx, 1),
                atr_pct  = round(atr_pct * 100, 2),
                bb_width = round(bb_width * 100, 2)
            )

        # RANGING
        if adx < self.ADX_TREND_THRESHOLD and bb_width < self.BB_WIDE_THRESHOLD:
            return ConditionReport(
                condition       = MarketCondition.RANGING,
                confidence      = 1.0 - (adx / 25),
                position_scalar = 0.7,
                should_trade    = True,
                reason          = (
                    f"Ranging market: ADX={adx:.1f}, "
                    f"BB width={bb_width*100:.2f}%"
                ),
                adx      = round(adx, 1),
                atr_pct  = round(atr_pct * 100, 2),
                bb_width = round(bb_width * 100, 2)
            )

        # Default — uncertain conditions
        return ConditionReport(
            condition       = MarketCondition.UNKNOWN,
            confidence      = 0.5,
            position_scalar = 0.75,
            should_trade    = True,
            reason          = (
                f"Mixed signals: ADX={adx:.1f}, "
                f"ATR={atr_pct*100:.2f}%"
            ),
            adx      = round(adx, 1),
            atr_pct  = round(atr_pct * 100, 2),
            bb_width = round(bb_width * 100, 2)
        )

    def get_spy_condition(self, stock_scanner) -> ConditionReport:
        """
        Analyse SPY as a proxy for overall market health.
        Used to decide whether to trade at all on a given day.
        """
        try:
            bars = stock_scanner.get_bars("SPY", timeframe="5Min", limit=100)
            if bars is not None:
                return self.analyse(bars)
        except Exception as e:
            logger.debug(f"SPY condition check failed: {e}")

        return ConditionReport(
            condition       = MarketCondition.UNKNOWN,
            confidence      = 0.5,
            position_scalar = 0.75,
            should_trade    = True,
            reason          = "SPY data unavailable — using default conditions"
        )


# Class alias so bot_engine.py can do:
# from intelligence.condition_detector import ConditionDetector
ConditionDetector = MarketConditionDetector

# Singleton
condition_detector = MarketConditionDetector()
