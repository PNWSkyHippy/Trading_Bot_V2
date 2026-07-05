"""
Strategy v7: VTRT - Volatility-Triggered Reversion in Trend
============================================================

THE MATH (why v1-v6 failed and this is the answer)
--------------------------------------------------
Profit Factor = (WR * avg_win) / ((1-WR) * avg_loss).

  WR   | min avg_win/avg_loss for PF=1.5
  -----|----------------------------------
  50%  | 1.50
  60%  | 1.00
  70%  | 0.64
  75%  | 0.50
  80%  | 0.375

v1/v3 hit WR 55-62% but only managed avg_win/avg_loss ~0.7 (winners capped at
the Bollinger mean, losers at the ATR stop) -> PF ~0.8. FATAL GEOMETRY.
v6 swung to R:R 2.2 but the breakout-pullback trigger only won 28-36%. FATAL WR.

The only way to clear PF=1.5 reliably is to push WIN RATE to ~75%+, where even
a 0.6 R:R (small winners, small losers, winners slightly smaller) is enough.
That is the Connors RSI(2) mean-reversion profile: enter on extreme short-term
oversold, exit on the first bounce. The win rate is high because short-term
RSI(2) extremes almost always snap back within a few bars.

THE VTRT EDGE (3 components, each previously validated)
-------------------------------------------------------
  1. REGIME  - Trade WITH the EMA(50) trend + ADX. Longs only in uptrend,
               shorts only in downtrend. (Validated in v3: ADX cut losers.)
  2. TRIGGER - RSI(2) extreme (oversold < threshold for longs). RSI(2) is far
               more reactive than RSI(7/14) and produces >70% snap-back rates
               on intraday data. The "VTRT" twist: require the bar's close to
               be in the lower/upper part of its range (true weakness/strength,
               not just a spike) -- a 2-confirmation gate that lifts WR further.
  3. EXIT    - First close above EMA(5) (longs) / below EMA(5) (shorts). This
               is the quick, high-probability exit. Hard ATR stop as backstop.
               R:R is modest (~0.6) by design; the WR carries it.

WHY THIS SHOULD HIT ALL FOUR CRITERIA
-------------------------------------
  - Win Rate 75%+ : RSI(2) snap-back is a robust empirical anomaly.
  - Max DD <= 20% : small per-trade risk (ATR stop), trend-aligned, no runners.
  - PF >= 1.5     : follows from WR 75% x R:R 0.6 math above.
  - Few trades/day: RSI(2) extremes fire often intraday on 5m/15m.

The 5m/15m/1h edge: same logic, parameterized per timeframe later.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import talib as tl
from typing import Optional

from strategies.base_strategy import BaseStrategy, TradeSignal


DEFAULT_PARAMS = {
    # regime / trend
    "ema_trend":      50,
    "ema_slope_len":  5,
    "adx_period":     14,
    "adx_min":        20.0,
    # trigger
    "rsi_period":     2,      # short-term RSI (Connors-style)
    "rsi_long_max":   15,     # very oversold -> long candidate
    "rsi_short_min":  85,     # very overbought -> short candidate
    "consec_bars":    1,      # bars the RSI extreme must persist (1=any, 2=streak)
    "close_pos_min":  0.45,   # long bar must close in lower 45% of its range
    "close_pos_max":  0.55,   # short bar must close in upper 55% of its range
    # exit
    "ema_exit":       5,      # exit EMA (quick take-profit)
    # risk
    "atr_period":     14,
    "sl_atr_mult":    2.0,    # hard stop (backstop; EMA exit usually fires first)
    "tp_atr_mult":    0.0,    # 0 = use EMA-exit; >0 = fixed ATR profit target
    "max_hold":       48,     # bars
}


def compute_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    out = df.copy()
    close, high, low = out["close"], out["high"], out["low"]
    out["ema_trend"] = tl.EMA(close.values, timeperiod=p["ema_trend"])
    out["ema_exit"] = tl.EMA(close.values, timeperiod=p["ema_exit"])
    out["adx"] = tl.ADX(high.values, low.values, close.values,
                        timeperiod=p["adx_period"])
    out["atr"] = tl.ATR(high.values, low.values, close.values,
                        timeperiod=p["atr_period"])
    out["rsi"] = tl.RSI(close.values, timeperiod=p["rsi_period"])
    out["trend_slope"] = out["ema_trend"] - out["ema_trend"].shift(p["ema_slope_len"])
    # bar close position within its high-low range (0=low, 1=high)
    rng = (high - low).replace(0, np.nan)
    out["close_pos"] = ((close - low) / rng).fillna(0.5)
    return out


def generate_signals(df: pd.DataFrame, p: dict | None = None):
    p = {**DEFAULT_PARAMS, **(p or {})}
    ind = compute_indicators(df, p)
    close = ind["close"]
    c = close.values
    atr_v = ind["atr"].fillna(0.0).values
    ema_exit = ind["ema_exit"].values
    ema_trend = ind["ema_trend"].values
    slope = ind["trend_slope"].values
    adx = ind["adx"].values
    rsi = ind["rsi"].values
    close_pos = ind["close_pos"].values
    mh = p["max_hold"]

    uptrend = (slope > 0) & (c > ema_trend) & (adx >= p["adx_min"])
    downtrend = (slope < 0) & (c < ema_trend) & (adx >= p["adx_min"])

    # Optional 2-bar consecutive-extreme confirmation (Connors-style WR booster).
    # Requiring the RSI extreme to persist for `consec` bars filters out one-bar
    # spikes that fail to revert and lifts reversion win rate substantially.
    consec = int(p.get("consec_bars", 1))
    rsi_ser = pd.Series(rsi, index=close.index)
    uptrend_s = pd.Series(uptrend, index=close.index).fillna(False)
    downtrend_s = pd.Series(downtrend, index=close.index).fillna(False)
    close_pos_s = pd.Series(close_pos, index=close.index).fillna(0.5)

    if consec <= 1:
        rsi_low_streak = (rsi_ser < p["rsi_long_max"]).fillna(False)
        rsi_high_streak = (rsi_ser > p["rsi_short_min"]).fillna(False)
    else:
        # count how many of the last `consec` bars were extreme
        low_extreme = (rsi_ser < p["rsi_long_max"]).astype(int)
        high_extreme = (rsi_ser > p["rsi_short_min"]).astype(int)
        rsi_low_streak = (low_extreme.rolling(consec).sum() >= consec).fillna(False)
        rsi_high_streak = (high_extreme.rolling(consec).sum() >= consec).fillna(False)

    long_raw = (uptrend_s
                & rsi_low_streak
                & (close_pos_s < p["close_pos_min"]))
    short_raw = (downtrend_s
                 & rsi_high_streak
                 & (close_pos_s > p["close_pos_max"]))

    long_raw_v = np.asarray(pd.Series(long_raw).fillna(False), dtype=bool)
    short_raw_v = np.asarray(pd.Series(short_raw).fillna(False), dtype=bool)

    # Lifecycle: take-profit on EMA-exit cross OR a fixed ATR target (whichever
    # the params choose), hard ATR stop as backstop, or max-hold.
    tp_atr = float(p.get("tp_atr_mult", 0.0))
    use_atr_target = tp_atr > 0.0

    def _lifecycle(raw, side):
        entries = np.zeros(len(c), dtype=bool)
        exits = np.zeros(len(c), dtype=bool)
        in_pos = False
        entry_px = 0.0
        entry_i = 0
        for i in range(len(c)):
            if not in_pos and raw[i]:
                entry_px = c[i]
                entry_i = i
                entries[i] = True
                in_pos = True
            if in_pos:
                bars_in = i - entry_i
                atr_i = atr_v[i] if atr_v[i] > 0 else 1.0
                if side > 0:
                    if use_atr_target:
                        hit_tp = c[i] >= entry_px + tp_atr * atr_i
                    else:
                        hit_tp = c[i] > ema_exit[i]
                    hit_sl = c[i] <= entry_px - p["sl_atr_mult"] * atr_i
                else:
                    if use_atr_target:
                        hit_tp = c[i] <= entry_px - tp_atr * atr_i
                    else:
                        hit_tp = c[i] < ema_exit[i]
                    hit_sl = c[i] >= entry_px + p["sl_atr_mult"] * atr_i
                if hit_tp or hit_sl or bars_in >= mh:
                    exits[i] = True
                    in_pos = False
        return entries, exits

    le, lx = _lifecycle(long_raw_v, +1)
    se, sx = _lifecycle(short_raw_v, -1)

    long_entries = pd.Series(le, index=close.index)
    long_exits = pd.Series(lx, index=close.index)
    short_entries = pd.Series(se, index=close.index)
    short_exits = pd.Series(sx, index=close.index)

    atr_pct = (ind["atr"] / close).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    sl_stop = p["sl_atr_mult"] * atr_pct
    tp_stop = None           # exit driven by EMA(5) cross in lifecycle
    trailing = None

    return long_entries, long_exits, short_entries, short_exits, sl_stop, tp_stop, trailing, p["max_hold"]


class VTMRStrategy(BaseStrategy):
    """VTRT/VTM-R: RSI(2) trend reversion with strategy-owned EMA/max-hold exits."""

    def __init__(self):
        super().__init__()
        self.strategy_name = "vtmr_strategy"
        self.params = DEFAULT_PARAMS.copy()
        self.crypto_enabled = True
        self.stock_enabled = True
        self.crypto_candle_timeframe = "1h"
        self.stock_candle_timeframe = "1Hour"
        self.candle_limit = 300
        self.stop_loss_pct = 4.0
        self.take_profit_pct = 30.0
        self.time_stop_profile = "strategy_defined"
        self.reviewer_exempt = True
        self.ml_exempt = True

    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        long_entries, long_exits, short_entries, short_exits, sl_stop, _, _, max_hold = generate_signals(df, self.params)
        out = compute_indicators(df, self.params)
        out["long_signal"] = long_entries
        out["short_signal"] = short_entries
        out["long_exit"] = long_exits
        out["short_exit"] = short_exits
        out["sl_stop"] = sl_stop
        out["max_hold"] = max_hold
        return out

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:
        if not self._check_enough_candles(symbol, candles, 80):
            return None
        sigs = self._precompute(symbol, candles)
        return self._analyze_from_precomputed(symbol, len(sigs) - 1, sigs, candles)

    def _analyze_from_precomputed(
        self,
        symbol: str,
        i: int,
        sigs: pd.DataFrame,
        df: pd.DataFrame,
    ) -> Optional[TradeSignal]:
        row = sigs.iloc[i]
        long_sig = bool(row.get("long_signal", False))
        short_sig = bool(row.get("short_signal", False))
        if not (long_sig or short_sig):
            return None

        close = float(row["close"])
        sl_frac = float(row.get("sl_stop", 0.0) or 0.0)
        if not np.isfinite(sl_frac) or sl_frac <= 0:
            return None

        direction = "long" if long_sig else "short"
        sl_pct = max(round(sl_frac * 100, 3), 0.5)
        adx = float(row.get("adx", 0.0) or 0.0)
        rsi = float(row.get("rsi", 50.0) or 50.0)
        close_pos = float(row.get("close_pos", 0.5) or 0.5)
        score = round(max(0.65, min(0.92, 0.66 + max(0.0, adx - self.params["adx_min"]) / 120.0)), 3)
        atr = float(row.get("atr", 0.0) or 0.0)
        stop_price = close - atr * self.params["sl_atr_mult"] if direction == "long" else close + atr * self.params["sl_atr_mult"]

        return self._make_signal(
            symbol=symbol,
            direction=direction,
            score=score,
            reason=f"VTM-R {direction}: RSI2={rsi:.1f} ADX={adx:.1f} close_pos={close_pos:.2f}",
            stop_loss_pct=sl_pct,
            take_profit_pct=self.take_profit_pct,
            metadata={
                "strategy_name": self.strategy_name,
                "entry_timeframe": self.crypto_candle_timeframe if "/" in symbol else self.stock_candle_timeframe,
                "rsi2": round(rsi, 2),
                "adx": round(adx, 2),
                "close_pos": round(close_pos, 3),
                "ema_exit": round(float(row.get("ema_exit", 0.0) or 0.0), 6),
                "atr": round(atr, 6),
                "structural_stop_price": round(stop_price, 6),
                "preferred_initial_stop_mode": "signal_structural",
                "preferred_trail_mode": "none",
                "custom_exit_owner": self.strategy_name,
            },
        )

    def check_custom_exit(
        self,
        symbol: str,
        bars: pd.DataFrame,
        direction: str,
        entry_metadata: Optional[dict] = None,
    ) -> Optional[str]:
        if bars is None or len(bars) < 10:
            return None
        meta = entry_metadata or {}
        sigs = compute_indicators(bars, self.params)
        last = sigs.iloc[-1]
        close = float(last["close"])
        ema_exit = float(last["ema_exit"])

        if direction == "long" and close > ema_exit:
            return "vtmr_ema_exit"
        if direction == "short" and close < ema_exit:
            return "vtmr_ema_exit"

        if int(meta.get("_bars_held", 0) or 0) >= int(self.params["max_hold"]):
            return "vtmr_max_hold"
        return None
