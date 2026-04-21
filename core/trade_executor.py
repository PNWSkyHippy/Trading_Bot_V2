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

    def close_position(self, symbol: str) -> bool:
        try:
            self.api.close_position(symbol)
            logger.info(f"Alpaca position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to close {symbol}: {e}")
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
        try:
            positions = self.api.list_positions()
            for pos in positions:
                self.close_position(pos.symbol)
            logger.info(f"Closed {len(positions)} stock positions at end of day.")
        except Exception as e:
            logger.error(f"Error closing all stock positions: {e}")


class CoinbaseExecutor:
    """Executes crypto trades via Coinbase Advanced Trade."""

    def __init__(self):
        self.exchange = ccxt.coinbase({
            "apiKey":          config.COINBASE_API_KEY,
            "secret":          config.COINBASE_SECRET_KEY,
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
        self.coinbase = CoinbaseExecutor()
        self.kraken   = KrakenExecutor(
            api_key    = config.KRAKEN_API_KEY,
            api_secret = config.KRAKEN_SECRET_KEY,
            paper      = config.KRAKEN_PAPER_MODE
        )

        # IBKR executor — lazy loaded only when IBKR_ENABLED=True
        # so the bot starts fine even without ib_insync installed
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
        """
        Full pipeline: approve → settlement check → execute → log → return trade_id.
        """
        logger.info(
            f"Attempting to execute signal: {signal.symbol} {signal.direction}"
        )

        custom_sl  = signal.indicators.get("custom_stop_loss_pct")
        custom_tp  = signal.indicators.get("custom_take_profit_pct")
        custom_pos = signal.indicators.get("custom_position_pct")

        approval = self._risk_manager.approve_trade(
            symbol                 = signal.symbol,
            entry_price            = signal.current_price,
            signal_score           = signal.score,
            direction              = signal.direction,
            custom_stop_loss_pct   = custom_sl,
            custom_take_profit_pct = custom_tp,
            custom_position_pct    = custom_pos
        )
        if not approval.approved:
            logger.info(f"Trade rejected for {signal.symbol}: {approval.reason}")
            return None

        # ── Settlement check for IBKR cash account stock trades ────────
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
            logger.debug(
                f"Settlement check passed: {signal.symbol} | "
                f"need=${approval.position_value:,.2f} available=${available:,.2f}"
            )

        trade_id     = str(uuid.uuid4())[:12]
        broker_result= self._submit(signal, approval)
        if not broker_result:
            logger.error(f"Order submission failed for {signal.symbol}")
            return None

        entry_price = broker_result.get("filled_avg_price") or signal.current_price
        if entry_price == 0:
            entry_price = signal.current_price

        sl_pct = (custom_sl  or config.DEFAULT_STOP_LOSS_PCT)   / 100
        tp_pct = (custom_tp  or config.DEFAULT_TAKE_PROFIT_PCT) / 100

        if signal.direction == "long":
            stop_loss   = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)
        else:
            stop_loss   = entry_price * (1 + sl_pct)
            take_profit = entry_price * (1 - tp_pct)

        broker_name = self._get_broker_name(signal)

        if broker_result.get("manual_sl_tp"):
            logger.info(
                f"[SHORT TICKER] {signal.symbol} — bracket order not supported. "
                f"SL=${stop_loss:.4f} TP=${take_profit:.4f} tracked by position monitor."
            )

        trade_record = {
            "trade_id":        trade_id,
            "symbol":          signal.symbol,
            "asset_class":     signal.asset_class,
            "direction":       signal.direction,
            "entry_time":      datetime.utcnow().isoformat(),
            "entry_price":     round(entry_price, 6),
            "quantity":        approval.quantity,
            "strategy_name":   signal.indicators.get("strategy_name", "original"),
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
            else:
                success = self.alpaca.close_position(symbol)
        elif asset_class == "crypto" and broker == "kraken" and config.KRAKEN_ENABLED:
            side    = "buy" if direction == "long" else "sell"
            success = self.kraken.close_position(symbol, qty, side)
        elif asset_class == "crypto":
            side = "buy" if direction == "long" else "sell"
            try:
                result = self.coinbase.close_position(symbol, qty, side)
                success = result is not False and result is not None
            except Exception as e:
                logger.debug(f"Coinbase close failed for {symbol}: {e} — paper sim")
                success = False
            if not success:
                logger.info(f"[PAPER] Simulated close: {symbol} {side.upper()} @ ${current_price:.4f}")
                success = True

        if not success:
            logger.error(f"Failed to close position {symbol}")
            return False

        if direction == "long":
            pnl = (current_price - entry_price) * qty
        else:
            pnl = (entry_price - current_price) * qty

        pnl_pct   = (pnl / trade["position_value"]) * 100 if trade["position_value"] else 0
        trade_won = pnl > 0

        # Record T+1 settlement for stock trades on IBKR cash account
        if asset_class == "stock" and settlement_tracker:
            try:
                settlement_tracker.record_trade_closed(
                    trade_id       = trade["trade_id"],
                    symbol         = symbol,
                    position_value = trade.get("position_value", 0)
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
            "exit_time":  datetime.utcnow().isoformat(),
            "exit_price": current_price,
            "status":     "closed"
        }
        self._db.record_tax_event(full_trade)
        self._risk_manager.record_trade_result(pnl, trade_won)

        strategy_name = trade.get("strategy_name", "original")
        if strategy_name not in ("original", "manual") and exit_reason != "manual_close":
            try:
                from strategies.strategy_engine import strategy_engine
                strategy_engine.record_trade_result(strategy_name, pnl, trade_won)
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
        """Route order to the correct broker."""
        side   = "buy" if signal.direction == "long" else "sell"
        broker = signal.indicators.get("exchange", "").lower()

        if signal.asset_class == "stock":
            # Try IBKR first if enabled and reachable
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
            # Alpaca fallback
            return self.alpaca.submit_order(
                signal.symbol, approval.quantity, side,
                approval.stop_loss, approval.take_profit
            )

        elif signal.asset_class == "crypto" and "kraken" in broker:
            if not config.KRAKEN_ENABLED:
                logger.info(f"Kraken disabled — routing {signal.symbol} to paper")
                return self._paper_fill(signal, approval)
            return self.kraken.submit_order(
                signal.symbol, approval.quantity, side,
                approval.stop_loss, approval.take_profit
            )
        else:
            result = self.coinbase.submit_order(
                signal.symbol, approval.quantity, side,
                approval.stop_loss, approval.take_profit
            )
            if result is None:
                logger.info(f"Coinbase unavailable — paper sim for {signal.symbol}")
                return self._paper_fill(signal, approval)
            return result

    def _paper_fill(self, signal, approval: TradeApproval) -> Dict:
        """Simulate a paper trade fill locally."""
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
        """Determine broker name to record for this trade."""
        exchange = signal.indicators.get("exchange", "").lower()
        if signal.asset_class == "stock":
            if self._ibkr is not None and self._ibkr.is_available():
                return "ibkr"
            return "alpaca"
        if "kraken" in exchange and config.KRAKEN_ENABLED:
            return "kraken"
        if "kraken" in exchange and not config.KRAKEN_ENABLED:
            return "paper"
        return "coinbase"

    def get_account_value(self) -> float:
        """Get total account equity."""
        try:
            # Prefer IBKR balance if enabled
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
