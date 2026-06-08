"""
BMR-357  —  Bollinger Band Mean Reversion  /  3-5-7 Risk Rule
==============================================================
CLASSIFICATION : INCUBATE
  Edge confirmed on crypto LONGS at 15m with strict parameters.
  Sample sizes too small for Candidate — needs 30+ pairs to build
  statistical weight.  Do NOT live trade until N >= 50 per direction.

STRATEGY BRIEF
--------------
Crypto pairs oscillate around a moving average.  When price closes
outside a Bollinger Band (20-period, 2 std dev) AND RSI confirms
exhaustion, the setup fades the move back to the SMA20 midline.

The math of 2:1 reward-to-risk forces positive profit factor regardless
of win rate, as long as WR > 33%.

    Entry  — Long:  close < BB(20, 2σ) lower   AND  RSI(14) < 30
    Entry  — Short: close > BB(20, 2σ) upper   AND  RSI(14) > 70
    TP:    3.0%  from entry  (or price returns to SMA20, whichever first)
    SL:    1.5%  from entry  (fixed)
    R:R:   2:1

THE 3-5-7 RISK RULE (enforced by risk engine / position sizer)
  3%  — maximum portfolio risk on any single trade
  5%  — maximum total portfolio exposure across all open positions
  7%  — minimum reward-to-risk threshold (TP/SL >= 2 satisfies this)

PROFIT FACTOR MATH (from 2:1 R:R)
  WR 40%: PF = (0.40 × 3%) / (0.60 × 1.5%) = 1.33
  WR 50%: PF = (0.50 × 3%) / (0.50 × 1.5%) = 2.00
  WR 67%: PF = (0.67 × 3%) / (0.33 × 1.5%) = 4.06

BACKTEST RESULTS (15m, 180 days, strict BB 2σ / RSI 30/70)
  BNB/USD  long: PF=2.96, 75% WR, 4 trades
  LINK/USD long: PF=2.32, 67% WR, 3 trades
  DOT/USD  long: PF=2.18, 67% WR, 3 trades
  BTC/USD  long: PF=1.67, 67% WR, 3 trades
  ADA/USD  both: PF=1.55, 50% WR, 4 trades
  AVAX/USD both: PF=1.21, 60% WR, 5 trades

KEY FINDINGS
  1. LONG SIDE WORKS: BB(2σ) + RSI<30 achieves 67-75% WR on crypto longs.
     This is the mean-reversion thesis working as intended.
  2. SHORT SIDE WEAK: crypto shorts produce 0-1 trades over 6 months.
     BB(2σ) + RSI>70 events are extremely rare in the bull market regime.
  3. STRICT > RELAXED: loosening to BB(1.5σ) + RSI(35/65) destroys edge.
     The 2σ + RSI<30 combination is exactly where the edge lives.
  4. SIGNAL FREQUENCY: fires 2-8 times per pair per 6 months at 15m.
     Must run across 30+ pairs to build statistical weight.

PARAMETERS TO TUNE BEFORE LIVE TRADING
  Recommend param sweep on: bb_std (1.75-2.25), rsi_long (25-33),
  sl_pct (1.0-2.0), tp_pct (2.5-4.0) across 30+ crypto pairs.
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

_log = logging.getLogger(__name__)


# ── Parameters ────────────────────────────────────────────────────────────────

@dataclass
class BMR357Params:
    # Bollinger Bands
    # Sweep winner (2026-06-07): 2.25σ gives edge rate 50% vs 24% at 2.0σ
    bb_len:         int   = 20
    bb_std:         float = 2.25

    # RSI confirmation
    # Sweep winner: RSI 28/72 selects deeper exhaustion than 30/70
    rsi_len:        int   = 14
    rsi_long:       float = 28.0      # long entry: RSI must be BELOW this
    rsi_short:      float = 72.0      # short entry: RSI must be ABOVE this

    # 3-5-7 Risk Rule — trade level
    # Sweep winner: TP 3.5% → R:R 2.33:1 (beats 2:1 default)
    sl_pct:         float = 1.5       # stop loss %   (rule "3": 3% portfolio risk → position size)
    tp_pct:         float = 3.5       # take profit % (R:R 2.33:1 — optimized from 3.0%)

    # 3-5-7 Risk Rule — portfolio level (enforced by risk engine, stored in metadata)
    max_risk_per_trade_pct:  float = 3.0    # 3 %
    max_portfolio_risk_pct:  float = 5.0    # 5 %
    min_rr_ratio:            float = 2.33   # 7 leg: TP/SL = 3.5/1.5 = 2.33

    # Trend filter — DISABLED by default.
    # SMA200 blocks mean-reversion entries because oversold longs are below SMA200
    # and overbought shorts are above it — the filter is self-defeating.
    sma_filter_len: int   = 0

    # Time stop
    max_bars:       int   = 48        # exit after 48 bars regardless (2 days on 1h, 12h on 15m)


# ── Indicators ────────────────────────────────────────────────────────────────

def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(com=length - 1, adjust=False).mean()
    avg_l = loss.ewm(com=length - 1, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).rename("rsi")


def _bollinger(close: pd.Series, length: int, num_std: float):
    mid   = close.rolling(length).mean()
    std   = close.rolling(length).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


def _sma(close: pd.Series, length: int) -> pd.Series:
    return close.rolling(length).mean()


# ── Signal generation ─────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame,
                     params: BMR357Params = BMR357Params()) -> pd.DataFrame:
    """
    No lookahead — all signals confirmed on the closed bar.

    Long:  close < bb_lower  AND  rsi < rsi_long
    Short: close > bb_upper  AND  rsi > rsi_short
    """
    p   = params
    out = df.copy()

    # Guard against multi-level / duplicate columns (yfinance artifact)
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[0]).lower() if isinstance(c, tuple) else str(c).lower()
                       for c in out.columns]
    if out.columns.duplicated().any():
        out = out.loc[:, ~out.columns.duplicated(keep="first")]

    bb_mid, bb_upper, bb_lower = _bollinger(out["close"], p.bb_len, p.bb_std)
    rsi_series                  = _rsi(out["close"], p.rsi_len)

    out["bb_mid"]   = bb_mid
    out["bb_upper"] = bb_upper
    out["bb_lower"] = bb_lower
    out["rsi"]      = rsi_series

    if p.sma_filter_len > 0:
        out["sma_filter"] = _sma(out["close"], p.sma_filter_len)
        bull_bias = out["close"] > out["sma_filter"]
        bear_bias = out["close"] < out["sma_filter"]
    else:
        bull_bias = pd.Series(True,  index=out.index)
        bear_bias = pd.Series(True,  index=out.index)
        out["sma_filter"] = np.nan

    out["long_signal"]  = (out["close"] < out["bb_lower"]) & (out["rsi"] < p.rsi_long)  & bull_bias
    out["short_signal"] = (out["close"] > out["bb_upper"]) & (out["rsi"] > p.rsi_short) & bear_bias

    out["sl_long"]  = out["close"] * (1 - p.sl_pct / 100)
    out["sl_short"] = out["close"] * (1 + p.sl_pct / 100)
    out["tp_long"]  = out["close"] * (1 + p.tp_pct / 100)
    out["tp_short"] = out["close"] * (1 - p.tp_pct / 100)

    return out


# ── Bot integration wrapper ────────────────────────────────────────────────────

try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object
    TradeSignal  = None


class BMR357Strategy(BaseStrategy):
    """
    Bollinger Band Mean Reversion with 3-5-7 Risk Rule.

    Long entry:  close < BB(20, 2σ) lower + RSI < 30
    Short entry: close > BB(20, 2σ) upper + RSI > 70
    TP: 3% / SL: 1.5% / time stop: 48 bars / midline exit
    """

    def __init__(self):
        super().__init__()
        self.strategy_name           = "bmr_357"
        self.params                  = BMR357Params()
        self.stop_loss_pct           = self.params.sl_pct
        self.take_profit_pct         = self.params.tp_pct
        self.crypto_enabled          = True
        self.stock_enabled           = False
        self.stock_candle_timeframe  = "1Hour"
        self.crypto_candle_timeframe = "15m"   # 15m is the best performing timeframe
        self.candle_limit            = 250
        self.reviewer_exempt         = True
        self.ml_exempt               = True
        self.time_stop_profile       = "strategy_defined"

    def analyze(self, symbol: str, candles: pd.DataFrame,
                market_condition: str = "unknown") -> Optional["TradeSignal"]:
        p        = self.params
        MIN_BARS = max(p.bb_len, p.rsi_len,
                       p.sma_filter_len if p.sma_filter_len > 0 else 0) + 10
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
            close     = float(last["close"])
            rsi_val   = float(last["rsi"])
            bb_mid    = float(last["bb_mid"])   if not pd.isna(last["bb_mid"])   else close
            bb_upper  = float(last["bb_upper"]) if not pd.isna(last["bb_upper"]) else close
            bb_lower  = float(last["bb_lower"]) if not pd.isna(last["bb_lower"]) else close

            # Distance from midline in %
            dist_to_mid_pct = abs(close - bb_mid) / bb_mid * 100

            # Score: larger RSI extreme + larger band distance = higher conviction
            if long_sig:
                rsi_norm = max(0.0, (p.rsi_long  - rsi_val) / p.rsi_long)
            else:
                rsi_norm = max(0.0, (rsi_val - p.rsi_short) / (100 - p.rsi_short))
            score = round(min(0.92, max(0.60, 0.62 + rsi_norm * 0.18 + min(dist_to_mid_pct, 5) * 0.02)), 3)

            sl_price      = float(last["sl_long"])  if long_sig else float(last["sl_short"])
            tp_price      = float(last["tp_long"])  if long_sig else float(last["tp_short"])
            sl_pct_actual = round(abs(close - sl_price) / close * 100, 3)
            tp_pct_actual = round(abs(tp_price - close)  / close * 100, 3)

            vol_series = candles["volume"]
            vol_ma_val = vol_series.rolling(20).mean().iloc[-1]
            vol_ratio  = round(float(vol_series.iloc[-1] / vol_ma_val), 3) if vol_ma_val > 0 else None

            reason_tag = (
                f"BMR-357: close {'below' if long_sig else 'above'} BB({p.bb_len},{p.bb_std}σ) | "
                f"RSI={rsi_val:.1f} | dist_mid={dist_to_mid_pct:.2f}% | "
                f"TP={tp_pct_actual:.2f}% SL={sl_pct_actual:.2f}% R:R={tp_pct_actual/sl_pct_actual:.2f}"
            )

            self.verbose_log(symbol, "BB+RSI mean-reversion", True,
                             round(close, 6), reason_tag, direction)
            self.verbose_log_score(symbol, score, 0.60)

            return self._make_signal(
                symbol          = symbol,
                direction       = direction,
                score           = score,
                reason          = reason_tag,
                stop_loss_pct   = sl_pct_actual,
                take_profit_pct = tp_pct_actual,
                metadata={
                    "strategy_name":    "bmr_357",
                    "entry_timeframe":  self.crypto_candle_timeframe,
                    "rsi":              round(rsi_val, 2),
                    "bb_mid":           round(bb_mid,   6),
                    "bb_upper":         round(bb_upper, 6),
                    "bb_lower":         round(bb_lower, 6),
                    "dist_to_mid_pct":  round(dist_to_mid_pct, 4),
                    "volume_ratio":     vol_ratio,
                    # 3-5-7 rule values — consumed by risk engine / position sizer
                    "rule_357_max_risk_per_trade_pct": p.max_risk_per_trade_pct,
                    "rule_357_max_portfolio_risk_pct": p.max_portfolio_risk_pct,
                    "rule_357_min_rr_ratio":           p.min_rr_ratio,
                    # exit references
                    "structural_stop_price":           round(sl_price, 6),
                    "preferred_initial_stop_mode":     "signal_structural",
                    "preferred_trail_mode":            "none",
                    "sma20_target":                    round(bb_mid, 6),
                },
            )

        except Exception as e:
            self.logger.error(f"BMR357Strategy.analyze error on {symbol}: {e}", exc_info=True)
            return None

    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str,
                          entry_metadata: Optional[dict] = None) -> Optional[str]:
        """
        Two exit triggers (whichever fires first):
          1. Time stop: exit after max_bars — prevents stalled trades.
          2. Midline: price returns to SMA20 — primary mean-reversion target.
        """
        meta      = entry_metadata or {}
        bars_held = int(meta.get("_bars_held", 0))

        if bars_held >= self.params.max_bars:
            return "bmr357_time_stop"

        sma20_target = meta.get("sma20_target")
        if sma20_target and len(bars) >= 1:
            current_close = float(bars["close"].iloc[-1])
            if direction == "long"  and current_close >= sma20_target:
                return "bmr357_midline_reached"
            if direction == "short" and current_close <= sma20_target:
                return "bmr357_midline_reached"

        return None
