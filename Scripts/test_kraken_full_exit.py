"""Focused full-Kraken-exit regression tests; no network or production DB."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

config.IBKR_ENABLED = False
config.KRAKEN_ENABLED = True

from core.kraken_executor import KrakenExecutor
from core.position_monitor import PositionMonitor
from core.trade_executor import TradeExecutor


class FakeExchange:
    def __init__(self, open_orders=None, open_error=None, market=None,
                 follow_up=None, cancel_error=None):
        self.open_orders = open_orders or {}
        self.open_error = open_error
        self.market = market or {
            "id": "CLOSE-1", "status": "closed", "filled": 10.0,
            "average": 12.0,
        }
        self.follow_up = follow_up
        self.cancel_error = cancel_error
        self.cancel_calls = []
        self.market_calls = []
        self.resolve_cancel_calls = []

    def privatePostOpenorders(self, _params):
        if self.open_error:
            raise self.open_error
        return {"result": {"open": self.open_orders}}

    def cancelOrder(self, order_id):
        self.cancel_calls.append(order_id)
        if self.cancel_error:
            raise self.cancel_error
        return {"id": order_id, "status": "canceled"}

    def create_market_order(self, symbol, side, qty, params=None):
        self.market_calls.append((symbol, side, qty, params))
        return self.market

    def cancel_order(self, order_id, symbol, params=None):
        self.resolve_cancel_calls.append((order_id, symbol, params))
        return {"id": order_id, "status": "canceled"}

    def fetch_order(self, _order_id, _symbol, params=None):
        if isinstance(self.follow_up, Exception):
            raise self.follow_up
        if self.follow_up is None:
            raise AssertionError("unexpected fetch_order")
        return self.follow_up


def live_executor(exchange, attempts=0):
    executor = KrakenExecutor(
        paper=False, fill_poll_attempts=attempts, fill_poll_interval_sec=0
    )
    executor.exchange = exchange
    executor._unresolved_log_path = os.path.join(
        tempfile.gettempdir(), "full_exit_unresolved_test.log"
    )
    return executor


def test_raw_kraken_aliases_cancel_before_full_close():
    exchange = FakeExchange(open_orders={
        "STOP-ETH": {"descr": {"pair": "XETHZUSD"}},
        "STOP-BTC": {"descr": {"pair": "XXBTZUSD"}},
    })
    eth = live_executor(exchange).close_position("ETH/USD", 10.0, "buy")
    assert eth["resolution_failed"] is False
    assert exchange.cancel_calls == ["STOP-ETH"]
    exchange.cancel_calls.clear()
    btc = live_executor(exchange).close_position("BTC/USD", 10.0, "buy")
    assert btc["resolution_failed"] is False
    assert exchange.cancel_calls == ["STOP-BTC"]


def test_cancellation_ambiguity_blocks_full_market_close():
    exchange = FakeExchange(open_error=RuntimeError("timeout"))
    result = live_executor(exchange).close_position("ETH/USD", 10.0, "buy")
    assert result["cancellation_ambiguous"] is True
    assert result["resolution_failed"] is True
    assert exchange.market_calls == []


def test_open_market_response_resolves_to_terminal_full_fill():
    exchange = FakeExchange(
        market={"id": "CLOSE-OPEN", "status": "open", "filled": 0},
        follow_up={"id": "CLOSE-OPEN", "status": "closed", "filled": 10.0,
                   "average": 12.25},
    )
    result = live_executor(exchange, attempts=1).close_position("ETH/USD", 10.0, "buy")
    assert result["resolution_failed"] is False
    assert result["filled_qty"] == 10.0
    assert result["filled_avg_price"] == 12.25


def test_leveraged_short_full_close_preserves_leverage():
    exchange = FakeExchange()
    result = live_executor(exchange).close_position("ETH/USD", 10.0, "sell", leverage=2)
    assert result["resolution_failed"] is False
    assert exchange.market_calls == [("ETH/USD", "buy", 10.0, {"leverage": 2})]


class FullExitDB:
    def __init__(self):
        self.states = {}
        self.closed = []
        self.order_updates = []
        self.tax_events = []

    def get_state(self, key, default=None):
        return self.states.get(key, default)

    def set_state(self, key, value):
        self.states[key] = value

    def update_trade_order_ids(self, trade_id, stop_order_id=None, tp_order_id=None):
        self.order_updates.append((trade_id, stop_order_id, tp_order_id))

    def close_trade(self, **kwargs):
        self.closed.append(kwargs)

    def record_tax_event(self, trade):
        self.tax_events.append(trade)

    def get_latest_capital(self):
        return None


class BrokerStub:
    def get_broker_balance(self, _broker):
        return None

    def update_broker_balance(self, *args):
        pass


class RiskStub:
    def __init__(self):
        self.results = []
        self.halts = []

    def record_trade_result(self, *args, **kwargs):
        self.results.append((args, kwargs))

    def manual_halt(self, reason):
        self.halts.append(reason)


class FullKrakenStub:
    def __init__(self, result, stop_id="RESIDUAL-STOP"):
        self.result = result
        self.stop_id = stop_id
        self.close_calls = []
        self.stop_calls = []

    def close_position(self, *args, **kwargs):
        self.close_calls.append((args, kwargs))
        return self.result

    def place_stop_order(self, *args, **kwargs):
        self.stop_calls.append((args, kwargs))
        return self.stop_id


def full_trade():
    return {
        "trade_id": "T-FULL", "symbol": "ETH/USD", "direction": "long",
        "quantity": 10.0, "entry_price": 10.0, "asset_class": "crypto",
        "broker": "kraken", "position_value": 100.0, "stop_loss": 9.0,
        "stop_order_id": "OLD-STOP", "partial_pnl": 0.0,
        "partial_fees_paid": 0.0, "strategy_name": "manual",
    }


def executor_for_result(result, stop_id="RESIDUAL-STOP"):
    database = FullExitDB()
    executor = TradeExecutor(db_ref=database, broker_manager_ref=BrokerStub())
    executor._risk_manager = RiskStub()
    executor.kraken = FullKrakenStub(result, stop_id=stop_id)
    return executor, database


def test_terminal_zero_fill_holds_without_db_or_capital_mutation():
    executor, database = executor_for_result({
        "status": "closed", "filled_qty": 0.0, "filled_avg_price": 0.0,
        "resolution_failed": False, "cancellation_ambiguous": False,
    })
    assert executor.close_trade(full_trade(), 12.0, "take_profit") is False
    assert database.closed == []
    assert "kraken_full_reconcile_T-FULL" in database.states
    assert executor.kraken.stop_calls[0][0][1] == 10.0


def test_terminal_partial_fill_holds_and_protects_exact_residual():
    executor, database = executor_for_result({
        "status": "closed", "filled_qty": 2.5, "filled_avg_price": 12.0,
        "resolution_failed": False, "cancellation_ambiguous": False,
    })
    assert executor.close_trade(full_trade(), 12.0, "take_profit") is False
    assert database.closed == []
    assert executor.kraken.stop_calls[0][0][1] == 7.5
    assert database.order_updates[-1] == ("T-FULL", "RESIDUAL-STOP", None)


def test_residual_stop_failure_marks_hold_without_unsafe_restore():
    executor, database = executor_for_result({
        "status": "closed", "filled_qty": 2.5, "filled_avg_price": 12.0,
        "resolution_failed": False, "cancellation_ambiguous": False,
    }, stop_id=None)
    trade = full_trade()
    assert executor.close_trade(trade, 12.0, "take_profit") is False
    assert trade["stop_order_id"] == ""
    assert database.states["kraken_stop_unprotected_T-FULL"][
        "manual_reconciliation_required"
    ] is True
    PositionMonitor(db_ref=database)._maybe_restore_missing_kraken_stop(
        trade, "T-FULL", "ETH/USD", "long"
    )
    assert len(executor.kraken.stop_calls) == 1


def test_overfill_and_unresolved_hold_without_db_close():
    for result in (
        {"status": "closed", "filled_qty": 10.5, "filled_avg_price": 12.0,
         "resolution_failed": False, "cancellation_ambiguous": False},
        {"status": "unresolved", "filled_qty": 0.5, "filled_avg_price": 12.0,
         "resolution_failed": True, "cancellation_ambiguous": False},
    ):
        executor, database = executor_for_result(result)
        assert executor.close_trade(full_trade(), 12.0, "take_profit") is False
        assert database.closed == []
        assert "kraken_full_reconcile_T-FULL" in database.states


def test_full_fill_uses_confirmed_price_and_closes_once():
    executor, database = executor_for_result({
        "status": "closed", "filled_qty": 10.0, "filled_avg_price": 12.25,
        "resolution_failed": False, "cancellation_ambiguous": False,
    })
    assert executor.close_trade(full_trade(), 99.0, "take_profit") is True
    assert database.closed[0]["exit_price"] == 12.25
    assert "kraken_full_reconcile_T-FULL" not in database.states


def test_confirmed_full_fill_over_pnl_cap_holds_halts_and_blocks_duplicate():
    old_paper_mode = config.KRAKEN_PAPER_MODE
    config.KRAKEN_PAPER_MODE = False
    try:
        for recorded_broker in ("kraken", "coinbase"):
            executor, database = executor_for_result({
                "status": "closed", "filled_qty": 10.0, "filled_avg_price": 17.0,
                "broker_order_id": "AUDIT-CONFIRMED-10-AT-17",
                "resolution_failed": False, "cancellation_ambiguous": False,
            })
            trade = full_trade()
            trade["broker"] = recorded_broker

            assert executor.close_trade(trade, 99.0, "take_profit") is False
            hold = database.states["kraken_full_reconcile_T-FULL"]
            assert hold["reason"] == "confirmed full fill exceeds P&L sanity cap"
            assert hold["filled_qty"] == 10.0
            assert hold["filled_avg_price"] == 17.0
            assert hold["broker_order_id"] == "AUDIT-CONFIRMED-10-AT-17"
            assert len(executor._risk_manager.halts) == 1
            assert database.closed == []

            held_trade = full_trade()
            held_trade["stop_order_id"] = ""
            PositionMonitor(db_ref=database)._maybe_restore_missing_kraken_stop(
                held_trade, "T-FULL", "ETH/USD", "long"
            )
            assert database.order_updates == []

            assert executor.close_trade(trade, 99.0, "take_profit") is False
            assert len(executor.kraken.close_calls) == 1
            assert database.closed == []
    finally:
        config.KRAKEN_PAPER_MODE = old_paper_mode


def test_paper_full_fill_over_pnl_cap_keeps_generic_bad_tick_behavior():
    old_paper_mode = config.KRAKEN_PAPER_MODE
    config.KRAKEN_PAPER_MODE = True
    try:
        executor, database = executor_for_result({
            "status": "closed", "filled_qty": 10.0, "filled_avg_price": 17.0,
            "broker_order_id": "PAPER-10-AT-17",
            "resolution_failed": False, "cancellation_ambiguous": False,
        })

        assert executor.close_trade(full_trade(), 99.0, "take_profit") is None
        assert "kraken_full_reconcile_T-FULL" not in database.states
        assert executor._risk_manager.halts == []
        assert database.closed == []
    finally:
        config.KRAKEN_PAPER_MODE = old_paper_mode


def test_reconciliation_hold_blocks_duplicate_full_close_submission():
    executor, database = executor_for_result({
        "status": "cancellation_ambiguous", "filled_qty": 0.0,
        "filled_avg_price": 0.0, "resolution_failed": True,
        "cancellation_ambiguous": True,
    })
    trade = full_trade()
    assert executor.close_trade(trade, 12.0, "take_profit") is False
    assert len(executor.kraken.close_calls) == 1
    assert executor.close_trade(trade, 12.0, "take_profit") is False
    assert len(executor.kraken.close_calls) == 1
    assert database.closed == []


if __name__ == "__main__":
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print(f"{len(tests)}/{len(tests)} passed")
