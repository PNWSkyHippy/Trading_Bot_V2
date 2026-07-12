"""
Focused, deterministic probe for the live-Kraken order-lifecycle-resolution
fix in core/kraken_executor.py + the fill-quantity fix in
core/trade_executor.py.

Scope: confirmed-fill-quantity / leveraged-short accounting, and safe
resolution of orders that come back non-terminal (open/pending) instead of
immediately closed. Does NOT exercise ghost-close, bracket-stop-mismatch,
IBKR fallback, settlement, or partial-exit code paths — those are separate
findings.

Run:
    ./venv312/Scripts/python.exe Scripts/test_kraken_fill_quantity.py

No network calls, no real DB writes, no real orders — everything the fix
touches (ccxt exchange, DB, risk_manager, broker_manager) is stubbed.
IBKR_ENABLED is forced off BEFORE core.trade_executor is imported, so the
module-level TradeExecutor() singleton never attempts a TWS connection.
"""

import sys
import os
import json
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
config.IBKR_ENABLED = False   # must happen before core.trade_executor is imported

from core.risk_manager import TradeApproval
import core.risk_manager as rm_mod
from core.kraken_executor import KrakenExecutor
import core.trade_executor as te_mod
from core.trade_executor import TradeExecutor
import core.exchange_capabilities as ec_mod
import core.broker_manager as bm_mod


# ── Test doubles ────────────────────────────────────────────────────────────

class FakeExchange:
    """
    Stands in for KrakenExecutor.exchange (a ccxt.kraken instance).

    fetch_order_responses: queue of dicts/Exceptions consumed in order by
        polling fetch_order() calls made BEFORE cancel_order() is called.
    cancel_order_result: None => cancel succeeds; an Exception instance =>
        cancel_order() raises it (simulating e.g. "already filled").
    fetch_order_after_cancel: dict/Exception used for the single mandatory
        fetch_order() call made AFTER cancel_order() — this is the race-
        safe "source of truth" call. If None, falls back to the queue.
    """

    def __init__(self, market_order_response,
                 fetch_order_responses=None,
                 cancel_order_result=None,
                 fetch_order_after_cancel=None):
        self.market_order_response = market_order_response
        self.market_order_calls = []
        self.fetch_order_calls = []
        self.cancel_order_calls = []
        self.stop_order_calls = []
        self._fetch_order_responses = list(fetch_order_responses or [])
        self._cancel_order_result = cancel_order_result
        self._fetch_order_after_cancel = fetch_order_after_cancel
        self._cancel_called = False
        self.create_order_result = None   # None => succeed; Exception => raise

    def create_market_order(self, symbol, side, qty, params=None):
        self.market_order_calls.append(
            {"symbol": symbol, "side": side, "qty": qty, "params": params}
        )
        return self.market_order_response

    def create_order(self, symbol, type, side, amount, params=None):
        self.stop_order_calls.append(
            {"symbol": symbol, "type": type, "side": side,
             "amount": amount, "params": params}
        )
        if isinstance(self.create_order_result, Exception):
            raise self.create_order_result
        return {"id": "STOP-ORDER-1"}

    def fetch_order(self, order_id, symbol, params=None):
        self.fetch_order_calls.append({"order_id": order_id, "symbol": symbol})
        if self._cancel_called and self._fetch_order_after_cancel is not None:
            resp = self._fetch_order_after_cancel
        elif self._fetch_order_responses:
            resp = self._fetch_order_responses.pop(0)
        else:
            raise AssertionError(
                f"fetch_order called more times than the test configured "
                f"responses for (order_id={order_id!r})"
            )
        if isinstance(resp, Exception):
            raise resp
        return resp

    def cancel_order(self, order_id, symbol, params=None):
        self.cancel_order_calls.append({"order_id": order_id, "symbol": symbol})
        self._cancel_called = True
        if isinstance(self._cancel_order_result, Exception):
            raise self._cancel_order_result
        return {"id": order_id, "status": "canceled"}


class FakeDB:
    """
    Deliberately has NO _conn() attribute — this routes
    TradeExecutor._persist_unresolved_markers() through its independent,
    symbol-first fallback path rather than the atomic-transaction path
    (that path is exercised separately, against a real sqlite Database, by
    test_atomic_transaction_prevents_partial_marker_state).

    fail_on_keys: optional set/predicate of bot_state keys whose set_state()
    call should raise, to test that one marker write failing doesn't take
    the other down with it.
    """

    def __init__(self, fail_on_keys=None):
        self.opened_trades = []
        self.order_id_updates = []
        self._state = {}
        self._fail_on_keys = fail_on_keys or set()

    def open_trade(self, trade):
        self.opened_trades.append(trade)

    def update_trade_order_ids(self, trade_id, stop_order_id=None, tp_order_id=None):
        self.order_id_updates.append(
            {"trade_id": trade_id, "stop_order_id": stop_order_id, "tp_order_id": tp_order_id}
        )

    def set_state(self, key, value):
        if key in self._fail_on_keys:
            raise RuntimeError(f"simulated set_state failure for key={key!r}")
        self._state[key] = value

    def get_state(self, key, default=None):
        return self._state.get(key, default)


class FakeRiskManager:
    """Returns a canned, always-approved TradeApproval."""

    def __init__(self, quantity, position_value, stop_loss, take_profit):
        self._approval = TradeApproval(
            approved=True,
            reason="ok",
            quantity=quantity,
            position_value=position_value,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=position_value * 0.02,
        )
        self.halt_calls = []

    def approve_trade(self, **kwargs):
        return self._approval

    def record_trade_result(self, *a, **kw):
        pass

    def manual_halt(self, reason):
        self.halt_calls.append(reason)


