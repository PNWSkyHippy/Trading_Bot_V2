"""
=============================================================
  STARTUP RECONCILER
  Runs once at bot startup to reconcile DB state vs broker.

  Problems it fixes:
  1. Ghost open trades — trades the DB thinks are open but
     the broker already closed (stop-loss hit, TP hit, or
     closed manually while bot was offline). These cause
     capital calculations to be wrong after restart.

  2. Capital drift — after reconciling ghost trades, recalculates
     true capital from all closed trades so the dashboard
     shows accurate numbers immediately on startup.

  How it works:
  - Fetches all open trades from DB
  - For stocks: checks Alpaca for current position
  - For crypto: checks current price vs SL/TP via Kraken price feed
  - If position not found at broker: marks it closed at last
    known price with reason 'reconciled_on_startup'
  - Logs every action clearly so you can see what happened

  Called automatically from bot_engine.py on startup.
=============================================================
"""

import logging
from datetime import datetime
from typing import List, Dict

import config
from data.database import db

logger = logging.getLogger(__name__)


def reconcile_on_startup():
    """
    Main entry point. Call this once at bot startup before
    any scanning begins.
    """
    logger.info("[RECONCILE] Starting startup reconciliation...")

    open_trades = db.get_open_trades()
    if not open_trades:
        logger.info("[RECONCILE] No open trades in DB — nothing to reconcile.")
        return

    logger.info(f"[RECONCILE] Found {len(open_trades)} open trade(s) in DB to verify.")

    stock_trades  = [t for t in open_trades if t["asset_class"] == "stock"]
    crypto_trades = [t for t in open_trades if t["asset_class"] == "crypto"]

    reconciled = 0

    # ---- Stocks: check against Alpaca ----
    if stock_trades:
        reconciled += _reconcile_stocks(stock_trades)

    # ---- Crypto: check price vs SL/TP ----
    if crypto_trades:
        reconciled += _reconcile_crypto(crypto_trades)

    if reconciled > 0:
        logger.info(
            f"[RECONCILE] Closed {reconciled} ghost trade(s). "
            f"Capital will now calculate correctly."
        )
    else:
        logger.info("[RECONCILE] All open trades verified — no ghosts found.")

    logger.info("[RECONCILE] Startup reconciliation complete.")


def _reconcile_stocks(trades: List[Dict]) -> int:
    """Check each open stock trade against Alpaca positions."""
    closed = 0
    try:
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.ALPACA_BASE_URL
        )
        # Get all current Alpaca positions
        try:
            positions = api.list_positions()
            open_symbols = {p.symbol for p in positions}
        except Exception as e:
            logger.warning(f"[RECONCILE] Could not fetch Alpaca positions: {e}")
            return 0

        for trade in trades:
            symbol = trade["symbol"]
            broker = trade.get("broker", "alpaca")

            # Only reconcile alpaca trades — skip IBKR and paper
            if broker not in ("alpaca", ""):
                continue

            if symbol not in open_symbols:
                # Position not found at broker — ghost trade
                # Use entry price as best estimate (we don't know exit price)
                exit_price = trade["entry_price"]
                pnl        = 0.0
                pnl_pct    = 0.0

                # Try to get last quote for a better exit price
                try:
                    quote = api.get_latest_trade(symbol)
                    if quote and quote.price:
                        exit_price = float(quote.price)
                        qty = trade["quantity"]
                        direction = trade["direction"]
                        pnl = (exit_price - trade["entry_price"]) * qty
                        if direction == "short":
                            pnl = -pnl
                        pnl_pct = (pnl / trade["position_value"] * 100) \
                                  if trade["position_value"] else 0
                except Exception:
                    pass

                db.close_trade(
                    trade_id    = trade["trade_id"],
                    exit_price  = round(exit_price, 6),
                    exit_reason = "reconciled_on_startup",
                    pnl         = round(pnl, 4),
                    pnl_pct     = round(pnl_pct, 4)
                )
                logger.info(
                    f"[RECONCILE] Ghost stock trade closed: {symbol} "
                    f"| Entry: ${trade['entry_price']:.4f} "
                    f"| Exit: ${exit_price:.4f} "
                    f"| PnL: ${pnl:+.2f} "
                    f"| trade_id: {trade['trade_id']}"
                )
                closed += 1
            else:
                logger.info(f"[RECONCILE] Stock position verified open at Alpaca: {symbol}")

    except ImportError:
        logger.warning("[RECONCILE] alpaca_trade_api not installed — skipping stock reconciliation")
    except Exception as e:
        logger.error(f"[RECONCILE] Stock reconciliation error: {e}")

    return closed


def _reconcile_crypto(trades: List[Dict]) -> int:
    """
    For crypto, check current price vs stop-loss and take-profit.
    If price has passed either level, close the trade.
    We can't check exchange positions easily so we use price logic.
    """
    closed = 0
    try:
        import ccxt
        exchange = ccxt.kraken({
            "apiKey":          config.KRAKEN_API_KEY,
            "secret":          config.KRAKEN_SECRET_KEY,
            "enableRateLimit": True,
        })
        logger.info(
            f"[RECONCILE] Crypto: verifying {len(trades)} position(s) via Kraken price feed"
        )

        for trade in trades:
            symbol    = trade["symbol"]
            direction = trade["direction"]
            sl        = trade["stop_loss"]
            tp        = trade["take_profit"]
            entry     = trade["entry_price"]

            # Get current price
            try:
                ticker     = exchange.fetch_ticker(symbol)
                price      = float(ticker["last"])
            except Exception:
                # Try yfinance as fallback
                try:
                    import yfinance as yf
                    yf_sym = symbol.replace("/", "-")
                    t = yf.Ticker(yf_sym)
                    hist = t.history(period="1d", interval="1m")
                    price = float(hist["Close"].iloc[-1]) if not hist.empty else None
                except Exception:
                    price = None

            if price is None:
                logger.warning(f"[RECONCILE] Could not get price for {symbol} — skipping")
                continue

            # Check if SL or TP was hit
            exit_reason = None
            exit_price  = price

            if direction == "long":
                if price <= sl:
                    exit_reason = "stop_loss"
                    exit_price  = sl  # assume filled at SL
                elif price >= tp:
                    exit_reason = "take_profit"
                    exit_price  = tp
            else:  # short
                if price >= sl:
                    exit_reason = "stop_loss"
                    exit_price  = sl
                elif price <= tp:
                    exit_reason = "take_profit"
                    exit_price  = tp

            if exit_reason:
                qty = trade["quantity"]
                pnl = (exit_price - entry) * qty if direction == "long" \
                      else (entry - exit_price) * qty
                pnl_pct = (pnl / trade["position_value"] * 100) \
                          if trade["position_value"] else 0

                db.close_trade(
                    trade_id    = trade["trade_id"],
                    exit_price  = round(exit_price, 6),
                    exit_reason = f"reconciled_{exit_reason}",
                    pnl         = round(pnl, 4),
                    pnl_pct     = round(pnl_pct, 4)
                )
                logger.info(
                    f"[RECONCILE] Crypto trade closed ({exit_reason}): {symbol} "
                    f"| Entry: ${entry:.4f} | Exit: ${exit_price:.4f} "
                    f"| PnL: ${pnl:+.2f} | trade_id: {trade['trade_id']}"
                )
                closed += 1
            else:
                logger.info(
                    f"[RECONCILE] Crypto trade still valid: {symbol} "
                    f"| Price: ${price:.4f} | SL: ${sl:.4f} | TP: ${tp:.4f}"
                )

    except Exception as e:
        logger.error(f"[RECONCILE] Crypto reconciliation error: {e}")

    return closed
