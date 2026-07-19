"""Offline contract tests for producer-owned breakout event identity."""

from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep imports offline and point every incidental DB singleton at scratch.
_dotenv = types.ModuleType("dotenv")
_dotenv.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", _dotenv)
_keyring = types.ModuleType("keyring")
_keyring.get_password = lambda *_a, **_k: None
sys.modules.setdefault("keyring", _keyring)

import config

_tmp = tempfile.TemporaryDirectory(prefix="breakout-producer-contract-")
config.DB_PATH = os.path.join(_tmp.name, "identity.db")
config.IBKR_ENABLED = False

from core.event_identity import derive_breakout_event_ids
from scanners.base_scanner import BaseEventScanner
import scanners.base_scanner as base_scanner_module
import breakout_sender
import api_server


class _Receiver:
    def __init__(self):
        self.payloads = []

    def receive_signal(self, payload, **_kwargs):
        self.payloads.append(dict(payload))
        return {"accepted": False, "reason": "contract reached receiver"}


def _direct_payload(source: str, timestamp: str) -> dict:
    return {
        "symbol": "TEST/USD",
        "broker": "kraken",
        "direction": "long",
        "asset_class": "crypto",
        "entry_price": 100.0,
        "current_price": 100.0,
        "move_pct": 2.0,
        "volume_spike": 2.0,
        "confidence": 0.8,
        "escalation": 1,
        "timestamp": timestamp,
        "signal_source": source,
    }


class ProducerIdentityTests(unittest.TestCase):
    def test_root_and_escalation_child_semantics(self):
        recognized = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
        root2, child2 = derive_breakout_event_ids(
            "breakout_scanner", recognized, "BTC/USD", "long", "escalation:2"
        )
        root2b, child2b = derive_breakout_event_ids(
            "breakout_scanner", recognized, "BTC/USD", "long", "escalation:2"
        )
        root3, child3 = derive_breakout_event_ids(
            "breakout_scanner", recognized, "BTC/USD", "long", "escalation:3"
        )
        self.assertEqual((root2, child2), (root2b, child2b))
        self.assertEqual(root2, root3)
        self.assertNotEqual(child2, child3)

    def test_separate_semantic_events_do_not_collide(self):
        first = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
        second = first + timedelta(microseconds=1)
        self.assertNotEqual(
            derive_breakout_event_ids("nr7_scanner", first, "MSFT", "long", "daily")[1],
            derive_breakout_event_ids("nr7_scanner", second, "MSFT", "long", "daily")[1],
        )

    def test_direct_scanner_families_reach_receiver_with_identity(self):
        receiver = _Receiver()
        scanner = BaseEventScanner("ContractScanner")
        scanner.set_receiver(receiver)
        when = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc).isoformat()
        sources = (
            "nr7_scanner", "funding_scanner", "gap_scanner",
            "volume_surge", "breakout_scanner",
        )
        with patch.object(base_scanner_module, "is_scanner_enabled", return_value=True):
            for source in sources:
                scanner.push_signal(_direct_payload(source, when))
        self.assertEqual(len(sources), len(receiver.payloads))
        for payload in receiver.payloads:
            self.assertTrue(payload["event_id"])
            self.assertTrue(payload["root_event_id"])

    def test_standard_sender_to_api_model_to_receiver_contract(self):
        outbox = tempfile.TemporaryDirectory(prefix="identity-sender-")
        self.addCleanup(outbox.cleanup)
        sender = breakout_sender.BreakoutSender({
            "bot_api_key": "test",
            "bot_sender_outbox_dir": outbox.name,
        })
        self.addCleanup(sender.close, True, 1.0)
        recognized = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
        signal = SimpleNamespace(
            symbol="BTC/USD",
            asset_type=SimpleNamespace(value="crypto"),
            broker="KRAKEN",
            direction="long",
            timestamp=recognized,
            entry_price=100.0,
            current_price=101.0,
            best_move_pct=1.0,
            volume_spike=2.0,
            volume_history=[100.0] * 9 + [200.0],
            enrichment={},
            momentum_score=1.0,
            confidence=0.8,
            pattern_detected="early_breakout",
            bars_since_breakout=2,
            breakout_level=100.0,
            distance_from_breakout_pct=1.0,
        )
        built = sender._build_payload(signal, 2, "long")
        model = api_server.BreakoutSignalPayload.model_validate(built)
        fake = _Receiver()
        with patch.object(api_server, "breakout_receiver", fake), patch.object(
            api_server, "API_KEY", ""
        ):
            result = api_server.receive_breakout_signal(model, x_api_key=None)
        self.assertEqual("contract reached receiver", result["reason"])
        self.assertEqual(built["event_id"], fake.payloads[0]["event_id"])
        self.assertEqual(built["root_event_id"], fake.payloads[0]["root_event_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
