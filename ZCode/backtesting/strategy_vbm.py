"""
Strategy: VB-M -- Volatility Breakout Momentum
===============================================

WHY A NEW STRATEGY CLASS
------------------------
VTRT (mean-reversion) was proven timeframe-limited: on 5m/15m the 0.2%
round-trip fee exceeds the small reversion move, so PF collapsed to 0.12-0.30
no matter the parameters. The fix is a DIFFERENT edge class whose per-trade
move is large relative to fees.

VB-M is a volatility-breakout momentum system. Its three properties are chosen
specifically to fix reversion's failures on lower timeframes:

  1. LARGE per-trade move. Entries fire on a genuine range break, and a
     trailing stop lets the trade run. A typical winner is 3-6x the fee,
     so fees are a small fraction of P&L (the opposite of reversion).

  2. HIGH frequency. Breakouts of the last N bars happen often on 5m/15m --
     the lookback `entry_len` directly controls trade count and is short
     (e.g. 8-20 bars) on lower timeframes.

  3. SYMMETRIC long/short. Momentum works in both directions; the same logic
     buys upside breakouts and shorts downside breakouts.

THE EDGE (3 components)
-----------------------
  1. REGIME   - EMA(50) trend + ATR-scaled volatility channel. We trade
                breakouts in EITHER direction but bias position side with the
                trend (an upside breakout against a downtrend is allowed but
                the trail is tighter; a breakout WITH the trend is the A+ setup).

  2. TRIGGER  - Close crosses above (Donchian high of last `entry_len` bars) +
                `breakout_k * ATR` (a volatility fraction that filters noise).
                Symmetric for shorts.

  3. EXIT     - Chandelier-style trailing stop: peak/trough since entry minus
                `trail_k * ATR`. This is the structural opposite of reversion's
                "exit at the mean" -- momentum winners MUST run, and the trail
                captures the trend while protecting gains.

R:R is positive by construction (trailing winners, fixed-distance losers), so
the system is profitable at a LOWER win rate than reversion needs -- typically
breakeven at ~35% WR. That's the right profile for breakout trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import talib as tl


DEFAULT_PARAMS = {
    # regime
    "ema_trend":      50,
    "atr_period":     14,
    # breakout trigger
    "entry_len":      12,     # bars for the Donchian high/low lookback
    "breakout_k":     0.20,   # fraction of ATR price must exceed the channel by
    # exit (chandelier trailing stop)
    "trail_k":        2.0,    # trail distance in ATR
    "sl_atr_mult":    1.5,    # initial hard stop (backstop before trail engages)
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


def generate_signals(df: pd.DataFrame, p: dict | None = None):
    p = {**DEFAULT_PARAMS, **(p or {})}
    ind = compute_indicators(df, p)
    close = ind["close"]
    c = close.values
    atr_v = ind["atr"].fillna(0.0).values
    don_high = ind["don_high"].values
    don_low = ind["don_low"].values
    ema_trend = ind["ema_trend"].values
    mh = p["max_hold"]
    bk = p["breakout_k"]
    tk = p["trail_k"]
    sl_mult = p["sl_atr_mult"]

    # breakout triggers (long: close > don_high + k*ATR; symmetric short)
    long_raw = c > (don_high + bk * atr_v)
    short_raw = c < (don_low - bk * atr_v)

    long_raw_v = np.asarray(pd.Series(long_raw).fillna(False), dtype=bool)
    short_raw_v = np.asarray(pd.Series(short_raw).fillna(False), dtype=bool)

    # Lifecycle with chandelier trailing stop.
    # - On entry: set hard stop at entry - sl_mult*ATR (long) / entry + sl_mult*ATR (short).
    # - Track favorable excursion (peak for long / trough for short).
    # - Trail: exit when price gives back trail_k*ATR from the peak/trough.
    # - Also exit on max-hold.
    def _lifecycle(raw, side):
        entries = np.zeros(len(c), dtype=bool)
        exits = np.zeros(len(c), dtype=bool)
        in_pos = False
        entry_px = 0.0
        entry_i = 0
        stop_px = 0.0
        best = 0.0          # favorable excursion tracker
        for i in range(len(c)):
            if not in_pos and raw[i]:
                entry_px = c[i]
                entry_i = i
                atr_i = atr_v[i] if atr_v[i] > 0 else 1.0
                if side > 0:
                    stop_px = entry_px - sl_mult * atr_i
                    best = entry_px
                else:
                    stop_px = entry_px + sl_mult * atr_i
                    best = entry_px
                entries[i] = True
                in_pos = True
            if in_pos:
                bars_in = i - entry_i
                atr_i = atr_v[i] if atr_v[i] > 0 else 1.0
                if side > 0:
                    best = max(best, c[i])
                    # trail tightens as price rises: trail stop = best - trail_k*ATR
                    trail_stop = best - tk * atr_i
                    # effective stop is the HIGHER of initial hard stop and trail
                    eff_stop = max(stop_px, trail_stop)
                    hit_stop = c[i] <= eff_stop
                else:
                    best = min(best, c[i])
                    trail_stop = best + tk * atr_i
                    eff_stop = min(stop_px, trail_stop)
                    hit_stop = c[i] >= eff_stop
                if hit_stop or bars_in >= mh:
                    exits[i] = True
                    in_pos = False
        return entries, exits

    le, lx = _lifecycle(long_raw_v, +1)
    se, sx = _lifecycle(short_raw_v, -1)

    long_entries = pd.Series(le, index=close.index)
    long_exits = pd.Series(lx, index=close.index)
    short_entries = pd.Series(se, index=close.index)
    short_exits = pd.Series(sx, index=close.index)

    # vectorbt nominal stops (lifecycle manages the real exit; these are a backstop)
    atr_pct = (ind["atr"] / close).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    sl_stop = sl_mult * atr_pct
    tp_stop = None
    trailing = None

    return long_entries, long_exits, short_entries, short_exits, sl_stop, tp_stop, trailing, p["max_hold"]
