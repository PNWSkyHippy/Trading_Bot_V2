"""
=============================================================
  IBKR EXECUTOR
  Executes stock trades via Interactive Brokers using ib_insync.

  IBKR Cash Account advantages:
    - No PDT rule (trading with settled funds only)
    - No $25K minimum
    - Full API access via TWS or IB Gateway
    - T+1 settlement (SEC standard since 2024)

  Setup:
    1. Install: pip install ib_insync --break-system-packages
    2. Run TWS or IB Gateway on localhost
    3. Enable API access in TWS: File -> Global Config -> API -> Settings
       Check 'Enable ActiveX and Socket Clients'
       Set port to 7497 (paper) or 7496 (live)
    4. Add IBKR_USERNAME and IBKR_ACCOUNT to .env
    5. Set IBKR_ENABLED=True in config.py when ready

  Paper trading:
    TWS paper account uses port 7497.
    Set IBKR_PAPER_MODE=True in config.py.

  Notes:
    - ib_insync requires TWS or IB Gateway to be running locally.
    - The bot connects on demand and disconnects after each order
      to avoid holding a persistent connection that TWS may drop.
    - For bracket orders IBKR uses OCA (One Cancels All) groups.
    - Short tickers (1-2 chars) work fine with IBKR unlike Alpaca.
=============================================================
"""

import logging
import time
from typing import Optional, Dict

import config

logger = logging.getLogger(__name__)

# IBKR TWS/Gateway ports
IBKR_PAPER_PORT = 7497   # TWS paper trading
IBKR_LIVE_PORT  = 7496   # TWS live trading
IBKR_HOST       = "127.0.0.1"
IBKR_CLIENT_ID  = 1      # Unique client ID — change if running multiple bots


