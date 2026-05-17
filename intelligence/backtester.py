"""
=============================================================
  BACKTESTING ENGINE  v2.1
  Tests strategies against historical data BEFORE risking
  real money.  Uses yfinance for free OHLCV history.

  Timeframe support:
    5m   — up to 30 days   (best for Scalp Master, RSI)
    1h   — up to 730 days  (best for Swing, EMA, Bollinger)
    1d   — up to 3650 days (long-term trend view)

  Stop loss modes:
    standard    — fixed % stop from config (default)
    two_bar     — N-bar trailing stop (Pine Script port)
                  Initial stop = lowest low of prior N bars
                  Trail: advances on each new N-bar high
                  Ratchets up only, never down
                  Default N=2, configurable in dashboard

  Strategy-specific exits:
    Strategies that override BaseStrategy.check_custom_exit() get their
    exit logic called on every bar (after SL/TP), matching live behaviour.
    adaptive_regime uses this for EMA cross (trend) and BB midline/RSI
    (mean rev) exits. All other strategies use standard SL/TP only.

  Run from command line (from trading_bot_v2 root):
    python intelligence/backtester.py --symbol AAPL --days 180 --tf 1h
    python intelligence/backtester.py --symbol AAPL --days 60  --tf 5m
    python intelligence/backtester.py --all    --days 365 --tf 1h
    python intelligence/backtester.py --symbol AAPL --strategy swing_trader --days 180 --tf 1h
    python intelligence/backtester.py --symbol AAPL --stop two_bar --lookback 2

  With charts (requires matplotlib):
    python intelligence/backtester.py --symbol AAPL --days 180 --tf 1h --chart
=============================================================
"""

import logging
import argparse
import os
import sys
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Path setup so this runs from repo root OR intelligence/ directory
# ---------------------------------------------------------------------------
_this_dir   = os.path.dirname(os.path.abspath(__file__))
_root_dir   = os.path.join(_this_dir, "..")
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timeframe configuration
# ---------------------------------------------------------------------------
TF_CONFIG = {
    # annualise       = stock session (252 trading days)
    # annualise_crypto= crypto 365-day calendar, 24h/day
    # bars_per_day    = stock session bars (used for intraday time-stop mapping)
    "5m":  {"interval": "5m",  "max_days": 58,   "bars_per_day": 78,  "annualise": 252 * 78,  "annualise_crypto": 365 * 288},
    "15m": {"interval": "15m", "max_days": 59,   "bars_per_day": 96,  "annualise": 252 * 96,  "annualise_crypto": 365 * 96},
    "1h":  {"interval": "1h",  "max_days": 729,  "bars_per_day": 7,   "annualise": 252 * 7,   "annualise_crypto": 365 * 24},
    "1d":  {"interval": "1d",  "max_days": 3650, "bars_per_day": 1,   "annualise": 252,        "annualise_crypto": 365},
}

# Stop loss mode constants
STOP_STANDARD = "standard"   # Fixed % stop (existing behavior)
STOP_TWO_BAR  = "two_bar"    # N-bar trailing stop (Pine Script port)

# Max simultaneous positions (mirrors live bot)
MAX_OPEN_POSITIONS = 5

# ---------------------------------------------------------------------------
# Cancel flag — set by web_dashboard via request_cancel(); checked inside the
# _simulate bar loop every CHECK_CANCEL_EVERY bars so a long run stops within
# a few seconds rather than waiting for the whole symbol to finish.
# ---------------------------------------------------------------------------

class _BacktestCancelled(Exception):
    """Private sentinel — raised only by our cancel checkpoints.
    Intentionally NOT a subclass of OSError / InterruptedError so it cannot
    interfere with Python's own signal handling or server socket machinery."""

_cancel_event = threading.Event()
CHECK_CANCEL_EVERY = 5    # bars between cancel checks; keep UI cancel responsive on 5m runs

def request_cancel():
    """Signal the running backtest to stop at the next cancel checkpoint."""
    _cancel_event.set()

def clear_cancel():
    """Reset the cancel flag — call at the start of every new backtest run."""
    _cancel_event.clear()


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class BacktestTrade:
    symbol:         str
    direction:      str
    entry_date:     str
    exit_date:      str
    entry_price:    float
    exit_price:     float
    quantity:       float
    position_value: float
    stop_loss:      float
    take_profit:    float
    pnl:            float
    pnl_pct:        float
    exit_reason:    str
    signal_score:   float
    bars_held:      int
    strategy_name:  str = "default"
    stop_mode:      str = "standard"   # 'standard' or 'two_bar'
    fees:           float = 0.0        # round-trip friction cost for this trade
    # ── adaptive_regime metadata (blank for all other strategies) ──────
    entry_mode:  str   = ""    # "trend" | "mean_rev" | ""
    regime:      str   = ""    # regime label from signal metadata
    entry_rsi:   float = 0.0
    entry_adx:   float = 0.0
    entry_atr:   float = 0.0


@dataclass
class EquityPoint:
    """One point on the equity curve — recorded every bar."""
    bar_index:  int
    timestamp:  str
    equity:     float
    drawdown:   float          # negative pct from peak
    daily_ret:  float          # pct return vs previous bar


@dataclass
class BacktestResult:
    symbol:           str
    strategy_name:    str
    timeframe:        str
    start_date:       str
    end_date:         str
    starting_capital: float
    ending_capital:   float
    total_return_pct: float
    total_trades:     int
    winning_trades:   int
    losing_trades:    int
    win_rate:         float
    avg_win_pct:      float
    avg_loss_pct:     float
    profit_factor:    float
    max_drawdown_pct: float
    sharpe_ratio:     float
    sortino_ratio:    float
    calmar_ratio:     float
    largest_win:      float
    largest_loss:     float
    avg_bars_held:    float
    stop_mode:         str   = "standard"  # 'standard' or 'two_bar'
    two_bar_lookback:  int   = 2           # N used when stop_mode == 'two_bar'
    fees_paid:         float = 0.0         # total round-trip friction deducted
    commission_pct:    float = 0.0         # per-leg commission used
    slippage_pct:      float = 0.0         # per-leg slippage used
    initial_stop_mode: str   = "auto"      # "auto"|"percent"|"signal_structural"|"two_bar"
    trail_mode:        str   = "auto"      # "auto"|"percent"|"two_bar"|"none"
    trades:            List[BacktestTrade] = field(default_factory=list)
    equity_curve:      List[EquityPoint]   = field(default_factory=list)
    diagnostics:       dict                = field(default_factory=dict)  # adaptive_regime only


# ===========================================================================
# 2-Bar Trailing Stop Engine
# ===========================================================================

class TwoBarStop:
    """
    Python port of the Pine Script 2-Bar Trailing Stop Strategy.

    Algorithm (mirrors Pine Script exactly, no lookahead):
      - Initial stop at entry:  lowest low of bars [entry-N .. entry-1]
      - Trail trigger:          current bar high > highest high of prior N bars
      - New candidate stop:     lowest low of prior N bars at that moment
      - Apply only if raises:   stop ratchets UP only, never down

    Parameters:
        lookback (int): N in 'N-bar stop'. Default 2 matches Pine default.
                        Range 1-20. Higher = wider stop, slower trail.
    """

    def __init__(self, lookback: int = 2):
        self.lookback = max(1, min(20, lookback))

    def initial_stop(self, df: pd.DataFrame, entry_idx: int,
                     direction: str) -> float:
        """
        Calculate the initial stop price at the moment of entry.
        Uses bars [entry_idx - lookback .. entry_idx - 1] to avoid lookahead.

        Long:  stop = lowest low of prior N bars
        Short: stop = highest high of prior N bars
        """
        start = max(0, entry_idx - self.lookback)
        end   = entry_idx   # exclusive — does NOT include current bar
        if start >= end:
            # Not enough bars — fallback to 1 bar back
            start = max(0, end - 1)
        window = df.iloc[start:end]
        if window.empty:
            # Absolute fallback: use current bar price with 2% buffer
            price = float(df.iloc[entry_idx]["close"])
            return price * 0.98 if direction == "long" else price * 1.02

        if direction == "long":
            return float(window["low"].min())
        else:
            return float(window["high"].max())

    def update_stop(self, df: pd.DataFrame, current_idx: int,
                    current_stop: float, direction: str) -> float:
        """
        Called on every bar while in a position.
        Returns new stop price (may be same as current_stop if no trail triggered).

        Trail trigger:
          Long:  current bar high > highest high of prior N bars  -> advance stop up
          Short: current bar low  < lowest low  of prior N bars   -> advance stop down

        Ratchet rule: new stop only applies if it improves (moves in profit direction).
        """
        start = max(0, current_idx - self.lookback)
        end   = current_idx   # prior N bars, no current bar
        if start >= end:
            return current_stop

        prior_window = df.iloc[start:end]
        if prior_window.empty:
            return current_stop

        current_bar = df.iloc[current_idx]
        current_high = float(current_bar["high"])
        current_low  = float(current_bar["low"])

        if direction == "long":
            prior_highest_high = float(prior_window["high"].max())
            is_new_n_bar_high  = current_high > prior_highest_high
            if is_new_n_bar_high:
                candidate = float(prior_window["low"].min())
                if candidate > current_stop:   # ratchet up only
                    return candidate
        else:  # short
            prior_lowest_low  = float(prior_window["low"].min())
            is_new_n_bar_low  = current_low < prior_lowest_low
            if is_new_n_bar_low:
                candidate = float(prior_window["high"].max())
                if candidate < current_stop:   # ratchet down only (tighten short stop)
                    return candidate

        return current_stop

    def check_stop_hit(self, df: pd.DataFrame, bar_idx: int,
                       stop_price: float, direction: str) -> bool:
        """
        Check if the stop was hit on this bar.
        Uses intrabar logic: long hit if low <= stop, short hit if high >= stop.
        """
        bar = df.iloc[bar_idx]
        if direction == "long":
            return float(bar["low"]) <= stop_price
        else:
            return float(bar["high"]) >= stop_price


# ===========================================================================
# Backtester lifecycle-exit helpers
# Mirror the exit stack in position_monitor so backtest and live diverge
# as little as possible.  All functions are stateless and bar-index based.
# ===========================================================================

def _bt_eod_close(df: pd.DataFrame, bar_idx: int, asset_class: str) -> Optional[str]:
    """
    EOD close for stock positions.
    Fires when bar timestamp >= 15:45 in whatever tz the index carries
    (yfinance strips tz for US stocks, leaving naive ET timestamps).
    Not applicable to crypto.
    """
    if asset_class != "stock":
        return None
    try:
        ts = df.index[bar_idx]
        if ts.hour > 15 or (ts.hour == 15 and ts.minute >= 45):
            return "eod_close"
    except Exception:
        pass
    return None


def _bt_pivot_break(df: pd.DataFrame, bar_idx: int,
                    trade: Dict, pivot_bars: int = 20) -> Optional[str]:
    """
    Pivot-point structure break exit — mirrors position_monitor._check_pivot_break().
    Uses prior `pivot_bars` bars to compute classic floor-trader pivots.
    Long: close breaks below S1 → structure failed.
    Short: close breaks above R1 → structure failed.
    """
    if bar_idx < pivot_bars:
        return None
    try:
        window = df.iloc[max(0, bar_idx - pivot_bars): bar_idx]
        h  = float(window["high"].max())
        l  = float(window["low"].min())
        c  = float(window["close"].iloc[-1])
        pp = (h + l + c) / 3
        s1 = 2 * pp - h
        r1 = 2 * pp - l
        price = float(df.iloc[bar_idx]["close"])
        if trade["direction"] == "long"  and price < s1:
            return "pivot_break"
        if trade["direction"] == "short" and price > r1:
            return "pivot_break"
    except Exception:
        pass
    return None


