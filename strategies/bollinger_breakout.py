"""
bollinger_breakout.py — Strategy 2: Bollinger Breakout
Trading Bot v2

Enters when price breaks outside the Bollinger Bands.
A squeeze condition (tight bands) strengthens the signal significantly.

Long:  Price breaks above upper band
Short: Price breaks below lower band

Thresholds configurable in config.SIGNAL_TUNING.

Symbol blacklist: backtest data (30d 5m, Apr 2026) showed SMCI producing
catastrophic outlier losses ($53 largest loss vs $7 avg win) due to extreme
intraday volatility and thin liquidity on 5m bars. All other symbols showed
positive returns and acceptable risk metrics.
"""

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta
import numpy as np

import config
from strategies.base_strategy import BaseStrategy, TradeSignal


# Symbols excluded from Bollinger Breakout on 5m bars.
# SMCI: extreme intraday volatility causes outsized losses that dwarf avg wins.
# Update after each monthly backtest review.
BOLLINGER_BLACKLIST = {"SMCI"}
# Crypto pairs blacklisted based on Apr 2026 backtest (365d 1h)
# These showed significant negative returns — counter-trend losers
BOLLINGER_CRYPTO_BLACKLIST = {
    "TON/USD", "AGIX/USD", "HOT/USD", "STRK/USD", "EOS/USD",
    "OCEAN/USD", "REN/USD", "MKR/USD", "BAL/USD", "HT/USD",
    "XMR/USD", "GT/USD", "ARB/USD", "BCH/USD", "XTZ/USD",
    "RLC/USD", "FLOW/USD", "OKB/USD",
}

