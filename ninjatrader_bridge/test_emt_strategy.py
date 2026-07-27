import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from emt_strategy import EMTStrategyEngine


ET = ZoneInfo("America/New_York")


def stamp(hour, minute, second=0):
    return datetime(2026, 7, 20, hour, minute, second, tzinfo=ET).isoformat()


def bar(time_text, close, high=None, low=None, volume=610, **extra):
    high = close + 0.25 if high is None else high
    low = close - 0.25 if low is None else low
    return {
        "symbol": "ES 09-26",
        "time": time_text,
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "bar_type": "tick",
        "bar_value": 610,
        **extra,
    }


class FakeMirrorDB:
    def __init__(self):
        self.opened = []
        self.closed = []

    def open_trade(self, trade):
        self.opened.append(trade)
        return {"status": "inserted", "trade_id": trade["trade_id"]}

    def close_trade(self, trade_id, exit_price, exit_reason, pnl, pnl_pct, fees_paid=0.0):
        self.closed.append({
            "trade_id": trade_id,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "fees_paid": fees_paid,
        })


class EMTStrategyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = {
            "enabled": True,
            "paper_only": True,
            "symbol": "ES",
            "tick_bar_value": 610,
            "source_timezone": "America/New_York",
            "market_timezone": "America/New_York",
            "opening_range_start": "09:30",
            "opening_range_minutes": 15,
            "trade_window_minutes": 60,
            "keltner_ema_period": 5,
            "retrace_tolerance_ticks": 1,
            "confirmation_ticks": 1,
            "stop_points": 2.0,
            "target_points": 2.0,
            "contracts": 1,
            "max_trades_per_session": 12,
            "double_pattern_lookback_bars": 20,
            "double_pattern_tolerance_points": 1.0,
            "double_pattern_min_separation_bars": 6,
            "double_pattern_neckline_points": 1.0,
            "paper_ledger_path": "ledger.jsonl",
        }
        self.contract = {"tick_size": 0.25, "tick_value": 12.50}
        self.engine = EMTStrategyEngine(
            self.settings, self.contract, self.temp.name
        )

    def tearDown(self):
        self.temp.cleanup()

    def seed_opening_range(self, high=101.0, low=99.0):
        for minute in range(30, 45):
            close = 100.0
            minute_bar = bar(
                stamp(9, minute), close,
                high=high if minute == 35 else 100.5,
                low=low if minute == 40 else 99.5,
                volume=100,
            )
            self.engine.on_minute_bar(minute_bar, historical=True)

    def seed_tick_history(self, close=98.5, count=8):
        start = datetime(2026, 7, 20, 9, 40, tzinfo=ET)
        for index in range(count):
            value = close + (index % 2) * 0.05
            self.engine.on_tick_bar(
                bar((start + timedelta(seconds=index)).isoformat(), value),
                complete=True,
                historical=True,
            )

    def arm_short_and_touch(self):
        self.seed_opening_range()
        self.seed_tick_history()
        self.engine.on_tick_bar(
            bar(stamp(9, 45), 98.0), complete=True, historical=False
        )
        self.assertEqual(self.engine.phase, "WAIT_RETRACE")
        self.engine.on_tick_bar(
            bar(stamp(9, 45, 1), 98.35), complete=False, historical=False
        )
        self.assertEqual(self.engine.phase, "RETRACE_TOUCHED")

    def test_opening_range_uses_exact_fifteen_one_minute_bars(self):
        self.seed_opening_range(high=101.25, low=98.75)
        self.assertEqual(self.engine.opening_high, 101.25)
        self.assertEqual(self.engine.opening_low, 98.75)

    def test_breakout_requires_price_and_midline_outside_range(self):
        self.seed_opening_range()
        self.seed_tick_history(close=102.0)
        self.engine.on_tick_bar(
            bar(stamp(9, 45), 98.75), complete=True, historical=False
        )
        self.assertEqual(self.engine.phase, "WAIT_BREAKOUT")
        self.assertGreaterEqual(
            self.engine.last_midline, self.engine.support_level
        )
        self.assertIn(
            "Price below support; waiting for Keltner midline",
            self.engine.snapshot()["status_message"],
        )
        self.assertFalse(
            any(event.kind == "BREAKOUT_ARMED" for event in self.engine.events)
        )

    def test_short_retrace_confirmation_opens_exact_two_point_paper_bracket(self):
        self.arm_short_and_touch()
        self.engine.on_tick_bar(
            bar(stamp(9, 45, 2), 97.75), complete=False, historical=False
        )
        trade = self.engine.active_trade
        self.assertIsNotNone(trade)
        self.assertEqual(trade.direction, "short")
        self.assertEqual(trade.quantity, 1)
        self.assertEqual(trade.stop_price, 99.75)
        self.assertEqual(trade.target_price, 95.75)

    def test_two_point_es_target_is_one_hundred_dollars(self):
        self.arm_short_and_touch()
        self.engine.on_tick_bar(
            bar(stamp(9, 45, 2), 97.75), complete=False, historical=False
        )
        self.engine.on_tick_bar(
            bar(stamp(9, 46), 95.75, high=97.75, low=95.5),
            complete=False,
            historical=False,
        )
        trade = self.engine.closed_trades[-1]
        self.assertEqual(trade.exit_reason, "take_profit")
        self.assertEqual(trade.pnl, 100.0)

    def test_same_forming_bar_cannot_use_pre_entry_high_for_false_stop(self):
        self.arm_short_and_touch()
        entry_time = stamp(9, 45, 2)
        self.engine.on_tick_bar(
            bar(entry_time, 97.5, high=102.0, low=97.25),
            complete=False,
            historical=False,
        )
        self.assertIsNotNone(self.engine.active_trade)
        self.engine.on_tick_bar(
            bar(entry_time, 97.5, high=102.0, low=97.25),
            complete=False,
            historical=False,
        )
        self.assertIsNotNone(self.engine.active_trade)

    def test_historical_tick_data_never_opens_a_trade(self):
        self.seed_opening_range()
        self.seed_tick_history(close=98.0, count=30)
        self.assertIsNone(self.engine.active_trade)
        self.assertEqual(self.engine.trades_this_session, 0)

    def test_current_setup_double_bottom_veto_uses_small_window(self):
        lows = [101, 100, 99, 98, 99, 100, 102, 101, 100, 99, 98.5, 99.5, 100.5, 101]
        for index, low in enumerate(lows):
            self.engine.tick_bars.append({
                "time": str(index), "dt": datetime.now(tz=ET),
                "open": low + 0.5, "high": low + (2.5 if index == 6 else 0.75),
                "low": low, "close": low + 0.5, "volume": 610,
            })
        self.engine.setup_start_index = 0
        self.assertTrue(self.engine._adverse_double_pattern("short"))
        self.assertFalse(self.engine._adverse_double_pattern("long"))

    def test_old_pattern_before_current_setup_cannot_veto(self):
        lows = [101, 100, 99, 98, 99, 100, 102, 101, 100, 99, 98.5, 99.5, 100.5, 101]
        for index, low in enumerate(lows):
            self.engine.tick_bars.append({
                "time": str(index), "dt": datetime.now(tz=ET),
                "open": low + 0.5, "high": low + (2.5 if index == 6 else 0.75),
                "low": low, "close": low + 0.5, "volume": 610,
            })
        self.engine.setup_start_index = 8
        self.assertFalse(self.engine._adverse_double_pattern("short"))

    def test_trade_window_closes_and_refuses_new_entries(self):
        self.seed_opening_range()
        self.seed_tick_history()
        self.engine.on_tick_bar(
            bar(stamp(10, 46), 98.0), complete=True, historical=False
        )
        self.assertEqual(self.engine.phase, "SESSION_DONE")
        self.assertIsNone(self.engine.active_trade)

    def test_db_mirror_records_emt_open_and_close_for_dashboard_tables(self):
        mirror = FakeMirrorDB()
        settings = dict(self.settings, mirror_to_bot_db=True, broker_symbol="ESU6")
        engine = EMTStrategyEngine(settings, self.contract, self.temp.name, db_mirror=mirror)

        for minute in range(30, 45):
            engine.on_minute_bar(
                bar(stamp(9, minute), 100.0,
                    high=101.0 if minute == 35 else 100.5,
                    low=99.0 if minute == 40 else 99.5, volume=100),
                historical=True,
            )
        start = datetime(2026, 7, 20, 9, 40, tzinfo=ET)
        for index in range(8):
            engine.on_tick_bar(
                bar((start + timedelta(seconds=index)).isoformat(), 98.5),
                complete=True, historical=True,
            )
        engine.on_tick_bar(bar(stamp(9, 45), 98.0), complete=True, historical=False)
        engine.on_tick_bar(bar(stamp(9, 45, 1), 98.35), complete=False, historical=False)
        engine.on_tick_bar(bar(stamp(9, 45, 2), 97.75), complete=False, historical=False)
        engine.on_tick_bar(
            bar(stamp(9, 46), 95.75, high=97.75, low=95.75),
            complete=False, historical=False,
        )

        self.assertEqual(len(mirror.opened), 1)
        opened = mirror.opened[0]
        self.assertEqual(opened["strategy_name"], "emt")
        self.assertEqual(opened["asset_class"], "future")
        self.assertEqual(opened["broker"], "paper_emt")
        self.assertEqual(opened["symbol"], "ESU6")
        self.assertEqual(opened["position_value"], 100.0)
        self.assertEqual(opened["entry_timeframe"], "610Tick")
        self.assertEqual(opened["indicators"]["point_value"], 50.0)
        self.assertEqual(len(mirror.closed), 1)
        self.assertEqual(mirror.closed[0]["exit_reason"], "take_profit")
        self.assertEqual(mirror.closed[0]["pnl"], 100.0)
        self.assertEqual(mirror.closed[0]["pnl_pct"], 100.0)

    def test_malformed_ohlc_is_rejected(self):
        bad = bar(stamp(9, 45), 100.0, high=99.0, low=98.0)
        with self.assertRaises(ValueError):
            self.engine.on_tick_bar(bad, complete=True, historical=False)

    def test_ledger_contains_open_and_close_records(self):
        self.arm_short_and_touch()
        self.engine.on_tick_bar(
            bar(stamp(9, 45, 2), 97.75), complete=False, historical=False
        )
        self.engine.on_tick_bar(
            bar(stamp(9, 46), 95.75, high=97.75, low=95.75),
            complete=False,
            historical=False,
        )
        records = [
            json.loads(line)
            for line in Path(self.temp.name, "ledger.jsonl").read_text().splitlines()
        ]
        self.assertEqual([record["action"] for record in records], ["OPEN", "CLOSE"])

    def test_range_data_missed_when_window_closes_without_minute_bars(self):
        # No seed_opening_range() call: on_minute_bar() never fires, so
        # opening_high/opening_low stay None once the range window closes.
        self.engine.on_tick_bar(
            bar(stamp(9, 46), 100.0), complete=True, historical=False
        )
        self.assertEqual(self.engine.phase, "RANGE_DATA_MISSED")
        self.assertIn("RANGE_DATA_MISSED", [event.kind for event in self.engine.events])

    def test_range_data_missed_stays_building_range_before_window_closes(self):
        self.engine.on_tick_bar(
            bar(stamp(9, 40), 100.0), complete=True, historical=False
        )
        self.assertEqual(self.engine.phase, "BUILDING_RANGE")

    def test_session_done_takes_priority_over_range_data_missed_on_stale_bar(self):
        # A late bar can make _ensure_session() roll straight into a new
        # session whose own trade window has already elapsed too (wiping
        # opening_high/low back to None in the process). SESSION_DONE must
        # win over RANGE_DATA_MISSED in that case.
        self.seed_opening_range()
        self.seed_tick_history()
        self.engine.on_tick_bar(
            bar(stamp(10, 46), 98.0), complete=True, historical=False
        )
        self.assertEqual(self.engine.phase, "SESSION_DONE")

    def test_keltner_points_stable_when_window_rolls_forward(self):
        start = datetime(2026, 7, 20, 9, 45, tzinfo=ET)
        prices = [100.0 + (index % 7) * 0.3 for index in range(150)]
        for index, price in enumerate(prices):
            self.engine.on_tick_bar(
                bar((start + timedelta(seconds=index)).isoformat(), price),
                complete=True,
                historical=True,
            )
        first = self.engine._keltner_points(limit=10)
        first_by_time = {point["time"]: point["value"] for point in first["mid"]}

        for index, price in enumerate(prices[:5], start=150):
            self.engine.on_tick_bar(
                bar((start + timedelta(seconds=index)).isoformat(), price),
                complete=True,
                historical=True,
            )
        second = self.engine._keltner_points(limit=10)
        second_by_time = {point["time"]: point["value"] for point in second["mid"]}

        shared_times = set(first_by_time) & set(second_by_time)
        self.assertTrue(shared_times)
        for shared_time in shared_times:
            self.assertEqual(first_by_time[shared_time], second_by_time[shared_time])


if __name__ == "__main__":
    unittest.main()