class FakeSessionDB:
    """
    Stands in for the module-level `db` imported inside core.risk_manager,
    so RiskManager.manual_halt()/is_trading_allowed()/approve_trade() can be
    exercised end-to-end WITHOUT ever touching the real data/trading_bot.db
    (which is the live bot's actual database — halting it for real would be
    a serious, unwanted side effect of running this test file).
    """

    def __init__(self):
        self._sessions = {}

    def get_session(self, session_date=None):
        from datetime import date as _date
        today = session_date or _date.today().isoformat()
        if today not in self._sessions:
            self._sessions[today] = {
                "session_date": today, "consecutive_losses": 0, "trades_today": 0,
                "pnl_today": 0.0, "trading_halted": 0, "halt_reason": None,
                "starting_capital_today": 0.0,
            }
        return self._sessions[today]

    def update_session(self, session_date, **kwargs):
        self.get_session(session_date).update(kwargs)

    # ── Minimal stubs so RiskManager._get_capital()/_get_or_lock_starting_
    # capital()/is_trading_allowed() can run end-to-end while NOT halted
    # (the pre-halt sanity check in the test below needs this path to work
    # too, not just the post-halt short-circuit).
    def get_all_closed_trades(self, limit=99999):
        return []

    def get_latest_capital(self):
        return None

    def record_capital_snapshot(self, total):
        pass

    def get_starting_capital_today(self):
        return 0.0

    def set_starting_capital_today(self, capital):
        pass

    def get_open_trades(self):
        return []


def make_signal(symbol, direction, current_price, indicators=None):
    return SimpleNamespace(
        symbol=symbol,
        direction=direction,
        asset_class="crypto",
        current_price=current_price,
        score=0.9,
        indicators=indicators or {},
    )


def build_executor(approval, kraken_exec, db=None):
    """Construct a TradeExecutor with everything except Kraken/DB/risk stubbed out."""
    db = db if db is not None else FakeDB()
    rm = FakeRiskManager(
        quantity=approval.quantity,
        position_value=approval.position_value,
        stop_loss=approval.stop_loss,
        take_profit=approval.take_profit,
    )
    executor = TradeExecutor(db_ref=db, risk_manager_ref=rm)
    executor.kraken = kraken_exec
    return executor, db


class Patch:
    """Minimal context manager to set/restore an attribute."""

    def __init__(self, obj, name, value):
        self.obj, self.name, self.value = obj, name, value

    def __enter__(self):
        self.had = hasattr(self.obj, self.name)
        self.old = getattr(self.obj, self.name, None)
        setattr(self.obj, self.name, self.value)
        return self

    def __exit__(self, *a):
        if self.had:
            setattr(self.obj, self.name, self.old)
        else:
            delattr(self.obj, self.name)


def scratch_log_path(name):
    return os.path.join(tempfile.gettempdir(), f"kraken_unresolved_test_{name}.log")


def run_case(fn):
    name = fn.__name__
    try:
        fn()
        print(f"PASS  {name}")
        return True
    except AssertionError as e:
        print(f"FAIL  {name}: {e}")
        return False
    except Exception as e:
        print(f"ERROR {name}: {type(e).__name__}: {e}")
        return False


# ── KrakenExecutor._confirmed_qty: direct unit check ────────────────────────

def test_confirmed_qty_never_falls_back_to_requested_qty():
    assert KrakenExecutor._confirmed_qty({"filled": 0}) == 0.0
    assert KrakenExecutor._confirmed_qty({"filled": None}) == 0.0
    assert KrakenExecutor._confirmed_qty({}) == 0.0
    assert KrakenExecutor._confirmed_qty(None) == 0.0
    assert KrakenExecutor._confirmed_qty({"filled": 3.25}) == 3.25


def test_kraken_paper_mode_unaffected():
    kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=True)
    kraken_exec.get_current_price = lambda symbol: 42.0
    result = kraken_exec.submit_order("BTC/USD", 3.0, "buy", 0, 0, leverage=0)
    assert result["filled_qty"] == 3.0
    assert result["filled_avg_price"] == 42.0
    assert result["resolution_failed"] is False


# ── KrakenExecutor.submit_order: order-lifecycle resolution ────────────────

def test_kraken_terminal_full_fill():
    fake = FakeExchange({"id": "O1", "status": "closed", "filled": 5.0, "average": 100.0})
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 5.0
    assert result["filled_avg_price"] == 100.0
    assert result["status"] == "closed"
    assert len(fake.fetch_order_calls) == 0, "already-terminal order must not poll"
    assert len(fake.cancel_order_calls) == 0


def test_kraken_terminal_partial_fill():
    fake = FakeExchange({"id": "O2", "status": "closed", "filled": 2.5, "average": 100.0})
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 2.5, "must record the real partial, not the requested 5.0"
    assert len(fake.fetch_order_calls) == 0


def test_kraken_terminal_zero_fill_rejected():
    fake = FakeExchange({"id": "O3", "status": "rejected", "filled": 0, "average": None})
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 0.0
    assert result["status"] == "rejected"
    assert len(fake.fetch_order_calls) == 0
    assert len(fake.cancel_order_calls) == 0


