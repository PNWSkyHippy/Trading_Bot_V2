"""
=============================================================
  TRADE EXECUTOR
  Sends approved orders to the correct broker:
    Stocks: IBKR (preferred, if enabled) → Alpaca (fallback)
    Crypto: Coinbase → Kraken → paper simulation

  IBKR cash account mode:
    - No PDT rule (unlimited day trades with settled funds)
    - settlement_tracker checks settled capital before every IBKR stock trade
    - T+1 settlement (SEC standard since May 2024)
    - Full bracket order support including 1-2 char tickers (unlike Alpaca)

  To switch from Alpaca to IBKR:
    1. Set IBKR_ENABLED = True in config.py
    2. Set IBKR_ACCOUNT = "DUxxxxxxx" in .env
    3. Start TWS or IB Gateway on port 7497 (paper) or 7496 (live)
    4. Set IBKR_PAPER_MODE = True/False to match your TWS session
=============================================================
"""

import uuid
import time
import logging
from datetime import datetime
from typing import Optional, Dict

import alpaca_trade_api as tradeapi
import ccxt

import config
try:
    from core.settlement_tracker import settlement_tracker
except Exception:
    settlement_tracker = None
from reporting.alerts import alert_manager
from core.risk_manager import risk_manager, TradeApproval
from core.kraken_executor import KrakenExecutor
from data.database import db

logger = logging.getLogger(__name__)


