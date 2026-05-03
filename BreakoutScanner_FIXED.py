# Ron's Market Scanner - Complete System
# Stocks + Crypto Breakout Detection with Auto-Trading
# Compatible with Alpaca (stocks), Coinbase/Kraken (crypto)

import os
import json
from signal import signal
import time
import threading
import smtplib
import winsound
import logging
from datetime import datetime, timedelta, time as dt_time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from collections import deque
from enum import Enum
import queue
import time
from numpy import rint

from signal_engine import classify_signal

def update_signal_tracking(scanner):
    import csv
    import os
    from datetime import datetime

    CSV_FILE = "signals_log.csv"

    if not os.path.isfile(CSV_FILE):
        return

    rows = []

    with open(CSV_FILE, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows.append(row)

    updated = False

    for row in rows:
        symbol = row["Symbol"]

        try:
            # Get current price
            if "/" in symbol:
                ticker = self.crypto_fetcher.exchange.fetch_ticker(symbol)
                price = ticker["last"]
            else:
                hist = scanner.stock_fetcher.get_historical_data(symbol)
                price = hist[-1].price if hist else None
 
            if price is None:
                continue

            # Time calculations
            entry_time = datetime.strptime(
                row["Date"] + " " + row["Time"],
                "%Y-%m-%d %H:%M:%S"
            )

            elapsed = (datetime.now() - entry_time).total_seconds()

            # Fill time buckets
            def fill(col, seconds):
                if row[col] == "" and elapsed >= seconds:
                    row[col] = round(price, 4)
                    return True
                return False

            if fill("t_5m", 300): updated = True
            if fill("t_15m", 900): updated = True
            if fill("t_1h", 3600): updated = True
            if fill("t_4h", 14400): updated = True
            if fill("t_24h", 86400): updated = True

            # ðŸ”¥ Momentum calculation
            entry_price = float(row["Price"])
            status, move_pct = classify_momentum(entry_price, price)

            row["momentum"] = status
            row["move_pct"] = round(move_pct, 2)

            if row["t_5m"] != "":
                t5 = float(row["t_5m"])

                if t5 <= entry_price:
                    row["momentum"] = "DEAD"

                elif move_pct < 1.0:
                    row["momentum"] = "WEAK"

                elif row["t_15m"] != "":
                    t15 = float(row["t_15m"])
                    if t15 <= t5:
                        row["momentum"] = "FADING"

            if move_pct >= 2.0:
                source = self.crypto_fetcher.exchange.id.upper()
                logger.warning(f"STRONG MOVE: {source} | {symbol} +{move_pct:.2f}%") 
            elif move_pct >= 1.5:
                source = self.crypto_fetcher.exchange.id.upper()
                logger.info(f"LIVE MOVE: {source} | {symbol} +{move_pct:.2f}%")
 
        except Exception:
            continue

    if updated:
        with open(CSV_FILE, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)



def classify_momentum(entry_price, current_price):
    try:
        entry = float(entry_price)
        current = float(current_price)

        move_pct = ((current - entry) / entry) * 100

        if move_pct < 1:
            return "DEAD", move_pct
        elif move_pct < 3:
            return "SMALL", move_pct
        elif move_pct < 5:
            return "MEDIUM", move_pct
        else:
            return "STRONG", move_pct

    except Exception:
        return "UNKNOWN", 0



import csv
import os

CSV_FILE = "signals_log.csv"
def log_signal_to_csv(signal):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Symbol", "Score", "Confidence",
                "Date", "Time", "Price",
                "t_5m", "t_15m", "t_1h", "t_4h", "t_24h",
                "momentum", "move_pct"
]           )

        writer.writerow([
            signal.symbol,
            round(signal.predicted_move_pct, 2),
            round(signal.confidence * 100, 2),
            signal.timestamp.strftime("%Y-%m-%d"),
            signal.timestamp.strftime("%H:%M:%S"),
            signal.current_price,
            "", "", "", "", "",
            "", ""   # momentum + move_pct placeholders
        ])


# Try to import optional dependencies
try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import alpaca_trade_api as tradeapi

    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