def test_kraken_open_zero_then_full_fill_during_polling():
    fake = FakeExchange(
        {"id": "O4", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[
            {"id": "O4", "status": "open", "filled": 0, "average": None},
            {"id": "O4", "status": "closed", "filled": 5.0, "average": 101.0},
        ],
    )
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                         fill_poll_attempts=5, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 5.0
    assert result["filled_avg_price"] == 101.0
    assert result["status"] == "closed"
    assert len(fake.fetch_order_calls) == 2, "should stop polling as soon as terminal"
    assert len(fake.cancel_order_calls) == 0, "never needed to cancel — it filled on its own"


def test_kraken_open_zero_then_cancel_confirms_zero():
    poll_attempts = 3
    fake = FakeExchange(
        {"id": "O5", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[{"id": "O5", "status": "open", "filled": 0, "average": None}] * poll_attempts,
        cancel_order_result=None,
        fetch_order_after_cancel={"id": "O5", "status": "canceled", "filled": 0, "average": None},
    )
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                         fill_poll_attempts=poll_attempts, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 0.0
    assert result["status"] == "canceled"
    assert len(fake.fetch_order_calls) == poll_attempts + 1, \
        "must poll the full budget, then do exactly one post-cancel fetch"
    assert len(fake.cancel_order_calls) == 1


def test_kraken_open_partial_then_cancel_confirms_partial():
    poll_attempts = 2
    fake = FakeExchange(
        {"id": "O6", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[
            {"id": "O6", "status": "open", "filled": 1.0, "average": 99.5},
            {"id": "O6", "status": "open", "filled": 1.0, "average": 99.5},
        ],
        cancel_order_result=None,
        fetch_order_after_cancel={"id": "O6", "status": "canceled", "filled": 1.0, "average": 99.5},
    )
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                         fill_poll_attempts=poll_attempts, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)  # requested 5, only 1 ever filled
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 1.0, "must protect exactly the confirmed remainder, not 0 and not 5"
    assert result["status"] == "canceled"
    assert len(fake.cancel_order_calls) == 1


def test_kraken_cancel_race_fill_increases():
    """cancel_order raises (order already filled) — the post-cancel fetch,
    not the polling snapshot or the cancel's own failure, is the source of
    truth, and it can show MORE filled than polling last observed."""
    fake = FakeExchange(
        {"id": "O7", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[
            {"id": "O7", "status": "open", "filled": 2.0, "average": 100.0},
        ],
        cancel_order_result=Exception("EOrder:Unknown order (already closed)"),
        fetch_order_after_cancel={"id": "O7", "status": "closed", "filled": 5.0, "average": 100.2},
    )
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                         fill_poll_attempts=1, fill_poll_interval_sec=0)
    ex.exchange = fake
    result = ex.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 5.0, "post-cancel fetch's higher cumulative fill must win"
    assert result["status"] == "closed"
    assert len(fake.cancel_order_calls) == 1


def test_kraken_unresolved_when_final_state_cannot_be_confirmed():
    # Sub-case A: cancel raises AND the mandatory post-cancel fetch also raises.
    log_a = scratch_log_path("a")
    if os.path.exists(log_a):
        os.remove(log_a)
    fake_a = FakeExchange(
        {"id": "O8A", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[{"id": "O8A", "status": "open", "filled": 0, "average": None}],
        cancel_order_result=Exception("network timeout"),
        fetch_order_after_cancel=Exception("network timeout"),
    )
    ex_a = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                           fill_poll_attempts=1, fill_poll_interval_sec=0)
    ex_a.exchange = fake_a
    ex_a._unresolved_log_path = log_a

    result_a = ex_a.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result_a["resolution_failed"] is True, "must fail closed, not guess zero or full"
    assert result_a["status"] == "unresolved"
    assert os.path.exists(log_a), "a durable reconciliation record must be written"
    with open(log_a) as f:
        rec = json.loads(f.readline())
    assert rec["order_id"] == "O8A"
    assert rec["symbol"] == "BTC/USD"
    os.remove(log_a)

    # Sub-case B: cancel succeeds, but the mandatory post-cancel fetch fails.
    log_b = scratch_log_path("b")
    if os.path.exists(log_b):
        os.remove(log_b)
    fake_b = FakeExchange(
        {"id": "O8B", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[{"id": "O8B", "status": "open", "filled": 0, "average": None}],
        cancel_order_result=None,
        fetch_order_after_cancel=Exception("network timeout"),
    )
    ex_b = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                           fill_poll_attempts=1, fill_poll_interval_sec=0)
    ex_b.exchange = fake_b
    ex_b._unresolved_log_path = log_b

    result_b = ex_b.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result_b["resolution_failed"] is True, \
        "a successful cancel does not by itself prove zero fill — fetch confirmation is mandatory"
    assert os.path.exists(log_b)
    os.remove(log_b)

    # Sub-case C: post-cancel fetch succeeds but still reports a non-terminal
    # status — ambiguous (cancel apparently didn't take), must also fail closed.
    fake_c = FakeExchange(
        {"id": "O8C", "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[{"id": "O8C", "status": "open", "filled": 0, "average": None}],
        cancel_order_result=None,
        fetch_order_after_cancel={"id": "O8C", "status": "open", "filled": 0.5, "average": 10.0},
    )
    ex_c = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                           fill_poll_attempts=1, fill_poll_interval_sec=0)
    ex_c.exchange = fake_c
    ex_c._unresolved_log_path = scratch_log_path("c")
    if os.path.exists(ex_c._unresolved_log_path):
        os.remove(ex_c._unresolved_log_path)

    result_c = ex_c.submit_order("BTC/USD", 5.0, "buy", 0, 0, leverage=0)
    assert result_c["resolution_failed"] is True
    os.remove(ex_c._unresolved_log_path)


# ── trade_executor.py integration: end-to-end through execute_signal() ─────

def test_A_live_leveraged_short_filled_qty_wins():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(config, "KRAKEN_SHORT_LEVERAGE", 2), \
         Patch(config, "KRAKEN_MAX_LEVERAGE", 10), \
         Patch(ec_mod.exchange_capabilities, "can_short", lambda symbol, broker: True), \
         Patch(ec_mod.exchange_capabilities, "get_max_short_leverage", lambda symbol, broker: 10), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 100.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=10.0, position_value=10.0 * entry_price,   # requested (unscaled)
            stop_loss=95.0, take_profit=110.0,
        )
        fake_exchange = FakeExchange({
            "id": "ORD-1", "status": "closed", "filled": 2.0, "average": 101.0,
        })
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("DOGE/USD", "short", entry_price)

        trade_id = executor.execute_signal(signal)

        assert trade_id is not None
        assert len(db.opened_trades) == 1
        rec = db.opened_trades[0]

        sent_qty = fake_exchange.market_order_calls[0]["qty"]
        assert abs(sent_qty - 2.0) < 1e-9, f"expected submitted qty=2.0, got {sent_qty}"
        assert abs(rec["quantity"] - 2.0) < 1e-9, \
            f"DB quantity must be 2.0 (confirmed fill), got {rec['quantity']}"

        expected_pv = round(2.0 * 101.0, 4)
        assert abs(rec["position_value"] - expected_pv) < 1e-6
        assert rec["position_value"] != approval.position_value

        stop_qty = fake_exchange.stop_order_calls[0]["amount"]
        assert abs(stop_qty - 2.0) < 1e-9


def test_B_live_long_uses_confirmed_fill():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 50.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=5.0, position_value=5.0 * entry_price,
            stop_loss=47.5, take_profit=55.0,
        )
        fake_exchange = FakeExchange({
            "id": "ORD-2", "status": "closed", "filled": 5.0, "average": 50.25,
        })
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("ETH/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)
        assert trade_id is not None
        rec = db.opened_trades[0]

        assert abs(rec["quantity"] - 5.0) < 1e-9
        expected_pv = round(5.0 * 50.25, 4)
        assert abs(rec["position_value"] - expected_pv) < 1e-6

        stop_qty = fake_exchange.stop_order_calls[0]["amount"]
        assert abs(stop_qty - 5.0) < 1e-9


def test_open_partial_then_cancel_records_confirmed_partial():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 10.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=8.0, position_value=8.0 * entry_price,
            stop_loss=9.5, take_profit=11.0,
        )
        fake_exchange = FakeExchange(
            {"id": "OD1", "status": "open", "filled": 0, "average": None},
            fetch_order_responses=[{"id": "OD1", "status": "open", "filled": 3.5, "average": 10.1}],
            cancel_order_result=None,
            fetch_order_after_cancel={"id": "OD1", "status": "canceled", "filled": 3.5, "average": 10.1},
        )
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_attempts=1, fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("AVAX/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)
        assert trade_id is not None, "a positive confirmed partial is a real position — must be tracked"
        rec = db.opened_trades[0]

        assert abs(rec["quantity"] - 3.5) < 1e-9
        assert rec["quantity"] != approval.quantity

        stop_qty = fake_exchange.stop_order_calls[0]["amount"]
        assert abs(stop_qty - 3.5) < 1e-9
        assert len(fake_exchange.cancel_order_calls) == 1


def _make_unresolved_kraken_exec(order_id="OE1", cancel_exc=None, fetch_after_cancel_exc=None,
                                 unresolved_log_path=None):
    """Kraken executor rigged so the order stays open, polling exhausts, and
    the final state cannot be confirmed (cancel and/or post-cancel fetch fail)."""
    if cancel_exc is None:
        cancel_exc = Exception("timeout")
    if fetch_after_cancel_exc is None:
        fetch_after_cancel_exc = Exception("timeout")
    fake_exchange = FakeExchange(
        {"id": order_id, "status": "open", "filled": 0, "average": None},
        fetch_order_responses=[{"id": order_id, "status": "open", "filled": 0, "average": None}],
        cancel_order_result=cancel_exc,
        fetch_order_after_cancel=fetch_after_cancel_exc,
    )
    kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                  fill_poll_attempts=1, fill_poll_interval_sec=0)
    kraken_exec.exchange = fake_exchange
    if unresolved_log_path is not None:
        kraken_exec._unresolved_log_path = unresolved_log_path
    return kraken_exec, fake_exchange


