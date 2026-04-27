"""
=============================================================
  KRAKEN EXECUTOR
  Executes crypto trades via Kraken using CCXT.

  PAPER MODE NOTE:
    Kraken does not support a sandbox/demo API endpoint.
    ccxt's sandbox=True flag has no effect on Kraken.
    Paper mode is implemented locally — when paper=True,
    all order submissions are simulated in memory and no
    real API calls are made for order entry/exit.
    Price lookups still use the real Kraken API.
=============================================================
"""

import logging
import time
from typing import Optional, Dict
import ccxt

logger = logging.getLogger(__name__)


class KrakenExecutor:

    def __init__(self, api_key: str = "", api_secret: str = "",
                 paper: bool = False):
        self.paper = paper

        # Always init the exchange for price lookups
        self.exchange = ccxt.kraken({
            "apiKey":          api_key,
            "secret":          api_secret,
            "enableRateLimit": True,
        })

        if paper:
            logger.info("Kraken executor initialized in PAPER mode — orders simulated locally.")
        else:
            logger.info("Kraken executor initialized in LIVE mode.")

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        ccxt_symbol = symbol.replace("-", "/")

        if self.paper:
            # Paper mode: simulate fill at current market price
            price = self.get_current_price(symbol) or 0.0
            order_id = f"PAPER-{symbol}-{int(time.time())}"
            logger.info(
                f"[PAPER] Kraken simulated fill: {symbol} {side} "
                f"{qty} @ ${price:.4f}"
            )
            return {
                "broker_order_id":  order_id,
                "status":           "filled",
                "filled_qty":       qty,
                "filled_avg_price": price,
            }

        # Live mode
        try:
            order        = self.exchange.create_market_order(ccxt_symbol, side, qty)
            filled_price = float(order.get("average") or order.get("price") or 0)
            filled_qty   = float(order.get("filled") or qty)
            logger.info(
                f"Kraken order filled: {symbol} {side} "
                f"{filled_qty} @ ${filled_price:.4f}"
            )
            return {
                "broker_order_id":  order["id"],
                "status":           order["status"],
                "filled_qty":       filled_qty,
                "filled_avg_price": filled_price,
            }
        except Exception as e:
            logger.error(f"Kraken order failed for {symbol}: {e}")
            return None

    def close_position(self, symbol: str, qty: float, side: str) -> bool:
        ccxt_symbol = symbol.replace("-", "/")

        if self.paper:
            price = self.get_current_price(symbol) or 0.0
            close_side = "sell" if side == "buy" else "buy"
            logger.info(
                f"[PAPER] Kraken simulated close: {symbol} "
                f"{close_side} {qty} @ ${price:.4f}"
            )
            return True

        # Live mode
        try:
            close_side = "sell" if side == "buy" else "buy"
            self.exchange.create_market_order(ccxt_symbol, close_side, qty)
            logger.info(f"Kraken position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to close Kraken {symbol}: {e}")
            return False

    def get_balance(self, currency: str = "USD") -> float:
        if self.paper:
            # Paper mode: return a nominal balance so capital tracking works
            return 0.0
        try:
            balance = self.exchange.fetch_balance()
            usd = float(balance.get(currency, {}).get("free", 0))
            if usd == 0 and currency == "USD":
                usd = float(balance.get("ZUSD", {}).get("free", 0))
            return usd
        except Exception as e:
            logger.debug(f"Kraken balance fetch error: {e}")
            return 0.0

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ccxt_symbol = symbol.replace("-", "/")
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            return float(ticker["last"])
        except Exception as e:
            logger.debug(f"Kraken price lookup failed for {symbol}: {e}")
            return None

    def get_trading_pairs(self) -> list:
        try:
            markets = self.exchange.load_markets()
            return [m for m in markets.keys() if "/USD" in m]
        except Exception as e:
            logger.debug(f"Failed to load Kraken markets: {e}")
            return []