class BollingerBreakout(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name   = "bollinger_breakout"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT
        self.logger = logging.getLogger("BollingerBreakout")

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        # ----------------------------------------------------------------
        # Symbol blacklist — exclude symbols with proven destructive behavior
        # on 5m bars. SMCI showed $53 max loss vs $7 avg win in Apr 2026.
        # ----------------------------------------------------------------
        if symbol.upper() in BOLLINGER_BLACKLIST:
            self.verbose_log_skip(
                symbol,
                f"In Bollinger blacklist — skipping "
                f"(excluded: {', '.join(sorted(BOLLINGER_BLACKLIST))})"
            )
            return None

        tuning      = config.SIGNAL_TUNING
        period      = tuning["bb_breakout_period"]
        std_dev     = tuning["bb_breakout_std"]
        squeeze_thr = tuning["bb_squeeze_threshold"]
        min_score   = tuning["bb_breakout_min_score"]

        required = period + 5
        if not self._check_enough_candles(symbol, candles, required):
            return None

        # Calculate Bollinger Bands
        try:
            bb = ta.bbands(candles["close"], length=period, std=std_dev)
            if bb is None or bb.empty:
                self.verbose_log_skip(symbol, "Bollinger Bands calculation returned no data")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"Bollinger Bands error: {e}")
            return None

        # Column names from pandas_ta: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0
        col_lower = [c for c in bb.columns if c.startswith("BBL_")]
        col_upper = [c for c in bb.columns if c.startswith("BBU_")]
        col_mid   = [c for c in bb.columns if c.startswith("BBM_")]

        if not col_lower or not col_upper or not col_mid:
            self.verbose_log_skip(symbol, "Could not find BB column names in output")
            return None

        lower = bb[col_lower[0]].iloc[-1]
        upper = bb[col_upper[0]].iloc[-1]
        mid   = bb[col_mid[0]].iloc[-1]
        close = candles["close"].iloc[-1]

        if pd.isna(lower) or pd.isna(upper) or pd.isna(mid):
            self.verbose_log_skip(symbol, "Bollinger Band values are NaN")
            return None

        # Check for squeeze: band width as ratio of midline
        band_width = (upper - lower) / mid if mid != 0 else 1.0
        squeeze    = band_width < squeeze_thr

        self.verbose_log(
            symbol, "Bollinger Band squeeze (increases signal strength)",
            squeeze, band_width, f"<{squeeze_thr}",
            extra=f"upper={upper:.4f} lower={lower:.4f} mid={mid:.4f}"
        )

        squeeze_bonus = 0.10 if squeeze else 0.0
        """""
        # ----------------------------------------------------------------
        # OBV CONFIRMATION — filter fake breakouts with no volume support
        # OBV must be trending up over last 3 bars for long signals,
        # and down for short signals. Neutral/flat OBV = skip.
        # ----------------------------------------------------------------
        try:
            obv = ta.obv(candles["close"], candles["volume"])
            #if obv is None or len(obv) < 4:
            if obv is None or len(obv) < 2:
                self.verbose_log_skip(symbol, "OBV: insufficient data for confirmation")
                return None
            obv_now     = obv.iloc[-1]
            #obv_prev    = obv.iloc[-4]
            obv_prev    = obv.iloc[-2]
            obv_rising  = obv_now > obv_prev
            obv_falling = obv_now < obv_prev
            self.logger.info(f"[OBV] {symbol}: rising={obv_rising} falling={obv_falling} now={round(obv_now,0)} prev={round(obv_prev,0)}")
            self.verbose_log(
                symbol, "OBV direction check",
                obv_rising or obv_falling,
                round(obv_now, 0),
                f"prev={round(obv_prev, 0)}",
                extra=f"rising={obv_rising} falling={obv_falling}"
            )
        except Exception as e:
            self.verbose_log_skip(symbol, f"OBV calculation error: {e}")
            return None
        """""
        # ----------------------------------------------------------------
        # CRYPTO BLACKLIST — pairs with confirmed negative edge on 1h bars
        # ----------------------------------------------------------------
        if "/" in symbol and symbol.upper() in BOLLINGER_CRYPTO_BLACKLIST:
            self.verbose_log_skip(symbol, f"In crypto blacklist — skipping {symbol}")
            return None

        # ----------------------------------------------------------------
        # EMA200 TREND FILTER — only trade with the trend
        # Long signals require price above EMA200 (uptrend)
        # Short signals require price below EMA200 (downtrend)
        # Filters counter-trend trades which are the biggest losers
        # ----------------------------------------------------------------
        try:
            ema200 = ta.ema(candles["close"], length=200)
            if ema200 is None or len(ema200) < 1 or pd.isna(ema200.iloc[-1]):
                self.verbose_log_skip(symbol, "EMA200: insufficient data")
                return None
            ema200_val = ema200.iloc[-1]
            price_above_ema200 = close > ema200_val
            self.logger.info(f"[EMA200] {symbol}: close={close:.4f} ema200={ema200_val:.4f} above={price_above_ema200}")
        except Exception as e:
            self.verbose_log_skip(symbol, f"EMA200 calculation error: {e}")
            return None

        # ----------------------------------------------------------------
        # RSI DIRECTION FILTER — RSI must be moving the right way
        # Long: RSI rising over last 3 bars (momentum building up)
        # Short: RSI falling over last 3 bars (momentum building down)
        # ----------------------------------------------------------------
        try:
            rsi = ta.rsi(candles["close"], length=14)
            if rsi is None or len(rsi) < 4:
                self.verbose_log_skip(symbol, "RSI: insufficient data for direction check")
                return None
            rsi_now  = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-4]
            rsi_rising  = rsi_now > rsi_prev
            rsi_falling = rsi_now < rsi_prev
            self.logger.info(f"[RSI] {symbol}: now={rsi_now:.1f} prev={rsi_prev:.1f} rising={rsi_rising} falling={rsi_falling}")
        except Exception as e:
            self.verbose_log_skip(symbol, f"RSI direction check error: {e}")
            return None

        # ----------------------------------------------------------------
        # LONG SIGNAL: price breaks above upper band
        # ----------------------------------------------------------------
        breaks_upper = close > upper
        self.verbose_log(
            symbol, "Price breaks above upper Bollinger Band (long)",
            breaks_upper, close, f">{upper:.4f}", "long"
        )

        if breaks_upper:
            if not obv_rising:
                self.logger.info(f"[OBV] {symbol}: LONG rejected — OBV not rising (rising={obv_rising})")
                return None
            if not price_above_ema200:
                self.logger.info(f"[EMA200] {symbol}: LONG rejected — price below EMA200 (counter-trend)")
                return None
            if not rsi_rising:
                self.logger.info(f"[RSI] {symbol}: LONG rejected — RSI not rising (rsi_now={rsi_now:.1f})")
                return None

            breakout_pct = (close - upper) / upper if upper != 0 else 0
            score = min(1.0, min_score + squeeze_bonus + breakout_pct * 2)
            self.verbose_log_score(symbol, score, min_score)

            if score >= min_score:
                return self._make_signal(
                    symbol    = symbol,
                    direction = "long",
                    score     = score,
                    reason    = (
                        f"BB upper breakout: close={close:.4f} > upper={upper:.4f} "
                        f"{'(squeeze!)' if squeeze else ''}"
                    )
                )

        # ----------------------------------------------------------------
        # SHORT SIGNAL: price breaks below lower band
        # ----------------------------------------------------------------
        breaks_lower = close < lower
        self.verbose_log(
            symbol, "Price breaks below lower Bollinger Band (short)",
            breaks_lower, close, f"<{lower:.4f}", "short"
        ) 
        if breaks_lower:
            if not obv_falling:
                self.logger.info(f"[OBV] {symbol}: SHORT rejected — OBV not falling (falling={obv_falling})")
                return None
            if price_above_ema200:
                self.logger.info(f"[EMA200] {symbol}: SHORT rejected — price above EMA200 (counter-trend)")
                return None
            if not rsi_falling:
                self.logger.info(f"[RSI] {symbol}: SHORT rejected — RSI not falling (rsi_now={rsi_now:.1f})")
                return None
            
            breakout_pct = (lower - close) / lower if lower != 0 else 0
            score = min(1.0, min_score + squeeze_bonus + breakout_pct * 2)
            self.verbose_log_score(symbol, score, min_score)

            if score >= min_score:
                return self._make_signal(
                    symbol    = symbol,
                    direction = "short",
                    score     = score,
                    reason    = (
                        f"BB lower breakout: close={close:.4f} < lower={lower:.4f} "
                        f"{'(squeeze!)' if squeeze else ''}"
                    )
                )

        # No signal
        self.verbose_log(
            symbol, "Price inside Bollinger Bands (no signal)",
            False, close,
            f"need >{upper:.4f} or <{lower:.4f}"
        )
        return None