# ── Requirement 1: unresolved zero-known-fill globally halts + writes DB state ──

def test_unresolved_zero_fill_halts_trading_and_writes_db_state():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 15.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=4.0, position_value=4.0 * entry_price,
            stop_loss=14.0, take_profit=16.5,
        )
        log_path = scratch_log_path("integration_zero")
        if os.path.exists(log_path):
            os.remove(log_path)
        kraken_exec, fake_exchange = _make_unresolved_kraken_exec(
            order_id="OE1", unresolved_log_path=log_path
        )

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("MATIC/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)

        assert trade_id is None, "unresolved final state must never open a normal DB trade"
        assert len(db.opened_trades) == 0, "zero confirmed fill -> no provisional trade either"
        assert len(fake_exchange.stop_order_calls) == 0, "must never place a stop for an unconfirmed/zero fill"

        # DB state marker (the real state store, not just the JSONL log)
        order_marker = db.get_state("kraken_unresolved_order_OE1")
        assert order_marker is not None
        assert order_marker["symbol"] == "MATIC/USD"
        assert order_marker["last_known_filled_qty"] == 0.0
        assert order_marker["reconciliation_required"] is True

        symbol_marker = db.get_state("kraken_unresolved_symbol_MATIC/USD")
        assert symbol_marker is not None
        assert symbol_marker["order_id"] == "OE1"

        # Global halt invoked, with symbol + order ID in the reason
        assert len(executor._risk_manager.halt_calls) == 1
        reason = executor._risk_manager.halt_calls[0]
        assert "MATIC/USD" in reason
        assert "OE1" in reason

        assert os.path.exists(log_path), "the JSONL record is still written as supplementary evidence"
        os.remove(log_path)


# ── Requirement 2: unresolved positive-known-fill is tracked and protected ──

def test_unresolved_positive_fill_creates_provisional_trade_and_stop():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 20.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=6.0, position_value=6.0 * entry_price,
            stop_loss=19.0, take_profit=22.0,
        )
        log_path = scratch_log_path("integration_partial")
        if os.path.exists(log_path):
            os.remove(log_path)

        # Polling shows a confirmed partial fill (2.5), then cancel + the
        # mandatory post-cancel fetch BOTH fail -> resolution_failed=True
        # with a positive last-known confirmed quantity.
        fake_exchange = FakeExchange(
            {"id": "OP1", "status": "open", "filled": 0, "average": None},
            fetch_order_responses=[{"id": "OP1", "status": "open", "filled": 2.5, "average": 20.2}],
            cancel_order_result=Exception("timeout"),
            fetch_order_after_cancel=Exception("timeout"),
        )
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_attempts=1, fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange
        kraken_exec._unresolved_log_path = log_path

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("XRP/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)

        assert trade_id is None, "still not a normal successful signal outcome"
        assert len(db.opened_trades) == 1, "the confirmed partial must be tracked, not discarded"
        rec = db.opened_trades[0]

        assert abs(rec["quantity"] - 2.5) < 1e-9, \
            f"provisional trade must cover exactly the confirmed 2.5, got {rec['quantity']}"
        assert rec["trade_id"].startswith("UNRESOLVED-"), "must be clearly marked, not a normal trade"
        assert rec["indicators"]["kraken_provisional_unresolved"] is True
        assert rec["indicators"]["kraken_unresolved_order_id"] == "OP1"

        # Emergency stop placed for exactly the confirmed quantity — never more.
        assert len(fake_exchange.stop_order_calls) == 1
        stop_qty = fake_exchange.stop_order_calls[0]["amount"]
        assert abs(stop_qty - 2.5) < 1e-9, \
            f"emergency stop must cover exactly 2.5 (confirmed), got {stop_qty}"

        assert len(db.order_id_updates) == 1
        assert db.order_id_updates[0]["trade_id"] == rec["trade_id"]

        assert len(executor._risk_manager.halt_calls) == 1
        assert "XRP/USD" in executor._risk_manager.halt_calls[0]
        os.remove(log_path)


# ── Requirement 3: subsequent approval attempts are rejected while halted ──

def test_global_halt_blocks_subsequent_approve_trade():
    fake_session_db = FakeSessionDB()
    with Patch(rm_mod, "db", fake_session_db), \
         Patch(rm_mod.alert_manager, "trading_halted", lambda reason: None):
        fresh_rm = rm_mod.RiskManager()

        allowed_before, _ = fresh_rm.is_trading_allowed()
        assert allowed_before is True, "sanity: not halted before manual_halt()"

        fresh_rm.manual_halt(
            "Kraken order unresolved for BTC/USD (order_id=O9): manual "
            "reconciliation required before trading can resume."
        )

        allowed_after, reason = fresh_rm.is_trading_allowed()
        assert allowed_after is False
        assert "unresolved" in reason.lower() or "reconciliation" in reason.lower()

        approval = fresh_rm.approve_trade(
            symbol="ETH/USD", entry_price=100.0, signal_score=0.99, direction="long"
        )
        assert approval.approved is False, \
            "a completely unrelated symbol must also be rejected while globally halted"
        assert "unresolved" in approval.reason.lower() or "reconciliation" in approval.reason.lower() \
            or "halt" in approval.reason.lower()


# ── Requirement 4: no second entry for the affected symbol while unresolved ──

def test_no_second_entry_for_symbol_while_unresolved_marker_exists():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 30.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=2.0, position_value=2.0 * entry_price,
            stop_loss=28.0, take_profit=33.0,
        )
        log_path = scratch_log_path("integration_symbol_block")
        if os.path.exists(log_path):
            os.remove(log_path)
        kraken_exec, fake_exchange = _make_unresolved_kraken_exec(
            order_id="OS1", unresolved_log_path=log_path
        )

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("LINK/USD", "long", entry_price)

        first_result = executor.execute_signal(signal)
        assert first_result is None
        assert db.get_state("kraken_unresolved_symbol_LINK/USD") is not None
        os.remove(log_path)

        # Second attempt for the SAME symbol, with a broker that would
        # otherwise succeed cleanly — must be blocked before ever touching
        # the exchange.
        fake_exchange_2 = FakeExchange({"id": "OS2", "status": "closed", "filled": 2.0, "average": 30.1})
        kraken_exec_2 = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                        fill_poll_interval_sec=0)
        kraken_exec_2.exchange = fake_exchange_2
        executor.kraken = kraken_exec_2

        second_signal = make_signal("LINK/USD", "long", entry_price)
        second_result = executor.execute_signal(second_signal)

        assert second_result is None, "must be blocked while the symbol marker is present"
        assert len(fake_exchange_2.market_order_calls) == 0, \
            "must never even submit an order for a blocked symbol"
        assert len(db.opened_trades) == 0


