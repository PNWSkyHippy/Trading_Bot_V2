"""
=============================================================
  POSITION MONITOR
  Runs every 30 seconds. Watches all open positions for:
  - Stop-loss triggers
  - Take-profit triggers
  - Trailing stop adjustments
  - Extended take-profit on continued momentum

  Stock positions are only monitored during market hours
  (Mon-Fri 09:30-16:00 ET). Crypto is monitored 24/7.
=============================================================
"""

import logging
import time
import threading
from datetime import datetime
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

import config
from data.database import db
from core.risk_manager import risk_manager

logger = logging.getLogger(__name__)


def _stock_market_open() -> bool:
    """
    Returns True if the US stock market is currently open.
    Uses real Eastern Time via ZoneInfo — immune to machine timezone.
    Window: Monday-Friday, 09:30-16:00 ET.
    (Wider than the scan gate — we monitor from open, not 10:00.)
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    now_et  = datetime.now(ZoneInfo("America/New_York"))
    weekday = now_et.weekday()   # 0=Mon ... 4=Fri
    hour    = now_et.hour
    minute  = now_et.minute

    if weekday > 4:
        return False  # Weekend

    after_open  = hour > 9 or (hour == 9 and minute >= 30)
    before_close= hour < 16

    return after_open and before_close


class PositionMonitor:
    """
    Continuously monitors all open positions.
    Runs in its own background thread so it never blocks the scanner.
    """

    def __init__(self, db_ref=None, trade_executor=None):
        self._db       = db_ref or db
        self._executor = trade_executor
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
        """
        Check every open position against current prices.
        Stock positions are skipped entirely outside market hours —
        no price fetches, no exit checks, no Alpaca API calls.
        Crypto positions run 24/7 regardless.
        """
        open_trades = self._db.get_open_trades()
        if not open_trades:
            return

        market_open = _stock_market_open()

        # Separate stocks and crypto
        stock_trades  = [t for t in open_trades if t.get("asset_class") == "stock"]
        crypto_trades = [t for t in open_trades if t.get("asset_class") != "stock"]

        if stock_trades and not market_open:
            logger.debug(
                f"Position monitor: skipping {len(stock_trades)} stock position(s) "
                f"— market closed"
            )

        # Process crypto always, stocks only during market hours
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

        # Price alerts — only check stocks during market hours
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
        """
        Score current momentum on a 0.0–1.0 scale using three independent signals.
        Returns 0.0 on any data failure so the trade closes safely (no free ride).

        Signal 1 — RSI trend:  RSI >= MOMENTUM_RIDER_RSI_MIN and higher than 3 bars ago.
        Signal 2 — Bar trend:  last 3 consecutive closes each above the previous.
        Signal 3 — Volume surge: current bar volume >= MOMENTUM_RIDER_VOL_RATIO * 20-bar avg.
        """
        try:
            bars = self._get_bars(symbol, asset_class, limit=25)
            if bars is None or len(bars) < 15:
                logger.debug(f"Momentum scorer: insufficient bars for {symbol}")
                return 0.0

            closes  = bars["close"]
            volumes = bars["volume"]

            hits = 0

            # Signal 1: RSI level + rising slope
            delta    = closes.diff()
            gain     = delta.clip(lower=0)
            loss     = -delta.clip(upper=0)
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()
            rs       = avg_gain / avg_loss.replace(0, np.nan)
            rsi      = 100 - (100 / (1 + rs))
            rsi_now  = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-4]   # 3 bars ago
            if rsi_now >= config.MOMENTUM_RIDER_RSI_MIN and rsi_now > rsi_prev:
                hits += 1

            # Signal 2: Three consecutive higher closes
            c = closes.iloc[-3:].values
            if c[1] > c[0] and c[2] > c[1]:
                hits += 1

            # Signal 3: Volume surge on the current bar
            vol_avg = volumes.iloc[-21:-1].mean()   # 20 completed bars, not current
            vol_now = volumes.iloc[-1]
            if vol_avg > 0 and vol_now >= vol_avg * config.MOMENTUM_RIDER_VOL_RATIO:
                hits += 1

            score = hits / 3
            logger.debug(
                f"Momentum score {symbol}: {score:.2f} "
                f"(RSI={rsi_now:.1f}, hits={hits}/3)"
            )
            return score

        except Exception as e:
            logger.debug(f"Momentum score error for {symbol}: {e}")
            return 0.0   # safe default → close the trade

    # ------------------------------------------------------------------

    def _process_position(self, trade: Dict):
        """
        Process a single open position — fetch price, check exits,
        update trailing stops.
        Only called for stocks during market hours (enforced by check_positions).

        Exit order:
          1. Stop-loss  → always close immediately.
          2. Take-profit hit → run momentum check:
               Strong momentum + extensions remaining → extend TP, ride it.
               Weak momentum or cap reached         → close normally.
          3. Trailing stop update (runs every cycle regardless of TP).
        """
        symbol      = trade["symbol"]
        asset_class = trade["asset_class"]
        direction   = trade["direction"]
        trade_id    = trade["trade_id"]

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

        # ── 1. Stop-loss check — always fires immediately ──────────────
        sl_exit = risk_manager.check_sl_exit(trade, current_price)
        if sl_exit:
            logger.info(f"Stop-loss triggered: {symbol} @ ${current_price:.4f}")
            self._db.set_state(f"momentum_ext_{trade_id}", 0)   # clean up counter
            self._get_executor().close_trade(trade, current_price, sl_exit)
            return

        # ── 2. Take-profit hit — momentum rider decision ───────────────
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
                # Extend TP by another take-profit increment
                tp_pct = config.DEFAULT_TAKE_PROFIT_PCT / 100
                if direction == "long":
                    new_tp = current_price * (1 + tp_pct)
                else:
                    new_tp = current_price * (1 - tp_pct)
                new_tp = round(new_tp, 4)

                self._db.update_trade_levels(trade_id, take_profit=new_tp)
                self._db.set_state(f"momentum_ext_{trade_id}", ext_count + 1)
                logger.info(
                    f"MOMENTUM RIDER: {symbol} TP extended "
                    f"${trade['take_profit']:.4f} → ${new_tp:.4f} "
                    f"(extension {ext_count + 1}/{max_extensions}, "
                    f"P&L {pnl_pct:+.2f}%)"
                )
                # Fall through to trailing-stop update below
            else:
                close_reason = "take_profit"
                if at_tp and ext_count >= max_extensions:
                    close_reason = "take_profit_max_extensions"
                logger.info(
                    f"Take-profit exit: {symbol} @ ${current_price:.4f} "
                    f"(P&L {pnl_pct:+.2f}%, extensions used: {ext_count})"
                )
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._get_executor().close_trade(trade, current_price, "take_profit")
                return

        # ── 3. Trailing stop update (every cycle) ─────────────────────
        updates = risk_manager.calculate_trailing_stop(trade, current_price)
        if updates:
            self._db.update_trade_levels(
                trade_id,
                stop_loss   = updates.get("stop_loss"),
                take_profit = updates.get("take_profit")
            )
            if "stop_loss" in updates:
                logger.info(
                    f"Trailing stop updated: {symbol} SL -> "
                    f"${updates['stop_loss']:.4f} "
                    f"(locked in {pnl_pct:+.2f}% gain)"
                )

    def get_positions_summary(self) -> List[Dict]:
        """
        Return enriched summary of all open positions with live P&L.
        Used by the dashboard and chat interface.

        Stock prices are only fetched during market hours — outside hours
        the last known entry price is used as current price for display.
        This prevents hammering Alpaca API at 3 AM and getting stale/error data.
        """
        open_trades = self._db.get_open_trades()
        enriched    = []
        market_open = _stock_market_open()

        for trade in open_trades:
            symbol      = trade["symbol"]
            asset_class = trade["asset_class"]

            # Only fetch live price for stocks during market hours
            if asset_class == "stock" and not market_open:
                current_price = trade["entry_price"]
                logger.debug(
                    f"Dashboard: using entry price for {symbol} "
                    f"(market closed)"
                )
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
                # Pass through overnight flag for dashboard display
                "is_overnight": bool(trade.get("is_overnight", False)),
            })

        return enriched


# Singleton
monitor = PositionMonitor()