class AlpacaExecutor:
    """Executes stock trades via Alpaca Markets API."""

    def __init__(self):
        self.api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.ALPACA_BASE_URL
        )

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        """
        Submit a stock order to Alpaca.
        Short tickers (1-2 chars) use plain market order — Alpaca silently
        rejects bracket orders for these, causing ghost trades.
        """
        if len(symbol) <= 2:
            return self._submit_plain_market(symbol, qty, side, stop_loss, take_profit)

        try:
            order = self.api.submit_order(
                symbol        = symbol,
                qty           = int(qty) if qty >= 1 else qty,
                side          = side,
                type          = "market",
                time_in_force = "day",
                order_class   = "bracket",
                stop_loss     = {"stop_price": str(round(stop_loss, 2))},
                take_profit   = {"limit_price": str(round(take_profit, 2))}
            )
            logger.info(
                f"Alpaca bracket order submitted: {symbol} {side} {qty} shares | "
                f"SL={stop_loss} TP={take_profit} | Order ID: {order.id}"
            )
            return {
                "broker_order_id":  order.id,
                "status":           order.status,
                "filled_qty":       float(order.filled_qty or 0),
                "filled_avg_price": float(order.filled_avg_price or 0),
                "manual_sl_tp":     False
            }
        except Exception as e:
            logger.error(f"Alpaca bracket order failed for {symbol}: {e}")
            logger.warning(f"Falling back to plain market order for {symbol}")
            return self._submit_plain_market(symbol, qty, side, stop_loss, take_profit)

    def _submit_plain_market(self, symbol: str, qty: float, side: str,
                             stop_loss: float, take_profit: float) -> Optional[Dict]:
        """Plain market order — used for short tickers or as bracket fallback."""
        try:
            order = self.api.submit_order(
                symbol        = symbol,
                qty           = int(qty) if qty >= 1 else qty,
                side          = side,
                type          = "market",
                time_in_force = "day"
            )
            logger.info(
                f"[SHORT TICKER] Alpaca plain market order: {symbol} {side} "
                f"{qty} shares | SL/TP managed by position monitor | "
                f"SL={stop_loss:.4f} TP={take_profit:.4f} | Order ID: {order.id}"
            )
            return {
                "broker_order_id":  order.id,
                "status":           order.status,
                "filled_qty":       float(order.filled_qty or 0),
                "filled_avg_price": float(order.filled_avg_price or 0),
                "manual_sl_tp":     True
            }
        except Exception as e:
            logger.error(f"Alpaca plain market order also failed for {symbol}: {e}")
            return None

    def cancel_open_orders(self, symbol: str) -> int:
        """
        Cancel all open orders for a symbol before closing the position.
        This is CRITICAL for bracket orders — the limit (TP) and stop (SL)
        legs must be canceled first or Alpaca will reject the close order
        with 'insufficient qty available'.

        Returns number of orders canceled.
        """
        canceled = 0
        try:
            open_orders = self.api.list_orders(status="open", symbols=[symbol])
            for order in open_orders:
                try:
                    self.api.cancel_order(order.id)
                    canceled += 1
                    logger.info(
                        f"Canceled open order for {symbol}: "
                        f"{order.order_type} {order.side} @ {order.limit_price or order.stop_price} "
                        f"| ID: {order.id}"
                    )
                except Exception as e:
                    logger.warning(f"Could not cancel order {order.id} for {symbol}: {e}")
            if canceled > 0:
                # Brief pause to let Alpaca process cancellations before closing
                time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Error listing open orders for {symbol}: {e}")
        return canceled

    def close_position(self, symbol: str) -> bool:
        """
        Close a position at Alpaca.
        ALWAYS cancels open orders first (bracket legs) before sending
        the close order. Without this, Alpaca returns 'insufficient qty
        available' because the bracket order has already allocated the shares.
        """
        # Step 1: Cancel all open orders (bracket legs) first
        canceled = self.cancel_open_orders(symbol)
        if canceled > 0:
            logger.info(f"Canceled {canceled} open order(s) for {symbol} before closing")

        # Step 2: Now close the actual position
        try:
            self.api.close_position(symbol)
            logger.info(f"Alpaca position closed: {symbol}")
            return True
        except Exception as e:
            # If close_position fails, try a manual market sell
            logger.warning(f"close_position failed for {symbol}: {e} — trying manual market order")
            try:
                pos = self.api.get_position(symbol)
                qty = abs(float(pos.qty))
                side = "sell" if float(pos.qty) > 0 else "buy"
                self.api.submit_order(
                    symbol        = symbol,
                    qty           = qty,
                    side          = side,
                    type          = "market",
                    time_in_force = "day"
                )
                logger.info(f"Manual market close submitted for {symbol} {side} {qty}")
                return True
            except Exception as e2:
                logger.error(f"Failed to close {symbol}: {e2}")
                return False

    def get_position(self, symbol: str) -> Optional[Dict]:
        try:
            pos = self.api.get_position(symbol)
            return {
                "symbol":        pos.symbol,
                "qty":           float(pos.qty),
                "market_value":  float(pos.market_value),
                "unrealized_pl": float(pos.unrealized_pl),
                "current_price": float(pos.current_price),
                "avg_entry":     float(pos.avg_entry_price)
            }
        except Exception:
            return None

    def get_account(self) -> Dict:
        acct = self.api.get_account()
        return {
            "equity":          float(acct.equity),
            "cash":            float(acct.cash),
            "buying_power":    float(acct.buying_power),
            "portfolio_value": float(acct.portfolio_value)
        }

    def close_all_stock_positions(self):
        """
        Close all open stock positions at EOD.
        Cancels all open orders first, then closes positions.
        """
        try:
            # Cancel ALL open orders first before closing any positions
            try:
                all_open_orders = self.api.list_orders(status="open")
                for order in all_open_orders:
                    try:
                        self.api.cancel_order(order.id)
                        logger.info(f"EOD: Canceled order {order.id} for {order.symbol}")
                    except Exception as e:
                        logger.warning(f"EOD: Could not cancel order {order.id}: {e}")
                if all_open_orders:
                    time.sleep(1)  # Let cancellations process
            except Exception as e:
                logger.warning(f"EOD: Error canceling open orders: {e}")

            # Now close all positions
            positions = self.api.list_positions()
            for pos in positions:
                try:
                    self.api.close_position(pos.symbol)
                    logger.info(f"EOD: Closed position {pos.symbol}")
                except Exception as e:
                    logger.error(f"EOD: Failed to close {pos.symbol}: {e}")
            logger.info(f"EOD close complete: {len(positions)} position(s) processed.")
        except Exception as e:
            logger.error(f"Error in EOD close all: {e}")