# ── Requirement 5: JSONL-write failure must not block the DB halt/marker ──

def test_jsonl_write_failure_does_not_block_db_halt_or_marker():
    blocker_file = os.path.join(tempfile.gettempdir(), "kraken_unresolved_blocker_file.tmp")
    with open(blocker_file, "w") as f:
        f.write("x")
    try:
        # blocker_file is a FILE, so treating it as a directory component
        # makes os.makedirs() (inside _record_unresolved_order) fail.
        bad_log_path = os.path.join(blocker_file, "sub", "kraken_unresolved.log")

        with Patch(config, "KRAKEN_ENABLED", True), \
             Patch(config, "KRAKEN_PAPER_MODE", False), \
             Patch(bm_mod.broker_manager, "get_broker_balance",
                   lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
             Patch(bm_mod.broker_manager, "update_broker_balance",
                   lambda *a, **kw: None):

            entry_price = 12.0
            approval = TradeApproval(
                approved=True, reason="ok",
                quantity=3.0, position_value=3.0 * entry_price,
                stop_loss=11.0, take_profit=13.0,
            )
            kraken_exec, fake_exchange = _make_unresolved_kraken_exec(
                order_id="OJ1", unresolved_log_path=bad_log_path
            )

            executor, db = build_executor(approval, kraken_exec)
            signal = make_signal("LTC/USD", "long", entry_price)

            trade_id = executor.execute_signal(signal)

            assert trade_id is None
            assert len(executor._risk_manager.halt_calls) == 1, \
                "halt must still fire even though the JSONL write failed"
            marker = db.get_state("kraken_unresolved_symbol_LTC/USD")
            assert marker is not None, \
                "DB marker must still be written even though the JSONL write failed"
            assert not os.path.exists(bad_log_path), "the JSONL write should have failed, as rigged"
    finally:
        os.remove(blocker_file)


# ── Requirement 6: normal terminal fills do not halt trading ──

def test_normal_terminal_fill_does_not_halt_trading():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 8.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=10.0, position_value=10.0 * entry_price,
            stop_loss=7.6, take_profit=8.8,
        )
        fake_exchange = FakeExchange({"id": "ON1", "status": "closed", "filled": 10.0, "average": 8.05})
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("ADA/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)

        assert trade_id is not None
        assert len(executor._risk_manager.halt_calls) == 0, \
            "a normal, cleanly-resolved terminal fill must never trigger a halt"
        assert db.get_state("kraken_unresolved_symbol_ADA/USD") is None


def test_E_paper_mode_sizing_unchanged():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", True), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 200.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=1.5, position_value=1.5 * entry_price,
            stop_loss=190.0, take_profit=220.0,
        )
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=True)
        kraken_exec.get_current_price = lambda symbol: entry_price

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("BTC/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)
        assert trade_id is not None
        rec = db.opened_trades[0]

        assert abs(rec["quantity"] - approval.quantity) < 1e-9
        assert abs(rec["position_value"] - approval.position_value) < 1e-6


def test_broker_balance_uses_open_position_value():
    calls = []

    def fake_update(broker_name, balance, invested, available):
        calls.append({"broker_name": broker_name, "balance": balance,
                      "invested": invested, "available": available})

    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(config, "KRAKEN_SHORT_LEVERAGE", 2), \
         Patch(config, "KRAKEN_MAX_LEVERAGE", 10), \
         Patch(ec_mod.exchange_capabilities, "can_short", lambda symbol, broker: True), \
         Patch(ec_mod.exchange_capabilities, "get_max_short_leverage", lambda symbol, broker: 10), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance", fake_update):

        entry_price = 100.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=10.0, position_value=1000.0,   # unscaled approved notional
            stop_loss=95.0, take_profit=110.0,
        )
        fake_exchange = FakeExchange({
            "id": "OB1", "status": "closed", "filled": 2.0, "average": 100.0,
        })
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("DOGE/USD", "short", entry_price)
        trade_id = executor.execute_signal(signal)

        assert trade_id is not None
        assert len(calls) == 1, "broker balance must be updated exactly once on open"
        call = calls[0]
        # confirmed fill = 2.0 @ 100.0 -> open_position_value = 200.0,
        # NOT the unscaled approval.position_value of 1000.0
        assert abs(call["invested"] - 200.0) < 1e-6, call
        assert abs(call["available"] - (10000.0 - 200.0)) < 1e-6, call


