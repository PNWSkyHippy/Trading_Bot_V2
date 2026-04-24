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
       UNCHECK 'Read-Only API'
       Set port to 7497 (paper) or 7496 (live)
    4. Add IBKR_ACCOUNT to .env
    5. Set IBKR_ENABLED=True in config.py when ready

  Connection model:
    Persistent connection maintained all session. is_available() simply
    checks isConnected() without reconnecting. _ensure_connected() is
    called before every order and reconnects if dropped with backoff.
    This avoids the clientId conflict that caused 'unreachable' warnings
    when connect/disconnect/reconnect happened on every trade.

  ClientId:
    IBKR_CLIENT_ID = 2. If you see 'clientId already in use' change this
    to any unused number (3, 4, etc). Each connection to TWS needs a
    unique clientId. ClientId 1 is often used by TWS itself or other tools.
=============================================================
"""

import logging
import time
from typing import Optional, Dict

import config

logger = logging.getLogger(__name__)

IBKR_PAPER_PORT = 7497
IBKR_LIVE_PORT  = 7496
IBKR_HOST       = "127.0.0.1"
IBKR_CLIENT_ID  = 2      # Changed from 1 — avoids conflict with TWS own clientId
MAX_RECONNECT_ATTEMPTS = 3


class IBKRExecutor:
    """
    Executes stock trades via Interactive Brokers TWS/Gateway API.
    Maintains a persistent connection all session to avoid clientId conflicts.
    """

    def __init__(self):
        self.account    = getattr(config, "IBKR_ACCOUNT", "")
        self.paper_mode = getattr(config, "IBKR_PAPER_MODE", True)
        self.port       = IBKR_PAPER_PORT if self.paper_mode else IBKR_LIVE_PORT
        self._ib        = None
        self._connected = False
        # Establish connection immediately at startup
        self._establish_connection()

    def _establish_connection(self) -> bool:
        """
        Establish persistent connection to TWS.
        Called once at startup and on reconnect attempts.
        Returns True if connected successfully.
        """
        try:
            from ib_insync import IB
            if self._ib is None:
                self._ib = IB()
            if self._ib.isConnected():
                return True
            self._ib.connect(
                host     = IBKR_HOST,
                port     = self.port,
                clientId = IBKR_CLIENT_ID,
                timeout  = 10,
                readonly = False
            )
            if self._ib.isConnected():
                self._connected = True
                logger.info(
                    f"IBKR connected: port={self.port} "
                    f"({'paper' if self.paper_mode else 'LIVE'}) "
                    f"account={self.account or 'default'} "
                    f"clientId={IBKR_CLIENT_ID}"
                )
                return True
            return False
        except Exception as e:
            self._connected = False
            logger.warning(f"IBKR connection attempt failed: {e}")
            return False

    def _ensure_connected(self) -> bool:
        """
        Check connection and reconnect if dropped.
        Uses backoff to avoid hammering TWS.
        Returns True if connected and ready.
        """
        if self._ib and self._ib.isConnected():
            return True

        logger.warning("IBKR connection lost — attempting reconnect...")
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            time.sleep(attempt * 1.0)  # 1s, 2s, 3s backoff
            if self._establish_connection():
                logger.info(f"IBKR reconnected on attempt {attempt}")
                return True
            logger.warning(f"IBKR reconnect attempt {attempt}/{MAX_RECONNECT_ATTEMPTS} failed")

        self._connected = False
        return False

    def is_available(self) -> bool:
        """
        Quick connectivity check — no connect/disconnect.
        Just checks if the persistent connection is alive.
        If not connected, tries one reconnect.
        """
        if self._ib and self._ib.isConnected():
            return True
        return self._establish_connection()

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        """
        Submit a bracket order to IBKR.
        Uses persistent connection — no connect/disconnect cycle.
        """
        if not self._ensure_connected():
            logger.error(f"IBKR submit_order: cannot connect for {symbol}")
            return None

        try:
            from ib_insync import Stock, MarketOrder, StopOrder, LimitOrder

            ib     = self._ib
            shares = max(1, int(round(qty)))
            action = "BUY" if side == "buy" else "SELL"

            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            parent = MarketOrder(
                action        = action,
                totalQuantity = shares,
                transmit      = False,
                orderId       = ib.client.getReqId()
            )

            sl_action = "SELL" if action == "BUY" else "BUY"
            stop = StopOrder(
                action        = sl_action,
                totalQuantity = shares,
                stopPrice     = round(stop_loss, 2),
                parentId      = parent.orderId,
                transmit      = False,
                orderId       = ib.client.getReqId()
            )

            tp = LimitOrder(
                action        = sl_action,
                totalQuantity = shares,
                lmtPrice      = round(take_profit, 2),
                parentId      = parent.orderId,
                transmit      = True,
                orderId       = ib.client.getReqId()
            )

            parent_trade = ib.placeOrder(contract, parent)
            ib.placeOrder(contract, stop)
            ib.placeOrder(contract, tp)

            # Wait for fill (up to 10 seconds)
            for _ in range(20):
                ib.sleep(0.5)
                if parent_trade.orderStatus.status in ("Filled", "PartiallyFilled"):
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

            return {
                "broker_order_id":  str(parent.orderId),
                "status":           status.lower(),
                "filled_qty":       float(filled_qty),
                "filled_avg_price": float(filled_price),
                "manual_sl_tp":     False
            }

        except Exception as e:
            logger.error(f"IBKR order failed for {symbol}: {e}")
            return None

    def close_position(self, symbol: str) -> bool:
        """Close an open IBKR position via market order."""
        if not self._ensure_connected():
            logger.error(f"IBKR close_position: cannot connect for {symbol}")
            return False

        try:
            from ib_insync import Stock, MarketOrder

            ib        = self._ib
            positions = ib.positions(account=self.account or "")
            target    = None

            for pos in positions:
                if pos.contract.symbol == symbol:
                    target = pos
                    break

            if not target:
                logger.warning(f"IBKR close: no position found for {symbol}")
                return False

            qty    = abs(target.position)
            action = "SELL" if target.position > 0 else "BUY"

            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            order = MarketOrder(action=action, totalQuantity=qty, transmit=True)
            trade = ib.placeOrder(contract, order)

            for _ in range(20):
                ib.sleep(0.5)
                if trade.orderStatus.status in ("Filled", "PartiallyFilled"):
                    break

            logger.info(
                f"IBKR position closed: {symbol} {action} {qty} shares | "
                f"Status={trade.orderStatus.status}"
            )
            return True

        except Exception as e:
            logger.error(f"IBKR close_position failed for {symbol}: {e}")
            return False

    def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all open orders for a symbol."""
        if not self._ensure_connected():
            return 0

        try:
            ib          = self._ib
            open_orders = ib.openOrders()
            cancelled   = 0

            for order in open_orders:
                try:
                    ib.cancelOrder(order)
                    cancelled += 1
                except Exception:
                    pass

            logger.info(f"IBKR cancelled {cancelled} open orders for {symbol}")
            return cancelled

        except Exception as e:
            logger.error(f"IBKR cancel_all_orders failed for {symbol}: {e}")
            return 0

    def get_account(self) -> Dict:
        """Fetch account summary from IBKR."""
        if not self._ensure_connected():
            return {"equity": 0, "cash": 0, "buying_power": 0,
                    "portfolio_value": 0, "settled_cash": 0}

        try:
            ib      = self._ib
            summary = ib.accountSummary(account=self.account or "")
            values  = {item.tag: item.value for item in summary}

            equity       = float(values.get("NetLiquidation", 0))
            cash         = float(values.get("CashBalance",    0))
            buying_power = float(values.get("BuyingPower",    0))
            settled_cash = float(values.get("SettledCash",    0))

            logger.info(
                f"IBKR account: equity=${equity:,.2f} | "
                f"cash=${cash:,.2f} | settled=${settled_cash:,.2f}"
            )

            return {
                "equity":          equity,
                "cash":            cash,
                "buying_power":    buying_power,
                "portfolio_value": equity,
                "settled_cash":    settled_cash
            }

        except Exception as e:
            logger.error(f"IBKR get_account failed: {e}")
            return {"equity": 0, "cash": 0, "buying_power": 0,
                    "portfolio_value": 0, "settled_cash": 0}

    def disconnect(self):
        """Graceful shutdown — called when bot stops."""
        try:
            if self._ib and self._ib.isConnected():
                self._ib.disconnect()
                logger.info("IBKR disconnected cleanly.")
        except Exception:
            pass
