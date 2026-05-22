"""
Short-Timeframe Mean Reversion Audit -- FELS & CBAE
====================================================
Tests FELS and CBAE at 5m and 15m with parameters tuned for intraday.

Why these two strategies:
  FELS  -- liquidity sweeps / stop-hunts are a 5-15m phenomenon
  CBAE  -- body asymmetry exhaustion accumulates faster on short bars

1h audit result (yfinance):
  FELS: 54-91 trades per symbol, PF 0.04-0.34 -- over-fires at 1h (too loose)
  CBAE: 0 trades -- macro trend filter is contradictory; thresholds too high

Hypothesis for short TF:
  FELS: tighten close-threshold + volume filter -> fewer, cleaner sweeps
  CBAE: remove contradictory macro filter, lower accumulation threshold

Run: venv312\Scripts\python.exe Scripts\audit_short_tf_v1.py
"""
import os, sys, logging
logging.basicConfig(level=logging.WARNING)
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

import numpy as np
import pandas as pd
from intelligence.backtester import Backtester, STOP_STANDARD
from strategies.fels_strategy import FELSStrategy, FELSParams
from strategies.cbae_strategy import CBAEStrategy, CBAEParams

# -- Config -----------------------------------------------------------------
CAPITAL    = 10_000.0
COMMISSION = 0.26
SLIPPAGE   = 0.05
DAYS_5M    = 30       # yfinance 5m: up to 58 days
DAYS_15M   = 30       # yfinance 15m: up to 59 days

