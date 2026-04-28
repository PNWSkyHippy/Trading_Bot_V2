"""
=============================================================
  MARKET SCANNER
  Scans stocks and crypto for high-probability setups.
  Routes all signals through the 8-strategy engine.
  Only signals scoring >= min_signal_confidence are forwarded.
=============================================================
"""

import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

import alpaca_trade_api as tradeapi
import ccxt

import config
from core.inverse_etf_mapper import map_signal, is_leveraged_etf
from strategies.strategy_engine import strategy_engine

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    symbol:        str
    asset_class:   str      # "stock" or "crypto"
    direction:     str      # "long" or "short"
    score:         float    # 0.0 – 1.0 confidence
    current_price: float
    indicators:    Dict
    reason:        str


class TechnicalAnalysis:
    """Pure technical indicator calculations. No external dependencies."""

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta    = series.diff()
        gain     = delta.clip(lower=0)
        loss     = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs       = avg_gain / avg_loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> tuple:
        ema_fast    = series.ewm(span=fast,   adjust=False).mean()
        ema_slow    = series.ewm(span=slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram   = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20,
                        std_dev: float = 2.0) -> tuple:
        sma   = series.rolling(period).mean()
        std   = series.rolling(period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        pct_b = (series - lower) / (upper - lower).replace(0, float("nan"))
        return upper, lower, pct_b

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        cum_tp_vol    = (typical_price * df["volume"]).cumsum()
        cum_vol       = df["volume"].cumsum()
        return cum_tp_vol / cum_vol.replace(0, float("nan"))

    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        direction = df["close"].diff().apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )
        return (direction * df["volume"]).cumsum()

    @staticmethod
    def stochastic(df: pd.DataFrame, k_period: int = 14,
                   d_period: int = 3) -> tuple:
        low_min  = df["low"].rolling(k_period).min()
        high_max = df["high"].rolling(k_period).max()
        k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, float("nan"))
        d = k.rolling(d_period).mean()
        return k, d


