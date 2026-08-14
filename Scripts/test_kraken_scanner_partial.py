"""
Deterministic acceptance tests for the fail-closed Kraken scanner-partial path.

No network calls, production database access, or real broker orders occur.
All broker behavior is provided by FakeExchange and every database is created
inside a disposable temporary directory.
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_TEMP_ROOT = tempfile.TemporaryDirectory(prefix="kraken-partial-tests-")

import config

config.DB_PATH = os.path.join(_TEMP_ROOT.name, "module-import.db")
config.IBKR_ENABLED = False
config.KRAKEN_ENABLED = True
config.KRAKEN_PAPER_MODE = True
config.ALPACA_API_KEY = ""
config.ALPACA_SECRET_KEY = ""

from core.kraken_executor import KrakenExecutor
from core.position_monitor import PositionMonitor
from core.trade_executor import PartialCloseOutcome, TradeExecutor
from data.database import Database


class FakeExchange:
    def __init__(
        self,
        open_orders=None,
        market_response=None,
        open_orders_error=None,
        cancel_fail_ids=None,
        post_cancel_fetch=None,
    ):
        self.open_orders = open_orders or {}
        self.market_response = market_response or {
            "id": "CLOSE-1",
            "status": "closed",
            "filled": 0.0,
            "average": 0.0,
        }
        self.open_orders_error = open_orders_error
        self.cancel_fail_ids = set(cancel_fail_ids or [])
        self.post_cancel_fetch = post_cancel_fetch
        self.cancel_calls = []
        self.market_calls = []
        self.fetch_calls = []
        self.stop_calls = []

    def privatePostOpenorders(self, _params):
        if self.open_orders_error:
            raise self.open_orders_error
        return {"result": {"open": self.open_orders}}

    def cancelOrder(self, order_id):
        self.cancel_calls.append(order_id)
        if order_id in self.cancel_fail_ids:
            raise RuntimeError(f"cancel failed for {order_id}")
        return {"id": order_id, "status": "canceled"}

    def create_market_order(self, symbol, side, qty, params=None):
        self.market_calls.append(
            {"symbol": symbol, "side": side, "qty": qty, "params": params or {}}
        )
        if isinstance(self.market_response, Exception):
            raise self.market_response
        return dict(self.market_response)

    def cancel_order(self, order_id, symbol, params=None):
        self.cancel_calls.append(("market", order_id, symbol))
        return {"id": order_id, "status": "canceled"}

    def fetch_order(self, order_id, symbol, params=None):
        self.fetch_calls.append((order_id, symbol))
        if isinstance(self.post_cancel_fetch, Exception):
            raise self.post_cancel_fetch
        if self.post_cancel_fetch is None:
            raise AssertionError("unexpected fetch_order call")
        return dict(self.post_cancel_fetch)

    def create_order(self, symbol, type, side, amount, price=None, params=None):
        self.stop_calls.append(
            {
                "symbol": symbol,
                "type": type,
                "side": side,
                "amount": amount,
                "price": price,
                "params": params or {},
            }
        )
        return {"id": f"STOP-{len(self.stop_calls)}"}


class FakeRiskManager:
    def __init__(self):
        self.halts = []

    def manual_halt(self, reason):
        self.halts.append(reason)


class FakeBrokerManager:
    def __init__(self):
        self.balance = {
            "balance": 100_000.0,
            "available": 99_000.0,
            "invested": 1_000.0,
        }
        self.updates = []

    def get_broker_balance(self, _broker):
        return dict(self.balance)

    def update_broker_balance(self, broker, balance, invested, available):
        self.updates.append((broker, balance, invested, available))


def make_kraken(exchange):
    executor = KrakenExecutor.__new__(KrakenExecutor)
    executor.paper = False
    executor.exchange = exchange
    executor.fill_poll_attempts = 0
    executor.fill_poll_interval_sec = 0
    executor._unresolved_log_path = os.path.join(
        _TEMP_ROOT.name, "kraken_unresolved_orders.log"
    )
    return executor


def make_database(name):
    return Database(os.path.join(_TEMP_ROOT.name, f"{name}.db"))


def seed_trade(database, trade_id="T-1", symbol="ETH/USD", qty=10.0):
    database.log_capital(
        total=100_000.0,
        available=99_000.0,
        invested=1_000.0,
        daily_pnl=0.0,
        total_pnl=0.0,
        note="test seed",
    )
    database.open_trade(
        {
            "trade_id": trade_id,
            "symbol": symbol,
            "asset_class": "crypto",
            "direction": "long",
            "entry_time": "2026-07-26T08:00:00",
            "entry_price": 100.0,
            "quantity": qty,
            "position_value": qty * 100.0,
            "stop_loss": 95.0,
            "take_profit": 120.0,
            "signal_score": 90,
            "indicators": {
                "strategy_name": "breakout_scanner",
                "kraken_leverage": 0,
            },
            "broker": "kraken",
            "broker_order_id": "ENTRY-1",
            "strategy_name": "breakout_scanner",
            "entry_timeframe": "1Min",
        }
    )
    trade = database.get_open_trades()[0]
    trade["stop_order_id"] = "OLD-STOP"
    database.update_trade_order_ids(trade_id, stop_order_id="OLD-STOP")
    return trade


def make_trade_executor(database, kraken):
    executor = TradeExecutor.__new__(TradeExecutor)
    executor._db = database
    executor._risk_manager = FakeRiskManager()
    executor._broker_manager = FakeBrokerManager()
    executor.kraken = kraken
    executor.alpaca = None
    executor._ibkr = None
    return executor


def scalar(database, sql, params=()):
    with database._conn() as conn:
        row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def test_raw_pair_cancellation():
    exchange = FakeExchange(
        open_orders={
            "ETH-STOP": {"descr": {"pair": "XETHZUSD"}},
            "BTC-STOP": {"descr": {"pair": "XXBTZUSD"}},
        }
    )
    kraken = make_kraken(exchange)
    eth = kraken.cancel_orders_for_partial_close("ETH/USD")
    assert eth == {
        "matched": 1,
        "cancelled": 1,
        "ambiguous": False,
        "errors": [],
    }
    assert exchange.cancel_calls == ["ETH-STOP"]

    exchange.cancel_calls.clear()
    btc = kraken.cancel_orders_for_partial_close("BTC/USD")
    assert btc["matched"] == 1 and btc["cancelled"] == 1
    assert not btc["ambiguous"]
    assert exchange.cancel_calls == ["BTC-STOP"]


def test_cancellation_ambiguity_blocks_market_order():
    exchange = FakeExchange(open_orders_error=RuntimeError("Kraken timeout"))
    result = make_kraken(exchange).close_partial_position(
        "ETH/USD", 3.5, "buy"
    )
    assert result["reason"] == "cancellation_ambiguous"
    assert result["cancellation"]["ambiguous"]
    assert exchange.market_calls == []

    exchange = FakeExchange(
        open_orders={"ETH-STOP": {"descr": {"pair": "XETHZUSD"}}},
        cancel_fail_ids={"ETH-STOP"},
    )
    result = make_kraken(exchange).close_partial_position(
        "ETH/USD", 3.5, "buy"
    )
    assert result["reason"] == "cancellation_ambiguous"
    assert exchange.market_calls == []

    database = make_database("cancel-ambiguity")
    trade = seed_trade(database, trade_id="T-CANCEL")
    executor = make_trade_executor(database, make_kraken(exchange))
    outcome = executor.close_partial_trade(trade, 110.0, 0.35)
    assert not outcome and outcome.reconciliation_required
    assert database.get_state("kraken_partial_reconcile_T-CANCEL")["required"]
    assert executor._risk_manager.halts
    assert scalar(
        database,
        "SELECT COUNT(*) FROM trade_partials WHERE trade_id=?",
        ("T-CANCEL",),
    ) == 0
    assert trade["quantity"] == 10.0
    assert exchange.market_calls == []


def test_confirmed_partial_uses_broker_quantity_and_is_idempotent():
    database = make_database("confirmed-partial")
    trade = seed_trade(database)
    exchange = FakeExchange(
        open_orders={"ETH-STOP": {"descr": {"pair": "XETHZUSD"}}},
        market_response={
            "id": "CLOSE-PARTIAL",
            "status": "closed",
            "filled": 3.5,
            "average": 110.0,
        },
    )
    executor = make_trade_executor(database, make_kraken(exchange))
    monitor = PositionMonitor(db_ref=database, trade_executor=executor)

    assert monitor._maybe_take_scanner_partial(trade, 999.0, 10.0)
    assert trade["quantity"] == 6.5
    assert trade["partial_exit_count"] == 1
    assert len(exchange.market_calls) == 1
    assert scalar(
        database,
        "SELECT quantity FROM trade_partials WHERE trade_id=?",
        ("T-1",),
    ) == 3.5
    assert scalar(
        database,
        "SELECT exit_price FROM trade_partials WHERE trade_id=?",
        ("T-1",),
    ) == 110.0
    assert database.get_state("scanner_partial_taken_T-1") == 1
    assert trade["stop_order_id"] == "STOP-1"

    assert not monitor._maybe_take_scanner_partial(trade, 111.0, 11.0)
    assert len(exchange.market_calls) == 1


def test_terminal_zero_is_retryable_without_accounting():
    database = make_database("zero-fill")
    trade = seed_trade(database, trade_id="T-ZERO")
    exchange = FakeExchange(
        open_orders={"ETH-STOP": {"descr": {"pair": "XETHZUSD"}}},
        market_response={
            "id": "CLOSE-ZERO",
            "status": "canceled",
            "filled": 0.0,
            "average": 0.0,
        },
    )
    executor = make_trade_executor(database, make_kraken(exchange))
    monitor = PositionMonitor(db_ref=database, trade_executor=executor)
    assert not monitor._maybe_take_scanner_partial(trade, 110.0, 10.0)
    assert scalar(
        database,
        "SELECT COUNT(*) FROM trade_partials WHERE trade_id=?",
        ("T-ZERO",),
    ) == 0
    assert trade["quantity"] == 10.0
    assert trade["stop_order_id"] == "STOP-1"
    assert database.get_state("scanner_partial_retry_after_T-ZERO") > 0
    assert database.get_state("scanner_partial_taken_T-ZERO", default=0) == 0


def test_terminal_full_fill_routes_without_partial_accounting():
    database = make_database("full-fill")
    trade = seed_trade(database, trade_id="T-FULL")
    exchange = FakeExchange(
        open_orders={"ETH-STOP": {"descr": {"pair": "XETHZUSD"}}},
        market_response={
            "id": "CLOSE-FULL",
            "status": "closed",
            "filled": 10.0,
            "average": 112.0,
        },
    )
    executor = make_trade_executor(database, make_kraken(exchange))
    monitor = PositionMonitor(db_ref=database, trade_executor=executor)
    assert monitor._maybe_take_scanner_partial(trade, 112.0, 12.0)
    assert scalar(
        database,
        "SELECT COUNT(*) FROM trade_partials WHERE trade_id=?",
        ("T-FULL",),
    ) == 0
    assert scalar(
        database,
        "SELECT status FROM trades WHERE trade_id=?",
        ("T-FULL",),
    ) == "closed"
    assert scalar(
        database,
        "SELECT exit_price FROM trades WHERE trade_id=?",
        ("T-FULL",),
    ) == 112.0
    assert trade["status"] == "closed"
    assert database.get_state("kraken_full_reconcile_T-FULL") == 0


def test_unresolved_fill_sets_hold_and_does_not_account():
    database = make_database("unresolved")
    trade = seed_trade(database, trade_id="T-HOLD")
    exchange = FakeExchange(
        open_orders={"ETH-STOP": {"descr": {"pair": "XETHZUSD"}}},
        market_response={
            "id": "CLOSE-UNKNOWN",
            "status": "open",
            "filled": 1.0,
            "average": 109.0,
        },
        post_cancel_fetch=RuntimeError("post-cancel fetch failed"),
    )
    executor = make_trade_executor(database, make_kraken(exchange))
    outcome = executor.close_partial_trade(trade, 109.0, 0.35)
    assert not outcome and outcome.reconciliation_required
    marker = database.get_state("kraken_partial_reconcile_T-HOLD")
    assert marker["required"] is True
    assert marker["last_known_filled_qty"] == 1.0
    assert executor._risk_manager.halts
    assert scalar(
        database,
        "SELECT COUNT(*) FROM trade_partials WHERE trade_id=?",
        ("T-HOLD",),
    ) == 0


class StopOnlyKraken:
    def __init__(self):
        self.stop_id = None

    def place_stop_order(self, *_args, **_kwargs):
        return self.stop_id


class StopRecoveryDB:
    def __init__(self):
        self.state = {}
        self.order_updates = []

    def get_state(self, key, default=None):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def update_trade_order_ids(self, trade_id, stop_order_id=None, **_kwargs):
        self.order_updates.append((trade_id, stop_order_id))


def test_falsey_residual_stop_enters_existing_restore_path():
    database = StopRecoveryDB()
    stop_kraken = StopOnlyKraken()
    partial_outcome = PartialCloseOutcome(
        True,
        "confirmed_partial_fill",
        filled_qty=3.5,
        fill_price=110.0,
        stop_refresh_required=True,
        broker_order_id="CLOSE-1",
    )

    class PartialExecutor:
        def __init__(self):
            self.kraken = stop_kraken
            self.calls = 0

        def close_partial_trade(self, trade, *_args):
            self.calls += 1
            trade["quantity"] = 6.5
            trade["partial_exit_count"] = 1
            return partial_outcome

    executor = PartialExecutor()
    monitor = PositionMonitor(db_ref=database, trade_executor=executor)
    trade = {
        "trade_id": "T-STOP",
        "symbol": "ETH/USD",
        "asset_class": "crypto",
        "direction": "long",
        "strategy_name": "breakout_scanner",
        "partial_exit_count": 0,
        "quantity": 10.0,
        "stop_loss": 95.0,
        "stop_order_id": "OLD-STOP",
        "indicators_json": "{}",
    }

    assert monitor._maybe_take_scanner_partial(trade, 110.0, 10.0)
    assert trade["stop_order_id"] == ""
    unprotected = database.state["kraken_stop_unprotected_T-STOP"]
    assert unprotected["cancelled_stop_order_id"] == "OLD-STOP"
    assert "scanner_partial_taken_T-STOP" not in database.state

    stop_kraken.stop_id = "RESTORED-STOP"
    monitor._maybe_restore_missing_kraken_stop(
        trade, "T-STOP", "ETH/USD", "long"
    )
    assert trade["stop_order_id"] == "RESTORED-STOP"
    assert database.state["kraken_stop_unprotected_T-STOP"] == 0
    assert database.state["scanner_partial_taken_T-STOP"] == 1


TESTS = [
    test_raw_pair_cancellation,
    test_cancellation_ambiguity_blocks_market_order,
    test_confirmed_partial_uses_broker_quantity_and_is_idempotent,
    test_terminal_zero_is_retryable_without_accounting,
    test_terminal_full_fill_routes_without_partial_accounting,
    test_unresolved_fill_sets_hold_and_does_not_account,
    test_falsey_residual_stop_enters_existing_restore_path,
]


def main():
    passed = 0
    try:
        for test in TESTS:
            test()
            passed += 1
            print(f"PASS {test.__name__}")
    finally:
        _TEMP_ROOT.cleanup()
    print(f"{passed}/{len(TESTS)} scanner-partial Kraken tests passed")


if __name__ == "__main__":
    main()
