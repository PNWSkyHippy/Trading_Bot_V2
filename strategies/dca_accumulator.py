"""
dca_accumulator.py — Strategy 8: DCA Accumulator
Trading Bot v2

Dollar-cost averaging strategy for blue-chip stocks and major crypto.
LONG ONLY — buys dips below the EMA50 when RSI confirms oversold conditions.
Uses a wider stop (2%) and larger target (5%) to hold through volatility.

Only trades symbols in the blue-chip/major-crypto whitelist.
Thresholds configurable in config.SIGNAL_TUNING.
"""

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal


# Blue-chip stocks and major crypto appropriate for DCA
DCA_WHITELIST = {
    # Stocks
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "SPY", "QQQ", "JPM", "BAC", "XOM",
    # Crypto — major coins only
    "BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD",
    "BTC-USD", "ETH-USD", "SOL-USD",  # Coinbase format
}


class DCAAccumulator(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name   = "dca_accumulator"
        self.stop_loss_pct   = 2.0     # Wider stop — willing to hold through dips
        self.take_profit_pct = 5.0     # Larger target

        # DCA accumulator is a slow-moving strategy — 1hr bars are the right
        # timeframe. Backtested at 1hr/365 days with all GO results.
        # Needs more bars (200) to see EMA50 and RSI context clearly.
        self.stock_candle_timeframe  = "1Hour"
        self.crypto_candle_timeframe = "1h"
        self.candle_limit            = 200

        self.logger = logging.getLogger("DCAAccumulator")

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        tuning      = config.SIGNAL_TUNING
        ema_period  = tuning["dca_ema_period"]
        dip_pct     = tuning["dca_dip_pct"]
        rsi_max     = tuning["dca_rsi_max"]
        min_score   = tuning["dca_min_score"]

        # Only trade blue-chip/major assets
        in_whitelist = symbol in DCA_WHITELIST
        self.verbose_log(
            symbol, "Symbol in DCA whitelist (blue-chip/major crypto only)",
            in_whitelist, symbol, "must be in whitelist"
        )
        if not in_whitelist:
            return None

        required = ema_period + 5
        if not self._check_enough_candles(symbol, candles, required):
            return None

        close = candles["close"]

        # Calculate EMA50
        try:
            ema = ta.ema(close, length=ema_period)
            if ema is None or ema.isna().all():
                self.verbose_log_skip(symbol, "EMA returned no data")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"EMA error: {e}")
            return None

        ema_value     = ema.iloc[-1]
        current_price = close.iloc[-1]

        if pd.isna(ema_value):
            self.verbose_log_skip(symbol, "EMA value is NaN")
            return None

        # Check price is below EMA50 by at least dip_pct
        if ema_value == 0:
            self.verbose_log_skip(symbol, "EMA value is zero")
            return None

        price_vs_ema  = (current_price - ema_value) / ema_value  # negative = below EMA
        required_dip  = -dip_pct  # e.g. -0.02 means 2% below EMA

        below_ema = price_vs_ema <= required_dip
        self.verbose_log(
            symbol, f"Price is {dip_pct*100:.1f}%+ below EMA{ema_period} (dip condition)",
            below_ema,
            price_vs_ema,
            f"<={required_dip:.4f}",
            "long",
            extra=f"price={current_price:.4f} EMA{ema_period}={ema_value:.4f}"
        )

        if not below_ema:
            return None

        # Calculate RSI to confirm oversold
        try:
            rsi_series = ta.rsi(close, length=14)
            if rsi_series is None:
                self.verbose_log_skip(symbol, "RSI returned None")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"RSI error: {e}")
            return None

        current_rsi = rsi_series.iloc[-1]
        if pd.isna(current_rsi):
            self.verbose_log_skip(symbol, "RSI is NaN")
            return None

        rsi_oversold = current_rsi <= rsi_max
        self.verbose_log(
            symbol, f"RSI confirms oversold (RSI <= {rsi_max})",
            rsi_oversold, current_rsi, f"<={rsi_max}", "long"
        )

        if not rsi_oversold:
            return None

        # Both conditions met — compute score
        dip_depth   = abs(price_vs_ema) / dip_pct  # 1.0 = exactly at threshold
        rsi_depth   = (rsi_max - current_rsi) / rsi_max
        score = min(1.0, min_score + (dip_depth * 0.1) + (rsi_depth * 0.1))

        self.verbose_log_score(symbol, score, min_score)

        if score >= min_score:
            return self._make_signal(
                symbol    = symbol,
                direction = "long",
                score     = score,
                reason    = (
                    f"DCA accumulate: price {abs(price_vs_ema)*100:.1f}% below "
                    f"EMA{ema_period}, RSI={current_rsi:.1f}"
                )
            )

        return None
