"""
=============================================================
  MARKET SCANNER
  Scans stocks and crypto for high-probability setups.
  Routes all signals through the 8-strategy engine.
  Only signals scoring >= min_signal_confidence are forwarded.
=============================================================
"""

import logging
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
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> pd.DataFrame:
        ema_fast    = series.ewm(span=fast,   adjust=False).mean()
        ema_slow    = series.ewm(span=slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram   = macd_line - signal_line
        return pd.DataFrame({
            "macd":   macd_line,
            "signal": signal_line,
            "hist":   histogram
        })

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20,
                        std: float = 2.0) -> pd.DataFrame:
        mid   = series.rolling(period).mean()
        sigma = series.rolling(period).std()
        return pd.DataFrame({
            "upper": mid + std * sigma,
            "mid":   mid,
            "lower": mid - std * sigma,
            "pct_b": (series - (mid - std * sigma)) / (2 * std * sigma)
        })

    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        avg = volume.rolling(period).mean()
        return volume / avg.replace(0, np.nan)


class StockScanner:
    """Scans stock watchlist for opportunities using Alpaca market data."""

    MIN_PRICE   = getattr(config, "STOCK_MIN_PRICE",  1.0)
    MAX_PRICE   = getattr(config, "STOCK_MAX_PRICE",  5000.0)
    MIN_VOLUME  = getattr(config, "STOCK_MIN_VOLUME", 100000)

    def __init__(self):
        self.api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.ALPACA_BASE_URL
        )

    def get_bars(self, symbol: str, timeframe: str = "5Min",
                 limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            bars = self.api.get_bars(symbol, timeframe, limit=limit).df
            if bars.empty or len(bars) < 50:
                return None
            bars.index = pd.to_datetime(bars.index)
            return bars
        except Exception as e:
            logger.debug(f"Failed to get bars for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            quote = self.api.get_latest_quote(symbol)
            return (quote.ap + quote.bp) / 2
        except Exception as e:
            logger.debug(f"Price lookup failed for {symbol}: {e}")
            return None

    def scan(self) -> List[Signal]:
        """Scan all stocks in watchlist and return signals."""
        signals = []
        for symbol in config.STOCK_WATCHLIST:
            try:
                bars = self.get_bars(symbol)
                if bars is None:
                    continue
                price = bars["close"].iloc[-1]

                # Basic filters
                if price < self.MIN_PRICE or price > self.MAX_PRICE:
                    continue
                if bars["volume"].iloc[-20:].mean() < self.MIN_VOLUME:
                    continue

                strat_signals = strategy_engine.run_strategies(
                    symbol, "stock", bars, price
                )
                for ss in strat_signals:
                    raw_indicators = {
                        **ss.indicators,
                        "strategy_name":          ss.strategy_name,
                        "custom_stop_loss_pct":   ss.custom_stop_loss_pct,
                        "custom_take_profit_pct": ss.custom_take_profit_pct,
                        "custom_position_pct":    ss.custom_position_pct,
                    }

                    use_lev = getattr(config, "USE_LEVERAGED_LONGS", False)
                    mapped_sym, mapped_dir, mapped_ind = map_signal(
                        symbol              = ss.symbol,
                        direction           = ss.direction,
                        score               = ss.score,
                        current_price       = ss.current_price,
                        indicators          = raw_indicators,
                        use_leveraged_longs = use_lev,
                    )

                    # ── CRITICAL FIX ──────────────────────────────────────
                    # If the symbol was remapped to an ETF (e.g. MSFT→TQQQ),
                    # the original stock price is WRONG for the ETF.
                    # Fetch the actual current price of the mapped symbol
                    # so stop-loss and take-profit are calculated correctly.
                    if mapped_sym != ss.symbol:
                        etf_price = self.get_current_price(mapped_sym)
                        if etf_price is None or etf_price <= 0:
                            logger.warning(
                                f"Could not fetch price for mapped ETF {mapped_sym} "
                                f"(from {ss.symbol}) — skipping signal"
                            )
                            continue
                        signal_price = etf_price
                        logger.info(
                            f"ETF remap: {ss.symbol} ${ss.current_price:.2f} → "
                            f"{mapped_sym} ${etf_price:.2f} "
                            f"({'leveraged' if use_lev else 'inverse'})"
                        )
                    else:
                        signal_price = ss.current_price

                    signals.append(Signal(
                        symbol        = mapped_sym,
                        asset_class   = ss.asset_class,
                        direction     = mapped_dir,
                        score         = ss.score,
                        current_price = signal_price,
                        indicators    = mapped_ind,
                        reason        = f"[{ss.strategy_name}] {ss.reason}",
                    ))

            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {e}")

        signals.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Stock scan complete: {len(signals)} signals found")
        return signals


class CryptoScanner:
    """
    Scans crypto pairs using Coinbase Advanced Trade via CCXT.
    Also supports Kraken if keys are configured.
    """

    def __init__(self):
        self.coinbase = ccxt.coinbase({
            "apiKey":          config.COINBASE_API_KEY,
            "secret":          config.COINBASE_SECRET_KEY,
            "enableRateLimit": True,
        })

        self.kraken = None
        if config.KRAKEN_API_KEY and config.KRAKEN_SECRET_KEY:
            try:
                self.kraken = ccxt.kraken({
                    "apiKey":          config.KRAKEN_API_KEY,
                    "secret":          config.KRAKEN_SECRET_KEY,
                    "enableRateLimit": True,
                })
                logger.info("Kraken exchange initialized.")
            except Exception as e:
                logger.warning(f"Kraken init failed: {e}")

    def get_ohlcv(self, pair: str, timeframe: str = "5m",
                  limit: int = 100,
                  exchange=None) -> Optional[pd.DataFrame]:
        ex = exchange or self.coinbase
        try:
            ohlcv = ex.fetch_ohlcv(pair, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 50:
                return None
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df
        except Exception as e:
            logger.debug(f"Failed OHLCV for {pair}: {e}")
            return None

    def get_current_price(self, pair: str) -> Optional[float]:
        if self.kraken:
            try:
                ticker = self.kraken.fetch_ticker(pair)
                if ticker and ticker.get("last"):
                    return float(ticker["last"])
            except Exception as e:
                logger.debug(f"Kraken price lookup failed for {pair}: {e}")

        try:
            ticker = self.coinbase.fetch_ticker(pair)
            if ticker and ticker.get("last"):
                return float(ticker["last"])
        except Exception as e:
            logger.debug(f"Coinbase price lookup failed for {pair}: {e}")

        try:
            df = self.get_ohlcv(pair, timeframe="1m", limit=2)
            if df is not None and not df.empty:
                return float(df["close"].iloc[-1])
        except Exception as e:
            logger.debug(f"OHLCV price fallback failed for {pair}: {e}")

        return None

    def scan(self) -> List[Signal]:
        """Scan all crypto pairs and return signals."""
        signals = []
        for pair in config.CRYPTO_WATCHLIST:
            for exchange_name, exchange in [
                ("Coinbase", self.coinbase),
                ("Kraken",   self.kraken)
            ]:
                if exchange is None:
                    continue
                try:
                    df = self.get_ohlcv(pair, exchange=exchange)
                    if df is None:
                        continue
                    price = df["close"].iloc[-1]

                    crypto_min = getattr(config, "CRYPTO_MIN_PRICE", 0.001)
                    crypto_max = getattr(config, "CRYPTO_MAX_PRICE", 999999.0)
                    if price < crypto_min or price > crypto_max:
                        logger.debug(
                            f"Skipping {pair} — price ${price:.8f} outside "
                            f"filter (min=${crypto_min}, max=${crypto_max})"
                        )
                        continue

                    strat_signals = strategy_engine.run_strategies(
                        pair, "crypto", df, price
                    )
                    for ss in strat_signals:
                        signals.append(Signal(
                            symbol        = ss.symbol,
                            asset_class   = ss.asset_class,
                            direction     = ss.direction,
                            score         = ss.score,
                            current_price = ss.current_price,
                            indicators    = {
                                **ss.indicators,
                                "strategy_name":          ss.strategy_name,
                                "custom_stop_loss_pct":   ss.custom_stop_loss_pct,
                                "custom_take_profit_pct": ss.custom_take_profit_pct,
                                "custom_position_pct":    ss.custom_position_pct,
                                "exchange":               exchange_name,
                            },
                            reason = f"[{ss.strategy_name}][{exchange_name}] {ss.reason}",
                        ))
                    break
                except Exception as e:
                    logger.debug(f"Error scanning {pair} on {exchange_name}: {e}")

        signals.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Crypto scan complete: {len(signals)} signals found")
        return signals


class MarketScanner:
    """Combines stock and crypto scanners into one unified interface."""

    def __init__(self, db_ref=None, trade_executor=None, risk_manager=None,
                 strategy_engine_ref=None, ml_scorer=None, condition_detector=None):
        self.stock_scanner   = StockScanner()
        self.crypto_scanner  = CryptoScanner()
        self._executor       = trade_executor
        self._risk_manager   = risk_manager
        self._ml_scorer      = ml_scorer
        self._condition_detector = condition_detector

    def _get_ml_scorer(self):
        if self._ml_scorer:
            return self._ml_scorer
        from intelligence.ml_scorer import ml_scorer
        return ml_scorer

    def _get_condition_detector(self):
        if self._condition_detector:
            return self._condition_detector
        from intelligence.condition_detector import condition_detector
        return condition_detector

    def _get_executor(self):
        if self._executor:
            return self._executor
        from core.trade_executor import executor
        return executor

    def scan_stocks(self):
        self._process_signals(self.stock_scanner.scan())

    def scan_crypto(self):
        self._process_signals(self.crypto_scanner.scan())

    def _process_signals(self, signals: List[Signal]):
        if not signals:
            return

        # ── Claude morning briefing ───────────────────────────────────────
        # Get or refresh market context — cached 60 min, conservative on failure.
        # If briefing fails or blocks trading, no signals execute today.
        # FALLBACK: if reviewer unavailable, market_context = None and signals
        # proceed through mechanical execution only (no Claude veto).
        market_context = None
        try:
            from intelligence.claude_reviewer import claude_reviewer
            if claude_reviewer.is_enabled():
                market_context = claude_reviewer.get_morning_context()
                if not market_context.allow_trading:
                    logger.info(
                        f"Claude reviewer: trading blocked — "
                        f"{market_context.briefing_text[:120]}"
                    )
                    return
        except Exception as e:
            logger.warning(
                f"Claude reviewer unavailable: {e} — "
                f"proceeding with mechanical execution only"
            )
            market_context = None

        is_crypto = all(s.asset_class == "crypto" for s in signals)

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

        executor = self._get_executor()
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
            # Any failure, timeout, or non-APPROVE response = SKIP this signal.
            # The only path to execution is an explicit APPROVE from Claude.
            if market_context is not None:
                try:
                    from intelligence.claude_reviewer import claude_reviewer
                    decision = claude_reviewer.review_signal(signal, market_context)
                    if decision.decision != "APPROVE":
                        logger.info(
                            f"Claude reviewer: {decision.decision} {signal.symbol} — "
                            f"{decision.reasoning}"
                        )
                        continue   # Skip — never default to approve
                    # Apply suggested position size override if provided
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
                    continue   # Skip on any reviewer error — never default to approve

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
