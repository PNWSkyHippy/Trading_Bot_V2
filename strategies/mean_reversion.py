"""
mean_reversion.py — Strategy 4: Mean Reversion
Trading Bot v2

Fades extreme price deviations — bets that price will return to the mean.
Uses z-score (standard deviations from moving average) to measure extremity.

Long:  Price is far below the mean (z-score very negative) → expect bounce up
Short: Price is far above the mean (z-score very positive) → expect drop down

Z-score threshold configurable in config.SIGNAL_TUNING.

Symbol whitelist: stress test (2yr 1h, Apr 2026) showed mean reversion works
on volatile individual stocks but fails on ETFs and mega-caps. ETFs trend too
smoothly — they don't produce the sharp z-score deviations this strategy needs.

Confirmed KEEP (positive PF):  NVDA(1.37), PLTR(1.23), MRVL(1.18),
                                AMZN(1.15), INTC(1.07), AMD(1.07), META(1.02)
Confirmed REMOVE (negative PF): SPY(0.58), QQQ(0.82), AAPL(0.95),
                                 GOOGL(0.92), AVGO(0.90), NET(0.88), NOW(0.90)
"""

import logging
from typing import Optional

import pandas as pd
import numpy as np
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal


# ── Symbol whitelist ────────────────────────────────────────────────────────
# Only trade symbols where mean reversion has demonstrated positive PF
# on 2yr 1h backtests. ETFs (SPY/QQQ/IWM) and smooth mega-caps (AAPL/GOOGL)
# are excluded — they trend too consistently for reversion to work reliably.
# Update after each monthly stress test review.
MEAN_REVERSION_WHITELIST = {
    "NVDA", "PLTR", "MRVL", "AMZN", "INTC", "AMD",
    "META", "TSLA", "ALAB", "NIO", "MARA", "IREN",
    "CLS", "CRWV", "APLD", "LUNR",
}


class MeanReversion(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name   = "mean_reversion"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT
        self.logger = logging.getLogger("MeanReversion")

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        # ── Symbol whitelist check ───────────────────────────────────────
        # ETFs and smooth mega-caps consistently show negative PF on this
        # strategy. Volatile individual stocks show strong positive PF.
        if symbol.upper() not in MEAN_REVERSION_WHITELIST:
            self.verbose_log_skip(
                symbol,
                f"Not in mean reversion whitelist — skipping "
                f"(allowed: {len(MEAN_REVERSION_WHITELIST)} symbols)"
            )
            return None

        tuning       = config.SIGNAL_TUNING
        zscore_entry = tuning["mean_rev_zscore_entry"]
        period       = tuning["mean_rev_period"]
        min_score    = tuning["mean_rev_min_score"]

        required = period + 5
        if not self._check_enough_candles(symbol, candles, required):
            return None

        # Skip if market is trending — mean reversion works best in ranging
        if market_condition == "trending":
            self.verbose_log_skip(
                symbol, "Market is trending — mean reversion skipped"
            )
            return None

        close  = candles["close"]
        window = close.iloc[-period:]
        mean   = window.mean()
        std    = window.std()

        if std == 0 or pd.isna(std):
            self.verbose_log_skip(symbol, "Standard deviation is zero or NaN")
            return None

        current_price = close.iloc[-1]
        zscore = (current_price - mean) / std

        self.verbose_log(
            symbol, "Z-score deviation from mean",
            abs(zscore) >= zscore_entry,
            zscore, f">={zscore_entry} or <=-{zscore_entry}",
            extra=f"mean={mean:.4f} std={std:.4f}"
        )

        # ----------------------------------------------------------------
        # LONG SIGNAL: price far below mean (negative z-score extreme)
        # ----------------------------------------------------------------
        if zscore <= -zscore_entry:
            strength = min(1.0, abs(zscore) / (zscore_entry * 2))
            score    = min(1.0, min_score + strength * 0.3)
            self.verbose_log(
                symbol, "Z-score in oversold extreme (long signal)",
                True, zscore, f"<=-{zscore_entry}", "long"
            )
            self.verbose_log_score(symbol, score, min_score)

            if score >= min_score:
                return self._make_signal(
                    symbol    = symbol,
                    direction = "long",
                    score     = score,
                    reason    = (
                        f"Mean reversion long: z-score={zscore:.3f} "
                        f"(extreme low, {abs(zscore):.1f}σ from mean)"
                    )
                )

        # ----------------------------------------------------------------
        # SHORT SIGNAL: price far above mean (positive z-score extreme)
        # ----------------------------------------------------------------
        elif zscore >= zscore_entry:
            strength = min(1.0, abs(zscore) / (zscore_entry * 2))
            score    = min(1.0, min_score + strength * 0.3)
            self.verbose_log(
                symbol, "Z-score in overbought extreme (short signal)",
                True, zscore, f">={zscore_entry}", "short"
            )
            self.verbose_log_score(symbol, score, min_score)

            if score >= min_score:
                return self._make_signal(
                    symbol    = symbol,
                    direction = "short",
                    score     = score,
                    reason    = (
                        f"Mean reversion short: z-score={zscore:.3f} "
                        f"(extreme high, {abs(zscore):.1f}σ from mean)"
                    )
                )

        return None
