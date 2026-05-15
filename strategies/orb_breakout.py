"""
orb_breakout.py — Strategy 11: Opening Range Breakout (ORB)
Trading Bot v2

Classic institutional day trading strategy. The first 30 minutes of
the trading day (9:30-10:00 ET) establish the opening range. A breakout
above or below that range with VWAP + EMA confirmation and volume conviction
often leads to strong directional momentum for the rest of the session.

Why it works:
  Large institutions execute big orders at the open creating price
  imbalances. When price breaks the opening range, it triggers stop
  losses, algorithmic signals, and momentum entries simultaneously
  which accelerates the move.

Entry conditions (long):
  1. Closed bar above ORB high (closed-bar confirmation, not wick)
  2. Prior bar at or below ORB high (catches the first bar through)
  3. Price above session VWAP (institutional buying confirmation)
  4. Fast EMA > Slow EMA (trend direction aligned)
  5. Volume >= 1.2x 20-bar average (stock) / 1.1x (crypto)
  6. RSI <= 75 (not overbought at entry)
  7. Not chasing > 0.75% above breakout (stock) / 1.25% (crypto)
  8. Stock: symbol in GO whitelist (optional, configurable)

Entry conditions (short): mirror of above.

Stop loss:
  Structural — opposite side of the opening range. This is the natural
  invalidation point for the breakout thesis.

Take profit:
  Risk × R_MULT (2.0 stock, 2.5 crypto). Uses structural ORB risk so
  TP adapts to the actual range of the day.

Whitelist (stocks):
  GO symbols from 5m 30-day backtest (Apr 2026) by default.
  Set USE_WHITELIST = False to scan all watchlist stocks.
  Crypto always unfiltered.

Timeframe: 5m bars (stocks) | 15m bars (crypto)

Default: DISABLED — backtest first, enable via dashboard.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)

# ── Whitelist toggle ──────────────────────────────────────────────────────────
# True  = only GO stocks from backtest are scanned (lower signal count, higher quality)
# False = all watchlist stocks are scanned (more signals, higher noise)
USE_WHITELIST = True

# GO stocks from 5m 30-day backtest (Apr 2026).
# TUNE verdict excluded: NVDA, INTC, NIO, APLD, MARA
ORB_STOCK_WHITELIST = {
    "META",  "TSLA",  "MSFT",  "AMD",   "MRVL",
    "ALAB",  "PLTR",  "CRWV",  "IREN",  "CLS",
    "AMZN",  "GOOGL", "AAPL",  "SPY",   "QQQ",
}

# ── Core parameters ───────────────────────────────────────────────────────────
FAST_EMA    = 20
SLOW_EMA    = 50
ATR_PERIOD  = 14
RSI_PERIOD  = 14
VOL_PERIOD  = 20

STOCK_ORB_BARS   = 6    # 6 × 5m  = first 30 min
CRYPTO_ORB_BARS  = 4    # 4 × 15m = first 60 min

STOCK_VOL_MULT   = 1.20
CRYPTO_VOL_MULT  = 1.10

STOCK_MIN_OR_ATR = 0.35   # OR must be >= 0.35 ATR
CRYPTO_MIN_OR_ATR= 0.50

STOCK_R_MULT     = 2.0    # TP = structural risk × R_MULT
CRYPTO_R_MULT    = 2.5

STOCK_MAX_CHASE_PCT  = 0.75   # max % above breakout still tradeable
CRYPTO_MAX_CHASE_PCT = 1.25

MAX_LONG_ENTRY_RSI   = 75    # skip if already overbought
MIN_SHORT_ENTRY_RSI  = 25    # skip if already oversold

MIN_BARS = max(SLOW_EMA, ATR_PERIOD, RSI_PERIOD, VOL_PERIOD) + 30


class ORBBreakout(BaseStrategy):
    """
    Opening Range Breakout — Strategy 11.
    5m bars (stocks) | 15m bars (crypto).
    VWAP + EMA + volume filtered. Closed-bar confirmation.
    """

    def __init__(self):
        super().__init__()
        self.strategy_name = "orb_breakout"
        self.stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT
        self.take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT

        self.stock_candle_timeframe  = "5Min"
        self.crypto_candle_timeframe = "15m"
        self.candle_limit            = 220

        self.stock_enabled  = True
        self.crypto_enabled = True
        self.enabled        = False   # DISABLED — backtest first, enable via dashboard

        logger.info(
            f"[{self.strategy_name}] Initialized — stock 5Min ORB + crypto 15m ORB | "
            f"whitelist={'ON' if USE_WHITELIST else 'OFF'}"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _asset_class(self, symbol: str) -> str:
        return "crypto" if "/" in symbol else "stock"

    def _normalise_index(self, candles: pd.DataFrame, asset_class: str) -> pd.DataFrame:
        """
        Normalise timestamps for session calculations.
        Stocks → America/New_York (strip tz). Crypto → UTC (strip tz).
        Naive timestamps are left as-is.
        """
        out = candles.copy()
        idx = pd.DatetimeIndex(out.index)
        try:
            if idx.tz is not None:
                if asset_class == "stock":
                    from zoneinfo import ZoneInfo
                    idx = idx.tz_convert(ZoneInfo("America/New_York")).tz_localize(None)
                else:
                    idx = idx.tz_convert("UTC").tz_localize(None)
        except Exception:
            pass
        out.index = idx
        return out.sort_index()

    def _session_bars(self, candles: pd.DataFrame, asset_class: str) -> Optional[pd.DataFrame]:
        """Return today's session bars only."""
        df = self._normalise_index(candles, asset_class)
        if df.empty:
            return None
        if asset_class == "stock":
            try:
                df = df.between_time("09:30", "16:00")
            except Exception:
                pass
        if df.empty:
            return None
        session_date = df.index[-1].date()
        df = df[df.index.date == session_date]
        return df if not df.empty else None

    def _session_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Intraday VWAP anchored to session open."""
        typical  = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
        volume   = df["volume"].astype(float)
        cum_vol  = volume.cumsum().replace(0, float("nan"))
        return (typical * volume).cumsum() / cum_vol

    def _calc_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Optional[float]:
        try:
            atr_s = ta.atr(high, low, close, length=ATR_PERIOD)
            if atr_s is None or atr_s.empty:
                return None
            val = atr_s.iloc[-1]
            return float(val) if not pd.isna(val) else None
        except Exception:
            return None

    def _calc_rsi(self, close: pd.Series) -> Optional[float]:
        try:
            rsi_s = ta.rsi(close, length=RSI_PERIOD)
            if rsi_s is None or rsi_s.empty:
                return None
            val = rsi_s.iloc[-1]
            return float(val) if not pd.isna(val) else None
        except Exception:
            return None

    def _calc_ema_pair(self, close: pd.Series):
        try:
            fast_s = ta.ema(close, length=FAST_EMA)
            slow_s = ta.ema(close, length=SLOW_EMA)
            if fast_s is None or slow_s is None:
                return None, None
            return float(fast_s.iloc[-1]), float(slow_s.iloc[-1])
        except Exception:
            return None, None

    # ── Main analysis ─────────────────────────────────────────────────────────

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown",
    ) -> Optional[TradeSignal]:

        asset_class = self._asset_class(symbol)

        # ── Whitelist gate (stocks only) ─────────────────────────────────
        if asset_class == "stock" and USE_WHITELIST:
            if symbol.upper() not in ORB_STOCK_WHITELIST:
                self.verbose_log_skip(symbol, "Not in ORB GO whitelist")
                return None

        if not self._check_enough_candles(symbol, candles, MIN_BARS):
            return None

        close  = candles["close"].astype(float)
        high   = candles["high"].astype(float)
        low    = candles["low"].astype(float)
        volume = candles["volume"].astype(float)
        current_close = float(close.iloc[-1])

        # ── Session bars ─────────────────────────────────────────────────
        session = self._session_bars(candles, asset_class)
        if session is None or session.empty:
            self.verbose_log_skip(symbol, "No current session bars available")
            return None

        orb_bars      = STOCK_ORB_BARS    if asset_class == "stock" else CRYPTO_ORB_BARS
        vol_mult      = STOCK_VOL_MULT    if asset_class == "stock" else CRYPTO_VOL_MULT
        min_or_atr    = STOCK_MIN_OR_ATR  if asset_class == "stock" else CRYPTO_MIN_OR_ATR
        r_mult        = STOCK_R_MULT      if asset_class == "stock" else CRYPTO_R_MULT
        max_chase_pct = STOCK_MAX_CHASE_PCT if asset_class == "stock" else CRYPTO_MAX_CHASE_PCT
        tf_label      = "5Min" if asset_class == "stock" else "15m"

        if len(session) <= orb_bars:
            self.verbose_log_skip(
                symbol,
                f"Opening range not complete yet ({len(session)}/{orb_bars} bars)"
            )
            return None

        # ── Opening range levels ─────────────────────────────────────────
        opening  = session.iloc[:orb_bars]
        orb_high = float(opening["high"].max())
        orb_low  = float(opening["low"].min())
        or_width = orb_high - orb_low

        atr = self._calc_atr(high, low, close)
        if atr is None or atr <= 0:
            self.verbose_log_skip(symbol, "ATR unavailable")
            return None

        if or_width < atr * min_or_atr:
            self.verbose_log_skip(
                symbol,
                f"Opening range too small ({or_width:.4f} < {min_or_atr:.2f}×ATR)"
            )
            return None

        # ── Indicators ───────────────────────────────────────────────────
        ema_fast, ema_slow = self._calc_ema_pair(close)
        if ema_fast is None or ema_slow is None:
            self.verbose_log_skip(symbol, "EMA calculation failed")
            return None

        rsi = self._calc_rsi(close)
        if rsi is None:
            self.verbose_log_skip(symbol, "RSI unavailable")
            return None

        vwap_s = self._session_vwap(session)
        if vwap_s is None or vwap_s.empty or pd.isna(vwap_s.iloc[-1]):
            self.verbose_log_skip(symbol, "VWAP unavailable")
            return None

        vwap_now    = float(vwap_s.iloc[-1])
        prev_close  = float(session["close"].iloc[-2])
        current_vol = float(session["volume"].iloc[-1])
        vol_avg     = float(volume.iloc[-VOL_PERIOD:].mean()) if len(volume) >= VOL_PERIOD else float(volume.mean())
        vol_ratio   = (current_vol / vol_avg) if vol_avg > 0 else 1.0

        # Chase distance from breakout level
        long_chase_pct  = ((current_close - orb_high) / orb_high * 100) if orb_high > 0 else 0.0
        short_chase_pct = ((orb_low - current_close) / orb_low  * 100) if orb_low  > 0 else 0.0

        # ── LONG breakout ────────────────────────────────────────────────
        long_ok = (
            current_close > orb_high           and   # closed bar above OR high
            prev_close    <= orb_high           and   # previous bar was still inside
            current_close >  vwap_now           and   # above session VWAP
            current_close >  ema_fast           and   # price above fast EMA
            ema_fast      >  ema_slow            and   # trend aligned
            vol_ratio     >= vol_mult            and   # volume conviction
            rsi           <= MAX_LONG_ENTRY_RSI  and   # not overbought
            long_chase_pct <= max_chase_pct             # not chasing too far
        )

        if long_ok:
            stop_price = orb_low
            if stop_price >= current_close:
                self.verbose_log_skip(symbol, "Long stop invalid — OR low above entry")
                return None
            risk = current_close - stop_price
            if risk <= 0:
                self.verbose_log_skip(symbol, "Long risk <= 0")
                return None

            target_price = current_close + (risk * r_mult)
            sl_pct = (risk / current_close) * 100
            tp_pct = ((target_price - current_close) / current_close) * 100

            score = 0.72
            score += min(0.12, max(0.0, vol_ratio - vol_mult) * 0.12)
            if or_width >= atr:
                score += 0.06
            score = min(1.0, score)

            self.verbose_log_score(symbol, score, 0.65)

            reason = (
                f"ORB long: close {current_close:.4f} > OR high {orb_high:.4f} | "
                f"VWAP={vwap_now:.4f} | EMA{FAST_EMA}>{SLOW_EMA} | "
                f"vol={vol_ratio:.2f}x | RSI={rsi:.1f} | chase={long_chase_pct:.2f}%"
            )
            logger.info(f"[{self.strategy_name}] LONG signal: {symbol} | {reason}")

            return self._make_signal(
                symbol          = symbol,
                direction       = "long",
                score           = round(score, 3),
                reason          = reason,
                stop_loss_pct   = round(sl_pct, 3),
                take_profit_pct = round(tp_pct, 3),
                metadata        = {
                    "strategy_name":              self.strategy_name,
                    "entry_timeframe":            tf_label,
                    "entry_type":                 "orb_breakout_long",
                    "structural_stop_price":      round(stop_price, 6),
                    "orb_high":                   round(orb_high, 6),
                    "orb_low":                    round(orb_low, 6),
                    "orb_width":                  round(or_width, 6),
                    "orb_width_atr":              round(or_width / atr, 4),
                    "session_vwap":               round(vwap_now, 6),
                    "ema_fast":                   round(ema_fast, 6),
                    "ema_slow":                   round(ema_slow, 6),
                    "atr":                        round(atr, 6),
                    "rsi":                        round(rsi, 2),
                    "volume_ratio":               round(vol_ratio, 3),
                    "distance_from_breakout_pct": round(long_chase_pct, 3),
                    "entry_time_utc":             datetime.now(timezone.utc).isoformat(),
                }
            )

        # ── SHORT breakout ───────────────────────────────────────────────
        short_ok = (
            current_close < orb_low            and   # closed bar below OR low
            prev_close    >= orb_low            and   # previous bar was still inside
            current_close <  vwap_now           and   # below session VWAP
            current_close <  ema_fast           and   # price below fast EMA
            ema_fast      <  ema_slow            and   # trend aligned
            vol_ratio     >= vol_mult            and   # volume conviction
            rsi           >= MIN_SHORT_ENTRY_RSI and   # not oversold
            short_chase_pct <= max_chase_pct            # not chasing too far
        )

        if short_ok:
            stop_price = orb_high
            if stop_price <= current_close:
                self.verbose_log_skip(symbol, "Short stop invalid — OR high below entry")
                return None
            risk = stop_price - current_close
            if risk <= 0:
                self.verbose_log_skip(symbol, "Short risk <= 0")
                return None

            target_price = current_close - (risk * r_mult)
            sl_pct = (risk / current_close) * 100
            tp_pct = ((current_close - target_price) / current_close) * 100

            score = 0.72
            score += min(0.12, max(0.0, vol_ratio - vol_mult) * 0.12)
            if or_width >= atr:
                score += 0.06
            score = min(1.0, score)

            self.verbose_log_score(symbol, score, 0.65)

            reason = (
                f"ORB short: close {current_close:.4f} < OR low {orb_low:.4f} | "
                f"VWAP={vwap_now:.4f} | EMA{FAST_EMA}<{SLOW_EMA} | "
                f"vol={vol_ratio:.2f}x | RSI={rsi:.1f} | chase={short_chase_pct:.2f}%"
            )
            logger.info(f"[{self.strategy_name}] SHORT signal: {symbol} | {reason}")

            return self._make_signal(
                symbol          = symbol,
                direction       = "short",
                score           = round(score, 3),
                reason          = reason,
                stop_loss_pct   = round(sl_pct, 3),
                take_profit_pct = round(tp_pct, 3),
                metadata        = {
                    "strategy_name":              self.strategy_name,
                    "entry_timeframe":            tf_label,
                    "entry_type":                 "orb_breakout_short",
                    "structural_stop_price":      round(stop_price, 6),
                    "orb_high":                   round(orb_high, 6),
                    "orb_low":                    round(orb_low, 6),
                    "orb_width":                  round(or_width, 6),
                    "orb_width_atr":              round(or_width / atr, 4),
                    "session_vwap":               round(vwap_now, 6),
                    "ema_fast":                   round(ema_fast, 6),
                    "ema_slow":                   round(ema_slow, 6),
                    "atr":                        round(atr, 6),
                    "rsi":                        round(rsi, 2),
                    "volume_ratio":               round(vol_ratio, 3),
                    "distance_from_breakout_pct": round(short_chase_pct, 3),
                    "entry_time_utc":             datetime.now(timezone.utc).isoformat(),
                }
            )

        logger.debug(
            f"[{self.strategy_name}] {symbol}: no signal | "
            f"close={current_close:.4f} OR=({orb_low:.4f}-{orb_high:.4f}) "
            f"VWAP={vwap_now:.4f} EMAf={ema_fast:.4f} EMAs={ema_slow:.4f} "
            f"vol={vol_ratio:.2f}x RSI={rsi:.1f}"
        )
        return None
