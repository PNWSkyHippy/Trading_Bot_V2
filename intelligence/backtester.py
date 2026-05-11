"""
=============================================================
  BACKTESTING ENGINE  v2.1
  Tests strategies against historical data BEFORE risking
  real money.  Uses yfinance for free OHLCV history.

  Timeframe support:
    5m   — up to 60 days   (best for Scalp Master, RSI)
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
    "5m":  {"interval": "5m",  "max_days": 30,   "bars_per_day": 78,  "annualise": 252 * 78},
    "1h":  {"interval": "1h",  "max_days": 729,  "bars_per_day": 7,   "annualise": 252 * 7},
    "1d":  {"interval": "1d",  "max_days": 3650, "bars_per_day": 1,   "annualise": 252},
}

# Stop loss mode constants
STOP_STANDARD = "standard"   # Fixed % stop (existing behavior)
STOP_TWO_BAR  = "two_bar"    # N-bar trailing stop (Pine Script port)

# Max simultaneous positions (mirrors live bot)
MAX_OPEN_POSITIONS = 5


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
    stop_mode:        str = "standard"   # 'standard' or 'two_bar'
    fees_paid:        float = 0.0        # total round-trip friction deducted
    commission_pct:   float = 0.0        # per-leg commission used
    slippage_pct:     float = 0.0        # per-leg slippage used
    trades:           List[BacktestTrade]  = field(default_factory=list)
    equity_curve:     List[EquityPoint]    = field(default_factory=list)


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
    # Data fetching
    # -----------------------------------------------------------------------

    def fetch_history(self, symbol: str, days: int = 365,
                      timeframe: str = "1h") -> Optional[pd.DataFrame]:
        cfg     = TF_CONFIG.get(timeframe, TF_CONFIG["1h"])
        tf      = cfg["interval"]
        max_d   = cfg["max_days"]
        days    = min(days, max_d)
        fetch_days = days + 5
        end   = datetime.now()
        start = end - timedelta(days=fetch_days)
        logger.info(f"Fetching {days}d of {tf} data for {symbol}...")
        try:
            ticker = self.yf.Ticker(symbol)
            df = ticker.history(
                start       = start.strftime("%Y-%m-%d"),
                end         = end.strftime("%Y-%m-%d"),
                interval    = tf,
                auto_adjust = True,
            )
            if df is None or df.empty:
                logger.error(f"No data returned for {symbol}")
                return None
            df.columns = [c.lower() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            cutoff = end - timedelta(days=days)
            df = df[df.index >= pd.Timestamp(cutoff)]
            if len(df) < 30:
                logger.error(f"Only {len(df)} bars for {symbol} — need >=30")
                return None
            logger.info(f"  -> {len(df)} bars  ({df.index[0].date()} - {df.index[-1].date()})")
            return df
        except Exception as e:
            logger.error(f"fetch_history failed for {symbol}: {e}")
            return None

    def fetch_history_crypto(self, symbol: str, days: int = 30,
                              timeframe: str = "1h") -> Optional[pd.DataFrame]:
        yf_symbol = symbol.replace("/", "-")
        cfg    = TF_CONFIG.get(timeframe, TF_CONFIG["1h"])
        tf     = cfg["interval"]
        max_d  = cfg["max_days"]
        days   = min(days, max_d)
        fetch_days = days + 5
        end   = datetime.now()
        start = end - timedelta(days=fetch_days)
        logger.info(f"Fetching {days}d of {tf} crypto data for {yf_symbol} via yfinance...")
        try:
            ticker = self.yf.Ticker(yf_symbol)
            df = ticker.history(
                start       = start.strftime("%Y-%m-%d"),
                end         = end.strftime("%Y-%m-%d"),
                interval    = tf,
                auto_adjust = True,
            )
            if df is None or df.empty:
                logger.error(f"No yfinance data returned for {yf_symbol}")
                return None
            df.columns = [c.lower() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            cutoff = end - timedelta(days=days)
            df = df[df.index >= pd.Timestamp(cutoff)]
            if len(df) < 30:
                logger.error(f"Only {len(df)} bars for {yf_symbol} — need >=30")
                return None
            logger.info(f"  -> {len(df)} bars  ({df.index[0].date()} - {df.index[-1].date()})")
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
            rsi       = self.ta.rsi(close, rsi_period).iloc[-1]
            macd_df   = self.ta.macd(close)
            macd_hist = macd_df["hist"].iloc[-1]
            macd_prev = macd_df["hist"].iloc[-2] if len(macd_df) > 1 else 0
            ema_f     = self.ta.ema(close, ema_fast).iloc[-1]
            ema_s     = self.ta.ema(close, ema_slow).iloc[-1]
            ema_t     = self.ta.ema(close, ema_trend).iloc[-1]
            bb        = self.ta.bollinger_bands(close, bb_period, bb_std)
            bb_pct    = bb["pct_b"].iloc[-1]
            vol_ratio = self.ta.volume_ratio(volume).iloc[-1]
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
            "ema_crossover":      ("strategies.ema_crossover",       "EMACrossover"),
            "mean_reversion":     ("strategies.mean_reversion",      "MeanReversion"),
            "scalp_master":       ("strategies.scalp_master",        "ScalpMaster"),
            "swing_trader":       ("strategies.swing_trader",        "SwingTrader"),
            "grid_bot":           ("strategies.grid_bot",            "GridBot"),
            "dca_accumulator":    ("strategies.dca_accumulator",     "DCAAccumulator"),
            "vwap_momentum":      ("strategies.vwap_momentum",       "VWAPMomentum"),
            "hammer_reversal":    ("strategies.hammer_reversal",     "HammerReversal"),
            "orb_breakout":       ("strategies.orb_breakout",        "ORBBreakout"),
            "adaptive_regime":    ("strategies.adaptive_regime",     "AdaptiveRegime"),
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
        """Standard fixed % stop with trailing. Uses intrabar low/high for stop check."""
        d     = trade["direction"]
        sl    = trade["current_sl"]
        tp    = trade["current_tp"]
        low   = float(row["low"])
        high  = float(row["high"])
        price = float(row["close"])
        if d == "long":
            if low <= sl:
                return "stop_loss"
            if price >= tp:
                return "take_profit"
            new_sl = price * (1 - trailing_gap_pct)
            if new_sl > sl:
                trade["current_sl"] = new_sl
        else:
            if high >= sl:
                return "stop_loss"
            if price <= tp:
                return "take_profit"
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

        # Step 3: Take profit check (uses close price)
        tp = trade["current_tp"]
        if direction == "long" and price >= tp:
            return "take_profit"
        if direction == "short" and price <= tp:
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
                  slippage_pct:   float = None) -> BacktestResult:
        """
        commission_pct / slippage_pct: per-leg friction (%).
        None → use config defaults for the asset class.
        Pass 0.0 for both to reproduce friction-free (optimistic) results.
        """
        cfg              = TF_CONFIG.get(timeframe, TF_CONFIG["1h"])
        annualise_factor = cfg["annualise"]

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

        # Initialise the 2-bar stop engine if needed
        two_bar_engine = TwoBarStop(two_bar_lookback) if stop_mode == STOP_TWO_BAR else None

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

        daily_pnl          = 0.0
        consecutive_losses = 0
        trading_halted     = False
        last_date          = None
        peak_equity        = starting_capital
        min_bars           = min(120, max(20, len(df) // 4))

        for i in range(min_bars, len(df)):
            row          = df.iloc[i]
            current_date = str(df.index[i])[:10]
            price        = float(row["close"])

            if current_date != last_date:
                daily_pnl          = 0.0
                trading_halted     = False
                consecutive_losses = 0
                last_date          = current_date

            # --- Check exits on all open trades ---
            still_open = []
            for trade in open_trades:

                if stop_mode == STOP_TWO_BAR:
                    exit_reason = self._check_exit_two_bar(
                        trade, df, i, default_tp_pct, two_bar_engine
                    )
                else:
                    exit_reason = self._check_exit_standard(
                        trade, row, trailing_gap_pct, default_tp_pct
                    )

                # ── Strategy-specific exit hook ───────────────────────────
                # Fires AFTER standard SL/TP so the stop remains a hard gate.
                # Only strategies that override check_custom_exit() are affected
                # (all others return None from the BaseStrategy stub).
                if exit_reason is None and strategy_obj is not None:
                    window = df.iloc[max(0, i - 150): i + 1]
                    exit_reason = strategy_obj.check_custom_exit(
                        trade["symbol"],
                        window,
                        trade["direction"],
                        trade.get("entry_metadata", {}),
                    )

                if exit_reason:
                    pnl, bt_trade = self._close_trade(
                        trade, price, exit_reason, i, df,
                        strategy_name, stop_mode
                    )
                    # Deduct round-trip friction (entry leg + exit leg).
                    # Applied to position_value so cost scales with trade size.
                    round_trip_cost = bt_trade.position_value * friction_per_leg * 2
                    pnl            -= round_trip_cost
                    total_fees_paid += round_trip_cost
                    bt_trade.fees   = round(round_trip_cost, 4)
                    bt_trade.pnl    = round(pnl, 4)
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

            # --- Mark-to-market equity ---
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

            if trading_halted or len(open_trades) >= MAX_OPEN_POSITIONS:
                continue

            # --- Signal generation ---
            signal_direction = "none"
            signal_score     = 0.0
            sl_pct           = default_sl_pct
            tp_pct           = default_tp_pct

            signal_meta: dict = {}
            if strategy_obj is not None:
                window = df.iloc[max(0, i - 150): i + 1].copy()
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

            already_in = any(
                t["symbol"] == symbol and t["direction"] == signal_direction
                for t in open_trades
            )
            if already_in:
                continue

            position_value = capital * max_position_pct
            if position_value < 1.0 or price <= 0:
                continue
            quantity = position_value / price

            # --- Calculate initial stop & take profit ---
            if stop_mode == STOP_TWO_BAR:
                # Initial stop from 2-bar engine (structure-based)
                sl = two_bar_engine.initial_stop(df, i, signal_direction)
                # Take profit: use fixed % from strategy
                if signal_direction == "long":
                    tp = price * (1 + tp_pct)
                else:
                    tp = price * (1 - tp_pct)
            else:
                # Prefer structural_stop_price from signal metadata when present.
                # Strategies like adaptive_regime embed an ATR-based absolute stop
                # price instead of a percentage. Using it here means the simulation
                # matches the live bot's behaviour exactly.
                structural_stop = signal_meta.get("structural_stop_price")
                if structural_stop and structural_stop > 0:
                    if signal_direction == "long" and structural_stop < price:
                        sl = structural_stop
                    elif signal_direction == "short" and structural_stop > price:
                        sl = structural_stop
                    else:
                        # structural_stop is on the wrong side — fall back to %
                        sl = (price * (1 - sl_pct) if signal_direction == "long"
                              else price * (1 + sl_pct))
                else:
                    sl = (price * (1 - sl_pct) if signal_direction == "long"
                          else price * (1 + sl_pct))

                tp = (price * (1 + tp_pct) if signal_direction == "long"
                      else price * (1 - tp_pct))

            open_trades.append({
                "symbol":         symbol,
                "direction":      signal_direction,
                "entry_idx":      i,
                "entry_date":     str(df.index[i]),
                "entry_price":    price,
                "quantity":       quantity,
                "position_value": position_value,
                "stop_loss":      sl,
                "take_profit":    tp,
                "signal_score":   signal_score,
                "current_sl":     sl,
                "current_tp":     tp,
                "entry_metadata": signal_meta,   # strategy exit hook reads this
            })

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

        return self._compile_results(
            symbol, df, closed_trades, equity_curve,
            starting_capital, capital,
            strategy_name, timeframe, annualise_factor,
            stop_mode,
            fees_paid      = round(total_fees_paid, 2),
            commission_pct = commission_pct,
            slippage_pct   = slippage_pct,
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
            slippage_pct:   float = None) -> Optional[BacktestResult]:
        capital = starting_capital or self.starting_capital
        if asset_class == "crypto":
            df = self.fetch_history_crypto(symbol, days, timeframe)
        else:
            df = self.fetch_history(symbol, days, timeframe)
        if df is None or len(df) < 30:
            return None
        return self._simulate(symbol, df, "default", None, capital, timeframe,
                              stop_mode, two_bar_lookback,
                              asset_class=asset_class,
                              commission_pct=commission_pct,
                              slippage_pct=slippage_pct)

    def run_strategy(self, symbol: str, strategy_name: str,
                     days: int = 365,
                     starting_capital: float = None,
                     timeframe: str = "1h",
                     asset_class: str = "stock",
                     stop_mode: str = STOP_STANDARD,
                     two_bar_lookback: int = 2,
                     commission_pct: float = None,
                     slippage_pct:   float = None) -> Optional[BacktestResult]:
        capital = starting_capital or self.starting_capital
        if asset_class == "crypto":
            df = self.fetch_history_crypto(symbol, days, timeframe)
        else:
            df = self.fetch_history(symbol, days, timeframe)
        if df is None or len(df) < 30:
            return None
        try:
            strategy_obj = self._load_strategy(strategy_name)
            if strategy_obj is None:
                logger.error(f"Unknown strategy: {strategy_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to load strategy {strategy_name}: {e}")
            return None
        return self._simulate(
            symbol, df, strategy_name, strategy_obj, capital, timeframe,
            stop_mode, two_bar_lookback,
            asset_class=asset_class,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
        )

    def run_all(self, symbols: List[str], strategy_name: str = None,
                days: int = 365, starting_capital: float = None,
                timeframe: str = "1h",
                asset_class: str = "stock",
                stop_mode: str = STOP_STANDARD,
                two_bar_lookback: int = 2,
                commission_pct: float = None,
                slippage_pct:   float = None) -> List[BacktestResult]:
        results = []
        for sym in symbols:
            if strategy_name:
                r = self.run_strategy(sym, strategy_name, days,
                                      starting_capital, timeframe, asset_class,
                                      stop_mode, two_bar_lookback,
                                      commission_pct=commission_pct,
                                      slippage_pct=slippage_pct)
            else:
                r = self.run(sym, days, starting_capital, timeframe, asset_class,
                             stop_mode, two_bar_lookback,
                             commission_pct=commission_pct,
                             slippage_pct=slippage_pct)
            if r:
                results.append(r)
        return results

    # -----------------------------------------------------------------------
    # Results compilation
    # -----------------------------------------------------------------------

    def _compile_results(self, symbol, df, trades, equity_curve,
                          start_cap, end_cap,
                          strategy_name, timeframe,
                          annualise_factor,
                          stop_mode: str = STOP_STANDARD,
                          fees_paid: float = 0.0,
                          commission_pct: float = 0.0,
                          slippage_pct:   float = 0.0) -> BacktestResult:
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
            stop_mode        = stop_mode,
            fees_paid        = fees_paid,
            commission_pct   = commission_pct,
            slippage_pct     = slippage_pct,
            trades           = trades,
            equity_curve     = equity_curve,
        )

    # -----------------------------------------------------------------------
    # Rich text report
    # -----------------------------------------------------------------------

    def print_report(self, result: BacktestResult):
        w = 62
        sep = "=" * w
        thin = "-" * w
        stop_label = (
            f"2-Bar Trailing (N={result.stop_mode.split('_')[-1]})"
            if result.stop_mode == STOP_TWO_BAR
            else "Standard Fixed %"
        )
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
# Portfolio summary
# ===========================================================================

def print_portfolio_summary(results: List[BacktestResult]):
    if not results:
        return
    friction_free = all(r.commission_pct == 0 and r.slippage_pct == 0 for r in results)
    print(f"\n{'='*62}")
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
          f"{'MaxDD':>8} {'Sharpe':>7} {'Trades':>7} {'Stop':>10}")
    print(f"  {'-'*65}")
    for r in sorted(results, key=lambda x: x.total_return_pct, reverse=True):
        stop_label = "2-Bar" if r.stop_mode == STOP_TWO_BAR else "Std%"
        print(f"  {r.symbol:<8} {r.total_return_pct:>+7.1f}% "
              f"{r.win_rate:>7.1f}% {r.profit_factor:>6.2f} "
              f"{r.max_drawdown_pct:>7.1f}% {r.sharpe_ratio:>7.2f} "
              f"{r.total_trades:>7} {stop_label:>10}")
    avgs = {
        "ret": np.mean([r.total_return_pct for r in results]),
        "wr":  np.mean([r.win_rate         for r in results]),
        "pf":  np.mean([r.profit_factor    for r in results]),
        "dd":  np.mean([r.max_drawdown_pct for r in results]),
        "sh":  np.mean([r.sharpe_ratio     for r in results]),
    }
    print(f"  {'-'*65}")
    print(f"  {'AVG':<8} {avgs['ret']:>+7.1f}% "
          f"{avgs['wr']:>7.1f}% {avgs['pf']:>6.2f} "
          f"{avgs['dd']:>7.1f}% {avgs['sh']:>7.2f}")
    print(f"  (averages across isolated runs — not a blended portfolio metric)")
    print(f"{'='*62}\n")


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
    parser.add_argument("--symbol",   default="AAPL")
    parser.add_argument("--days",     type=int, default=180)
    parser.add_argument("--capital",  type=float, default=10_000.0)
    parser.add_argument("--tf",       default="1h", choices=["5m", "1h", "1d"])
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--all",      action="store_true")
    parser.add_argument("--chart",    action="store_true")
    parser.add_argument("--ascii",    action="store_true")
    parser.add_argument("--export",   action="store_true")
    parser.add_argument("--stop",     default="standard",
                        choices=["standard", "two_bar"],
                        help="Stop loss mode: standard (fixed %%) or two_bar (N-bar trailing)")
    parser.add_argument("--lookback", type=int, default=2,
                        help="Lookback bars N for two_bar stop (default 2, range 1-20)")
    parser.add_argument("--asset-class", default="stock", choices=["stock", "crypto"],
                        help="Asset class — affects default friction assumptions")
    parser.add_argument("--no-fees", action="store_true",
                        help="Run with zero commission and zero slippage (optimistic baseline)")
    args = parser.parse_args()

    # Friction override: --no-fees forces both to 0.0
    _commission = 0.0 if args.no_fees else None   # None = use config default
    _slippage   = 0.0 if args.no_fees else None

    backtester = Backtester(starting_capital=args.capital)

    if args.all:
        symbols = config.STOCK_WATCHLIST[:15]
        results = backtester.run_all(
            symbols,
            strategy_name    = args.strategy,
            days             = args.days,
            starting_capital = args.capital,
            timeframe        = args.tf,
            asset_class      = args.asset_class,
            stop_mode        = args.stop,
            two_bar_lookback = args.lookback,
            commission_pct   = _commission,
            slippage_pct     = _slippage,
        )
        for r in results:
            backtester.print_report(r)
            if args.ascii:
                backtester.print_ascii_chart(r)
            if args.export:
                backtester.export_json(r)
        print_portfolio_summary(results)
    else:
        if args.strategy:
            result = backtester.run_strategy(
                args.symbol, args.strategy, args.days, args.capital, args.tf,
                asset_class=args.asset_class,
                stop_mode=args.stop, two_bar_lookback=args.lookback,
                commission_pct=_commission, slippage_pct=_slippage,
            )
        else:
            result = backtester.run(
                args.symbol, args.days, args.capital, args.tf,
                asset_class=args.asset_class,
                stop_mode=args.stop, two_bar_lookback=args.lookback,
                commission_pct=_commission, slippage_pct=_slippage,
            )

        if result:
            backtester.print_report(result)
            if args.ascii:
                backtester.print_ascii_chart(result)
            if args.chart:
                backtester.show_charts(result)
            if args.export:
                backtester.export_json(result)
        else:
            print("Backtest returned no results — check symbol and timeframe.")
