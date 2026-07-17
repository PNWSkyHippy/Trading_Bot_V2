"""Deterministic, offline regression tests for BreakoutScanner audit fixes."""

from __future__ import annotations

import ast
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import BreakoutScanner as scanner


def _bar(symbol: str, index: int, price: float, volume: float = 100.0):
    return scanner.PriceData(
        symbol=symbol,
        price=price,
        open_price=price,
        high=price,
        low=price,
        volume=volume,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index),
        asset_type=scanner.AssetType.CRYPTO if "/" in symbol else scanner.AssetType.STOCK,
    )


class _Config:
    def get(self, key, default=None):
        return default


class BreakoutScannerSafetyTests(unittest.TestCase):
    def test_dead_auto_trader_is_absent(self):
        source = Path(scanner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        self.assertNotIn("TradingEngine", class_names)
        for removed in (
            "enable_auto_trade",
            "auto_trade_without_confirm",
            "default_trade_amount_usd",
            "max_position_size_usd",
            "stop_loss_percent",
            "take_profit_percent",
        ):
            self.assertNotIn(removed, scanner.DEFAULT_CONFIG)
        self.assertNotIn("self.trading", source)
        self.assertNotIn("_toggle_auto_trade", source)

    def test_history_replay_is_idempotent_and_overlap_merges(self):
        detector = scanner.BreakoutDetector(_Config())
        first = [_bar("BTC/USD", i, 100 + i) for i in range(100)]
        detector.merge_history(first)
        detector.merge_history(first)
        self.assertEqual(100, len(detector.price_history["BTC/USD"]))
        self.assertEqual(list(range(100, 200)), list(detector.price_history["BTC/USD"]))

        overlap = [_bar("BTC/USD", i, 100 + i) for i in range(50, 102)]
        detector.merge_history(overlap)
        self.assertEqual(102, len(detector.price_history["BTC/USD"]))
        self.assertEqual(201, detector.price_history["BTC/USD"][-1])

    def test_same_timestamp_revision_replaces_bar(self):
        detector = scanner.BreakoutDetector(_Config())
        detector.merge_history([_bar("AAPL", 1, 100.0, 10.0)])
        detector.merge_history([_bar("AAPL", 1, 101.0, 20.0)])
        self.assertEqual([101.0], list(detector.price_history["AAPL"]))
        self.assertEqual([20.0], list(detector.volume_history["AAPL"]))

    def test_history_is_chronological_and_bounded(self):
        detector = scanner.BreakoutDetector(_Config())
        bars = [_bar("ETH/USD", i, float(i + 1)) for i in reversed(range(250))]
        detector.merge_history(bars)
        self.assertEqual(200, len(detector.price_history["ETH/USD"]))
        self.assertEqual(51.0, detector.price_history["ETH/USD"][0])
        self.assertEqual(250.0, detector.price_history["ETH/USD"][-1])

    def test_direction_is_tri_state_and_never_defaults_long(self):
        self.assertEqual("long", scanner.resolved_direction("LONG", -99))
        self.assertEqual("short", scanner.resolved_direction("short", 99))
        self.assertEqual("long", scanner.resolved_direction("", 0.51))
        self.assertEqual("short", scanner.resolved_direction("", -0.51))
        for value in (0.5, -0.5, 0, float("nan"), "bad"):
            self.assertEqual("", scanner.resolved_direction("", value))
        self.assertEqual(0.0, scanner.favorable_move_pct("unknown", 9.0))

    def test_directional_helpers_are_mirrored(self):
        detector = scanner.BreakoutDetector(_Config())
        up = [100.0] * 8 + [100.0, 101.0, 102.0]
        down = [100.0] * 8 + [100.0, 99.0, 98.0]
        self.assertTrue(detector._expanding(up, "long"))
        self.assertTrue(detector._expanding(down, "short"))
        self.assertFalse(detector._expanding(up, "short"))
        self.assertFalse(detector._expanding(down, "long"))

        plus_nine = [100.0] * 9 + [109.0]
        minus_nine = [100.0] * 9 + [91.0]
        self.assertFalse(detector._not_overextended(plus_nine))
        self.assertFalse(detector._not_overextended(minus_nine))

    def test_neutral_momentum_produces_no_signal(self):
        detector = scanner.BreakoutDetector(_Config())
        flat = [_bar("AAPL", i, 100.0, 100.0) for i in range(30)]
        detector.merge_history(flat)
        with patch.object(scanner, "PATTERNS_AVAILABLE", False):
            self.assertIsNone(detector.detect_breakout(_bar("AAPL", 31, 100.0, 100.0)))

    def test_stock_movers_include_large_decliners(self):
        fetcher = scanner.StockDataFetcher.__new__(scanner.StockDataFetcher)
        fetcher.api = None
        candidates = [
            _bar("UP", 1, 110.0),
            scanner.PriceData("DOWN", 80.0, 100.0, 100.0, 80.0, 100.0,
                              datetime.now(timezone.utc), scanner.AssetType.STOCK),
            _bar("SMALL", 1, 105.0),
        ]
        candidates[0].open_price = 100.0
        candidates[2].open_price = 100.0
        with patch.object(scanner, "YFINANCE_AVAILABLE", True), \
             patch.object(fetcher, "_yfinance_movers", return_value=candidates), \
             patch.object(scanner, "load_injected_stock_symbols", return_value=[]):
            result = fetcher.get_top_movers(count=2)
        self.assertEqual(["DOWN", "UP"], [item.symbol for item in result])

    def test_csv_persists_direction_and_writes_valid_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "signals.csv"
            signal = scanner.BreakoutSignal(
                symbol="ETH/USD",
                asset_type=scanner.AssetType.CRYPTO,
                current_price=100.0,
                predicted_move_pct=5.0,
                confidence=0.8,
                volume_spike=2.0,
                momentum_score=-1.0,
                pattern_detected="early_breakout",
                timestamp=datetime.now(timezone.utc),
                broker="KRAKEN",
                entry_price=100.0,
                direction="short",
            )
            with patch.object(scanner, "CSV_FILE", csv_path):
                scanner.log_signal_to_csv(signal)
                rows = scanner._load_csv()
            self.assertEqual("SHORT", rows[0]["Direction"])
            self.assertEqual(scanner.CSV_FIELDS, list(rows[0].keys()))

    def test_alert_start_is_idempotent_and_stop_joins(self):
        class _Sender:
            pass

        with patch.object(scanner, "BreakoutSender", return_value=_Sender()):
            alerts = scanner.AlertSystem(_Config())
            alerts.start()
            first_thread = alerts.alert_thread
            alerts.start()
            self.assertIs(first_thread, alerts.alert_thread)
            self.assertTrue(first_thread.is_alive())
            alerts.stop()
            self.assertFalse(first_thread.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
