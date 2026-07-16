"""
Deterministic tests for core/metrics.py (Patch A telemetry).

Covers: counter increment/snapshot/reset, and alert_gate_failure()'s
rate-limiting behavior — always counts + logs, but only actually sends an
external alert once per config.GATE_FAILURE_ALERT_COOLDOWN_SEC per category
— AND the corrected retry semantics: a FAILED delivery must not consume the
cooldown window, so the very next call retries rather than being silently
suppressed for the full cooldown despite nothing ever having been delivered.

IMPORTANT: every test mocks reporting.alerts.alert_manager.gate_failure (the
dedicated gate-failure alert method — distinct from trading_halted()) so no
test ever attempts a real email/SMS send. Do not remove that mock — see
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


def _mock_gate_alert(return_value=True, side_effect=None):
    if side_effect is not None:
        return mock.patch("reporting.alerts.alert_manager.gate_failure", side_effect=side_effect)
    return mock.patch("reporting.alerts.alert_manager.gate_failure", return_value=return_value)


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
    with _mock_gate_alert(return_value=True):
        metrics.alert_gate_failure("cat", "reason", now_epoch=1000)
    metrics.reset()
    assert metrics.get_snapshot() == {}
    # Cooldown state must also be cleared: an immediate re-alert at the same
    # epoch after reset should send again, not be suppressed by stale state.
    with _mock_gate_alert(return_value=True) as m:
        metrics.alert_gate_failure("cat", "reason", now_epoch=1000)
        m.assert_called_once()


def test_alert_gate_failure_always_counts_and_logs_even_when_delivery_fails():
    metrics.reset()
    with _mock_gate_alert(return_value=False):
        metrics.alert_gate_failure("calendar", "stale schedule", now_epoch=1000)
        metrics.alert_gate_failure("calendar", "stale schedule", now_epoch=1001)
        metrics.alert_gate_failure("calendar", "stale schedule", now_epoch=1002)
    assert metrics.get_snapshot()["gate_failure.calendar"] == 3


def test_alert_gate_failure_rate_limits_external_send_on_success():
    metrics.reset()
    with _mock_gate_alert(return_value=True) as m:
        first = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        second = metrics.alert_gate_failure("calendar", "reason", now_epoch=1001)  # 1s later, within cooldown
        assert first is True
        assert second is False
        assert m.call_count == 1


def test_alert_gate_failure_sends_again_after_cooldown_elapses():
    metrics.reset()
    cooldown = __import__("config").GATE_FAILURE_ALERT_COOLDOWN_SEC
    with _mock_gate_alert(return_value=True) as m:
        first = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        second = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000 + cooldown + 1)
        assert first is True
        assert second is True
        assert m.call_count == 2


def test_alert_gate_failure_cooldown_is_per_category():
    metrics.reset()
    with _mock_gate_alert(return_value=True) as m:
        a = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        b = metrics.alert_gate_failure("broker_position", "other reason", now_epoch=1000)
        assert a is True
        assert b is True  # different category, not subject to calendar's cooldown
        assert m.call_count == 2


def test_alert_gate_failure_delivery_exception_does_not_raise():
    """Defensive backstop: even if gate_failure() unexpectedly raises
    (a coding error, not a normal delivery failure — those are supposed to
    return False, not raise), alert_gate_failure() itself must not raise."""
    metrics.reset()
    with _mock_gate_alert(side_effect=RuntimeError("unexpected bug")):
        result = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        assert result is False


def test_failed_delivery_does_not_consume_cooldown_and_retries_immediately():
    """The corrected retry semantics, the crux of this fix: a FAILED
    delivery (gate_failure() returns False, e.g. an SMTP outage) must not
    block the very next call from retrying, even immediately (well within
    what would be the cooldown window). The old behavior consumed the
    cooldown on any attempt, so a single failure would black out real alerts
    for the entire cooldown window despite zero successful deliveries."""
    metrics.reset()
    with _mock_gate_alert(return_value=False) as m:
        first = metrics.alert_gate_failure("calendar", "reason", now_epoch=1000)
        assert first is False
        # Immediately after — well within the cooldown window — must still attempt.
        second = metrics.alert_gate_failure("calendar", "reason", now_epoch=1001)
        assert second is False
        assert m.call_count == 2  # both attempts actually reached gate_failure()

    # Once delivery starts succeeding, it sends and THEN the cooldown applies.
    with _mock_gate_alert(return_value=True) as m:
        third = metrics.alert_gate_failure("calendar", "reason", now_epoch=1002)
        assert third is True
        fourth = metrics.alert_gate_failure("calendar", "reason", now_epoch=1003)
        assert fourth is False  # now correctly suppressed by the cooldown
        assert m.call_count == 1  # only the successful attempt was made; the
        # 4th call was suppressed before ever calling gate_failure() again


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} metrics tests passed")


if __name__ == "__main__":
    main()