try:
    import ccxt

    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox

    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("scanner.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_CONFIG = {
    # Market Hours (Pacific Time)
    "stock_market_open": "06:30",
    "stock_market_close": "13:00",
    "crypto_24_7": True,
    "scan_interval_seconds": 30,
    "timezone": "US/Pacific",
    # Top Lists
    "top_stocks_count": 100,
    "top_cryptos_count": 100,
    # Breakout Detection Thresholds (%)
    "breakout_thresholds": [10, 20, 30, 50, 100, 200, 500],
    "momentum_window": 5,  # candles to analyze momentum
    "volume_spike_multiplier": 3.0,  # volume must be 3x average
    "price_acceleration_threshold": 0.5,  # % increase per interval accelerating
    # Alert Settings
    "enable_sound_alert": True,
    "enable_visual_alert": True,
    "enable_email_alert": True,
    "email_smtp_server": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_from": "ronkhensley@gmail.com",
    "email_to": "ronkhensley@gmail.com",
    "email_password": "ugzk usng tcms vjom",
    # Auto-Trading Settings
    "enable_auto_trade": False,
    "auto_trade_without_confirm": False,
    "broker": "alpaca",  # "alpaca" or "ibkr"
    # API Keys (store securely in production)
    "alpaca_api_key": "PKCCCMMJB6NKHBIYRHL34T6GJG",
    "alpaca_secret_key": "GKurkA5vqcwvsePp24hT51FSX6ajSYmcFJduD2hHtsAz",
    "alpaca_base_url": "https://paper-api.alpaca.markets",  # paper trading default
    "coinbase_api_key": "organizations/92656068-0785-41bd-94f1-c5fe0eb4190b/apiKeys/7544a55f-9a8b-4e41-bfe2-8db537cb3dee",
    "coinbase_api_secret": "organizations/92656068-0785-41bd-94f1-c5fe0eb4190b/apiKeys/7544a55f-9a8b-4e41-bfe2-8db537cb3dee",
    "kraken_api_key": "maZKoR8dBNWRnWYzSfVkW9bVGDisy6uqx5O4Tle73NVnYdsESR740+21",
    "kraken_api_secret": "63ug0E5bdMtBWmy/sJB+aYQs9c1n+XDq2qXd6pavL1p5uFl1661DFXsNX3d5Bn6vPU430oKgnMRk5cPp3NE3mg==",
    # Trading Parameters
    "default_trade_amount_usd": 1000,
    "max_position_size_usd": 5000,
    "stop_loss_percent": 5,
    "take_profit_percent": 20,
    # Schedule
    "run_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "exclude_dates": [],  # Holiday dates in YYYY-MM-DD format
    # Sound
    "alert_sound_frequency": 800,
    "alert_sound_duration_ms": 1000,
}

# ============================================================
# DATA CLASSES
# ============================================================


class AlertType(Enum):
    SOUND = "sound"
    VISUAL = "visual"
    EMAIL = "email"
    TRADE = "trade"


class AssetType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"


@dataclass
class PriceData:
    symbol: str
    price: float
    open_price: float
    high: float
    low: float
    volume: float
    timestamp: datetime
    asset_type: AssetType

    @property
    def daily_change_pct(self) -> float:
        if self.open_price == 0:
            return 0
        return ((self.price - self.open_price) / self.open_price) * 100

    @property
    def daily_high_pct(self) -> float:
        if self.open_price == 0:
            return 0
        return ((self.high - self.open_price) / self.open_price) * 100


@dataclass
class BreakoutSignal:
    symbol: str
    asset_type: AssetType
    current_price: float
    predicted_move_pct: float
    confidence: float  # 0.0 to 1.0
    volume_spike: float
    momentum_score: float
    pattern_detected: str
    timestamp: datetime
    price_history: List[float] = field(default_factory=list)
    volume_history: List[float] = field(default_factory=list)


@dataclass
class Alert:
    signal: BreakoutSignal
    alert_type: AlertType
    message: str
    timestamp: datetime
    acknowledged: bool = False


# ============================================================
# CONFIGURATION MANAGER
# ============================================================


