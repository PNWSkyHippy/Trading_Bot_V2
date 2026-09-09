import tempfile
import unittest
from datetime import datetime, timedelta

from eat_strategy import EATStrategyEngine, EATTrade


BASE_TIME = datetime.fromisoformat("2026-07-23T05:00:00-07:00")


def minute_bar(offset, close=99.75, high=100.0, low=99.0):
    stamp = BASE_TIME + timedelta(minutes=offset)
    return {
        "symbol": "MNQ",
        "time": stamp.isoformat(),
        "open": close,
        "high": max(high, close),
        "low": min(low, close),
        "close": close,
        "volume": 1,
    }


class FakeMirrorDB:
    def __init__(self):
        self.closed = []
        self.results = []

    def close_trade(self, trade_id, exit_price, exit_reason, pnl, pnl_pct,
                    fees_paid=0.0):
        self.closed.append({
            "trade_id": trade_id,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "fees_paid": fees_paid,
        })

    def record_consecutive_result(self, won):
        self.results.append(won)


class EATStrategyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = {
            "enabled": True,
            "symbol": "MNQ",
            "contracts": 2,
            "mirror_to_bot_db": False,
            "primary_box_minutes": 5,
            "fallback_box_minutes": 15,
            "min_box_ticks": 4,
            "max_box_ticks": 100,
            "buffer_ticks": 2,
            "tp1_ticks": 4,
            "runner_trail_ticks": 2,
            "trade_window_minutes": 60,
            "sessions": [{"name": "test", "start": "05:00"}],
        }
        self.contract = {"tick_size": 0.25, "tick_value": 0.5}

    def tearDown(self):
        self.temp_dir.cleanup()

    def engine(self, overrides=None):
        settings = dict(self.settings)
        settings.update(overrides or {})
        return EATStrategyEngine(
            settings, self.contract, self.temp_dir.name
        )

    def test_primary_box_and_buffer_close_open_one_trade(self):
        engine = self.engine()
        for minute in range(5):
            engine.on_minute_bar(
                minute_bar(minute, high=100.0, low=99.0),
                historical=False,
            )
        events = engine.on_minute_bar(
            minute_bar(5, close=100.25, high=100.25, low=100.0),
            historical=False,
        )

        self.assertEqual(engine.box_minutes, 5)
        self.assertEqual(engine.inner_low, 99.0)
        self.assertEqual(engine.inner_high, 100.0)
        self.assertEqual(engine.trades_this_session, 1)
        self.assertEqual(engine.active_trade.direction, "long")
        self.assertEqual(engine.active_trade.quantity, 2)
        self.assertTrue(any(event.kind == "PAPER_ENTRY" for event in events))

    def test_small_primary_box_uses_fifteen_minute_fallback(self):
        engine = self.engine()
        for minute in range(15):
            low = 99.0 if minute >= 10 else 99.5
            engine.on_minute_bar(
                minute_bar(minute, close=99.75, high=100.0, low=low),
                historical=False,
            )
        engine.on_minute_bar(
            minute_bar(15, close=100.75, high=100.75, low=100.5),
            historical=False,
        )

        self.assertEqual(engine.box_minutes, 15)
        self.assertEqual(engine.phase, "WAIT_BUFFER_CLOSE")
        self.assertIsNone(engine.active_trade)

    def test_open_trade_keeps_risk_monitoring_after_entry_window(self):
        engine = self.engine({"trade_window_minutes": 1})
        engine.session_name = "test"
        engine.active_trade = EATTrade(
            trade_id="test",
            symbol="MNQ",
            direction="long",
            quantity=1,
            entry_time="2026-07-23T12:05:00+00:00",
            entry_price=100.0,
            stop_price=99.0,
            tp1_price=125.0,
            entry_bar_time="2026-07-23T05:05:00-07:00",
            remaining_quantity=1,
            tp1_quantity=1,
        )
        events = engine.on_minute_bar(
            minute_bar(120, close=99.2, high=100.2, low=98.8),
            historical=False,
        )

        self.assertIsNone(engine.active_trade)
        self.assertTrue(any(event.kind == "PAPER_EXIT" for event in events))

    def test_fallback_box_cannot_be_shorter_than_primary(self):
        with self.assertRaisesRegex(ValueError, "fallback box minutes"):
            self.engine({
                "primary_box_minutes": 15,
                "fallback_box_minutes": 5,
            })

    def test_stop_override_replaces_wick_stop_and_ignores_cap(self):
        engine = self.engine({
            "stop_ticks_override": 100,
            "max_stop_ticks": 10,
        })
        trade_bar = minute_bar(5, close=100.0)
        trade_bar["dt"] = datetime.fromisoformat(trade_bar["time"])
        engine.inner_high = 100.0
        engine.inner_low = 99.0

        engine._open_trade("long", 100.0, trade_bar)

        self.assertEqual(engine.active_trade.stop_price, 75.0)
        self.assertEqual(
            (engine.active_trade.entry_price - engine.active_trade.stop_price)
            / engine.tick_size,
            100,
        )

    def test_manual_close_closes_exact_active_paper_trade(self):
        engine = self.engine()
        engine.active_trade = EATTrade(
            trade_id="EAT-PAPER-TEST",
            symbol="MNQ",
            direction="long",
            quantity=2,
            entry_time="2026-07-23T12:05:00+00:00",
            entry_price=100.0,
            stop_price=90.0,
            tp1_price=125.0,
            entry_bar_time="2026-07-23T05:05:00-07:00",
            remaining_quantity=2,
            tp1_quantity=1,
        )
        engine.last_live_price = 101.0

        closed = engine.manual_close("EAT-PAPER-TEST")

        self.assertIsNone(engine.active_trade)
        self.assertEqual(closed["exit_reason"], "manual_close")
        self.assertEqual(closed["exit_price"], 101.0)
        # MNQ Free-plan all-in rate is $0.95/side: two contracts cost $3.80.
        self.assertEqual(closed["fees_paid"], 3.8)
        self.assertEqual(closed["realized_pnl"], 0.2)
        with self.assertRaises(LookupError):
            engine.manual_close("EAT-PAPER-TEST")

    def test_session_close_uses_last_live_price_and_eod_reason(self):
        engine = self.engine()
        engine.active_trade = EATTrade(
            trade_id="EAT-PAPER-EOD", symbol="MNQ", direction="long", quantity=1,
            entry_time="2026-09-08T16:00:00+00:00", entry_price=100.0,
            stop_price=99.0, tp1_price=102.0, entry_bar_time="2026-09-08T05:05:00-07:00",
            remaining_quantity=1, tp1_quantity=1,
        )
        engine.last_live_price = 101.0

        closed = engine.session_close(BASE_TIME + timedelta(hours=7, minutes=50))

        self.assertIsNone(engine.active_trade)
        self.assertEqual(closed["exit_reason"], "futures_eod_close")
        self.assertEqual(closed["exit_price"], 101.0)

    def test_db_mirror_receives_quantity_scaled_net_eat_result_and_fee(self):
        mirror = FakeMirrorDB()
        engine = EATStrategyEngine(
            dict(self.settings, mirror_to_bot_db=True), self.contract,
            self.temp_dir.name, db_mirror=mirror,
        )
        engine.active_trade = EATTrade(
            trade_id="EAT-PAPER-MIRROR",
            symbol="MNQ",
            direction="long",
            quantity=2,
            entry_time="2026-07-23T12:05:00+00:00",
            entry_price=100.0,
            stop_price=90.0,
            tp1_price=125.0,
            entry_bar_time="2026-07-23T05:05:00-07:00",
            remaining_quantity=2,
            tp1_quantity=1,
        )
        engine.last_live_price = 101.0

        engine.manual_close("EAT-PAPER-MIRROR")

        self.assertEqual(mirror.closed[0]["fees_paid"], 3.8)
        self.assertEqual(mirror.closed[0]["pnl"], 0.2)
        self.assertEqual(mirror.results, [True])


if __name__ == "__main__":
    unittest.main()
