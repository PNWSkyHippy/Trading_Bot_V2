"""
TraderDev GridBot Iter1 ADX15 lane.

Parity-oriented port of the public TraderDev Pine:
ADX < 15, Bollinger 30/2, long <= 20% band position, short >= 80% band
position, 0.8% stop, 1.5% target. Vectorized precompute keeps matrix runs fast.
"""

from typing import Optional

import numpy as np
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object
    TradeSignal = None


def _rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def _adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = _rma(tr, length).replace(0, np.nan)

    plus_di = 100.0 * _rma(pd.Series(plus_dm, index=df.index), length) / atr
    minus_di = 100.0 * _rma(pd.Series(minus_dm, index=df.index), length) / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100.0
    return _rma(dx, length)


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    mid = close.rolling(30).mean()
    std = close.rolling(30).std(ddof=0)
    upper = mid + 2.0 * std
    lower = mid - 2.0 * std
    band_range = (upper - lower).replace(0, np.nan)

    out["adx"] = _adx(out, 14)
    out["bb_mid"] = mid
    out["bb_upper"] = upper
    out["bb_lower"] = lower
    out["position_pct"] = ((close - lower) / band_range).fillna(0.5)
    out["is_ranging"] = out["adx"] < 15.0
    out["long_signal"] = out["is_ranging"] & (out["position_pct"] <= 0.20)
    out["short_signal"] = out["is_ranging"] & (out["position_pct"] >= 0.80)
    return out


class TraderDevGridBotADX15(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.strategy_name = "td_gridbot_adx15"
        self.stop_loss_pct = 0.8
        self.take_profit_pct = 1.5
        self.crypto_candle_timeframe = "1h"
        self.stock_enabled = False
        self.crypto_enabled = True
        self.reviewer_exempt = True
        self.ml_exempt = True
        self.candle_limit = 220

    def _make_grid_signal(self, symbol: str, row: pd.Series) -> Optional[TradeSignal]:
        long_sig = bool(row["long_signal"])
        short_sig = bool(row["short_signal"])
        if not (long_sig or short_sig):
            return None

        direction = "long" if long_sig else "short"
        pos_pct = float(row["position_pct"])
        adx = float(row["adx"]) if not pd.isna(row["adx"]) else 99.0
        if direction == "long":
            closeness = 1.0 - min(max(pos_pct / 0.20, 0.0), 1.0)
        else:
            closeness = min(max((pos_pct - 0.80) / 0.20, 0.0), 1.0)
        score = round(min(0.86, 0.66 + closeness * 0.12 + max(15.0 - adx, 0.0) * 0.004), 3)

        return self._make_signal(
            symbol=symbol,
            direction=direction,
            score=score,
            reason=f"TraderDev GridBot ADX15 {direction}: ADX={adx:.1f}, BB pos={pos_pct:.1%}",
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
            metadata={
                "strategy_name": self.strategy_name,
                "source": "TraderDev GridBot Iter1 ADX15",
                "adx": round(adx, 3),
                "bb_position_pct": round(pos_pct, 4),
                "preferred_initial_stop_mode": "fixed_pct",
                "preferred_trail_mode": "none",
            },
        )

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:
        if not self._check_enough_candles(symbol, candles, 45):
            return None
        try:
            sigs = generate_signals(candles)
            return self._make_grid_signal(symbol, sigs.iloc[-1])
        except Exception as exc:
            self.logger.error("td_gridbot_adx15 error on %s: %s", symbol, exc, exc_info=True)
            return None

    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        return generate_signals(df)

    def _analyze_from_precomputed(
        self,
        symbol: str,
        i: int,
        sigs: pd.DataFrame,
        df: pd.DataFrame,
    ) -> Optional[TradeSignal]:
        return self._make_grid_signal(symbol, sigs.iloc[i])