class KrakenSpotExecutor:
    """
    Legacy direct-ccxt Kraken executor.
    NOTE: The primary crypto execution path is KrakenExecutor (core/kraken_executor.py),
    which handles paper mode, stop orders, and position tracking. This class was
    previously named CoinbaseExecutor but always used Kraken internally. It is
    retained for reference and potential fallback use; the main TradeExecutor
    routes all crypto through self.kraken (KrakenExecutor), not this class.
    """

    def __init__(self):
        self.exchange = ccxt.kraken({
            "apiKey":          config.KRAKEN_API_KEY,
            "secret":          config.KRAKEN_SECRET_KEY,
            "enableRateLimit": True,
        })

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        try:
            order = self.exchange.create_market_order(symbol, side, qty)
            filled_price = float(order.get("average") or order.get("price") or 0)
            filled_qty   = float(order.get("filled") or qty)
            logger.info(
                f"Coinbase order filled: {symbol} {side} "
                f"{filled_qty} @ ${filled_price:.4f}"
            )
            return {
                "broker_order_id":  order["id"],
                "status":           order["status"],
                "filled_qty":       filled_qty,
                "filled_avg_price": filled_price
            }
        except Exception as e:
            logger.error(f"Coinbase order failed for {symbol}: {e}")
            return None

    def close_position(self, symbol: str, qty: float, side: str) -> bool:
        try:
            close_side = "sell" if side == "buy" else "buy"
            self.exchange.create_market_order(symbol, close_side, qty)
            logger.info(f"Coinbase position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to close Coinbase {symbol}: {e}")
            return False

    def get_balance(self, currency: str = "USD") -> float:
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get(currency, {}).get("free", 0))
        except Exception as e:
            logger.debug(f"Balance fetch error: {e}")
            return 0.0


