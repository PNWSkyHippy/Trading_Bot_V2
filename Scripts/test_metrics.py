"""
Deterministic tests for core/metrics.py (Patch A telemetry).

Covers: counter increment/snapshot/reset, and alert_gate_failure()'s
rate-limiting behavior (always counts + logs, but only actually sends an
external alert once per config.GATE_FAILURE_ALERT_COOLDOWN_SEC per category).

IMPORTANT: every test mocks reporting.alerts.alert_manager.trading_halted so
no test ever attempts a real email/SMS send. Do not remove that mock — see
Scripts/test_stock_calendar_authority.py's module docstring for why this
matters (an earlier ad-hoc script skipped it and triggered a real, if failed,
SMTP attempt against this system's actual configured credentials).

Runnable directly (`python Scripts/test_metrics.py`) or via pytest.
"""

import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import metrics


def _mock_alerts():
    return mock.patch("reporting.alerts.alert_manager.trading_halted")


def test_increment_and_snapshot():
    metrics.reset()
    metrics.increment("foo")
    metrics.increment("foo")
    metrics.increment("bar", 5)
    snap = metrics.get_snapshot()
    assert snap["foo"] == 2
    assert snap["bar"] == 5


def test_reset_clears_counters_and_cooldowns():
    metrics.reset()
    metrics.increment("foo")
    with _mock_alerts():
        metrics.alert_gate_failure("cat", "reason", now_epoch=1000)
    metrics.reset()
    assert metrics.get_snapshot() == {}
    # Cooldown state must also be cleared: an immediate re-alert at the same
    # epoch after reset should send again, not be suppressed by stale state.
    with _mock_alerts() as m:
        metrics.alert_gate_failure("cat", "reason", now_epoch=1000)
        m.assert_called_once()


def test_alert_gate_failure_always_counts_and_logs():
    metrics.reset()
    with _mock_alerts():
        metrics.alert_gate_failure("calendar", "stale schedule", now_epoch=1000)
        metrics.alert_gate_failure("calendar", "stale schedule", now_epoch=1001)
        metrics.alert_gate_failure("calendar", "stale schedule", now_epoch=1002)
    assert metrics.get_snapshot()["gate_failure.calendar"] == 3


def test_alert_gate_failure_rate_limits_external_send():
    metrics.reset()
    with _mock_alerts() as m:
        first = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        second = metrics.alert_gate_failure("calendar", "reason", now_epoch=1001)  # 1s later, within cooldown
        assert first is True
        assert second is False
        assert m.call_count == 1


def test_alert_gate_failure_sends_again_after_cooldown_elapses():
    metrics.reset()
    cooldown = __import__("config").GATE_FAILURE_ALERT_COOLDOWN_SEC
    with _mock_alerts() as m:
        first = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        second = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000 + cooldown + 1)
        assert first is True
        assert second is True
        assert m.call_count == 2


def test_alert_gate_failure_cooldown_is_per_category():
    metrics.reset()
    with _mock_alerts() as m:
        a = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        b = metrics.alert_gate_failure("broker_position", "other reason", now_epoch=1000)
        assert a is True
        assert b is True  # different category, not subject to calendar's cooldown
        assert m.call_count == 2


def test_alert_gate_failure_delivery_exception_does_not_raise():
    metrics.reset()
    with mock.patch("reporting.alerts.alert_manager.trading_halted", side_effect=RuntimeError("smtp down")):
        result = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        assert result is False  # delivery failed, but the call itself must not raise


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} metrics tests passed")


if __name__ == "__main__":
    main()
