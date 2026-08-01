"""Focused regression tests for crypto monitor quote-unavailable containment.

No network calls, production database access, or broker orders occur.  The
state database is disposable and every quote source is a deterministic fake.
"""

import os
import sys
import tempfile
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_TEMP_ROOT = tempfile.TemporaryDirectory(prefix="kraken-price-unavailable-")

import config

config.DB_PATH = os.path.join(_TEMP_ROOT.name, "module-import.db")
config.IBKR_ENABLED = False
config.KRAKEN_ENABLED = True
config.KRAKEN_PAPER_MODE = True

import core.position_monitor as position_monitor_module
from core.position_monitor import PositionMonitor
from data.database import Database


class FakeKraken:
    def __init__(self, price=None, error=None):
        self.price = price
        self.error = error
        self.price_calls = 0
        self.close_calls = 0

    def get_current_price(self, _symbol):
        self.price_calls += 1
        if self.error:
            raise self.error
        return self.price

    def close_position(self, *_args, **_kwargs):
        self.close_calls += 1
        raise AssertionError("quote-unavailable containment must never close")


class FakeExecutor:
    def __init__(self, kraken):
        self.kraken = kraken


def make_database(name):
    return Database(os.path.join(_TEMP_ROOT.name, f"{name}.db"))


def make_trade(trade_id="T-QUOTE"):
    return {
        "trade_id": trade_id,
        "symbol": "BOME/USD",
        "asset_class": "crypto",
        "direction": "long",
        "entry_price": 0.000536,
        "quantity": 100.0,
        "stop_loss": 0.000528,
    }


def test_valid_scanner_quote_clears_only_price_marker_without_broker_call():
    database = make_database("scanner-valid")
    trade = make_trade()
    state_key = "kraken_price_unavailable_T-QUOTE"
    database.set_state(state_key, {"consecutive_failures": 3})
    database.set_state("kraken_full_reconcile_T-QUOTE", {"required": True})
    kraken = FakeKraken(price=0.0005)
    monitor = PositionMonitor(db_ref=database, trade_executor=FakeExecutor(kraken))

    assert monitor._resolve_crypto_quote_or_hold(trade, 0.00055) == 0.00055
    assert database.get_state(state_key) == 0
    assert database.get_state("kraken_full_reconcile_T-QUOTE") == {"required": True}
    assert kraken.price_calls == 0
    assert kraken.close_calls == 0


def test_broker_fallback_clears_marker_and_preserves_monitoring():
    database = make_database("broker-fallback")
    trade = make_trade()
    state_key = "kraken_price_unavailable_T-QUOTE"
    database.set_state(state_key, {"consecutive_failures": 2})
    kraken = FakeKraken(price=0.00054)
    monitor = PositionMonitor(db_ref=database, trade_executor=FakeExecutor(kraken))

    assert monitor._resolve_crypto_quote_or_hold(trade, None) == 0.00054
    assert database.get_state(state_key) == 0
    assert kraken.price_calls == 1
    assert kraken.close_calls == 0


def test_dual_source_failure_persists_one_threshold_alert_without_close():
    database = make_database("dual-failure")
    trade = make_trade()
    kraken = FakeKraken(price=None)
    monitor = PositionMonitor(db_ref=database, trade_executor=FakeExecutor(kraken))
    alerts = []
    original_alert = position_monitor_module.metrics.alert_gate_failure
    original_threshold = config.CRYPTO_PRICE_UNAVAILABLE_ALERT_AFTER_CYCLES
    config.CRYPTO_PRICE_UNAVAILABLE_ALERT_AFTER_CYCLES = 3
    position_monitor_module.metrics.alert_gate_failure = (
        lambda category, reason: alerts.append((category, reason)) or True
    )
    try:
        for _ in range(4):
            assert monitor._resolve_crypto_quote_or_hold(trade, None) is None
    finally:
        position_monitor_module.metrics.alert_gate_failure = original_alert
        config.CRYPTO_PRICE_UNAVAILABLE_ALERT_AFTER_CYCLES = original_threshold

    marker = database.get_state("kraken_price_unavailable_T-QUOTE")
    assert marker["consecutive_failures"] == 4
    assert marker["symbol"] == "BOME/USD"
    assert marker["scanner_diagnostic"] == "unavailable"
    assert marker["broker_diagnostic"] == "unavailable"
    assert marker["manual_reconciliation_required"] is True
    assert marker["first_seen"] and marker["last_seen"]
    assert [category for category, _reason in alerts] == ["kraken_price_unavailable"]
    assert kraken.price_calls == 4
    assert kraken.close_calls == 0
    assert trade["quantity"] == 100.0


TESTS = [
    test_valid_scanner_quote_clears_only_price_marker_without_broker_call,
    test_broker_fallback_clears_marker_and_preserves_monitoring,
    test_dual_source_failure_persists_one_threshold_alert_without_close,
]


def main():
    passed = 0
    try:
        for test in TESTS:
            test()
            passed += 1
            print(f"PASS {test.__name__}")
    finally:
        _TEMP_ROOT.cleanup()
    print(f"{passed}/{len(TESTS)} Kraken price-unavailable tests passed")


if __name__ == "__main__":
    main()
