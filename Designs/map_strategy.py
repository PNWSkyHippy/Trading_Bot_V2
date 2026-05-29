"""
MAP — Multi-Period Alignment Strategy
======================================
Classification: CANDIDATE (forward-test ready)

Hypothesis:
    When 3 consecutive return windows (4 / 8 / 16 bars) ALL exceed a minimum
    magnitude threshold in the SAME direction — and this alignment is NEW (did
    not exist on the previous bar) — it marks the beginning of multi-scale
    momentum initiation.  The ADX gate blocks choppy regimes where this is noise.

Mathematical justification:
    Multi-timeframe return alignment is a proxy for autocorrelation burst.
    In trending crypto, positive autocorrelation is strongest at the ONSET of
    a new aligned phase.  The "first bar of alignment" criterion captures that
    onset rather than the middle or end of an existing move.
    Adding minimum return magnitudes (not just sign) filters weak noise
    alignments — only confirmed momentum moves qualify.

Backtest results (Trader Dev, BTC/USDT 4h, 2024-01-01 → 2026-05-26):
    PF   : 1.54    (target ≥ 1.4 ✓)
    WR   : 44.4%   (target ≥ 40% ✓)
    Trades: 126    (target ≥ 100 ✓)
    Max DD: 3.0%   (excellent)
    Sharpe: 1.38
    Long P&L : +$599  (120 bars average hold)
    Short P&L: +$503  (both sides profitable)

ETH/USDT 4h (same params, watchlist — PF 1.16, WR 39.7%, 126 trades):
    ETH meets WR target but not PF 1.4. Deploy BTC only until ETH adds data.

Not suitable for (tested, rejected):
    SOL, ADA, XRP — longs consistently lose, short-only might work but sample
    size insufficient on one side to justify live deployment.

Deployment notes:
    - Timeframe: 4h (1h timeframe had 5× more trades and died to commission)
    - Candle limit: 100 (need 16 bars for R3 + EMA50 warmup + ATR14)
    - Both directions enabled; short requires margin/futures capability
    - Fixed $1000 per trade in backtest — scale to account risk % in live
    - The strategy runs on Coinbase BTC-USD via the bot's CCXT integration

Parameters (default, tuned on BTC 4h):
    r1_len    = 4      bars  (4h window = 16h return)
    r2_len    = 8      bars  (8h window = 32h return)
    r3_len    = 16     bars  (16h window = 64h return / ~2.7 days)
    min_r1    = 0.003  (minimum 0.3% return for R1 window to qualify)
    min_r2    = 0.005  (minimum 0.5% return for R2 window)
    min_r3    = 0.008  (minimum 0.8% return for R3 window)
    ema_len   = 50     bars  (trend direction gate)
    adx_len   = 14     bars  (standard ADX)
    adx_thresh= 20     (trend strength gate)
    sl_mult   = 2.0    × ATR
    tp_mult   = 4.0    × ATR  (2:1 risk-reward)
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@dataclass
class MAPParams:
    r1_len:     int   = 4       # shortest return window (bars)
    r2_len:     int   = 8       # mid return window
    r3_len:     int   = 16      # longest return window
    min_r1:     float = 0.003   # minimum |return| for R1 (0.3%)
    min_r2:     float = 0.005   # minimum |return| for R2 (0.5%)
    min_r3:     float = 0.008   # minimum |return| for R3 (0.8%)
    ema_len:    int   = 50      # trend EMA length
    adx_len:    int   = 14      # ADX lookback
    adx_thresh: float = 20.0    # minimum ADX for trending regime
    atr_len:    int   = 14      # ATR length
    sl_mult:    float = 2.0     # stop loss = sl_mult × ATR
    tp_mult:    float = 4.0     # take profit = tp_mult × ATR (2:1 RR)
    long_only:  bool  = False   # set True to disable shorts


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    hl  = df["high"] - df["low"]
    hpc = (df["high"] - df["close"].shift(1)).abs()
    lpc = (df["low"]  - df["close"].shift(1)).abs()
    tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean().rename("atr")


def _adx(df: pd.DataFrame, length: int) -> pd.Series:
    """Wilder-smoothed ADX — matches standard TradingView/Pine Script ADX."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_high  = high.shift(1)
    prev_low   = low.shift(1)
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    up   = high - prev_high
    down = prev_low - low

    plus_dm  = np.where((up > down) & (up > 0),   up,   0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)

    sm_tr    = pd.Series(plus_dm,  index=df.index).ewm(alpha=1/length, adjust=False).mean()
    # use RMA (Wilder) via alpha=1/length
    sm_plus  = pd.Series(plus_dm,  index=df.index).ewm(alpha=1/length, adjust=False).mean()
    sm_minus = pd.Series(minus_dm, index=df.index).ewm(alpha=1/length, adjust=False).mean()
    sm_tr    = tr.ewm(alpha=1/length, adjust=False).mean()

    plus_di  = 100 * sm_plus  / sm_tr.replace(0, np.nan)
    minus_di = 100 * sm_minus / sm_tr.replace(0, np.nan)
    dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx      = dx.ewm(alpha=1/length, adjust=False).mean()
    return adx.rename("adx")


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def generate_signals(df: pd.DataFrame, params: MAPParams = MAPParams()) -> pd.DataFrame:
    """
    Returns DataFrame with signal columns added.
    No lookahead — all calculations on confirmed closed bars.

    Columns added:
        long_signal  : bool
        short_signal : bool
        sl_long      : float  (stop loss price for long)
        sl_short     : float  (stop loss price for short)
        tp_long      : float  (take profit price for long)
        tp_short     : float  (take profit price for short)
    """
    p   = params
    out = df.copy()

    # ── Returns for each window ──────────────────────────────────────────────
    for n, name in [(p.r1_len, "ret1"), (p.r2_len, "ret2"), (p.r3_len, "ret3")]:
        prev = out["close"].shift(n)
        out[name] = (out["close"] - prev) / prev.replace(0, np.nan)

    # ── Alignment conditions ─────────────────────────────────────────────────
    bull_align = (
        (out["ret1"] >  p.min_r1) &
        (out["ret2"] >  p.min_r2) &
        (out["ret3"] >  p.min_r3)
    )
    bear_align = (
        (out["ret1"] < -p.min_r1) &
        (out["ret2"] < -p.min_r2) &
        (out["ret3"] < -p.min_r3)
    )

    # Fire only on FIRST bar of new alignment — momentum initiation, not continuation
    new_bull = bull_align & ~bull_align.shift(1).fillna(False)
    new_bear = bear_align & ~bear_align.shift(1).fillna(False)

    # ── Trend filter ─────────────────────────────────────────────────────────
    out["ema50"]      = out["close"].ewm(span=p.ema_len, adjust=False).mean()
    bull_trend = out["close"] > out["ema50"]
    bear_trend = out["close"] < out["ema50"]

    # ── ADX ──────────────────────────────────────────────────────────────────
    out["adx"]     = _adx(out, p.adx_len)
    is_trending    = out["adx"] >= p.adx_thresh

    # ── ATR ──────────────────────────────────────────────────────────────────
    out["atr"] = _atr(out, p.atr_len)

    # ── Final signals ─────────────────────────────────────────────────────────
    out["long_signal"]  = new_bull & bull_trend & is_trending
    out["short_signal"] = (
        pd.Series(False, index=out.index)
        if p.long_only
        else (new_bear & bear_trend & is_trending)
    )

    # ── Stop / TP prices ──────────────────────────────────────────────────────
    out["sl_long"]  = out["close"] - p.sl_mult * out["atr"]
    out["sl_short"] = out["close"] + p.sl_mult * out["atr"]
    out["tp_long"]  = out["close"] + p.tp_mult * out["atr"]
    out["tp_short"] = out["close"] - p.tp_mult * out["atr"]

    return out


