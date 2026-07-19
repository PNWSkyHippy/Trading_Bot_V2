"""Offline regression tests for BreakoutSender containment and validation."""

from __future__ import annotations

import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import breakout_sender as sender_module


class _Response:
    status_code = 200

    @staticmethod
    def json():
        return {"accepted": False, "reason": "test", "trade_id": None}


def _payload(**overrides):
    data = {
        "symbol": "BTC/USD",
        "broker": "kraken",
        "source_broker": "kraken",
        "direction": "long",
        "asset_class": "crypto",
        "signal_source": "breakout_scanner",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry_price": 100.0,
        "current_price": 101.0,
        "move_pct": 1.0,
        "volume_spike": 2.0,
        "confidence": 0.8,
        "escalation": 2,
    }
    data.update(overrides)
    return data


def _signal(**overrides):
    data = {
        "symbol": "BTC/USD",
        "asset_type": SimpleNamespace(value="crypto"),
        "broker": "KRAKEN",
        "direction": "long",
        "timestamp": datetime.now(timezone.utc),
        "entry_price": 100.0,
        "current_price": 101.0,
        "best_move_pct": 1.0,
        "volume_spike": 2.0,
        "volume_history": [100.0] * 9 + [200.0],
        "enrichment": {},
        "momentum_score": 1.0,
        "confidence": 0.8,
        "pattern_detected": "early_breakout",
        "bars_since_breakout": 2,
        "breakout_level": 100.0,
        "distance_from_breakout_pct": 1.0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class BreakoutSenderSafetyTests(unittest.TestCase):
    def _sender(self, **config):
        outbox = tempfile.TemporaryDirectory(prefix="breakout-sender-test-")
        self.addCleanup(outbox.cleanup)
        values = {
            "bot_api_key": "test-key",
            "bot_enabled": True,
            "bot_min_escalation": 1,
            "bot_sender_queue_size": 8,
            "bot_sender_outbox_dir": outbox.name,
        }
        values.update(config)
        instance = sender_module.BreakoutSender(values)
        self.addCleanup(instance.close, True, 1.0)
        return instance

    def test_real_signal_liquidity_uses_current_price_and_history(self):
        instance = self._sender()
        with patch.object(instance, "_live_enabled", return_value=True):
            self.assertTrue(instance.should_send(_signal(), 2))
            self.assertFalse(instance.should_send(
                _signal(current_price=1.0, entry_price=1.0,
                        volume_history=[10.0] * 10),
                2,
            ))
            self.assertFalse(instance.should_send(
                _signal(volume_history=[]), 2
            ))

    def test_invalid_direction_and_nonfinite_values_are_rejected(self):
        instance = self._sender()
        self.assertIsNone(instance._validate_payload(_payload(direction="sideways")))
        self.assertIsNone(instance._validate_payload(_payload(current_price=float("nan"))))
        self.assertIsNone(instance._validate_payload(_payload(confidence=1.1)))
        self.assertIsNone(instance._validate_payload(_payload(timestamp="2026-01-01T00:00:00")))

    def test_normal_signal_build_uses_authoritative_asset_and_source_broker(self):
        instance = self._sender()
        payload = instance._build_payload(
            _signal(broker="COINGECKO"), 2, "long"
        )
        validated = instance._validate_payload(payload)
        self.assertIsNotNone(validated)
        self.assertEqual("crypto", validated["asset_class"])
        self.assertEqual("kraken", validated["broker"])
        self.assertEqual("coingecko", validated["source_broker"])

    def test_source_aware_atomic_dedup_keeps_distinct_escalations(self):
        instance = self._sender()
        calls = []

        def post(*_args, **kwargs):
            calls.append(kwargs["json"])
            return _Response()

        instance._session.post = post
        event = _payload(escalation=2)
        self.assertTrue(instance._reserve_and_enqueue(event))
        self.assertFalse(instance._reserve_and_enqueue(event))
        self.assertTrue(instance._reserve_and_enqueue({**event, "escalation": 3}))
        self.assertTrue(instance._reserve_and_enqueue({
            **event, "signal_source": "gap_scanner",
        }))
        instance._queue.join()
        self.assertEqual(3, len(calls))

    def test_concurrent_duplicate_reservation_enqueues_exactly_once(self):
        instance = self._sender()
        calls = []
        instance._session.post = lambda *_a, **kw: calls.append(kw["json"]) or _Response()
        barrier = threading.Barrier(8)
        results = []
        event = _payload()

        def submit():
            barrier.wait()
            results.append(instance._reserve_and_enqueue(event))

        threads = [threading.Thread(target=submit) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        instance._queue.join()
        self.assertEqual(1, sum(results))
        self.assertEqual(1, len(calls))

    def test_timeout_retries_reuse_exact_event_identity(self):
        instance = self._sender()
        attempts = 0
        event_ids = []

        def timeout(*_args, **kwargs):
            nonlocal attempts
            attempts += 1
            event_ids.append(kwargs["json"]["event_id"])
            raise sender_module.requests.exceptions.Timeout()

        instance._session.post = timeout
        self.assertTrue(instance._reserve_and_enqueue(_payload()))
        instance._queue.join()
        self.assertEqual(3, attempts)
        self.assertEqual(1, len(set(event_ids)))
        self.assertEqual(1, len(list(instance._outbox_dir.glob("*.json"))))

    def test_pending_outbox_restarts_with_same_event_id(self):
        outbox = tempfile.TemporaryDirectory(prefix="breakout-restart-test-")
        self.addCleanup(outbox.cleanup)
        config = {
            "bot_api_key": "test-key",
            "bot_enabled": True,
            "bot_min_escalation": 1,
            "bot_sender_queue_size": 8,
            "bot_sender_retry_attempts": 1,
            "bot_sender_outbox_dir": outbox.name,
        }
        first = sender_module.BreakoutSender(config)
        first._session.post = lambda *_a, **_kw: (_ for _ in ()).throw(
            sender_module.requests.exceptions.Timeout()
        )
        self.assertTrue(first._reserve_and_enqueue(_payload()))
        first._queue.join()
        records = list(Path(outbox.name).glob("*.json"))
        self.assertEqual(1, len(records))
        persisted_id = __import__("json").loads(
            records[0].read_text(encoding="utf-8")
        )["event_id"]
        first.close(True, 1.0)

        # Keep restored work queued until the fake transport is installed.
        with patch.object(sender_module.threading.Thread, "start", lambda _self: None):
            second = sender_module.BreakoutSender(config)
        restored = second._queue.get_nowait()
        self.assertEqual(persisted_id, restored["event_id"])
        second._queue.task_done()
        second._worker = None
        second.close(False, 0.0)

    def test_raw_payload_is_copied_before_worker_uses_it(self):
        instance = self._sender()
        release = threading.Event()
        seen = []

        def post(*_args, **kwargs):
            release.wait(1.0)
            seen.append(kwargs["json"])
            return _Response()

        instance._session.post = post
        raw = _payload()
        with patch.object(instance, "_live_enabled", return_value=True):
            instance.send_raw_payload(raw)
        raw["direction"] = "short"
        release.set()
        instance._queue.join()
        self.assertEqual("long", seen[0]["direction"])

    def test_kill_switch_read_error_fails_closed(self):
        instance = self._sender()
        import core.scanner_controls as controls
        with patch.object(controls, "is_scanner_enabled", side_effect=RuntimeError("locked")):
            self.assertFalse(instance._live_enabled())

    def test_worker_rechecks_kill_switch_before_post(self):
        instance = self._sender()
        calls = []
        instance._session.post = lambda *_a, **_kw: calls.append(True) or _Response()
        with patch.object(instance, "_live_enabled", return_value=False):
            instance._send_once(_payload())
        self.assertEqual([], calls)

    def test_close_stops_worker_and_rejects_new_work(self):
        instance = self._sender()
        instance.close(drain=True, timeout=1.0)
        self.assertFalse(instance._worker.is_alive())
        self.assertFalse(instance._reserve_and_enqueue(_payload()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