def _bt_stale_adx(df: pd.DataFrame, bar_idx: int,
                  trade: Dict) -> Optional[str]:
    """
    Stale-trend exit — mirrors position_monitor._check_stale_adx().
    If ADX has fallen below 25 the trend has likely ended; adverse DI
    cross triggers even sooner.
    """
    try:
        import pandas_ta as _ta
        window = df.iloc[max(0, bar_idx - 50): bar_idx + 1]
        if len(window) < 20:
            return None
        adx_df = _ta.adx(
            window["high"].astype(float),
            window["low"].astype(float),
            window["close"].astype(float),
            length=14,
        )
        if adx_df is None or adx_df.empty:
            return None
        adx_col = [c for c in adx_df.columns if c.startswith("ADX_")]
        dmp_col = [c for c in adx_df.columns if c.startswith("DMP_")]
        dmn_col = [c for c in adx_df.columns if c.startswith("DMN_")]
        if not (adx_col and dmp_col and dmn_col):
            return None
        adx_v = float(adx_df[adx_col[0]].iloc[-1])
        dmp_v = float(adx_df[dmp_col[0]].iloc[-1])
        dmn_v = float(adx_df[dmn_col[0]].iloc[-1])
        if adx_v < 25.0:           # ADX_STALE_THRESHOLD
            return "stale_adx"
        if trade["direction"] == "long"  and dmn_v > dmp_v:
            return "stale_di_cross"
        if trade["direction"] == "short" and dmp_v > dmn_v:
            return "stale_di_cross"
    except Exception:
        pass
    return None


def _bt_orb_vwap(df: pd.DataFrame, bar_idx: int, trade: Dict) -> Optional[str]:
    """
    ORB VWAP cross exit — mirrors position_monitor._check_orb_vwap_exit().
    VWAP computed from the most recent ~78 bars (~one 5m session).
    Long: close crosses below VWAP → exit.
    Short: close crosses above VWAP → exit.
    """
    try:
        window  = df.iloc[max(0, bar_idx - 78): bar_idx + 1]
        if len(window) < 5:
            return None
        typ     = ((window["high"].astype(float) +
                    window["low"].astype(float) +
                    window["close"].astype(float)) / 3)
        vol     = window["volume"].astype(float)
        vol_sum = float(vol.sum())
        if vol_sum <= 0:
            return None
        vwap    = float((typ * vol).sum() / vol_sum)
        price   = float(df.iloc[bar_idx]["close"])
        if trade["direction"] == "long"  and price < vwap:
            return "vwap_cross"
        if trade["direction"] == "short" and price > vwap:
            return "vwap_cross"
    except Exception:
        pass
    return None


# ===========================================================================
# Main Backtester
# ===========================================================================

