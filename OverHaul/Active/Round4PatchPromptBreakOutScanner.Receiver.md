Yep — this receiver is mostly solid. The fix I’d prioritize is this one:

_check_price_still_moving() is validating against entry_price, but for breakout alerts the correct reference should be the payload’s current_price at alert-send time, with entry_price only as fallback.

Why it matters:

If a long was first watched at 100
alert fired at 103
live price is now 102.4
Current code compares to 100 and says “still moving.” But in reality it reversed about -0.58% from the alert price and should probably fail your drift check.

Use this exact Claude prompt:

Patch core/breakout_receiver.py.

Problem The hard check _check_price_still_moving() is using entry_price as the reference price:

sig_price = float(p.get("entry_price", 0))
This is wrong for breakout alerts. The scanner sends both:

entry_price = original watchlist price
current_price = actual price when the alert/escalation was emitted
The drift/reversal check should validate against the alert-time price (current_price), not the earlier watchlist entry. Right now a signal can reverse meaningfully after alerting and still pass because it is being compared against the older entry anchor.

Required fix Update _check_price_still_moving() so it uses:

current_price as the primary reference
entry_price only as fallback if current_price is missing
Implementation

Replace:

sig_price = float(p.get("entry_price", 0)) with:
ref_price = float(p.get("current_price") or p.get("entry_price", 0))
Update the zero/missing guard accordingly:

if ref_price <= 0: fail with a message like reference price is zero or missing
Compute drift vs ref_price, not vs entry_price.

Keep the existing direction-specific drift logic unchanged:

long fails if drift < -PRICE_DRIFT_MAX_PCT
short fails if drift > +PRICE_DRIFT_MAX_PCT
Update success/failure log text so it is clear the drift is relative to the alert-time reference price, not the original watchlist entry.

Small hardening cleanup Also make these two lookups null-safe:

In _check_no_open_position():
use db.get_open_trades() or []
In _check_trading_not_halted():
use session = db.get_session(today) or {}
Important

Do not change checklist ordering
Do not change TTL logic
Do not change hard vs soft check behavior
Do not change payload field names
This is only a reference-price correctness fix plus minor null-safety
Verify

python -m py_compile core/breakout_receiver.py
Confirm receiver still logs checklist results normally
Confirm price drift now reflects movement relative to alert-time current_price
Expected

Post-alert reversals are caught correctly
The drift check reflects actual signal freshness/continuation
No behavior change to the rest of the receiver pipeline