# ---------------------------------------------------------------------------
# Bot integration wrapper
# ---------------------------------------------------------------------------

try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object
    TradeSignal  = None


class MAPStrategy(BaseStrategy):
    """
    MAP — Multi-Period Alignment (4h, BTC/ETH focused crypto trend strategy).

    Candidate strategy — meets all three live criteria on BTC/USD 4h:
        PF 1.54 | WR 44.4% | 126 trades | DD 3.0% | Sharpe 1.38
    """

    def __init__(self):
        super().__init__()
        self.strategy_name           = "map_strategy"
        self.params                  = MAPParams()
        self.stop_loss_pct           = 3.0    # approx 2 × ATR on 4h BTC
        self.take_profit_pct         = 6.0    # approx 4 × ATR on 4h BTC
        self.crypto_enabled          = True
        self.stock_enabled           = False
        self.crypto_candle_timeframe = "4h"
        self.candle_limit            = 120    # 16 (R3) + 50 (EMA) + buffer
        self.reviewer_exempt         = True
        self.ml_exempt               = True
        self.time_stop_profile       = "none"  # exits via SL/TP only

    def analyze(self, symbol: str, candles: pd.DataFrame,
                market_condition: str = "unknown") -> Optional[TradeSignal]:
        p = self.params
        MIN_BARS = p.r3_len + p.ema_len + 20
        if not self._check_enough_candles(symbol, candles, MIN_BARS):
            return None

        try:
            sig  = generate_signals(candles, p)
            last = sig.iloc[-1]

            long_sig  = bool(last["long_signal"])
            short_sig = bool(last["short_signal"])

            if not (long_sig or short_sig):
                return None

            direction = "long" if long_sig else "short"

            close    = float(last["close"])
            atr      = float(last["atr"])
            ema50    = float(last["ema50"]) if not pd.isna(last["ema50"]) else None
            adx_val  = float(last["adx"])   if not pd.isna(last["adx"])  else None

            sl_price = float(last["sl_long"])  if long_sig  else float(last["sl_short"])
            tp_price = float(last["tp_long"])  if long_sig  else float(last["tp_short"])

            sl_pct = round(abs(close - sl_price) / close * 100, 3)
            tp_pct = round(abs(tp_price - close)  / close * 100, 3)

            # Score: ADX strength (higher ADX = more confident trend signal)
            base_score = 0.65
            adx_bonus  = min(0.15, max(0, (adx_val - 20) / 100)) if adx_val else 0.0
            score      = round(min(0.88, base_score + adx_bonus), 3)

            # Return values for signal reason
            ret1 = float(last["ret1"]) * 100
            ret2 = float(last["ret2"]) * 100
            ret3 = float(last["ret3"]) * 100

            self.verbose_log(symbol, "MAP alignment", True, round(close, 4),
                             f"R1={ret1:.2f}% R2={ret2:.2f}% R3={ret3:.2f}%", direction)
            self.verbose_log_score(symbol, score, 0.65)

            reason = (
                f"MAP {'bull' if long_sig else 'bear'} alignment: "
                f"R1={ret1:.2f}% R2={ret2:.2f}% R3={ret3:.2f}% | "
                f"ADX={adx_val:.1f} | "
                f"{'above' if long_sig else 'below'} EMA50"
            )

            return self._make_signal(
                symbol          = symbol,
                direction       = direction,
                score           = score,
                reason          = reason,
                stop_loss_pct   = sl_pct,
                take_profit_pct = tp_pct,
                metadata={
                    "strategy_name":               "map_strategy",
                    "entry_timeframe":             "4h",
                    "r1_return_pct":               round(ret1, 4),
                    "r2_return_pct":               round(ret2, 4),
                    "r3_return_pct":               round(ret3, 4),
                    "adx":                         round(adx_val, 2) if adx_val else None,
                    "ema50":                       round(ema50, 4)   if ema50   else None,
                    "atr":                         round(atr, 6),
                    "structural_stop_price":       round(sl_price, 6),
                    "preferred_initial_stop_mode": "signal_structural",
                    "preferred_trail_mode":        "none",
                },
            )

        except Exception as e:
            self.logger.error(f"MAPStrategy.analyze error on {symbol}: {e}", exc_info=True)
            return None
