"""
core/breakout_decision.py
==========================
Shared, pure decision predicates for the breakout signal pipeline.

Step 8 of the Reconciled Safe Patch Sequence
(reports/agent_pipeline/20260717-085541/final_unified_report.md §6 item 8)
calls for extracting the receiver's checklist and the sender's signal logic
into explicit, side-effect-free decision functions usable by both the live
path and a future backtester replay lane, instead of maintaining the same
threshold in multiple files where it can silently drift.

PATCH NOTES — 2026-07-18, Step 8 (SCOPED, not the full item-8 vision).
Applied by agent (Ron reviewing before commit; 3-Way Standoff Review
explicitly waived for this item by Ron due to resource constraints — the
2026-07-18 commit that pushed Steps 1-6b to origin/main is the designated
rollback point if anything here causes issues).

Why scoped down: `core/breakout_receiver.py`'s 18-step checklist is deeply
entangled with live side effects — DB reads/writes (open-trade counts,
daily-loss streaks, session halt state, AI-signal-review logging), a
class-level slot-reservation lock that is itself part of a check's "pass"
path, live network price re-fetches, and payload mutations consumed by
later steps (drift state, cooldown bypass, structural-stop fallback). A
full mechanical extraction of all 18 checks into one "pure" function in a
single autonomous pass — on a live-money entry-signal engine, with no
second reviewer — is exactly the risk class the 3-Way Standoff Review
exists to catch. Rather than accept that risk to hit the report's full
"one function for both live and replay" vision in one shot, this patch:

  1. Creates this module and moves `ChecklistResult` here as the one
     canonical definition (previously defined only inside
     breakout_receiver.py).
  2. Extracts ONLY the concrete, confirmed duplications the report's own
     mapping identified as literally the same threshold maintained in two
     files with real drift risk:
       - breakout-staleness (`bars_since_breakout` vs a max-bars cutoff):
         previously `MAX_BARS_SINCE = 3` inline in
         breakout_receiver.py::_check_momentum_phase, and separately
         `MAX_BREAKOUT_AGE_BARS = 3` as a class constant in
         breakout_sender.py::BreakoutSender.should_send. Same semantic
         check, same value, two independent constants.
       - escalation-minimum gate: previously `esc < min_escalation` inline
         in breakout_receiver.py::receive_signal, and separately
         `escalation < self._min_esc` in
         breakout_sender.py::BreakoutSender.should_send.
     Both are now single functions here; both files import and call them
     instead of re-deriving the comparison. Values are UNCHANGED (3 bars,
     same escalation semantics) — this is a single-source-of-truth move,
     not a threshold change.
  3. Leaves every side-effecting step (DB reads/writes, network price
     fetch, slot reservation, payload mutation, AI-signal-review logging)
     exactly where and in what order it already ran — nothing about when
     or how those happen has changed.
  4. Does NOT wire this into `intelligence/backtester.py`. Per the
     Step-8-prep investigation, breakout signals are not currently
     injected into the backtester's replay path at all (no
     `breakout_scanner`/`BreakoutStrategy` reference anywhere in
     backtester.py) — building that "replay lane" is new backtester
     functionality on top of an already-large item, not a refactor of
     something that already runs in both places, and deserves its own
     dedicated design pass rather than being bundled in here.
  5. Deliberately does NOT unify the sender's liquidity filter
     (MIN_USD_VOLUME_PER_CANDLE), the sender's `_validate_payload()`
     schema check, or the receiver's `VOLUME_SPIKE_MIN` volume-elevated
     check with `WatchlistManager.check`'s `momentum_gate_vol_min` — these
     look similar but serve different purposes at different thresholds
     (initial-signal-generation gate vs. pre-entry confirmation gate vs.
     transport-layer liquidity floor); forcibly merging them without
     verifying they were ever meant to be identical risks changing which
     signals pass, which is a much larger and riskier change than fixing
     a confirmed accidental duplication.

Back out: delete this file; in core/breakout_receiver.py, restore the
inline `ChecklistResult` class definition and the inline
`MAX_BARS_SINCE = 3` / `esc < min_escalation` comparisons; in
breakout_sender.py, restore the inline `MAX_BREAKOUT_AGE_BARS = 3` class
constant and the inline `escalation < self._min_esc` comparison. No other
files were touched by this patch.
"""

from typing import Optional


# ── Canonical breakout-staleness threshold ──────────────────────────────────
# Shared by core/breakout_receiver.py::_check_momentum_phase (bars-since-
# breakout hard check) and breakout_sender.py::BreakoutSender.should_send
# (stale-breakout guard before sending). Both previously hardcoded 3 bars
# independently — this is the single source of truth going forward.
MAX_BREAKOUT_AGE_BARS = 3


def is_breakout_stale(bars_since_breakout: Optional[int],
                       max_bars: int = MAX_BREAKOUT_AGE_BARS) -> bool:
    """True if the breakout move is too many bars old to still be a valid
    entry. `bars_since_breakout=None` is treated as "unknown, not stale" —
    matches both call sites' prior behavior of only rejecting when the
    field is present and numeric."""
    if bars_since_breakout is None:
        return False
    return int(bars_since_breakout) > max_bars


def escalation_meets_minimum(escalation: Optional[int],
                              min_escalation: Optional[int]) -> bool:
    """True if `escalation` satisfies `min_escalation` (or no minimum is
    set). Shared by breakout_receiver.py::receive_signal's `min_escalation`
    parameter gate and breakout_sender.py::should_send's `self._min_esc`
    gate — both previously compared `escalation < min` independently."""
    if min_escalation is None:
        return True
    try:
        return int(escalation) >= int(min_escalation)
    except (TypeError, ValueError):
        return False


class ChecklistResult:
    """Canonical result type for a single breakout-checklist step.

    Moved here from core/breakout_receiver.py (where it was previously the
    only definition) so it has one home usable by any future consumer of
    these shared predicates without importing the receiver module itself.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, status: str, reason: str):
        self.status = status
        self.passed = (status == self.PASS)
        self.reason = reason

    @classmethod
    def ok(cls, reason: str) -> "ChecklistResult":
        return cls(cls.PASS, reason)

    @classmethod
    def fail(cls, reason: str) -> "ChecklistResult":
        return cls(cls.FAIL, reason)

    @classmethod
    def skip(cls, reason: str) -> "ChecklistResult":
        return cls(cls.SKIP, reason)

    def __repr__(self):
        return f"[{self.status}] {self.reason}"
