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
import json
import math
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict

# ── Duplicate-entry race-condition guard ──────────────────────────────────────
# Tracks symbols currently mid-execution. Prevents two scan cycles firing
# within ~2s from both passing the DB "already open?" check before the first
# write commits. Lock makes the check-and-add atomic across threads.
_pending_symbols: set = set()
_pending_lock = threading.Lock()
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

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
from core.exchange_capabilities import exchange_capabilities
from core.broker_manager import broker_manager as shared_broker_manager
from core.event_identity import derive_kraken_userref
from data.database import db

logger = logging.getLogger(__name__)


@dataclass
class PartialCloseOutcome:
    """Confirmed result returned to the scanner partial-close coordinator."""

    success: bool
    reason: str
    filled_qty: float = 0.0
    fill_price: float = 0.0
    full_fill: bool = False
    stop_refresh_required: bool = False
    reconciliation_required: bool = False
    retryable: bool = False
    broker_order_id: Optional[str] = None
    cancellation: Dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.success


def _stock_entries_allowed_now() -> bool:
    """Stocks may open during regular hours, but not after the EOD close window."""
    from core.market_calendar import is_us_equity_regular_session_now

    return is_us_equity_regular_session_now(
        open_hour=9,
        open_minute=30,
        close_hour=15,
        close_minute=45,
    )