# ── Marker persistence: symbol-first priority, independent writes ──────────

def test_symbol_marker_persisted_first_survives_order_marker_failure():
    """If the order-ID marker write fails, the symbol marker (the one that
    actually blocks new entries) must already be safely written — it must
    never depend on the order-ID write succeeding first."""
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 18.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=2.0, position_value=2.0 * entry_price,
            stop_loss=17.0, take_profit=19.5,
        )
        log_path = scratch_log_path("symbol_first_marker")
        if os.path.exists(log_path):
            os.remove(log_path)
        kraken_exec, fake_exchange = _make_unresolved_kraken_exec(
            order_id="OM1", unresolved_log_path=log_path
        )

        # FakeDB has no _conn(), so this exercises the independent-writes
        # fallback specifically. Only the order-key write fails.
        db = FakeDB(fail_on_keys={"kraken_unresolved_order_OM1"})
        executor, _ = build_executor(approval, kraken_exec, db=db)
        signal = make_signal("DOT/USD", "long", entry_price)

        trade_id = executor.execute_signal(signal)
        if os.path.exists(log_path):
            os.remove(log_path)
        assert trade_id is None

        symbol_marker = db.get_state("kraken_unresolved_symbol_DOT/USD")
        assert symbol_marker is not None, \
            "symbol marker must be written first and independently of the order-key write"
        assert db.get_state("kraken_unresolved_order_OM1") is None, \
            "sanity: the injected failure really did block the order-key write"

        # The safety property that matters: a second attempt for this symbol
        # is still blocked even though the order-key marker never landed.
        fake_exchange_2 = FakeExchange({"id": "OM2", "status": "closed", "filled": 2.0, "average": 18.1})
        kraken_exec_2 = KrakenExecutor(api_key="x", api_secret="y", paper=False, fill_poll_interval_sec=0)
        kraken_exec_2.exchange = fake_exchange_2
        executor.kraken = kraken_exec_2

        second_result = executor.execute_signal(make_signal("DOT/USD", "long", entry_price))
        assert second_result is None, "symbol must remain blocked despite the order-key write failure"
        assert len(fake_exchange_2.market_order_calls) == 0

        # And the global halt still fired regardless of the partial marker failure.
        assert len(executor._risk_manager.halt_calls) == 1


def test_atomic_transaction_prevents_partial_marker_state():
    """
    Against a REAL sqlite-backed Database (isolated temp file, never the
    live bot DB): if the order-key write inside the single marker
    transaction fails, the WHOLE transaction must roll back — the symbol-key
    write must not be left committed from a failed transaction. The
    subsequent independent-writes fallback then recovers the symbol marker
    on its own (separate transaction), while the order marker — which fails
    unconditionally in this test — never lands.
    """
    import data.database as db_mod
    import sqlite3
    import contextlib

    tmp_db_path = os.path.join(tempfile.gettempdir(), f"kraken_marker_atomic_test_{os.getpid()}.db")
    for ext in ("", "-shm", "-wal"):
        p = tmp_db_path + ext
        if os.path.exists(p):
            os.remove(p)

    real_db = db_mod.Database(db_path=tmp_db_path)
    order_key_marker = "kraken_unresolved_order_OA1"

    class _ExecuteInterceptor:
        """
        sqlite3.Connection's `execute` attribute is read-only (C extension
        object) — can't monkeypatch it directly. Proxy instead: intercept
        only `execute`, delegate everything else to the real connection.
        """
        def __init__(self, real_conn, blocked_first_param):
            self._real = real_conn
            self._blocked = blocked_first_param

        def execute(self, sql, params=()):
            # Fail ONLY the INSERT that targets the order-key row, in every
            # transaction (both the atomic attempt and the fallback retry).
            # Reads (get_state's SELECT, used both by production code and by
            # this test's own post-hoc assertions) must never be blocked.
            if (sql.strip().upper().startswith("INSERT")
                    and params and params[0] == self._blocked):
                raise sqlite3.OperationalError("simulated failure writing order marker")
            return self._real.execute(sql, params)

        def __getattr__(self, name):
            return getattr(self._real, name)

    @contextlib.contextmanager
    def failing_conn_cm():
        conn = sqlite3.connect(tmp_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        wrapper = _ExecuteInterceptor(conn, order_key_marker)
        try:
            yield wrapper
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    real_db._conn = failing_conn_cm

    try:
        with Patch(config, "KRAKEN_ENABLED", True), \
             Patch(config, "KRAKEN_PAPER_MODE", False):
            approval = TradeApproval(
                approved=True, reason="ok", quantity=1.0, position_value=10.0,
                stop_loss=9.0, take_profit=11.0,
            )
            _atomic_test_log_path = scratch_log_path("atomic_marker_test")
            if os.path.exists(_atomic_test_log_path):
                os.remove(_atomic_test_log_path)
            kraken_exec, fake_exchange = _make_unresolved_kraken_exec(
                order_id="OA1", unresolved_log_path=_atomic_test_log_path
            )
            rm = FakeRiskManager(quantity=1.0, position_value=10.0, stop_loss=9.0, take_profit=11.0)
            executor = TradeExecutor(db_ref=real_db, risk_manager_ref=rm)
            executor.kraken = kraken_exec

            signal = make_signal("ALGO/USD", "long", 10.0)
            trade_id = executor.execute_signal(signal)
            if os.path.exists(_atomic_test_log_path):
                os.remove(_atomic_test_log_path)
            assert trade_id is None

        # The order marker permanently fails to write (atomic AND fallback).
        assert real_db.get_state(order_key_marker) is None

        # The symbol marker must still end up present: the failed atomic
        # transaction rolled back cleanly (didn't leave a dangling partial
        # write), and the independent fallback then wrote it successfully
        # on its own.
        assert real_db.get_state("kraken_unresolved_symbol_ALGO/USD") is not None
    finally:
        # Best-effort: on Windows, WAL-mode sqlite can transiently hold the
        # file handle a moment after the last connection closes. Cleanup
        # failing here must never fail the test — the assertions above have
        # already run by this point.
        for ext in ("", "-shm", "-wal"):
            p = tmp_db_path + ext
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


# ── Idempotency: handling the same unresolved order ID twice ───────────────

def test_handle_unresolved_kraken_order_is_idempotent_for_same_order_id():
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False):
        approval = TradeApproval(
            approved=True, reason="ok", quantity=4.0, position_value=80.0,
            stop_loss=19.0, take_profit=22.0,
        )
        kraken_exec, fake_exchange = _make_unresolved_kraken_exec(order_id="OI1")
        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("NEAR/USD", "long", 20.0)

        broker_result = {
            "broker_order_id": "OI1", "status": "open",
            "filled_qty": 2.5, "filled_avg_price": 20.1,
            "resolution_failed": True, "leverage": 0,
        }

        executor._handle_unresolved_kraken_order(signal, approval, broker_result)
        executor._handle_unresolved_kraken_order(signal, approval, broker_result)

        assert len(db.opened_trades) == 1, \
            "a second call for the SAME order ID must not open a second provisional trade"
        assert len(fake_exchange.stop_order_calls) == 1, \
            "a second call for the SAME order ID must not place a second emergency stop"
        assert len(executor._risk_manager.halt_calls) == 2, \
            "halt is safe/idempotent to re-assert, unlike the trade/stop side effects"


