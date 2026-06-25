"""TraderDev F40D-ADX ETH 1h parity port."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, TradeSignal
from strategies.btc_v6_chandelier import _adx, _ema


@dataclass
class TraderDevF40DADXParams:
    adx_thresh: float = 10.0
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 5.0
    expansion_z: float = 1.0
    min_vel_z: float = 0.5
    detrend_len: int = 50
    env_smooth_len: int = 10
    env_slope_len: int = 10
    env_base_len: int = 150
    price_vel_len: int = 5


def _zscore(series: pd.Series, length: int) -> pd.Series:
    mean = series.rolling(length).mean()
    std = series.rolling(length).std(ddof=0)
    return (series - mean) / std.replace(0, np.nan)


def generate_signals(
    df: pd.DataFrame,
    params: TraderDevF40DADXParams = TraderDevF40DADXParams(),
) -> pd.DataFrame:
    p = params
    out = df.copy()
    c = out["close"]

    out["adx"] = _adx(out, 14)
    out["ema200"] = _ema(c, 200)
    out["regime_bull"] = c > out["ema200"]
    out["sideways"] = out["adx"] < p.adx_thresh

    trend = c.rolling(p.detrend_len).mean()
    osc = (c - trend).fillna(0.0)
    quad = (
        0.0962 * osc
        + 0.5769 * osc.shift(2).fillna(0.0)
        - 0.5769 * osc.shift(4).fillna(0.0)
        - 0.0962 * osc.shift(6).fillna(0.0)
    )
    env_inst = np.sqrt(osc * osc + quad * quad)
    env = env_inst.ewm(span=p.env_smooth_len, adjust=False).mean()
    env_slope = env - env.shift(p.env_slope_len).fillna(env)
    out["env_exp_z"] = _zscore(env_slope, p.env_base_len)

    price_vel = c - c.shift(p.price_vel_len).fillna(c)
    out["price_vel"] = price_vel
    out["price_vel_z"] = _zscore(price_vel, p.env_base_len)
    out["expansion_edge"] = (
        (out["env_exp_z"].shift(1) <= p.expansion_z)
        & (out["env_exp_z"] > p.expansion_z)
    )
    out["ready"] = np.arange(len(out)) > (p.detrend_len + p.env_base_len + 50)
    vel_ok = out["price_vel_z"].abs() > p.min_vel_z
    out["long_signal"] = (
        out["expansion_edge"]
        & (out["price_vel"] > 0)
        & vel_ok
        & out["regime_bull"]
        & ~out["sideways"]
        & out["ready"]
    )
    out["short_signal"] = (
        out["expansion_edge"]
        & (out["price_vel"] < 0)
        & vel_ok
        & ~out["sideways"]
        & out["ready"]
    )
    return out


class TraderDevF40DADXStrategy(BaseStrategy):
    """Envelope expansion edge with ADX/EMA200 regime filter."""

    def __init__(self):
        super().__init__()
        self.strategy_name = "td_f40d_adx"
        self.params = TraderDevF40DADXParams()
        self.crypto_enabled = True
        self.stock_enabled = False
        self.crypto_candle_timeframe = "1h"
        self.stop_loss_pct = self.params.stop_loss_pct
        self.take_profit_pct = self.params.take_profit_pct
        self.time_stop_profile = "strategy_defined"
        self.reviewer_exempt = True
        self.candle_limit = 300

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:
        if not self._check_enough_candles(symbol, candles, 260):
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
        if not (long_sig or short_sig):
            return None

        direction = "long" if long_sig else "short"
        vel_z = float(row["price_vel_z"])
        score = round(max(0.66, min(0.92, 0.66 + abs(vel_z) / 12.0)), 3)
        return self._make_signal(
            symbol=symbol,
            direction=direction,
            score=score,
            reason=(
                f"TD F40D {direction}: envZ={float(row['env_exp_z']):.2f} "
                f"velZ={vel_z:.2f} ADX={float(row['adx']):.1f}"
            ),
            stop_loss_pct=self.params.stop_loss_pct,
            take_profit_pct=self.params.take_profit_pct,
            metadata={
                "strategy_name": self.strategy_name,
                "env_exp_z": round(float(row["env_exp_z"]), 3),
                "price_vel_z": round(vel_z, 3),
                "adx": round(float(row["adx"]), 2),
                "preferred_trail_mode": "none",
            },
        )

    def _exit_from_precomputed(
        self,
        i: int,
        sigs: pd.DataFrame,
        direction: str,
        meta: dict,
    ) -> Optional[str]:
        row = sigs.iloc[i]
        if bool(row["sideways"]):
            return "sideways_exit"
        if direction == "long":
            if not bool(row["regime_bull"]):
                return "bear_exit"
            if bool(row["short_signal"]):
                return "env_flip_short"
        elif direction == "short" and bool(row["long_signal"]):
            return "env_flip_long"
        return None
