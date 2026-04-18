"""
base_strategy.py — Abstract base class for all 8 trading strategies.
Trading Bot v2

All strategies inherit from BaseStrategy and must implement:
  - name (property)
  - analyze(symbol, candles, market_condition) -> TradeSignal or None

The verbose_log() method is available to all strategies and will log
detailed signal condition pass/fail data when --verbose mode is active.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

import config


# =============================================================================
# TRADE SIGNAL — returned by strategies when a trade opportunity is found
# =============================================================================

@dataclass
class TradeSignal:
    """Represents a trade opportunity identified by a strategy."""
    symbol:         str
    direction:      str         # "long" or "short"
    score:          float       # Confidence score 0.0–1.0
    strategy_name:  str
    stop_loss_pct:  float       # Strategy-specific stop loss %
    take_profit_pct:float       # Strategy-specific take profit %
    reason:         str = ""    # Human-readable reason for the signal
    metadata:       dict = field(default_factory=dict)


# =============================================================================
# BASE STRATEGY
# =============================================================================

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    Subclasses must define:
      - self.strategy_name (str)
      - self.stop_loss_pct (float)
      - self.take_profit_pct (float)
      - analyze(symbol, candles, market_condition) -> Optional[TradeSignal]
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = True

        # These must be set by each subclass
        self.strategy_name   = "BaseStrategy"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT

    @property
    def name(self) -> str:
        return self.strategy_name

    @abstractmethod
    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:
        """
        Analyze candle data for a symbol and return a TradeSignal if
        conditions are met, or None if no trade opportunity exists.

        Args:
            symbol:           Ticker symbol, e.g. "BTC/USD" or "AAPL"
            candles:          DataFrame with columns: open, high, low, close, volume
                              Sorted oldest-first. At least 60 rows recommended.
            market_condition: "trending", "ranging", "volatile", or "unknown"

        Returns:
            TradeSignal if conditions are met, None otherwise.
        """
        pass

    # =========================================================================
    # VERBOSE LOGGING — call this for every condition check in analyze()
    # =========================================================================

    def verbose_log(
        self,
        symbol: str,
        condition_name: str,
        passed: bool,
        actual_value,
        threshold_value,
        direction: str = "",
        extra: str = ""
    ):
        """
        Log the result of a single signal condition check.

        Only writes to the log when VERBOSE_MODE is True (--verbose flag).
        Each call produces one line in bot.log showing whether the condition
        passed or failed, what the actual value was, and what was required.

        Example log output:
            [VERBOSE][RSIMomentum][BTC/USD] FAIL: RSI oversold |
                actual=52.31 | required=<30 | direction=long

        Args:
            symbol:          The symbol being analyzed, e.g. "BTC/USD"
            condition_name:  Short description, e.g. "RSI oversold"
            passed:          True if the condition was satisfied
            actual_value:    The actual indicator value
            threshold_value: The required threshold (for display)
            direction:       "long", "short", or "" if not directional
            extra:           Any additional context string
        """
        if not config.VERBOSE_MODE:
            return

        status = "PASS" if passed else "FAIL"
        dir_str = f" | direction={direction}" if direction else ""
        extra_str = f" | {extra}" if extra else ""

        # Format actual_value — handle both floats and other types
        try:
            actual_str = f"{float(actual_value):.4f}"
        except (TypeError, ValueError):
            actual_str = str(actual_value)

        message = (
            f"[VERBOSE][{self.strategy_name}][{symbol}] "
            f"{status}: {condition_name} | "
            f"actual={actual_str} | "
            f"required={threshold_value}"
            f"{dir_str}"
            f"{extra_str}"
        )

        # Always log at DEBUG level — visible in log file during verbose mode
        self.logger.debug(message)

    def verbose_log_score(self, symbol: str, score: float, threshold: float):
        """
        Log the final computed score vs the minimum required score.
        Call this at the end of analyze() before returning the signal.
        """
        if not config.VERBOSE_MODE:
            return

        passed = score >= threshold
        status = "PASS — SIGNAL GENERATED" if passed else "FAIL — below threshold, no trade"

        try:
            score_str = f"{score:.4f}"
        except (TypeError, ValueError):
            score_str = str(score)

        message = (
            f"[VERBOSE][{self.strategy_name}][{symbol}] "
            f"FINAL SCORE: {score_str} | "
            f"min_required={threshold:.4f} | "
            f"{status}"
        )
        self.logger.debug(message)

    def verbose_log_skip(self, symbol: str, reason: str):
        """
        Log when a strategy skips analysis entirely (e.g. wrong market condition,
        not enough candle data, strategy disabled).
        """
        if not config.VERBOSE_MODE:
            return

        message = (
            f"[VERBOSE][{self.strategy_name}][{symbol}] "
            f"SKIP: {reason}"
        )
        self.logger.debug(message)

    # =========================================================================
    # UTILITY HELPERS — shared calculations used by multiple strategies
    # =========================================================================

    def _check_enough_candles(self, symbol: str, candles: pd.DataFrame, required: int) -> bool:
        """Return True if there are enough candles; log skip if not."""
        if len(candles) < required:
            self.verbose_log_skip(
                symbol,
                f"Not enough candles: have {len(candles)}, need {required}"
            )
            return False
        return True

    def _make_signal(
        self,
        symbol: str,
        direction: str,
        score: float,
        reason: str,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        metadata: Optional[dict] = None
    ) -> TradeSignal:
        """Convenience constructor for TradeSignal using this strategy's defaults."""
        return TradeSignal(
            symbol          = symbol,
            direction       = direction,
            score           = score,
            strategy_name   = self.strategy_name,
            stop_loss_pct   = stop_loss_pct if stop_loss_pct is not None else self.stop_loss_pct,
            take_profit_pct = take_profit_pct if take_profit_pct is not None else self.take_profit_pct,
            reason          = reason,
            metadata        = metadata or {}
        )
