"""
=============================================================
  POSITION MONITOR
  Runs every 30 seconds. Watches all open positions for:
  - Stop-loss triggers
  - Take-profit triggers
  - Trailing stop adjustments
  - Extended take-profit on continued momentum
  - Stale position sell-off (3hr ADX/DI trend check)
  - VWAP cross exit for ORB trades
  - EOD close for all stock positions

  Stock positions are only monitored during market hours
  (Mon-Fri 09:30-16:00 ET). Crypto is monitored 24/7.
=============================================================
"""

import logging
import time
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

import config
from data.database import db
from core.risk_manager import risk_manager

logger = logging.getLogger(__name__)

# Stale position check: 3 hours in seconds
STALE_THRESHOLD_SEC = 3 * 60 * 60

# ADX threshold below which trend is considered stalled
ADX_STALE_THRESHOLD = 25.0

# EOD close time: 15:45 ET (gives 15 min buffer before 16:00 close)
EOD_CLOSE_HOUR   = 15
EOD_CLOSE_MINUTE = 45


def _stock_market_open() -> bool:
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    now_et  = datetime.now(ZoneInfo("America/New_York"))
    weekday = now_et.weekday()
    hour    = now_et.hour
    minute  = now_et.minute

    if weekday > 4:
        return False

    after_open   = hour > 9 or (hour == 9 and minute >= 30)
    before_close = hour < 16

    return after_open and before_close


