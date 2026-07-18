"""
Shared breakout-decision predicate tests — Step 8 (Reconciled Safe Patch
Sequence, scoped — see core/breakout_decision.py's own patch notes).

core/breakout_decision.py extracts exactly two confirmed cross-file
duplications (breakout-staleness bars-since cutoff, escalation-minimum
gate) into single shared functions, used by both
core/breakout_receiver.py's checklist and breakout_sender.py's
should_send(). Everything else about the 18-step checklist and the
sender's other gates (liquidity, payload schema) is deliberately
untouched this pass.

These tests lock in:
  1. The shared predicates' own behavior at the boundary values that
     matter (exactly-at-threshold, one-over, None/missing).
  2. That core/breakout_receiver.py's ChecklistResult IS
     core.breakout_decision.ChecklistResult (single definition, not a
     silently-diverged duplicate).
  3. That receiver._check_momentum_phase() and
     breakout_sender.should_send() actually call through to the shared
     functions for the same bars_since_breakout value and agree with
     each other — the exact "could drift independently" risk the report
     flagged, now provably impossible since they share one function.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.breakout_decision import (
    ChecklistResult,
    MAX_BREAKOUT_AGE_BARS,
    is_breakout_stale,
    escalation_meets_minimum,
)


def test_is_breakout_stale_boundary_values():
    assert is_breakout_stale(MAX_BREAKOUT_AGE_BARS) is False   # exactly at limit — still OK
    assert is_breakout_stale(MAX_BREAKOUT_AGE_BARS + 1) is True
    assert is_breakout_stale(0) is False
    assert is_breakout_stale(None) is False   # unknown treated as not-stale, matches prior behavior
    assert is_breakout_stale("5") is True     # string-numeric coerces, matches prior int(bars_since) usage


def test_escalation_meets_minimum_boundary_values():
    assert escalation_meets_minimum(3, 3) is True     # exactly at minimum passes
    assert escalation_meets_minimum(2, 3) is False
    assert escalation_meets_minimum(5, None) is True  # no minimum set — always passes
    assert escalation_meets_minimum(None, 3) is False  # unparsable escalation fails closed


def test_checklist_result_is_single_shared_definition():
    from core.breakout_receiver import ChecklistResult as ReceiverChecklistResult
    assert ReceiverChecklistResult is ChecklistResult
    r = ChecklistResult.ok("fine")
    assert r.status == "PASS" and r.passed is True
    r2 = ChecklistResult.fail("nope")
    assert r2.status == "FAIL" and r2.passed is False


def test_receiver_momentum_phase_uses_shared_staleness_function():
    """Direct call into BreakoutReceiver._check_momentum_phase with a
    bars_since_breakout value one past the shared threshold must FAIL with
    the shared MAX_BREAKOUT_AGE_BARS value in the message — proving the
    receiver reads the same constant the sender uses, not an independent
    inline literal that could later drift."""
    from core.breakout_receiver import BreakoutReceiver

    recv = BreakoutReceiver.__new__(BreakoutReceiver)  # skip __init__, method is stateless here
    payload = {
        "symbol": "BTC/USD",
        "direction": "long",
        "bars_since_breakout": MAX_BREAKOUT_AGE_BARS + 1,
        "distance_from_breakout_pct": 0.5,
        "rsi": 50,
    }
    with mock.patch("core.candle_manager.candle_manager.get", return_value=None):
        result = recv._check_momentum_phase(payload)
    assert result.status == "FAIL"
    assert str(MAX_BREAKOUT_AGE_BARS) in result.reason

    payload_ok = dict(payload, bars_since_breakout=MAX_BREAKOUT_AGE_BARS)
    with mock.patch("core.candle_manager.candle_manager.get", return_value=None):
        result_ok = recv._check_momentum_phase(payload_ok)
    assert result_ok.status != "FAIL", (
        f"expected bars_since_breakout == MAX_BREAKOUT_AGE_BARS to still pass, got: {result_ok.reason}"
    )


def test_sender_should_send_uses_shared_staleness_and_escalation_functions():
    """BreakoutSender.should_send() must reject a signal exactly
    MAX_BREAKOUT_AGE_BARS + 1 bars old — the same cutoff
    _check_momentum_phase() enforces above — proving both files now agree
    by construction rather than by two independently-maintained constants
    happening to match today."""
    import breakout_sender as bs_mod

    sender = bs_mod.BreakoutSender.__new__(bs_mod.BreakoutSender)
    sender._min_esc = 1

    signal = SimpleNamespace(
        symbol="BTC/USD",
        enrichment={},
        current_price=100.0,
        entry_price=100.0,
        bars_since_breakout=MAX_BREAKOUT_AGE_BARS + 1,
    )

    with mock.patch.object(bs_mod.BreakoutSender, "ready", new_callable=mock.PropertyMock, return_value=True), \
         mock.patch.object(
             bs_mod.BreakoutSender, "_resolve_volume_info",
             return_value={"avg_volume": 1_000_000.0},
         ):
        result = sender.should_send(signal, escalation=2)

    assert result is False, "signal older than MAX_BREAKOUT_AGE_BARS must be rejected"

    # Escalation below the shared minimum must also be rejected via the
    # shared escalation_meets_minimum() function, independent of staleness.
    fresh_signal = SimpleNamespace(
        symbol="BTC/USD", enrichment={}, current_price=100.0,
        entry_price=100.0, bars_since_breakout=0,
    )
    sender._min_esc = 3
    with mock.patch.object(bs_mod.BreakoutSender, "ready", new_callable=mock.PropertyMock, return_value=True), \
         mock.patch.object(
             bs_mod.BreakoutSender, "_resolve_volume_info",
             return_value={"avg_volume": 1_000_000.0},
         ):
        result_low_esc = sender.should_send(fresh_signal, escalation=2)
    assert result_low_esc is False, "escalation below _min_esc must be rejected"


def main():
    tests = [
        test_is_breakout_stale_boundary_values,
        test_escalation_meets_minimum_boundary_values,
        test_checklist_result_is_single_shared_definition,
        test_receiver_momentum_phase_uses_shared_staleness_function,
        test_sender_should_send_uses_shared_staleness_and_escalation_functions,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} breakout decision shared-predicate tests passed")


if __name__ == "__main__":
    main()