class ConfigManager:
    def __init__(self, config_path: str = "scanner_config.json"):
        self.config_path = config_path
        self.config = {}
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"Config loaded from {self.config_path}")
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save()
            logger.info(f"Default config created at {self.config_path}")

    def save(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Config saved to {self.config_path}")

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()

    def is_market_open(self, asset_type: AssetType) -> bool:
        """Check if market should be open for given asset type."""
        now = datetime.now()

        # Check excluded dates
        today_str = now.strftime("%Y-%m-%d")
        if today_str in self.config.get("exclude_dates", []):
            return False

        # Check day of week
        day_name = now.strftime("%A")
        if day_name not in self.config.get(
            "run_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        ):
            return False

        if asset_type == AssetType.CRYPTO and self.config.get("crypto_24_7", True):
            return True

        if asset_type == AssetType.STOCK:
            open_time = self.config.get("stock_market_open", "06:30")
            close_time = self.config.get("stock_market_close", "13:00")

            open_hour, open_min = map(int, open_time.split(":"))
            close_hour, close_min = map(int, close_time.split(":"))

            current_time = now.time()
            market_open = dt_time(open_hour, open_min)
            market_close = dt_time(close_hour, close_min)

            return market_open <= current_time <= market_close

        return False


# ============================================================
# DATA FETCHERS
# ============================================================


class StockDataFetcher:
    """Fetches stock data using Yahoo Finance and Alpaca."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.api = None
        if ALPACA_AVAILABLE:
            try:
                self.api = tradeapi.REST(
                    config.get("alpaca_api_key"),
                    config.get("alpaca_secret_key"),
                    config.get("alpaca_base_url"),
                    api_version="v2",
                )
                logger.info("Alpaca API initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca: {e}")

    def get_top_movers(self, count: int = 100) -> List[PriceData]:
        """Get top stocks by daily percentage change."""
        stocks = []

        # Use Alpaca scanner if available
        if self.api:
            try:
                # Get active assets
                assets = self.api.list_assets(status="active", asset_class="us_equity")
                symbols = [a.symbol for a in assets[:500]]  # Limit for performance

                # Get snapshots (current data)
                snapshots = self.api.get_snapshots(symbols)

                for symbol, snapshot in snapshots.items():
                    if snapshot and snapshot.daily_bar:
                        bar = snapshot.daily_bar
                        stocks.append(
                            PriceData(
                                symbol=symbol,
                                price=bar.c,
                                open_price=bar.o,
                                high=bar.h,
                                low=bar.l,
                                volume=bar.v,
                                timestamp=datetime.now(),
                                asset_type=AssetType.STOCK,
                            )
                        )
            except Exception as e:
                logger.error(f"Alpaca fetch error: {e}")

        # Fallback to yfinance for top movers
        if not stocks and YFINANCE_AVAILABLE:
            stocks = self._get_top_movers_yfinance(count)

        # Sort by daily change percentage
        stocks.sort(key=lambda x: x.daily_change_pct, reverse=True)
        return stocks[:count]

    def _get_top_movers_yfinance(self, count: int) -> List[PriceData]:
        """Fallback using yfinance."""
        stocks = []
        # Major stock symbols for scanning
        major_symbols = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "TSLA",
            "META",
            "NVDA",
            "BRK-B",
            "JPM",
            "V",
            "JNJ",
            "WMT",
            "UNH",
            "PG",
            "HD",
            "MA",
            "BAC",
            "ABBV",
            "PFE",
            "KO",
            "AVGO",
            "PEP",
            "LLY",
            "TMO",
            "COST",
            "DIS",
            "ABT",
            "CSCO",
            "VZ",
            "ACN",
            "WFC",
            "ADBE",
            "CRM",
            "NKE",
            "TXN",
            "CMCSA",
            "NFLX",
            "QCOM",
            "NEE",
            "PM",
            "RTX",
            "HON",
            "BMY",
            "UPS",
            "LIN",
            "ORCL",
            "LOW",
            "CVX",
            "AMGN",
            "SBUX",
            "IBM",
            "MDT",
            "GS",
            "CAT",
            "DE",
            "SPGI",
            "BLK",
            "PLD",
            "T",
            "DHR",
            "INTU",
            "AMAT",
            "GILD",
            "ADI",
            "BKNG",
            "SYK",
            "LMT",
            "MU",
            "MDLZ",
            "TJX",
            "C",
            "ELV",
            "CI",
            "CB",
            "MMC",
            "ADP",
            "SO",
            "DUK",
            "AON",
            "ICE",
            "SHW",
            "ITW",
            "ZTS",
            "GE",
            "F",
            "GM",
            "UBER",
            "LYFT",
            "SNOW",
            "ZM",
            "ROKU",
            "SQ",
            "PYPL",
            "SHOP",
            "CRWD",
            "OKTA",
            "DDOG",
            "NET",
            "MDB",
            "FSLY",
            "TWLO",
            "DOCU",
            "PTON",
            "MRNA",
            "BNTX",
            "AMD",
            "INTC",
            "MU",
            "TSM",
            "ASML",
            "LRCX",
            "KLAC",
            "MRVL",
            "NXPI",
        ]

        for symbol in major_symbols[:count]:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    latest = hist.iloc[-1]
                    open_p = hist.iloc[0]["Open"]
                    stocks.append(
                        PriceData(
                            symbol=symbol,
                            price=latest["Close"],
                            open_price=open_p,
                            high=latest["High"],
                            low=latest["Low"],
                            volume=latest["Volume"],
                            timestamp=datetime.now(),
                            asset_type=AssetType.STOCK,
                        )
                    )
            except Exception as e:
                logger.debug(f"Error fetching {symbol}: {e}")

        return stocks

    def get_historical_data(
        self, symbol: str, period: str = "5d", interval: str = "5m"
    ) -> List[PriceData]:
        """Get historical price data for pattern analysis."""
        data = []

        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period, interval=interval)
                for idx, row in hist.iterrows():
                    data.append(
                        PriceData(
                            symbol=symbol,
                            price=row["Close"],
                            open_price=row["Open"],
                            high=row["High"],
                            low=row["Low"],
                            volume=row["Volume"],
                            timestamp=idx.to_pydatetime(),
                            asset_type=AssetType.STOCK,
                        )
                    )
            except Exception as e:
                logger.error(f"Error fetching historical for {symbol}: {e}")

        return data


class CryptoDataFetcher:
    """Fetches crypto data using Coinbase/Kraken via CCXT."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.exchange = None
        self._init_exchange()

    def _init_exchange(self):
        """Initialize the crypto exchange connection."""
        if not CCXT_AVAILABLE:
            logger.warning("CCXT not available. Install with: pip install ccxt")
            return

        # Try Kraken first (good for WA state)
        try:
            self.exchange = ccxt.kraken(
                {
                    "apiKey": self.config.get("kraken_api_key"),
                    "secret": self.config.get("kraken_api_secret"),
                    "enableRateLimit": True,
                }
            )
            self.exchange.load_markets()
            logger.info("Kraken exchange initialized")
            return
        except Exception as e:
            logger.warning(f"Kraken init failed: {e}")

        # Fallback to Coinbase
        try:
            self.exchange = ccxt.coinbase(
                {
                    "apiKey": self.config.get("coinbase_api_key"),
                    "secret": self.config.get("coinbase_api_secret"),
                    "enableRateLimit": True,
                }
            )
            self.exchange.load_markets()
            logger.info("Coinbase exchange initialized")
        except Exception as e:
            logger.warning(f"Coinbase init failed: {e}")

    def get_top_movers(self, count: int = 100) -> List[PriceData]:
        """Get top cryptos by daily percentage change."""
        cryptos = []

        if not self.exchange:
            logger.warning("No crypto exchange available")
            return cryptos

        try:
            # Get tickers for all markets
            tickers = self.exchange.fetch_tickers()

            for symbol, ticker in tickers.items():
                # Filter for USD pairs
                if "/USD" in symbol or "/USDT" in symbol:
                    try:
                        change_pct = ticker.get("percentage", 0) or 0
                        if change_pct != 0:
                            cryptos.append(
                                PriceData(
                                    symbol=symbol,
                                    price=ticker["last"],
                                    open_price=(
                                        ticker["open"]
                                        if ticker["open"]
                                        else ticker["last"] / (1 + change_pct / 100)
                                    ),
                                    high=ticker["high"],
                                    low=ticker["low"],
                                    volume=ticker["quoteVolume"]
                                    or ticker["baseVolume"],
                                    timestamp=datetime.now(),
                                    asset_type=AssetType.CRYPTO,
                                )
                            )
                    except Exception as e:
                        continue

            # Sort by daily change
            cryptos.sort(key=lambda x: abs(x.daily_change_pct), reverse=True)

        except Exception as e:
            logger.error(f"Error fetching crypto data: {e}")

        return cryptos[:count]

    def get_historical_data(
        self, symbol: str, timeframe: str = "5m", limit: int = 100
    ) -> List[PriceData]:
        """Get historical OHLCV data for pattern analysis."""
        data = []

        if not self.exchange:
            return data

        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            for candle in ohlcv:
                timestamp, open_p, high, low, close, volume = candle
                data.append(
                    PriceData(
                        symbol=symbol,
                        price=close,
                        open_price=open_p,
                        high=high,
                        low=low,
                        volume=volume,
                        timestamp=datetime.fromtimestamp(timestamp / 1000),
                        asset_type=AssetType.CRYPTO,
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching crypto history for {symbol}: {e}")

        return data


# ============================================================
# BREAKOUT DETECTION ENGINE
# ============================================================
class BreakoutDetector:
    """
    Pro-grade breakout detector:
    Focuses on EARLY breakout signals (before big moves happen)
    """

    def __init__(self, config):
        self.config = config
        self.price_history = {}
        self.volume_history = {}
        self.detected_signals = {}
        self.history_length = 50  # more context

    def update_history(self, price_data):
        symbol = price_data.symbol

        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.history_length)
            self.volume_history[symbol] = deque(maxlen=self.history_length)

        self.price_history[symbol].append(price_data.price)
        self.volume_history[symbol].append(price_data.volume)

    def detect_breakout(self, price_data):
        symbol = price_data.symbol
        self.update_history(price_data)

        if len(self.price_history[symbol]) < 25:
            return None

        prices = list(self.price_history[symbol])
        volumes = list(self.volume_history[symbol])

        # --- CORE SIGNAL COMPONENTS ---
        compression = self._is_compressing(prices)
        expansion = self._is_expanding(prices)
        early_volume = self._early_volume(volumes, prices)
        vwap_ok = self._near_vwap(prices, volumes)
        not_chasing = self._not_overextended(prices)

        momentum = self._momentum(prices)

        # --- SCORING SYSTEM ---
        score = 0.0

        if compression:
            score += 0.25
        if early_volume:
            score += 0.25
        if expansion:
            score += 0.20
        if vwap_ok:
            score += 0.15
        if momentum > 1:
            score += 0.10
        if not_chasing:
            score += 0.05

        # --- THRESHOLDS ---
        if score < 0.5:
            return None

        # cooldown (avoid spam)
        last = self.detected_signals.get(symbol)
        if last and (datetime.now() - last).seconds < 300:
            return None

        self.detected_signals[symbol] = datetime.now()

        # classify strength
        if score > 0.75:
            pattern = "early_breakout_strong"
        elif score > 0.6:
            pattern = "early_breakout"
        else:
            pattern = "watchlist"

        return BreakoutSignal(
            symbol=symbol,
            asset_type=price_data.asset_type,
            current_price=price_data.price,
            predicted_move_pct=score * 100,  # repurposed as strength
            confidence=score,
            volume_spike=self._volume_spike(volumes),
            momentum_score=momentum,
            pattern_detected=pattern,
            timestamp=datetime.now(),
            price_history=prices[-20:],
            volume_history=volumes[-20:],
        )

    # =========================================================
    # SIGNAL COMPONENTS
    # =========================================================

    def _is_compressing(self, prices):
        recent = prices[-20:]
        avg = sum(recent) / len(recent)
        range_pct = (max(recent) - min(recent)) / avg * 100
        return range_pct < 2.0  # tight range

    def _is_expanding(self, prices):
        move = (prices[-1] - prices[-3]) / prices[-3] * 100
        return move > 1.2  # breakout starting

    def _early_volume(self, volumes, prices):
        avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
        spike = volumes[-1] / avg_vol if avg_vol > 0 else 1

        price_change = (prices[-1] - prices[-5]) / prices[-5] * 100
        return spike > 2.5 and price_change < 2.0

    def _near_vwap(self, prices, volumes):
        total_vol = sum(volumes)
        if total_vol == 0:
            return False

        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_vol
        distance = abs(prices[-1] - vwap) / vwap * 100
        return distance < 1.0

    def _not_overextended(self, prices):
        move = (prices[-1] - prices[-10]) / prices[-10] * 100
        return move < 8  # avoid chasing

    def _momentum(self, prices):
        changes = [
            (prices[i] - prices[i - 1]) / prices[i - 1] * 100
            for i in range(1, len(prices))
        ]
        return sum(changes[-5:]) / 5 if len(changes) >= 5 else 0

    def _volume_spike(self, volumes):
        avg = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
        return volumes[-1] / avg if avg > 0 else 1


# ============================================================
# ALERT SYSTEM
# ============================================================


class AlertSystem:
    """Handles all types of alerts."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.alert_queue: queue.Queue = queue.Queue()
        self.alert_history: List[Alert] = []
        self.email_last_sent: Dict[str, datetime] = {}
        self.running = False

    def start(self):
        """Start the alert processing thread."""
        self.running = True
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()
        logger.info("Alert system started")

    def stop(self):
        """Stop the alert processing thread."""
        self.running = False
        logger.info("Alert system stopped")

    def send_alert(self, signal: BreakoutSignal):
        """Send all configured alert types for a signal."""
        message = self._format_alert_message(signal)

        if self.config.get("enable_sound_alert", True):
            self._sound_alert(signal)

        if self.config.get("enable_visual_alert", True):
            alert = Alert(
                signal=signal,
                alert_type=AlertType.VISUAL,
                message=message,
                timestamp=datetime.now(),
            )
            self.alert_queue.put(alert)

        if self.config.get("enable_email_alert", True):
            self._email_alert(signal, message)

    def _format_alert_message(self, signal: BreakoutSignal) -> str:
        meta = classify_signal(signal)

        direction = meta["direction"]
        stage = meta["stage"]
        poc = meta["poc"]

        strength = "HIGH" if poc > 75 else "MEDIUM" if poc > 60 else "LOW"

        reasons = []

        if signal.volume_spike > 2:
            reasons.append(f"Volume spike ({signal.volume_spike:.1f}x)")

        if signal.momentum_score > 0.5:
            reasons.append(f"Strong momentum ({signal.momentum_score:.2f})")

        if "compression" in signal.pattern_detected:
            reasons.append("Price compression detected")

        if "early" in signal.pattern_detected:
            reasons.append("Early breakout structure")

        if "strong" in signal.pattern_detected:
            reasons.append("Strong breakout pattern")

        reason_text = "\n- " + "\n- ".join(reasons) if reasons else "N/A"

        return f"""
    BREAKOUT SIGNAL

    Symbol: {signal.symbol}
    Type: {signal.asset_type.value.upper()}

    Direction: {direction}
    Stage: {stage}
    Continuation Probability: {poc:.0f}% ({strength})

    Price: ${signal.current_price:.4f}
    Score: {signal.predicted_move_pct:.0f}

    Volume Spike: {signal.volume_spike:.1f}x
    Momentum: {signal.momentum_score:.2f}

    Pattern: {signal.pattern_detected}

    Why this triggered:
    {reason_text}

    Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
    """.strip()


    def _sound_alert(self, signal):
        import time

        now = time.time()

        # create once
        if not hasattr(self, "_last_sound_time"):
            self._last_sound_time = 0

        # limit to 1 beep every 3 seconds
        if now - self._last_sound_time < 3:
            return

        self._last_sound_time = now

        try:
            import winsound
            winsound.Beep(1000, 300)
        except:
            pass

    def _email_alert(self, signal: BreakoutSignal, message: str):
        """Send email alert."""
        # Rate limit emails
        symbol = signal.symbol
        last_sent = self.email_last_sent.get(symbol)
        if last_sent and (datetime.now() - last_sent).seconds < 600:
            return

        try:
            smtp_server = self.config.get("email_smtp_server", "smtp.gmail.com")
            smtp_port = self.config.get("email_smtp_port", 587)
            email_from = self.config.get("email_from", "")
            email_to = self.config.get("email_to", "")
            password = self.config.get("email_password", "")

            if not all([email_from, email_to, password]):
                logger.warning("Email credentials not configured")
                return

            subject = (
                f"? BREAKOUT ALERT: {signal.symbol} (+{signal.predicted_move_pct:.1f}%)"
            )

            email_body = f"""From: {email_from}
To: {email_to}
Subject: {subject}

{message}
"""

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_from, password)
                server.sendmail(email_from, email_to, email_body)

            self.email_last_sent[symbol] = datetime.now()
            logger.info(f"Email alert sent for {symbol}")

        except Exception as e:
            logger.error(f"Email alert failed: {e}")

    def _process_alerts(self):
        """Process alerts from queue (for GUI updates)."""
        while self.running:
            try:
                alert = self.alert_queue.get(timeout=1)
                self.alert_history.append(alert)
                logger.info(f"Alert processed: {alert.signal.symbol}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Alert processing error: {e}")


# ============================================================
# TRADING ENGINE
# ============================================================


class TradingEngine:
    """Handles trade execution through configured brokers."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.alpaca_api = None
        self.crypto_exchange = None
        self.positions: Dict[str, dict] = {}
        self._init_brokers()

    def _init_brokers(self):
        """Initialize broker connections."""
        # Alpaca for stocks
        if ALPACA_AVAILABLE and self.config.get("broker") == "alpaca":
            try:
                self.alpaca_api = tradeapi.REST(
                    self.config.get("alpaca_api_key"),
                    self.config.get("alpaca_secret_key"),
                    self.config.get("alpaca_base_url"),
                    api_version="v2",
                )
                logger.info("Alpaca trading API initialized")
            except Exception as e:
                logger.error(f"Alpaca init failed: {e}")

        # CCXT for crypto
        if CCXT_AVAILABLE:
            try:
                self.crypto_exchange = ccxt.kraken(
                    {
                        "apiKey": self.config.get("kraken_api_key"),
                        "secret": self.config.get("kraken_api_secret"),
                        "enableRateLimit": True,
                    }
                )
            except Exception as e:
                logger.warning(f"Kraken trading init failed: {e}")
                try:
                    self.crypto_exchange = ccxt.coinbase(
                        {
                            "apiKey": self.config.get("coinbase_api_key"),
                            "secret": self.config.get("coinbase_api_secret"),
                            "enableRateLimit": True,
                        }
                    )
                except Exception as e2:
                    logger.error(f"Coinbase trading init failed: {e2}")

    def can_auto_trade(self) -> bool:
        """Check if auto-trading is enabled."""
        return self.config.get("enable_auto_trade", False)

    def should_confirm_trade(self) -> bool:
        """Check if user confirmation is required."""
        return not self.config.get("auto_trade_without_confirm", False)

    def place_stock_order(
        self, symbol: str, side: str, qty: float = None, notional: float = None
    ) -> dict:
        """Place a stock order through Alpaca."""
        if not self.alpaca_api:
            return {"error": "Alpaca API not available"}

        try:
            if notional:
                order = self.alpaca_api.submit_order(
                    symbol=symbol,
                    notional=notional,
                    side=side,
                    type="market",
                    time_in_force="day",
                )
            else:
                order = self.alpaca_api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type="market",
                    time_in_force="day",
                )

            logger.info(f"Stock order placed: {side} {symbol}")
            return {"success": True, "order_id": order.id, "status": order.status}

        except Exception as e:
            logger.error(f"Stock order failed: {e}")
            return {"error": str(e)}

    def place_crypto_order(self, symbol: str, side: str, amount: float) -> dict:
        """Place a crypto order through CCXT."""
        if not self.crypto_exchange:
            return {"error": "Crypto exchange not available"}

        try:
            order_type = "market"
            order = self.crypto_exchange.create_order(
                symbol=symbol, type=order_type, side=side, amount=amount
            )

            logger.info(f"Crypto order placed: {side} {amount} {symbol}")
            return {
                "success": True,
                "order_id": order.get("id"),
                "status": order.get("status"),
            }

        except Exception as e:
            logger.error(f"Crypto order failed: {e}")
            return {"error": str(e)}

    def execute_signal(self, signal: BreakoutSignal) -> dict:
        """Execute a trade based on breakout signal."""
        if not self.can_auto_trade():
            return {"status": "auto_trade_disabled"}

        if self.should_confirm_trade():
            return {"status": "confirmation_required", "signal": signal}

        # Auto-trade without confirmation
        amount = self.config.get("default_trade_amount_usd", 1000)

        if signal.asset_type == AssetType.STOCK:
            return self.place_stock_order(
                symbol=signal.symbol, side="buy", notional=amount
            )
        else:
            # For crypto, calculate amount based on current price
            qty = amount / signal.current_price
            return self.place_crypto_order(symbol=signal.symbol, side="buy", amount=qty)


# ============================================================
# GUI (Optional)
# ============================================================


class ScannerGUI:
    """Tkinter-based GUI for the scanner."""

    def __init__(self, scanner: "MarketScanner"):
        self.scanner = scanner
        self.root = None
        self.alert_text = None
        self.status_label = None
        self.running = False

    def start(self):
        """Start the GUI."""
        if not TKINTER_AVAILABLE:
            logger.warning("Tkinter not available, running in console mode")
            return

        self.root = tk.Tk()
        self.root.title("? Ron's Market Breakout Scanner")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a2e")

        self._setup_ui()
        self.running = True

        # Start update loop
        self._update_loop()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _setup_ui(self):
        """Setup the user interface."""
        # Title
        title = tk.Label(
            self.root,
            text="? BREAKOUT SCANNER",
            font=("Helvetica", 24, "bold"),
            bg="#1a1a2e",
            fg="#00ff88",
        )
        title.pack(pady=10)

        # Status frame
        status_frame = tk.Frame(self.root, bg="#16213e")
        status_frame.pack(fill="x", padx=20, pady=5)

        self.status_label = tk.Label(
            status_frame,
            text="Status: Initializing...",
            font=("Helvetica", 12),
            bg="#16213e",
            fg="#ffffff",
        )
        self.status_label.pack(side="left", padx=10)

        # Control buttons
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=20, pady=5)

        self.start_btn = tk.Button(
            btn_frame,
            text="? Start Scanner",
            command=self._start_scanner,
            bg="#00ff88",
            fg="#000000",
            font=("Helvetica", 12, "bold"),
            padx=20,
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(
            btn_frame,
            text="? Stop Scanner",
            command=self._stop_scanner,
            bg="#ff4444",
            fg="#ffffff",
            font=("Helvetica", 12, "bold"),
            padx=20,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5)

        # Auto-trade toggle
        self.auto_trade_var = tk.BooleanVar(value=False)
        self.auto_trade_check = tk.Checkbutton(
            btn_frame,
            text="Auto-Trade",
            variable=self.auto_trade_var,
            command=self._toggle_auto_trade,
            bg="#1a1a2e",
            fg="#ffffff",
            selectcolor="#16213e",
            font=("Helvetica", 11),
        )
        self.auto_trade_check.pack(side="left", padx=20)

        # Alert area
        alert_frame = tk.LabelFrame(
            self.root,
            text="? LIVE ALERTS",
            font=("Helvetica", 14, "bold"),
            bg="#16213e",
            fg="#ffaa00",
            padx=10,
            pady=10,
        )
        alert_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.alert_text = scrolledtext.ScrolledText(
            alert_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#0f0f23",
            fg="#00ff88",
            insertbackground="#ffffff",
            state="disabled",
        )
        self.alert_text.pack(fill="both", expand=True)

        # Top movers display
        movers_frame = tk.LabelFrame(
            self.root,
            text="? Stock Top Movers  (Performance)",
            font=("Helvetica", 14, "bold"),
            bg="#16213e",
            fg="#00ccff",
            padx=10,
            pady=10,
        )
        movers_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.movers_text = scrolledtext.ScrolledText(
            movers_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#0f0f23",
            fg="#00ccff",
            height=10,
            state="disabled",
        )
        self.movers_text.pack(fill="both", expand=True)

    def _start_scanner(self):
        """Start the scanner."""
        self.scanner.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text="Status: SCANNING ?", fg="#00ff88")

    def _stop_scanner(self):
        """Stop the scanner."""
        self.scanner.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="Status: STOPPED", fg="#ff4444")

    def _toggle_auto_trade(self):
        """Toggle auto-trading."""
        enabled = self.auto_trade_var.get()
        self.scanner.config.set("enable_auto_trade", enabled)
        logger.info(f"Auto-trade {'enabled' if enabled else 'disabled'}")

    def _update_loop(self):
        """Update GUI periodically."""
        if not self.running:
            return

        # Update alerts
        self._update_alerts()

        # Update top movers
        self._update_movers()

        self.root.after(1000, self._update_loop)

    def _update_alerts(self):
        """Update alert display."""
        alerts = self.scanner.alert_system.alert_history[-10:]

        self.alert_text.config(state="normal")
        self.alert_text.delete("1.0", tk.END)

        for alert in reversed(alerts):
            self.alert_text.insert(tk.END, f"[{alert.timestamp.strftime('%H:%M:%S')}]")
            self.alert_text.insert(tk.END, f" {alert.signal.symbol}", "symbol")

            self.alert_text.insert(
                tk.END, f" | Score: {alert.signal.predicted_move_pct:.0f}"
            )

            self.alert_text.insert(
                tk.END, f" | Confidence: {alert.signal.confidence*100:.0f}%\n"
            )

            self.alert_text.insert(
                tk.END, f"   Pattern: {alert.signal.pattern_detected}\n"
            )

            self.alert_text.insert(tk.END, "-" * 60 + "\n")

        self.alert_text.config(state="disabled")

    def _update_movers(self):
        """Update top movers display."""
        movers = self.scanner.latest_movers[:20]

        self.movers_text.config(state="normal")
        self.movers_text.delete("1.0", tk.END)

        for i, mover in enumerate(movers, 1):
            color = "#00ff88" if mover.daily_change_pct > 0 else "#ff4444"
            self.movers_text.insert(tk.END, f"{i:2d}. {mover.symbol:8s} ")
            self.movers_text.insert(tk.END, f"{mover.daily_change_pct:+.2f}%\n")

        self.movers_text.config(state="disabled")

    def _on_close(self):
        """Handle window close."""
        self.running = False
        self.scanner.stop()
        self.root.destroy()


