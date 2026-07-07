"""
Strategy: VB-M -- Volatility Breakout Momentum
===============================================

Port of ZCode/backtesting/strategy_vbm.py (GLM5.2's v1, unfinished) into the
bot's strategy interface, with the exits implemented for real this time.

WHY THIS EDGE CLASS (vs VTRT/vtmr mean-reversion)
-------------------------------------------------
VTRT died on our real cost structure: its winners are small ATR fractions and
its holds ~2 bars, so the 0.62% crypto round-trip (Kraken taker + slippage)
exceeded the gross edge (matrix run 2026-07-06: gross +$2k, fees $13.3k,
PF 0.26). VB-M is the structural opposite: breakout entries with chandelier
trailing exits, so a typical winner is a multiple of ATR and fees are a small
fraction of P&L. Breakeven WR is ~35% by construction (trail lets winners run,
hard ATR stop caps losers).

COMPONENTS
----------
  1. TRIGGER - close breaks the prior `entry_len`-bar Donchian high by
     `breakout_k * ATR` (noise filter). Symmetric for shorts.
  2. EXIT    - chandelier trail: `trail_k * ATR` giveback from the favorable
     extreme since entry. Initial hard stop `sl_atr_mult * ATR` (engine-owned,
     structural). Max-hold backstop.
  3. REGIME (v2, param-gated) - GLM's design doc called for an EMA(50) trend
     bias but his v1 never implemented it. `trend_filter=True` only takes
     breakouts in the EMA(50) trend direction.

Params are iterated via the backtest matrix; defaults below are GLM's v1
baseline so the first matrix run measures his design faithfully.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import talib as tl
from typing import Optional

from strategies.base_strategy import BaseStrategy, TradeSignal


DEFAULT_PARAMS = {
    # Validated 2026-07-07 via matrix sweeps v1-v4 (real fees, 0.62% RT crypto):
    # DAILY candles, long bias. Crypto broad (20 pairs, 1500d): 24/24 configs
    # PF>1, this set PF 2.06 pooled; per-pair leaders AVAX 5.4 / XRP 4.9 /
    # SOL 3.2. Stocks (15 syms, 720d) same params long-only: PF 2.88 WR 50%.
    # GLM's v1 defaults (entry_len 12, k 0.2, trail 2.0, no trend filter, 5m-1h)
    # scored PF 0.08-0.49 — structure below the crypto fee floor.
    # regime
    "ema_trend":      50,
    "trend_filter":   True,
    "atr_period":     14,
    # breakout trigger
    "entry_len":      96,     # bars for the Donchian high/low lookback
    "breakout_k":     0.60,   # fraction of ATR price must exceed the channel by
    # exit (chandelier trailing stop)
    "trail_k":        3.0,    # trail distance in ATR
    "sl_atr_mult":    2.5,    # initial hard stop (engine-owned structural stop)
    "max_hold":       96,     # bars
}


def compute_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    out = df.copy()
    close, high, low = out["close"], out["high"], out["low"]
    out["ema_trend"] = tl.EMA(close.values, timeperiod=p["ema_trend"])
    out["atr"] = tl.ATR(high.values, low.values, close.values,
                        timeperiod=p["atr_period"])
    n = p["entry_len"]
    out["don_high"] = high.rolling(n).max().shift(1)   # prior bar's N-high
    out["don_low"] = low.rolling(n).min().shift(1)     # prior bar's N-low
    return out


def generate_entry_signals(df: pd.DataFrame, p: dict | None = None):
    """Raw breakout triggers (the engine owns position state and dedup)."""
    p = {**DEFAULT_PARAMS, **(p or {})}
    ind = compute_indicators(df, p)
    c = ind["close"].values
    atr_v = ind["atr"].fillna(0.0).values
    don_high = ind["don_high"].values
    don_low = ind["don_low"].values
    bk = p["breakout_k"]

    long_raw = c > (don_high + bk * atr_v)
    short_raw = c < (don_low - bk * atr_v)

    if p.get("trend_filter"):
        ema = ind["ema_trend"].values
        long_raw = long_raw & (c > ema)
        short_raw = short_raw & (c < ema)

    ind["long_signal"] = pd.Series(long_raw, index=ind.index).fillna(False)
    ind["short_signal"] = pd.Series(short_raw, index=ind.index).fillna(False)
    return ind


class VBMStrategy(BaseStrategy):
    """VB-M: Donchian+ATR breakout momentum with chandelier trailing exits."""

    def __init__(self):
        super().__init__()
        self.strategy_name = "vbm_strategy"
        self.params = DEFAULT_PARAMS.copy()
        self.crypto_enabled = True
        self.stock_enabled = True
        self.crypto_candle_timeframe = "1d"
        self.stock_candle_timeframe = "1Day"
        self.candle_limit = 300
        self.stop_loss_pct = 4.0
        self.take_profit_pct = 30.0          # trail owns the exit; TP is a far backstop
        self.time_stop_profile = "strategy_defined"
        self.reviewer_exempt = True
        self.ml_exempt = True

    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        return generate_entry_signals(df, self.params)

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:
        min_bars = max(80, self.params["ema_trend"] + 10)
        if not self._check_enough_candles(symbol, candles, min_bars):
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
        atr = float(row.get("atr", 0.0) or 0.0)
        if not np.isfinite(atr) or atr <= 0 or close <= 0:
            return None

        direction = "long" if long_sig else "short"
        sl_mult = self.params["sl_atr_mult"]
        sl_pct = max(round(atr / close * sl_mult * 100, 3), 0.5)
        stop_price = close - atr * sl_mult if direction == "long" else close + atr * sl_mult

        # score: how decisively the channel broke, in ATRs beyond the filter
        don = float(row.get("don_high" if direction == "long" else "don_low", close) or close)
        excess_atr = abs(close - don) / atr
        score = round(max(0.65, min(0.92, 0.65 + excess_atr * 0.08)), 3)

        return self._make_signal(
            symbol=symbol,
            direction=direction,
            score=score,
            reason=f"VB-M {direction}: {self.params['entry_len']}-bar break by {excess_atr:.2f} ATR",
            stop_loss_pct=sl_pct,
            take_profit_pct=self.take_profit_pct,
            metadata={
                "strategy_name": self.strategy_name,
                "entry_timeframe": self.crypto_candle_timeframe if "/" in symbol else self.stock_candle_timeframe,
                "entry_atr": round(atr, 6),
                "excess_atr": round(excess_atr, 3),
                "structural_stop_price": round(stop_price, 6),
                "preferred_initial_stop_mode": "signal_structural",
                "preferred_trail_mode": "none",   # chandelier trail is strategy-owned below
                "custom_exit_owner": self.strategy_name,
            },
        )

    # ── Exits: chandelier trail + max-hold (hard stop is engine-owned) ──────

    def _exit_from_precomputed(self, i: int, sigs: pd.DataFrame,
                               direction: str, meta: dict) -> Optional[str]:
        bars_held = int(meta.get("_bars_held", 0) or 0)
        if bars_held >= int(self.params["max_hold"]):
            return "vbm_max_hold"
        if bars_held < 1:
            return None
        entry_i = max(0, i - bars_held)
        cur_close = float(sigs["close"].iloc[i])
        cur_atr = float(sigs["atr"].iloc[i] or 0.0)
        if cur_atr <= 0:
            return None
        tk = self.params["trail_k"]
        if direction == "long":
            best = float(sigs["high"].iloc[entry_i:i + 1].max())
            if cur_close <= best - tk * cur_atr:
                return "vbm_chandelier"
        else:
            best = float(sigs["low"].iloc[entry_i:i + 1].min())
            if cur_close >= best + tk * cur_atr:
                return "vbm_chandelier"
        return None

    def check_custom_exit(
        self,
        symbol: str,
        bars: pd.DataFrame,
        direction: str,
        entry_metadata: Optional[dict] = None,
    ) -> Optional[str]:
        if bars is None or len(bars) < 2:
            return None
        meta = entry_metadata or {}
        bars_held = int(meta.get("_bars_held", 0) or 0)
        if bars_held >= int(self.params["max_hold"]):
            return "vbm_max_hold"
        if bars_held < 1:
            return None
        since = bars.iloc[-min(bars_held + 1, len(bars)):]
        cur_close = float(bars["close"].iloc[-1])
        atr_arr = tl.ATR(bars["high"].values, bars["low"].values,
                         bars["close"].values, timeperiod=self.params["atr_period"])
        cur_atr = float(atr_arr[-1]) if np.isfinite(atr_arr[-1]) else float(meta.get("entry_atr", 0.0) or 0.0)
        if cur_atr <= 0:
            return None
        tk = self.params["trail_k"]
        if direction == "long":
            best = float(since["high"].max())
            if cur_close <= best - tk * cur_atr:
                return "vbm_chandelier"
        else:
            best = float(since["low"].min())
            if cur_close >= best + tk * cur_atr:
                return "vbm_chandelier"
        return None