# ── Leveraged-short stop semantics: exact create_order params ──────────────

def test_place_stop_order_spot_long_no_margin_params():
    """(a) spot-long stop: no leverage/reduceOnly params — Kraken rejects
    margin-only params on spot orders."""
    fake = FakeExchange(None)
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False)
    ex.exchange = fake
    order_id = ex.place_stop_order("BTC/USD", 1.5, "sell", 45000.0, leverage=0)
    assert order_id == "STOP-ORDER-1"
    assert len(fake.stop_order_calls) == 1
    call = fake.stop_order_calls[0]
    assert call["type"] == "market"
    assert call["params"] == {"stopLossPrice": 45000.0}
    assert "leverage" not in call["params"]
    assert "reduceOnly" not in call["params"]


def test_place_stop_order_leveraged_short_includes_leverage_and_reduce_only():
    """(b) leveraged-short stop: must carry both leverage AND reduceOnly so
    Kraken reduces the existing margin position rather than opening a new
    (or opposite) one."""
    fake = FakeExchange(None)
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False)
    ex.exchange = fake
    order_id = ex.place_stop_order("ETH/USD", 0.4, "buy", 2600.0, leverage=2)
    assert order_id == "STOP-ORDER-1"
    call = fake.stop_order_calls[0]
    assert call["type"] == "market"
    assert call["params"]["stopLossPrice"] == 2600.0
    assert call["params"]["leverage"] == 2
    assert call["params"]["reduceOnly"] is True


def test_update_stop_order_leveraged_short_preserves_leverage():
    """(d) replacement stop for a leveraged short: the cancel+replace cycle
    must carry the same leverage/reduceOnly as the original entry stop."""
    fake = FakeExchange(None)
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False)
    ex.exchange = fake
    new_id = ex.update_stop_order("ETH/USD", "OLD-STOP-1", 0.4, "buy", 2550.0, leverage=2)
    assert new_id == "STOP-ORDER-1"
    assert len(fake.cancel_order_calls) == 1
    assert fake.cancel_order_calls[0]["order_id"] == "OLD-STOP-1"
    call = fake.stop_order_calls[0]
    assert call["params"]["leverage"] == 2
    assert call["params"]["reduceOnly"] is True


def test_place_stop_order_rejection_with_margin_params_handled_safely():
    """(e) Kraken/ccxt rejects the leveraged/reduceOnly order (e.g. margin
    unavailable for this pair) — must fail safely (None), not raise, and
    must never fall back to a spot-style order without those params (that
    would silently drop the reduce-only protection)."""
    fake = FakeExchange(None)
    fake.create_order_result = Exception("EOrder:Insufficient margin")
    ex = KrakenExecutor(api_key="x", api_secret="y", paper=False)
    ex.exchange = fake
    order_id = ex.place_stop_order("ETH/USD", 0.4, "buy", 2600.0, leverage=2)
    assert order_id is None
    assert len(fake.stop_order_calls) == 1, "exactly one attempt — no silent spot-style retry"
    assert fake.stop_order_calls[0]["params"]["reduceOnly"] is True


