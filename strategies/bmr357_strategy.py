"""
BMR-357  —  Bollinger Band Mean Reversion  /  3-5-7 Risk Rule
==============================================================
CLASSIFICATION : INCUBATE  (2026-06-07)
  Paper-trade only until 50+ aggregate live trades are logged.
  Do NOT promote to CANDIDATE without a second matrix run after 90 live days.

STRATEGY BRIEF
--------------
Crypto pairs oscillate around a moving average.  When price closes outside
a Bollinger Band (20-period, 2.25 std dev) AND RSI confirms deep exhaustion
(< 28), fade the move back to the SMA20 midline.

  Entry  — Long:  close < BB(20, 2.25 std) lower  AND  RSI(14) < 28
  Entry  — Short: close > BB(20, 2.25 std) upper  AND  RSI(14) > 72
  TP:    3.5 % from entry  (or price returns to SMA20, whichever comes first)
  SL:    1.5 % from entry  (fixed)
  R:R:   2.33:1

3-5-7 RISK RULE (enforced via metadata / position sizer)
  3 %  — maximum portfolio risk on any single trade
  5 %  — maximum total portfolio risk across all open positions
  7 %  — minimum reward-to-risk threshold (TP/SL = 2.33 satisfies this)

PROFIT FACTOR MATH (at optimised 2.33:1 R:R)
  WR 33%  ->  PF = 1.00  (breakeven)
  WR 50%  ->  PF = 2.33
  WR 67%  ->  PF = 4.75  (observed on best pairs)

PARAM OPTIMISATION SWEEP (2026-06-07)
  Tested: bb_std 1.75-2.5, rsi_long 24-36, sl 1.0-2.5%, tp 2.0-4.5%
  Winner: bb_std=2.25, rsi_long=28, sl=1.5%, tp=3.5%
  Strict 2.25 std + RSI 28 -> 50% edge-cell rate vs 24% at default 2.0/30

BACKTEST RESULTS  —  40-symbol crypto, 15m, 180d, long-only
  Overall avg PF : 1.509   |   Edge cells (PF>=1.2) : 15/33 = 45.5%
  YFI/USD   PF=4.30  WR=75%  4t  |  AVAX/USD  PF=2.95  WR=67%  3t
  CAKE/USD  PF=2.92  WR=67%  3t  |  VET/USD   PF=2.71  WR=67%  3t
  DOT/USD   PF=2.64  WR=67%  3t  |  SNX/USD   PF=2.32  WR=50%  4t
  BNB/USD   PF=2.06  WR=67%  3t  |  LINK/USD  PF=1.40  WR=50%  2t
  XRP/USD   PF=1.36  WR=50%  2t  |  ARB/USD   PF=1.36  WR=50%  2t

BACKTEST RESULTS  —  5m crypto, 18 pairs, 90d
  Overall avg PF : 1.280   |   Edge cells : 5/17 = 29.4%
  5m is weaker — fee hurdle bites at smaller ATR%; 15m is the primary TF.

BACKTEST RESULTS  —  Stocks 15m, 14 symbols, 180d, long+short
  Overall avg PF : 1.281   |   Edge cells : 10/26 = 38.5%
  AMD long PF=2.16 | QQQ long PF=1.58 | NVDA long PF=1.25
  BNB/USD short PF=2.04 — only confirmed short across all tests
  Stocks are secondary; short side unproven except BNB/USD

RECOMMENDATIONS
  Primary universe : 15m crypto longs across 30-40 pairs
  Best pairs       : DOT, BNB, AVAX, VET, YFI, CAKE, SNX, LINK, XRP, ARB
  Stocks           : Enabled (secondary) — AMD/QQQ/NVDA longs show edge
  Short side       : Enabled but unproven — BNB/USD is only confirmed signal
  Signal frequency : 2-8 trades per pair per 6 months; needs wide watchlist
  Upgrade path     : Re-run matrix at 90 live days; target PF>=1.3 on 50+ trades

TIMEFRAME : 15m crypto (primary) | stock candle TF set to 15Min for parity
STATUS    : INCUBATE — paper trade only | ml_exempt=True (no training history)
"""

import logging
import time
from collections import defaultdict
import numpy as np
import pandas as pd
import config
from strategies.base_strategy import BaseStrategy, TradeSignal
from dataclasses import dataclass
from typing import Optional

