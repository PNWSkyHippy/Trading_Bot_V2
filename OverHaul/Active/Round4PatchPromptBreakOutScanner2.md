Patch BreakoutScanner.py.

Problem The scanner now supports explicit signal direction (long / short), but post-alert tracking is still long-only in several places.

Current bugs

EscalationTracker.check() only escalates when:

mpct >= 2 / 5 / 10 This works for longs only. Good shorts have negative move_pct and never escalate.
EscalationTracker.check() only updates:

sig.best_move_pct when mpct > sig.best_move_pct Also long-only. For shorts, the “best” move is the most negative move (largest favorable move in short direction).
GUI tagging/status treats any negative move as FAIL:

_tag_for(): if mpct < 0 -> fail
_status_for(): if mpct < 0 -> FAIL This is wrong for shorts because a negative move is favorable for a short breakout.
update_signal_tracking() classifies momentum/dead/fading based only on raw move_pct sign This is long-biased and mislabels short signals in CSV tracking.

Required fix Make post-alert tracking direction-aware everywhere.

Implementation details

A. Add helper for favorable move Create a small helper function, near move_pct(), something like:

favorable_move_pct(direction: str, raw_move_pct: float) -> float
Rules:

long -> favorable move = raw_move_pct
short -> favorable move = -raw_move_pct
This gives a unified “positive means moving in the right direction” metric.

B. Fix EscalationTracker.check() In EscalationTracker.check():

Keep calculating raw move:

mpct = move_pct(sig.entry_price, pd.price)
Determine favorable move using signal direction:

direction = getattr(sig, "direction", "") or ("long" if sig.momentum_score >= -0.5 else "short")
fav_move = favorable_move_pct(direction, mpct)
Update best move using favorable move, not raw move:

if fav_move > sig.best_move_pct: sig.best_move_pct = fav_move
Escalation thresholds should use favorable move:

if fav_move >= t2 / t5 / t10 then escalate
Keep sig.current_price updated as today

Important:

best_move_pct should now represent “best favorable move” regardless of long/short
so for shorts it should be stored as a positive number too (e.g. +6.2 means favorable short move of 6.2%)
C. Fix GUI tag/status logic In ScannerGUI._tag_for() and _status_for():

Use signal direction awareness rather than raw mpct < 0
Add a helper or infer favorable move from row values:
rows already store direction as LONG/SHORT
convert row move_pct into favorable move based on direction
Only mark FAIL when favorable move is negative
long: negative raw move = fail
short: positive raw move = fail
D. Fix update_signal_tracking() CSV momentum classification In update_signal_tracking():

Continue computing raw move_pct from entry to current
Determine direction from stored CSV row if available
if unavailable, keep current behavior as fallback
Classify STRONG / MOVING / WEAK / FADING / DEAD using favorable move, not raw move
If direction is unavailable in CSV rows:

do not break existing behavior
fallback to current raw move logic
E. Logging Where escalation is logged, keep the existing raw move display if you want, but it would be useful to also show favorable move for clarity, especially on shorts.

Important

Do NOT change scanner detection scoring yet
Do NOT change watchlist gate logic unless required for correctness
This patch is only about post-alert tracking, escalation, GUI state, and CSV classification
Preserve existing public interfaces
Verify

python -m py_compile BreakoutScanner.py
Confirm long signals still escalate normally
Confirm short signals now escalate when price moves down favorably
Confirm GUI no longer marks favorable short moves as FAIL
Confirm best_move_pct grows positively for both longs and shorts
Expected

Shorts can escalate to MOVING / HOT / ROCKET
GUI status reflects favorable movement correctly for both directions
CSV momentum labels are direction-aware
best_move_pct is comparable across long and short signals