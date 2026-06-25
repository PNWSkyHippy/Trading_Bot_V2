"""TraderDev parity lane for RSI Dip & Spike v4c.

This keeps the public SOLUSDT 1h Pine defaults separate from the locally tuned
``rsi_dip_spike_v4`` strategy so matrix tests can compare the original lane.
"""

from strategies.rsi_dip_spike_v4 import RSIDipSpikeV4Params, RSIDipSpikeV4Strategy


class TraderDevRSIDipSpikeV4CStrategy(RSIDipSpikeV4Strategy):
    """Original TraderDev SOL 1h RSI Dip & Spike v4c parameters."""

    def __init__(self):
        super().__init__()
        self.strategy_name = "td_rsi_dip_spike_v4c"
        self.params = RSIDipSpikeV4Params(
            rsi_length=7,
            rsi_oversold=35.0,
            rsi_overbought=80.0,
            rsi_exit_long=55.0,
            rsi_exit_short=45.0,
            trend_ma_length=200,
            adx_length=14,
            adx_min=25.0,
            adx_max=100.0,
            atr_length=14,
            sl_atr_mult=2.5,
            tp_atr_mult=2.0,
            max_bars_hold=48,
            signal_mode="penetration",
        )
        self.stop_loss_pct = 2.5
        self.take_profit_pct = 2.0
        self.crypto_enabled = True
        self.stock_enabled = False
        self.crypto_candle_timeframe = "1h"
        self.reviewer_exempt = True
        self.ml_exempt = True
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
