"""
rsi_momentum.py — Strategy 1: RSI Momentum
Trading Bot v2

Enters when RSI crosses back from oversold or overbought territory.
Long:  RSI was below oversold threshold, now crossing back above it.
Short: RSI was above overbought threshold, now crossing back below it.

Thresholds are configurable in config.SIGNAL_TUNING.
"""

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal


class RSIMomentum(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name   = "rsi_momentum"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT     # 1.0%
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT   # 3.0%
        self.logger = logging.getLogger("RSIMomentum")

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:
        """Analyze RSI for crossback signals from extreme levels."""

        tuning      = config.SIGNAL_TUNING
        oversold    = tuning["rsi_momentum_oversold"]
        overbought  = tuning["rsi_momentum_overbought"]
        period      = tuning["rsi_momentum_period"]
        min_score   = tuning["rsi_momentum_min_score"]

        # Need enough candles for RSI calculation
        required = period + 5
        if not self._check_enough_candles(symbol, candles, required):
            return None

        # Calculate RSI
        try:
            rsi_series = ta.rsi(candles["close"], length=period)
            if rsi_series is None or rsi_series.isna().all():
                self.verbose_log_skip(symbol, "RSI calculation returned no data")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"RSI calculation error: {e}")
            return None

        current_rsi  = rsi_series.iloc[-1]
        previous_rsi = rsi_series.iloc[-2]

        if pd.isna(current_rsi) or pd.isna(previous_rsi):
            self.verbose_log_skip(symbol, "RSI values are NaN")
            return None

        # ----------------------------------------------------------------
        # LONG SIGNAL: RSI was below oversold, now crossing back above it
        # ----------------------------------------------------------------
        was_oversold = previous_rsi < oversold
        self.verbose_log(
            symbol, "Previous RSI was oversold (long setup)",
            was_oversold, previous_rsi, f"<{oversold}", "long"
        )

        if was_oversold:
            now_recovering = current_rsi >= oversold
            self.verbose_log(
                symbol, "Current RSI crossed back above oversold (long entry)",
                now_recovering, current_rsi, f">={oversold}", "long"
            )

            if now_recovering:
                # Score based on how deep the oversold was
                depth = max(0.0, (oversold - previous_rsi) / oversold)
                score = min(1.0, min_score + depth * 0.3)
                self.verbose_log_score(symbol, score, min_score)

                if score >= min_score:
                    return self._make_signal(
                        symbol    = symbol,
                        direction = "long",
                        score     = score,
                        reason    = (
                            f"RSI crossback from oversold: "
                            f"prev={previous_rsi:.1f} → curr={current_rsi:.1f} "
                            f"(threshold={oversold})"
                        )
                    )

        # ----------------------------------------------------------------
        # SHORT SIGNAL: RSI was above overbought, now crossing back below it
        # ----------------------------------------------------------------
        was_overbought = previous_rsi > overbought
        self.verbose_log(
            symbol, "Previous RSI was overbought (short setup)",
            was_overbought, previous_rsi, f">{overbought}", "short"
        )

        if was_overbought:
            now_retreating = current_rsi <= overbought
            self.verbose_log(
                symbol, "Current RSI crossed back below overbought (short entry)",
                now_retreating, current_rsi, f"<={overbought}", "short"
            )

            if now_retreating:
                height = max(0.0, (previous_rsi - overbought) / (100 - overbought))
                score  = min(1.0, min_score + height * 0.3)
                self.verbose_log_score(symbol, score, min_score)

                if score >= min_score:
                    return self._make_signal(
                        symbol    = symbol,
                        direction = "short",
                        score     = score,
                        reason    = (
                            f"RSI crossback from overbought: "
                            f"prev={previous_rsi:.1f} → curr={current_rsi:.1f} "
                            f"(threshold={overbought})"
                        )
                    )

        # No signal — log the current RSI so we can see how far off we are
        self.verbose_log(
            symbol, "RSI in neutral zone (no signal)",
            False, current_rsi,
            f"need <{oversold} or >{overbought}"
        )
        return None
