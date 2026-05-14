Patch breakout_sender.py.

Problem The sender currently requires signal.direction to already exist:

it does: direction = getattr(signal, "direction", "") or ""
and drops the send if direction is missing
This is too brittle for the current scanner integration. In the current BreakoutScanner flow, BreakoutSignal direction is often implied by momentum_score and not guaranteed to be stored explicitly on the signal object.

That creates a cross-file mismatch:

scanner can produce valid breakout signals
sender can silently drop them with: [SENDER] SYMBOL missing direction — dropping send
Required fix Make direction resolution robust inside BreakoutSender.

Implementation

Add a helper method on BreakoutSender: _resolve_direction(self, signal) -> Optional[str]

Resolution order:

First, check explicit signal.direction
Accept variants like:
long
short
LONG
SHORT
Normalize the final result to lowercase:
long
short
If explicit direction is missing, derive it from signal.momentum_score using the same logic already used in BreakoutScanner:

if momentum_score >= -0.5 → long
else → short
If direction cannot be resolved from either explicit direction or momentum_score:

log a warning
drop the send
In send_signal(), replace the current direct direction lookup with:

direction = self._resolve_direction(signal)
If direction was derived from momentum_score rather than explicit field:

log a debug/info message noting fallback direction inference was used
Important

Do NOT silently default to long
Do NOT change payload field names
Do NOT change retry logic
Do NOT change URL/auth behavior
Keep payload direction lowercase because receiver logic expects lowercase long / short
Why this matters Right now sender behavior depends on scanner attaching signal.direction explicitly. That is fragile and can suppress valid signals. The sender should be resilient to both:

explicit scanner direction
legacy/implied direction via momentum_score
Verify

python -m py_compile breakout_sender.py
Restart scanner
Confirm no warnings like: [SENDER] SYMBOL missing direction — dropping send
Confirm outbound payloads still include:
direction
symbol
asset_class
timestamp
Expected

Sender can transmit signals even when direction is not explicitly stored on the signal object
Payload direction is consistently normalized to lowercase
No valid breakout signals are dropped due to missing signal.direction