def test_unresolved_leveraged_short_provisional_stop_preserves_leverage():
    """(c) provisional unresolved leveraged-short stop: the emergency stop
    placed for a confirmed partial fill on a leveraged short must carry the
    same leverage/reduceOnly semantics as a normal entry stop would."""
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(bm_mod.broker_manager, "get_broker_balance",
               lambda name: {"balance": 10000.0, "invested": 0.0, "available": 10000.0}), \
         Patch(bm_mod.broker_manager, "update_broker_balance",
               lambda *a, **kw: None):

        entry_price = 40.0
        approval = TradeApproval(
            approved=True, reason="ok",
            quantity=10.0, position_value=10.0 * entry_price,
            stop_loss=42.0, take_profit=36.0,
        )
        # Confirmed partial (1.0) on a leveraged (3x) short, then cancel and
        # the mandatory post-cancel fetch both fail -> resolution_failed.
        fake_exchange = FakeExchange(
            {"id": "OL1", "status": "open", "filled": 0, "average": None},
            fetch_order_responses=[{"id": "OL1", "status": "open", "filled": 1.0, "average": 40.2}],
            cancel_order_result=Exception("timeout"),
            fetch_order_after_cancel=Exception("timeout"),
        )
        kraken_exec = KrakenExecutor(api_key="x", api_secret="y", paper=False,
                                      fill_poll_attempts=1, fill_poll_interval_sec=0)
        kraken_exec.exchange = fake_exchange
        log_path = scratch_log_path("leveraged_short_provisional")
        if os.path.exists(log_path):
            os.remove(log_path)
        kraken_exec._unresolved_log_path = log_path

        executor, db = build_executor(approval, kraken_exec)
        signal = make_signal("LTC/USD", "short", entry_price)

        # _submit() is what normally computes/threads leverage through for a
        # live short — drive execute_signal() for real rather than calling
        # _handle_unresolved_kraken_order() directly, so this test proves
        # the leverage value actually flows end-to-end from _submit()'s
        # scaling decision through to the emergency stop.
        with Patch(config, "KRAKEN_SHORT_LEVERAGE", 3), \
             Patch(config, "KRAKEN_MAX_LEVERAGE", 10), \
             Patch(ec_mod.exchange_capabilities, "can_short", lambda symbol, broker: True), \
             Patch(ec_mod.exchange_capabilities, "get_max_short_leverage", lambda symbol, broker: 10):
            trade_id = executor.execute_signal(signal)

        if os.path.exists(log_path):
            os.remove(log_path)

        assert trade_id is None
        assert len(db.opened_trades) == 1
        rec = db.opened_trades[0]
        assert rec["indicators"]["kraken_leverage"] == 3

        assert len(fake_exchange.stop_order_calls) == 1
        stop_call = fake_exchange.stop_order_calls[0]
        assert abs(stop_call["amount"] - 1.0) < 1e-9, "stop must cover exactly the confirmed 1.0"
        assert stop_call["params"]["leverage"] == 3
        assert stop_call["params"]["reduceOnly"] is True


# ── data/database.py schema: stop_order_id / tp_order_id columns ───────────

def test_update_trade_order_ids_persists_stop_and_tp_ids():
    """
    trades.stop_order_id / trades.tp_order_id are referenced by
    update_trade_order_ids() but were missing from both the base CREATE
    TABLE and every ALTER TABLE migration — meaning any fresh database
    (this test's brand-new temp DB included) would fail with
    "no such column: stop_order_id" the moment a Kraken stop order was
    recorded against it. Proves the columns now exist on a fresh DB and
    round-trip correctly.
    """
    import data.database as db_mod

    tmp_db_path = os.path.join(
        tempfile.gettempdir(), f"trades_order_ids_schema_test_{os.getpid()}.db"
    )
    for ext in ("", "-shm", "-wal"):
        p = tmp_db_path + ext
        if os.path.exists(p):
            os.remove(p)

    try:
        real_db = db_mod.Database(db_path=tmp_db_path)

        trade = {
            "trade_id":        "SCHEMA-TEST-1",
            "symbol":          "BTC/USD",
            "asset_class":     "crypto",
            "direction":       "long",
            "entry_time":      "2026-07-12T00:00:00",
            "entry_price":     100.0,
            "quantity":        1.0,
            "position_value":  100.0,
            "stop_loss":       95.0,
            "take_profit":     110.0,
            "signal_score":    0.9,
            "indicators":      {},
            "broker":          "kraken",
            "strategy_name":   "original",
            "entry_timeframe": "5m",
        }
        real_db.open_trade(trade)
        real_db.update_trade_order_ids(
            "SCHEMA-TEST-1", stop_order_id="STOP-123", tp_order_id="TP-456"
        )

        open_trades = real_db.get_open_trades()
        rec = next(t for t in open_trades if t["trade_id"] == "SCHEMA-TEST-1")
        assert rec["stop_order_id"] == "STOP-123"
        assert rec["tp_order_id"] == "TP-456"
    finally:
        for ext in ("", "-shm", "-wal"):
            p = tmp_db_path + ext
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


if __name__ == "__main__":
    cases = [
        test_confirmed_qty_never_falls_back_to_requested_qty,
        test_kraken_paper_mode_unaffected,
        test_kraken_terminal_full_fill,
        test_kraken_terminal_partial_fill,
        test_kraken_terminal_zero_fill_rejected,
        test_kraken_open_zero_then_full_fill_during_polling,
        test_kraken_open_zero_then_cancel_confirms_zero,
        test_kraken_open_partial_then_cancel_confirms_partial,
        test_kraken_cancel_race_fill_increases,
        test_kraken_unresolved_when_final_state_cannot_be_confirmed,
        test_A_live_leveraged_short_filled_qty_wins,
        test_B_live_long_uses_confirmed_fill,
        test_open_partial_then_cancel_records_confirmed_partial,
        test_E_paper_mode_sizing_unchanged,
        test_broker_balance_uses_open_position_value,
        test_unresolved_zero_fill_halts_trading_and_writes_db_state,
        test_unresolved_positive_fill_creates_provisional_trade_and_stop,
        test_global_halt_blocks_subsequent_approve_trade,
        test_no_second_entry_for_symbol_while_unresolved_marker_exists,
        test_jsonl_write_failure_does_not_block_db_halt_or_marker,
        test_normal_terminal_fill_does_not_halt_trading,
        test_symbol_marker_persisted_first_survives_order_marker_failure,
        test_atomic_transaction_prevents_partial_marker_state,
        test_handle_unresolved_kraken_order_is_idempotent_for_same_order_id,
        test_place_stop_order_spot_long_no_margin_params,
        test_place_stop_order_leveraged_short_includes_leverage_and_reduce_only,
        test_update_stop_order_leveraged_short_preserves_leverage,
        test_place_stop_order_rejection_with_margin_params_handled_safely,
        test_unresolved_leveraged_short_provisional_stop_preserves_leverage,
        test_update_trade_order_ids_persists_stop_and_tp_ids,
    ]
    results = [run_case(c) for c in cases]
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)