# ============================================================
# MAIN SCANNER
# ============================================================


class MarketScanner:
    """Main scanner orchestrator."""

    def __init__(self):
        self.config = ConfigManager()
        self.stock_fetcher = StockDataFetcher(self.config)
        self.crypto_fetcher = CryptoDataFetcher(self.config)
        self.detector = BreakoutDetector(self.config)
        self.alert_system = AlertSystem(self.config)
        self.trading = TradingEngine(self.config)

        self.latest_movers: List[PriceData] = []
        self.running = False
        self.scan_thread = None
        self.gui = None

    def start(self):
        """Start the scanner."""
        if self.running:
            return

        self.running = True
        self.alert_system.start()

        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()

        logger.info("=" * 50)
        logger.info("MARKET SCANNER STARTED")
        logger.info("=" * 50)

    def stop(self):
        """Stop the scanner."""
        self.running = False
        self.alert_system.stop()

        if self.scan_thread:
            self.scan_thread.join(timeout=5)

        logger.info("Scanner stopped")

    def _scan_loop(self):
        """Main scanning loop."""
        while self.running:
            try:
                # Check stock market hours
                if self.config.is_market_open(AssetType.STOCK):
                    self._scan_stocks()

                # Crypto scans 24/7
                if self.config.is_market_open(AssetType.CRYPTO):
                    self._scan_cryptos()
                update_signal_tracking(self)                     # Sleep between scans
                interval = self.config.get("scan_interval_seconds", 30)
                time.sleep(interval)

            except Exception as e:
                logger.error(f"Scan loop error: {e}")
                time.sleep(5)

    def should_log_signal(self, signal):
        from datetime import datetime

        if not hasattr(self, "recent_signals"):
            self.recent_signals = {}

        key = signal.symbol
        now = datetime.now()

        last_time = self.recent_signals.get(key)

        # â± 10 minute cooldown (adjustable)
        if last_time and (now - last_time).total_seconds() < 600:
            return False

        self.recent_signals[key] = now
        return True

    def _scan_stocks(self):
        """Scan stocks for breakout patterns."""
        logger.info("Scanning stocks...")

        try:
            movers = self.stock_fetcher.get_top_movers(
                self.config.get("top_stocks_count", 100)
            )
            self.latest_movers = movers

            for stock in movers:

                hist = self.stock_fetcher.get_historical_data(stock.symbol)

                for h in hist:
                    self.detector.update_history(h)

                signal = self.detector.detect_breakout(stock)

                if not signal:
                    continue

                meta = classify_signal(signal)

                if meta["direction"] != "LONG":
                    continue

                if meta["poc"] < 60:
                    continue

                if signal.confidence > 0.5:

                    if not self.should_log_signal(signal):
                        continue

                    # ðŸ”¥ NEW FILTER RULES
                    # TEMP disabled filter

                    # Optional: require stronger signals
                    # TEMP disabled filter
                    source = self.crypto_fetcher.exchange.id.upper()
                    logger.warning(
                       
                        f"? STOCK BREAKOUT: {source} {signal.symbol} | " 
                        f"Score: {signal.predicted_move_pct:.0f} | "
                        f"Confidence: {signal.confidence*100:.0f}%"
                    )

                    log_signal_to_csv(signal)

                if signal.confidence > 0.5:
                    if not self.should_log_signal(signal):
                        continue
                    source = self.crypto_fetcher.exchange.id.upper()
                    logger.warning(
                        f"? STOCK BREAKOUT: {source} {signal.symbol} | "
                        f"Score: {signal.predicted_move_pct:.0f} | "
                        f"Confidence: {signal.confidence*100:.0f}%" 
                    )
                    log_signal_to_csv(signal)


                    if self.trading.can_auto_trade():
                        if self.trading.should_confirm_trade():
                            logger.info(
                                f"Trade confirmation required for {signal.symbol}"
                            )
                        else:
                            result = self.trading.execute_signal(signal)
                            logger.info(f"Auto-trade result: {result}")

        except Exception as e:
            logger.error(f"Stock scan error: {e}")

    def _scan_cryptos(self):         
        """Scan cryptos for breakout patterns."""         
        logger.info("Scanning cryptos...")          
        try:            
            movers = self.crypto_fetcher.get_top_movers(                
                self.config.get("top_cryptos_count", 100)             
                )             
            logger.info(f"MOVERS COUNT: {len(movers) 
                                         if movers else 0}")              
            for crypto in movers:                 
                if crypto.symbol not in self.crypto_fetcher.exchange.symbols:                     
                    continue                  
                hist = self.crypto_fetcher.get_historical_data(crypto.symbol)                  
                for h in hist:                     
                    self.detector.update_history(h)                  
                    signal = self.detector.detect_breakout(crypto)                  
                    if not signal:                     
                        continue                  
                    # per-symbol cooldown (60 sec)                 
                    # now = time.time()                 
                    # if not hasattr(self, "_last_alerts"):                     s
                    # elf._last_alerts = {}                  
                    # last = self._last_alerts.get(crypto.symbol)                 
                    # if last and now - last < 60:                     
                    # continue                  
                    # self._last_alerts[crypto.symbol] = now                  
                    # meta = classify_signal(signal)                  
                    # if signal.confidence < 0.4:                     
                    # continue                  
                    # if meta["poc"] < 40:                     
                    # continue                  
                    # logger.info(f"SIGNAL FOUND: {crypto.symbol}")                  
                    # self.alert_system.send_alert(signal)                  
                    # log_signal_to_csv(signal)          
                    # except Exception as e:             
                    # logger.error(f"Crypto scan failed: {e}")

    def _scan_stocks_backup_backup(self):
        """Scan stocks for breakout patterns."""
        logger.info("Scanning stocks...")

        try:
            movers = self.stock_fetcher.get_top_movers(
                self.config.get("top_stocks_count", 100)
            )
            self.latest_movers = movers

            for stock in movers:

                hist = self.stock_fetcher.get_historical_data(stock.symbol)

                for h in hist:
                    self.detector.update_history(h)

                signal = self.detector.detect_breakout(stock)

                if not signal:
                    continue
                meta = classify_signal(signal)

                if meta["direction"] != "LONG":
                    continue

                if meta["poc"] < 60:
                    continue

                if signal.confidence > 0.5:
                    source = self.crypto_fetcher.exchange.id.upper()
                    logger.warning(
                        f"? STOCK BREAKOUT: {source} | {signal.symbol} | "
                        f"Score: {signal.predicted_move_pct:.0f} | "
                        f"Confidence: {signal.confidence*100:.0f}%"
                    )

                    if self.trading.can_auto_trade():
                        if self.trading.should_confirm_trade():
                            logger.info(
                                f"Trade confirmation required for {signal.symbol}"
                            )
                        else:
                            result = self.trading.execute_signal(signal)
                            logger.info(f"Auto-trade result: {result}")

        except Exception as e:
            logger.error(f"Crypto scan error: {e}")

    def run_gui(self):
        """Run with GUI."""
        self.gui = ScannerGUI(self)
        self.gui.start()


def run_console(self):
    """Run in console mode."""
    self.start()

    print("\n" + "=" * 60)
    print("  ? RON'S MARKET BREAKOUT SCANNER")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scanner...")
        self.stop()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    scanner = MarketScanner()

    if TKINTER_AVAILABLE:
        scanner.run_gui()
    else:
        scanner.run_console()



