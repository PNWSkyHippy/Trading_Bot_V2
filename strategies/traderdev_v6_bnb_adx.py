"""TraderDev parity lane for V6 BNB F19 + ADX sizing.

The Pine uses dynamic cash sizing. The local bot keeps position sizing inside
the risk manager, so this wrapper preserves the signal and chandelier exit only.
"""

from strategies.btc_v6_chandelier import BTCV6ChandelierParams, BTCV6ChandelierStrategy


class TraderDevV6BNBADXStrategy(BTCV6ChandelierStrategy):
    """Original TraderDev BNBUSDT 1h V6 parameters."""

    def __init__(self):
        super().__init__()
        self.strategy_name = "td_v6_bnb_adx"
        self.params = BTCV6ChandelierParams(
            rsi_length=14,
            rsi_thresh=40.0,
            ema_fast=21,
            ema_slow=55,
            adx_min=20.0,
            atr_length=14,
            atr_mult=4.0,
            hard_sl_pct=9.0,
        )
        self.stop_loss_pct = self.params.hard_sl_pct
        self.take_profit_pct = 30.0
        self.crypto_enabled = True
        self.stock_enabled = False
        self.crypto_candle_timeframe = "1h"
        self.reviewer_exempt = True
        self.time_stop_profile = "strategy_defined"
        self.candle_limit = 250

    def _stamp_signal(self, signal):
        if signal is not None:
            signal.metadata["strategy_name"] = self.strategy_name
            signal.metadata["entry_timeframe"] = self.crypto_candle_timeframe
        return signal

    def analyze(self, symbol, candles, market_condition="unknown"):
        return self._stamp_signal(super().analyze(symbol, candles, market_condition))

    def _analyze_from_precomputed(self, symbol, i, sigs, df):
        return self._stamp_signal(
            super()._analyze_from_precomputed(symbol, i, sigs, df)
        )
