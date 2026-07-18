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


if __name__ == "__main__":
    unittest.main(verbosity=2)
