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

import json
import logging
import os
import time
from typing import Optional, Dict
import ccxt

logger = logging.getLogger(__name__)

# Order states ccxt/Kraken report that mean "nothing more will happen to
# this order" — a fully/partially filled close, or a clean reject/cancel.
_TERMINAL_ORDER_STATUSES = {"closed", "canceled", "cancelled", "expired", "rejected"}


class KrakenExecutor:

    def __init__(self, api_key: str = "", api_secret: str = "",
                 paper: bool = False,
                 fill_poll_attempts: int = 5,
                 fill_poll_interval_sec: float = 0.5):
        self.paper = paper

        # Always init the exchange for price lookups
        # timeout=10000ms — prevents API hangs from freezing the scan thread
        self.exchange = ccxt.kraken({
            "apiKey":          api_key,
            "secret":          api_secret,
            "enableRateLimit": True,
            "timeout":         10000,   # 10 second hard timeout on all API calls
        })

        # Bounded poll budget for resolving a just-submitted order that comes
        # back non-terminal (still "open") before we give up and cancel it.
        # Overridable per-instance (tests use 0-interval polling).
        self.fill_poll_attempts     = fill_poll_attempts
        self.fill_poll_interval_sec = fill_poll_interval_sec

        # Durable, append-only record of orders whose final fill state could
        # not be confirmed even after a cancel + follow-up fetch. Matches the
        # existing core/candle_manager.py._log_unreachable() convention.
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._unresolved_log_path = os.path.join(_root, "logs", "kraken_unresolved_orders.log")

        if paper:
            logger.info("Kraken executor initialized in PAPER mode — orders simulated locally.")
        else:
            logger.info("Kraken executor initialized in LIVE mode.")

    def submit_order(self, symbol: str, qty: float, side: str,
                     stop_loss: float, take_profit: float,
                     leverage: int = 0,
                     client_order_id: Optional[int] = None) -> Optional[Dict]:
        """
        Submit a market order to Kraken.

        leverage:
          0 (default) — spot order, no margin params sent
          N > 1       — margin order at N× leverage; ccxt sends leverage in params
                        Required for short (sell) orders on Kraken; optional for
                        leveraged longs.

        client_order_id: Kraken's userref — a 32-bit integer, already derived
        by the caller (core.event_identity.derive_kraken_userref). Not a
        string like Alpaca/IBKR client identity; passed pre-converted so this
        module has no dependency on event_identity's hashing internals.

        qty is the notional amount in base currency AFTER any scaling the caller
        has already applied (trade_executor scales qty down for margin trades so
        that effective exposure = qty * leverage, not qty * max_leverage).

        Returns a dict describing the FINAL confirmed order state (never the
        raw, possibly-still-open response from create_market_order — see
        _resolve_order_fill). "filled_qty" is the authoritative cumulative
        base-asset amount actually bought/sold; callers must never fall back
        to the requested qty. When the final state genuinely cannot be
        confirmed, "resolution_failed" is True and a durable reconciliation
        record has already been written — callers must fail closed, not
        silently treat this as either a fill or a non-fill.
        """
        ccxt_symbol = symbol.replace("-", "/")
        lev_str     = f" {leverage}x" if leverage > 1 else ""

        if self.paper:
            # Paper mode: simulate fill at current market price
            price    = self.get_current_price(symbol) or 0.0
            order_id = f"PAPER-{symbol}-{int(time.time())}"
            logger.info(
                f"[PAPER] Kraken simulated fill: {symbol} {side}{lev_str} "
                f"{qty} @ ${price:.4f}"
            )
            return {
                "broker_order_id":   order_id,
                "status":            "filled",
                "filled_qty":        qty,
                "filled_avg_price":  price,
                "resolution_failed": False,
                "leverage":          leverage,
            }

        # Live mode
        try:
            params = {}
            if leverage > 1:
                params["leverage"] = leverage
            if client_order_id is not None:
                params["userref"] = client_order_id

            order    = self.exchange.create_market_order(
                ccxt_symbol, side, qty, params=params
            )
            order_id = order.get("id")

            final = self._resolve_order_fill(ccxt_symbol, order_id, order)

            if final["resolution_failed"]:
                self._record_unresolved_order(symbol, order_id, side, qty, final)
                logger.critical(
                    f"[KRAKEN UNRESOLVED] {symbol} {side} qty={qty} "
                    f"order_id={order_id}: final fill state could not be "
                    f"confirmed after cancel + follow-up fetch — last known "
                    f"filled={final['filled_qty']} status='{final['status']}'. "
                    f"Manual reconciliation required — see "
                    f"{self._unresolved_log_path}"
                )
                return {
                    "broker_order_id":   order_id,
                    "status":            "unresolved",
                    "filled_qty":        final["filled_qty"],
                    "filled_avg_price":  final["filled_avg_price"],
                    "resolution_failed": True,
                    "leverage":          leverage,
                }

            logger.info(
                f"Kraken order filled: {symbol} {side}{lev_str} "
                f"{final['filled_qty']} @ ${final['filled_avg_price']:.4f} "
                f"(status={final['status']})"
            )
            return {
                "broker_order_id":   order_id,
                "status":            final["status"],
                "filled_qty":        final["filled_qty"],
                "filled_avg_price":  final["filled_avg_price"],
                "resolution_failed": False,
                "leverage":          leverage,
            }
        except Exception as e:
            logger.error(f"Kraken order failed for {symbol}: {e}")
            return None

    @staticmethod
    def _confirmed_qty(order: Optional[dict]) -> float:
        """
        Extract a cumulative filled quantity from an order dict, treating a
        missing/None "filled" field as 0.0 — never as "trust the caller's
        requested qty instead" (that fallback is exactly the bug this whole
        resolution path exists to close).
        """
        raw = (order or {}).get("filled")
        return float(raw) if raw is not None else 0.0

    @staticmethod
    def _confirmed_price(order: Optional[dict]) -> float:
        order = order or {}
        return float(order.get("average") or order.get("price") or 0)

    def _resolve_order_fill(self, ccxt_symbol: str, order_id: Optional[str],
                            initial_order: dict) -> Dict:
        """
        Resolve the definitive terminal state of a just-submitted order.

        1. If the initial response is already terminal (closed/canceled/
           rejected/expired), trust it — no polling needed.
        2. Otherwise poll fetch_order() for a bounded interval looking for a
           terminal state (covers an order that fills a moment after
           submission).
        3. If still non-terminal after polling, cancel the remainder.
        4. Regardless of whether the cancel call itself succeeded or raised
           (Kraken may reject a cancel because the order just filled — that's
           not a failure, it's information), fetch the order ONE more time —
           a fill can race the cancel, so the cancel's own outcome is never
           trusted as the final word.
        5. Only if that mandatory post-cancel fetch also fails to produce a
           terminal state do we give up and report resolution_failed=True.

        Returns {"filled_qty", "filled_avg_price", "status", "resolution_failed"}.
        """
        if not order_id:
            # Can't poll or cancel without an order ID — nothing to resolve.
            return {
                "filled_qty":        self._confirmed_qty(initial_order),
                "filled_avg_price":  self._confirmed_price(initial_order),
                "status":            (initial_order.get("status") or "unknown"),
                "resolution_failed": True,
            }

        status = (initial_order.get("status") or "").lower()
        if status in _TERMINAL_ORDER_STATUSES:
            return {
                "filled_qty":        self._confirmed_qty(initial_order),
                "filled_avg_price":  self._confirmed_price(initial_order),
                "status":            status,
                "resolution_failed": False,
            }

        # ── Non-terminal: poll for a bounded interval ───────────────────────
        last_order = initial_order
        for _ in range(self.fill_poll_attempts):
            if self.fill_poll_interval_sec > 0:
                time.sleep(self.fill_poll_interval_sec)
            try:
                last_order = self.exchange.fetch_order(order_id, ccxt_symbol)
            except Exception as e:
                logger.warning(f"Kraken fetch_order poll failed for {order_id}: {e}")
                continue
            status = (last_order.get("status") or "").lower()
            if status in _TERMINAL_ORDER_STATUSES:
                return {
                    "filled_qty":        self._confirmed_qty(last_order),
                    "filled_avg_price":  self._confirmed_price(last_order),
                    "status":            status,
                    "resolution_failed": False,
                }

        # ── Still non-terminal after polling — cancel the remainder ────────
        try:
            self.exchange.cancel_order(order_id, ccxt_symbol)
        except Exception as e:
            # A cancel can legitimately fail because the order just filled
            # (nothing left to cancel) — not necessarily an error. The
            # mandatory fetch below is the actual source of truth, not this.
            logger.warning(
                f"Kraken cancel_order failed for {order_id} "
                f"(order may have just filled): {e}"
            )

        # ── Mandatory post-cancel fetch: a fill can race the cancel ─────────
        try:
            final_order = self.exchange.fetch_order(order_id, ccxt_symbol)
        except Exception as e:
            logger.error(f"Kraken post-cancel fetch_order failed for {order_id}: {e}")
            return {
                "filled_qty":        self._confirmed_qty(last_order),
                "filled_avg_price":  self._confirmed_price(last_order),
                "status":            (last_order.get("status") or "unknown"),
                "resolution_failed": True,
            }

        status = (final_order.get("status") or "").lower()
        if status in _TERMINAL_ORDER_STATUSES:
            return {
                "filled_qty":        self._confirmed_qty(final_order),
                "filled_avg_price":  self._confirmed_price(final_order),
                "status":            status,
                "resolution_failed": False,
            }

        # The post-cancel fetch succeeded but still isn't terminal — the
        # cancel apparently didn't take effect. Ambiguous: fail closed
        # rather than guess whether/how much of the order is still live.
        return {
            "filled_qty":        self._confirmed_qty(final_order),
            "filled_avg_price":  self._confirmed_price(final_order),
            "status":            status,
            "resolution_failed": True,
        }

    def _record_unresolved_order(self, symbol: str, order_id: Optional[str],
                                 side: str, requested_qty: float, final: Dict):
        """
        Append a durable, greppable record of an order whose final fill
        state could not be confirmed — needs manual reconciliation against
        the live Kraken account (see Scripts/reconcile_positions.py) before
        any DB/position assumption is made for this order_id.
        Best-effort: a failure to write this record must never itself
        produce a second, worse silent failure.
        """
        try:
            record = {
                "timestamp":             time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol":                symbol,
                "order_id":              order_id,
                "side":                  side,
                "requested_qty":         requested_qty,
                "last_known_filled_qty": final.get("filled_qty"),
                "last_known_status":     final.get("status"),
                "note": (
                    "Final fill state could not be confirmed after a cancel "
                    "attempt and follow-up fetch. Reconcile manually against "
                    "the Kraken account before trusting any DB record for "
                    "this order."
                ),
            }
            os.makedirs(os.path.dirname(self._unresolved_log_path), exist_ok=True)
            with open(self._unresolved_log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as log_err:
            logger.critical(
                f"[KRAKEN UNRESOLVED] Could not write durable reconciliation "
                f"record for order {order_id} ({symbol}): {log_err} — "
                f"side={side} requested_qty={requested_qty} "
                f"last_known_filled={final.get('filled_qty')} "
                f"last_known_status={final.get('status')}"
            )

    def cancel_all_orders_for_symbol(self, symbol: str) -> int:
        """
        Cancel every open order on Kraken for the given symbol.

        Called before closing a position so no resting stop/TP order fires
        after the position is gone and opens an unintended new trade.

        Returns the number of orders cancelled.
        Paper mode: always returns 0 (no real orders placed in paper mode).
        """
        if self.paper:
            return 0
        cancelled = 0
        try:
            # Fetch all open orders (Kraken returns them keyed by order ID)
            resp       = self.exchange.privatePostOpenorders({})
            open_orders = (resp.get("result", {}).get("open") or {})
            for oid, o in open_orders.items():
                descr    = o.get("descr", {})
                pair_raw = descr.get("pair", "")
                # Normalise both sides to "BASE/QUOTE" for comparison
                norm = pair_raw.replace("XBT", "BTC").upper()
                tgt  = symbol.replace("-", "/").upper()
                # Match if pair contains the base currency or full symbol
                if tgt in norm or norm.replace("/", "") in tgt.replace("/", ""):
                    try:
                        self.exchange.cancelOrder(oid)
                        logger.info(
                            f"[PRE-CLOSE CANCEL] {symbol}: cancelled order {oid[:12]}"
                        )
                        cancelled += 1
                    except Exception as ce:
                        logger.warning(
                            f"[PRE-CLOSE CANCEL] {symbol}: could not cancel {oid[:12]}: {ce}"
                        )
        except Exception as e:
            logger.warning(f"cancel_all_orders_for_symbol({symbol}): {e}")
        return cancelled

    def close_position(self, symbol: str, qty: float, side: str,
                       leverage: int = 0) -> bool:
        """
        Close an open Kraken position.

        Steps (live mode):
          1. Cancel all resting orders for the symbol first (stop, TP, etc.)
             so nothing fires after the position is gone.
          2. Send a margin-aware market close order.
             - If leverage > 1 the original entry was a margin trade; we must
               send leverage in the close order so Kraken reduces the margin
               position rather than opening a new spot position.
             - If leverage == 0 (spot entry) a plain market order is correct.

        Paper mode skips both steps and returns True immediately.
        """
        ccxt_symbol = symbol.replace("-", "/")

        if self.paper:
            price      = self.get_current_price(symbol) or 0.0
            close_side = "sell" if side == "buy" else "buy"
            logger.info(
                f"[PAPER] Kraken simulated close: {symbol} "
                f"{close_side} {qty} @ ${price:.4f}"
            )
            return True

        # ── 1. Cancel all resting orders for this symbol ─────────────────────
        n_cancelled = self.cancel_all_orders_for_symbol(symbol)
        if n_cancelled:
            logger.info(
                f"[CLOSE] {symbol}: cancelled {n_cancelled} open order(s) before close"
            )

        # ── 2. Send margin-aware market close order ───────────────────────────
        try:
            close_side = "sell" if side == "buy" else "buy"
            params     = {}
            if leverage > 1:
                params["leverage"] = leverage
            self.exchange.create_market_order(ccxt_symbol, close_side, qty,
                                              params=params)
            logger.info(
                f"Kraken position closed: {symbol} {close_side} "
                f"{qty} {'@ {}x leverage'.format(leverage) if leverage > 1 else '(spot)'}"
            )
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

    def get_open_position(self, symbol: str) -> Optional[Dict]:
        """
        Check if a position actually exists on Kraken exchange.
        Returns position dict with size and avg price, or None if no position.
        In paper mode always returns None (positions are DB-only).
        Used by position_monitor to detect broker-closed positions.
        """
        if self.paper:
            return None   # paper mode has no real positions

        try:
            # Kraken uses base currency as the position key (e.g. BTC for BTC/USD)
            base = symbol.split("/")[0]
            balance = self.exchange.fetch_balance()
            free  = float(balance.get(base, {}).get("free",  0) or 0)
            used  = float(balance.get(base, {}).get("used",  0) or 0)
            total = free + used
            if total > 0.0001:   # position exists
                return {"symbol": symbol, "size": total, "free": free, "used": used}
            return None
        except Exception as e:
            logger.debug(f"get_open_position error for {symbol}: {e}")
            return None

    def find_order_by_userref(self, userref: int, symbol: Optional[str] = None) -> Optional[Dict]:
        """
        Best-effort reconciliation lookup by Kraken userref (our deterministic
        client-order identity — see core.event_identity.derive_kraken_userref).

        LIMITATION (flagged, not fully resolved): ccxt's generic
        fetch_open_orders()/fetch_closed_orders() do not expose a userref
        filter parameter on this exchange integration, so this scans the
        raw 'info' of each returned order for a matching userref instead of
        querying Kraken's native QueryOrders-by-userref endpoint directly.
        This is correct but not necessarily complete — Kraken's closed-order
        history has retention/pagination limits ccxt's default call does not
        page through. Treat a miss here as "not found in the scanned
        window", not as definitive proof the order doesn't exist.
        """
        if self.paper:
            return None
        try:
            ccxt_symbol = symbol.replace("-", "/") if symbol else None
            candidates = []
            try:
                candidates += self.exchange.fetch_open_orders(ccxt_symbol) or []
            except Exception as e:
                logger.debug(f"find_order_by_userref: fetch_open_orders failed: {e}")
            try:
                candidates += self.exchange.fetch_closed_orders(ccxt_symbol, limit=50) or []
            except Exception as e:
                logger.debug(f"find_order_by_userref: fetch_closed_orders failed: {e}")

            for o in candidates:
                info = o.get("info") or {}
                raw_userref = info.get("userref")
                if raw_userref is not None and int(raw_userref) == int(userref):
                    return {
                        "broker_order_id":  o.get("id"),
                        "status":           o.get("status"),
                        "filled_qty":       float(o.get("filled") or 0),
                        "filled_avg_price": float(o.get("average") or o.get("price") or 0),
                    }
            return None
        except Exception as e:
            logger.warning(f"find_order_by_userref({userref}) failed: {e}")
            return None

    def get_recent_closed_order(self, symbol: str,
                                 since_timestamp: float = None) -> Optional[Dict]:
        """
        Query Kraken for the most recent closed order for a symbol.
        Used to find the actual fill price after an SL/TP fires at the exchange.
        Returns dict with fill price and side, or None if not found.
        """
        if self.paper:
            return None

        try:
            ccxt_symbol = symbol.replace("-", "/")
            since_ms    = int(since_timestamp * 1000) if since_timestamp else None
            orders      = self.exchange.fetch_closed_orders(
                ccxt_symbol, since=since_ms, limit=5
            )
            if not orders:
                return None
            # Most recent closed order
            orders.sort(key=lambda o: o.get("timestamp", 0), reverse=True)
            o = orders[0]
            return {
                "fill_price": float(o.get("average") or o.get("price") or 0),
                "filled_qty": float(o.get("filled") or 0),
                "side":       o.get("side", ""),
                "order_id":   o.get("id", ""),
                "timestamp":  o.get("timestamp", 0),
            }
        except Exception as e:
            logger.debug(f"get_recent_closed_order error for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Return the current mid-price for *symbol* from Kraken.

        Defence against stale / garbage ticker prices
        ------------------------------------------------
        Some tokens (especially newly listed ones) have a `last` trade price
        that is days or weeks old and wildly different from the active market.
        We cross-check `last` against the live bid/ask mid-price:

        * If bid AND ask are present and sane (bid < ask, both > 0), use
          mid-price as the reference.
        * If `last` deviates from mid by more than 50 %, the ticker is stale
          — return mid instead (it reflects the live order book).
        * If bid/ask are missing (e.g. market closed or illiquid) fall back to
          `last` as before, so normal operation is unaffected.
        """
        try:
            ccxt_symbol = symbol.replace("-", "/")
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            last = float(ticker.get("last") or 0)
            bid  = float(ticker.get("bid")  or 0)
            ask  = float(ticker.get("ask")  or 0)

            # ── prefer mid-price when the order book is live ─────────────────
            if bid > 0 and ask > 0 and bid < ask:
                mid = (bid + ask) / 2.0
                if last > 0:
                    deviation = abs(last - mid) / mid
                    if deviation > 0.50:
                        logger.warning(
                            f"[TICKER SANITY] {symbol}: last=${last:.6f} deviates "
                            f"{deviation*100:.1f}% from mid=${mid:.6f} — "
                            f"using mid (stale last price suspected)"
                        )
                        return mid
                return mid          # bid/ask available — mid is more reliable

            # ── no live book — fall back to last ─────────────────────────────
            if last > 0:
                return last

            return None
        except Exception as e:
            logger.debug(f"Kraken price lookup failed for {symbol}: {e}")
            return None

    def place_stop_order(self, symbol: str, qty: float,
                         side: str, stop_price: float,
                         leverage: int = 0) -> Optional[str]:
        """
        Place a protective stop-loss order on Kraken (executes as a market
        order once the trigger price is hit).
        side: 'buy' (to close a short) or 'sell' (to close a long)

        leverage:
          0 (default) — spot stop. No margin-only params are sent; Kraken
            rejects reduceOnly/leverage on spot orders (ccxt docs flag both
            as "*margin only*"), so they must never be attached here.
          N > 1       — margin stop closing a position that was opened at
            N× leverage. Sent with BOTH `leverage` (so Kraken recognises the
            same margin context the position was opened in) AND
            `reduceOnly` (so Kraken reduces the existing position instead of
            potentially opening a new/opposite one if the order and the
            live position size ever diverge) — mirrors the leverage handling
            close_position() already uses for full closes.

        NOTE: this previously sent type="stop-market" with params={"stopPrice"}.
        Neither is a real Kraken/ccxt order shape — "stop-market" is not a
        valid Kraken raw ordertype, and ccxt's Kraken order_request() only
        recognises params.stopLossPrice (not stopPrice), so that combination
        would have been rejected by Kraken's API in live mode. Fixed to use
        ccxt's documented params.stopLossPrice mechanism, which order_request()
        maps to the real 'stop-loss' ordertype.

        Returns order_id string or None on failure. A returned order_id only
        confirms Kraken accepted the order — it does NOT by itself prove the
        order carries correct leverage/reduceOnly semantics; callers must not
        assume "got an ID" means "this protects the leveraged position."
        Paper mode: returns a fake order ID for tracking.
        """
        ccxt_symbol = symbol.replace("-", "/")
        if self.paper:
            fake_id = f"PAPER-STOP-{symbol}-{int(stop_price*10000)}"
            logger.info(
                f"[PAPER] Stop order placed: {symbol} {side} {qty} "
                f"@ ${stop_price:.4f} | id={fake_id}"
            )
            return fake_id
        try:
            params = {"stopLossPrice": stop_price}
            if leverage > 1:
                params["leverage"]   = leverage
                params["reduceOnly"] = True
            order = self.exchange.create_order(
                symbol = ccxt_symbol,
                type   = "market",
                side   = side,
                amount = qty,
                params = params,
            )
            order_id = order["id"]
            logger.info(
                f"Stop order placed: {symbol} {side} {qty} @ ${stop_price:.4f}"
                f"{f' (leverage={leverage}x, reduceOnly=True)' if leverage > 1 else ''} "
                f"| id={order_id}"
            )
            return order_id
        except Exception as e:
            logger.error(f"Failed to place stop order for {symbol}: {e}")
            return None

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an open order by ID. Paper mode: always succeeds."""
        if self.paper:
            logger.info(f"[PAPER] Order cancelled: {order_id}")
            return True
        ccxt_symbol = symbol.replace("-", "/")
        try:
            self.exchange.cancel_order(order_id, ccxt_symbol)
            logger.info(f"Order cancelled: {order_id} for {symbol}")
            return True
        except Exception as e:
            logger.warning(f"Cancel order failed {order_id} for {symbol}: {e}")
            return False

    def update_stop_order(self, symbol: str, old_order_id: str,
                          qty: float, side: str,
                          new_stop_price: float,
                          leverage: int = 0) -> Optional[str]:
        """
        Move a stop order to a new price.
        Cancel old order → place new one → return new order_id.
        Returns new order_id on success, None when the old stop remains in
        place, or "" when the old stop was cancelled but replacement failed.

        leverage: must match the leverage the position was originally opened
        at (0 for spot) — see place_stop_order() for why. The replacement
        stop must preserve the same close semantics as the original.
        """
        if old_order_id:
            cancelled = self.cancel_order(symbol, old_order_id)
            if not cancelled:
                logger.warning(
                    f"Stop replacement skipped for {symbol}: could not cancel "
                    f"existing stop {old_order_id}"
                )
                return None

        new_order_id = self.place_stop_order(
            symbol, qty, side, new_stop_price, leverage=leverage
        )
        if old_order_id and not new_order_id and not self.paper:
            logger.error(
                f"[STOP REPLACE UNPROTECTED] {symbol}: cancelled stop "
                f"{old_order_id} but failed to place replacement at "
                f"${new_stop_price:.6f}"
            )
            return ""
        return new_order_id

    def get_trading_pairs(self) -> list:
        try:
            markets = self.exchange.load_markets()
            return [m for m in markets.keys() if "/USD" in m]
        except Exception as e:
            logger.debug(f"Failed to load Kraken markets: {e}")
            return []
