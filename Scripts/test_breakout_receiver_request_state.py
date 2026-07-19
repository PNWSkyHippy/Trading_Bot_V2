"""Regression tests for request-local BreakoutReceiver checklist state."""

from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config

config.IBKR_ENABLED = False

from core.breakout_receiver import BreakoutReceiver, ChecklistResult


class BreakoutReceiverRequestStateTests(unittest.TestCase):
    def test_crypto_reverify_uses_exact_source_exchange_not_generic_ticker(self):
        class FakeExchange:
            symbols = ["ESPORTS/USD"]

            def fetch_ticker(self, _symbol):
                return {"last": 0.0100, "bid": 0.0203, "ask": 0.0205}

        class FakeCryptoScanner:
            exchanges = {"KRAKEN": FakeExchange()}
            exchange = None
            exchange_name = "KRAKEN"

        class FakeMarketScanner:
            crypto_scanner = FakeCryptoScanner()
            generic_calls = 0

            def get_current_price(self, _symbol, _asset_class):
                self.generic_calls += 1
                return 0.000028  # Same ticker, different CoinGecko asset.

        scanner = FakeMarketScanner()
        receiver = BreakoutReceiver()
        receiver._scanner_ref = scanner
        payload = {
            "symbol": "ESPORTS/USD",
            "asset_class": "crypto",
            "broker": "kraken",
            "source_broker": "kraken",
        }

        self.assertEqual(0.0204, receiver._fetch_live_price_from_scanner(payload))
        self.assertEqual(0, scanner.generic_calls)

    def test_non_execution_crypto_source_fails_identity_check(self):
        receiver = BreakoutReceiver()
        receiver._scanner_ref = object()
        payload = {
            "symbol": "TOKEN/USD",
            "asset_class": "crypto",
            "broker": "kraken",
            "source_broker": "coingecko",
            "direction": "long",
            "current_price": 1.0,
        }

        result = receiver._check_price_still_moving(payload)

        self.assertEqual(ChecklistResult.FAIL, result.status)
        self.assertIn("cannot verify identity", result.reason)

    def test_concurrent_price_drift_state_stays_on_its_own_payload(self):
        receiver = BreakoutReceiver()
        receiver._scanner_ref = object()
        prices = {"AAA": 90.0, "BBB": 110.0}
        receiver._fetch_live_price_from_scanner = lambda payload: prices[payload["symbol"]]
        payloads = [
            {
                "symbol": "AAA", "direction": "long",
                "source_price": 100.0, "current_price": 100.0,
            },
            {
                "symbol": "BBB", "direction": "short",
                "source_price": 100.0, "current_price": 100.0,
            },
        ]
        barrier = threading.Barrier(2)
        results = []

        def run(payload):
            barrier.wait()
            results.append(receiver._check_price_still_moving(payload))

        threads = [threading.Thread(target=run, args=(payload,)) for payload in payloads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertTrue(all(result.status == ChecklistResult.FAIL for result in results))
        self.assertEqual(90.0, payloads[0]["_drift_state"]["live_price"])
        self.assertEqual(-10.0, payloads[0]["_drift_state"]["drift_pct"])
        self.assertEqual(110.0, payloads[1]["_drift_state"]["live_price"])
        self.assertEqual(10.0, payloads[1]["_drift_state"]["drift_pct"])
        self.assertFalse(hasattr(receiver, "_drift_state"))

    def test_null_optional_flip_telemetry_does_not_crash_receiver(self):
        receiver = BreakoutReceiver.__new__(BreakoutReceiver)
        receiver._run_checklist = lambda _payload, _age: (
            [ChecklistResult.fail("expected test rejection")], []
        )
        payload = {
            "symbol": "KGEN/USD",
            "direction": "long",
            "volume_spike": 3.02,
            "momentum_score": None,
            "candle_open": 0.20,
            "distance_from_breakout_pct": None,
        }

        result = receiver._try_direction_flip(
            payload=payload,
            live_price=0.1895,
            drift_pct=-3.33,
            signal_age_sec=5.0,
            event_id="evt-kgen-null-momentum",
            client_order_id="bo-kgen-null-momentum",
        )

        self.assertIsNotNone(result)
        self.assertFalse(result["accepted"])
        self.assertEqual("flip_checklist_rejected", result["failure_class"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
