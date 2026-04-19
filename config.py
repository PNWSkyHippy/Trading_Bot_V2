"""
config.py — All settings, API keys, and tunable parameters
Trading Bot v2
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# API KEYS (loaded from .env)
# =============================================================================

ALPACA_API_KEY      = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY   = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL     = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

COINBASE_API_KEY    = os.getenv("COINBASE_API_KEY", "")
COINBASE_SECRET_KEY = os.getenv("COINBASE_SECRET_KEY", "")

KRAKEN_API_KEY      = os.getenv("KRAKEN_API_KEY", "")
KRAKEN_SECRET_KEY   = os.getenv("KRAKEN_SECRET_KEY", "")
KRAKEN_ENABLED      = False            # Set True only when ready for live Kraken trading

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")

EMAIL_SENDER        = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD      = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT     = os.getenv("EMAIL_RECIPIENT", "")

# =============================================================================
# CAPITAL & TRADING PARAMETERS
# =============================================================================

STARTING_CAPITAL        = 100000.00    # USD — matches Alpaca paper balance
BOT_CAPITAL_ALLOCATION  = 0.00         # Bot's share of account. 0 = use full balance. e.g. 500.00
DAILY_PROFIT_TARGET_PCT = 2.0          # % daily profit goal
GOAL_CAPITAL            = 1038198.96   # Final goal amount
GOAL_DAYS               = 480          # 1 year, 3 months, 10 days

# Position sizing
MAX_POSITION_PCT        = 2.0          # % of total capital per trade
MIN_SIGNAL_CONFIDENCE   = 0.65         # Minimum score to enter a trade (0.0–1.0) was .65

# Stop-loss / take-profit defaults
DEFAULT_STOP_LOSS_PCT   = 1.5          # % below entry price
DEFAULT_TAKE_PROFIT_PCT = 3.0          # % above entry price
TRAILING_STOP_PCT       = 1.5          # Trailing stop stays this % behind price

# Momentum rider — when price hits TP, check live momentum before closing.
# If momentum is strong, extend TP another DEFAULT_TAKE_PROFIT_PCT% and let
# the trailing stop protect profits.  When momentum fades the trailing stop
# exits; at MAX_EXTENSIONS the trade closes normally regardless of momentum.
MOMENTUM_RIDER_ENABLED        = True   # Master on/off switch
MOMENTUM_RIDER_RSI_MIN        = 55.0   # RSI must be at or above this (and rising)
MOMENTUM_RIDER_VOL_RATIO      = 1.2    # Current bar volume must be ≥ Nx the 20-bar avg
MOMENTUM_RIDER_MIN_SCORE      = 0.67   # Fraction of signals that must agree (2 of 3)
MOMENTUM_RIDER_MAX_EXTENSIONS = 3      # Max TP pushes per trade before forcing close

# Risk circuit breakers
# With a strong 3:1 R:R ratio, consecutive loss halts are too reactive.
# Daily loss % is the primary safety net. Consecutive losses logged but not halted.
MAX_DAILY_LOSS_PCT      = 15.0         # Halt trading if daily loss exceeds this %
MAX_CONSECUTIVE_LOSSES  = 10           # Raised — R:R ratio protects us, not loss streaks
MAX_OPEN_POSITIONS      = 30           # Maximum simultaneous open trades

# =============================================================================
# MOMENTUM RIDER
# Extends take-profit when momentum confirms continuation at TP level.
# Max 3 extensions = max 12% total gain before forced close.
# Set MOMENTUM_RIDER_ENABLED = False to disable and revert to standard TP close.
# =============================================================================
MOMENTUM_RIDER_ENABLED        = True
MOMENTUM_RIDER_MAX_EXTENSIONS = 3      # Hard cap — closes after 3 extensions
MOMENTUM_RIDER_MIN_SCORE      = 0.67   # 2 of 3 signals must confirm
MOMENTUM_RIDER_RSI_MIN        = 50     # RSI floor — must be above midline
MOMENTUM_RIDER_VOL_RATIO      = 1.3    # Volume must be 1.3x 20-bar average


# Price filters
STOCK_MIN_PRICE     = 0.40         # Ignore stocks below this price was 1.0
STOCK_MAX_PRICE     = 5000.00          # Ignore stocks above this price
STOCK_MIN_VOLUME    = 100000           # Minimum average daily volume
CRYPTO_MIN_PRICE    = 0.001            # Ignore crypto below $0.001 (filters PEPE/SHIB noise)
CRYPTO_MAX_PRICE    = 999999.00        # No upper limit on crypto

# Inverse ETF / Leveraged ETF settings
USE_LEVERAGED_LONGS = False   # True = use SOXL/TQQQ etc for bullish signals
                                       # False = use regular ETFs only (safer default)

# Cash account / PDT settings
CASH_ACCOUNT_MODE   = True             # True = T+2 settlement tracking (avoids PDT)
SETTLEMENT_DAYS     = 2               # T+2 standard settlement period

# Market timing (Eastern Time)
MARKET_OPEN_BUFFER_MIN  = 30           # Skip first N minutes after market open
STOCK_SCAN_INTERVAL_SEC = 60           # How often to scan stocks (seconds)
CRYPTO_SCAN_INTERVAL_SEC= 300          # How often to scan crypto (seconds, 5 min)

# =============================================================================
# BROKER SETTINGS
# =============================================================================

ALPACA_PAPER_MODE   = True             # True = paper trading, False = live
KRAKEN_PAPER_MODE   = True             # True = use Kraken sandbox

# =============================================================================
# WATCHLISTS
# Loaded from watchlists/stocks.txt and watchlists/crypto.txt
# Edit those files directly — no need to touch this code.
# Lines starting with # are comments. One symbol per line.
# =============================================================================

def _load_watchlist(filepath: str, fallback: list) -> list:
    """Load a watchlist from a text file, falling back to hardcoded list."""
    try:
        with open(filepath, "r") as f:
            symbols = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        if symbols:
            return symbols
    except FileNotFoundError:
        pass
    return fallback

_STOCK_FALLBACK = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "AMD",  "INTC", "BABA",  "NFLX", "SPY",  "QQQ",  "IWM",
    "JPM",  "BAC",  "GS",    "XOM",  "CVX",  "PFE",
]

_CRYPTO_FALLBACK = [
    "BTC/USD",  "ETH/USD",  "SOL/USD",  "ADA/USD",
    "MATIC/USD","DOT/USD",  "AVAX/USD", "LINK/USD",
    "LTC/USD",  "XRP/USD",
]

STOCK_WATCHLIST  = _load_watchlist("watchlists/stocks.txt",  _STOCK_FALLBACK)
CRYPTO_WATCHLIST = _load_watchlist("watchlists/crypto.txt",  _CRYPTO_FALLBACK)

# =============================================================================
# DATABASE
# =============================================================================

DB_PATH = "data/trading_bot.db"

# =============================================================================
# REPORTING
# =============================================================================

EOD_REPORT_HOUR_ET  = 17              # 5:00 PM Eastern — end of day report
ML_RETRAIN_HOUR_ET  = 18              # 6:00 PM Eastern — ML model retrain
CAPITAL_SYNC_MIN    = 15              # Sync broker balances every N minutes
ML_MIN_TRADES       = 50              # Minimum trades before ML model trains

# =============================================================================
# STRATEGY AUTO-DISABLE
# =============================================================================

STRATEGY_MIN_TRADES         = 20      # Trades needed before evaluation begins
STRATEGY_DISABLE_WIN_RATE   = 45.0    # Disable if win rate drops below this %
STRATEGY_REENABLE_WIN_RATE  = 50.0    # Re-enable when win rate recovers to this %

# =============================================================================
# VERBOSE MODE
# Set by --verbose flag at startup. Do not change this manually —
# it is overridden in bot_engine.py based on command-line argument.
# =============================================================================

VERBOSE_MODE = False

# =============================================================================
# SIGNAL FINE-TUNING
# All signal thresholds are here so you can adjust them without digging
# through strategy files. Changes take effect on the NEXT bot startup.
# While in paper trading mode, feel free to experiment — worst case is
# a few bad paper trades that teach you where to recalibrate.
# =============================================================================

SIGNAL_TUNING = {

    # -------------------------------------------------------------------------
    # GLOBAL
    # -------------------------------------------------------------------------
    # Minimum confidence score (0.0–1.0) for any trade to execute.
    # If you're seeing zero trades, try lowering this to 0.50 or 0.45. WAS .65
    "min_signal_confidence":        0.65,

    # -------------------------------------------------------------------------
    # ORIGINAL SCANNER — market_scanner.py (StockScanner / CryptoScanner)
    # These are the classic multi-indicator scores used before the 8 strategies.
    # The scanner still runs but routes through the strategy engine.
    # -------------------------------------------------------------------------

    # Stock thresholds
    "stock_rsi_oversold":           35,     # RSI below this → buy signal
    "stock_rsi_overbought":         65,     # RSI above this → sell signal
    "stock_rsi_weight":             2.0,    # Points awarded for RSI signal
    "stock_macd_weight":            2.5,    # Points for MACD histogram crossover
    "stock_ema_weight":             2.0,    # Points for EMA alignment
    "stock_bb_weight":              1.5,    # Points for Bollinger Band touch
    "stock_volume_weight":          1.0,    # Points for volume spike
    "stock_volume_spike_ratio":     1.5,    # Volume must be Nx the average
    "stock_bb_lower_pct":           0.05,   # BB lower band touch threshold (5%)
    "stock_bb_upper_pct":           0.95,   # BB upper band touch threshold (95%)

    # Crypto thresholds (slightly wider RSI range than stocks)
    "crypto_rsi_oversold":          38,
    "crypto_rsi_overbought":        62,
    "crypto_rsi_weight":            2.5,
    "crypto_macd_weight":           2.5,
    "crypto_ema_weight":            2.0,
    "crypto_bb_weight":             1.5,
    "crypto_volume_weight":         1.0,
    "crypto_volume_spike_ratio":    1.5,
    "crypto_bb_lower_pct":          0.05,
    "crypto_bb_upper_pct":          0.95,

    # -------------------------------------------------------------------------
    # STRATEGY 1: RSI Momentum
    # Enters when RSI crosses back from oversold or overbought territory.
    # Lower oversold = fewer but stronger buy signals.
    # -------------------------------------------------------------------------
    "rsi_momentum_oversold":        30,     # Long entry: RSI crosses back above this
    "rsi_momentum_overbought":      70,     # Short entry: RSI crosses back below this
    "rsi_momentum_period":          14,     # RSI lookback period (candles)
    "rsi_momentum_min_score":       0.60,   # Minimum score for this strategy to fire

    # -------------------------------------------------------------------------
    # STRATEGY 2: Bollinger Breakout
    # Enters when price breaks outside the Bollinger Bands.
    # Squeeze condition (tight bands) strengthens the signal.
    # -------------------------------------------------------------------------
    "bb_breakout_period":           20,     # BB moving average period
    "bb_breakout_std":              2.0,    # Standard deviations for band width
    "bb_squeeze_threshold":         0.04,   # Band width ratio — below = squeeze
    "bb_breakout_min_score":        0.70,

    # -------------------------------------------------------------------------
    # STRATEGY 3: EMA Crossover
    # Enters when fast EMA crosses above/below slow EMA.
    # Trend EMA (50) used to confirm direction.
    # -------------------------------------------------------------------------
    "ema_fast_period":              9,      # Fast EMA period
    "ema_slow_period":              21,     # Slow EMA period
    "ema_trend_period":             50,     # Trend confirmation EMA period
    "ema_crossover_min_score":      0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 4: Mean Reversion
    # Fades extreme price deviations — bets price returns to the mean.
    # Higher z-score = stronger signal but fewer opportunities.
    # -------------------------------------------------------------------------
    "mean_rev_zscore_entry":        2.0,    # Z-score deviation required to enter
    "mean_rev_period":              20,     # Lookback period for mean/std
    "mean_rev_min_score":           0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 5: Scalp Master
    # Very tight stops (0.5%), quick 1% profit targets.
    # Needs higher volume confirmation to avoid noise.
    # -------------------------------------------------------------------------
    "scalp_rsi_oversold":           35,
    "scalp_rsi_overbought":         65,
    "scalp_rsi_period":             7,      # Shorter RSI period for scalping
    "scalp_min_volume_ratio":       1.2,    # Volume must be 1.2x average
    "scalp_min_score":              0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 6: Swing Trader
    # Wider stops (2.5%), bigger targets (6%). Needs trending market.
    # ADX measures trend strength — raise this to only trade strong trends.
    # -------------------------------------------------------------------------
    "swing_adx_min":                20,     # ADX must exceed this (trend strength)
    "swing_adx_period":             14,
    "swing_rsi_oversold":           40,
    "swing_rsi_overbought":         60,
    "swing_min_score":              0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 7: Grid Bot
    # Profits from ranging (sideways) markets by placing a grid of orders.
    # Only activates when ADX shows market is NOT trending.
    # -------------------------------------------------------------------------
    "grid_adx_max":                 20,     # ADX must be BELOW this (ranging market)
    "grid_adx_period":              14,
    "grid_bb_period":               30,
    "grid_min_score":               0.70,

    # -------------------------------------------------------------------------
    # STRATEGY 8: DCA Accumulator
    # Buys dips on blue-chip stocks and major crypto.
    # Only enters long — buys when price is below EMA50 by dip_pct.
    # -------------------------------------------------------------------------
    "dca_ema_period":               50,
    "dca_dip_pct":                  0.02,   # Price must be 2% below EMA50
    "dca_rsi_max":                  45,     # RSI must confirm oversold condition
    "dca_min_score":                0.60,

    # -------------------------------------------------------------------------
    # ML SCORER BOOST
    # The Random Forest model can boost a signal's score by this multiplier.
    # 1.0 = no boost, 1.5 = 50% boost possible from ML confirmation.
    # -------------------------------------------------------------------------
    "ml_score_multiplier":          1.5,
    "ml_min_confidence":            0.55,   # ML must be at least this confident to boost
}
