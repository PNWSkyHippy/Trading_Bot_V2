Yep — and there’s also a very likely hard bug causing your current breakout injections to fail:

Immediate bug
In core/breakout_receiver.py you do:

signal = Signal(
    ...
    broker = p.get("broker", "kraken").lower(),
)
But the Signal dataclass in scanners/market_scanner.py is:

@dataclass
class Signal:
    symbol: str
    asset_class: str
    direction: str
    score: float
    current_price: float
    indicators: Dict
    reason: str
It has no broker field.

So yes, that "no field broker" / unexpected kwarg error is likely killing every injected breakout before anything else happens.

The right logic frame
For fast breakout trading, this should be the split:

BreakoutScanner owns:
all market-sensitive / pattern-sensitive validation
all the stuff that depends on the breakout candle and breakout structure
all the “is this a real breakout or a fakeout?” work
BreakoutReceiver owns:
stateful execution gating
freshness
re-check current price
cooldown / open position / trading halt
final risk-manager handoff
execution
That’s the clean architecture.

Here’s a ready-to-paste note for Claude Code
Save this as something like:

BREAKOUT_REFACTOR_SPEC.md
# BREAKOUT REFACTOR SPEC — Move breakout intelligence upstream

**Status:** Proposed  
**Goal:** Refactor breakout signal flow so the BreakoutScanner performs the heavy market/pattern validation before sending a signal, and BreakoutReceiver only performs fast execution gating and order injection.

---

## 1. Immediate blocker to fix first

### BUG: breakout injection currently fails due to unsupported `broker` field

In `core/breakout_receiver.py`, `_inject_signal()` builds:

```python
signal = Signal(..., broker=...)
But scanners.market_scanner.Signal has no broker field.

Required fix
Choose one of these approaches:

Preferred
Do not pass broker as a top-level Signal argument. Instead store it inside:

signal.indicators["preferred_broker"] = ...
and let trade_executor read it from indicators if needed.

Alternative
Extend the Signal dataclass and all downstream code to officially support an optional broker field.

Recommendation
Use the preferred approach unless broker routing is already fully wired end-to-end.

2. Core design principle
Fast breakout opportunities can be over in 5–15 minutes.

That means the receiver must not act like a second scanner.

Ownership split
BreakoutScanner should own:
breakout pattern detection
escalation logic (new / moving / hot / rocket)
volume spike analysis
wick rejection analysis
gap trap / exhaustion checks
liquidity checks
RSI confirmation
trend alignment (SMA200 / EMA stack / VWAP side, if used)
market context check
breakout level / breakout bar tracking
bars-since-breakout
structural stop calculation
extension-from-breakout calculation
final scanner verdict and confidence
BreakoutReceiver should own:
payload schema validation
signal freshness / TTL
no open position
symbol cooldown
trading not halted
quick current-price re-verification
stop still sane relative to current price
final risk manager approval
order injection
3. Why this refactor is needed
The current receiver checklist is too heavy for time-sensitive breakout execution.

If the scanner already detected a valid breakout, the receiver should not recompute or re-judge the whole setup from scratch. That adds latency and creates duplicated logic.

The scanner is closest to the event and should make the market-structure decision. The receiver is closest to execution and should make the execution-safety decision.

4. What must move from BreakoutReceiver into BreakoutScanner
Move these checks upstream into the scanner:

Move to scanner (market/pattern intelligence)
Volume still elevated / volume spike validation
Wick rejection / fakeout candle analysis
Gap trap / overextension exhaustion logic
Liquidity quality check
RSI confirmation
Trend alignment (SMA200 or equivalent)
Market context check
Any breakout-specific pattern classification
Breakout level and breakout age tracking
Structural stop calculation
These should be computed before the payload is sent.

The scanner should send the results in the payload rather than forcing the receiver to derive them again.

5. What should remain in BreakoutReceiver
Keep only fast execution gating:

Payload valid and required fields present
Signal age within TTL
No existing open position in symbol
Symbol not in cooldown
Trading not halted
Current price has not reversed too far
Current price not too extended from breakout level
Structural stop still valid relative to current price
Risk manager approves the trade
Execute immediately
6. New payload contract from BreakoutScanner
BreakoutScanner must send a richer payload so the receiver does not need to infer missing context.

Required payload fields
symbol: str
asset_class: str              # "stock" or "crypto"
direction: str                # "long" or "short"
timeframe: str                # e.g. "5m", "5Min"
signal_timestamp: str         # ISO timestamp when scanner emitted signal
signal_price: float           # price at signal generation
current_price: float          # latest scanner-side price
breakout_level: float         # the level that was broken
bars_since_breakout: int      # 0 = breakout this bar
move_pct: float               # move since trigger / baseline
distance_from_breakout_pct: float
volume_spike: float
confidence: float             # 0.0 - 1.0
escalation: str               # "moving", "hot", "rocket"
structural_stop_price: float
scanner_hard_pass: bool
scanner_soft_score: int       # number of soft checks passed
scanner_reason: str
preferred_broker: str         # optional, but if present store in indicators not Signal top-level
Recommended optional fields
best_move_pct: float
pattern: str
rsi: float
sma200: float
market_pct_change: float
candle_open: float
candle_high: float
candle_low: float
candle_close: float
wick_body_ratio: float
liquidity_score: float
scanner_checklist: dict
7. Receiver logic after refactor
Receiver should NOT recompute:
RSI
SMA200 trend
wick/body logic
volume spike logic
market context
breakout pattern classification
Receiver SHOULD enforce:
signal freshness
drift / reversal
extension limit
cooldown / state / risk
8. Add signal freshness (TTL)
This is critical for fast breakout trading.

Suggested TTLs
moving: reject if older than 60 sec
hot: reject if older than 90 sec
rocket: reject if older than 45 sec for auto-trade
(rocket can still be logged/alerted even if too old to auto-trade)
Receiver check
Reject stale signals immediately before any deeper processing.

9. Add breakout extension control
A breakout can still be "up" but already be too extended to chase.

Scanner should compute:

distance_from_breakout_pct = ((current_price - breakout_level) / breakout_level) * 100
(shorts mirrored)

Suggested starting limits
For longs:

moving: max extension 1.5%
hot: max extension 3.0%
rocket: max extension 2.0%, or alert-only initially
Reject signals beyond the extension ceiling.

This is more breakout-native than just looking at total move percent.

10. Add bars-since-breakout gating
This matters more than raw move percentage.

Suggested starting rule
Auto-trade only if bars_since_breakout <= 1
If bars_since_breakout > 2, reject for auto-trade but still allow alerting/logging
This helps avoid entering late-stage moves that are already near exhaustion.

11. Fail-open vs fail-closed policy
Current receiver often does:

missing field -> pass
scanner unavailable -> pass
re-verify error -> pass
That is too loose for auto-trading.

New policy
Fail-closed for required breakout fields:
Reject if missing:

symbol
direction
asset_class
signal_timestamp
signal_price
breakout_level
structural_stop_price
confidence
escalation
Fail-open only for optional analytics:
May allow missing:

RSI
SMA200
market_pct_change
pattern name
The scanner should be the system that guarantees these required fields are present before sending.

12. Recommended routing by escalation tier
moving
Best candidate for auto-trade if:

fresh
not extended
strong volume
scanner_hard_pass = True
hot
Tradable, but tighter extension / freshness rules

rocket
Initially prefer:

alert/log/manual only
OR
auto-trade only if:
bars_since_breakout <= 1
very fresh
still close to breakout level
high liquidity
no blowoff candle signature
Do not make rocket the primary auto-entry tier by default.

13. Receiver output contract
Receiver should log clearly whether rejection came from:

stale signal
cooldown
already in trade
trading halt
price reversal
overextension
invalid stop
risk manager rejection
broker/executor rejection
This must be visible in logs for tuning.

14. Implementation steps
Phase A — unblock execution
Fix unsupported broker field bug in _inject_signal()
Ensure at least one breakout signal can flow through receiver and reach trade_executor.execute_signal()
Phase B — move scanner intelligence upstream
Move hard breakout pattern checks from receiver into scanner
Move soft market-structure checks into scanner
Make scanner emit a normalized rich payload with checklist results
Phase C — slim receiver down
Remove duplicated market-analysis logic
Keep only execution gating + risk handoff
Add TTL + extension + bars-since-breakout enforcement
Phase D — logging and validation
Log scanner verdict and receiver verdict separately
Confirm pass/reject reason clarity in logs
Paper test with injected sample payloads
15. Acceptance criteria
#	Requirement
1	BreakoutReceiver no longer crashes on unsupported broker field
2	BreakoutScanner owns breakout/pattern intelligence
3	BreakoutReceiver no longer recomputes RSI/SMA200/wick/volume logic
4	Receiver enforces TTL
5	Receiver enforces extension-from-breakout
6	Receiver enforces bars-since-breakout rule
7	Required payload fields fail closed if missing
8	A valid breakout payload can reach trade_executor.execute_signal() successfully
9	Logs clearly show scanner pass/fail and receiver pass/fail reasons
16. Important philosophy note
This refactor is not about making breakout auto-trading more permissive. It is about making it faster, cleaner, and structurally correct.

The scanner should decide:

"Is this breakout real enough to consider?"

The receiver should decide:

"Is it still safe and timely enough to execute right now?"


---

# And here’s a Claude Code prompt you can paste with it

```md
Please implement the attached breakout refactor spec.

