import unittest
from datetime import datetime
import threading
from zoneinfo import ZoneInfo

from ninja_futures_scanner import MarketState, futures_session_is_active


PACIFIC = ZoneInfo("America/Los_Angeles")


def at(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=PACIFIC)


class FuturesSessionScheduleTests(unittest.TestCase):
    def test_sunday_reopens_at_three_pm_pacific(self):
        self.assertFalse(futures_session_is_active(at(2026, 9, 6, 14, 59)))
        self.assertTrue(futures_session_is_active(at(2026, 9, 6, 15, 0)))

    def test_weekday_flatten_starts_at_ten_to_one_pacific(self):
        self.assertTrue(futures_session_is_active(at(2026, 9, 7, 12, 49)))
        self.assertFalse(futures_session_is_active(at(2026, 9, 7, 12, 50)))
        self.assertFalse(futures_session_is_active(at(2026, 9, 7, 14, 59)))
        self.assertTrue(futures_session_is_active(at(2026, 9, 7, 15, 0)))

    def test_friday_does_not_reopen(self):
        self.assertTrue(futures_session_is_active(at(2026, 9, 11, 12, 49)))
        self.assertFalse(futures_session_is_active(at(2026, 9, 11, 12, 50)))
        self.assertFalse(futures_session_is_active(at(2026, 9, 11, 15, 0)))

    def test_closed_session_forces_each_active_scanner_engine_to_close(self):
        class FakeEngine:
            def __init__(self, trade_id):
                self.active_trade = {"trade_id": trade_id}
                self.closed_at = None

            def session_close(self, stamp):
                self.closed_at = stamp
                trade = self.active_trade
                self.active_trade = None
                return trade

        state = object.__new__(MarketState)
        state.engine_lock = threading.RLock()
        emt, eat = FakeEngine("EMT-PAPER-1"), FakeEngine("EAT-PAPER-1")
        state.emt_engines = {"ES": emt}
        state.eat_engines = {"MNQ": eat}

        closed = state.enforce_futures_session(at(2026, 9, 7, 12, 50))

        self.assertEqual(
            closed,
            [("emt", "ES", "EMT-PAPER-1"), ("eat", "MNQ", "EAT-PAPER-1")],
        )
        self.assertIsNotNone(emt.closed_at)
        self.assertIsNotNone(eat.closed_at)


if __name__ == "__main__":
    unittest.main()