SYMBOLS = ["BTC-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "BNB-USD"]

bt = Backtester(starting_capital=CAPITAL)


# ---------------------------------------------------------------------------
# FELS short-TF variant factory
# Key changes from 1h baseline:
#   atr_close_thresh: 0.8 -> 0.45  (must clearly reject back inside)
#   vol_spike_min:    1.2 -> 1.6   (need real volume to confirm trap)
#   lookback:         20  -> 12    (shorter lookback, more relevant sweeps)
#   adx_max:          28  -> 25    (only fade in more ranging conditions)
#   max_bars_hold:    16  -> 8     (get out faster on short TF)
# ---------------------------------------------------------------------------
def make_fels_short(
    lookback=12,
    atr_close=0.45,
    vol_spike=1.6,
    adx_max=25,
    max_hold=8,
):
    s = FELSStrategy()
    s.params = FELSParams(
        lookback         = lookback,
        atr_close_thresh = atr_close,
        atr_length       = 14,
        sl_atr_buffer    = 0.3,
        tp_revert_pct    = 0.5,
        adx_period       = 14,
        adx_max          = adx_max,
        vol_spike_min    = vol_spike,
        max_bars_hold    = max_hold,
    )
    return s


# ---------------------------------------------------------------------------
# CBAE short-TF variant factory
# Key changes from 1h baseline:
#   body_window:      14  -> 8     (accumulates faster on short bars)
#   extreme_thresh:   5.0 -> 3.0   (easier to reach on short TF noise)
#   shrink_factor:    0.6 -> 0.55  (slightly looser absorption)
#   trend_ma_length:  100 -> 30    (faster macro trend)
#   adx_max:          30  -> 25    (consistent regime filter)
#   max_bars_hold:    20  -> 10    (short TF exits quicker)
#   NOTE: direction logic patched below (remove contradictory macro filter)
# ---------------------------------------------------------------------------
class CBAEShortTF(CBAEStrategy):
    """CBAE with short-TF parameters and no macro-trend direction filter."""

    def __init__(
        self,
        body_window=8,
        extreme_thresh=3.0,
        shrink_factor=0.55,
        adx_max=25,
        max_hold=10,
        trend_ma=30,
    ):
        super().__init__()
        self.params = CBAEParams(
            body_window     = body_window,
            extreme_thresh  = extreme_thresh,
            shrink_factor   = shrink_factor,
            atr_length      = 14,
            sl_atr_mult     = 1.5,
            tp_atr_mult     = 2.0,
            adx_period      = 14,
            adx_max         = adx_max,
            trend_ma_length = trend_ma,
            max_bars_hold   = max_hold,
        )
        self.candle_limit = max(trend_ma, body_window, 14) + 30

    def analyze(self, symbol, candles, market_condition="unknown"):
        """
        Override: drop the contradictory macro-trend direction filter.
        Original logic blocked LONG when price below 100-bar MA (i.e., exactly
        when a bearish extreme body-sum is most likely to occur -- useless filter).
        Here we simply fade the extreme direction regardless of macro trend.
        ADX regime filter still applies.
        """
        p = self.params
        MIN_BARS = max(p.trend_ma_length, p.body_window * 2, p.atr_length) + 10
        if not self._check_enough_candles(symbol, candles, MIN_BARS):
            return None

        try:
            df   = candles.copy()
            c    = df["close"]

            # Body ratio
            body       = (df["close"] - df["open"]).abs()
            rng        = (df["high"] - df["low"]).clip(lower=0.0001)
            body_ratio = body / rng
            sign        = np.where(df["close"] >= df["open"], 1.0, -1.0)
            signed_body = pd.Series(sign * body_ratio.values, index=df.index)

            body_sum       = signed_body.rolling(p.body_window).sum()
            body_ma        = body_ratio.rolling(p.body_window).mean()
            body_last3_avg = body_ratio.rolling(3).mean()
            absorbing      = body_last3_avg < body_ma * p.shrink_factor

            # ATR
            hl  = df["high"] - df["low"]
            hpc = (df["high"] - c.shift()).abs()
            lpc = (df["low"]  - c.shift()).abs()
            tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
            atr = tr.ewm(span=p.atr_length, adjust=False).mean()

            # ADX (reuse parent helper)
            from strategies.cbae_strategy import _compute_adx
            adx = _compute_adx(df, p.adx_period)

            last  = df.index[-1]
            bs    = float(body_sum.loc[last])
            adx_  = float(adx.loc[last])
            abs_  = bool(absorbing.loc[last])
            atr_  = float(atr.loc[last])
            cls   = float(c.loc[last])

            if adx_ > p.adx_max:
                return None
            if not abs_:
                return None
            if abs(bs) < p.extreme_thresh:
                return None

            # Fade the commitment direction -- NO macro trend gating
            direction = "short" if bs >= p.extreme_thresh else "long"

            sl_pct = round(atr_ * p.sl_atr_mult / cls * 100, 3)
            tp_pct = round(atr_ * p.tp_atr_mult / cls * 100, 3)

            structural_stop = (
                cls - atr_ * p.sl_atr_mult if direction == "long"
                else cls + atr_ * p.sl_atr_mult
            )

            exhaustion_depth = min(1.0, (abs(bs) - p.extreme_thresh) / p.body_window)
            score = round(max(0.50, min(0.88,
                0.55 + 0.25 * exhaustion_depth + 0.10 * (1.0 - adx_ / p.adx_max)
            )), 3)

            return self._make_signal(
                symbol          = symbol,
                direction       = direction,
                score           = score,
                reason          = (
                    "CBAE-STF: body_sum=%.2f (thresh+/-%.1f) "
                    "absorbing=True adx=%.1f" % (bs, p.extreme_thresh, adx_)
                ),
                stop_loss_pct   = sl_pct,
                take_profit_pct = tp_pct,
                metadata={
                    "strategy_name":        "cbae_strategy",
                    "entry_timeframe":       self.crypto_candle_timeframe,
                    "_entry_bar_time":       str(candles.index[-1]),
                    "body_sum":              round(bs, 4),
                    "adx":                   round(adx_, 2),
                    "atr":                   round(atr_, 6),
                    "structural_stop_price": round(structural_stop, 6),
                    "preferred_trail_mode":  "none",
                },
            )

        except Exception as e:
            self.logger.error("CBAEShortTF.analyze error on %s: %s" % (symbol, e), exc_info=True)
            return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run(label, strat, sym, tf, days):
    df = bt.fetch_history_crypto(sym, days, tf)
    if df is None or len(df) < 50:
        n = len(df) if df is not None else 0
        print("  %-44s [%-10s]: not enough data (%d bars)" % (label, sym, n))
        return None
    r = bt._simulate(sym, df, strat.strategy_name, strat, CAPITAL, tf,
                     stop_mode=STOP_STANDARD, asset_class="crypto",
                     commission_pct=COMMISSION, slippage_pct=SLIPPAGE)
    if r is None:
        print("  %-44s [%-10s]: no result" % (label, sym))
        return None
    net = r.ending_capital - r.starting_capital
    pf  = "%.3f" % r.profit_factor if r.profit_factor != float("inf") else "  inf"
    print("  %-44s [%-10s]  trades=%3d  WR=%5.1f%%  PF=%7s  P&L=$%8.2f  DD=%5.2f%%" % (
        label, sym, r.total_trades, r.win_rate, pf, net, r.max_drawdown_pct))
    return r


# ---------------------------------------------------------------------------
# Configurations to sweep
# ---------------------------------------------------------------------------
FELS_CONFIGS = [
    # label,                       lookback, atr_close, vol_spike, adx_max, max_hold
    ("FELS-STF tight",             12,       0.45,      1.6,       25,      8),
    ("FELS-STF medium",            15,       0.55,      1.4,       28,      10),
    ("FELS-STF loose",             20,       0.65,      1.3,       30,      12),
    ("FELS-STF vol-heavy",         12,       0.40,      2.0,       25,      8),
]

CBAE_CONFIGS = [
    # label,                       bw, thresh, shrink, adx, hold, trend_ma
    ("CBAE-STF w8/t3.0",           8,  3.0,    0.55,   25,  10,   30),
    ("CBAE-STF w8/t2.5",           8,  2.5,    0.55,   25,  10,   30),
    ("CBAE-STF w10/t3.5",          10, 3.5,    0.55,   25,  12,   40),
    ("CBAE-STF w6/t2.0 fast",      6,  2.0,    0.50,   25,  8,    20),
]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print()
print("=" * 100)
print("Short-TF Mean Reversion Audit -- FELS & CBAE")
print("5m (%dd) and 15m (%dd)  |  Commission %.2f%%  |  Slippage %.2f%%" % (
    DAYS_5M, DAYS_15M, COMMISSION, SLIPPAGE))
print("Hypothesis: sweeps and body exhaustion have better edge on intraday timeframes")
print("=" * 100)

for TF, DAYS in [("5m", DAYS_5M), ("15m", DAYS_15M)]:
    print("\n" + "-"*100)
    print("  TIMEFRAME: %s   (%d days)" % (TF, DAYS))
    print("-"*100)

    # -- FELS -----------------------------------------------------------------
    print("\n  -- FELS (Failed Extension Liquidity Sweep) --")
    for (lbl, lb, ac, vs, am, mh) in FELS_CONFIGS:
        tag = "%s [%s]" % (lbl, TF)
        for sym in SYMBOLS:
            s = make_fels_short(lb, ac, vs, am, mh)
            s.crypto_candle_timeframe = TF
            run(tag, s, sym, TF, DAYS)

    # -- CBAE -----------------------------------------------------------------
    print("\n  -- CBAE (Candle Body Asymmetry Exhaustion) --")
    for (lbl, bw, th, sh, am, mh, tm) in CBAE_CONFIGS:
        tag = "%s [%s]" % (lbl, TF)
        for sym in SYMBOLS:
            s = CBAEShortTF(bw, th, sh, am, mh, tm)
            s.crypto_candle_timeframe = TF
            run(tag, s, sym, TF, DAYS)

print()
print("=" * 100)
print("SUMMARY NOTES:")
print("  Target: 15+ trades/symbol, WR > 50%, PF > 1.3")
print("  A config with PF > 1.2 on 3+ symbols is worth a full 60d sweep")
print("  FELS: look for vol-heavy + tight close-threshold combo")
print("  CBAE: if any config gets 10+ trades, the hypothesis is alive")
print("=" * 100)
