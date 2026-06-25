"""TraderDev BTC V11 final parity port.

The original Pine uses dynamic cash sizing and a drawdown circuit. This local
port preserves entries and chandelier exits; sizing remains with risk_manager.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, TradeSignal
from strategies.btc_v6_chandelier import _adx, _atr, _ema, _rsi


@dataclass
class TraderDevBTCV11Params:
    atr_mult_long: float = 4.0
    atr_mult_short: float = 2.5
    rsi_long: float = 40.0
    sma_len: int = 48
    sma_lookback: int = 48
    breakout_len: int = 20
    bear_persist: int = 120
    ema_fast: int = 21
    ema_slow: int = 55
    adx_min: float = 20.0
    atr_length: int = 14


def generate_signals(
    df: pd.DataFrame,
    params: TraderDevBTCV11Params = TraderDevBTCV11Params(),
) -> pd.DataFrame:
    p = params
    out = df.copy()
    c = out["close"]

    out["sma"] = c.rolling(p.sma_len).mean()
    out["sma_falling"] = out["sma"] < out["sma"].shift(p.sma_lookback)

    bear_count = []
    bull_count = []
    bears = 0
    bulls = 0
    for falling in out["sma_falling"].fillna(False):
        if falling:
            bears += 1
            bulls = 0
        else:
            bulls += 1
            bears = 0
        bear_count.append(bears)
        bull_count.append(bulls)
    out["bear_count"] = bear_count
    out["bull_count"] = bull_count
    out["bear_regime"] = out["bear_count"] >= p.bear_persist
    out["bull_regime"] = out["bull_count"] >= 1

    out["rsi"] = _rsi(c, 14)
    out["atr"] = _atr(out, p.atr_length)
    out["adx"] = _adx(out, p.atr_length)
    out["ema_fast"] = _ema(c, p.ema_fast)
    out["ema_slow"] = _ema(c, p.ema_slow)
    out["trend_up"] = out["ema_fast"] > out["ema_slow"]
    out["trend_down"] = out["ema_fast"] < out["ema_slow"]
    out["donch_low"] = out["low"].rolling(p.breakout_len).min()

    out["long_signal"] = (
        (out["rsi"] < p.rsi_long)
        & out["trend_up"]
        & (out["adx"] >= p.adx_min)
        & out["bull_regime"]
    )
    out["short_signal"] = (
        np.isclose(out["low"], out["donch_low"])
        & out["trend_down"]
        & (out["adx"] >= p.adx_min)
        & out["bear_regime"]
    )
    return out


class TraderDevBTCV11Strategy(BaseStrategy):
    """BTC V11 final: RSI trend longs plus persistent-bear Donchian shorts."""

    def __init__(self):
        super().__init__()
        self.strategy_name = "td_btc_v11"
        self.params = TraderDevBTCV11Params()
        self.crypto_enabled = True
        self.stock_enabled = False
        self.crypto_candle_timeframe = "1h"
        self.stop_loss_pct = 9.0
        self.take_profit_pct = 30.0
        self.time_stop_profile = "strategy_defined"
        self.reviewer_exempt = True
        self.candle_limit = 300

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:
        if not self._check_enough_candles(symbol, candles, 250):
            return None
        sigs = generate_signals(candles, self.params)
        return self._analyze_from_precomputed(symbol, len(sigs) - 1, sigs, candles)

    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        return generate_signals(df, self.params)

    def _analyze_from_precomputed(
        self,
        symbol: str,
        i: int,
        sigs: pd.DataFrame,
        df: pd.DataFrame,
    ) -> Optional[TradeSignal]:
        row = sigs.iloc[i]
        long_sig = bool(row["long_signal"])
        short_sig = bool(row["short_signal"])
        if not (long_sig or short_sig) or pd.isna(row["atr"]):
            return None

        p = self.params
        direction = "long" if long_sig else "short"
        close = float(row["close"])
        atr = float(row["atr"])
        atr_mult = p.atr_mult_long if long_sig else p.atr_mult_short
        stop_price = close - atr * atr_mult if long_sig else close + atr * atr_mult
        sl_pct = max(round(abs(close - stop_price) / close * 100, 3), 1.5)
        score = round(max(0.66, min(0.90, 0.66 + (float(row["adx"]) - 20.0) / 150.0)), 3)

        return self._make_signal(
            symbol=symbol,
            direction=direction,
            score=score,
            reason=(
                f"TD BTCV11 {direction}: RSI={float(row['rsi']):.1f} "
                f"ADX={float(row['adx']):.1f}"
            ),
            stop_loss_pct=sl_pct,
            take_profit_pct=self.take_profit_pct,
            metadata={
                "strategy_name": self.strategy_name,
                "rsi": round(float(row["rsi"]), 2),
                "adx": round(float(row["adx"]), 2),
                "atr": round(atr, 6),
                "atr_mult": atr_mult,
                "structural_stop_price": round(stop_price, 6),
                "preferred_initial_stop_mode": "signal_structural",
                "preferred_trail_mode": "chandelier",
            },
        )

    def _exit_from_precomputed(
        self,
        i: int,
        sigs: pd.DataFrame,
        direction: str,
        meta: dict,
    ) -> Optional[str]:
        p = self.params
        bars_held = int(meta.get("_bars_held", 0))
        if bars_held < 1:
            return None

        entry_i = max(0, i - bars_held)
        current_atr = float(sigs["atr"].iloc[i])
        current_close = float(sigs["close"].iloc[i])
        if direction == "long":
            track_high = float(sigs["high"].iloc[entry_i : i + 1].max())
            chandelier = track_high - current_atr * p.atr_mult_long
            return "chandelier_stop" if current_close <= chandelier else None
        if direction == "short":
            track_low = float(sigs["low"].iloc[entry_i : i + 1].min())
            chandelier = track_low + current_atr * p.atr_mult_short
            return "chandelier_stop" if current_close >= chandelier else None
        return None
