"""
Hammer Reversal Strategy (Strategy 10)
=======================================
Port of Gerald Lonlas' freqtrade Strategy002 to our framework.

Original backtest: 9 trades, 3.21% avg profit, Jan 2018 (crypto 5m bars).

Entry conditions (ALL must be true — very selective by design):
  1. RSI < 30          (oversold)
  2. Stochastic slowK < 20  (confirming oversold)
  3. Price < lower Bollinger Band  (extreme deviation below mean)
  4. Hammer candlestick detected   (reversal signal)

All four firing simultaneously means the market has:
  - Been sold off hard (RSI + Stoch both oversold)
  - Closed below the lower BB (statistically extreme)
  - Printed a reversal candle (buyers stepping in)

Exit / Take-profit — tiered ROI ladder (mirrors freqtrade original):
  <20 bars held  → target 5% gain
  20-30 bars     → target 4%
  30-60 bars     → target 3%
  60+ bars       → target 1% (kill switch — take anything)

  We implement this by setting take_profit_pct based on time held,
  which position_monitor adjusts dynamically via update_trade_levels.
  Initial take_profit is set to 5% (the best case target).

Stop-loss: 10% (wide, matching original — the hammer entry is already
  conservative so a tight stop would whipsaw too often).

Asset class: stocks + crypto (5-minute bars)
Default: DISABLED — backtest first, enable via dashboard or chat.
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional

import config
from strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)


class HammerReversal(BaseStrategy):
    """
    Hammer Reversal — port of freqtrade Strategy002.
    RSI+Stoch oversold + below lower Bollinger Band + Hammer candle.
    Very selective, high average profit per trade.
    """

    def __init__(self):
        super().__init__()
        self.strategy_name   = "hammer_reversal"
        self.stop_loss_pct   = 10.0   # Wide stop — entry is already conservative
        self.take_profit_pct = 5.0    # Initial TP — tiered ladder adjusts over time

        # ── Tunable parameters ──────────────────────────────────────────
        self.rsi_period       = 14
        self.rsi_oversold     = 30
        self.stoch_k_period   = 14
        self.stoch_d_period   = 3
        self.stoch_oversold   = 20
        self.bb_period        = 20
        self.bb_std           = 2.0
        self.min_score        = 0.70   # High threshold — 4/4 conditions = score 1.0

        # Fisher RSI exit threshold (secondary — used by position_monitor in future)
        self.fisher_rsi_exit  = 0.3

        # Start disabled — must be validated via backtest before going live
        self.enabled          = False

        logger.info(
            f"[{self.strategy_name}] Initialized — DISABLED by default. "
            f"Run backtest first, then enable via dashboard."
        )

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:
        """
        Check all four entry conditions. Returns signal only when ALL fire.
        """
        if not self._check_enough_candles(symbol, candles, 60):
            return None

        try:
            closes  = candles["close"].astype(float)
            highs   = candles["high"].astype(float)
            lows    = candles["low"].astype(float)
            opens   = candles["open"].astype(float)

            # ── 1. RSI ──────────────────────────────────────────────────
            delta    = closes.diff()
            gain     = delta.clip(lower=0)
            loss     = -delta.clip(upper=0)
            avg_gain = gain.ewm(com=self.rsi_period - 1, adjust=False).mean()
            avg_loss = loss.ewm(com=self.rsi_period - 1, adjust=False).mean()
            rs       = avg_gain / avg_loss.replace(0, np.nan)
            rsi      = 100 - (100 / (1 + rs))
            rsi_now  = rsi.iloc[-1]

            rsi_ok = rsi_now < self.rsi_oversold
            self.verbose_log(symbol, "RSI oversold", rsi_ok,
                             rsi_now, f"<{self.rsi_oversold}", "long")
            if not rsi_ok:
                return None

            # ── 2. Stochastic slowK ─────────────────────────────────────
            low_min  = lows.rolling(self.stoch_k_period).min()
            high_max = highs.rolling(self.stoch_k_period).max()
            fastk    = 100 * (closes - low_min) / (high_max - low_min + 1e-10)
            slowk    = fastk.rolling(self.stoch_d_period).mean()
            slowk_now= slowk.iloc[-1]

            stoch_ok = slowk_now < self.stoch_oversold
            self.verbose_log(symbol, "Stoch slowK oversold", stoch_ok,
                             slowk_now, f"<{self.stoch_oversold}", "long")
            if not stoch_ok:
                return None

            # ── 3. Price below lower Bollinger Band ─────────────────────
            typical  = (highs + lows + closes) / 3
            bb_mid   = typical.rolling(self.bb_period).mean()
            bb_std   = typical.rolling(self.bb_period).std()
            bb_lower = bb_mid - self.bb_std * bb_std
            price_now= closes.iloc[-1]
            bb_low_now = bb_lower.iloc[-1]

            bb_ok = price_now < bb_low_now
            self.verbose_log(symbol, "Price below lower BB", bb_ok,
                             price_now, f"<{bb_low_now:.4f}", "long")
            if not bb_ok:
                return None

            # ── 4. Hammer candlestick ───────────────────────────────────
            hammer_ok = self._detect_hammer(
                opens.iloc[-1], highs.iloc[-1],
                lows.iloc[-1],  closes.iloc[-1]
            )
            self.verbose_log(symbol, "Hammer candle", hammer_ok,
                             1 if hammer_ok else 0, "==1", "long")
            if not hammer_ok:
                return None

            # ── All 4 conditions met — compute Fisher RSI for metadata ──
            rsi_scaled  = 0.1 * (rsi_now - 50)
            fisher_rsi  = (np.exp(2 * rsi_scaled) - 1) / (np.exp(2 * rsi_scaled) + 1)

            # Score = 1.0 when all 4 conditions fire (very high conviction)
            score = 1.0
            self.verbose_log_score(symbol, score, self.min_score)

            reason = (
                f"Hammer Reversal: RSI={rsi_now:.1f} "
                f"SlowK={slowk_now:.1f} "
                f"Price={price_now:.4f}<BB={bb_low_now:.4f} "
                f"Fisher={fisher_rsi:.3f}"
            )

            logger.info(f"[HammerReversal] Signal: {symbol} LONG | {reason}")

            return self._make_signal(
                symbol          = symbol,
                direction       = "long",   # Long only — hammer is a bottom reversal
                score           = score,
                reason          = reason,
                stop_loss_pct   = self.stop_loss_pct,
                take_profit_pct = self.take_profit_pct,
                metadata        = {
                    "rsi":          round(rsi_now, 2),
                    "slowk":        round(slowk_now, 2),
                    "bb_lower":     round(bb_low_now, 4),
                    "fisher_rsi":   round(fisher_rsi, 4),
                    "hammer":       True,
                    # Tiered ROI ladder — position_monitor uses these
                    # to step down TP as hold time increases
                    "roi_ladder":   {
                        "0":  5.0,   # 0-20 bars: target 5%
                        "20": 4.0,   # 20-30 bars: target 4%
                        "30": 3.0,   # 30-60 bars: target 3%
                        "60": 1.0,   # 60+ bars: take 1% and exit
                    }
                }
            )

        except Exception as e:
            logger.error(f"[HammerReversal] Error analyzing {symbol}: {e}",
                         exc_info=config.VERBOSE_MODE)
            return None

    def _detect_hammer(
        self,
        open_: float, high: float,
        low: float,   close: float
    ) -> bool:
        """
        Detect a hammer candlestick pattern.

        A hammer has:
        - Small real body (open/close) in the upper third of the range
        - Long lower shadow >= 2x the body size
        - Little or no upper shadow (<= 10% of range)

        This is a pure Python port of TA-Lib's CDLHAMMER logic.
        """
        body      = abs(close - open_)
        range_    = high - low

        if range_ < 1e-10:   # Doji / zero-range candle — not a hammer
            return False

        body_top    = max(open_, close)
        body_bottom = min(open_, close)
        upper_shadow= high - body_top
        lower_shadow= body_bottom - low

        # Hammer criteria
        small_body    = body <= range_ * 0.3          # Body <= 30% of range
        long_lower    = lower_shadow >= body * 2.0    # Lower shadow >= 2x body
        small_upper   = upper_shadow <= range_ * 0.1  # Upper shadow <= 10% of range
        body_upper    = body_top >= low + range_ * 0.6 # Body in upper 40% of range

        return small_body and long_lower and small_upper and body_upper
