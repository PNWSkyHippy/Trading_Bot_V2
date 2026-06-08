"""
tema_crossover.py
=================
Port of TEMA1h_09641 Jesse Port (Trader Dev) — 2026-06-01

Signal logic:
  - Dual TEMA crossover: fast(11) vs slow(75) for short-term trend
  - Simulated HTF TEMA: fast(56) vs slow(300) for higher-timeframe alignment
  - ADX > 30: only trade in trending conditions
  - CMO filter: long when CMO > 30, short when CMO < -30
  - Limit entry: close ± ATR * entry_offset (better fill than market)
  - ATR-based SL and TP (symmetric by default)

Original ran on BTCUSDT 5m with fixed $1000 position size giving misleading
64,052% return due to leverage artifact. Strategy logic is sound; this port
uses proper position sizing via the bot's standard risk engine.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object
    TradeSignal  = None


@dataclass
class TEMAParams:
    # Short-term TEMA
    ema_fast:       int   = 11
    ema_slow:       int   = 75

    # HTF TEMA (simulated via multiplier)
    htf_fast:       int   = 14
    htf_slow:       int   = 75
    htf_mult:       int   = 4     # simulates 4× the base timeframe

    # Filters
    adx_period:     int   = 14
    adx_threshold:  float = 20.0  # sweep 2026-06-04: adx=20 gives 74% consistency (adx=30 drops to 61%)
    cmo_period:     int   = 14
    cmo_long:       float = 30.0
    cmo_short:      float = -30.0

    # Exits
    atr_period:     int   = 14
    atr_sl:         float = 3.0  # sweep 2026-06-04: best score rank #1 (PF 5.05, 74% consistency)
    atr_tp:         float = 5.0  # sweep 2026-06-04: rank #1
    entry_offset:   float = 1.0   # limit entry offset in ATR units


def _tema(series: pd.Series, length: int) -> pd.Series:
    e1 = series.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    e3 = e2.ewm(span=length, adjust=False).mean()
    return 3.0 * (e1 - e2) + e3


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up   = high.diff()
    down = -low.diff()
    pdm  = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    ndm  = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr   = pd.concat([high - low,
                      (high - close.shift()).abs(),
                      (low  - close.shift()).abs()], axis=1).max(axis=1)
    atr  = tr.ewm(span=period, adjust=False).mean()
    pdi  = 100 * pdm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    ndi  = 100 * ndm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    dx   = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(span=period, adjust=False).mean()


def _cmo(close: pd.Series, period: int) -> pd.Series:
    diff    = close.diff()
    up      = diff.clip(lower=0)
    down    = (-diff).clip(lower=0)
    up_sum  = up.rolling(period).sum()
    down_sum= down.rolling(period).sum()
    denom   = (up_sum + down_sum).replace(0, np.nan)
    return (up_sum - down_sum) / denom * 100


class TEMACrossoverStrategy(BaseStrategy):
    """
    Dual TEMA trend-following with ADX + CMO momentum filters.
    Ported from TEMA1h_09641 Jesse Port (Trader Dev).
    """

    def __init__(self):
        super().__init__()
        self.strategy_name           = "tema_crossover"
        self.params                  = TEMAParams()
        self.stop_loss_pct           = 2.0    # fallback only — ATR-based preferred
        self.take_profit_pct         = 2.0    # fallback only
        self.crypto_enabled          = False  # sweep 2026-06-04: PF=0.30, 0% consistency on all combos — dead
        self.stock_enabled           = True   # sweep 2026-06-04: PF=5.05, 74% consistency on 15m
        self.crypto_candle_timeframe = "5m"
        self.stock_candle_timeframe  = "15Min"  # sweep confirmed edge on 15m (not 5m)
        self.ml_exempt               = True
        self.reviewer_exempt         = True
        self.enabled                 = True

        p = self.params
        # Need enough bars for slowest indicator: TEMA slow × htf_mult + ATR period
        self.candle_limit = p.ema_slow * p.htf_mult + p.atr_period + 50

    def analyze(self, symbol: str, candles: pd.DataFrame,
                market_condition: str = "unknown") -> Optional[TradeSignal]:
        p = self.params
        MIN_BARS = p.ema_slow * p.htf_mult + p.atr_period + 20
        if not self._check_enough_candles(symbol, candles, MIN_BARS):
            return None

        try:
            df    = candles.copy()
            close = df["close"]

            # ── TEMA calculations ──────────────────────────────────────────
            t_fast = _tema(close, p.ema_fast)
            t_slow = _tema(close, p.ema_slow)
            h_fast = _tema(close, p.htf_fast * p.htf_mult)
            h_slow = _tema(close, p.htf_slow * p.htf_mult)

            # ── Filters ────────────────────────────────────────────────────
            adx_series = _adx(df, p.adx_period)
            cmo_series = _cmo(close, p.cmo_period)
            atr_series = (pd.concat([
                df["high"] - df["low"],
                (df["high"] - close.shift()).abs(),
                (df["low"]  - close.shift()).abs()
            ], axis=1).max(axis=1).ewm(span=p.atr_period, adjust=False).mean())

            # ── Last closed bar ────────────────────────────────────────────
            idx   = df.index[-1]
            tf    = float(t_fast.loc[idx])
            ts    = float(t_slow.loc[idx])
            hf    = float(h_fast.loc[idx])
            hs    = float(h_slow.loc[idx])
            adx   = float(adx_series.loc[idx])
            cmo   = float(cmo_series.loc[idx])
            atr   = float(atr_series.loc[idx])
            price = float(close.loc[idx])

            self.verbose_log(symbol, "tema_short_long",  tf > ts, tf, ts)
            self.verbose_log(symbol, "tema_htf_long",    hf > hs, hf, hs)
            self.verbose_log(symbol, "adx_above_thresh", adx > p.adx_threshold, adx, p.adx_threshold)
            self.verbose_log(symbol, "cmo",              cmo, cmo, p.cmo_long)

            # ── Signal conditions ──────────────────────────────────────────
            trending = adx > p.adx_threshold
            if not trending:
                return None

            short_long  = tf > ts
            short_short = tf < ts
            htf_long    = hf > hs
            htf_short   = hf < hs
            cmo_ok_long  = cmo > p.cmo_long
            cmo_ok_short = cmo < p.cmo_short

            is_long  = short_long  and htf_long  and cmo_ok_long
            is_short = short_short and htf_short and cmo_ok_short

            if not (is_long or is_short):
                return None

            direction = "long" if is_long else "short"

            # ── ATR-based SL / TP ──────────────────────────────────────────
            sl_pct = round(p.atr_sl * atr / price * 100, 3)
            tp_pct = round(p.atr_tp * atr / price * 100, 3)
            sl_pct = max(sl_pct, 0.3)
            tp_pct = max(tp_pct, 0.3)

            # Score: ADX strength + CMO conviction
            adx_score = min(0.15, (adx - p.adx_threshold) / 100)
            cmo_score = min(0.10, (abs(cmo) - abs(p.cmo_long)) / 100)
            score = round(max(0.55, min(0.88, 0.60 + adx_score + cmo_score)), 3)

            self.verbose_log_score(symbol, score, 0.55)

            vol_ma    = candles["volume"].rolling(20).mean().iloc[-1]
            vol_ratio = round(float(candles["volume"].iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

            reason = (
                f"TEMA {'LONG' if is_long else 'SHORT'}: "
                f"fast={'↑' if short_long else '↓'} htf={'↑' if htf_long else '↓'} "
                f"adx={adx:.1f} cmo={cmo:.1f}"
            )

            return TradeSignal(
                symbol          = symbol,
                strategy_name   = self.strategy_name,
                direction       = direction,
                score           = score,
                stop_loss_pct   = sl_pct,
                take_profit_pct = tp_pct,
                reason          = reason,
                metadata        = {
                    "strategy_name":    self.strategy_name,
                    "ml_exempt":        self.ml_exempt,
                    "reviewer_exempt":  self.reviewer_exempt,
                    "asset_class":      "stock",
                    "tema_fast":        round(tf, 4),
                    "tema_slow":        round(ts, 4),
                    "htf_fast":         round(hf, 4),
                    "htf_slow":         round(hs, 4),
                    "adx":              round(adx, 2),
                    "cmo":              round(cmo, 2),
                    "atr":              round(atr, 4),
                    "volume_ratio":     vol_ratio,
                    "preferred_initial_stop_mode": "percent",
                    "preferred_trail_mode":        "two_bar",
                },
            )

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "[TEMACrossover] %s: analysis error: %s", symbol, e
            )
            return None
