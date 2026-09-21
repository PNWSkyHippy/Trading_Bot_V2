"""No-network regressions for Alpaca partial-fill resolution and containment."""

import sys
from pathlib import Path
from types import SimpleNamespace


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import config
from core.trade_executor import AlpacaExecutor, TradeExecutor


class FakeApi:
    def __init__(self, submitted, resolved=None):
        self.submitted = submitted
        self.resolved = resolved
        self.get_order_calls = 0
        self.submit_calls = []

    def list_orders(self, **_kwargs):
        return []

    def submit_order(self, **_kwargs):
        self.submit_calls.append(_kwargs)
        if isinstance(self.submitted, Exception):
            raise self.submitted
        return self.submitted

    def get_order(self, _order_id):
        self.get_order_calls += 1
        return self.resolved


class FakeDb:
    def __init__(self):
        self.state = {}
        self.order_updates = []

    def get_state(self, key, default=0):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def update_trade_order_ids(self, trade_id, stop_order_id=None, **_kwargs):
        self.order_updates.append((trade_id, stop_order_id))


class FakeRiskManager:
    def __init__(self):
        self.halts = []

    def manual_halt(self, reason):
        self.halts.append(reason)


class FakeAlpaca:
    def __init__(self, result):
        self.result = result
        self.restored_stops = []

    def close_partial_position(self, *_args):
        return self.result

    def replace_stop_order(self, symbol, qty, direction, stop_price):
        self.restored_stops.append((symbol, qty, direction, stop_price))
        return "RESTORED-STOP"


def make_stock_trade():
    return {
        "trade_id": "STOCK-PARTIAL-1",
        "symbol": "HOOD",
        "asset_class": "stock",
        "broker": "alpaca",
        "direction": "long",
        "quantity": 20.0,
        "entry_price": 100.0,
        "position_value": 2000.0,
        "stop_loss": 95.0,
    }


def test_pending_order_is_polled_to_terminal_fill():
    original_attempts = config.ALPACA_PARTIAL_FILL_POLL_ATTEMPTS
    original_interval = config.ALPACA_PARTIAL_FILL_POLL_INTERVAL_SEC
    config.ALPACA_PARTIAL_FILL_POLL_ATTEMPTS = 2
    config.ALPACA_PARTIAL_FILL_POLL_INTERVAL_SEC = 0
    try:
        pending = SimpleNamespace(
            id="PENDING-1", status="pending_new", filled_qty="0", filled_avg_price=None
        )
        filled = SimpleNamespace(
            id="PENDING-1", status="filled", filled_qty="10", filled_avg_price="110.25"
        )
        alpaca = AlpacaExecutor.__new__(AlpacaExecutor)
        alpaca.api = FakeApi(pending, filled)
        result = alpaca.close_partial_position("HOOD", 10.0, "long")
        assert result["status"] == "filled"
        assert result["filled_qty"] == 10.0
        assert result["filled_avg_price"] == 110.25
        assert not result["resolution_failed"]
        assert alpaca.api.get_order_calls == 1
    finally:
        config.ALPACA_PARTIAL_FILL_POLL_ATTEMPTS = original_attempts
        config.ALPACA_PARTIAL_FILL_POLL_INTERVAL_SEC = original_interval


def test_rejected_stock_partial_restores_stop_without_global_halt():
    executor = TradeExecutor.__new__(TradeExecutor)
    executor._db = FakeDb()
    executor._risk_manager = FakeRiskManager()
    executor.kraken = SimpleNamespace(paper=False)
    executor.alpaca = FakeAlpaca({
        "ok": False,
        "reason": "submission_rejected",
        "status": "rejected",
        "broker_order_id": None,
        "filled_qty": 0.0,
        "filled_avg_price": 0.0,
        "resolution_failed": False,
        "cancellation": {},
    })
    trade = make_stock_trade()
    outcome = executor.close_partial_trade(trade, 110.0, 0.5)
    assert not outcome and outcome.reason == "terminal_zero_fill"
    assert executor.alpaca.restored_stops == [("HOOD", 20.0, "long", 95.0)]
    assert executor._risk_manager.halts == []
    assert not executor._db.state


def test_fractional_stock_stop_uses_day_lifetime():
    order = SimpleNamespace(id="STOP-1")
    alpaca = AlpacaExecutor.__new__(AlpacaExecutor)
    alpaca.api = FakeApi(order)
    stop_id = alpaca.replace_stop_order("HOOD", 10.189537, "long", 117.63)
    assert stop_id == "STOP-1"
    assert alpaca.api.submit_calls[-1]["time_in_force"] == "day"


def test_nonterminal_stock_partial_is_quarantined_without_global_halt():
    executor = TradeExecutor.__new__(TradeExecutor)
    executor._db = FakeDb()
    executor._risk_manager = FakeRiskManager()
    executor.kraken = SimpleNamespace(paper=False)
    executor.alpaca = FakeAlpaca({
        "ok": False,
        "reason": "unknown",
        "status": "pending_new",
        "broker_order_id": "PENDING-2",
        "filled_qty": 0.0,
        "filled_avg_price": 0.0,
        "resolution_failed": True,
        "cancellation": {},
    })
    trade = make_stock_trade()
    outcome = executor.close_partial_trade(trade, 110.0, 0.5)
    marker = executor._db.state["alpaca_partial_reconcile_STOCK-PARTIAL-1"]
    assert not outcome and outcome.reconciliation_required
    assert marker["required"] is True
    assert marker["broker_order_id"] == "PENDING-2"
    assert executor._risk_manager.halts == []
    assert "kraken_partial_reconcile_STOCK-PARTIAL-1" not in executor._db.state


def main():
    tests = (
        test_pending_order_is_polled_to_terminal_fill,
        test_rejected_stock_partial_restores_stop_without_global_halt,
        test_fractional_stock_stop_uses_day_lifetime,
        test_nonterminal_stock_partial_is_quarantined_without_global_halt,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)}/{len(tests)} Alpaca partial-safety tests passed")


if __name__ == "__main__":
    main()
