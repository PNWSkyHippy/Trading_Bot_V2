"""
TraderDev Day Trader v3
=======================

Faithful entry port of the public TraderDev "Day Trader v3" 15m BTC/SOL Pine
strategy. The Pine source uses two partial exits: 60% at 2R and the remainder
at 4R with ATR trailing. The local matrix backtester models one position with
one stop/target, so this Python port uses a weighted 2.8R target for screening.

Do not promote this live from matrix results alone. It needs a parity pass with
partial-exit support or forward paper tracking.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object
    TradeSignal = None


@dataclass
class DayTraderV3Params:
    st_len: int = 10
    st_mult: float = 2.5
    macd_fast: int = 12
    macd_slow: int = 26
    macd_sig: int = 9
    rsi_len: int = 14
    rsi_long: int = 55
    rsi_short: int = 50
    ema_len: int = 50
    vol_len: int = 20
    vol_mult: float = 1.2
    stop_mult: float = 1.0
    tp1_rr: float = 2.0
    tp2_rr: float = 4.0
    tp1_pct: float = 60.0
    trail_mult: float = 1.0
    time_cap: int = 32

    @property
    def weighted_rr(self) -> float:
        first = self.tp1_pct / 100.0
        return first * self.tp1_rr + (1.0 - first) * self.tp2_rr


def _rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _rma(tr, length)


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = _rma(gain, length) / _rma(loss, length).replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def _supertrend(
    df: pd.DataFrame,
    length: int,
    mult: float,
) -> tuple[pd.Series, pd.Series]:
    atr = _atr(df, length)
    hl2 = (df["high"] + df["low"]) / 2.0
    upper_basic = hl2 + mult * atr
    lower_basic = hl2 - mult * atr

    n = len(df)
    upper = upper_basic.copy()
    lower = lower_basic.copy()
    direction = pd.Series(np.nan, index=df.index, dtype=float)
    trend = pd.Series(np.nan, index=df.index, dtype=float)
    close = df["close"]

    for i in range(n):
        if pd.isna(atr.iloc[i]):
            continue
        if i == 0 or pd.isna(direction.iloc[i - 1]):
            direction.iloc[i] = 1.0
            trend.iloc[i] = upper.iloc[i]
            continue

        prev_upper = upper.iloc[i - 1]
        prev_lower = lower.iloc[i - 1]
        prev_close = close.iloc[i - 1]

        if upper_basic.iloc[i] < prev_upper or prev_close > prev_upper:
            upper.iloc[i] = upper_basic.iloc[i]
        else:
            upper.iloc[i] = prev_upper

        if lower_basic.iloc[i] > prev_lower or prev_close < prev_lower:
            lower.iloc[i] = lower_basic.iloc[i]
        else:
            lower.iloc[i] = prev_lower

        prev_dir = direction.iloc[i - 1]
        if prev_dir == -1.0:
            direction.iloc[i] = 1.0 if close.iloc[i] < lower.iloc[i] else -1.0
        else:
            direction.iloc[i] = -1.0 if close.iloc[i] > upper.iloc[i] else 1.0

        trend.iloc[i] = lower.iloc[i] if direction.iloc[i] == -1.0 else upper.iloc[i]

    return trend, direction


def generate_signals(
    df: pd.DataFrame,
    params: DayTraderV3Params = DayTraderV3Params(),
) -> pd.DataFrame:
    p = params
    out = df.copy()
    close = out["close"]

    out["atr"] = _atr(out, p.st_len)
    out["ema50"] = _ema(close, p.ema_len)
    out["rsi"] = _rsi(close, p.rsi_len)
    out["vol_avg"] = out["volume"].rolling(p.vol_len).mean()
    out["st_val"], out["st_dir"] = _supertrend(out, p.st_len, p.st_mult)

    macd_line = _ema(close, p.macd_fast) - _ema(close, p.macd_slow)
    macd_sig = _ema(macd_line, p.macd_sig)
    out["macd_hist"] = macd_line - macd_sig

    out["st_bull"] = out["st_dir"] == -1.0
    out["st_bear"] = out["st_dir"] == 1.0
    prev_bull = out["st_bull"].shift(1, fill_value=False).astype(bool)
    prev_bear = out["st_bear"].shift(1, fill_value=False).astype(bool)
    out["st_flip_up"] = out["st_bull"] & ~prev_bull
    out["st_flip_down"] = out["st_bear"] & ~prev_bear

    hist = out["macd_hist"]
    out["macd_bull"] = (hist > 0) & (hist.shift(1) <= 0)
    out["macd_bear"] = (hist < 0) & (hist.shift(1) >= 0)
    recent_bull = out["macd_bull"] | out["macd_bull"].shift(1) | out["macd_bull"].shift(2)
    recent_bear = out["macd_bear"] | out["macd_bear"].shift(1) | out["macd_bear"].shift(2)
    out["macd_recent_bull"] = (hist > 0) & recent_bull.fillna(False)
    out["macd_recent_bear"] = (hist < 0) & recent_bear.fillna(False)
    out["vol_ok"] = out["volume"] > out["vol_avg"] * p.vol_mult

    out["long_signal"] = (
        out["st_flip_up"]
        & out["macd_recent_bull"]
        & (out["rsi"] > p.rsi_long)
        & (close > out["ema50"])
        & out["vol_ok"]
    )
    out["short_signal"] = (
        out["st_flip_down"]
        & out["macd_recent_bear"]
        & (out["rsi"] < p.rsi_short)
        & (close < out["ema50"])
        & out["vol_ok"]
    )
    return out


class TraderDevDayTraderV3Strategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = DayTraderV3Params()
        self.strategy_name = "td_day_trader_v3"
        self.stock_enabled = False
        self.crypto_enabled = True
        self.crypto_candle_timeframe = "15m"
        self.candle_limit = 140
        self.time_stop_profile = "strategy_defined"
        self.reviewer_exempt = True
        self.ml_exempt = True
        self.stop_loss_pct = 1.0
        self.take_profit_pct = self.params.weighted_rr

    def _make_td_signal(self, symbol: str, row: pd.Series) -> Optional[TradeSignal]:
        p = self.params
        long_sig = bool(row["long_signal"])
        short_sig = bool(row["short_signal"])
        if not (long_sig or short_sig):
            return None

        close = float(row["close"])
        atr = float(row["atr"]) if not pd.isna(row["atr"]) else 0.0
        if close <= 0 or atr <= 0:
            return None

        risk_pct = max(0.05, atr * p.stop_mult / close * 100.0)
        tp_pct = risk_pct * p.weighted_rr
        direction = "long" if long_sig else "short"
        vol_ratio = float(row["volume"] / row["vol_avg"]) if row["vol_avg"] else 1.0

        score = 0.66
        score += min(max((abs(float(row["rsi"]) - 50.0) / 100.0), 0.0), 0.08)
        score += min(max(vol_ratio - p.vol_mult, 0.0) * 0.04, 0.06)
        score = round(max(0.60, min(score, 0.86)), 3)

        return self._make_signal(
            symbol=symbol,
            direction=direction,
            score=score,
            reason=(
                f"TraderDev DayTraderV3 {direction}: ST flip + recent MACD "
                f"+ RSI/EMA/volume filters | risk={risk_pct:.2f}%"
            ),
            stop_loss_pct=round(risk_pct, 4),
            take_profit_pct=round(tp_pct, 4),
            metadata={
                "strategy_name": self.strategy_name,
                "source": "TraderDev Day Trader v3 BTC/SOL 15m",
                "port_note": "single-position weighted 2.8R TP approximation",
                "atr": round(atr, 8),
                "rsi": round(float(row["rsi"]), 3),
                "macd_hist": round(float(row["macd_hist"]), 8),
                "volume_ratio": round(vol_ratio, 3),
                "preferred_initial_stop_mode": "fixed_pct",
                "preferred_trail_mode": "none",
                "td_weighted_rr": p.weighted_rr,
            },
        )

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:
        if not self._check_enough_candles(symbol, candles, 80):
            return None
        try:
            sigs = generate_signals(candles, self.params)
            return self._make_td_signal(symbol, sigs.iloc[-1])
        except Exception as exc:
            self.logger.error("td_day_trader_v3 error on %s: %s", symbol, exc, exc_info=True)
            return None

    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        return generate_signals(df, self.params)

    def _analyze_from_precomputed(
        self,
        symbol: str,
        i: int,
        sigs: pd.DataFrame,
        df: pd.DataFrame,
    ) -> Optional[TradeSignal]:
        return self._make_td_signal(symbol, sigs.iloc[i])

    def _exit_from_precomputed(
        self,
        i: int,
        sigs: pd.DataFrame,
        direction: str,
        meta: dict,
    ) -> Optional[str]:
        row = sigs.iloc[i]
        if direction == "long" and bool(row.get("st_bear", False)):
            return "td_supertrend_exit"
        if direction == "short" and bool(row.get("st_bull", False)):
            return "td_supertrend_exit"
        if int(meta.get("_bars_held", 0)) >= self.params.time_cap:
            return "td_time_exit"
        return None

    def check_custom_exit(
        self,
        symbol: str,
        bars: pd.DataFrame,
        direction: str,
        entry_metadata: Optional[dict] = None,
    ) -> Optional[str]:
        sigs = generate_signals(bars, self.params)
        return self._exit_from_precomputed(
            len(sigs) - 1,
            sigs,
            direction,
            entry_metadata or {},
        )
