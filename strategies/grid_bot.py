"""
grid_bot.py — Strategy 7: Grid Bot
Trading Bot v2

Profits from ranging (sideways) markets by identifying price near
the edges of the recent range (approximated via Bollinger Bands).
Only activates when ADX confirms the market is NOT trending (ADX < threshold).

ADX and BB thresholds configurable in config.SIGNAL_TUNING.

OPEN ISSUE: Grid Bot signals do not populate standard indicators (RSI, MACD,
volume ratio, BB%) in the signal metadata because it uses ADX + Bollinger Band
position rather than those indicators. This causes the Claude reviewer to SKIP
all Grid Bot signals due to missing data. Strategy is marked reviewer_exempt
until we have enough live trade data to evaluate its performance independently.
Once sufficient data exists (50+ trades), consider either:
  a) Populating RSI/volume in metadata so reviewer can evaluate properly, or
  b) Keeping exempt if win rate validates the strategy without review overhead.
"""

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal


class GridBot(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name   = "grid_bot"
        self.stop_loss_pct   = 0.8
        self.take_profit_pct = 1.5

        # REVIEWER EXEMPT: Grid Bot uses ADX + BB position signals, not standard
        # RSI/MACD/volume indicators. Claude reviewer SKIPs all signals due to
        # missing indicator data. Exempt until 50+ live trades confirm performance.
        # See open issue in module docstring above.
        self.reviewer_exempt = True

        self.logger = logging.getLogger("GridBot")

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        tuning      = config.SIGNAL_TUNING
        adx_max     = tuning["grid_adx_max"]
        adx_period  = tuning["grid_adx_period"]
        bb_period   = tuning["grid_bb_period"]
        min_score   = tuning["grid_min_score"]

        required = max(adx_period, bb_period) + 5
        if not self._check_enough_candles(symbol, candles, required):
            return None

        # Calculate ADX — must confirm ranging market
        try:
            adx_data = ta.adx(
                candles["high"], candles["low"], candles["close"],
                length=adx_period
            )
            if adx_data is None or adx_data.empty:
                self.verbose_log_skip(symbol, "ADX returned no data")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"ADX error: {e}")
            return None

        adx_col = [c for c in adx_data.columns if c.startswith("ADX_")]
        if not adx_col:
            self.verbose_log_skip(symbol, "ADX column not found")
            return None

        adx_value = adx_data[adx_col[0]].iloc[-1]
        if pd.isna(adx_value):
            self.verbose_log_skip(symbol, "ADX is NaN")
            return None

        # Grid bot only works in ranging markets (low ADX)
        is_ranging = adx_value < adx_max
        self.verbose_log(
            symbol, "ADX confirms ranging market (grid bot condition)",
            is_ranging, adx_value, f"<{adx_max}"
        )

        if not is_ranging:
            return None

        # Calculate Bollinger Bands to find range edges
        try:
            bb = ta.bbands(candles["close"], length=bb_period, std=2.0)
            if bb is None or bb.empty:
                self.verbose_log_skip(symbol, "Bollinger Bands returned no data")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"BB error: {e}")
            return None

        col_lower = [c for c in bb.columns if c.startswith("BBL_")]
        col_upper = [c for c in bb.columns if c.startswith("BBU_")]
        col_mid   = [c for c in bb.columns if c.startswith("BBM_")]

        if not col_lower or not col_upper or not col_mid:
            self.verbose_log_skip(symbol, "BB column names not found")
            return None

        lower = bb[col_lower[0]].iloc[-1]
        upper = bb[col_upper[0]].iloc[-1]
        mid   = bb[col_mid[0]].iloc[-1]
        close = candles["close"].iloc[-1]

        if any(pd.isna(v) for v in [lower, upper, mid]):
            self.verbose_log_skip(symbol, "BB values contain NaN")
            return None

        # Position within the band (0 = at lower, 1 = at upper)
        band_range = upper - lower
        if band_range == 0:
            self.verbose_log_skip(symbol, "BB band range is zero")
            return None

        position_pct = (close - lower) / band_range

        self.verbose_log(
            symbol, "Price position within BB range (0=lower, 1=upper)",
            True, position_pct, "0.0–1.0",
            extra=f"lower={lower:.4f} upper={upper:.4f} close={close:.4f}"
        )

        # ----------------------------------------------------------------
        # LONG SIGNAL: price near the lower edge of the range
        # ----------------------------------------------------------------
        near_lower = position_pct <= 0.20
        self.verbose_log(
            symbol, "Price near lower band edge (grid long)",
            near_lower, position_pct, "<=0.20 (bottom 20% of range)", "long"
        )

        if near_lower:
            closeness = 1.0 - (position_pct / 0.20)
            score = min(1.0, min_score + closeness * 0.15)
            self.verbose_log_score(symbol, score, min_score)
            if score >= min_score:
                return self._make_signal(
                    symbol    = symbol,
                    direction = "long",
                    score     = score,
                    reason    = (
                        f"Grid long: price at {position_pct:.1%} of range, "
                        f"ADX={adx_value:.1f} (ranging)"
                    )
                )

        # ----------------------------------------------------------------
        # SHORT SIGNAL: price near the upper edge of the range
        # ----------------------------------------------------------------
        near_upper = position_pct >= 0.80
        self.verbose_log(
            symbol, "Price near upper band edge (grid short)",
            near_upper, position_pct, ">=0.80 (top 20% of range)", "short"
        )

        if near_upper:
            closeness = (position_pct - 0.80) / 0.20
            score = min(1.0, min_score + closeness * 0.15)
            self.verbose_log_score(symbol, score, min_score)
            if score >= min_score:
                return self._make_signal(
                    symbol    = symbol,
                    direction = "short",
                    score     = score,
                    reason    = (
                        f"Grid short: price at {position_pct:.1%} of range, "
                        f"ADX={adx_value:.1f} (ranging)"
                    )
                )

        self.verbose_log(
            symbol, "Grid: price in middle of range (no signal)",
            False, position_pct, "need <=0.20 or >=0.80"
        )
        return None