_log = logging.getLogger(__name__)


# ── Parameters ────────────────────────────────────────────────────────────────

@dataclass
class BMR357Params:
    # Bollinger Bands
    # Sweep winner (2026-06-07): 2.25σ selects more extreme breakouts → stronger reversion
    bb_len:         int   = 20
    bb_std:         float = 2.25

    # RSI confirmation
    # Sweep winner: RSI 28/72 selects deeper exhaustion — edge rate 50% vs 24% at 30/70
    rsi_len:        int   = 14
    rsi_long:       float = 35.0   # long entry: RSI must be BELOW this # was 28
    rsi_short:      float = 65.0   # short entry: RSI must be ABOVE this # was 72

    # Risk / reward (3-5-7 rule core)
    # Sweep winner: TP 3.5% gives R:R 2.33:1 — beats 2:1 default, satisfies "7" rule
    sl_pct:         float = 1.5    # stop loss %  (the "3" leg: 3% max risk → pos size)
    tp_pct:         float = 3.5    # take profit % (R:R 2.33:1 — optimized from 3.0%)

    # Trend filter (0 = disabled — SMA200 blocks mean-reversion entries by design,
    # since oversold longs are typically below SMA200 and overbought shorts above it)
    sma_filter_len: int   = 0

    # Time stop
    max_bars:       int   = 48     # exit after N bars regardless

    # Live fee/edge guard. BMR exits at the SMA20 midline, so tiny targets
    # can be directionally correct but still lose after crypto round-trip costs.
    min_dist_to_mid_pct: float = 1.0  # Was 1.5

    # Regime guard. BMR's observed edge is strongest when the whole crypto tape
    # is moving, using BTC as the broad-market proxy.
    require_btc_momentum: bool = True
    min_btc_move_pct:     float = 1.0

    # 3-5-7 portfolio limits (stored in metadata, enforced by risk engine)
    max_risk_per_trade_pct:  float = 3.0   # 3 %
    max_portfolio_risk_pct:  float = 5.0   # 5 %
    min_rr_ratio:            float = 2.33  # 7 rule: TP/SL = 3.5/1.5 = 2.33


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
    Returns DataFrame with signal columns added.  No lookahead — all signals
    are confirmed on the closed bar.

    Long:  close < bb_lower  AND  rsi < rsi_long  AND  close > sma200
    Short: close > bb_upper  AND  rsi > rsi_short  AND  close < sma200
    """
    p   = params
    out = df.copy()

    # Guard against multi-level / duplicate columns (yfinance artifact)
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[0]).lower() if isinstance(c, tuple) else str(c).lower()
                       for c in out.columns]
    if out.columns.duplicated().any():
        out = out.loc[:, ~out.columns.duplicated(keep="first")]

    # Core indicators
    bb_mid, bb_upper, bb_lower = _bollinger(out["close"], p.bb_len, p.bb_std)
    rsi_series                  = _rsi(out["close"], p.rsi_len)

    out["bb_mid"]   = bb_mid
    out["bb_upper"] = bb_upper
    out["bb_lower"] = bb_lower
    out["rsi"]      = rsi_series

    # Trend filter
    if p.sma_filter_len > 0:
        out["sma_filter"] = _sma(out["close"], p.sma_filter_len)
        bull_bias = out["close"] > out["sma_filter"]
        bear_bias = out["close"] < out["sma_filter"]
    else:
        bull_bias = pd.Series(True,  index=out.index)
        bear_bias = pd.Series(True,  index=out.index)
        out["sma_filter"] = np.nan

    # Entry conditions
    price_below_lower = out["close"] < out["bb_lower"]
    price_above_upper = out["close"] > out["bb_upper"]
    rsi_oversold      = out["rsi"]   < p.rsi_long
    rsi_overbought    = out["rsi"]   > p.rsi_short

    out["long_signal"]  = price_below_lower & rsi_oversold  & bull_bias
    out["short_signal"] = price_above_upper & rsi_overbought & bear_bias

    # Pre-compute SL / TP prices for the signal bar
    out["sl_long"]  = out["close"] * (1 - p.sl_pct / 100)
    out["sl_short"] = out["close"] * (1 + p.sl_pct / 100)
    out["tp_long"]  = out["close"] * (1 + p.tp_pct / 100)
    out["tp_short"] = out["close"] * (1 - p.tp_pct / 100)

    return out


# ── Bot integration wrapper ────────────────────────────────────────────────────

class BMR357Strategy(BaseStrategy):
    """
    Bollinger Band Mean Reversion with 3-5-7 Risk Rule.

    Entry: close outside BB(20, 2σ) + RSI confirmation.
    Exit:  TP 3 % / SL 1.5 % / time stop 48 bars / SMA20 midline reached.
    """

    def __init__(self):
        super().__init__()
        self.strategy_name           = "bmr_357"
        self.params                  = BMR357Params()
        self.stop_loss_pct           = self.params.sl_pct
        self.take_profit_pct         = self.params.tp_pct
        self.crypto_enabled          = True
        self.stock_enabled           = False  # crypto-only until stock edge is re-audited
        self.stock_candle_timeframe  = "15Min"  # matches crypto 15m TF per backtest findings
        self.crypto_candle_timeframe = "15m"   # primary TF per backtest (best PF/edge rate)
        self.candle_limit            = 250
        self.reviewer_exempt         = True
        self.ml_exempt               = True
        self.time_stop_profile       = "strategy_defined"
        self._health_interval_sec    = max(
            30.0,
            float(getattr(config, "BMR357_HEALTH_LOG_INTERVAL_SEC", 300.0)),
        )
        self._health_window_started  = time.monotonic()
        self._health_scans           = 0
        self._health_counts          = defaultdict(int)
        self._health_examples        = {}

    def _record_health(self, symbol: str, outcome: str, detail: str = "",
                       extra_counts: Optional[list[str]] = None,
                       force: bool = False) -> None:
        """Aggregate BMR gate outcomes so INFO logs stay useful without spam."""
        self._health_scans += 1
        self._health_counts[outcome] += 1
        for extra in extra_counts or []:
            self._health_counts[extra] += 1

        if detail:
            self._health_examples[outcome] = f"{symbol} {detail}"

        now = time.monotonic()
        if force or (now - self._health_window_started) >= self._health_interval_sec:
            self._flush_health(now)

    def _flush_health(self, now: Optional[float] = None) -> None:
        if self._health_scans <= 0:
            return

        now = time.monotonic() if now is None else now
        elapsed = max(1.0, now - self._health_window_started)
        ordered_keys = [
            "no_bars",
            "insufficient_bars",
            "setup_fail",
            "bb_fail",
            "rsi_fail",
            "distance_fail",
            "btc_momentum_unavailable",
            "btc_momentum_fail",
            "signal_generated",
            "error",
        ]
        counts = " ".join(
            f"{key}={self._health_counts[key]}"
            for key in ordered_keys
            if self._health_counts.get(key, 0) > 0
        )
        examples = "; ".join(
            f"{key}: {value}"
            for key, value in self._health_examples.items()
        )
        example_suffix = f" | examples={examples}" if examples else ""

        self.logger.info(
            f"[BMR357][health] window={elapsed:.0f}s scans={self._health_scans} "
            f"{counts}{example_suffix}"
        )

        self._health_window_started = now
        self._health_scans = 0
        self._health_counts.clear()
        self._health_examples.clear()

    def _btc_momentum_active(self, symbol: str, candles: pd.DataFrame) -> tuple[bool, Optional[float]]:
        p = self.params
        min_move = float(getattr(config, "BMR_BTC_MOMENTUM_THRESHOLD", p.min_btc_move_pct))

        try:
            btc_df = candles if symbol.upper() == "BTC/USD" else None
            if btc_df is None:
                from core.candle_manager import candle_manager
                btc_df = candle_manager.get("BTC/USD", self.crypto_candle_timeframe, limit=3)
            if btc_df is None or len(btc_df) < 2:
                return False, None

            close = btc_df["close"]
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            if prev <= 0:
                return False, None

            move_pct = abs((last - prev) / prev * 100)
            return move_pct >= min_move, move_pct
        except Exception as e:
            self.logger.debug(f"BMR BTC momentum check failed for {symbol}: {e}")
            return False, None

    def analyze(self, symbol: str, candles: pd.DataFrame,
                market_condition: str = "unknown") -> Optional[TradeSignal]:
        p       = self.params
        MIN_BARS = max(p.bb_len, p.rsi_len, p.sma_filter_len) + 10
        candle_count = 0 if candles is None else len(candles)
        if candle_count <= 0:
            self._record_health(symbol, "no_bars", f"required={MIN_BARS}")
            return None
        if not self._check_enough_candles(symbol, candles, MIN_BARS):
            self._record_health(
                symbol,
                "insufficient_bars",
                f"bars={candle_count} required={MIN_BARS}",
            )
            return None

        try:
            sig  = generate_signals(candles, p)
            last = sig.iloc[-1]

            long_sig  = bool(last["long_signal"])

            if not long_sig:
                close = float(last["close"])
                rsi_val = float(last["rsi"]) if not pd.isna(last["rsi"]) else None
                bb_lower = float(last["bb_lower"]) if not pd.isna(last["bb_lower"]) else None
                bb_pass = bb_lower is not None and close < bb_lower
                rsi_pass = rsi_val is not None and rsi_val < p.rsi_long
                failed_parts = []
                if not bb_pass:
                    failed_parts.append("bb_fail")
                if not rsi_pass:
                    failed_parts.append("rsi_fail")
                rsi_detail = "nan" if rsi_val is None else f"{rsi_val:.1f}"
                bb_detail = "nan" if bb_lower is None else f"{bb_lower:.6f}"
                self._record_health(
                    symbol,
                    "setup_fail",
                    f"close={close:.6f} bb_lower={bb_detail} rsi={rsi_detail}",
                    extra_counts=failed_parts,
                )
                return None

            direction = "long"
            close     = float(last["close"])
            rsi_val   = float(last["rsi"])
            bb_mid    = float(last["bb_mid"])   if not pd.isna(last["bb_mid"])   else close
            bb_upper  = float(last["bb_upper"]) if not pd.isna(last["bb_upper"]) else close
            bb_lower  = float(last["bb_lower"]) if not pd.isna(last["bb_lower"]) else close
            sma_filter_value = float(last["sma_filter"]) if not pd.isna(last["sma_filter"]) else None

            # Distance from midline — larger distance = stronger reversion potential
            dist_to_mid_pct = abs(close - bb_mid) / bb_mid * 100
            min_target_pct = max(
                p.min_dist_to_mid_pct,
                float(getattr(config, "MIN_NET_PROFIT_CRYPTO_PCT", 1.02)),
            )
            if dist_to_mid_pct < min_target_pct:
                self._record_health(
                    symbol,
                    "distance_fail",
                    f"dist_to_mid={dist_to_mid_pct:.2f}% min={min_target_pct:.2f}%",
                )
                self.verbose_log(
                    symbol,
                    "BMR target too small after fees",
                    False,
                    round(close, 6),
                    f"dist_to_mid={dist_to_mid_pct:.2f}% < min_target={min_target_pct:.2f}%",
                    "long",
                )
                return None

            btc_active = True
            btc_move_pct = None
            if p.require_btc_momentum:
                btc_active, btc_move_pct = self._btc_momentum_active(symbol, candles)
                min_btc_move = float(getattr(config, "BMR_BTC_MOMENTUM_THRESHOLD", p.min_btc_move_pct))
                if not btc_active:
                    detail = (
                        "BTC move unavailable"
                        if btc_move_pct is None
                        else f"BTC 15m move {btc_move_pct:.2f}% < {min_btc_move:.2f}%"
                    )
                    self._record_health(
                        symbol,
                        "btc_momentum_unavailable" if btc_move_pct is None else "btc_momentum_fail",
                        detail,
                    )
                    self.verbose_log(
                        symbol,
                        "BMR BTC momentum regime inactive",
                        False,
                        round(close, 6),
                        detail,
                        "long",
                    )
                    return None

            # Score: further from midline + stronger RSI = higher conviction
            if long_sig:
                rsi_norm = max(0.0, (p.rsi_long - rsi_val) / p.rsi_long)
            else:
                rsi_norm = max(0.0, (rsi_val - p.rsi_short) / (100 - p.rsi_short))

            score = round(min(0.92, max(0.60, 0.62 + rsi_norm * 0.18 + min(dist_to_mid_pct, 5) * 0.02)), 3)

            # 3-5-7 rule values baked into metadata for position sizer
            sl_price = float(last["sl_long"])  if long_sig else float(last["sl_short"])
            tp_price = float(last["tp_long"])  if long_sig else float(last["tp_short"])

            sl_pct_actual = round(abs(close - sl_price) / close * 100, 3)
            tp_pct_actual = round(abs(tp_price - close)  / close * 100, 3)

            # Volume ratio
            vol_series = candles["volume"]
            vol_ma_val = vol_series.rolling(20).mean().iloc[-1]
            vol_ratio  = round(float(vol_series.iloc[-1] / vol_ma_val), 3) if vol_ma_val > 0 else None

            reason_tag = (
                f"BMR-357: close {'below' if long_sig else 'above'} BB({p.bb_len},{p.bb_std}σ) | "
                f"RSI={rsi_val:.1f} ({'oversold' if long_sig else 'overbought'}) | "
                f"dist_to_mid={dist_to_mid_pct:.2f}% | "
                f"TP={tp_pct_actual:.2f}% SL={sl_pct_actual:.2f}% R:R={tp_pct_actual/sl_pct_actual:.2f}"
            )

            self.verbose_log(symbol, "BB+RSI mean-reversion", True,
                             round(close, 6), reason_tag, direction)
            self.verbose_log_score(symbol, score, 0.60)
            self._record_health(
                symbol,
                "signal_generated",
                f"score={score:.3f} close={close:.6f} dist_to_mid={dist_to_mid_pct:.2f}%",
                force=True,
            )

            return self._make_signal(
                symbol          = symbol,
                direction       = direction,
                score           = score,
                reason          = reason_tag,
                stop_loss_pct   = sl_pct_actual,
                take_profit_pct = tp_pct_actual,
                metadata={
                    "strategy_name":   "bmr_357",
                    "entry_timeframe": self.crypto_candle_timeframe,
                    # indicator values
                    "rsi":             round(rsi_val, 2),
                    "bb_mid":          round(bb_mid,   6),
                    "bb_upper":        round(bb_upper, 6),
                    "bb_lower":        round(bb_lower, 6),
                    "sma_filter":      round(sma_filter_value, 6) if sma_filter_value is not None else None,
                    "dist_to_mid_pct": round(dist_to_mid_pct, 4),
                    "btc_15m_move_pct": round(btc_move_pct, 4) if btc_move_pct is not None else None,
                    "btc_momentum_active": btc_active,
                    "volume_ratio":    vol_ratio,
                    # 3-5-7 rule parameters (consumed by risk engine / position sizer)
                    "rule_357_max_risk_per_trade_pct":  p.max_risk_per_trade_pct,
                    "rule_357_max_portfolio_risk_pct":  p.max_portfolio_risk_pct,
                    "rule_357_min_rr_ratio":            p.min_rr_ratio,
                    # stops
                    "structural_stop_price":            round(sl_price, 6),
                    "preferred_initial_stop_mode":      "signal_structural",
                    "preferred_trail_mode":             "none",
                    # midline target (secondary exit reference)
                    "sma20_target":                     round(bb_mid, 6),
                },
            )

        except Exception as e:
            self._record_health(symbol, "error", str(e), force=True)
            self.logger.error(f"BMR357Strategy.analyze error on {symbol}: {e}", exc_info=True)
            return None

    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str,
                          entry_metadata: Optional[dict] = None) -> Optional[str]:
        """
        Two exit triggers (whichever fires first):
          1. Price returns to SMA20 midline (primary mean-reversion target).
          2. Time stop after max_bars (prevents stalled trades from bleeding).
        TP/SL wires in the bot engine handle the fixed % exits.
        """
        meta      = entry_metadata or {}
        bars_held = int(meta.get("_bars_held", 0))
        p         = self.params

        # Time stop
        if bars_held >= p.max_bars:
            return "bmr357_time_stop"

        # Midline exit
        sma20_target = meta.get("sma20_target")
        if sma20_target and len(bars) >= 1:
            current_close = float(bars["close"].iloc[-1])
            if direction == "long"  and current_close >= sma20_target:
                return "bmr357_midline_reached"
            if direction == "short" and current_close <= sma20_target:
                return "bmr357_midline_reached"

        return None