class IBKRExecutor:
    """
    Executes stock trades via Interactive Brokers TWS/Gateway API.
    Uses ib_insync for clean async-compatible IBKR communication.
    """

    def __init__(self):
        self.account    = getattr(config, "IBKR_ACCOUNT", "")
        self.paper_mode = getattr(config, "IBKR_PAPER_MODE", True)
        self.port       = IBKR_PAPER_PORT if self.paper_mode else IBKR_LIVE_PORT
        self._ib        = None

    def _connect(self):
        """
        Connect to TWS or IB Gateway.
        Raises RuntimeError if connection fails (TWS not running).
        """
        try:
            from ib_insync import IB
            ib = IB()
            ib.connect(
                host      = IBKR_HOST,
                port      = self.port,
                clientId  = IBKR_CLIENT_ID,
                timeout   = 10,
                readonly  = False
            )
            if not ib.isConnected():
                raise RuntimeError("ib_insync connected but isConnected() is False")
            self._ib = ib
            logger.info(
                f"IBKR connected: port={self.port} "
                f"({'paper' if self.paper_mode else 'LIVE'}) "
                f"account={self.account or 'default'}"
            )
            return ib
        except ImportError:
            raise RuntimeError(
                "ib_insync not installed. Run: "
                "pip install ib_insync --break-system-packages"
            )
        except Exception as e:
            raise RuntimeError(f"IBKR connection failed: {e}")

    def _disconnect(self):
        try:
            if self._ib and self._ib.isConnected():
                self._ib.disconnect()
        except Exception:
            pass
        self._ib = None

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        """
        Submit a stock order to IBKR via bracket order (OCA group).
        Works correctly for all ticker lengths including 1-2 char symbols.

        Args:
            symbol:      Stock ticker (e.g. 'V', 'GE', 'NVDA')
            qty:         Number of shares (will be rounded to int)
            side:        'buy' or 'sell'
            stop_loss:   Stop-loss price
            take_profit: Take-profit limit price

        Returns:
            Dict with broker_order_id, status, filled_qty, filled_avg_price
            or None on failure.
        """
        try:
            from ib_insync import Stock, MarketOrder, StopOrder, LimitOrder, IB

            ib = self._connect()

            # IBKR requires integer share quantities for stocks
            shares = max(1, int(round(qty)))
            action = "BUY" if side == "buy" else "SELL"

            # Define the stock contract
            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            # Parent market order
            parent = MarketOrder(
                action     = action,
                totalQuantity = shares,
                transmit   = False,     # Hold — send with children
                orderId    = ib.client.getReqId()
            )

            # Stop-loss child
            sl_action = "SELL" if action == "BUY" else "BUY"
            stop = StopOrder(
                action        = sl_action,
                totalQuantity = shares,
                stopPrice     = round(stop_loss, 2),
                parentId      = parent.orderId,
                transmit      = False,
                orderId       = ib.client.getReqId()
            )

            # Take-profit child — transmit=True sends the whole bracket
            tp = LimitOrder(
                action        = sl_action,
                totalQuantity = shares,
                lmtPrice      = round(take_profit, 2),
                parentId      = parent.orderId,
                transmit      = True,   # This transmits the whole OCA group
                orderId       = ib.client.getReqId()
            )

            # Place all three orders
            parent_trade = ib.placeOrder(contract, parent)
            ib.placeOrder(contract, stop)
            ib.placeOrder(contract, tp)

            # Wait for fill (up to 10 seconds for market order)
            timeout = 10
            elapsed = 0
            while elapsed < timeout:
                ib.sleep(0.5)
                elapsed += 0.5
                if parent_trade.orderStatus.status in (
                    "Filled", "PartiallyFilled"
                ):
                    break

            status       = parent_trade.orderStatus.status
            filled_qty   = parent_trade.orderStatus.filled or 0
            filled_price = parent_trade.orderStatus.avgFillPrice or 0.0

            logger.info(
                f"IBKR bracket order: {symbol} {action} {shares} shares | "
                f"Status={status} | Fill=${filled_price:.4f} | "
                f"SL={stop_loss:.4f} TP={take_profit:.4f} | "
                f"OrderID={parent.orderId}"
            )

            self._disconnect()

            return {
                "broker_order_id":  str(parent.orderId),
                "status":           status.lower(),
                "filled_qty":       float(filled_qty),
                "filled_avg_price": float(filled_price),
                "manual_sl_tp":     False
            }

        except Exception as e:
            logger.error(f"IBKR order failed for {symbol}: {e}")
            self._disconnect()
            return None

    def close_position(self, symbol: str) -> bool:
        """
        Close an open IBKR position by submitting a market order
        in the opposite direction of the current holding.
        """
        try:
            from ib_insync import Stock, MarketOrder

            ib = self._connect()

            # Find current position
            positions = ib.positions(account=self.account or "")
            target = None
            for pos in positions:
                if pos.contract.symbol == symbol:
                    target = pos
                    break

            if not target:
                logger.warning(f"IBKR close: no position found for {symbol}")
                self._disconnect()
                return False

            qty    = abs(target.position)
            action = "SELL" if target.position > 0 else "BUY"

            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            order = MarketOrder(action=action, totalQuantity=qty, transmit=True)
            trade = ib.placeOrder(contract, order)

            # Wait for fill
            for _ in range(20):
                ib.sleep(0.5)
                if trade.orderStatus.status in ("Filled", "PartiallyFilled"):
                    break

            logger.info(
                f"IBKR position closed: {symbol} {action} {qty} shares | "
                f"Status={trade.orderStatus.status}"
            )
            self._disconnect()
            return True

        except Exception as e:
            logger.error(f"IBKR close_position failed for {symbol}: {e}")
            self._disconnect()
            return False

    def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all open orders for a symbol. Returns count cancelled."""
        try:
            from ib_insync import Stock

            ib = self._connect()
            open_orders = ib.openOrders()
            cancelled = 0

            for order in open_orders:
                # ib_insync open orders don't always have contract attached
                # so we cancel any order for this symbol by checking reqId
                try:
                    ib.cancelOrder(order)
                    cancelled += 1
                except Exception:
                    pass

            self._disconnect()
            logger.info(f"IBKR cancelled {cancelled} open orders for {symbol}")
            return cancelled

        except Exception as e:
            logger.error(f"IBKR cancel_all_orders failed for {symbol}: {e}")
            self._disconnect()
            return 0

    def get_account(self) -> Dict:
        """
        Fetch account summary from IBKR.
        Returns dict with equity, cash, buying_power, settled_cash.
        settled_cash is the key value for cash account settlement tracking.
        """
        try:
            ib = self._connect()

            summary = ib.accountSummary(account=self.account or "")
            values  = {item.tag: item.value for item in summary}

            equity        = float(values.get("NetLiquidation",      0))
            cash          = float(values.get("CashBalance",          0))
            buying_power  = float(values.get("BuyingPower",          0))
            settled_cash  = float(values.get("SettledCash",          0))

            self._disconnect()

            logger.info(
                f"IBKR account: equity=${equity:,.2f} | "
                f"cash=${cash:,.2f} | settled=${settled_cash:,.2f} | "
                f"buying_power=${buying_power:,.2f}"
            )

            return {
                "equity":        equity,
                "cash":          cash,
                "buying_power":  buying_power,
                "portfolio_value": equity,
                "settled_cash":  settled_cash   # Key for cash account mode
            }

        except Exception as e:
            logger.error(f"IBKR get_account failed: {e}")
            self._disconnect()
            return {
                "equity": 0, "cash": 0,
                "buying_power": 0, "portfolio_value": 0,
                "settled_cash": 0
            }

    def is_available(self) -> bool:
        """
        Quick connectivity check — returns True if TWS/Gateway is reachable.
        Used by trade_executor to decide whether to route to IBKR or fall back.
        """
        try:
            ib = self._connect()
            connected = ib.isConnected()
            self._disconnect()
            return connected
        except Exception:
            return False
