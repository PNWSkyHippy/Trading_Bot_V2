"""
=============================================================
  KRAKEN EXECUTOR
  Executes crypto trades via Kraken using CCXT.
  Supports both live and paper trading (via kraken_cli).
  Kraken uses pairs like BTC/USD, XBT/USD internally.
=============================================================
"""

import logging
from typing import Optional, Dict
import ccxt

logger = logging.getLogger(__name__)


class KrakenExecutor:
    """
    Executes crypto trades via Kraken.
    Uses CCXT for standardized order handling.
    Paper trading: set paper=True to use Kraken's demo/sandbox.
    """

    def __init__(self, api_key: str = "", api_secret: str = "",
                 paper: bool = False):
        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        }

        if paper:
            # Kraken sandbox/demo endpoint
            config["sandbox"] = True
            logger.info("Kraken executor initialized in PAPER mode.")
        else:
            logger.info("Kraken executor initialized in LIVE mode.")

        self.exchange = ccxt.kraken(config)
        self.paper = paper

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        """
        Submit a market order on Kraken.
        Symbol should be in standard format: BTC/USD, ETH/USD, etc.
        Stop-loss and take-profit are managed by position monitor
        since Kraken API bracket orders are limited.
        """
        try:
            # Convert dash format (BTC-USD) to slash format (BTC/USD) for CCXT
            ccxt_symbol = symbol.replace("-", "/")

            order = self.exchange.create_market_order(ccxt_symbol, side, qty)
            filled_price = float(order.get("average") or order.get("price") or 0)
            filled_qty = float(order.get("filled") or qty)

            logger.info(
                f"Kraken order filled: {symbol} {side} "
                f"{filled_qty} @ ${filled_price:.4f}"
            )
            return {
                "broker_order_id": order["id"],
                "status": order["status"],
                "filled_qty": filled_qty,
                "filled_avg_price": filled_price
            }
        except Exception as e:
            logger.error(f"Kraken order failed for {symbol}: {e}")
            return None

    def close_position(self, symbol: str, qty: float, side: str) -> bool:
        """Close a crypto position at market price."""
        try:
            ccxt_symbol = symbol.replace("-", "/")
            close_side = "sell" if side == "buy" else "buy"
            self.exchange.create_market_order(ccxt_symbol, close_side, qty)
            logger.info(f"Kraken position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to close Kraken {symbol}: {e}")
            return False

    def get_balance(self, currency: str = "USD") -> float:
        """Get available balance for a currency."""
        try:
            balance = self.exchange.fetch_balance()
            # Kraken uses ZUSD internally for USD
            usd = float(balance.get(currency, {}).get("free", 0))
            if usd == 0 and currency == "USD":
                usd = float(balance.get("ZUSD", {}).get("free", 0))
            return usd
        except Exception as e:
            logger.debug(f"Kraken balance fetch error: {e}")
            return 0.0

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Quick price lookup."""
        try:
            ccxt_symbol = symbol.replace("-", "/")
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            return float(ticker["last"])
        except Exception as e:
            logger.debug(f"Kraken price lookup failed for {symbol}: {e}")
            return None

    def get_trading_pairs(self) -> list:
        """Get available trading pairs on Kraken."""
        try:
            markets = self.exchange.load_markets()
            return [m for m in markets.keys() if "/USD" in m]
        except Exception as e:
            logger.debug(f"Failed to load Kraken markets: {e}")
            return []