class TradeExecutor:
    """
    Unified executor that coordinates risk approval, order submission,
    and logging.

    Stock broker priority:
      1. IBKR  — if IBKR_ENABLED=True and TWS is reachable
                  Cash account: no PDT, settlement tracked by settlement_tracker
      2. Alpaca — fallback (paper mode by default)

    Crypto broker priority:
      1. Kraken  — if KRAKEN_ENABLED=True
      2. Coinbase
      3. Paper simulation — if both fail
    """

    def __init__(self, db_ref=None, risk_manager_ref=None, broker_manager_ref=None):
        self._db           = db_ref or db
        self._risk_manager = risk_manager_ref or risk_manager

        self.alpaca   = AlpacaExecutor()
        self.kraken   = KrakenExecutor(
            api_key    = config.KRAKEN_API_KEY,
            api_secret = config.KRAKEN_SECRET_KEY,
            paper      = config.KRAKEN_PAPER_MODE
        )

        self._ibkr = None
        if getattr(config, "IBKR_ENABLED", False):
            try:
                from core.ibkr_executor import IBKRExecutor
                self._ibkr = IBKRExecutor()
                logger.info(
                    f"IBKR executor initialized — "
                    f"{'paper' if config.IBKR_PAPER_MODE else 'LIVE'} mode | "
                    f"account={config.IBKR_ACCOUNT or 'default'}"
                )
            except Exception as e:
                logger.warning(
                    f"IBKR executor failed to initialize: {e} — "
                    f"falling back to Alpaca for stocks"
                )

    def execute_signal(self, signal) -> Optional[str]:
        logger.info(
            f"Attempting to execute signal: {signal.symbol} {signal.direction}"
        )

        custom_sl  = signal.indicators.get("custom_stop_loss_pct")
        custom_tp  = signal.indicators.get("custom_take_profit_pct")
        custom_pos = signal.indicators.get("custom_position_pct")

        # Pass broker name to risk_manager so it can check per-broker cash
        broker_name_hint = self._get_broker_name(signal)
        self._risk_manager._pending_broker = broker_name_hint
        approval = self._risk_manager.approve_trade(
            symbol                 = signal.symbol,
            entry_price            = signal.current_price,
            signal_score           = signal.score,
            direction              = signal.direction,
            custom_stop_loss_pct   = custom_sl,
            custom_take_profit_pct = custom_tp,
            custom_position_pct    = custom_pos
        )
        self._risk_manager._pending_broker = None   # clear after use
        if not approval.approved:
            logger.info(f"Trade rejected for {signal.symbol}: {approval.reason}")
            return None

        if (signal.asset_class == "stock" and
                self._ibkr is not None and
                settlement_tracker is not None and
                getattr(config, "CASH_ACCOUNT_MODE", True)):
            allowed, reason, available = settlement_tracker.can_open_trade(
                approval.position_value
            )
            if not allowed:
                logger.info(
                    f"Trade blocked by settlement tracker: {signal.symbol} — {reason}"
                )
                return None

        trade_id     = str(uuid.uuid4())[:12]
        broker_result= self._submit(signal, approval)
        if not broker_result:
            logger.error(f"Order submission failed for {signal.symbol}")
            return None

        entry_price = broker_result.get("filled_avg_price") or signal.current_price
        if entry_price == 0:
            entry_price = signal.current_price

        tp_pct = (custom_tp or config.DEFAULT_TAKE_PROFIT_PCT) / 100

        if signal.direction == "long":
            take_profit = entry_price * (1 + tp_pct)
        else:
            take_profit = entry_price * (1 - tp_pct)

        # ── Structural stop: recompute at fill price (hard pre-live gate) ───
        # The scanner embeds structural_stop_price from bars at signal time.
        # An adverse fill (price moved between signal and execution) can place
        # the stop above the fill price for longs (or below for shorts), causing
        # an immediate stop-out on the next monitor cycle.
        # Fix: re-run initial_stop_from_tail() on fresh bars after the fill is
        # confirmed, then validate the result is on the correct side of fill price.
        structural_stop = signal.indicators.get("structural_stop_price")
        if structural_stop is not None:
            try:
                from core.stop_engine import stop_engine as _se
                from scanners.market_scanner import scanner as _sc
                _tf = signal.indicators.get(
                    "timeframe", "5Min" if signal.asset_class == "stock" else "5m"
                )
                if signal.asset_class == "stock":
                    _fresh = _sc.stock_scanner.get_bars(
                        signal.symbol, timeframe=_tf, limit=10
                    )
                else:
                    _fresh = _sc.crypto_scanner.get_ohlcv(
                        signal.symbol, timeframe=_tf, limit=10
                    )
                if _fresh is not None and len(_fresh) >= 3:
                    _new_stop = _se.initial_stop_from_tail(_fresh, signal.direction)
                    _valid = (
                        (signal.direction == "long"  and _new_stop < entry_price) or
                        (signal.direction == "short" and _new_stop > entry_price)
                    )
                    if _valid:
                        logger.info(
                            f"[STOP REFRESH] {signal.symbol}: structural stop "
                            f"recomputed at fill — "
                            f"${structural_stop:.6f} → ${_new_stop:.6f}"
                        )
                        structural_stop = _new_stop
                    else:
                        logger.warning(
                            f"[STOP REFRESH] {signal.symbol}: fresh structural stop "
                            f"${_new_stop:.6f} is on the wrong side of fill price "
                            f"${entry_price:.6f} ({signal.direction}) — "
                            f"falling back to percent-based stop"
                        )
                        structural_stop = None   # force percent fallback below
            except Exception as _sr_err:
                logger.warning(
                    f"[STOP REFRESH] {signal.symbol}: could not recompute "
                    f"structural stop at fill: {_sr_err}"
                )

        if structural_stop is not None:
            stop_loss = structural_stop
        else:
            sl_pct    = (custom_sl or config.DEFAULT_STOP_LOSS_PCT) / 100
            stop_loss = (entry_price * (1 - sl_pct) if signal.direction == "long"
                         else entry_price * (1 + sl_pct))

        broker_name = self._get_broker_name(signal)

        trade_record = {
            "trade_id":        trade_id,
            "symbol":          signal.symbol,
            "asset_class":     signal.asset_class,
            "direction":       signal.direction,
            "entry_time":      datetime.now().isoformat(),
            "entry_price":     round(entry_price, 6),
            "quantity":        approval.quantity,
            "strategy_name":   signal.indicators.get("strategy_name", "original"),
            "entry_timeframe": signal.indicators.get("timeframe", "5Min"),
            "position_value":  approval.position_value,
            "stop_loss":       round(stop_loss, 6),
            "take_profit":     round(take_profit, 6),
            "signal_score":    signal.score,
            "indicators":      signal.indicators,
            "broker":          broker_name,
            "broker_order_id": broker_result.get("broker_order_id")
        }
        self._db.open_trade(trade_record)

        try:
            alert_manager.trade_opened({
                "symbol": signal.symbol, "direction": signal.direction,
                "entry_price": entry_price, "stop_loss": stop_loss,
                "take_profit": take_profit, "position_value": approval.position_value,
                "strategy_name": signal.indicators.get("strategy_name", "unknown")
            })
        except Exception:
            pass

        logger.info(
            f"[TRADE OPEN] {signal.symbol} {signal.direction.upper()} | "
            f"Entry: ${entry_price:.4f} | Qty: {approval.quantity:.4f} | "
            f"SL: ${stop_loss:.4f} | TP: ${take_profit:.4f} | "
            f"Broker: {broker_name} | ID: {trade_id}"
        )

        # ── Update broker available cash (deduct position value) ──────────
        try:
            from core.broker_manager import broker_manager
            bal = broker_manager.get_broker_balance(broker_name)
            new_invested  = bal.get("invested",  0.0) + approval.position_value
            new_available = max(0.0, bal.get("available", 0.0) - approval.position_value)
            broker_manager.update_broker_balance(
                broker_name, bal.get("balance", 0.0),
                new_invested, new_available
            )
        except Exception as _bm_err:
            logger.debug(f"Broker balance update on open failed: {_bm_err}")

        # ── Place real stop order on Kraken (live + paper) ────────────────
        # In paper mode this stores a fake order ID for tracking logic parity.
        # In live mode this places an actual stop-market order on Kraken.
        if signal.asset_class == "crypto" and broker_name in ("kraken", "paper"):
            stop_side = "buy" if signal.direction == "short" else "sell"
            stop_order_id = self.kraken.place_stop_order(
                signal.symbol, approval.quantity, stop_side, round(stop_loss, 6)
            )
            if stop_order_id:
                self._db.update_trade_order_ids(trade_id, stop_order_id=stop_order_id)
                logger.info(
                    f"[{'PAPER' if config.KRAKEN_PAPER_MODE else 'LIVE'}] "
                    f"Stop order placed for {signal.symbol} @ ${stop_loss:.4f} "
                    f"| order_id={stop_order_id}"
                )

        return trade_id

    def close_trade(self, trade: Dict, current_price: float,
                    exit_reason: str) -> bool:
        symbol      = trade["symbol"]
        direction   = trade["direction"]
        qty         = trade["quantity"]
        entry_price = trade["entry_price"]
        asset_class = trade["asset_class"]
        broker      = trade.get("broker", "alpaca")

        success = False
        if asset_class == "stock":
            if broker == "ibkr" and self._ibkr is not None:
                success = self._ibkr.close_position(symbol)
                # If IBKR close failed, check if position actually exists.
                if not success:
                    try:
                        ibkr_positions = self._ibkr._ib.positions()
                        has_pos = any(
                            p.contract.symbol == symbol
                            for p in ibkr_positions
                        )
                        if not has_pos:
                            logger.info(
                                f"[IBKR] {symbol}: no position found in Gateway "
                                f"— treating as already closed (paper mode quirk)"
                            )
                            success = True
                    except Exception:
                        pass

                # If IBKR still failed, ALWAYS try Alpaca too.
                # The position may have been opened via Alpaca fallback even
                # though DB records broker=ibkr. Both brokers must be checked.
                if not success:
                    logger.warning(
                        f"[IBKR CLOSE FAILED] {symbol}: trying Alpaca as well "
                        f"(position may exist on either broker)"
                    )
                    alpaca_success = self.alpaca.close_position(symbol)
                    if alpaca_success:
                        logger.info(f"[ALPACA FALLBACK CLOSE] {symbol}: closed via Alpaca")
                        success = True
                    else:
                        logger.warning(f"[ALPACA FALLBACK CLOSE] {symbol}: not found on Alpaca either")
                        # Both brokers checked — position genuinely doesn't exist
                        # Mark as success to clear from DB and stop retry loop
                        success = True
                        logger.info(
                            f"[CLOSE GHOST] {symbol}: not found on IBKR or Alpaca "
                            f"— marking closed in DB (ghost trade cleanup)"
                        )
            else:
                success = self.alpaca.close_position(symbol)
                # If Alpaca doesn't have it, check IBKR too
                if not success and self._ibkr is not None:
                    logger.warning(
                        f"[ALPACA CLOSE FAILED] {symbol}: trying IBKR as well"
                    )
                    ibkr_success = self._ibkr.close_position(symbol)
                    if ibkr_success:
                        logger.info(f"[IBKR FALLBACK CLOSE] {symbol}: closed via IBKR")
                        success = True
        elif asset_class == "crypto":
            # Kraken is the default crypto executor — Coinbase API is deprecated.
            side = "buy" if direction == "long" else "sell"
            if config.KRAKEN_ENABLED:
                success = self.kraken.close_position(symbol, qty, side)
            else:
                logger.info(f"[PAPER] Simulated close: {symbol} {side.upper()} @ ${current_price:.4f}")
                success = True

        if not success:
            logger.error(f"Failed to close position {symbol}")
            return False

        if direction == "long":
            pnl = (current_price - entry_price) * qty
        else:
            pnl = (entry_price - current_price) * qty

        # ── PnL% — calculate directly from price move, not position_value ─
        # position_value in DB can drift; price-based calc is always correct.
        # pnl_pct = % move from entry to exit, always positive for wins.
        if entry_price and entry_price > 0:
            raw_move_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_pct      = raw_move_pct if direction == "long" else -raw_move_pct
        else:
            pnl_pct = (pnl / trade["position_value"]) * 100 if trade["position_value"] else 0

        # ── Sanity check: pnl_pct should never exceed 3x the configured TP ─
        max_tp_pct = config.DEFAULT_TAKE_PROFIT_PCT * 3
        if abs(pnl_pct) > max_tp_pct:
            logger.warning(
                f"[PNL SANITY] {symbol}: pnl_pct={pnl_pct:.2f}% exceeds 3x TP threshold "
                f"({max_tp_pct:.1f}%). Capping and flagging for review. "
                f"entry={entry_price} exit={current_price} qty={qty}"
            )
            pnl_pct = max_tp_pct if pnl_pct > 0 else -max_tp_pct
            # Recalculate pnl dollar amount to match capped pct
            pnl = (pnl_pct / 100) * trade["position_value"]

        trade_won = pnl > 0

        if asset_class == "stock" and settlement_tracker:
            try:
                settlement_tracker.record_trade_closed(
                    trade_id       = trade["trade_id"],
                    symbol         = symbol,
                    position_value = trade.get("position_value", 0),
                    asset_class    = asset_class   # crypto excluded automatically
                )
            except Exception as e:
                logger.debug(f"Settlement record error: {e}")

        self._db.close_trade(
            trade_id   = trade["trade_id"],
            exit_price = current_price,
            exit_reason= exit_reason,
            pnl        = round(pnl, 4),
            pnl_pct    = round(pnl_pct, 4)
        )

        full_trade = {
            **trade,
            "exit_time":  datetime.now().isoformat(),
            "exit_price": current_price,
            "status":     "closed"
        }
        self._db.record_tax_event(full_trade)
        self._risk_manager.record_trade_result(pnl, trade_won, symbol=symbol)

        strategy_name = trade.get("strategy_name", "original")
        if strategy_name not in ("original", "manual") and exit_reason != "manual_close":
            try:
                from strategies.strategy_engine import strategy_engine
                strategy_engine.record_trade_result(
                    strategy_name, pnl, trade_won, exit_reason=exit_reason
                )
            except Exception as e:
                logger.debug(f"Strategy result recording error: {e}")

        if strategy_name == "scalp_master" and exit_reason != "manual_close":
            try:
                from strategies.scalp_master import log_trade_result
                log_trade_result(symbol, round(pnl_pct, 4), trade_won)
            except Exception as e:
                logger.debug(f"Scalp adaptive params update error: {e}")

        cap = self._db.get_latest_capital()
        if cap:
            new_capital = cap["total_capital"] + pnl
            self._db.log_capital(
                total     = new_capital,
                available = cap["available_cash"] + trade["position_value"] + pnl,
                invested  = max(0, cap["invested_value"] - trade["position_value"]),
                daily_pnl = cap["daily_pnl"] + pnl,
                total_pnl = cap["total_pnl"] + pnl,
                note      = (
                    f"Closed {symbol} @ {broker} {exit_reason}: "
                    f"{'+'if pnl>0 else ''}{pnl:.2f}"
                )
            )

        # ── Restore broker available cash (return position value + PnL) ────
        try:
            from core.broker_manager import broker_manager
            close_broker = trade.get("broker", broker)
            bal = broker_manager.get_broker_balance(close_broker)
            returned      = trade.get("position_value", 0.0) + pnl
            new_invested  = max(0.0, bal.get("invested",  0.0) - trade.get("position_value", 0.0))
            new_available = bal.get("available", 0.0) + returned
            new_balance   = bal.get("balance",  0.0) + pnl
            broker_manager.update_broker_balance(
                close_broker, new_balance, new_invested, new_available
            )
        except Exception as _bm_err:
            logger.debug(f"Broker balance update on close failed: {_bm_err}")

        result = "WIN" if trade_won else "LOSS"
        try:
            alert_manager.trade_closed({
                "symbol": symbol, "direction": direction,
                "entry_price": entry_price, "exit_price": current_price,
                "pnl": round(pnl, 4), "pnl_pct": round(pnl_pct, 4),
                "exit_reason": exit_reason,
                "strategy_name": trade.get("strategy_name", "unknown")
            })
        except Exception:
            pass

        logger.info(
            f"[TRADE CLOSED] [{result}] {symbol} | {broker} | {exit_reason} | "
            f"PnL: {'+'if pnl>0 else ''}{pnl:.4f} ({pnl_pct:+.2f}%)"
        )
        return True

    def close_all_stock_positions(self):
        """Close all open stock positions — called at end of day."""
        self.alpaca.close_all_stock_positions()

    def _submit(self, signal, approval: TradeApproval) -> Optional[Dict]:
        side   = "buy" if signal.direction == "long" else "sell"
        broker = signal.indicators.get("exchange", "").lower()

        if signal.asset_class == "stock":
            if self._ibkr is not None:
                if self._ibkr.is_available():
                    logger.info(f"Routing {signal.symbol} to IBKR (cash account)")
                    result = self._ibkr.submit_order(
                        signal.symbol, approval.quantity, side,
                        approval.stop_loss, approval.take_profit
                    )
                    if result is not None:
                        return result
                    logger.warning(
                        f"IBKR order failed for {signal.symbol} — "
                        f"falling back to Alpaca"
                    )
                else:
                    logger.warning(
                        f"IBKR unreachable (TWS not running?) — "
                        f"falling back to Alpaca for {signal.symbol}"
                    )
            return self.alpaca.submit_order(
                signal.symbol, approval.quantity, side,
                approval.stop_loss, approval.take_profit
            )

        elif signal.asset_class == "crypto":
            # Kraken is the default crypto executor — Coinbase API is deprecated.
            if not config.KRAKEN_ENABLED:
                return self._paper_fill(signal, approval)
            return self.kraken.submit_order(
                signal.symbol, approval.quantity, side,
                approval.stop_loss, approval.take_profit
            )

    def _paper_fill(self, signal, approval: TradeApproval) -> Dict:
        logger.info(
            f"[PAPER] Simulated fill: {signal.symbol} {signal.direction.upper()} "
            f"@ ${signal.current_price:.4f} x {approval.quantity:.6f}"
        )
        return {
            "broker_order_id":  f"PAPER-{signal.symbol}-{int(signal.current_price)}",
            "status":           "filled",
            "filled_qty":       approval.quantity,
            "filled_avg_price": signal.current_price,
        }

    def _get_broker_name(self, signal) -> str:
        exchange = signal.indicators.get("exchange", "").lower()
        if signal.asset_class == "stock":
            if self._ibkr is not None and self._ibkr.is_available():
                return "ibkr"
            return "alpaca"
        if signal.asset_class == "crypto":
            return "kraken" if config.KRAKEN_ENABLED else "paper"

    def get_account_value(self) -> float:
        try:
            if self._ibkr is not None and self._ibkr.is_available():
                acct = self._ibkr.get_account()
                return acct["equity"]
            acct = self.alpaca.get_account()
            return acct["equity"]
        except Exception:
            cap = self._db.get_latest_capital()
            return cap["total_capital"] if cap else 0.0


# Singleton
executor = TradeExecutor()