class StockScanner:

    def __init__(self):
        self.api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.ALPACA_BASE_URL
        )
        self.ta = TechnicalAnalysis()

    def get_bars(self, symbol: str, timeframe: str = "5Min",
                 limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            bars = self.api.get_bars(
                symbol, timeframe,
                limit=limit, adjustment="raw"
            ).df
            if bars.empty:
                return None
            bars.columns = [c.lower() for c in bars.columns]
            bars = bars.rename(columns={"vwap": "vwap_raw"}) if "vwap" in bars.columns else bars
            return bars
        except Exception as e:
            logger.debug(f"Bars fetch failed for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            trade = self.api.get_latest_trade(symbol)
            return float(trade.price)
        except Exception:
            try:
                bars = self.get_bars(symbol, "1Min", 1)
                if bars is not None and not bars.empty:
                    return float(bars["close"].iloc[-1])
            except Exception:
                pass
        return None

    def scan(self) -> List[Signal]:
        """
        Scan all stocks in the watchlist.
        Fetches candles once per timeframe per symbol and reuses them
        across all strategies that share the same timeframe.
        This avoids redundant API calls while giving each strategy
        the candle resolution it was designed and backtested for.
        """
        # Build timeframe → strategies map once (only enabled stock strategies)
        tf_groups: dict = {}
        for strategy in strategy_engine.get_all_strategies():
            if not strategy.enabled:
                continue
            if not getattr(strategy, "stock_enabled", True):
                continue
            tf = getattr(strategy, "stock_candle_timeframe", "5Min")
            tf_groups.setdefault(tf, [])
            if strategy not in tf_groups[tf]:
                tf_groups[tf].append(strategy)

        signals = []
        for symbol in config.STOCK_WATCHLIST:
            try:
                price = self.get_current_price(symbol)
                if not price:
                    continue
                if not (config.STOCK_MIN_PRICE <= price <= config.STOCK_MAX_PRICE):
                    continue

                # Fetch bars once per unique timeframe — reused across strategies
                bar_cache: dict = {}
                for tf in tf_groups:
                    limit = max(
                        getattr(s, "candle_limit", 100)
                        for s in tf_groups[tf]
                    )
                    bars = self.get_bars(symbol, tf, limit)
                    if bars is not None and len(bars) >= 20:
                        bar_cache[tf] = bars

                if not bar_cache:
                    continue

                # Run strategies against their correct candle timeframe
                strategy_signals = strategy_engine.run_strategies_multi_tf(
                    symbol, "stock", bar_cache, price
                )
                for ss in strategy_signals:
                    signals.append(Signal(
                        symbol        = ss.symbol,
                        asset_class   = ss.asset_class,
                        direction     = ss.direction,
                        score         = ss.score,
                        current_price = ss.current_price,
                        indicators    = ss.indicators,
                        reason        = ss.reason,
                    ))

                # Small delay between symbols to avoid Alpaca rate limiting.
                # With 137 stocks × 2 timeframes = 274+ API calls per scan.
                # 0.15s delay keeps us well under Alpaca's 200 req/min limit.
                time.sleep(0.15)

            except Exception as e:
                logger.debug(f"Stock scan error {symbol}: {e}")
        return signals


class CryptoScanner:

    def __init__(self):
        self.exchange = ccxt.kraken({
            "apiKey":          config.KRAKEN_API_KEY,
            "secret":          config.KRAKEN_SECRET_KEY,
            "enableRateLimit": True,
        })
        self.ta = TechnicalAnalysis()

    def get_ohlcv(self, symbol: str, timeframe: str = "5m",
                  limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return None
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df
        except Exception as e:
            logger.debug(f"OHLCV fetch failed for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception:
            return None

    def scan(self) -> List[Signal]:
        """
        Scan all crypto pairs in the watchlist.
        Fetches candles once per timeframe per symbol and reuses them
        across all strategies that share the same timeframe.
        """
        # Build timeframe → strategies map once (only enabled crypto strategies)
        tf_groups: dict = {}
        for strategy in strategy_engine.get_all_strategies():
            if not strategy.enabled:
                continue
            if not getattr(strategy, "crypto_enabled", True):
                continue
            tf = getattr(strategy, "crypto_candle_timeframe", "1h")
            tf_groups.setdefault(tf, [])
            if strategy not in tf_groups[tf]:
                tf_groups[tf].append(strategy)

        signals = []
        for symbol in config.CRYPTO_WATCHLIST:
            try:
                price = self.get_current_price(symbol)
                if not price:
                    continue
                if not (config.CRYPTO_MIN_PRICE <= price <= config.CRYPTO_MAX_PRICE):
                    continue

                # Fetch bars once per unique timeframe — reused across strategies
                bar_cache: dict = {}
                for tf in tf_groups:
                    limit = max(
                        getattr(s, "candle_limit", 100)
                        for s in tf_groups[tf]
                    )
                    bars = self.get_ohlcv(symbol, tf, limit)
                    if bars is not None and len(bars) >= 20:
                        bar_cache[tf] = bars

                if not bar_cache:
                    continue

                # Run strategies against their correct candle timeframe
                strategy_signals = strategy_engine.run_strategies_multi_tf(
                    symbol, "crypto", bar_cache, price
                )
                for ss in strategy_signals:
                    signals.append(Signal(
                        symbol        = ss.symbol,
                        asset_class   = ss.asset_class,
                        direction     = ss.direction,
                        score         = ss.score,
                        current_price = ss.current_price,
                        indicators    = ss.indicators,
                        reason        = ss.reason,
                    ))
            except Exception as e:
                logger.debug(f"Crypto scan error {symbol}: {e}")
        return signals


class MarketScanner:

    def __init__(self):
        self.stock_scanner  = StockScanner()
        self.crypto_scanner = CryptoScanner()

    def _get_executor(self):
        from core.trade_executor import executor
        return executor

    def _get_ml_scorer(self):
        from intelligence.ml_scorer import ml_scorer
        return ml_scorer

    def _get_condition_detector(self):
        from intelligence.condition_detector import condition_detector
        return condition_detector

    def scan_stocks(self):
        signals = self.stock_scanner.scan()
        if signals:
            self._process_signals(signals)

    def scan_crypto(self):
        signals = self.crypto_scanner.scan()
        if signals:
            self._process_signals(signals)

    def _process_signals(self, signals: List[Signal]):
        if not signals:
            return

        # Determine asset class FIRST — before any gate checks
        # is_crypto must be known before the morning briefing gate
        is_crypto = all(s.asset_class == "crypto" for s in signals)

        # ── Claude morning briefing ───────────────────────────────────────
        # Get or refresh market context — cached 120 min, conservative on failure.
        #
        # CRITICAL: allow_trading=False only blocks STOCKS.
        # Crypto trades 24/7 — the morning briefing gate is irrelevant for crypto.
        # Crypto signals bypass this gate and go straight to per-signal review.
        #
        # FALLBACK: if reviewer unavailable, market_context = None and signals
        # proceed through mechanical execution only (no Claude veto).
        market_context = None
        try:
            from intelligence.claude_reviewer import claude_reviewer
            if claude_reviewer.is_enabled():
                market_context = claude_reviewer.get_morning_context()
                if not market_context.allow_trading and not is_crypto:
                    # Stock trading blocked by morning briefing — return early
                    logger.info(
                        f"Claude reviewer: stock trading blocked — "
                        f"{market_context.briefing_text[:120]}"
                    )
                    return
                elif not market_context.allow_trading and is_crypto:
                    # Crypto bypasses the allow_trading gate — log and continue
                    logger.debug(
                        "Claude reviewer: allow_trading=False but this is a crypto scan "
                        "— bypassing market hours gate, proceeding to signal review"
                    )
        except Exception as e:
            logger.warning(
                f"Claude reviewer unavailable: {e} — "
                f"proceeding with mechanical execution only"
            )
            market_context = None

        condition_value = "unknown"
        position_scalar = 1.0
        adx             = 25

        if not is_crypto:
            try:
                market_condition = self._get_condition_detector().get_spy_condition(
                    self.stock_scanner
                )
                if not market_condition.should_trade:
                    logger.warning(
                        f"Market condition says skip stocks: {market_condition.reason}"
                    )
                    return
                condition_value = market_condition.condition.value
                position_scalar = market_condition.position_scalar
                adx             = market_condition.adx
                logger.info(
                    f"Market condition: {condition_value} | "
                    f"ADX={adx} | scalar={position_scalar:.0%}"
                )
            except Exception as e:
                logger.warning(f"Condition detector error: {e} — using defaults")
        else:
            try:
                market_condition = self._get_condition_detector().get_spy_condition(
                    self.stock_scanner
                )
                condition_value = market_condition.condition.value
                adx             = market_condition.adx
                position_scalar = market_condition.position_scalar
            except Exception:
                pass

        # Deduplicate: one signal per symbol, highest score wins
        by_symbol: Dict[str, Signal] = {}
        for sig in signals:
            existing = by_symbol.get(sig.symbol)
            if existing is None or sig.score > existing.score:
                by_symbol[sig.symbol] = sig
        unique_signals = list(by_symbol.values())

        min_confidence = config.SIGNAL_TUNING.get(
            "min_signal_confidence", config.MIN_SIGNAL_CONFIDENCE
        )

        for signal in unique_signals:
            ml_exempt = signal.indicators.get("ml_exempt", False)

            if ml_exempt:
                logger.debug(
                    f"[ML-EXEMPT] {signal.symbol} [{signal.indicators.get('strategy_name', '?')}] "
                    f"— keeping raw score {signal.score:.3f} (ML blending skipped)"
                )
            else:
                try:
                    enhanced = self._get_ml_scorer().score(
                        indicators    = signal.indicators,
                        base_score    = signal.score,
                        condition_adx = adx
                    )
                    signal.score = round(enhanced, 3)
                except Exception:
                    pass

            signal.indicators["market_condition"] = condition_value
            signal.indicators["condition_scalar"] = position_scalar

        final = [s for s in unique_signals if s.score >= min_confidence]
        final.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Signals after ML/filter: {len(final)}")

        executor     = self._get_executor()
        from data.database import db
        open_trades  = db.get_open_trades()
        open_symbols = set(t["symbol"] for t in open_trades)

        for signal in final:
            if signal.symbol in open_symbols:
                logger.info(
                    f"Skipping {signal.symbol} — already have an open position"
                )
                continue

            # ── Claude per-signal review ──────────────────────────────────
            # Only runs if morning briefing succeeded (market_context is not None).
            # Skipped for reviewer_exempt strategies (e.g. Grid Bot) which use
            # non-standard indicators that Claude can't evaluate meaningfully.
            # Any failure, timeout, or non-APPROVE = SKIP. Never default to approve.
            reviewer_exempt = signal.indicators.get("reviewer_exempt", False)

            if market_context is not None and not reviewer_exempt:
                try:
                    from intelligence.claude_reviewer import claude_reviewer
                    decision = claude_reviewer.review_signal(signal, market_context)
                    if decision.decision != "APPROVE":
                        logger.info(
                            f"Claude reviewer: {decision.decision} {signal.symbol} — "
                            f"{decision.reasoning}"
                        )
                        continue
                    if decision.suggested_size_pct:
                        signal.indicators["condition_scalar"] = (
                            decision.suggested_size_pct / config.MAX_POSITION_PCT
                        )
                    logger.info(
                        f"Claude reviewer: APPROVED {signal.symbol} "
                        f"(confidence={decision.confidence}) — {decision.reasoning}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Claude reviewer error for {signal.symbol}: {e} "
                        f"— SKIPPING signal (conservative fallback)"
                    )
                    continue

            # ── Execute signal ────────────────────────────────────────────
            try:
                executor.execute_signal(signal)
                open_symbols.add(signal.symbol)
            except Exception as e:
                logger.error(f"Executor error for {signal.symbol}: {e}")

    def scan_all(self) -> List[Signal]:
        return self.stock_scanner.scan() + self.crypto_scanner.scan()

    def get_current_price(self, symbol: str, asset_class: str) -> Optional[float]:
        try:
            if asset_class == "stock":
                return self.stock_scanner.get_current_price(symbol)
            elif asset_class == "crypto":
                return self.crypto_scanner.get_current_price(symbol)
        except Exception as e:
            logger.error(f"Price lookup failed for {symbol}: {e}")
        return None


# Singleton
scanner = MarketScanner()