class AlpacaExecutor:
    """Executes stock trades via Alpaca Markets API."""

    def __init__(self):
        if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
            raise RuntimeError(
                "Alpaca credentials are not configured. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY, or APCA_API_KEY_ID and APCA_API_SECRET_KEY."
            )
        self.api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.ALPACA_BASE_URL
        )

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float,
                     client_order_id: Optional[str] = None) -> Optional[Dict]:
        """
        Submit a stock order to Alpaca.
        Short tickers (1-2 chars) use plain market order — Alpaca silently
        rejects bracket orders for these, causing ghost trades.
        """
        if len(symbol) <= 2:
            return self._submit_plain_market(symbol, qty, side, stop_loss, take_profit,
                                              client_order_id=client_order_id)

        try:
            order = self.api.submit_order(
                symbol        = symbol,
                qty           = int(qty) if qty >= 1 else qty,
                side          = side,
                type          = "market",
                time_in_force = "day",
                order_class   = "bracket",
                stop_loss     = {"stop_price": str(round(stop_loss, 2))},
                take_profit   = {"limit_price": str(round(take_profit, 2))},
                client_order_id = client_order_id,
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
            return self._submit_plain_market(symbol, qty, side, stop_loss, take_profit,
                                              client_order_id=client_order_id)

    def _submit_plain_market(self, symbol: str, qty: float, side: str,
                             stop_loss: float, take_profit: float,
                             client_order_id: Optional[str] = None) -> Optional[Dict]:
        """Plain market order — used for short tickers or as bracket fallback."""
        try:
            order = self.api.submit_order(
                symbol        = symbol,
                qty           = int(qty) if qty >= 1 else qty,
                side          = side,
                type          = "market",
                time_in_force = "day",
                client_order_id = client_order_id,
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
        self._broker_manager = (
            broker_manager_ref
            if broker_manager_ref is not None
            else shared_broker_manager
        )

        self.alpaca = None
        try:
            self.alpaca = AlpacaExecutor()
        except Exception as e:
            logger.warning(
                f"Alpaca executor disabled: {e} "
                "Stock orders will be unavailable unless IBKR live trading is enabled."
            )

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

    def execute_signal(self, signal, disposition_out: Optional[dict] = None) -> Optional[str]:
        # disposition_out, if provided, is mutated in place with at least an
        # "outcome" key classifying the broker-exposure result of this call:
        # "pre_submission_rejected" | "rejected_no_exposure" | "accepted" |
        # "submission_unknown". Defaults to "pre_submission_rejected" and is
        # only ever narrowed — never widen a known-safe outcome back into
        # ambiguity. This is additive/optional: existing callers that don't
        # pass it are unaffected.
        if disposition_out is not None:
            disposition_out["outcome"] = "pre_submission_rejected"

        # ── Race-condition guard: block duplicate entries within same scan cycle ──
        with _pending_lock:
            if signal.symbol in _pending_symbols:
                logger.warning(
                    f"[LOCK] {signal.symbol} already pending execution — "
                    f"dropping duplicate signal ({signal.direction})"
                )
                return None
            _pending_symbols.add(signal.symbol)

        try:
            return self._execute_signal_inner(signal, disposition_out=disposition_out)
        finally:
            with _pending_lock:
                _pending_symbols.discard(signal.symbol)

    def _execute_signal_inner(self, signal, disposition_out: Optional[dict] = None) -> Optional[str]:
        logger.info(
            f"Attempting to execute signal: {signal.symbol} {signal.direction}"
        )

        # ── Unresolved-order symbol block ───────────────────────────────────
        # A prior Kraken order for this symbol had a final fill state that
        # could not be confirmed (see _handle_unresolved_kraken_order). That
        # marker persists in the DB independently of the global trading halt
        # so this specific symbol stays blocked even if the halt is later
        # cleared without this symbol actually being reconciled.
        if signal.asset_class == "crypto":
            _unresolved = self._db.get_state(f"kraken_unresolved_symbol_{signal.symbol}")
            if _unresolved:
                logger.critical(
                    f"[KRAKEN UNRESOLVED BLOCK] {signal.symbol}: entries "
                    f"blocked — order {_unresolved.get('order_id')} requires "
                    f"manual reconciliation before new positions can open here"
                )
                return None

        if signal.asset_class == "stock":
            try:
                _ibkr_reconciliation = self._db.get_state(
                    f"ibkr_reconciliation_symbol_{signal.symbol}"
                )
            except Exception as exc:
                logger.error(
                    f"[IBKR RECONCILIATION BLOCK] {signal.symbol}: could not "
                    f"verify reconciliation state ({exc}); rejecting entry"
                )
                return None
            if _ibkr_reconciliation:
                logger.critical(
                    f"[IBKR RECONCILIATION BLOCK] {signal.symbol}: new entries "
                    "remain blocked until the persisted incident is explicitly "
                    "reconciled and cleared"
                )
                return None

        if signal.asset_class == "stock" and not _stock_entries_allowed_now():
            logger.info(
                f"Trade rejected for {signal.symbol}: stock entries closed "
                f"after 15:45 ET EOD cutoff"
            )
            return None

        # Resolve once before any broker-specific eligibility checks. This
        # exact name is carried through risk approval and submission unless
        # orchestration explicitly begins a separately approved fallback.
        broker_name_hint = self._select_entry_broker(signal)
        if broker_name_hint is None:
            logger.info(
                f"Trade rejected for {signal.symbol}: no enabled broker "
                "is eligible for new entries"
            )
            return None

        if not self._entry_preconditions_pass(signal, broker_name_hint):
            return None

        custom_sl  = signal.indicators.get("custom_stop_loss_pct")
        custom_tp  = signal.indicators.get("custom_take_profit_pct")
        custom_pos = signal.indicators.get("custom_position_pct")
        bypass_win_cooldown = bool(signal.indicators.get("bypass_win_cooldown", False))

        # Resolve the broker once for this approval/submission attempt. The
        # selected name is immutable until orchestration explicitly starts a
        # new fallback attempt with a fresh approval.
        structural_stop_hint  = signal.indicators.get("structural_stop_price")
        approval = self._approve_for_broker(
            signal, broker_name_hint, custom_sl, custom_tp, custom_pos,
            structural_stop_hint, bypass_win_cooldown,
        )
        if not approval.approved:
            # A broker-specific IBKR cash failure may start a separate Alpaca
            # attempt. General risk rejections must never be bypassed by
            # switching brokers.
            if (broker_name_hint == "ibkr" and
                    self._approval_allows_alpaca_fallback(approval)):
                logger.warning(
                    f"IBKR cannot fund {signal.symbol} — starting a new "
                    "Alpaca approval attempt"
                )
                broker_name_hint = "alpaca"
                if not self._entry_enabled("alpaca"):
                    logger.info(
                        f"Trade rejected for {signal.symbol}: Alpaca new "
                        "entries are disabled"
                    )
                    return None
                if not self._entry_preconditions_pass(signal, "alpaca"):
                    return None
                approval = self._approve_for_broker(
                    signal, broker_name_hint, custom_sl, custom_tp, custom_pos,
                    structural_stop_hint, bypass_win_cooldown,
                )
                if not approval.approved:
                    logger.info(
                        f"Trade rejected for {signal.symbol} (Alpaca fallback): "
                        f"{approval.reason}"
                    )
                    return None
            else:
                logger.info(f"Trade rejected for {signal.symbol}: {approval.reason}")
                return None

        # Settlement tracker only applies to IBKR cash account trades.
        # Alpaca paper has margin buying power — no settlement restriction needed.
        if (signal.asset_class == "stock" and
                broker_name_hint == "ibkr" and
                settlement_tracker is not None and
                getattr(config, "CASH_ACCOUNT_MODE", True) and
                self._ibkr is not None):
            allowed, reason, available = settlement_tracker.can_open_trade(
                approval.position_value
            )
            if not allowed:
                logger.info(
                    f"Trade blocked by settlement tracker: {signal.symbol} — {reason}"
                )
                return None

        trade_id     = str(uuid.uuid4())[:12]
        # From here on, exposure may exist even if this function later
        # returns None — never let disposition_out fall back to
        # "pre_submission_rejected" without an explicit, proven reason.
        if disposition_out is not None:
            disposition_out["outcome"] = "submission_unknown"
        broker_result = self._submit(signal, approval, broker_name_hint)

        # _submit() never changes brokers. Only an explicit, proven
        # no-exposure IBKR result may start a new Alpaca attempt, including a
        # completely fresh Alpaca risk approval.
        if (broker_name_hint == "ibkr" and
                self._ibkr_result_allows_alpaca_fallback(broker_result)):
            # IBKR's result already proved no exposure was created there —
            # safe to narrow back until the Alpaca attempt reaches its own
            # _submit() call.
            if disposition_out is not None:
                disposition_out["outcome"] = "rejected_no_exposure"
            if not self._entry_enabled("alpaca"):
                logger.warning(
                    f"IBKR created no exposure for {signal.symbol}, but "
                    "Alpaca new entries are disabled"
                )
                return None

            if not self._entry_preconditions_pass(signal, "alpaca"):
                return None
            alpaca_approval = self._approve_for_broker(
                signal, "alpaca", custom_sl, custom_tp, custom_pos,
                structural_stop_hint, bypass_win_cooldown,
            )
            if not alpaca_approval.approved:
                logger.info(
                    f"Trade rejected for {signal.symbol} (Alpaca fallback): "
                    f"{alpaca_approval.reason}"
                )
                return None
            broker_name_hint = "alpaca"
            approval = alpaca_approval
            if disposition_out is not None:
                disposition_out["outcome"] = "submission_unknown"
            broker_result = self._submit(signal, approval, broker_name_hint)

        # IBKR has broker-specific result semantics. Classify it before the
        # generic ghost guard or normal trade sizing can guess at exposure.
        if broker_name_hint == "ibkr":
            ibkr_disposition = self._classify_ibkr_result(broker_result)
            if ibkr_disposition == "definitive_zero":
                logger.warning(
                    f"[IBKR NO EXPOSURE] {signal.symbol}: status="
                    f"{self._ibkr_status(broker_result)!r}; no DB trade created"
                )
                if disposition_out is not None:
                    disposition_out["outcome"] = "rejected_no_exposure"
                return None
            if ibkr_disposition in (
                "reconcile_zero", "reconcile_partial", "reconcile_invalid",
            ):
                # Not provably zero exposure — reconcile_partial/invalid may
                # have created a live position; reconcile_zero is merely
                # unconfirmed, not proven zero. Stays submission_unknown.
                self._handle_ibkr_reconciliation_required(
                    signal, approval, broker_result,
                    has_confirmed_exposure=(ibkr_disposition == "reconcile_partial"),
                )
                return None

        if not broker_result:
            # A generic None/falsy broker_result is NOT proof of no exposure —
            # the request may have reached the broker and the response was
            # simply lost (network error, timeout, etc). Stays
            # submission_unknown so replay/reconciliation logic, not this
            # return value, is what future callers rely on.
            logger.error(
                f"Order submission failed for {signal.symbol} — outcome "
                "unknown, exposure cannot be ruled out"
            )
            return None
        # Ghost trade guard: block definitively-rejected orders from creating DB records.
        # Alpaca returns status=pending_new or accepted with filled_qty=0 — these are
        # valid in-flight orders that WILL fill. Only block hard failure statuses.
        # IBKR rejected orders return filled_qty=0 with status=cancelled/rejected.
        _status = str(broker_result.get("status", "")).lower()
        _HARD_FAIL_STATUSES = {"rejected", "cancelled", "expired", "done_for_day"}
        if _status in _HARD_FAIL_STATUSES:
            logger.warning(
                f"[GHOST GUARD] {signal.symbol}: order status='{_status}' — "
                f"definitively rejected, skipping DB record"
            )
            if disposition_out is not None:
                disposition_out["outcome"] = "rejected_no_exposure"
            return None

        # ── Live Kraken fill confirmation ──────────────────────────────────
        # _submit()'s crypto branch scales the submitted qty down for
        # leveraged shorts (see KRAKEN_SHORT_LEVERAGE scaling below) — the
        # only trustworthy record of what was actually bought/sold is
        # broker_result["filled_qty"] as reported by Kraken itself.
        # Scoped to live Kraken only: paper fills and Alpaca/IBKR pending
        # orders have their own separate (unmodified) handling.
        _is_live_kraken = (
            signal.asset_class == "crypto"
            and broker_name_hint == "kraken"
            and not getattr(config, "KRAKEN_PAPER_MODE", False)
        )
        if _is_live_kraken and broker_result.get("resolution_failed"):
            # KrakenExecutor already wrote a durable JSONL record and logged
            # CRITICAL — but that log/file is supplementary evidence, not a
            # system-level response. The true final state is unknown (could
            # be zero, could be a live, possibly-unprotected position) and
            # must not be guessed at: persist DB state, protect any confirmed
            # minimum exposure, and halt everything until a human reconciles.
            self._handle_unresolved_kraken_order(signal, approval, broker_result)
            return None
        if _is_live_kraken and float(broker_result.get("filled_qty") or 0) <= 0:
            logger.warning(
                f"[KRAKEN GHOST GUARD] {signal.symbol}: order confirmed with "
                f"filled_qty=0 (status={broker_result.get('status')!r}) — no "
                f"position opened, skipping DB record"
            )
            if disposition_out is not None:
                disposition_out["outcome"] = "rejected_no_exposure"
            return None

        entry_price = broker_result.get("filled_avg_price") or signal.current_price
        if entry_price == 0:
            entry_price = signal.current_price

        _is_confirmed_ibkr_fill = (
            broker_name_hint == "ibkr"
            and self._classify_ibkr_result(broker_result) == "confirmed_full"
        )

        if _is_live_kraken or _is_confirmed_ibkr_fill:
            # Live Kraken: broker_result["filled_qty"] is the confirmed
            # base-asset amount actually bought/sold — this is what was
            # really sent to Kraken (post leverage-scaling for shorts, see
            # _submit()), not the pre-scaling approval.quantity/position_value.
            # Trusting the reconstructed position_value/entry_price formula
            # here would silently record the full unscaled size for a
            # leveraged short even though only a fraction was really opened.
            actual_quantity = round(float(broker_result.get("filled_qty", 0)), 8)
        elif entry_price > 0 and approval.position_value > 0:
            # Recalculate quantity from actual fill price.
            # approval.quantity was sized using signal.current_price which can be stale
            # or from a bad feed (e.g. $0.05 instead of $42.79). Using the real fill
            # price ensures quantity × fill_price == position_value and prevents
            # phantom PNL on close (e.g. 39,952 qty × $1.14 = $45k on a $2k position).
            actual_quantity = round(approval.position_value / entry_price, 6)
        else:
            actual_quantity = approval.quantity

        # Position dollar value must reflect what was actually committed, not
        # the pre-scaling approved amount — otherwise a leveraged short's
        # capital-ledger bookkeeping and DB record overstate the real
        # position by the same factor the quantity was scaled down.
        open_position_value = (
            round(actual_quantity * entry_price, 4)
            if (_is_live_kraken or _is_confirmed_ibkr_fill)
            else approval.position_value
        )

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
                    _wrong_side = (
                        (signal.direction == "long"  and _new_stop >= entry_price) or
                        (signal.direction == "short" and _new_stop <= entry_price)
                    )
                    # Also reject stops that are technically on the correct side
                    # but unreasonably far (> 3× the expected percent stop distance).
                    # These indicate a bad candle tail or data glitch and would result
                    # in a bracket order with a 50-98% stop that never fires.
                    _max_stop_dist = entry_price * config.DEFAULT_STOP_LOSS_PCT / 100 * 3
                    _too_far = abs(entry_price - _new_stop) > _max_stop_dist
                    if _wrong_side or _too_far:
                        _reason = (
                            "wrong side of fill"
                            if _wrong_side
                            else f"distance {abs(entry_price - _new_stop) / entry_price * 100:.1f}% > 3× expected"
                        )
                        logger.warning(
                            f"[STOP REFRESH] {signal.symbol}: fresh structural stop "
                            f"${_new_stop:.6f} rejected ({_reason}) vs fill "
                            f"${entry_price:.6f} ({signal.direction}) — "
                            f"falling back to percent-based stop"
                        )
                        structural_stop = None   # force percent fallback below
                    else:
                        logger.info(
                            f"[STOP REFRESH] {signal.symbol}: structural stop "
                            f"recomputed at fill — "
                            f"${structural_stop:.6f} → ${_new_stop:.6f}"
                        )
                        structural_stop = _new_stop
            except Exception as _sr_err:
                logger.warning(
                    f"[STOP REFRESH] {signal.symbol}: could not recompute "
                    f"structural stop at fill: {_sr_err}"
                )

        # ── Stop-loss selection with minimum-distance guard ──────────────────
        # Structural stop wins over percent-based stop UNLESS it would result in
        # a tighter stop than the strategy's own declared stop_loss_pct.
        # Scenario: DCA accumulator enters at a local bottom; the prior 2 bars
        # are also at lows, so initial_stop_from_tail() places the stop almost
        # at entry price (< 0.3%), overriding DCA's 2% fallback and causing an
        # immediate stop-out on any noise.  The guard enforces the declared %
        # as a hard floor — structural stops must be at least that far away.
        strategy_sl_pct = (custom_sl or config.DEFAULT_STOP_LOSS_PCT) / 100
        if structural_stop is not None:
            if signal.direction == "long":
                min_stop = entry_price * (1 - strategy_sl_pct)
                if structural_stop > min_stop:
                    logger.info(
                        f"[STOP GUARD] {signal.symbol}: structural ${structural_stop:.6f} "
                        f"tighter than declared {strategy_sl_pct*100:.2f}% floor "
                        f"(${min_stop:.6f}) — using percent floor"
                    )
                    stop_loss = min_stop
                else:
                    stop_loss = structural_stop
            else:  # short
                min_stop = entry_price * (1 + strategy_sl_pct)
                if structural_stop < min_stop:
                    logger.info(
                        f"[STOP GUARD] {signal.symbol}: structural ${structural_stop:.6f} "
                        f"tighter than declared {strategy_sl_pct*100:.2f}% floor "
                        f"(${min_stop:.6f}) — using percent floor"
                    )
                    stop_loss = min_stop
                else:
                    stop_loss = structural_stop
        else:
            stop_loss = (entry_price * (1 - strategy_sl_pct) if signal.direction == "long"
                         else entry_price * (1 + strategy_sl_pct))

        # Use the broker that actually filled the order (tagged in _submit).
        # Paper fills have no tag, so retain the immutable broker selected and
        # approved for this attempt; never re-run routing after submission.
        broker_name = broker_result.get("actual_broker") or broker_name_hint

        # Leverage actually used for this fill (0 = spot). Persisted so any
        # later stop replacement (position_monitor.py ratchet/restore) or
        # provisional emergency stop preserves the same close semantics —
        # leverage/reduceOnly can't be safely re-derived after the fact,
        # since exchange_capabilities' leverage limits can change over time.
        _kraken_leverage = int(broker_result.get("leverage") or 0) if signal.asset_class == "crypto" else 0

        trade_record = {
            "trade_id":        trade_id,
            "symbol":          signal.symbol,
            "asset_class":     signal.asset_class,
            "direction":       signal.direction,
            "entry_time":      datetime.now().isoformat(),
            "entry_price":     round(entry_price, 6),
            "quantity":        actual_quantity,
            "strategy_name":   signal.indicators.get("strategy_name", "original"),
            "entry_timeframe": signal.indicators.get(
                "timeframe",
                "5Min" if signal.asset_class == "stock" else "5m"
            ),
            "position_value":  open_position_value,
            "stop_loss":       round(stop_loss, 6),
            "take_profit":     round(take_profit, 6),
            "signal_score":    signal.score,
            "indicators": (
                {**signal.indicators, "kraken_leverage": _kraken_leverage}
                if signal.asset_class == "crypto" else signal.indicators
            ),
            "broker":          broker_name,
            "broker_order_id": broker_result.get("broker_order_id"),
            "event_id":        signal.indicators.get("event_id"),
        }
        open_result = self._db.open_trade(trade_record)
        if isinstance(open_result, dict):
            open_status = open_result.get("status")
            if open_status == "conflict":
                # The broker order filled — exposure exists — but this
                # process could not durably claim the trade row. Exposure is
                # real and confirmed here even though this call returns None.
                if disposition_out is not None:
                    disposition_out["outcome"] = "accepted"
                self._handle_trade_identity_conflict(
                    signal, broker_result, trade_record, open_result, _kraken_leverage
                )
                return None
            if open_status in ("idempotent", "existing_processed"):
                logger.warning(
                    "Trade persistence replay for %s (%s): %s; skipping "
                    "duplicate alerts, balance changes, and stop placement",
                    signal.symbol, trade_id, open_status,
                )
                if disposition_out is not None:
                    disposition_out["outcome"] = "accepted"
                return trade_id

        try:
            alert_manager.trade_opened({
                "symbol": signal.symbol, "direction": signal.direction,
                "entry_price": entry_price, "stop_loss": stop_loss,
                "take_profit": take_profit, "position_value": open_position_value,
                "strategy_name": signal.indicators.get("strategy_name", "unknown")
            })
        except Exception:
            pass

        logger.info(
            f"[TRADE OPEN] {signal.symbol} {signal.direction.upper()} | "
            f"Entry: ${entry_price:.4f} | Qty: {actual_quantity:.4f} | "
            f"SL: ${stop_loss:.4f} | TP: ${take_profit:.4f} | "
            f"Broker: {broker_name} | ID: {trade_id}"
        )

        # ── Update broker available cash (deduct position value) ──────────
        try:
            bal = self._broker_manager.get_broker_balance(broker_name)
            if not isinstance(bal, dict):
                logger.debug(f"Broker balance update on open skipped: get_broker_balance returned {type(bal).__name__} for {broker_name}")
            else:
                new_invested  = bal.get("invested",  0.0) + open_position_value
                new_available = max(0.0, bal.get("available", 0.0) - open_position_value)
                self._broker_manager.update_broker_balance(
                    broker_name, bal.get("balance", 0.0),
                    new_invested, new_available
                )
        except Exception as _bm_err:
            logger.debug(f"Broker balance update on open failed: {_bm_err}")

        # ── Place real stop order on Kraken (live + paper) ────────────────
        # In paper mode this stores a fake order ID for tracking logic parity.
        # In live mode this places an actual stop order on Kraken, preserving
        # the same leverage/reduceOnly close semantics the entry used.
        if signal.asset_class == "crypto" and broker_name in ("kraken", "paper"):
            stop_side = "buy" if signal.direction == "short" else "sell"
            stop_order_id = self.kraken.place_stop_order(
                signal.symbol, actual_quantity, stop_side, round(stop_loss, 6),
                leverage=_kraken_leverage,
            )
            if stop_order_id:
                self._db.update_trade_order_ids(trade_id, stop_order_id=stop_order_id)
                logger.info(
                    f"[{'PAPER' if config.KRAKEN_PAPER_MODE else 'LIVE'}] "
                    f"Stop order placed for {signal.symbol} @ ${stop_loss:.4f} "
                    f"| order_id={stop_order_id}"
                )

        if disposition_out is not None:
            disposition_out["outcome"] = "accepted"
        return trade_id

    def reconcile_unresolved_breakout_events(self) -> Dict[str, int]:
        """
        Startup/replay reconciliation for requirement #10: for every
        breakout_event_execution row still SUBMITTING or SUBMISSION_UNKNOWN
        (crash or timeout happened after we may have contacted a broker),
        query each broker by the deterministic client identity instead of
        ever resubmitting. A found order proves exposure and moves the event
        to ACCEPTED; a miss leaves it exactly as-is — still blocked/unknown.

        Does NOT reconstruct a full trades row from a bare broker order (that
        would require re-deriving stop/TP/position-sizing blind, which is a
        separate and riskier problem). If a matching broker order is found
        with no corresponding trades.event_id row, this logs CRITICAL and
        records broker_order_id on the event so a human can reconcile the
        trades table — this is the flagged residual gap, not a silent one.

        Returns counts: {"checked", "confirmed_accepted", "still_unresolved"}.
        """
        events = self._db.get_unresolved_breakout_events()
        counts = {"checked": 0, "confirmed_accepted": 0, "still_unresolved": 0}

        for ev in events:
            counts["checked"] += 1
            event_id         = ev["event_id"]
            client_order_id  = ev["client_order_id"]
            symbol           = ev["symbol"]
            found = None
            found_broker = None

            if self.alpaca is not None:
                try:
                    order = self.alpaca.api.get_order_by_client_order_id(client_order_id)
                    if order is not None:
                        found = {
                            "broker_order_id":  order.id,
                            "status":           order.status,
                            "filled_qty":       float(order.filled_qty or 0),
                            "filled_avg_price": float(order.filled_avg_price or 0),
                        }
                        found_broker = "alpaca"
                except Exception as e:
                    logger.debug(f"[RECONCILE] {event_id}: alpaca lookup miss/error: {e}")

            if found is None and self._ibkr is not None:
                try:
                    found = self._ibkr.find_order_by_ref(client_order_id)
                    if found is not None:
                        found_broker = "ibkr"
                except Exception as e:
                    logger.debug(f"[RECONCILE] {event_id}: ibkr lookup miss/error: {e}")

            if found is None:
                try:
                    userref = derive_kraken_userref(event_id)
                    found = self.kraken.find_order_by_userref(userref, symbol=symbol)
                    if found is not None:
                        found_broker = "kraken"
                except Exception as e:
                    logger.debug(f"[RECONCILE] {event_id}: kraken lookup miss/error: {e}")

            if found is None:
                logger.warning(
                    f"[RECONCILE] {event_id} ({symbol}) still unresolved after "
                    f"broker lookup across alpaca/ibkr/kraken — leaving "
                    f"{ev['state']}, will not resubmit"
                )
                counts["still_unresolved"] += 1
                continue

            existing_trade = None
            try:
                existing_trade = self._db.get_trade(ev.get("trade_id")) if ev.get("trade_id") else None
            except Exception:
                existing_trade = None

            if existing_trade is None:
                logger.critical(
                    f"[RECONCILE] {event_id} ({symbol}): confirmed {found_broker} "
                    f"order {found.get('broker_order_id')} (status="
                    f"{found.get('status')}) with NO matching trades row — "
                    "exposure exists but is not represented in the trades "
                    "table. Manual reconciliation required."
                )

            self._db.finish_breakout_event(
                event_id, "ACCEPTED",
                broker_order_id=found.get("broker_order_id"),
                last_error=(
                    None if existing_trade is not None else
                    f"Reconciled to {found_broker} order with no trades row — "
                    "manual reconciliation required"
                ),
            )
            counts["confirmed_accepted"] += 1

        logger.info(f"[RECONCILE] breakout event reconciliation complete: {counts}")
        return counts

    def _handle_trade_identity_conflict(self, signal, broker_result: Dict,
                                        trade_record: Dict, result: Dict,
                                        kraken_leverage: int = 0) -> None:
        """Fail closed when a filled broker order cannot claim its DB identity."""
        order_id = broker_result.get("broker_order_id")
        marker = {
            "symbol": signal.symbol,
            "trade_id": trade_record["trade_id"],
            "broker_order_id": order_id,
            "broker": trade_record.get("broker"),
            "filled_qty": broker_result.get("filled_qty"),
            "filled_avg_price": broker_result.get("filled_avg_price"),
            "conflicting_fields": result.get("conflicting_fields", []),
            "timestamp": datetime.now().isoformat(),
            "reconciliation_required": True,
            "reason": "trade_identity_conflict",
        }
        key = f"trade_identity_conflict_{trade_record['trade_id']}"
        try:
            self._db.set_state(key, marker)
        except Exception as exc:
            logger.critical("Failed to persist %s: %s", key, exc)

        if (signal.asset_class == "crypto" and
                trade_record.get("broker") == "kraken" and
                float(broker_result.get("filled_qty") or 0) > 0):
            stop_side = "buy" if signal.direction == "short" else "sell"
            try:
                self.kraken.place_stop_order(
                    signal.symbol, float(broker_result["filled_qty"]), stop_side,
                    trade_record["stop_loss"], leverage=kraken_leverage,
                )
            except Exception as exc:
                logger.critical("Emergency stop failed after identity conflict: %s", exc)

        reason = (
            f"Trade identity conflict for {signal.symbol}, trade_id="
            f"{trade_record['trade_id']}, broker_order_id={order_id}; "
            "manual reconciliation required"
        )
        logger.critical(reason)
        self._risk_manager.manual_halt(reason)

    def _persist_unresolved_markers(self, symbol: str, order_id: Optional[str],
                                    marker: Dict) -> None:
        """
        Persist both the symbol-keyed and order-ID-keyed unresolved markers.

        The symbol-keyed marker is the safety-critical one — it is what
        blocks new entries for this symbol independently of the global halt
        (see the guard at the top of _execute_signal_inner), so if a later
        manual_resume() clears the halt without this specific order being
        reconciled, this symbol must still stay blocked. It is therefore
        always written FIRST, and each key's write is attempted
        independently — one failing must never suppress the other.

        Prefers a single DB transaction, reusing the exact same private
        _conn() primitive data/database.py's own set_state() is built on, so
        a mid-write failure can never leave one marker committed and the
        other silently missing (true atomicity: both keys commit together or
        neither does). Falls back to two fully independent set_state() calls
        — symbol first — when the injected db_ref doesn't expose a
        transaction primitive (e.g. a test double) or the atomic attempt
        itself raises.
        """
        symbol_key = f"kraken_unresolved_symbol_{symbol}"
        order_key  = f"kraken_unresolved_order_{order_id}"

        if hasattr(self._db, "_conn"):
            try:
                with self._db._conn() as conn:
                    _now = datetime.now().isoformat()
                    conn.execute(
                        "INSERT OR REPLACE INTO bot_state (key, value, updated) "
                        "VALUES (?, ?, ?)",
                        (symbol_key, json.dumps(marker), _now),
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO bot_state (key, value, updated) "
                        "VALUES (?, ?, ?)",
                        (order_key, json.dumps(marker), _now),
                    )
                return
            except Exception as _atomic_err:
                logger.critical(
                    f"[KRAKEN UNRESOLVED] {symbol}: atomic marker transaction "
                    f"failed ({_atomic_err}) — falling back to independent "
                    f"per-key writes, symbol marker first"
                )

        try:
            self._db.set_state(symbol_key, marker)
        except Exception as _sym_err:
            logger.critical(
                f"[KRAKEN UNRESOLVED] {symbol}: FAILED to persist the SYMBOL "
                f"reconciliation marker: {_sym_err} — this symbol may NOT "
                f"stay blocked if the global halt is later cleared, treat as "
                f"highest-priority manual intervention"
            )
        try:
            self._db.set_state(order_key, marker)
        except Exception as _ord_err:
            logger.critical(
                f"[KRAKEN UNRESOLVED] {symbol}: FAILED to persist the "
                f"order-ID reconciliation marker ({order_id}): {_ord_err}"
            )

    def _handle_unresolved_kraken_order(
        self, signal, approval: TradeApproval, broker_result: Dict
    ) -> None:
        """
        Fail-closed handling for a Kraken order whose final fill state
        KrakenExecutor could not confirm (resolution_failed=True). The true
        outcome is unknown — it could be a clean zero-fill, or a live,
        possibly-unprotected position at Kraken. Never guessed at:

          0. Idempotency: if this exact order ID has already been handled,
             do not create a second provisional trade or a second emergency
             stop for the same confirmed exposure — just re-assert the halt.
          1. Persist a durable DB bot_state marker, keyed both by the Kraken
             order ID and by symbol (see _persist_unresolved_markers) — this
             DB record is the system's actual state store; the
             KrakenExecutor JSONL log is supplementary evidence only, not
             something anything else consumes.
          2. If a positive confirmed-minimum quantity is known, open a
             clearly marked provisional DB trade and place an emergency stop
             — preserving the same leverage/reduceOnly close semantics as a
             normal entry stop — for exactly that confirmed quantity. Never
             more, and never guessing at any unconfirmed remainder.
          3. Invoke the public global risk halt (which also fires the
             existing critical trading-halted alert) so every strategy,
             including BMR-357, rejects new entries until a human
             reconciles this order.

        Each step is independently best-effort (wrapped so a failure in one
        cannot suppress the others) — manual_halt() is always attempted last,
        regardless of whether the marker/provisional-trade steps succeeded.
        """
        order_id       = broker_result.get("broker_order_id")
        last_known_qty = float(broker_result.get("filled_qty") or 0)
        last_known_px  = float(broker_result.get("filled_avg_price") or 0)
        leverage       = int(broker_result.get("leverage") or 0)
        status         = broker_result.get("status")
        symbol         = signal.symbol
        now_iso        = datetime.now().isoformat()

        order_key = f"kraken_unresolved_order_{order_id}"
        try:
            already_handled = self._db.get_state(order_key)
        except Exception:
            already_handled = None
        if already_handled:
            logger.critical(
                f"[KRAKEN UNRESOLVED] {symbol}: order {order_id} already has "
                f"an unresolved marker — skipping duplicate provisional "
                f"trade/stop (idempotent no-op); re-asserting halt in case "
                f"it was cleared without this order being reconciled"
            )
            self._risk_manager.manual_halt(
                f"Kraken order unresolved for {symbol} (order_id={order_id}): "
                f"manual reconciliation required before trading can resume "
                f"(duplicate resolution attempt detected)."
            )
            return

        marker = {
            "symbol":                  symbol,
            "side":                    "sell" if signal.direction == "short" else "buy",
            "requested_qty":           approval.quantity,
            "last_known_filled_qty":   last_known_qty,
            "last_known_avg_price":    last_known_px,
            "leverage":                leverage,
            "status":                  status,
            "timestamp":               now_iso,
            "reconciliation_required": True,
            "order_id":                order_id,
        }
        self._persist_unresolved_markers(symbol, order_id, marker)

        halt_reason = (
            f"Kraken order unresolved for {symbol} (order_id={order_id}): "
            f"final fill state could not be confirmed after cancel + "
            f"follow-up fetch. Manual reconciliation required before "
            f"trading can resume."
        )

        if last_known_qty > 0:
            # A confirmed minimum position exists. It must be tracked and
            # protected — not silently discarded just because the rest of
            # the order's outcome is unknown.
            try:
                entry_price = last_known_px or signal.current_price
                strategy_sl_pct = (
                    signal.indicators.get("custom_stop_loss_pct")
                    or config.DEFAULT_STOP_LOSS_PCT
                ) / 100
                strategy_tp_pct = (
                    signal.indicators.get("custom_take_profit_pct")
                    or config.DEFAULT_TAKE_PROFIT_PCT
                ) / 100
                if signal.direction == "long":
                    stop_loss   = entry_price * (1 - strategy_sl_pct)
                    take_profit = entry_price * (1 + strategy_tp_pct)
                else:
                    stop_loss   = entry_price * (1 + strategy_sl_pct)
                    take_profit = entry_price * (1 - strategy_tp_pct)

                provisional_trade_id = f"UNRESOLVED-{str(uuid.uuid4())[:8]}"
                provisional_record = {
                    "trade_id":        provisional_trade_id,
                    "symbol":          symbol,
                    "asset_class":     "crypto",
                    "direction":       signal.direction,
                    "entry_time":      now_iso,
                    "entry_price":     round(entry_price, 6),
                    "quantity":        last_known_qty,
                    "strategy_name":   signal.indicators.get("strategy_name", "original"),
                    "entry_timeframe": signal.indicators.get("timeframe", "5m"),
                    "position_value":  round(last_known_qty * entry_price, 4),
                    "stop_loss":       round(stop_loss, 6),
                    "take_profit":     round(take_profit, 6),
                    "signal_score":    signal.score,
                    "indicators": {
                        **signal.indicators,
                        "kraken_provisional_unresolved": True,
                        "kraken_unresolved_order_id":    order_id,
                        "kraken_leverage":                leverage,
                    },
                    "broker":          "kraken",
                    "broker_order_id": order_id,
                }
                self._db.open_trade(provisional_record)
                logger.critical(
                    f"[KRAKEN UNRESOLVED] {symbol}: provisional trade "
                    f"{provisional_trade_id} opened for confirmed minimum "
                    f"{last_known_qty} @ ${entry_price:.6f} — treat as "
                    f"requiring reconciliation, not a normal position"
                )

                # Emergency stop MUST preserve the same leverage/reduceOnly
                # close semantics as a normal entry stop for this position —
                # a returned order ID alone does not prove the stop actually
                # protects a leveraged short (see place_stop_order()).
                stop_side = "buy" if signal.direction == "short" else "sell"
                try:
                    stop_order_id = self.kraken.place_stop_order(
                        symbol, last_known_qty, stop_side, round(stop_loss, 6),
                        leverage=leverage,
                    )
                except Exception as _stop_err:
                    stop_order_id = None
                    logger.critical(
                        f"[KRAKEN UNRESOLVED] {symbol}: emergency stop "
                        f"placement raised: {_stop_err}"
                    )
                if stop_order_id:
                    self._db.update_trade_order_ids(
                        provisional_trade_id, stop_order_id=stop_order_id
                    )
                else:
                    logger.critical(
                        f"[KRAKEN UNRESOLVED] {symbol}: emergency stop "
                        f"placement FAILED for provisional trade "
                        f"{provisional_trade_id} — confirmed {last_known_qty} "
                        f"is UNPROTECTED, treat as highest-priority "
                        f"manual reconciliation"
                    )

                halt_reason += (
                    f" A provisional trade ({provisional_trade_id}) was "
                    f"opened for the confirmed minimum {last_known_qty} units."
                )
            except Exception as _prov_err:
                logger.critical(
                    f"[KRAKEN UNRESOLVED] {symbol}: FAILED to create "
                    f"provisional protective trade: {_prov_err} — confirmed "
                    f"{last_known_qty} may be completely untracked and "
                    f"unprotected, treat as highest-priority reconciliation"
                )

        self._risk_manager.manual_halt(halt_reason)

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
                # If IBKR close failed, ALWAYS try Alpaca too before giving up.
                # Do NOT short-circuit with success=True just because IBKR
                # doesn't list the position — it may have been opened via the
                # Alpaca fallback path even though DB records broker=ibkr.
                if not success:
                    logger.warning(
                        f"[IBKR CLOSE FAILED] {symbol}: trying Alpaca as well "
                        f"(position may exist on either broker)"
                    )
                    alpaca_success = (
                        self.alpaca.close_position(symbol)
                        if self.alpaca is not None else False
                    )
                    if alpaca_success:
                        logger.info(f"[ALPACA FALLBACK CLOSE] {symbol}: closed via Alpaca")
                        # Correct the DB broker field so future lookups are accurate
                        trade_id = trade.get("trade_id")
                        if trade_id:
                            try:
                                self._db.update_trade_broker(trade_id, "alpaca")
                            except Exception:
                                pass
                        success = True
                    else:
                        logger.warning(f"[ALPACA FALLBACK CLOSE] {symbol}: not found on Alpaca either")
                        # Both brokers checked — do NOT mark success here.
                        # IBKR may be temporarily down; leave trade open in DB
                        # so EOD Pass 3 (IBKR sweep) can retry when it comes back.
                        success = False
                        logger.warning(
                            f"[CLOSE SKIP] {symbol}: not found on IBKR or Alpaca "
                            f"— leaving open in DB for EOD sweep retry"
                        )
            else:
                if self.alpaca is None:
                    logger.warning(
                        f"[ALPACA CLOSE SKIP] {symbol}: Alpaca credentials are not configured"
                    )
                    success = False
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
                        # Correct the DB broker field
                        trade_id = trade.get("trade_id")
                        if trade_id:
                            try:
                                self._db.update_trade_broker(trade_id, "ibkr")
                            except Exception:
                                pass
                        success = True
        elif asset_class == "crypto":
            # Kraken is the default crypto executor — Coinbase API is deprecated.
            side = "buy" if direction == "long" else "sell"
            if config.KRAKEN_ENABLED:
                # ── Re-derive leverage to match the entry order ───────────────
                # Short entries are placed as margin orders at KRAKEN_SHORT_LEVERAGE.
                # The close must send the same leverage so Kraken reduces the margin
                # position rather than opening a new opposing spot position.
                # Longs are entered as spot (leverage=0), so close is also spot.
                close_leverage = 0
                if direction == "short":
                    desired_lev = getattr(config, "KRAKEN_SHORT_LEVERAGE", 2)
                    max_lev     = exchange_capabilities.get_max_short_leverage(
                        symbol, "kraken"
                    )
                    close_leverage = min(desired_lev, max_lev) if max_lev > 1 else 0

                # close_position now: (1) cancels ALL open orders for symbol first,
                # (2) sends a margin-aware market close.  The separate stop_order_id
                # cancel below is therefore redundant but left as a belt-and-braces
                # fallback for paper mode where cancel_all_orders_for_symbol is a no-op.
                success = self.kraken.close_position(symbol, qty, side,
                                                     leverage=close_leverage)
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

        # ── Brokerage fee simulation (matches backtester rates) ───────────
        if asset_class == "crypto":
            fee_rt_pct = (config.BT_COMMISSION_CRYPTO_PCT + config.BT_SLIPPAGE_CRYPTO_PCT) / 100 * 2
        else:
            fee_rt_pct = (config.BT_COMMISSION_STOCK_PCT + config.BT_SLIPPAGE_STOCK_PCT) / 100 * 2
        fees_paid = round(entry_price * qty * fee_rt_pct, 4)
        pnl       = pnl - fees_paid
        partial_pnl = float(trade.get("partial_pnl") or 0.0)
        partial_fees_paid = float(trade.get("partial_fees_paid") or 0.0)
        total_pnl = pnl + partial_pnl
        total_fees_paid = fees_paid + partial_fees_paid

        # ── PnL% — calculate directly from price move, not position_value ─
        # position_value in DB can drift; price-based calc is always correct.
        # pnl_pct = % move from entry to exit, always positive for wins.
        if entry_price and entry_price > 0:
            raw_move_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_pct      = raw_move_pct if direction == "long" else -raw_move_pct
        else:
            pnl_pct = (pnl / trade["position_value"]) * 100 if trade["position_value"] else 0

        # ── Sanity check: pnl_pct cap against bad price feeds ────────────────
        # Use a FIXED asset-class cap, not derived from stop_loss — the stop_loss
        # itself can be corrupted by the same bad feed, making a derived cap useless.
        # Stocks: 15% max (a genuine 15% stock move in one trade is already huge;
        #   this catches $85-for-$209 entry corruption like the NFLX case)
        # Crypto: 60% max (wider for volatile coins)
        # Fall-through: also honour 3× DEFAULT_STOP_LOSS_PCT as a floor so
        # legitimate wide-stop trades are never accidentally capped.
        _fixed_cap   = 15.0 if asset_class == "stock" else 60.0
        max_sane_pct = max(_fixed_cap, config.DEFAULT_STOP_LOSS_PCT * 3)
        if abs(pnl_pct) > max_sane_pct:
            logger.warning(
                f"[PNL SANITY] {symbol}: pnl_pct={pnl_pct:.2f}% exceeds cap "
                f"({max_sane_pct:.1f}%). Bad price feed suspected — "
                f"entry={entry_price} bad_exit={current_price} qty={qty} — CLOSE SKIPPED"
            )
            return  # ignore bad tick, position monitor will retry next cycle

        trade_won = total_pnl > 0

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
            pnl_pct    = round(pnl_pct, 4),
            fees_paid  = fees_paid,
        )

        full_trade = {
            **trade,
            "exit_time":  datetime.now().isoformat(),
            "exit_price": current_price,
            "fees_paid":  total_fees_paid,
            "pnl":        total_pnl,
            "status":     "closed"
        }
        self._db.record_tax_event(full_trade)
        self._risk_manager.record_trade_result(total_pnl, trade_won, symbol=symbol)

        strategy_name = trade.get("strategy_name", "original")
        if strategy_name not in ("original", "manual") and exit_reason != "manual_close":
            try:
                from strategies.strategy_engine import strategy_engine
                strategy_engine.record_trade_result(
                    strategy_name, total_pnl, trade_won, exit_reason=exit_reason
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
            new_invested = max(0, cap["invested_value"] - trade["position_value"])
            new_available = cap["available_cash"] + trade["position_value"] + pnl
            new_available = min(new_available, max(0.0, new_capital - new_invested))
            self._db.log_capital(
                total     = new_capital,
                available = new_available,
                invested  = new_invested,
                daily_pnl = cap["daily_pnl"] + pnl,
                total_pnl = cap["total_pnl"] + pnl,
                note      = (
                    f"Closed {symbol} @ {broker} {exit_reason}: "
                    f"{'+'if pnl>0 else ''}{pnl:.2f}"
                )
            )

        # ── Restore broker available cash (return position value + PnL) ────
        try:
            close_broker = trade.get("broker", broker)
            bal = self._broker_manager.get_broker_balance(close_broker)
            if not isinstance(bal, dict):
                logger.debug(f"Broker balance update on close skipped: get_broker_balance returned {type(bal).__name__} for {close_broker}")
            else:
                returned      = trade.get("position_value", 0.0) + pnl
                new_invested  = max(0.0, bal.get("invested",  0.0) - trade.get("position_value", 0.0))
                new_available = bal.get("available", 0.0) + returned
                new_balance   = bal.get("balance",  0.0) + pnl
                self._broker_manager.update_broker_balance(
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
            f"PnL: {'+'if total_pnl>0 else ''}{total_pnl:.4f} "
            f"({pnl_pct:+.2f}%)"
        )
        return True

    def _set_kraken_partial_reconcile_hold(
        self,
        trade: Dict,
        reason: str,
        requested_qty: float,
        broker_result: Optional[Dict] = None,
    ) -> None:
        """Persist a fail-closed hold for an ambiguous scanner partial."""
        trade_id = trade["trade_id"]
        symbol = trade["symbol"]
        result = broker_result if isinstance(broker_result, dict) else {}
        marker = {
            "required": True,
            "trade_id": trade_id,
            "symbol": symbol,
            "reason": reason,
            "requested_qty": float(requested_qty),
            "broker_order_id": result.get("broker_order_id"),
            "status": result.get("status"),
            "last_known_filled_qty": result.get("filled_qty"),
            "last_known_fill_price": result.get("filled_avg_price"),
            "cancellation": result.get("cancellation"),
            "timestamp": datetime.now().isoformat(),
        }
        state_key = f"kraken_partial_reconcile_{trade_id}"
        try:
            existing = self._db.get_state(state_key, default=0)
        except Exception:
            existing = 0
        if not existing:
            try:
                self._db.set_state(state_key, marker)
            except Exception as exc:
                logger.critical(
                    f"[KRAKEN PARTIAL HOLD] {symbol}: failed to persist "
                    f"{state_key} ({exc})"
                )
        logger.critical(
            f"[KRAKEN PARTIAL HOLD] {symbol}: {reason}; no further scanner "
            f"partial action is allowed until live Kraken reconciliation"
        )
        try:
            self._risk_manager.manual_halt(
                f"Kraken scanner partial unresolved for {symbol}: {reason}. "
                "Manual live-fill reconciliation required."
            )
        except Exception as exc:
            logger.critical(
                f"[KRAKEN PARTIAL HOLD] {symbol}: risk halt failed ({exc})"
            )

    def close_partial_trade(
        self, trade: Dict, current_price: float, fraction: float,
        exit_reason: str = "partial_take_profit"
    ) -> PartialCloseOutcome:
        """
        Close part of an open trade using only confirmed broker fill quantity.

        Live Kraken cancellation or fill ambiguity persists a reconciliation
        hold and performs no accounting. A terminal zero fill is retryable,
        while a confirmed partial is recorded for the exact filled quantity.
        """
        symbol      = trade["symbol"]
        direction   = trade["direction"]
        qty         = float(trade.get("quantity") or 0)
        entry_price = float(trade.get("entry_price") or 0)
        asset_class = trade.get("asset_class", "crypto")
        broker      = trade.get("broker", "alpaca")
        trade_id    = trade["trade_id"]

        fraction = max(0.0, min(float(fraction or 0), 0.95))
        close_qty = round(qty * fraction, 8)
        if close_qty <= 0 or qty <= 0 or entry_price <= 0:
            return PartialCloseOutcome(False, "invalid_partial_request")

        if asset_class != "crypto":
            logger.info(
                f"[PARTIAL SKIP] {symbol}: partial exits currently enabled "
                f"only for crypto scanner trades"
            )
            return PartialCloseOutcome(False, "unsupported_asset_class")

        side = "buy" if direction == "long" else "sell"
        if config.KRAKEN_ENABLED:
            try:
                close_leverage = int(
                    json.loads(trade.get("indicators_json") or "{}").get(
                        "kraken_leverage", 0
                    )
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                close_leverage = 0
            if direction == "short" and close_leverage <= 1:
                desired_lev = getattr(config, "KRAKEN_SHORT_LEVERAGE", 2)
                max_lev = exchange_capabilities.get_max_short_leverage(
                    symbol, "kraken"
                )
                close_leverage = min(desired_lev, max_lev) if max_lev > 1 else 0
            broker_result = self.kraken.close_partial_position(
                symbol, close_qty, side, leverage=close_leverage
            )
        else:
            close_side = "sell" if direction == "long" else "buy"
            logger.info(
                f"[PAPER] Simulated partial close: {symbol} "
                f"{close_side.upper()} {close_qty} @ ${current_price:.4f}"
            )
            broker_result = {
                "ok": True,
                "reason": "local_paper_fill",
                "broker_order_id": None,
                "status": "filled",
                "filled_qty": close_qty,
                "filled_avg_price": current_price,
                "resolution_failed": False,
                "cancellation": {
                    "matched": 0,
                    "cancelled": 0,
                    "ambiguous": False,
                    "errors": [],
                },
            }

        if not isinstance(broker_result, dict):
            self._set_kraken_partial_reconcile_hold(
                trade, "missing broker result", close_qty, None
            )
            return PartialCloseOutcome(
                False,
                "missing_broker_result",
                reconciliation_required=True,
            )

        cancellation = broker_result.get("cancellation")
        if not isinstance(cancellation, dict):
            cancellation = {}
        result_reason = str(broker_result.get("reason") or "unknown")
        if (
            cancellation.get("ambiguous")
            or broker_result.get("resolution_failed")
            or result_reason in {
                "cancellation_ambiguous",
                "submission_unknown",
                "fill_resolution_failed",
            }
        ):
            self._set_kraken_partial_reconcile_hold(
                trade, result_reason, close_qty, broker_result
            )
            return PartialCloseOutcome(
                False,
                result_reason,
                filled_qty=float(broker_result.get("filled_qty") or 0),
                fill_price=float(broker_result.get("filled_avg_price") or 0),
                reconciliation_required=True,
                broker_order_id=broker_result.get("broker_order_id"),
                cancellation=cancellation,
            )

        try:
            actual_close_qty = float(broker_result.get("filled_qty") or 0)
            broker_fill_price = float(
                broker_result.get("filled_avg_price") or 0
            )
        except (TypeError, ValueError):
            actual_close_qty = float("nan")
            broker_fill_price = float("nan")
        if not math.isfinite(actual_close_qty) or actual_close_qty < 0:
            self._set_kraken_partial_reconcile_hold(
                trade, "invalid confirmed fill quantity", close_qty, broker_result
            )
            return PartialCloseOutcome(
                False,
                "invalid_fill_quantity",
                reconciliation_required=True,
                cancellation=cancellation,
            )

        if actual_close_qty == 0:
            logger.warning(
                f"[PARTIAL ZERO FILL] {symbol}: terminal broker result "
                f"confirmed no fill; partial may retry after backoff"
            )
            return PartialCloseOutcome(
                False,
                "terminal_zero_fill",
                retryable=True,
                stop_refresh_required=True,
                broker_order_id=broker_result.get("broker_order_id"),
                cancellation=cancellation,
            )

        if (
            not math.isfinite(broker_fill_price)
            or broker_fill_price <= 0
        ):
            if getattr(self.kraken, "paper", False):
                broker_fill_price = float(current_price)
            else:
                self._set_kraken_partial_reconcile_hold(
                    trade,
                    "positive fill has no confirmed average price",
                    close_qty,
                    broker_result,
                )
                return PartialCloseOutcome(
                    False,
                    "invalid_fill_price",
                    filled_qty=actual_close_qty,
                    reconciliation_required=True,
                    broker_order_id=broker_result.get("broker_order_id"),
                    cancellation=cancellation,
                )

        qty_tolerance = max(1e-8, qty * 1e-8)
        if actual_close_qty > qty + qty_tolerance:
            self._set_kraken_partial_reconcile_hold(
                trade,
                "confirmed close fill exceeds tracked position quantity",
                close_qty,
                broker_result,
            )
            return PartialCloseOutcome(
                False,
                "confirmed_overfill",
                filled_qty=actual_close_qty,
                fill_price=broker_fill_price,
                reconciliation_required=True,
                broker_order_id=broker_result.get("broker_order_id"),
                cancellation=cancellation,
            )
        if actual_close_qty >= qty - qty_tolerance:
            return PartialCloseOutcome(
                True,
                "confirmed_full_fill",
                filled_qty=min(actual_close_qty, qty),
                fill_price=broker_fill_price,
                full_fill=True,
                broker_order_id=broker_result.get("broker_order_id"),
                cancellation=cancellation,
            )

        if direction == "long":
            pnl = (broker_fill_price - entry_price) * actual_close_qty
            pnl_pct = ((broker_fill_price - entry_price) / entry_price) * 100
        else:
            pnl = (entry_price - broker_fill_price) * actual_close_qty
            pnl_pct = ((entry_price - broker_fill_price) / entry_price) * 100

        fee_rt_pct = (
            (config.BT_COMMISSION_CRYPTO_PCT + config.BT_SLIPPAGE_CRYPTO_PCT)
            / 100 * 2
        )
        fees_paid = round(entry_price * actual_close_qty * fee_rt_pct, 4)
        pnl = pnl - fees_paid
        partial_value = entry_price * actual_close_qty

        try:
            self._db.record_partial_exit(
                trade_id=trade_id,
                symbol=symbol,
                exit_price=broker_fill_price,
                quantity=actual_close_qty,
                position_value=partial_value,
                pnl=round(pnl, 4),
                pnl_pct=round(pnl_pct, 4),
                fees_paid=fees_paid,
                reason=exit_reason,
            )
        except Exception as exc:
            failed_result = dict(broker_result)
            failed_result["accounting_error"] = str(exc)
            self._set_kraken_partial_reconcile_hold(
                trade,
                "confirmed fill could not be recorded atomically",
                close_qty,
                failed_result,
            )
            return PartialCloseOutcome(
                False,
                "accounting_failed",
                filled_qty=actual_close_qty,
                fill_price=broker_fill_price,
                reconciliation_required=True,
                broker_order_id=broker_result.get("broker_order_id"),
                cancellation=cancellation,
            )

        trade["quantity"] = max(qty - actual_close_qty, 0)
        trade["position_value"] = max(
            float(trade.get("position_value") or 0) - partial_value, 0
        )
        trade["partial_pnl"] = float(trade.get("partial_pnl") or 0) + pnl
        trade["partial_fees_paid"] = (
            float(trade.get("partial_fees_paid") or 0) + fees_paid
        )
        trade["partial_exit_count"] = int(
            trade.get("partial_exit_count") or 0
        ) + 1

        try:
            cap = self._db.get_latest_capital()
            if cap:
                new_capital = cap["total_capital"] + pnl
                new_invested = max(0, cap["invested_value"] - partial_value)
                new_available = cap["available_cash"] + partial_value + pnl
                new_available = min(
                    new_available, max(0.0, new_capital - new_invested)
                )
                self._db.log_capital(
                    total=new_capital,
                    available=new_available,
                    invested=new_invested,
                    daily_pnl=cap["daily_pnl"] + pnl,
                    total_pnl=cap["total_pnl"] + pnl,
                    note=(
                        f"Partial {symbol} @ {broker} {exit_reason}: "
                        f"{'+' if pnl > 0 else ''}{pnl:.2f}"
                    ),
                )
        except Exception as cap_exc:
            logger.error(
                f"[PARTIAL ACCOUNTING] {symbol}: confirmed fill was recorded "
                f"but capital snapshot update failed ({cap_exc})"
            )

        try:
            bal = self._broker_manager.get_broker_balance(broker)
            if isinstance(bal, dict):
                returned = partial_value + pnl
                self._broker_manager.update_broker_balance(
                    broker,
                    bal.get("balance", 0.0) + pnl,
                    max(0.0, bal.get("invested", 0.0) - partial_value),
                    bal.get("available", 0.0) + returned,
                )
        except Exception as _bm_err:
            logger.debug(f"Broker balance update on partial close failed: {_bm_err}")

        logger.info(
            f"[PARTIAL TP] {symbol}: requested {close_qty:.6f}, broker "
            f"confirmed {actual_close_qty:.6f} @ ${broker_fill_price:.4f} | "
            f"P&L ${pnl:.2f} ({pnl_pct:+.2f}%) | "
            f"remaining qty {trade['quantity']:.6f}"
        )
        return PartialCloseOutcome(
            True,
            "confirmed_partial_fill",
            filled_qty=actual_close_qty,
            fill_price=broker_fill_price,
            stop_refresh_required=True,
            broker_order_id=broker_result.get("broker_order_id"),
            cancellation=cancellation,
        )

    def close_all_stock_positions(self):
        """Close all open stock positions — called at end of day."""
        if self.alpaca is None:
            logger.warning("EOD Alpaca close skipped: Alpaca credentials are not configured")
            return
        self.alpaca.close_all_stock_positions()

    def _submit(
        self,
        signal,
        approval: TradeApproval,
        broker_name_hint: str,
    ) -> Optional[Dict]:
        """Submit to exactly one pre-approved broker; never fall back here."""
        side   = "buy" if signal.direction == "long" else "sell"
        # Deterministic broker-native idempotency key, derived once by the
        # caller (breakout_receiver._inject_signal) from event_id and carried
        # through Signal.indicators. None for callers that don't set it
        # (e.g. non-breakout scanner paths) — brokers treat that as "no
        # client id supplied," matching pre-patch behavior exactly.
        client_order_id = signal.indicators.get("client_order_id")

        if signal.asset_class == "stock":
            if broker_name_hint == "ibkr":
                if not self._entry_enabled("ibkr") or self._ibkr is None:
                    logger.error(
                        f"IBKR submission blocked for {signal.symbol}: new "
                        "entries are no longer eligible"
                    )
                    return {
                        "status": "not_submitted",
                        "filled_qty": 0.0,
                        "filled_avg_price": 0.0,
                        "safe_to_fallback": True,
                        "order_submitted": False,
                        "broker_order_id": None,
                        "child_orders": {},
                        "actual_broker": "ibkr",
                    }
                if not self._ibkr.is_available():
                    logger.warning(
                        f"IBKR became unavailable before submission for "
                        f"{signal.symbol}; no order was submitted"
                    )
                    return {
                        "status": "not_submitted",
                        "filled_qty": 0.0,
                        "filled_avg_price": 0.0,
                        "safe_to_fallback": True,
                        "order_submitted": False,
                        "broker_order_id": None,
                        "child_orders": {},
                        "actual_broker": "ibkr",
                    }
                logger.info(f"Routing {signal.symbol} to IBKR (cash account, LIVE)")
                result = self._ibkr.submit_order(
                    signal.symbol, approval.quantity, side,
                    approval.stop_loss, approval.take_profit,
                    client_order_id=client_order_id,
                )
                if result is not None:
                    result["actual_broker"] = "ibkr"
                return result

            if broker_name_hint != "alpaca":
                logger.error(
                    f"Stock submission rejected for {signal.symbol}: "
                    f"unsupported selected broker {broker_name_hint!r}"
                )
                return None
            if not self._entry_enabled("alpaca") or self.alpaca is None:
                logger.error(
                    f"Stock order rejected for {signal.symbol}: Alpaca new "
                    "entries are disabled or credentials are not configured"
                )
                return None
            logger.info(f"Routing {signal.symbol} to Alpaca")
            result = self.alpaca.submit_order(
                signal.symbol, approval.quantity, side,
                approval.stop_loss, approval.take_profit,
                client_order_id=client_order_id,
            )
            if result is not None:
                result["actual_broker"] = "alpaca"         # record which broker filled
            return result

        elif signal.asset_class == "crypto":
            # Kraken is the default crypto executor — Coinbase API is deprecated.
            if broker_name_hint == "paper":
                return self._paper_fill(signal, approval)
            if broker_name_hint != "kraken" or not self._entry_enabled("kraken"):
                logger.error(
                    f"Crypto submission rejected for {signal.symbol}: selected "
                    f"broker {broker_name_hint!r} is not enabled for new entries"
                )
                return None

            qty      = approval.quantity
            leverage = 0   # 0 = spot (no margin params sent)

            # ── Margin leverage for short orders ─────────────────────────────
            # Kraken allows up to KRAKEN_MAX_LEVERAGE× on eligible pairs.
            # We cap at KRAKEN_SHORT_LEVERAGE and scale the position down so
            # our effective notional exposure = (desired/max) * normal_notional.
            # Example at defaults (desired=2, max=10):
            #   scale = 2/10 = 0.20  →  order qty = 20% of normal
            #   At 2× leverage, margin required = qty/2 = 10% of normal capital
            if signal.direction == "short" and not getattr(config, "KRAKEN_PAPER_MODE", False):
                desired_lev = getattr(config, "KRAKEN_SHORT_LEVERAGE", 2)
                max_lev     = exchange_capabilities.get_max_short_leverage(
                    signal.symbol, "kraken"
                )
                # Cap desired to whatever the pair actually supports
                actual_lev  = min(desired_lev, max_lev) if max_lev > 1 else 0
                if actual_lev > 1:
                    ref_max = getattr(config, "KRAKEN_MAX_LEVERAGE", 10)
                    scale   = actual_lev / ref_max
                    qty     = round(approval.quantity * scale, 8)
                    leverage = actual_lev
                    logger.info(
                        f"[LEVERAGE] {signal.symbol} short: "
                        f"{actual_lev}×/{ref_max}× → scale {scale:.2f} "
                        f"qty {approval.quantity:.6f}→{qty:.6f} "
                        f"(margin≈${qty/actual_lev * signal.current_price:.2f})"
                    )
            elif signal.direction == "short":
                logger.info(
                    f"[PAPER SHORT] {signal.symbol}: using full paper size "
                    "with no live Kraken leverage params"
                )

            _event_id_for_kraken = signal.indicators.get("event_id")
            kraken_userref = (
                derive_kraken_userref(_event_id_for_kraken)
                if _event_id_for_kraken else None
            )
            return self.kraken.submit_order(
                signal.symbol, qty, side,
                approval.stop_loss, approval.take_profit,
                leverage=leverage,
                client_order_id=kraken_userref,
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

    def _entry_enabled(self, broker_name: str) -> bool:
        """Return whether a broker may receive a new entry order.

        IBKR is intentionally not registered/synchronized by BrokerManager in
        Patch 1, so its entry gate is the explicit config/executor policy.
        The synthetic paper broker likewise has no persisted registration.
        Existing-position close/cancel/protection paths do not call this gate.
        """
        if broker_name == "ibkr":
            return bool(
                getattr(config, "IBKR_ENABLED", False)
                and getattr(config, "IBKR_TRADE_ENABLED", False)
                and self._ibkr is not None
            )
        if broker_name == "paper":
            return not getattr(config, "KRAKEN_ENABLED", False)
        info = self._broker_manager.get_broker(broker_name)
        return bool(info and info.get("enabled"))

    def _select_entry_broker(self, signal) -> Optional[str]:
        """Select one broker before approval; submission receives this name."""
        if signal.asset_class == "stock":
            if (self._entry_enabled("ibkr") and
                    self._ibkr.is_available()):
                return "ibkr"
            return "alpaca" if self._entry_enabled("alpaca") else None
        if signal.asset_class == "crypto":
            if getattr(config, "KRAKEN_ENABLED", False):
                return "kraken" if self._entry_enabled("kraken") else None
            return "paper" if self._entry_enabled("paper") else None
        return None

    def _get_broker_name(self, signal) -> Optional[str]:
        """Compatibility wrapper for callers/tests; entries use one selection."""
        return self._select_entry_broker(signal)

    def _entry_preconditions_pass(self, signal, broker_name: str) -> bool:
        """Run broker-specific checks once for each separately selected attempt."""
        if signal.direction != "short":
            return True
        paper_kraken_short = (
            signal.asset_class == "crypto"
            and broker_name == "kraken"
            and getattr(config, "KRAKEN_PAPER_MODE", False)
        )
        if paper_kraken_short:
            logger.info(
                f"[PAPER SHORT] {signal.symbol}: skipping live Kraken "
                "margin-eligibility check"
            )
            return True
        if not exchange_capabilities.can_short(signal.symbol, broker_name):
            logger.info(
                f"[SHORT BLOCKED] {signal.symbol} on {broker_name}: "
                "not margin-eligible — entry attempt dropped"
            )
            return False
        return True

    def _approve_for_broker(
        self, signal, broker_name: str, custom_sl, custom_tp, custom_pos,
        structural_stop_hint, bypass_win_cooldown,
    ) -> TradeApproval:
        return self._risk_manager.approve_trade(
            symbol=signal.symbol,
            entry_price=signal.current_price,
            signal_score=signal.score,
            direction=signal.direction,
            custom_stop_loss_pct=custom_sl,
            custom_take_profit_pct=custom_tp,
            custom_position_pct=custom_pos,
            broker_name=broker_name,
            structural_stop_price=structural_stop_hint,
            bypass_win_cooldown=bypass_win_cooldown,
            strategy_name=signal.indicators.get("strategy_name"),
        )

    @staticmethod
    def _approval_allows_alpaca_fallback(approval: TradeApproval) -> bool:
        reason = approval.reason or ""
        return any(reason.startswith(prefix) for prefix in (
            "No available cash on ibkr",
            "Insufficient cash on ibkr",
            "Broker balance unavailable for ibkr",
        ))

    @staticmethod
    def _ibkr_result_allows_alpaca_fallback(result: Optional[Dict]) -> bool:
        if not isinstance(result, dict):
            return False
        if result.get("safe_to_fallback") is not True:
            return False
        try:
            filled_qty = float(result.get("filled_qty"))
            filled_price = float(result.get("filled_avg_price"))
        except (TypeError, ValueError):
            return False
        if not math.isfinite(filled_qty) or filled_qty != 0.0:
            return False
        if not math.isfinite(filled_price) or filled_price != 0.0:
            return False
        if str(result.get("status") or "").strip().lower() not in {
            "not_submitted", "definitive_no_exposure",
        }:
            return False
        if result.get("order_submitted") is not False:
            return False
        if result.get("broker_order_id") is not None:
            return False
        child_orders = result.get("child_orders")
        if not isinstance(child_orders, dict):
            return False
        for child in child_orders.values():
            if not isinstance(child, dict):
                return False
            status = str(child.get("status") or "").strip().lower()
            if child.get("submitted") is True or child.get("order_submitted") is True:
                return False
            if child.get("transmit") is True:
                return False
            if status not in {"", "not_submitted"}:
                return False
        return True

    @staticmethod
    def _ibkr_status(result: Optional[Dict]) -> str:
        if not isinstance(result, dict):
            return "missing_result"
        return str(result.get("status") or "unknown").strip().lower()

    @classmethod
    def _classify_ibkr_result(cls, result: Optional[Dict]) -> str:
        """Classify IBKR exposure before any generic trade persistence."""
        if cls._ibkr_result_allows_alpaca_fallback(result):
            return "proven_pre_submit_zero"
        if not isinstance(result, dict):
            return "reconcile_zero"

        status = cls._ibkr_status(result)
        valid, filled_qty, _filled_price, _error = cls._validated_ibkr_fill_values(result)
        if not valid:
            return "reconcile_invalid"

        if status == "filled" and filled_qty > 0:
            return "confirmed_full"
        if filled_qty > 0:
            return "reconcile_partial"
        if status in {"rejected", "cancelled", "canceled", "expired"}:
            return "definitive_zero"
        return "reconcile_zero"

    @staticmethod
    def _validated_ibkr_fill_values(result: Dict):
        try:
            filled_qty = float(result.get("filled_qty"))
            filled_price = float(result.get("filled_avg_price"))
        except (TypeError, ValueError):
            return False, None, None, "malformed fill quantity or average price"
        if not math.isfinite(filled_qty) or filled_qty < 0:
            return False, None, None, "filled quantity is non-finite or negative"
        if not math.isfinite(filled_price) or filled_price < 0:
            return False, None, None, "filled average price is non-finite or negative"
        if filled_qty > 0 and filled_price <= 0:
            return False, None, None, "positive fill has no positive average price"
        return True, filled_qty, filled_price, None

    def _persist_ibkr_reconciliation_markers(
        self, symbol: str, marker_id: str, marker: Dict,
    ) -> None:
        """Persist a marker pair atomically, or symbol-first for test doubles."""
        symbol_key = f"ibkr_reconciliation_symbol_{symbol}"
        order_key = f"ibkr_reconciliation_order_{marker_id}"
        if hasattr(self._db, "_conn"):
            try:
                with self._db._conn() as conn:
                    now_iso = datetime.now().isoformat()
                    for key in (symbol_key, order_key):
                        conn.execute(
                            "INSERT OR REPLACE INTO bot_state (key, value, updated) "
                            "VALUES (?, ?, ?)",
                            (key, json.dumps(marker), now_iso),
                        )
                return
            except Exception as exc:
                logger.critical(
                    f"[IBKR RECONCILIATION] atomic marker persistence failed "
                    f"for {symbol}: {exc}; using symbol-first fallback"
                )
        for key in (symbol_key, order_key):
            try:
                self._db.set_state(key, marker)
            except Exception as exc:
                logger.critical(
                    f"[IBKR RECONCILIATION] failed to persist {key}: {exc}"
                )

    def _handle_ibkr_reconciliation_required(
        self, signal, approval: TradeApproval, result: Optional[Dict],
        has_confirmed_exposure: bool,
    ) -> None:
        """Persist IBKR ambiguity/partial exposure exactly and halt globally.

        IBKR bracket children may already protect confirmed exposure. Their
        identifiers and observed states are retained for reconciliation; this
        handler does not place duplicate protection or infer child behavior.
        """
        result = result if isinstance(result, dict) else {}
        order_id = result.get("broker_order_id")
        status = self._ibkr_status(result)
        valid_fill, filled_qty, filled_price, validation_error = (
            self._validated_ibkr_fill_values(result)
        )
        if not valid_fill:
            filled_qty = None
            filled_price = None
            has_confirmed_exposure = False

        if order_id is not None:
            marker_id = str(order_id)
            try:
                already_handled = self._db.get_state(
                    f"ibkr_reconciliation_order_{marker_id}"
                )
            except Exception:
                already_handled = None
            if already_handled:
                reason = (
                    f"IBKR order {order_id} for {signal.symbol} remains "
                    "unreconciled; duplicate handling suppressed."
                )
                logger.critical(reason)
                self._risk_manager.manual_halt(reason)
                return
        else:
            marker_id = result.get("reconciliation_incident_id")
            if not marker_id:
                marker_id = f"unknown-{uuid.uuid4().hex[:12]}"
                result["reconciliation_incident_id"] = marker_id
        marker = {
            "broker": "ibkr",
            "symbol": signal.symbol,
            "direction": signal.direction,
            "order_id": order_id,
            "status": status,
            "requested_qty": result.get("requested_qty", approval.quantity),
            "confirmed_filled_qty": filled_qty,
            "confirmed_filled_avg_price": filled_price,
            "fill_validation_error": validation_error,
            "incident_id": marker_id,
            "order_submitted": result.get("order_submitted"),
            "child_orders": result.get("child_orders", {}),
            "reconciliation_required": True,
            "timestamp": datetime.now().isoformat(),
        }
        self._persist_ibkr_reconciliation_markers(signal.symbol, marker_id, marker)

        provisional_id = None
        if has_confirmed_exposure and filled_qty is not None and filled_qty > 0:
            if filled_price > 0:
                provisional_id = f"IBKR-RECON-{marker_id}"
                provisional_record = {
                    "trade_id": provisional_id,
                    "symbol": signal.symbol,
                    "asset_class": "stock",
                    "direction": signal.direction,
                    "entry_time": marker["timestamp"],
                    "entry_price": round(filled_price, 6),
                    "quantity": filled_qty,
                    "strategy_name": signal.indicators.get("strategy_name", "original"),
                    "entry_timeframe": signal.indicators.get("timeframe", "5Min"),
                    "position_value": round(filled_qty * filled_price, 4),
                    "stop_loss": round(approval.stop_loss, 6),
                    "take_profit": round(approval.take_profit, 6),
                    "signal_score": signal.score,
                    "indicators": {
                        **signal.indicators,
                        "ibkr_provisional_reconciliation": True,
                        "ibkr_parent_status": status,
                        "ibkr_child_orders": marker["child_orders"],
                    },
                    "broker": "ibkr",
                    "broker_order_id": order_id,
                }
                try:
                    self._db.open_trade(provisional_record)
                except Exception as exc:
                    logger.critical(
                        f"[IBKR RECONCILIATION] failed to persist confirmed "
                        f"partial exposure for {signal.symbol}: {exc}"
                    )
            else:
                logger.critical(
                    f"[IBKR RECONCILIATION] {signal.symbol}: confirmed quantity "
                    f"{filled_qty} has no confirmed average price; refusing to "
                    "guess a normal trade value"
                )

        reason = (
            f"IBKR order requires reconciliation for {signal.symbol} "
            f"(order_id={order_id}, status={status}, confirmed_qty={filled_qty})."
        )
        if provisional_id:
            reason += f" Confirmed exposure tracked as {provisional_id}."
        logger.critical(reason)
        self._risk_manager.manual_halt(reason)

    def get_account_value(self) -> float:
        try:
            if self._ibkr is not None and self._ibkr.is_available():
                acct = self._ibkr.get_account()
                return acct["equity"]
            if self.alpaca is None:
                raise RuntimeError("Alpaca credentials are not configured")
            acct = self.alpaca.get_account()
            return acct["equity"]
        except Exception:
            cap = self._db.get_latest_capital()
            return cap["total_capital"] if cap else 0.0


# Singleton
executor = TradeExecutor()
