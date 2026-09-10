import unittest
from types import SimpleNamespace

import config
from core.position_monitor import PositionMonitor


class FakeDB:
    def __init__(self):
        self.state = {}
        self.level_updates = []
        self.order_updates = []

    def get_state(self, key, default=0):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def update_trade_levels(self, trade_id, stop_loss=None, take_profit=None):
        self.level_updates.append((trade_id, stop_loss, take_profit))

    def update_trade_order_ids(self, trade_id, stop_order_id=None, tp_order_id=None):
        self.order_updates.append((trade_id, stop_order_id, tp_order_id))


class FakeExecutor:
    def __init__(self):
        self.partial_calls = []
        self.stop_calls = []

    def close_partial_trade(self, trade, price, fraction, reason):
        self.partial_calls.append((trade["trade_id"], price, fraction, reason))
        trade["quantity"] = 5.0
        trade["partial_exit_count"] = 1
        return SimpleNamespace(success=True, full_fill=False, fill_price=price)

    def replace_stock_stop(self, trade, stop_price):
        self.stop_calls.append((trade["trade_id"], trade["quantity"], stop_price))
        return "stock-stop-id"


class UniversalTpRunnerTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.executor = FakeExecutor()
        self.monitor = PositionMonitor(db_ref=self.db, trade_executor=self.executor)
        self.old_enabled = config.UNIVERSAL_TP_RUNNER_ENABLED
        self.old_fraction = config.UNIVERSAL_TP_RUNNER_FRACTION
        self.old_trail = config.UNIVERSAL_TP_RUNNER_TRAIL_PCT
        config.UNIVERSAL_TP_RUNNER_ENABLED = True
        config.UNIVERSAL_TP_RUNNER_FRACTION = 0.5
        config.UNIVERSAL_TP_RUNNER_TRAIL_PCT = 2.0
        self.trade = {
            "trade_id": "runner-test",
            "symbol": "TEST",
            "asset_class": "stock",
            "broker": "alpaca",
            "direction": "long",
            "quantity": 10.0,
            "entry_price": 90.0,
            "take_profit": 100.0,
            "stop_loss": 85.0,
            "stop_order_id": "old-bracket-stop",
            "partial_exit_count": 0,
        }

    def tearDown(self):
        config.UNIVERSAL_TP_RUNNER_ENABLED = self.old_enabled
        config.UNIVERSAL_TP_RUNNER_FRACTION = self.old_fraction
        config.UNIVERSAL_TP_RUNNER_TRAIL_PCT = self.old_trail

    def test_banks_half_then_trails_remaining_half_from_peak(self):
        self.assertTrue(self.monitor._start_universal_tp_runner(self.trade, 100.0))

        self.assertEqual(self.executor.partial_calls, [
            ("runner-test", 100.0, 0.5, "take_profit_half_runner")
        ])
        self.assertEqual(self.trade["quantity"], 5.0)
        self.assertEqual(self.trade["stop_loss"], 98.0)
        self.assertEqual(self.executor.stop_calls[-1], ("runner-test", 5.0, 98.0))

        self.assertTrue(self.monitor._advance_universal_tp_runner(self.trade, 110.0))
        self.assertEqual(self.trade["stop_loss"], 107.8)
        self.assertEqual(self.executor.stop_calls[-1], ("runner-test", 5.0, 107.8))


if __name__ == "__main__":
    unittest.main()