class Backtester:
    """
    Simulates trading strategies on historical OHLCV data.
    - Supports 5m / 1h / 1d timeframes
    - Up to 5 simultaneous open positions (mirrors live bot)
    - Per-bar equity curve for accurate drawdown & Sharpe
    - Two stop loss modes: standard (fixed %) or two_bar (N-bar trailing)
    - Exports JSON-ready equity data for the Streamlit dashboard
    """

    def __init__(self, starting_capital: float = 10_000.0):
        self.starting_capital = starting_capital

        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            raise ImportError("Run: pip install --upgrade yfinance --break-system-packages")

        try:
            import ccxt
            self.ccxt = ccxt
        except ImportError:
            self.ccxt = None

        try:
            from scanners.market_scanner import TechnicalAnalysis
            self.ta = TechnicalAnalysis()
        except Exception as e:
            logger.warning(f"TechnicalAnalysis not loaded — default scorer unavailable: {e}")
            self.ta = None

    # -----------------------------------------------------------------------
    # Data quality validation
    # -----------------------------------------------------------------------

    def _validate_ohlcv(self, df: pd.DataFrame, symbol: str,
                        timeframe: str = "1h") -> Optional[pd.DataFrame]:
        """
        Validate and lightly clean an OHLCV dataframe before simulation.

        Returns the (possibly cleaned) dataframe, or None if data is too
        corrupted to trust.  Never invents or interpolates prices.

        Checks performed
        ----------------
        1. Required columns present
        2. Duplicate timestamps removed (keep last)
        3. NaN / inf in OHLC -> reject if > 1 % of rows after minimal drop
        4. Non-positive OHLC values -> reject
        5. Candle integrity  (high >= max(o,c,l), low <= min(o,c,h))
        6. Corruption heuristics
           a. Single-bar close-to-close drop >= 90 %  (TON-style spike)
           b. Collapse-and-reversion: close drops >= 80 % then recovers
              >= 60 % of that drop within 5 bars
           c. More than 2 % of bars are integrity violators
        """
        date_span = ""
        try:
            date_span = f" ({df.index[0].date()} - {df.index[-1].date()})"
        except Exception:
            pass

        def _fail(reason: str) -> None:
            logger.warning(
                f"[DATA QUALITY FAIL] {symbol} | {timeframe}{date_span} | {reason}"
            )

        # 1. Required columns
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            _fail(f"missing columns: {missing}")
            return None

        # 2. Drop duplicate index entries (keep last)
        dupes = df.index.duplicated(keep="last")
        if dupes.any():
            logger.debug(f"  {symbol}: dropping {dupes.sum()} duplicate timestamps")
            df = df[~dupes]

        # 3. NaN / inf in OHLC
        ohlc = df[["open", "high", "low", "close"]]
        nan_rows = ohlc.isnull().any(axis=1) | np.isinf(ohlc.values).any(axis=1)
        if nan_rows.any():
            # Allow dropping up to 1 % of rows (isolated spikes / weekend stubs)
            frac = nan_rows.sum() / len(df)
            if frac > 0.01:
                _fail(f"NaN/inf in OHLC on {nan_rows.sum()} rows ({frac:.1%})")
                return None
            df = df[~nan_rows]
            logger.debug(f"  {symbol}: dropped {nan_rows.sum()} NaN/inf rows")

        if len(df) < 30:
            _fail(f"only {len(df)} clean rows after NaN drop — need >= 30")
            return None

        # 4. Non-positive prices
        if (df[["open", "high", "low", "close"]] <= 0).any().any():
            _fail("non-positive OHLC values detected")
            return None

        # 5. Candle integrity
        bad_high = df["high"] < df[["open", "close", "low"]].max(axis=1)
        bad_low  = df["low"]  > df[["open", "close", "high"]].min(axis=1)
        bad_candle = bad_high | bad_low
        bad_frac = bad_candle.sum() / len(df)
        if bad_frac > 0.02:
            _fail(
                f"candle integrity violations on {bad_candle.sum()} rows "
                f"({bad_frac:.1%}) — high < body or low > body"
            )
            return None

        # 6. Corruption heuristics (intraday focus: 5m / 1h)
        closes = df["close"].values

        # 6a. Any single bar close-to-close drop >= 90 %
        pct_changes = np.diff(closes) / closes[:-1]
        worst_drop = pct_changes.min() if len(pct_changes) else 0.0
        if worst_drop <= -0.90:
            _fail(
                f"single-bar close-to-close drop of {worst_drop:.1%} — "
                "likely data corruption (spike / bad print)"
            )
            return None

        # 6b. Collapse-and-reversion within 5 bars (TON/USD pattern)
        #     Price drops >= 80 % in one bar, then recovers >= 60 % of
        #     that drop within the next 5 bars.
        for i in range(len(closes) - 5):
            drop = (closes[i + 1] - closes[i]) / closes[i]
            if drop <= -0.80:
                drop_abs = closes[i] - closes[i + 1]
                recovery = max(closes[i + 2 : i + 7]) - closes[i + 1]
                if drop_abs > 0 and recovery / drop_abs >= 0.60:
                    _fail(
                        f"collapse-and-reversion pattern at bar {i} "
                        f"(drop {drop:.1%}, recovered {recovery / drop_abs:.0%} within 5 bars)"
                    )
                    return None

        return df

    # -----------------------------------------------------------------------
    # Data fetching
    # -----------------------------------------------------------------------

    def fetch_history(self, symbol: str, days: int = 365,
                      timeframe: str = "1h") -> Optional[pd.DataFrame]:
        cfg   = TF_CONFIG.get(timeframe, TF_CONFIG["1h"])
        tf    = cfg["interval"]
        max_d = cfg["max_days"]
        days  = min(days, max_d)

        # Intraday (5m / 15m / 1h): use period= so Yahoo returns exactly the
        # requested window without date-boundary edge cases or +5-day padding.
        # Daily (1d): use start/end because period= is capped at 1y but we
        # support up to 10 years of daily data.
        is_intraday = timeframe in ("5m", "15m", "1h")

        if is_intraday:
            logger.info(f"Fetching {days}d of {tf} data for {symbol} (period=)...")
            fetch_kw = {"period": f"{days}d", "interval": tf, "auto_adjust": True}
        else:
            end   = datetime.now()
            start = end - timedelta(days=days)
            logger.info(f"Fetching {days}d of {tf} data for {symbol}...")
            fetch_kw = {
                "start":       start.strftime("%Y-%m-%d"),
                "end":         end.strftime("%Y-%m-%d"),
                "interval":    tf,
                "auto_adjust": True,
            }

        try:
            ticker = self.yf.Ticker(symbol)
            df = ticker.history(**fetch_kw)
            if df is None or df.empty:
                logger.error(f"No data returned for {symbol}")
                return None
            df.columns = [c.lower() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            if len(df) < 30:
                logger.error(f"Only {len(df)} bars for {symbol} — need >=30")
                return None
            logger.info(f"  -> {len(df)} bars  ({df.index[0].date()} - {df.index[-1].date()})")
            df = self._validate_ohlcv(df, symbol, timeframe)
            return df
        except Exception as e:
            logger.error(f"fetch_history failed for {symbol}: {e}")
            return None

    def fetch_history_crypto(self, symbol: str, days: int = 30,
                              timeframe: str = "1h") -> Optional[pd.DataFrame]:
        yf_symbol = symbol.replace("/", "-")
        cfg   = TF_CONFIG.get(timeframe, TF_CONFIG["1h"])
        tf    = cfg["interval"]
        max_d = cfg["max_days"]
        days  = min(days, max_d)

        # Same intraday / daily split as fetch_history — period= for intraday
        # avoids the start/end boundary weirdness and +5-day over-fetch.
        is_intraday = timeframe in ("5m", "15m", "1h")

        if is_intraday:
            logger.info(f"Fetching {days}d of {tf} crypto data for {yf_symbol} via yfinance (period=)...")
            fetch_kw = {"period": f"{days}d", "interval": tf, "auto_adjust": True}
        else:
            end   = datetime.now()
            start = end - timedelta(days=days)
            logger.info(f"Fetching {days}d of {tf} crypto data for {yf_symbol} via yfinance...")
            fetch_kw = {
                "start":       start.strftime("%Y-%m-%d"),
                "end":         end.strftime("%Y-%m-%d"),
                "interval":    tf,
                "auto_adjust": True,
            }

        try:
            ticker = self.yf.Ticker(yf_symbol)
            df = ticker.history(**fetch_kw)
            if df is None or df.empty:
                logger.error(f"No yfinance data returned for {yf_symbol}")
                return None
            df.columns = [c.lower() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            if len(df) < 30:
                logger.error(f"Only {len(df)} bars for {yf_symbol} — need >=30")
                return None
            logger.info(f"  -> {len(df)} bars  ({df.index[0].date()} - {df.index[-1].date()})")
            df = self._validate_ohlcv(df, symbol, timeframe)
            return df
        except Exception as e:
            logger.error(f"fetch_history_crypto failed for {yf_symbol}: {e}")
            return None

    # -----------------------------------------------------------------------
    # Default signal scorer
    # -----------------------------------------------------------------------

    def _score_bar(self, df: pd.DataFrame, idx: int) -> Tuple[str, float, Dict]:
        if self.ta is None:
            return "none", 0.0, {}
        window = df.iloc[max(0, idx - 120): idx + 1]
        if len(window) < 15:
            return "none", 0.0, {}
        close  = window["close"]
        volume = window["volume"]
        rsi_period = config.SIGNAL_TUNING.get("rsi_momentum_period", 14)
        ema_fast   = config.SIGNAL_TUNING.get("ema_fast_period",      9)
        ema_slow   = config.SIGNAL_TUNING.get("ema_slow_period",      21)
        ema_trend  = config.SIGNAL_TUNING.get("ema_trend_period",     50)
        bb_period  = config.SIGNAL_TUNING.get("bb_breakout_period",   20)
        bb_std     = config.SIGNAL_TUNING.get("bb_breakout_std",      2.0)
        try:
            rsi = float(self.ta.rsi(close, rsi_period).iloc[-1])

            # macd() returns (macd_line, signal_line, histogram) — unpack the tuple
            _, _, _macd_hist_s = self.ta.macd(close)
            macd_hist = float(_macd_hist_s.iloc[-1])
            macd_prev = float(_macd_hist_s.iloc[-2]) if len(_macd_hist_s) > 1 else 0.0

            ema_f = float(self.ta.ema(close, ema_fast).iloc[-1])
            ema_s = float(self.ta.ema(close, ema_slow).iloc[-1])
            ema_t = float(self.ta.ema(close, ema_trend).iloc[-1])

            # bollinger_bands() returns (upper, lower, pct_b) — unpack the tuple
            _, _, _pct_b_s = self.ta.bollinger_bands(close, bb_period, bb_std)
            bb_pct = float(_pct_b_s.iloc[-1])

            # TechnicalAnalysis has no volume_ratio() — compute inline
            _vol_sma  = float(volume.rolling(20).mean().iloc[-1])
            vol_ratio = float(volume.iloc[-1]) / _vol_sma if _vol_sma > 0 else 1.0
        except Exception:
            return "none", 0.0, {}
        ls = ss = 0.0
        if   rsi < 38:  ls += 2.0
        elif rsi < 44:  ls += 1.0
        elif rsi > 62:  ss += 1.0
        elif rsi > 66:  ss += 2.0
        if   macd_hist > 0 and macd_prev < 0:  ls += 2.5
        elif macd_hist > 0 and macd_prev > 0:  ls += 1.0
        elif macd_hist < 0 and macd_prev > 0:  ss += 2.5
        elif macd_hist < 0 and macd_prev < 0:  ss += 1.0
        if   ema_f > ema_s > ema_t:  ls += 2.0
        elif ema_f > ema_s:          ls += 1.0
        elif ema_f < ema_s < ema_t:  ss += 2.0
        elif ema_f < ema_s:          ss += 1.0
        if   bb_pct < 0.15:  ls += 1.5
        elif bb_pct < 0.30:  ls += 0.75
        elif bb_pct > 0.85:  ss += 1.5
        elif bb_pct > 0.70:  ss += 0.75
        if vol_ratio >= 1.2:
            ls += 1.0
            ss += 1.0
        ln = min(ls / 10.0, 1.0)
        sn = min(ss / 10.0, 1.0)
        MIN_CONF = 0.60
        indicators = {
            "rsi": round(rsi, 2), "macd_hist": round(macd_hist, 4),
            "ema_fast": round(ema_f, 4), "ema_slow": round(ema_s, 4),
            "bb_pct": round(bb_pct, 3), "volume_ratio": round(vol_ratio, 2),
        }
        if ln >= sn and ln >= MIN_CONF:
            return "long",  round(ln, 3), indicators
        if sn > ln  and sn >= MIN_CONF:
            return "short", round(sn, 3), indicators
        return "none", 0.0, indicators

    # -----------------------------------------------------------------------
    # Strategy loader
    # -----------------------------------------------------------------------

    def _load_strategy(self, strategy_name: str):
        strategy_map = {
            "rsi_momentum":       ("strategies.rsi_momentum",       "RSIMomentum"),
            "bollinger_breakout": ("strategies.bollinger_breakout",  "BollingerBreakout"),
            "bollinger_squeeze": ("strategies.bollinger_squeeze",  "BollingerSqueeze"),                      
            "ema_crossover":      ("strategies.ema_crossover",       "EMACrossover"),
            "mean_reversion":     ("strategies.mean_reversion",      "MeanReversion"),
            "scalp_master":       ("strategies.scalp_master",        "ScalpMaster"),
            "swing_trader":       ("strategies.swing_trader",        "SwingTrader"),
            "grid_bot":           ("strategies.grid_bot",            "GridBot"),
            "dca_accumulator":    ("strategies.dca_accumulator",     "DCAAccumulator"),
            "vwap_momentum":      ("strategies.vwap_momentum",       "VWAPMomentum"),
            "vwap_confirmed_orb": ("strategies.vwap_confirmed_orb",  "VwapConfirmedOrb"),
            "hammer_reversal":    ("strategies.hammer_reversal",     "HammerReversal"),
            "orb_breakout":       ("strategies.orb_breakout",        "ORBBreakout"),
            "adaptive_regime":    ("strategies.adaptive_regime",     "AdaptiveRegime"),
            "ecb_strategy":       ("strategies.ecb_strategy",        "ECBStrategy"),
            "vdmr_strategy":      ("strategies.vdmr_strategy",       "VDMRStrategy"),
            "rsi_dip_spike_v4":   ("strategies.rsi_dip_spike_v4",   "RSIDipSpikeV4Strategy"),
        }
        if strategy_name not in strategy_map:
            return None
        import importlib
        module_path, class_name = strategy_map[strategy_name]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()

    # -----------------------------------------------------------------------
    # Trade helpers — standard stop mode
    # -----------------------------------------------------------------------

    def _check_exit_standard(self, trade: Dict, row: pd.Series,
                              trailing_gap_pct: float,
                              take_profit_pct:  float) -> Optional[str]:
        """
        Standard fixed % stop with symmetric trailing for both directions.

        Stop checks use intrabar low/high so a wick that touches the stop
        registers even when the bar closes beyond it.  TP also uses intrabar
        high/low for the same reason (parity with live fill logic).

        Same-bar conflict rule: when both SL and TP are hit on the same bar
        the stop wins (conservative — avoids crediting the full TP gain when
        the price also visited the stop level intrabar).
        """
        d     = trade["direction"]
        sl    = trade["current_sl"]
        tp    = trade["current_tp"]
        low   = float(row["low"])
        high  = float(row["high"])
        price = float(row["close"])

        if d == "long":
            sl_hit = low  <= sl
            tp_hit = high >= tp
            if sl_hit:                    # stop wins on same-bar conflict
                return "stop_loss"
            if tp_hit:
                return "take_profit"
            # Trail: advance stop only if it raises the floor
            new_sl = price * (1 - trailing_gap_pct)
            if new_sl > sl:
                trade["current_sl"] = new_sl
        else:
            sl_hit = high >= sl
            tp_hit = low  <= tp
            if sl_hit:                    # stop wins on same-bar conflict
                return "stop_loss"
            if tp_hit:
                return "take_profit"
            # Trail: advance stop only if it lowers the ceiling
            new_sl = price * (1 + trailing_gap_pct)
            if new_sl < sl:
                trade["current_sl"] = new_sl

        return None

    def _check_exit_two_bar(self, trade: Dict, df: pd.DataFrame,
                             bar_idx: int,
                             take_profit_pct: float,
                             two_bar_engine: TwoBarStop) -> Optional[str]:
        """
        2-Bar trailing stop exit check.
        1. Update the trailing stop (ratchet up on new N-bar high)
        2. Check if stop was hit intrabar (low <= stop for longs)
        3. Check take profit (unchanged from standard mode)
        """
        direction = trade["direction"]
        price     = float(df.iloc[bar_idx]["close"])

        # Step 1: Check if stop was hit intrabar using the PREVIOUS bar's stop.
        # Must happen before update_stop — a single OHLCV bar cannot both advance
        # the stop AND be stopped out by the advanced level (same-bar optimism bug).
        if two_bar_engine.check_stop_hit(df, bar_idx, trade["current_sl"], direction):
            return "stop_loss"

        # Step 2: Advance trailing stop if triggered (bar survived the stop check)
        new_stop = two_bar_engine.update_stop(
            df, bar_idx, trade["current_sl"], direction
        )
        if new_stop != trade["current_sl"]:
            trade["current_sl"] = new_stop

        # Step 3: Take profit — intrabar high/low for parity with stop check.
        # Same-bar conflict is already resolved: if the stop was hit in step 1
        # we already returned "stop_loss", so reaching here means the stop was
        # NOT hit — we can safely credit the TP without double-counting.
        tp   = trade["current_tp"]
        low  = float(df.iloc[bar_idx]["low"])
        high = float(df.iloc[bar_idx]["high"])
        if direction == "long"  and high >= tp:
            return "take_profit"
        if direction == "short" and low  <= tp:
            return "take_profit"

        return None

    def _close_trade(self, trade: Dict, price: float,
                     reason: str, idx: int,
                     df: pd.DataFrame,
                     strategy_name: str = "default",
                     stop_mode: str = "standard") -> Tuple[float, BacktestTrade]:
        d   = trade["direction"]
        qty = trade["quantity"]

        # Stop loss exits fill at the stop price for both stop modes.
        # Both _check_exit_standard and _check_exit_two_bar now use intrabar
        # low/high, so we know the stop was touched — fill at the stop level,
        # not the close (which may be far from where the stop was hit).
        if reason == "stop_loss":
            exit_price = trade["current_sl"]
        else:
            exit_price = price

        pnl = (
            (exit_price - trade["entry_price"]) * qty if d == "long"
            else (trade["entry_price"] - exit_price) * qty
        )
        pnl_pct = (pnl / trade["position_value"] * 100
                   if trade["position_value"] else 0)
        bt_trade = BacktestTrade(
            symbol         = trade["symbol"],
            direction      = d,
            entry_date     = trade["entry_date"],
            exit_date      = str(df.index[idx]),
            entry_price    = trade["entry_price"],
            exit_price     = exit_price,
            quantity       = qty,
            position_value = trade["position_value"],
            stop_loss      = trade["stop_loss"],
            take_profit    = trade["take_profit"],
            pnl            = round(pnl, 4),
            pnl_pct        = round(pnl_pct, 2),
            exit_reason    = reason,
            signal_score   = trade["signal_score"],
            bars_held      = idx - trade["entry_idx"],
            strategy_name  = strategy_name,
            stop_mode      = stop_mode,
        )
        # Populate adaptive_regime metadata fields if present
        _meta = trade.get("entry_metadata", {})
        bt_trade.entry_mode = str(_meta.get("adaptive_exit_mode", "") or "")
        bt_trade.regime     = str(_meta.get("regime",             "") or "")
        bt_trade.entry_rsi  = float(_meta.get("rsi", 0.0) or 0.0)
        bt_trade.entry_adx  = float(_meta.get("adx", 0.0) or 0.0)
        bt_trade.entry_atr  = float(_meta.get("atr", 0.0) or 0.0)
        return pnl, bt_trade

    # -----------------------------------------------------------------------
    # Core simulation loop
    # -----------------------------------------------------------------------

    def _simulate(self, symbol: str, df: pd.DataFrame,
                  strategy_name: str,
                  strategy_obj,
                  starting_capital: float,
                  timeframe: str,
                  stop_mode: str = STOP_STANDARD,
                  two_bar_lookback: int = 2,
                  asset_class: str = "stock",
                  commission_pct: float = None,
                  slippage_pct:   float = None,
                  initial_stop_mode: str = "auto",
                  trail_mode:        str = "auto",
                  entry_mode_filter: str = "all",
                  entry_side_filter: str = "all") -> BacktestResult:
        """
        commission_pct / slippage_pct: per-leg friction (%).
        None → use config defaults for the asset class.
        Pass 0.0 for both to reproduce friction-free (optimistic) results.
        """
 

        cfg = TF_CONFIG.get(timeframe, TF_CONFIG["1h"])
        # Crypto trades 365d × 24h — use crypto-specific factor so Sharpe/Sortino
        # is correctly scaled. Stock sessions use 252 trading days.
        annualise_factor = (
            cfg.get("annualise_crypto", cfg["annualise"])
            if asset_class == "crypto"
            else cfg["annualise"]
        )

        # Resolve friction defaults from config if not explicitly overridden
        if commission_pct is None:
            commission_pct = (config.BT_COMMISSION_CRYPTO_PCT
                              if asset_class == "crypto"
                              else config.BT_COMMISSION_STOCK_PCT)
        if slippage_pct is None:
            slippage_pct   = (config.BT_SLIPPAGE_CRYPTO_PCT
                              if asset_class == "crypto"
                              else config.BT_SLIPPAGE_STOCK_PCT)

        # Total per-leg friction; round-trip = 2 × this value
        friction_per_leg = (commission_pct + slippage_pct) / 100.0

        # ── Stop mode resolution ─────────────────────────────────────────────
        # `initial_stop_mode` and `trail_mode` decouple initial stop selection
        # from trailing behaviour.  "auto" preserves legacy stop_mode semantics.
        #
        #   initial_stop_mode:
        #     "auto"               → two_bar if stop_mode==two_bar, else percent_or_structural
        #     "percent"            → fixed % always (ignore structural_stop_price)
        #     "signal_structural"  → ATR-structural from signal metadata, % fallback
        #     "two_bar"            → N-bar structural initial stop
        #     "percent_or_structural" → legacy: use structural if present, else %
        #
        #   trail_mode:
        #     "auto"    → two_bar if stop_mode==two_bar, else percent
        #     "percent" → trailing % ratchet
        #     "two_bar" → N-bar trailing stop engine
        #     "none"    → no trail (SL stays at initial level)
        _initial = (
            "two_bar" if stop_mode == STOP_TWO_BAR else "percent_or_structural"
        ) if initial_stop_mode == "auto" else initial_stop_mode

        _trail = (
            "two_bar" if stop_mode == STOP_TWO_BAR else "percent"
        ) if trail_mode == "auto" else trail_mode

        _need_two_bar  = (_initial == "two_bar" or _trail == "two_bar")
        two_bar_engine = TwoBarStop(two_bar_lookback) if _need_two_bar else None

        capital            = starting_capital
        total_fees_paid    = 0.0
        open_trades: List[Dict] = []
        closed_trades: List[BacktestTrade] = []
        equity_curve:  List[EquityPoint]  = []

        max_daily_loss_pct = config.MAX_DAILY_LOSS_PCT / 100
        max_position_pct   = config.MAX_POSITION_PCT / 100
        trailing_gap_pct   = config.TRAILING_STOP_PCT / 100

        default_sl_pct = config.DEFAULT_STOP_LOSS_PCT   / 100
        default_tp_pct = config.DEFAULT_TAKE_PROFIT_PCT / 100

        if strategy_obj is not None:
            default_sl_pct = strategy_obj.stop_loss_pct   / 100
            default_tp_pct = strategy_obj.take_profit_pct / 100
            # Reset per-symbol diagnostics counters (adaptive_regime and any future strategy)
            if hasattr(strategy_obj, "_reset_diagnostics"):
                strategy_obj._reset_diagnostics()

        daily_pnl          = 0.0
        consecutive_losses = 0
        trading_halted     = False
        last_date          = None
        peak_equity        = starting_capital
        min_bars           = min(120, max(20, len(df) // 4))
       
        # ── Lifecycle exit thresholds ─────────────────────────────────────────
        # Map live position_monitor second-based constants to bar counts so the
        # backtester fires the same exits at approximately the same elapsed time.
        # Daily bars (bars_per_hour == 0) skip time stops — day-trade logic n/a.
        _BPH = {"5m": 12, "15m": 4, "1h": 1, "1d": 0} 
        bph = _BPH.get(timeframe, 1)
        time_stops_on = bph > 0
        EARLY_LOSS_BARS = max(1, round(0.5 * bph))   # 30 min
        PERF_2HR_BARS   = max(1, round(2.0 * bph))   # 2 hr
        PERF_5HR_BARS   = max(1, round(5.0 * bph))   # 5 hr
        HARD_STOP_BARS  = max(1, round(8.0 * bph))   # 8 hr
        STALE_ADX_BARS  = max(1, round(3.0 * bph))   # 3 hr (ADX staleness)

        # Exact mirrors of position_monitor constant values
        EARLY_LOSS_PCT   = -0.5   # EARLY_LOSS_MIN_PCT
        PERF_2HR_PCT     =  0.2   # PERF_CHECK_2HR_MIN_PCT
        PERF_5HR_PCT     =  1.0   # PERF_CHECK_5HR_MIN_PCT
        # grid_bot and dca_accumulator are exempt from time stops in live —
        # mirror that here so backtest results are comparable to live.
        # ecb_strategy uses strategy-defined 24-bar hold; generic 8h/30m/2h/5h
        # stops fire before its thesis plays out and invalidate results.
        TIME_STOP_EXEMPT = frozenset({"grid_bot", "dca_accumulator", "ecb_strategy", "rsi_dip_spike_v4", "adaptive_regime"})

        # ── Next-bar execution ────────────────────────────────────────────────
        # Signal generated on bar i is executed at bar i+1 open.
        # This eliminates the "signal and fill on the same close" lookahead bias.
        pending_signal: Optional[Dict] = None

        for i in range(min_bars, len(df)):
            # Cancel checkpoint — checked every CHECK_CANCEL_EVERY bars so a
            # cancel request lands within seconds rather than at end of symbol.
            if i % CHECK_CANCEL_EVERY == 0 and _cancel_event.is_set():
                raise _BacktestCancelled()

            row          = df.iloc[i]
            current_date = str(df.index[i])[:10]
            price        = float(row["close"])
            open_price   = float(row["open"])

            if current_date != last_date:
                daily_pnl          = 0.0
                trading_halted     = False
                consecutive_losses = 0
                last_date          = current_date

            # ── Step 0: Execute pending entry at this bar's OPEN ─────────────
            # Signal was generated on the previous bar; entry is at this bar's
            # open — realistic next-bar execution, no same-bar lookahead.
            if (pending_signal is not None
                    and not trading_halted
                    and len(open_trades) < MAX_OPEN_POSITIONS):
                _ps = pending_signal
                pending_signal = None

                entry_p    = open_price
                already_in = any(t["symbol"] == symbol for t in open_trades)

                if not already_in and entry_p > 0:
                    pos_val  = capital * max_position_pct
                    if pos_val >= 1.0:
                        qty = pos_val / entry_p

                        if _initial == "two_bar":
                            _sl = two_bar_engine.initial_stop(df, i, _ps["direction"])
                        else:
                            # signal_structural always prefers the ATR-based stop;
                            # percent_or_structural (legacy) also uses it when present;
                            # percent ignores structural metadata entirely.
                            _use_struct = _initial in ("signal_structural",
                                                       "percent_or_structural")
                            struct_sl   = (_ps["meta"].get("structural_stop_price")
                                           if _use_struct else None)
                            if struct_sl and struct_sl > 0:
                                if _ps["direction"] == "long"  and struct_sl < entry_p:
                                    _sl = struct_sl
                                elif _ps["direction"] == "short" and struct_sl > entry_p:
                                    _sl = struct_sl
                                else:
                                    _sl = (entry_p * (1 - _ps["sl_pct"])
                                           if _ps["direction"] == "long"
                                           else entry_p * (1 + _ps["sl_pct"]))
                            else:
                                _sl = (entry_p * (1 - _ps["sl_pct"])
                                       if _ps["direction"] == "long"
                                       else entry_p * (1 + _ps["sl_pct"]))
                        _tp = (entry_p * (1 + _ps["tp_pct"])
                               if _ps["direction"] == "long"
                               else entry_p * (1 - _ps["tp_pct"]))

                        open_trades.append({
                            "symbol":         symbol,
                            "direction":      _ps["direction"],
                            "entry_idx":      i,
                            "entry_date":     str(df.index[i]),   # execution bar
                            "entry_price":    entry_p,
                            "quantity":       qty,
                            "position_value": pos_val,
                            "stop_loss":      _sl,
                            "take_profit":    _tp,
                            "signal_score":   _ps["score"],
                            "current_sl":     _sl,
                            "current_tp":     _tp,
                            "entry_metadata": _ps["meta"],
                        })
            else:
                pending_signal = None   # discard: halted or max positions

            # ── Step 1: Check exits on all open trades ────────────────────────
            still_open = []
            for trade in open_trades:
                exit_reason = None

                # 1a. EOD close — stocks only, mirrors live exit-priority rank 2
                if exit_reason is None:
                    exit_reason = _bt_eod_close(df, i, asset_class)

                # 1b. Standard SL / TP or two-bar trailing stop
                if exit_reason is None:
                    if _trail == "two_bar":
                        exit_reason = self._check_exit_two_bar(
                            trade, df, i, default_tp_pct, two_bar_engine
                        )
                    else:
                        exit_reason = self._check_exit_standard(
                            trade, row, trailing_gap_pct, default_tp_pct
                        )

                # 1c. Strategy-specific exit hook (adaptive_regime EMA/BB/RSI,
                #     all other strategies return None from BaseStrategy stub).
                if exit_reason is None and strategy_obj is not None:
                    _win  = df.iloc[max(0, i - 150): i + 1]
                    # Inject bars_held so strategy exits (e.g. ECB max_hold) can
                    # use actual elapsed bars without extending the signature.
                    _meta = dict(trade.get("entry_metadata", {}))
                    _meta["_bars_held"] = i - trade["entry_idx"]
                    exit_reason = strategy_obj.check_custom_exit(
                        trade["symbol"], _win,
                        trade["direction"],
                        _meta,
                    )

                # 1d. ORB VWAP cross exit (ORB strategy only)
                if exit_reason is None and strategy_name == "orb_breakout":
                    exit_reason = _bt_orb_vwap(df, i, trade)

                # ── Lifecycle exits: compute shared values once ───────────────
                _bars_held = i - trade["entry_idx"]
                _ep        = trade["entry_price"]
                if _ep and _ep > 0:
                    _pnl_pct = (
                        (price - _ep) / _ep * 100 if trade["direction"] == "long"
                        else (_ep - price) / _ep * 100
                    )
                else:
                    _pnl_pct = 0.0

                _time_exempt = strategy_name in TIME_STOP_EXEMPT

                # 1e. Early loss (30 min, -0.5%) — exempt strategies skip
                if (exit_reason is None and time_stops_on
                        and not _time_exempt
                        and _bars_held >= EARLY_LOSS_BARS
                        and _pnl_pct < EARLY_LOSS_PCT):
                    exit_reason = "early_loss"

                # 1f. Performance time stop 1 (2hr, < 0.2%)
                if (exit_reason is None and time_stops_on
                        and not _time_exempt
                        and _bars_held >= PERF_2HR_BARS
                        and _pnl_pct < PERF_2HR_PCT):
                    exit_reason = "perf_time_stop_1hr"   # DB-compat reason code

                # 1g. Performance time stop 2 (5hr, < 1.0%)
                if (exit_reason is None and time_stops_on
                        and not _time_exempt
                        and _bars_held >= PERF_5HR_BARS
                        and _pnl_pct < PERF_5HR_PCT):
                    exit_reason = "perf_time_stop_3hr"   # DB-compat reason code

                # 1h. Hard time stop (8hr — grid_bot / dca_accumulator EXEMPT)
                if (exit_reason is None and time_stops_on
                        and strategy_name not in TIME_STOP_EXEMPT
                        and _bars_held >= HARD_STOP_BARS):
                    exit_reason = "hard_time_stop"

                # 1i. Pivot point break (structure failure)
                if exit_reason is None:
                    exit_reason = _bt_pivot_break(df, i, trade)

                # 1j. Stale ADX/DI exit (fires after 3hr of holding)
                # Skip on large datasets (>2000 bars) — pandas_ta ADX
                # computed every bar is too slow for long 15m/1h runs.
                if (exit_reason is None and time_stops_on
                        and _bars_held >= STALE_ADX_BARS
                        and len(df) < 2000):
                    exit_reason = _bt_stale_adx(df, i, trade)

                if exit_reason:
                    pnl, bt_trade = self._close_trade(
                        trade, price, exit_reason, i, df,
                        strategy_name, stop_mode
                    )
                    # Deduct round-trip friction (entry leg + exit leg).
                    # Applied to position_value so cost scales with trade size.
                    round_trip_cost  = bt_trade.position_value * friction_per_leg * 2
                    pnl             -= round_trip_cost
                    total_fees_paid += round_trip_cost
                    bt_trade.fees    = round(round_trip_cost, 4)
                    bt_trade.pnl     = round(pnl, 4)
                    bt_trade.pnl_pct = round(
                        pnl / bt_trade.position_value * 100
                        if bt_trade.position_value else 0, 2
                    )
                    closed_trades.append(bt_trade)
                    capital   += pnl
                    daily_pnl += pnl
                    if pnl <= 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0
                    start_cap = capital - daily_pnl
                    if (start_cap > 0 and
                            daily_pnl / start_cap <= -max_daily_loss_pct):
                        trading_halted = True
                else:
                    still_open.append(trade)
            open_trades = still_open

            # ── Step 2: Mark-to-market equity ────────────────────────────────
            mtm_capital = capital
            for trade in open_trades:
                d   = trade["direction"]
                qty = trade["quantity"]
                ep  = trade["entry_price"]
                unrealised = (
                    (price - ep) * qty if d == "long"
                    else (ep - price) * qty
                )
                mtm_capital += unrealised

            peak_equity  = max(peak_equity, mtm_capital)
            drawdown_pct = (
                (mtm_capital - peak_equity) / peak_equity * 100
                if peak_equity > 0 else 0.0
            )
            prev_equity = equity_curve[-1].equity if equity_curve else starting_capital
            bar_ret = (
                (mtm_capital - prev_equity) / prev_equity * 100
                if prev_equity > 0 else 0.0
            )
            equity_curve.append(EquityPoint(
                bar_index  = i,
                timestamp  = str(df.index[i]),
                equity     = round(mtm_capital, 2),
                drawdown   = round(drawdown_pct, 4),
                daily_ret  = round(bar_ret, 4),
            ))

            # ── Step 3: Signal generation → queue for NEXT bar entry ─────────
            if trading_halted or len(open_trades) >= MAX_OPEN_POSITIONS:
                continue

            # Don't queue if this is the last bar (no next bar to execute on)
            if i >= len(df) - 1:
                continue

            signal_direction = "none"
            signal_score     = 0.0
            sl_pct           = default_sl_pct
            tp_pct           = default_tp_pct
            signal_meta: dict = {}

            if strategy_obj is not None:
                # Use the strategy's declared candle_limit as the lookback window
                # (floor of 300 covers 200-bar SMA warmup used by quant strategies).
                # Old strategies that don't declare candle_limit get 300 bars —
                # larger than the previous 150 but harmless and more accurate.
                _lookback = max(300, getattr(strategy_obj, "candle_limit", 300))
                window = df.iloc[max(0, i - _lookback): i + 1].copy()
                try:
                    signal = strategy_obj.analyze(symbol, window, "unknown")
                    if signal is not None:
                        signal_direction = signal.direction
                        signal_score     = signal.score
                        signal_meta      = signal.metadata or {}
                        if signal.stop_loss_pct:
                            sl_pct = signal.stop_loss_pct / 100
                        if signal.take_profit_pct:
                            tp_pct = signal.take_profit_pct / 100
                except Exception as e:
                    logger.debug(f"{strategy_name} analyze error bar {i}: {e}")
            else:
                signal_direction, signal_score, _ = self._score_bar(df, i)

            if signal_direction == "none":
                continue

            # Block re-entry in EITHER direction while a position is open.
            # Same check fires again at execution time (trade may have closed).
            already_in = any(t["symbol"] == symbol for t in open_trades)
            if already_in:
                continue

            # ── Mode filter (adaptive_regime --mode trend|mean_rev) ──────────
            # Filters on the adaptive_exit_mode key in signal metadata.
            # Non-adaptive strategies always pass (their metadata won't have the key).
            if entry_mode_filter != "all":
                _sig_mode = signal_meta.get("adaptive_exit_mode", "")
                if _sig_mode != entry_mode_filter:
                    continue

            # ── Side filter (--side long|short) ──────────────────────────────
            if entry_side_filter != "all" and signal_direction != entry_side_filter:
                continue

            # Queue signal — will execute at bar i+1 open
            pending_signal = {
                "direction": signal_direction,
                "score":     signal_score,
                "sl_pct":    sl_pct,
                "tp_pct":    tp_pct,
                "meta":      signal_meta,
            }

        # --- Close any remaining open trades at end of data ---
        final_price = float(df.iloc[-1]["close"])
        for trade in open_trades:
            pnl, bt_trade = self._close_trade(
                trade, final_price, "backtest_end",
                len(df) - 1, df, strategy_name, stop_mode
            )
            round_trip_cost  = bt_trade.position_value * friction_per_leg * 2
            pnl             -= round_trip_cost
            total_fees_paid += round_trip_cost
            bt_trade.fees    = round(round_trip_cost, 4)
            bt_trade.pnl     = round(pnl, 4)
            bt_trade.pnl_pct = round(
                pnl / bt_trade.position_value * 100
                if bt_trade.position_value else 0, 2
            )
            closed_trades.append(bt_trade)
            capital += pnl

        _diagnostics = {}
        if strategy_obj is not None and hasattr(strategy_obj, "get_diagnostics"):
            _diagnostics = strategy_obj.get_diagnostics()

        return self._compile_results(
            symbol, df, closed_trades, equity_curve,
            starting_capital, capital,
            strategy_name, timeframe, annualise_factor,
            stop_mode,
            two_bar_lookback   = two_bar_lookback,
            fees_paid          = round(total_fees_paid, 2),
            commission_pct     = commission_pct,
            slippage_pct       = slippage_pct,
            initial_stop_mode  = _initial,
            trail_mode         = _trail,
            diagnostics        = _diagnostics,
        )

    # -----------------------------------------------------------------------
    # Public entry points
    # -----------------------------------------------------------------------

    def run(self, symbol: str, days: int = 365,
            starting_capital: float = None,
            timeframe: str = "1h",
            asset_class: str = "stock",
            stop_mode: str = STOP_STANDARD,
            two_bar_lookback: int = 2,
            commission_pct: float = None,
            slippage_pct:   float = None,
            initial_stop_mode: str = "auto",
            trail_mode:        str = "auto",
            entry_mode_filter: str = "all",
            entry_side_filter: str = "all") -> Optional[BacktestResult]:
        if _cancel_event.is_set():          # gate: skip before fetch starts
            return None
        capital = starting_capital or self.starting_capital
        if asset_class == "crypto":
            df = self.fetch_history_crypto(symbol, days, timeframe)
        else:
            df = self.fetch_history(symbol, days, timeframe)
        if _cancel_event.is_set():          # gate: skip simulate if cancelled during fetch
            return None
        if df is None or len(df) < 30:
            return None
        try:
            return self._simulate(symbol, df, "default", None, capital, timeframe,
                                  stop_mode, two_bar_lookback,
                                  asset_class=asset_class,
                                  commission_pct=commission_pct,
                                  slippage_pct=slippage_pct,
                                  initial_stop_mode=initial_stop_mode,
                                  trail_mode=trail_mode,
                                  entry_mode_filter=entry_mode_filter,
                                  entry_side_filter=entry_side_filter)
        except _BacktestCancelled:
            logger.info(f"[BACKTESTER] run() cancelled for {symbol}")
            return None

    def run_strategy(self, symbol: str, strategy_name: str,
                     days: int = 365,
                     starting_capital: float = None,
                     timeframe: str = "1h",
                     asset_class: str = "stock",
                     stop_mode: str = STOP_STANDARD,
                     two_bar_lookback: int = 2,
                     commission_pct: float = None,
                     slippage_pct:   float = None,
                     initial_stop_mode: str = "auto",
                     trail_mode:        str = "auto",
                     entry_mode_filter: str = "all",
                     entry_side_filter: str = "all") -> Optional[BacktestResult]:
        if _cancel_event.is_set():          # gate: skip before fetch starts
            return None
        capital = starting_capital or self.starting_capital
        if asset_class == "crypto":
            df = self.fetch_history_crypto(symbol, days, timeframe)
        else:
            df = self.fetch_history(symbol, days, timeframe)
        if _cancel_event.is_set():          # gate: skip simulate if cancelled during fetch
            return None
        if df is None or len(df) < 30:
            return None
        try:
            strategy_obj = self._load_strategy(strategy_name)
            if strategy_obj is None:
                logger.error(f"Unknown strategy: {strategy_name}")
                return None
            if (
                strategy_name == "grid_bot"
                and asset_class == "crypto"
                and entry_side_filter in ("all", "short")
            ):
                strategy_obj.backtest_allow_crypto_shorts = True
        except Exception as e:
            logger.error(f"Failed to load strategy {strategy_name}: {e}")
            return None
        try:
            return self._simulate(
                symbol, df, strategy_name, strategy_obj, capital, timeframe,
                stop_mode, two_bar_lookback,
                asset_class=asset_class,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
                initial_stop_mode=initial_stop_mode,
                trail_mode=trail_mode,
                entry_mode_filter=entry_mode_filter,
                entry_side_filter=entry_side_filter,
            )
        except _BacktestCancelled:
            logger.info(f"[BACKTESTER] run_strategy() cancelled for {symbol}/{strategy_name}")
            return None

    def run_all(self, symbols: List[str], strategy_name: str = None,
                days: int = 365, starting_capital: float = None,
                timeframe: str = "1h",
                asset_class: str = "stock",
                stop_mode: str = STOP_STANDARD,
                two_bar_lookback: int = 2,
                commission_pct: float = None,
                slippage_pct:   float = None,
                initial_stop_mode: str = "auto",
                trail_mode:        str = "auto",
                entry_mode_filter: str = "all",
                entry_side_filter: str = "all") -> List[BacktestResult]:
        clear_cancel()   # fresh run: ensure any stale cancel flag is cleared
        results = []
        for sym in symbols:
            if _cancel_event.is_set():
                logger.info("[BACKTESTER] run_all() cancelled before starting next symbol")
                break
            try:
                if strategy_name:
                    r = self.run_strategy(sym, strategy_name, days,
                                          starting_capital, timeframe, asset_class,
                                          stop_mode, two_bar_lookback,
                                          commission_pct=commission_pct,
                                          slippage_pct=slippage_pct,
                                          initial_stop_mode=initial_stop_mode,
                                          trail_mode=trail_mode,
                                          entry_mode_filter=entry_mode_filter,
                                          entry_side_filter=entry_side_filter)
                else:
                    r = self.run(sym, days, starting_capital, timeframe, asset_class,
                                 stop_mode, two_bar_lookback,
                                 commission_pct=commission_pct,
                                 slippage_pct=slippage_pct,
                                 initial_stop_mode=initial_stop_mode,
                                 trail_mode=trail_mode,
                                 entry_mode_filter=entry_mode_filter,
                                 entry_side_filter=entry_side_filter)
                if r:
                    results.append(r)
            except _BacktestCancelled:
                logger.info(f"[BACKTESTER] run_all() cancelled during {sym} — returning partial results")
                break
        return results

    # -----------------------------------------------------------------------
    # Results compilation
    # -----------------------------------------------------------------------

    def _compile_results(self, symbol, df, trades, equity_curve,
                          start_cap, end_cap,
                          strategy_name, timeframe,
                          annualise_factor,
                          stop_mode: str = STOP_STANDARD,
                          two_bar_lookback: int = 2,
                          fees_paid: float = 0.0,
                          commission_pct: float = 0.0,
                          slippage_pct:   float = 0.0,
                          initial_stop_mode: str = "auto",
                          trail_mode:        str = "auto",
                          diagnostics:       dict = None) -> BacktestResult:
        wins   = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate   = len(wins) / len(trades) * 100 if trades else 0.0
        avg_win    = float(np.mean([t.pnl_pct for t in wins]))   if wins   else 0.0
        avg_loss   = float(np.mean([t.pnl_pct for t in losses])) if losses else 0.0
        gross_win  = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        pf         = gross_win / gross_loss if gross_loss else (999.0 if gross_win > 0 else 0.0)
        avg_bars   = float(np.mean([t.bars_held for t in trades])) if trades else 0.0
        eq_vals  = pd.Series([ep.equity   for ep in equity_curve])
        dd_vals  = pd.Series([ep.drawdown for ep in equity_curve])
        max_dd   = float(dd_vals.min()) if not dd_vals.empty else 0.0
        eq_returns = eq_vals.pct_change().dropna()
        mean_ret   = float(eq_returns.mean())
        std_ret    = float(eq_returns.std())
        sharpe = (
            (mean_ret / std_ret * np.sqrt(annualise_factor))
            if std_ret > 0 else 0.0
        )
        downside = eq_returns[eq_returns < 0]
        dstd     = float(downside.std()) if len(downside) > 1 else 0.0
        sortino  = (
            (mean_ret / dstd * np.sqrt(annualise_factor))
            if dstd > 0 else 0.0
        )
        total_ret_pct = (end_cap - start_cap) / start_cap * 100 if start_cap else 0.0
        calmar = (
            abs(total_ret_pct / max_dd)
            if max_dd < 0 else 0.0
        )
        return BacktestResult(
            symbol           = symbol,
            strategy_name    = strategy_name,
            timeframe        = timeframe,
            start_date       = str(df.index[0])[:10],
            end_date         = str(df.index[-1])[:10],
            starting_capital = start_cap,
            ending_capital   = round(end_cap, 2),
            total_return_pct = round(total_ret_pct, 2),
            total_trades     = len(trades),
            winning_trades   = len(wins),
            losing_trades    = len(losses),
            win_rate         = round(win_rate, 1),
            avg_win_pct      = round(avg_win,  2),
            avg_loss_pct     = round(avg_loss, 2),
            profit_factor    = round(pf,       2),
            max_drawdown_pct = round(max_dd,   2),
            sharpe_ratio     = round(sharpe,   2),
            sortino_ratio    = round(sortino,  2),
            calmar_ratio     = round(calmar,   2),
            largest_win      = round(max((t.pnl for t in wins),   default=0), 2),
            largest_loss     = round(min((t.pnl for t in losses), default=0), 2),
            avg_bars_held    = round(avg_bars, 1),
            stop_mode          = stop_mode,
            two_bar_lookback   = two_bar_lookback,
            fees_paid          = fees_paid,
            commission_pct     = commission_pct,
            slippage_pct       = slippage_pct,
            initial_stop_mode  = initial_stop_mode,
            trail_mode         = trail_mode,
            trades             = trades,
            equity_curve       = equity_curve,
            diagnostics        = diagnostics or {},
        )

    # -----------------------------------------------------------------------
    # Rich text report
    # -----------------------------------------------------------------------

    def print_report(self, result: BacktestResult):
        w = 62
        sep = "=" * w
        thin = "-" * w
        # Build stop label — show initial + trail separately when decoupled
        _init_m  = getattr(result, "initial_stop_mode", "auto")
        _trail_m = getattr(result, "trail_mode",        "auto")
        _decoupled = (_init_m  not in ("auto", "percent_or_structural") or
                      _trail_m not in ("auto",))
        if _decoupled:
            _init_str = {
                "signal_structural":     "ATR/structural",
                "two_bar":               f"2-bar(N={result.two_bar_lookback})",
                "percent":               "fixed-%",
                "percent_or_structural": "fixed-% / struct",
                "auto":                  "auto",
            }.get(_init_m, _init_m)
            _trail_str = {
                "two_bar": f"2-bar(N={result.two_bar_lookback})",
                "percent": "% trail",
                "none":    "no trail",
                "auto":    "auto",
            }.get(_trail_m, _trail_m)
            stop_label = f"Initial: {_init_str}  |  Trail: {_trail_str}"
        elif result.stop_mode == STOP_TWO_BAR:
            stop_label = f"2-Bar Trailing (N={result.two_bar_lookback})"
        else:
            stop_label = "Standard Fixed %"
        friction_per_leg  = result.commission_pct + result.slippage_pct
        friction_rt       = friction_per_leg * 2
        friction_free     = friction_rt == 0.0
        print(f"\n{sep}")
        print(f"  BACKTEST REPORT — {result.symbol}  [{result.strategy_name}  |  {result.timeframe}]")
        print(f"  Stop Mode: {stop_label}")
        print(sep)
        print(f"  Period          : {result.start_date} -> {result.end_date}")
        print(f"  Starting Capital: ${result.starting_capital:>12,.2f}")
        print(f"  Ending Capital  : ${result.ending_capital:>12,.2f}")
        print(f"  Total Return    : {result.total_return_pct:>+.2f}%")
        print(thin)
        print(f"  Trades          : {result.total_trades}  "
              f"({result.winning_trades}W / {result.losing_trades}L)")
        print(f"  Win Rate        : {result.win_rate:.1f}%")
        print(f"  Avg Win         : +{result.avg_win_pct:.2f}%")
        print(f"  Avg Loss        :  {result.avg_loss_pct:.2f}%")
        print(f"  Profit Factor   : {result.profit_factor:.2f}   (>1.5 is good)")
        print(thin)
        print(f"  Max Drawdown    : {result.max_drawdown_pct:.2f}%")
        print(f"  Sharpe Ratio    : {result.sharpe_ratio:.2f}   (>1.0 is good)")
        print(f"  Sortino Ratio   : {result.sortino_ratio:.2f}   (>1.0 is good)")
        print(f"  Calmar Ratio    : {result.calmar_ratio:.2f}   (>1.0 is good)")
        print(f"  Largest Win     : ${result.largest_win:.2f}")
        print(f"  Largest Loss    : ${result.largest_loss:.2f}")
        print(f"  Avg Bars Held   : {result.avg_bars_held:.1f}")
        print(thin)
        if friction_free:
            print(f"  FRICTION        : NONE — zero-commission, zero-slippage run")
            print(f"                    Results are OPTIMISTIC. Use --no-fees to")
            print(f"                    compare; omit flag for realistic estimate.")
        else:
            print(f"  FRICTION ASSUMPTIONS (applied each leg, round-trip = 2x):")
            print(f"    Commission    : {result.commission_pct:.2f}% per leg")
            print(f"    Slippage      : {result.slippage_pct:.2f}% per leg")
            print(f"    Total per leg : {friction_per_leg:.2f}%  |  Round-trip: {friction_rt:.2f}%")
            print(f"    Total fees    : ${result.fees_paid:,.2f}  over {result.total_trades} trades")
            if result.total_trades > 0:
                avg_fee = result.fees_paid / result.total_trades
                print(f"    Avg per trade : ${avg_fee:.2f}")
        print(sep)
        approved = (result.win_rate >= 50 and result.profit_factor >= 1.2
                    and result.max_drawdown_pct > -25)
        status = "OK  STRATEGY APPROVED" if approved else "WARN  STRATEGY NEEDS TUNING"
        print(f"\n  {status}")

        # ── Low-sample warning ────────────────────────────────────────────────
        if result.total_trades < 10:
            print(f"\n  !!  LOW SAMPLE -- only {result.total_trades} trade(s).  "
                  f"Results are not statistically reliable.")

        # ── Mode / side / exit-reason breakdown ──────────────────────────────
        _has_mode = any(getattr(t, "entry_mode", "") for t in result.trades)
        if _has_mode:
            _print_mode_breakdown(result.trades, w)

        # ── AdaptiveRegime diagnostics ────────────────────────────────────────
        _diag = getattr(result, "diagnostics", {})
        if _diag and result.strategy_name == "adaptive_regime":
            _print_adaptive_diagnostics(_diag, w)

        print(f"{sep}\n")

    def print_ascii_chart(self, result: BacktestResult, width: int = 60, height: int = 12):
        eq = [ep.equity for ep in result.equity_curve]
        if not eq:
            return
        lo, hi = min(eq), max(eq)
        rng = hi - lo or 1
        cols = min(width, len(eq))
        step = max(1, len(eq) // cols)
        sampled = eq[::step][:cols]
        print(f"\n  Equity Curve — {result.symbol} ({result.timeframe})")
        for row in range(height, -1, -1):
            threshold = lo + (rng * row / height)
            line = ""
            for v in sampled:
                line += "#" if v >= threshold else " "
            print(f"  {'':<10} |{line}")
        print(f"  {'':<10} +{'-' * cols}")

    def show_charts(self, result: BacktestResult):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.gridspec as gridspec
        except ImportError:
            print("Install matplotlib: pip install matplotlib --break-system-packages")
            return
        eq_times  = [ep.timestamp[:10] for ep in result.equity_curve]
        eq_vals   = [ep.equity         for ep in result.equity_curve]
        dd_vals   = [ep.drawdown        for ep in result.equity_curve]
        ret_vals  = [ep.daily_ret       for ep in result.equity_curve]
        n       = len(eq_times)
        step    = max(1, n // 300)
        times   = eq_times[::step]
        equities= eq_vals[::step]
        dds     = dd_vals[::step]
        rets    = ret_vals[::step]
        x       = range(len(times))
        fig = plt.figure(figsize=(14, 9), facecolor="#0f172a")
        stop_label = "2-Bar Trail" if result.stop_mode == STOP_TWO_BAR else "Standard %"
        fig.suptitle(
            f"Backtest: {result.symbol}  |  {result.strategy_name}  |  "
            f"{result.timeframe}  |  Stop: {stop_label}  |  "
            f"Return: {result.total_return_pct:+.2f}%  |  Sharpe: {result.sharpe_ratio:.2f}",
            color="white", fontsize=12, y=0.98
        )
        gs  = gridspec.GridSpec(3, 1, figure=fig, hspace=0.45, height_ratios=[3, 1.5, 1.5])
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])
        ax3 = fig.add_subplot(gs[2])
        for ax in (ax1, ax2, ax3):
            ax.set_facecolor("#1e293b")
            ax.tick_params(colors="white", labelsize=7)
            ax.spines[:].set_color("#334155")
        ax1.plot(x, equities, color="#8b5cf6", linewidth=1.5)
        ax1.fill_between(x, result.starting_capital, equities,
                         where=[e >= result.starting_capital for e in equities],
                         alpha=0.2, color="#10b981")
        ax1.fill_between(x, result.starting_capital, equities,
                         where=[e < result.starting_capital for e in equities],
                         alpha=0.2, color="#ef4444")
        ax1.axhline(result.starting_capital, color="#475569", linewidth=0.8, linestyle="--")
        ax1.set_ylabel("Portfolio Value ($)", color="white", fontsize=8)
        ax1.set_title("Equity Curve", color="#94a3b8", fontsize=9, pad=4)
        ax2.fill_between(x, 0, dds, color="#ef4444", alpha=0.6)
        ax2.plot(x, dds, color="#ef4444", linewidth=0.8)
        ax2.set_ylabel("Drawdown %", color="white", fontsize=8)
        ax2.set_title("Drawdown", color="#94a3b8", fontsize=9, pad=4)
        bar_colors = ["#10b981" if r >= 0 else "#ef4444" for r in rets]
        ax3.bar(x, rets, color=bar_colors, alpha=0.7, width=1.0)
        ax3.axhline(0, color="#475569", linewidth=0.6)
        ax3.set_ylabel("Bar Return %", color="white", fontsize=8)
        ax3.set_title("Returns per Bar", color="#94a3b8", fontsize=9, pad=4)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.show()

    def export_trades_csv(self, result: BacktestResult,
                          path: str = None) -> str:
        """Export every trade in result to CSV for manual analysis in Excel."""
        import csv
        if path is None:
            path = (f"exports/backtest_{result.symbol}_{result.strategy_name}"
                    f"_{result.timeframe}_{result.stop_mode}_trades.csv")
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        _fields = [
            "symbol", "strategy_name", "timeframe", "direction",
            "entry_date", "exit_date", "bars_held",
            "entry_price", "exit_price", "pnl", "pnl_pct", "fees",
            "exit_reason", "signal_score",
            "entry_mode", "regime", "entry_rsi", "entry_adx", "entry_atr",
        ]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_fields)
            writer.writeheader()
            for t in result.trades:
                writer.writerow({
                    "symbol":        result.symbol,
                    "strategy_name": t.strategy_name,
                    "timeframe":     result.timeframe,
                    "direction":     t.direction,
                    "entry_date":    t.entry_date,
                    "exit_date":     t.exit_date,
                    "bars_held":     t.bars_held,
                    "entry_price":   t.entry_price,
                    "exit_price":    t.exit_price,
                    "pnl":           t.pnl,
                    "pnl_pct":       t.pnl_pct,
                    "fees":          t.fees,
                    "exit_reason":   t.exit_reason,
                    "signal_score":  t.signal_score,
                    "entry_mode":    getattr(t, "entry_mode", ""),
                    "regime":        getattr(t, "regime",     ""),
                    "entry_rsi":     getattr(t, "entry_rsi",  ""),
                    "entry_adx":     getattr(t, "entry_adx",  ""),
                    "entry_atr":     getattr(t, "entry_atr",  ""),
                })
        logger.info(f"Exported trades CSV -> {path}  ({len(result.trades)} trades)")
        return path

    def export_trades_csv_combined(self, results: List[BacktestResult],
                                    path: str = None) -> str:
        """Export all trades from multiple results into one combined CSV file."""
        import csv
        if path is None:
            strategy = results[0].strategy_name if results else "unknown"
            path = f"exports/backtest_all_{strategy}_trades.csv"
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        _fields = [
            "symbol", "strategy_name", "timeframe", "direction",
            "entry_date", "exit_date", "bars_held",
            "entry_price", "exit_price", "pnl", "pnl_pct", "fees",
            "exit_reason", "signal_score",
            "entry_mode", "regime", "entry_rsi", "entry_adx", "entry_atr",
        ]
        total = 0
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_fields)
            writer.writeheader()
            for result in results:
                for t in result.trades:
                    writer.writerow({
                        "symbol":        result.symbol,
                        "strategy_name": t.strategy_name,
                        "timeframe":     result.timeframe,
                        "direction":     t.direction,
                        "entry_date":    t.entry_date,
                        "exit_date":     t.exit_date,
                        "bars_held":     t.bars_held,
                        "entry_price":   t.entry_price,
                        "exit_price":    t.exit_price,
                        "pnl":           t.pnl,
                        "pnl_pct":       t.pnl_pct,
                        "fees":          t.fees,
                        "exit_reason":   t.exit_reason,
                        "signal_score":  t.signal_score,
                        "entry_mode":    getattr(t, "entry_mode", ""),
                        "regime":        getattr(t, "regime",     ""),
                        "entry_rsi":     getattr(t, "entry_rsi",  ""),
                        "entry_adx":     getattr(t, "entry_adx",  ""),
                        "entry_atr":     getattr(t, "entry_atr",  ""),
                    })
                    total += 1
        logger.info(f"Exported combined trades CSV -> {path}  ({total} trades, {len(results)} symbols)")
        return path

    def export_json(self, result: BacktestResult, path: str = None) -> str:
        import json
        step = max(1, len(result.equity_curve) // 500)
        sampled = result.equity_curve[::step]
        payload = {
            "symbol":           result.symbol,
            "strategy":         result.strategy_name,
            "timeframe":        result.timeframe,
            "stop_mode":        result.stop_mode,
            "start_date":       result.start_date,
            "end_date":         result.end_date,
            "starting_capital": result.starting_capital,
            "ending_capital":   result.ending_capital,
            "total_return_pct": result.total_return_pct,
            "win_rate":         result.win_rate,
            "total_trades":     result.total_trades,
            "winning_trades":   result.winning_trades,
            "losing_trades":    result.losing_trades,
            "profit_factor":    result.profit_factor,
            "max_drawdown_pct": result.max_drawdown_pct,
            "sharpe_ratio":     result.sharpe_ratio,
            "sortino_ratio":    result.sortino_ratio,
            "calmar_ratio":     result.calmar_ratio,
            "friction": {
                "commission_pct_per_leg": result.commission_pct,
                "slippage_pct_per_leg":   result.slippage_pct,
                "round_trip_pct":         round((result.commission_pct + result.slippage_pct) * 2, 4),
                "total_fees_paid":        result.fees_paid,
                "friction_free":          result.fees_paid == 0.0,
            },
            "equity_curve": [
                {"t": ep.timestamp[:16], "e": ep.equity,
                 "d": ep.drawdown,       "r": ep.daily_ret}
                for ep in sampled
            ],
        }
        if path is None:
            path = f"exports/backtest_{result.symbol}_{result.strategy_name}_{result.timeframe}_{result.stop_mode}.json"
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Exported JSON -> {path}")
        return path


# ===========================================================================
# Analytics helpers — mode / side / exit-reason breakdown
# ===========================================================================

def _trade_stats(subset: List[BacktestTrade]) -> Dict:
    """Compute standard stats for any sub-list of trades."""
    if not subset:
        return {"n": 0, "wins": 0, "wr": 0.0, "pf": 0.0,
                "pnl": 0.0, "avg_pct": 0.0}
    wins       = [t for t in subset if t.pnl > 0]
    losses     = [t for t in subset if t.pnl <= 0]
    gross_win  = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    return {
        "n":       len(subset),
        "wins":    len(wins),
        "wr":      len(wins) / len(subset) * 100,
        "pf":      (gross_win / gross_loss if gross_loss
                    else (999.0 if gross_win > 0 else 0.0)),
        "pnl":     sum(t.pnl for t in subset),
        "avg_pct": float(np.mean([t.pnl_pct for t in subset])),
    }


def _fmt_stat_row(label: str, s: Dict, low_sample_n: int = 5) -> str:
    if s["n"] == 0:
        return f"    {label}: no trades"
    warn   = "  !! LOW SAMPLE" if s["n"] < low_sample_n else ""
    pf_str = f"{s['pf']:.2f}" if s["pf"] < 999 else "inf"
    return (f"    {label}: {s['n']:>4} trades | WR {s['wr']:>5.1f}% | "
            f"PF {pf_str:>5} | PnL ${s['pnl']:>+9.2f} | "
            f"Avg {s['avg_pct']:>+6.2f}%{warn}")


def _print_adaptive_diagnostics(d: dict, width: int = 62):
    """
    Print per-symbol AdaptiveRegime diagnostics after the main report block.
    Answers: why didn't trend/mean_rev fire more often?
    """
    thin = "-" * width
    bars  = max(d.get("bars_analyzed", 1), 1)
    trend = d.get("trend_bars", 0)
    rang  = d.get("range_bars", 0)
    trans = d.get("transition_bars", 0)

    print(f"  {thin}")
    print(f"  ADAPTIVE REGIME DIAGNOSTICS")
    print(f"  {thin}")

    # Regime distribution
    print(f"  Regime bars  : {bars} analyzed  |  "
          f"trend={trend} ({trend/bars*100:.0f}%)  "
          f"range={rang} ({rang/bars*100:.0f}%)  "
          f"transit={trans} ({trans/bars*100:.0f}%)")

    # Trend mode
    t_sigs  = d.get("trend_long", 0) + d.get("trend_short", 0)
    t_vol   = d.get("trend_vol_fail", 0)
    t_ema   = d.get("trend_ema_fail", 0)
    t_don   = d.get("trend_don_fail", 0)
    t_rsi   = d.get("trend_rsi_fail", 0)
    if trend > 0:
        print(f"  {thin}")
        print(f"  TREND MODE  ({trend} bars)  ->  {t_sigs} signal(s) "
              f"[{d.get('trend_long',0)}L / {d.get('trend_short',0)}S]")
        print(f"    Blockers : vol={t_vol}  ema_align={t_ema}  "
              f"donchian={t_don}  rsi={t_rsi}")
        top_t = max({"vol": t_vol, "ema": t_ema, "donchian": t_don, "rsi": t_rsi}.items(),
                    key=lambda x: x[1])
        if top_t[1] > 0:
            print(f"    Top blocker: {top_t[0]} ({top_t[1]} bars)")

    # Mean-rev mode
    mr_sigs = d.get("mean_long", 0) + d.get("mean_short", 0)
    mr_vol  = d.get("mean_vol_fail", 0)
    mr_bb   = d.get("mean_bb_fail", 0)
    mr_rsi  = d.get("mean_rsi_fail", 0)
    if rang > 0:
        print(f"  {thin}")
        print(f"  MEAN-REV MODE  ({rang} bars)  ->  {mr_sigs} signal(s) "
              f"[{d.get('mean_long',0)}L / {d.get('mean_short',0)}S]")
        print(f"    Blockers : vol={mr_vol}  bb_touch={mr_bb}  rsi={mr_rsi}")
        top_mr = max({"vol": mr_vol, "bb_touch": mr_bb, "rsi": mr_rsi}.items(),
                     key=lambda x: x[1])
        if top_mr[1] > 0:
            print(f"    Top blocker: {top_mr[0]} ({top_mr[1]} bars)")


def _print_mode_breakdown(trades: List[BacktestTrade], width: int = 62):
    """
    Print per-mode, per-side, and exit-reason analytics for a trade list.
    Called by print_report() and print_portfolio_summary().
    Only prints the mode section when any trade has entry_mode populated.
    """
    thin = "-" * width

    # ── Mode breakdown ────────────────────────────────────────────────────
    trend_trades    = [t for t in trades if getattr(t, "entry_mode", "") == "trend"]
    mean_rev_trades = [t for t in trades if getattr(t, "entry_mode", "") == "mean_rev"]
    has_mode        = bool(trend_trades or mean_rev_trades)

    if has_mode:
        print(f"  {thin}")
        print(f"  MODE BREAKDOWN")
        print(_fmt_stat_row("trend   ", _trade_stats(trend_trades),    low_sample_n=5))
        print(_fmt_stat_row("mean_rev", _trade_stats(mean_rev_trades),  low_sample_n=5))

    # ── Side breakdown ────────────────────────────────────────────────────
    longs  = [t for t in trades if t.direction == "long"]
    shorts = [t for t in trades if t.direction == "short"]
    print(f"  {thin}")
    print(f"  SIDE BREAKDOWN")
    print(_fmt_stat_row("long ", _trade_stats(longs),  low_sample_n=3))
    print(_fmt_stat_row("short", _trade_stats(shorts), low_sample_n=3))

    # ── Exit reason breakdown ─────────────────────────────────────────────
    exit_pnls: Dict[str, list] = {}
    for t in trades:
        exit_pnls.setdefault(t.exit_reason, []).append(t.pnl_pct)

    print(f"  {thin}")
    print(f"  EXIT REASON BREAKDOWN")
    for reason, pcts in sorted(exit_pnls.items(), key=lambda x: -len(x[1])):
        avg_pct = float(np.mean(pcts))
        print(f"    {reason:<34}: {len(pcts):>4} | avg {avg_pct:>+6.2f}%")


# ===========================================================================
# Portfolio summary
# ===========================================================================

def print_portfolio_summary(results: List[BacktestResult]):
    if not results:
        return
    friction_free = all(r.commission_pct == 0 and r.slippage_pct == 0 for r in results)
    print(f"\n{'='*72}")
    print(f"  ISOLATED SYMBOL RESULTS — {len(results)} symbol(s)")
    print(f"  NOTE: Each symbol ran with full starting capital independently.")
    print(f"        This is NOT a shared-capital portfolio simulation.")
    print(f"        Averages below do not represent a real portfolio return.")
    if friction_free:
        print(f"  FRICTION: NONE — results are optimistic (no fees or slippage).")
    else:
        total_fees = sum(r.fees_paid for r in results)
        print(f"  FRICTION: applied — total fees across all symbols: ${total_fees:,.2f}")
    print(f"  {'Symbol':<8} {'Return':>8} {'WinRate':>8} {'PF':>6} "
          f"{'MaxDD':>8} {'Sharpe':>7} {'Trades':>9} {'Stop':>10}")
    print(f"  {'-'*72}")
    for r in sorted(results, key=lambda x: x.total_return_pct, reverse=True):
        # Build an accurate stop label from actual stop mode fields,
        # not just the legacy stop_mode flag (which doesn't capture structural stops).
        if r.stop_mode == STOP_TWO_BAR:
            stop_label = "2-Bar"
        elif r.initial_stop_mode == "signal_structural":
            stop_label = "ATR-struct"
        elif r.trail_mode == "two_bar":
            stop_label = "2-Bar-trail"
        else:
            stop_label = "Fixed%"
        sample_warn = " !!LOW" if r.total_trades < 10 else ""
        print(f"  {r.symbol:<8} {r.total_return_pct:>+7.1f}% "
              f"{r.win_rate:>7.1f}% {r.profit_factor:>6.2f} "
              f"{r.max_drawdown_pct:>7.1f}% {r.sharpe_ratio:>7.2f} "
              f"{r.total_trades:>5}{sample_warn:<4} {stop_label:>10}")

    all_rets = [r.total_return_pct for r in results]
    all_wrs  = [r.win_rate         for r in results]
    all_dds  = [r.max_drawdown_pct for r in results]
    all_shs  = [r.sharpe_ratio     for r in results]
    # Exclude inf profit-factor outliers from averages and medians
    pf_vals  = [r.profit_factor for r in results if r.profit_factor < 999]

    avgs = {
        "ret": float(np.mean(all_rets)),
        "wr":  float(np.mean(all_wrs)),
        "pf":  float(np.mean(pf_vals)) if pf_vals else 0.0,
        "dd":  float(np.mean(all_dds)),
        "sh":  float(np.mean(all_shs)),
    }
    meds = {
        "ret": float(np.median(all_rets)),
        "wr":  float(np.median(all_wrs)),
        "pf":  float(np.median(pf_vals)) if pf_vals else 0.0,
        "dd":  float(np.median(all_dds)),
        "sh":  float(np.median(all_shs)),
    }
    print(f"  {'-'*72}")
    print(f"  {'AVG':<8} {avgs['ret']:>+7.1f}% "
          f"{avgs['wr']:>7.1f}% {avgs['pf']:>6.2f} "
          f"{avgs['dd']:>7.1f}% {avgs['sh']:>7.2f}   (mean — excl. inf PF)")
    print(f"  {'MED':<8} {meds['ret']:>+7.1f}% "
          f"{meds['wr']:>7.1f}% {meds['pf']:>6.2f} "
          f"{meds['dd']:>7.1f}% {meds['sh']:>7.2f}   (median — not skewed by outliers)")
    print(f"  !!LOW = fewer than 10 trades -- results unreliable")
    print(f"{'='*72}")

    # ── Adaptive regime aggregate breakdown ───────────────────────────────
    all_trades = [t for r in results for t in r.trades]
    has_mode   = any(getattr(t, "entry_mode", "") for t in all_trades)
    if has_mode:
        strategy_name = results[0].strategy_name if results else "adaptive_regime"
        total_trades  = len(all_trades)
        print(f"\n{'='*72}")
        print(f"  {strategy_name.upper()} — AGGREGATE BREAKDOWN")
        print(f"  {total_trades} total trades across {len(results)} symbol(s)")
        _print_mode_breakdown(all_trades, width=72)
        print(f"{'='*72}")

        # ── Aggregate diagnostics footer ──────────────────────────────────
        agg_diag_results = [r for r in results
                            if getattr(r, "diagnostics", {})
                            and r.strategy_name == "adaptive_regime"]
        if agg_diag_results:
            # Sum all counters across symbols
            agg: Dict = {}
            for r in agg_diag_results:
                for k, v in r.diagnostics.items():
                    agg[k] = agg.get(k, 0) + v
            print(f"\n  AGGREGATE DIAGNOSTICS  ({len(agg_diag_results)} symbol(s))")
            bars  = max(agg.get("bars_analyzed", 1), 1)
            trend = agg.get("trend_bars", 0)
            rang  = agg.get("range_bars", 0)
            trans = agg.get("transition_bars", 0)
            print(f"  Regime: trend={trend} ({trend/bars*100:.0f}%)  "
                  f"range={rang} ({rang/bars*100:.0f}%)  "
                  f"transit={trans} ({trans/bars*100:.0f}%)")
            t_sigs = agg.get("trend_long", 0) + agg.get("trend_short", 0)
            mr_sigs = agg.get("mean_long", 0) + agg.get("mean_short", 0)
            print(f"  Signals: trend={t_sigs} "
                  f"[{agg.get('trend_long',0)}L/{agg.get('trend_short',0)}S]  "
                  f"mean_rev={mr_sigs} "
                  f"[{agg.get('mean_long',0)}L/{agg.get('mean_short',0)}S]")
            print(f"  Trend blockers  : vol={agg.get('trend_vol_fail',0)}  "
                  f"ema={agg.get('trend_ema_fail',0)}  "
                  f"don={agg.get('trend_don_fail',0)}  "
                  f"rsi={agg.get('trend_rsi_fail',0)}")
            print(f"  Mean-rev blockers: vol={agg.get('mean_vol_fail',0)}  "
                  f"bb_touch={agg.get('mean_bb_fail',0)}  "
                  f"rsi={agg.get('mean_rsi_fail',0)}")
            print(f"{'='*72}")
    print()


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
        )
    except ImportError:
        pass

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Backtest trading strategy")
    parser.add_argument("--symbol",    default="AAPL")
    parser.add_argument("--days",      type=int, default=180)
    parser.add_argument("--capital",   type=float, default=10_000.0)
    parser.add_argument("--tf", default="1h", choices=["5m", "15m", "1h", "1d"])
    parser.add_argument("--strategy",  default=None)
    parser.add_argument("--all",       action="store_true")
    parser.add_argument("--chart",     action="store_true")
    parser.add_argument("--ascii",     action="store_true")
    parser.add_argument("--export",    action="store_true")
    parser.add_argument("--stop",      default="standard",
                        choices=["standard", "two_bar"],
                        help="Stop loss mode: standard (fixed %%) or two_bar (N-bar trailing)")
    parser.add_argument("--lookback",  type=int, default=2,
                        help="Lookback bars N for two_bar stop (default 2, range 1-20)")
    parser.add_argument("--asset-class", default="stock", choices=["stock", "crypto"],
                        help="Asset class — affects default friction assumptions")
    parser.add_argument("--no-fees",   action="store_true",
                        help="Run with zero commission and zero slippage (optimistic baseline)")
    # ── Analytics / filtering ────────────────────────────────────────────
    parser.add_argument("--mode",      default="all",
                        choices=["all", "trend", "mean_rev"],
                        help="Filter entries by adaptive_regime mode (all = no filter)")
    parser.add_argument("--side",      default="all",
                        choices=["all", "long", "short"],
                        help="Filter entries by direction")
    parser.add_argument("--export-trades", action="store_true",
                        help="Export per-trade CSV after each backtest run")
    # ── Stop architecture ────────────────────────────────────────────────
    parser.add_argument("--initial-stop", default="auto",
                        choices=["auto", "percent", "signal_structural", "two_bar"],
                        help=("Initial stop source: auto=use --stop default | "
                              "signal_structural=ATR stop from signal metadata | "
                              "two_bar=N-bar structural | percent=fixed %%"))
    parser.add_argument("--trail-stop",   default="auto",
                        choices=["auto", "percent", "two_bar", "none"],
                        help=("Trail engine: auto=use --stop default | "
                              "two_bar=N-bar trail | percent=%% ratchet | none=no trail"))
    args = parser.parse_args()

    # Friction override: --no-fees forces both to 0.0
    _commission = 0.0 if args.no_fees else None   # None = use config default
    _slippage   = 0.0 if args.no_fees else None

    clear_cancel()   # ensure no stale cancel flag from a previous interrupted run
    backtester = Backtester(starting_capital=args.capital)

    if args.all:
        if args.asset_class == "crypto":
            symbols = config.CRYPTO_WATCHLIST[:15]
        else:
            symbols = config.STOCK_WATCHLIST[:15]
        results = backtester.run_all(
            symbols,
            strategy_name     = args.strategy,
            days              = args.days,
            starting_capital  = args.capital,
            timeframe         = args.tf,
            asset_class       = args.asset_class,
            stop_mode         = args.stop,
            two_bar_lookback  = args.lookback,
            commission_pct    = _commission,
            slippage_pct      = _slippage,
            initial_stop_mode = args.initial_stop,
            trail_mode        = args.trail_stop,
            entry_mode_filter = args.mode,
            entry_side_filter = args.side,
        )
        for r in results:
            backtester.print_report(r)
            if args.ascii:
                backtester.print_ascii_chart(r)
            if args.export:
                backtester.export_json(r)
            if args.export_trades:
                backtester.export_trades_csv(r)
        print_portfolio_summary(results)
        if args.export_trades and results:
            backtester.export_trades_csv_combined(results)
    else:
        if args.strategy:
            result = backtester.run_strategy(
                args.symbol, args.strategy, args.days, args.capital, args.tf,
                asset_class       = args.asset_class,
                stop_mode         = args.stop,
                two_bar_lookback  = args.lookback,
                commission_pct    = _commission,
                slippage_pct      = _slippage,
                initial_stop_mode = args.initial_stop,
                trail_mode        = args.trail_stop,
                entry_mode_filter = args.mode,
                entry_side_filter = args.side,
            )
        else:
            result = backtester.run(
                args.symbol, args.days, args.capital, args.tf,
                asset_class       = args.asset_class,
                stop_mode         = args.stop,
                two_bar_lookback  = args.lookback,
                commission_pct    = _commission,
                slippage_pct      = _slippage,
                initial_stop_mode = args.initial_stop,
                trail_mode        = args.trail_stop,
                entry_mode_filter = args.mode,
                entry_side_filter = args.side,
            )

        if result:
            backtester.print_report(result)
            if args.ascii:
                backtester.print_ascii_chart(result)
            if args.chart:
                backtester.show_charts(result)
            if args.export:
                backtester.export_json(result)
            if args.export_trades:
                backtester.export_trades_csv(result)
        else:
            print("Backtest returned no results — check symbol and timeframe.")
