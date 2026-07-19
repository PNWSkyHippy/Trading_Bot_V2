"""Deterministic tests for venue-local live crypto quote selection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.crypto_quote import live_ticker_reference


class CryptoQuoteTests(unittest.TestCase):
    def test_live_book_mid_replaces_stale_last(self):
        ticker = {"last": 60.0, "bid": 119.0, "ask": 121.0}
        self.assertEqual(120.0, live_ticker_reference(ticker))

    def test_venue_last_is_fallback_when_book_is_unavailable(self):
        self.assertEqual(60.0, live_ticker_reference({"last": 60.0}))

    def test_crossed_or_invalid_book_does_not_create_a_midpoint(self):
        self.assertEqual(
            60.0,
            live_ticker_reference({"last": 60.0, "bid": 121.0, "ask": 119.0}),
        )
        self.assertIsNone(live_ticker_reference({"last": float("nan")}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