Goals:
1. Fix the immediate breakout injection bug caused by passing `broker=` into `scanners.market_scanner.Signal`, which does not support that field.
2. Refactor ownership so BreakoutScanner performs the heavy breakout validation before sending payloads.
3. Slim BreakoutReceiver so it only performs fast execution gating:
   - payload validation
   - signal TTL
   - no open position
   - cooldown
   - trading not halted
   - price still valid
   - extension not too large
   - stop still valid
   - risk manager approval
   - execute
4. Add clean logging so scanner verdict and receiver verdict are visible separately.

Constraints:
- Do not break the existing scan/executor architecture.
- Preserve current breakout functionality as much as possible.
- Prefer storing `preferred_broker` inside `signal.indicators` rather than adding a new top-level Signal field unless absolutely necessary.
- Required payload fields must fail closed if missing.
- Optional analytics fields may fail open.
- Keep execution path fast and minimal for time-sensitive breakout signals.

Deliverables:
- Full edited files, not snippets
- Short summary of what changed
- Explicit list of any new required payload fields the scanner must send
- Note any remaining TODOs if scanner-side code is not available in this patch
My extra opinion, specifically
If you want this thing to actually catch fast movers:

yes, move the intelligence upstream
and make the receiver thin and fast.

Because right now it’s acting like:

scanner found setup
then receiver asks “but is it really a setup?”
by then the move may be halfway done
That’s backwards for breakout trading.

One more strategic note
For your style, I would have scanner send:

moving
hot
rocket
to the server,

but I’d only auto-trade:

fresh moving
select hot
and I’d make rocket:

alert/manual at first
or very strict auto-trade only
Because rocket-tier often means:

“you are already late unless this literally just broke”