def _approaching_eod() -> bool:
    """Returns True if it's time to close all stock positions (15:45 ET)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    now_et  = datetime.now(ZoneInfo("America/New_York"))
    weekday = now_et.weekday()
    if weekday > 4:
        return False

    at_or_after = (
        now_et.hour > EOD_CLOSE_HOUR or
        (now_et.hour == EOD_CLOSE_HOUR and now_et.minute >= EOD_CLOSE_MINUTE)
    )
    before_close = now_et.hour < 16
    return at_or_after and before_close


def _get_position_age_seconds(trade: Dict) -> float:
    """Return how many seconds a position has been open."""
    try:
        entry_raw = trade.get("entry_time", "")
        if not entry_raw:
            return 0.0
        # Handle both naive and aware datetimes
        entry_dt = pd.to_datetime(entry_raw)
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        return (now_utc - entry_dt).total_seconds()
    except Exception:
        return 0.0


class PositionMonitor:
    """
    Continuously monitors all open positions.
    Runs in its own background thread so it never blocks the scanner.
    """

    def __init__(self, db_ref=None, trade_executor=None):
        self._db            = db_ref or db
        self._executor      = trade_executor
        self.running        = False
        self.check_interval = 30
        self._thread        = None

    def _get_executor(self):
        if self._executor:
            return self._executor
        from core.trade_executor import executor
        return executor

    def _get_scanner(self):
        from scanners.market_scanner import scanner
        return scanner

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Position monitor started.")

    def stop(self):
        self.running = False
        logger.info("Position monitor stopped.")

    def _monitor_loop(self):
        while self.running:
            try:
                self.check_positions()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            time.sleep(self.check_interval)

    def check_positions(self):
        open_trades = self._db.get_open_trades()
        if not open_trades:
            return

        market_open = _stock_market_open()

        stock_trades  = [t for t in open_trades if t.get("asset_class") == "stock"]
        crypto_trades = [t for t in open_trades if t.get("asset_class") != "stock"]

        if stock_trades and not market_open:
            logger.debug(
                f"Position monitor: skipping {len(stock_trades)} stock position(s) "
                f"\u2014 market closed"
            )

        trades_to_check = crypto_trades
        if market_open:
            trades_to_check = trades_to_check + stock_trades

        if not trades_to_check:
            return

        logger.debug(f"Monitoring {len(trades_to_check)} open positions...")

        for trade in trades_to_check:
            try:
                self._process_position(trade)
            except Exception as e:
                logger.error(
                    f"Error processing position {trade['symbol']}: {e}"
                )

        # Price alerts
        try:
            from reporting.alerts import alert_manager
            from data.database import db as _db

            all_symbols = list(config.CRYPTO_WATCHLIST)
            if market_open:
                all_symbols += (
                    list(config.STOCK_WATCHLIST) +
                    ["SOXL", "SOXS", "TQQQ", "SQQQ", "SPXL", "SPXS",
                     "UVXY", "SVXY", "LABU", "LABD"]
                )

            for sym in all_symbols:
                alerts = _db.get_state(f"price_alerts_{sym}", default=[])
                if not alerts:
                    continue
                asset = "crypto" if "/" in sym else "stock"
                price = self._get_scanner().get_current_price(sym, asset)
                if price:
                    alert_manager.check_price_alerts(sym, price)
        except Exception as e:
            logger.debug(f"Price alert check error: {e}")

    def check_all_positions(self):
        """Alias for backward compatibility."""
        self.check_positions()

    # ------------------------------------------------------------------
    #  ADX / DI HELPERS FOR STALE POSITION CHECK
    # ------------------------------------------------------------------

    def _get_adx_di(self, symbol: str, asset_class: str) -> Optional[Dict]:
        """
        Fetch ADX, +DI, -DI for the stale position sell-off check.
        Returns dict with keys adx, plus_di, minus_di or None on failure.
        """
        try:
            import pandas_ta as ta
            bars = self._get_bars(symbol, asset_class, limit=50)
            if bars is None or len(bars) < 20:
                return None

            adx_df = ta.adx(bars["high"], bars["low"], bars["close"], length=14)
            if adx_df is None or adx_df.empty:
                return None

            adx_col  = [c for c in adx_df.columns if c.startswith("ADX_")]
            dmp_col  = [c for c in adx_df.columns if c.startswith("DMP_")]  # +DI
            dmn_col  = [c for c in adx_df.columns if c.startswith("DMN_")]  # -DI

            if not adx_col or not dmp_col or not dmn_col:
                return None

            return {
                "adx":      float(adx_df[adx_col[0]].iloc[-1]),
                "plus_di":  float(adx_df[dmp_col[0]].iloc[-1]),   # Green/bullish
                "minus_di": float(adx_df[dmn_col[0]].iloc[-1]),   # Red/bearish
            }
        except Exception as e:
            logger.debug(f"ADX/DI fetch error for {symbol}: {e}")
            return None

    def _check_stale_position(self, trade: Dict) -> Optional[str]:
        """
        Implements the stale asset sell-off logic.
        Called when position has been open >= 3 hours.

        Logic (from Linda's pseudo-code):
          If ADX < 25 (trend stalled) → sell immediately
          Else (trend exists):
            Long position:
              -DI > +DI (bearish) → sell immediately
              +DI > -DI (bullish) → stay (exit = None)
            Short position:
              +DI > -DI (bullish) → sell immediately
              -DI > +DI (bearish) → stay (exit = None)

        Returns exit reason string if should close, None if should stay.
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]

        adx_data = self._get_adx_di(symbol, trade["asset_class"])
        if adx_data is None:
            logger.debug(f"[STALE] {symbol}: could not get ADX data — skipping stale check")
            return None  # Can't check, don't close

        adx      = adx_data["adx"]
        plus_di  = adx_data["plus_di"]   # Green — bullish
        minus_di = adx_data["minus_di"]  # Red — bearish

        logger.info(
            f"[STALE CHECK] {symbol} {direction.upper()} | "
            f"Open 3+ hrs | ADX={adx:.1f} +DI={plus_di:.1f} -DI={minus_di:.1f}"
        )

        # ADX < 25: trend has stalled — close regardless of direction
        if adx < ADX_STALE_THRESHOLD:
            logger.info(
                f"[STALE EXIT] {symbol}: ADX={adx:.1f} < {ADX_STALE_THRESHOLD} "
                f"(trend stalled) — closing position"
            )
            return "stale_no_trend"

        # ADX >= 25: trend exists, check direction vs position
        if direction == "long":
            if minus_di > plus_di:  # Bearish — trend against long
                logger.info(
                    f"[STALE EXIT] {symbol}: LONG but -DI({minus_di:.1f}) > "
                    f"+DI({plus_di:.1f}) (bearish trend) — closing"
                )
                return "stale_trend_reversed"
            else:  # Bullish — trend still supporting long
                logger.info(
                    f"[STALE HOLD] {symbol}: LONG and +DI({plus_di:.1f}) > "
                    f"-DI({minus_di:.1f}) (bullish) — holding"
                )
                return None

        else:  # short
            if plus_di > minus_di:  # Bullish — trend against short
                logger.info(
                    f"[STALE EXIT] {symbol}: SHORT but +DI({plus_di:.1f}) > "
                    f"-DI({minus_di:.1f}) (bullish trend) — closing"
                )
                return "stale_trend_reversed"
            else:  # Bearish — trend still supporting short
                logger.info(
                    f"[STALE HOLD] {symbol}: SHORT and -DI({minus_di:.1f}) > "
                    f"+DI({plus_di:.1f}) (bearish) — holding"
                )
                return None

    def _check_vwap_cross_exit(self, trade: Dict, current_price: float) -> bool:
        """
        VWAP cross exit for ORB trades.
        Long:  price crosses back below VWAP → exit
        Short: price crosses back above VWAP → exit
        Returns True if should exit.
        """
        try:
            bars = self._get_bars(trade["symbol"], trade["asset_class"], limit=50)
            if bars is None or len(bars) < 5:
                return False

            typical = (bars["high"] + bars["low"] + bars["close"]) / 3
            cum_tpv = (typical * bars["volume"]).cumsum()
            cum_vol = bars["volume"].cumsum()
            vwap    = (cum_tpv / cum_vol.replace(0, float("nan"))).iloc[-1]

            if pd.isna(vwap):
                return False

            direction = trade["direction"]
            if direction == "long" and current_price < vwap:
                logger.info(
                    f"[ORB VWAP EXIT] {trade['symbol']}: price {current_price:.4f} "
                    f"crossed below VWAP {vwap:.4f} — closing"
                )
                return True
            elif direction == "short" and current_price > vwap:
                logger.info(
                    f"[ORB VWAP EXIT] {trade['symbol']}: price {current_price:.4f} "
                    f"crossed above VWAP {vwap:.4f} — closing"
                )
                return True

            return False
        except Exception as e:
            logger.debug(f"VWAP cross check error for {trade['symbol']}: {e}")
            return False

    # ------------------------------------------------------------------
    #  MOMENTUM RIDER HELPERS
    # ------------------------------------------------------------------

    def _get_bars(self, symbol: str, asset_class: str,
                  limit: int = 25) -> Optional[pd.DataFrame]:
        """Fetch recent OHLCV bars for momentum scoring."""
        try:
            sc = self._get_scanner()
            if asset_class == "stock":
                return sc.stock_scanner.get_bars(symbol, timeframe="5Min", limit=limit)
            else:
                return sc.crypto_scanner.get_ohlcv(symbol, timeframe="5m", limit=limit)
        except Exception as e:
            logger.debug(f"Bar fetch error for {symbol}: {e}")
            return None

    def _score_momentum(self, symbol: str, asset_class: str) -> float:
        try:
            bars = self._get_bars(symbol, asset_class, limit=25)
            if bars is None or len(bars) < 15:
                return 0.0

            closes  = bars["close"]
            volumes = bars["volume"]

            hits = 0

            delta    = closes.diff()
            gain     = delta.clip(lower=0)
            loss     = -delta.clip(upper=0)
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()
            rs       = avg_gain / avg_loss.replace(0, np.nan)
            rsi      = 100 - (100 / (1 + rs))
            rsi_now  = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-4]
            if rsi_now >= config.MOMENTUM_RIDER_RSI_MIN and rsi_now > rsi_prev:
                hits += 1

            c = closes.iloc[-3:].values
            if c[1] > c[0] and c[2] > c[1]:
                hits += 1

            vol_avg = volumes.iloc[-21:-1].mean()
            vol_now = volumes.iloc[-1]
            if vol_avg > 0 and vol_now >= vol_avg * config.MOMENTUM_RIDER_VOL_RATIO:
                hits += 1

            score = hits / 3
            return score

        except Exception as e:
            logger.debug(f"Momentum score error for {symbol}: {e}")
            return 0.0

    # ------------------------------------------------------------------

    def _process_position(self, trade: Dict):
        """
        Process a single open position.

        Exit priority order:
          1. EOD close (15:45 ET) — all stock positions
          2. Stop-loss — always fires immediately
          3. ORB VWAP cross exit — only for orb_breakout strategy
          4. Take-profit + momentum rider decision
          5. Stale position check (3hr ADX/DI)
          6. Trailing stop update
        """
        symbol      = trade["symbol"]
        asset_class = trade["asset_class"]
        direction   = trade["direction"]
        trade_id    = trade["trade_id"]
        strategy    = trade.get("strategy_name", "")
        is_overnight= bool(trade.get("is_overnight", False))

        current_price = self._get_scanner().get_current_price(symbol, asset_class)
        if current_price is None:
            logger.warning(f"Could not get price for {symbol} — skipping check")
            return

        qty = trade["quantity"]
        if direction == "long":
            unrealized_pnl = (current_price - trade["entry_price"]) * qty
            pnl_pct = (current_price - trade["entry_price"]) / trade["entry_price"] * 100
        else:
            unrealized_pnl = (trade["entry_price"] - current_price) * qty
            pnl_pct = (trade["entry_price"] - current_price) / trade["entry_price"] * 100

        logger.debug(
            f"{symbol}: price=${current_price:.4f} | "
            f"SL=${trade['stop_loss']:.4f} | TP=${trade['take_profit']:.4f} | "
            f"P&L: {pnl_pct:+.2f}%"
        )

        # ── 1. EOD CLOSE (15:45 ET) ─────────────────────────────────────
        # Close all non-overnight stock positions before market close
        if asset_class == "stock" and not is_overnight and _approaching_eod():
            logger.info(
                f"[EOD CLOSE] {symbol}: market approaching close @ 15:45 ET — closing"
            )
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._get_executor().close_trade(trade, current_price, "eod_close")
            return

        # ── 2. STOP-LOSS ───────────────────────────────────────────────────
        sl_exit = risk_manager.check_sl_exit(trade, current_price)
        if sl_exit:
            logger.info(f"Stop-loss triggered: {symbol} @ ${current_price:.4f}")
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._get_executor().close_trade(trade, current_price, sl_exit)
            return

        # ── 3. ORB VWAP CROSS EXIT ───────────────────────────────────────
        # ORB trades ride until VWAP cross instead of fixed TP
        if strategy == "orb_breakout":
            if self._check_vwap_cross_exit(trade, current_price):
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._get_executor().close_trade(trade, current_price, "vwap_cross")
                return
            # ORB trades skip the fixed TP check below — VWAP is the exit
            # Still fall through to stale check and trailing stop
        else:
            # ── 4. TAKE-PROFIT + MOMENTUM RIDER (non-ORB trades) ──────────
            at_tp = (
                (direction == "long"  and current_price >= trade["take_profit"]) or
                (direction == "short" and current_price <= trade["take_profit"])
            )

            if at_tp:
                rider_enabled  = getattr(config, "MOMENTUM_RIDER_ENABLED", True)
                max_extensions = getattr(config, "MOMENTUM_RIDER_MAX_EXTENSIONS", 3)
                min_score      = getattr(config, "MOMENTUM_RIDER_MIN_SCORE", 0.67)
                ext_count      = self._db.get_state(f"momentum_ext_{trade_id}", default=0)

                ride = False
                if rider_enabled and ext_count < max_extensions:
                    mom_score = self._score_momentum(symbol, asset_class)
                    ride = mom_score >= min_score

                if ride:
                    tp_pct = config.DEFAULT_TAKE_PROFIT_PCT / 100
                    if direction == "long":
                        new_tp = current_price * (1 + tp_pct)
                    else:
                        new_tp = current_price * (1 - tp_pct)
                    new_tp = round(new_tp, 4)
                    self._db.update_trade_levels(trade_id, take_profit=new_tp)
                    self._db.set_state(f"momentum_ext_{trade_id}", 0)
                    with self._db._conn() as conn:
                        conn.execute(
                            "UPDATE trades SET tp_hit_count = 0 WHERE trade_id = ?",
                            (trade_id,)
                        )
                        conn.commit()
                    with self._db._conn() as conn:
                        conn.execute(
                            "UPDATE trades SET tp_hit_count = ? WHERE trade_id = ?",
                            (ext_count + 1, trade_id)
                        )
                        conn.commit()
                    logger.info(
                        f"MOMENTUM RIDER: {symbol} TP extended "
                        f"${trade['take_profit']:.4f} → ${new_tp:.4f} "
                        f"(extension {ext_count + 1}/{max_extensions}, "
                        f"P&L {pnl_pct:+.2f}%)"
                    )
                else:
                    logger.info(
                        f"Take-profit exit: {symbol} @ ${current_price:.4f} "
                        f"(P&L {pnl_pct:+.2f}%, extensions used: {ext_count})"
                    )
                    self._db.set_state(f"momentum_ext_{trade_id}", 0)
                    with self._db._conn() as conn:
                        conn.execute(
                            "UPDATE trades SET tp_hit_count = 0 WHERE trade_id = ?",
                            (trade_id,)
                        )
                        conn.commit()
                    self._get_executor().close_trade(trade, current_price, "take_profit")
                    return

        # ── 5. STALE POSITION CHECK (3hr ADX/DI) ───────────────────────
        # Check every hour after the 3-hour mark
        age_seconds = _get_position_age_seconds(trade)
        if age_seconds >= STALE_THRESHOLD_SEC:
            stale_exit = self._check_stale_position(trade)
            if stale_exit:
                logger.info(
                    f"[STALE EXIT] {symbol}: closing after "
                    f"{age_seconds/3600:.1f}hrs | reason={stale_exit}"
                )
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._get_executor().close_trade(trade, current_price, stale_exit)
                return

        # ── 6. TRAILING STOP UPDATE ─────────────────────────────────────
        updates = risk_manager.calculate_trailing_stop(trade, current_price)
        if updates:
            self._db.update_trade_levels(
                trade_id,
                stop_loss   = updates.get("stop_loss"),
                take_profit = updates.get("take_profit")
            )
            if "stop_loss" in updates:
                logger.info(
                    f"Trailing stop updated: {symbol} SL → "
                    f"${updates['stop_loss']:.4f} "
                    f"(locked in {pnl_pct:+.2f}% gain)"
                )

    def get_positions_summary(self) -> List[Dict]:
        open_trades = self._db.get_open_trades()
        enriched    = []
        market_open = _stock_market_open()

        for trade in open_trades:
            symbol      = trade["symbol"]
            asset_class = trade["asset_class"]

            if asset_class == "stock" and not market_open:
                current_price = trade["entry_price"]
            else:
                current_price = self._get_scanner().get_current_price(
                    symbol, asset_class
                )
                if current_price is None:
                    current_price = trade["entry_price"]

            qty       = trade["quantity"]
            direction = trade["direction"]

            if direction == "long":
                unrealized_pnl = (current_price - trade["entry_price"]) * qty
                pnl_pct = (current_price / trade["entry_price"] - 1) * 100
            else:
                unrealized_pnl = (trade["entry_price"] - current_price) * qty
                pnl_pct = (trade["entry_price"] / current_price - 1) * 100

            enriched.append({
                **trade,
                "current_price":  round(current_price, 6),
                "unrealized_pnl": round(unrealized_pnl, 4),
                "pnl_pct":        round(pnl_pct, 2),
                "market_value":   round(current_price * qty, 2),
                "distance_to_sl": round(
                    abs(current_price - trade["stop_loss"]) / current_price * 100, 2
                ),
                "distance_to_tp": round(
                    abs(trade["take_profit"] - current_price) / current_price * 100, 2
                ),
                "is_overnight": bool(trade.get("is_overnight", False)),
                "tp_hit_count": int(trade.get("tp_hit_count", 0)),
            })

        return enriched


# Singleton
monitor = PositionMonitor()
