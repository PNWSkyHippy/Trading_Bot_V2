import copy
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from emt_strategy import EMTStrategyEngine
from tradovate_executor import BrokerOrder, TradovateExecutor


PACIFIC = ZoneInfo("America/Los_Angeles")


def stamp(hour, minute, second=0):
    return datetime(
        2026, 7, 20, hour, minute, second, tzinfo=PACIFIC
    ).isoformat()


def bar(time_text, close, high=None, low=None, volume=610):
    return {
        "symbol": "ES 09-26",
        "time": time_text,
        "open": close,
        "high": close + 0.25 if high is None else high,
        "low": close - 0.25 if low is None else low,
        "close": close,
        "volume": volume,
        "bar_type": "tick",
        "bar_value": 610,
    }


class RecordingTradovate(TradovateExecutor):
    def __init__(self):
        super().__init__(
            access_token="test", account_id=123, account_spec="SIM123",
            environment="demo",
        )
        self.requests = []
        self.position_net = 0

    def _request(self, path, body=None, query=None):
        self.requests.append((path, copy.deepcopy(body), copy.deepcopy(query)))
        if path == "/contract/find":
            return {"id": 456, "name": "ESU6"}
        if path == "/position/list":
            return ([{"accountId": 123, "contractId": 456,
                      "netPos": self.position_net}]
                    if self.position_net else [])
        if path == "/orderStrategy/list":
            return []
        if path == "/orderStrategy/startorderstrategy":
            return {"orderStrategy": {"id": 987, "status": "ActiveStrategy"}}
        raise AssertionError(path)


class FakeExecutor:
    def __init__(self):
        self.orders = []
        self.status = "open"

    def place_bracket(self, **kwargs):
        self.orders.append(kwargs)
        return BrokerOrder(321, None, kwargs["symbol"], kwargs["direction"], 1)

    def strategy_status(self, strategy_id):
        assert strategy_id == 321
        return self.status


class EMTLiveTests(unittest.TestCase):
    def settings(self):
        return {
            "enabled": True,
            "paper_only": False,
            "symbol": "ES",
            "broker_symbol": "ESU6",
            "tick_bar_value": 610,
            "source_timezone": "America/Los_Angeles",
            "market_timezone": "America/Los_Angeles",
            "opening_range_start": "06:30",
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
            "broker_status_interval_seconds": 0,
            "ledger_path": "live-ledger.jsonl",
        }

    def seed_entry(self, engine):
        for minute in range(30, 45):
            engine.on_minute_bar(
                bar(stamp(6, minute), 100, high=101 if minute == 35 else 100.5,
                    low=99 if minute == 40 else 99.5, volume=100),
                historical=True,
            )
        start = datetime(2026, 7, 20, 6, 40, tzinfo=PACIFIC)
        for index in range(8):
            engine.on_tick_bar(
                bar((start + timedelta(seconds=index)).isoformat(), 98.5),
                complete=True, historical=True,
            )
        engine.on_tick_bar(bar(stamp(6, 45), 98.0), True, False)
        engine.on_tick_bar(bar(stamp(6, 45, 1), 98.35), False, False)
        engine.on_tick_bar(bar(stamp(6, 45, 2), 97.75), False, False)

    def test_api_credentials_acquire_token_for_unattended_startup(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"accessToken":"fresh-token","userStatus":"Active"}'

        credentials = {
            "name": "user", "password": "password", "appId": "EMT",
            "appVersion": "1.0", "cid": "123", "sec": "secret",
            "deviceId": "123e4567-e89b-12d3-a456-426614174000",
        }
        with mock.patch("urllib.request.urlopen", return_value=Response()) as opened:
            executor = TradovateExecutor(
                access_token="", account_id=123, account_spec="SIM123",
                environment="demo", credentials=credentials,
            )
        self.assertEqual(executor.access_token, "fresh-token")
        self.assertIn("/auth/accesstokenrequest", opened.call_args.args[0].full_url)

    def test_tradovate_payload_uses_eight_tick_server_bracket(self):
        executor = RecordingTradovate()
        accepted = executor.place_bracket(
            symbol="ESU6", direction="short", quantity=1,
            stop_points=2.0, target_points=2.0, tick_size=0.25,
            client_id="EMT-LIVE-1",
        )
        self.assertEqual(accepted.strategy_id, 987)
        path, body, _ = executor.requests[-1]
        self.assertEqual(path, "/orderStrategy/startorderstrategy")
        params = __import__("json").loads(body["params"])
        self.assertEqual(params["entryVersion"], {"orderQty": 1, "orderType": "Market"})
        self.assertEqual(params["brackets"][0]["profitTarget"], -8)
        self.assertEqual(params["brackets"][0]["stopLoss"], 8)

    def test_existing_position_blocks_duplicate_entry(self):
        executor = RecordingTradovate()
        executor.position_net = 1
        with self.assertRaisesRegex(Exception, "existing ESU6 position"):
            executor.place_bracket(
                symbol="ESU6", direction="long", quantity=1,
                stop_points=2.0, target_points=2.0, tick_size=0.25,
                client_id="EMT-LIVE-DUPLICATE",
            )
        self.assertFalse(any(
            path == "/orderStrategy/startorderstrategy"
            for path, _, _ in executor.requests
        ))

    def test_signal_submits_one_live_bracket_and_does_not_simulate_exit(self):
        fake = FakeExecutor()
        with tempfile.TemporaryDirectory() as temp:
            engine = EMTStrategyEngine(
                self.settings(), {"tick_size": 0.25, "tick_value": 12.5},
                temp, executor=fake,
            )
            self.seed_entry(engine)
            self.assertEqual(len(fake.orders), 1)
            self.assertEqual(fake.orders[0]["symbol"], "ESU6")
            self.assertEqual(engine.active_trade.broker_strategy_id, 321)
            engine.on_tick_bar(
                bar(stamp(6, 46), 95.0, high=100.0, low=94.0), False, False
            )
            self.assertIsNotNone(engine.active_trade)

    def test_broker_completion_rearms_at_new_low(self):
        fake = FakeExecutor()
        with tempfile.TemporaryDirectory() as temp:
            engine = EMTStrategyEngine(
                self.settings(), {"tick_size": 0.25, "tick_value": 12.5},
                temp, executor=fake,
            )
            self.seed_entry(engine)
            fake.status = "closed"
            engine.on_tick_bar(
                bar(stamp(6, 46), 96.0, high=98.0, low=95.75), False, False
            )
            self.assertIsNone(engine.active_trade)
            self.assertEqual(engine.phase, "WAIT_BREAKOUT")
            self.assertEqual(engine.support_level, 95.75)


if __name__ == "__main__":
    unittest.main(verbosity=2)
