
---

# 2) `prompts/CLAUDE_CODE_BREAKOUT_8B_SENDER_PAYLOAD.md`

```md
# CLAUDE CODE — BREAKOUT PHASE 8B
**Focus:** Sender must serialize the scanner's enriched signal correctly

## Goal
Patch `breakout_sender.py` so it stops guessing and simply forwards the enriched breakout signal cleanly and consistently to the bot API.

The scanner should be the source of truth.
The sender should be a transport layer.

---

## Current confirmed problems

### 1) Silent default to long
Current code:
```python
direction = getattr(signal, "direction", "long")
If scanner forgot to attach direction, sender silently turns it into a long.

This must not happen.

2) Sender still tries to reconstruct missing data
Current code still tries to derive OHLC from signal.history or partial candle_data.

That is fragile.

3) Broker bug was patched, but payload quality is still weak
Broker is no longer the main blocker. Payload completeness now is.

Required code changes in breakout_sender.py
A. Require explicit direction
Do not silently default to "long".

Preferred behavior:

if signal.direction missing/blank -> log warning and do not send
or fail fast inside _build_payload()
Direction must be explicit and scanner-owned.

B. Prefer signal.enrichment
If scanner now attaches:

signal.enrichment
then sender should use that as the primary source for:

candle OHLC
rsi
trend metadata
market context
structural stop
breakout metadata
Do not make AlertSystem or sender reconstruct these fields if scanner already provides them.

C. Keep backward-compatible fallback only as secondary
Compatibility order should be:

signal.enrichment
explicit candle_data arg
legacy fallback (if still needed briefly)
But log when sender had to fall back, so we can see whether scanner enrichment is really working.

D. Forward these fields when present
Payload should include:

Identity
symbol
broker
direction
asset_class
signal_source
Time
timestamp
Prices
entry_price
current_price
Move context
move_pct
best_move_pct
escalation
Quality / analysis
volume_spike
momentum_score
confidence
pattern
rsi
sma200 (optional)
market_pct_change
structural_stop_price
Candle anatomy
candle_open
candle_high
candle_low
candle_close
Breakout structure
breakout_level
bars_since_breakout
distance_from_breakout_pct
If a field is unavailable, send None rather than inventing a fake value.

E. Keep TTL timestamp clean
Continue sending UTC ISO timestamp.

Do not change the TTL behavior.

F. Improve logging
On send attempt, log a compact one-line summary:

symbol
direction
escalation
whether enrichment is present
whether OHLC and RSI are present
Example:

[SENDER] PREP BTC/USD short esc=2 enrich=yes ohlc=yes rsi=yes market=yes
This will make debugging much easier.

G. Do not block GUI thread
Preserve the non-blocking threaded send behavior.

Rules
No silent direction defaulting
Sender must not become a second analysis engine
Keep transport async
Keep existing failure_class logging
Preserve dedup cooldown behavior unless broken
Deliverables
Provide:

summary
files changed
final payload schema actually sent
any compatibility fallback retained
verification steps
Verification checklist
1. Direction no longer silently defaults
Search:

grep -n 'getattr(signal, "direction", "long")' breakout_sender.py
Expected:

gone
2. Sender prefers scanner enrichment
Search:

grep -n "enrichment" breakout_sender.py
Expected:

payload built primarily from signal.enrichment
3. Breakout fields forwarded
Search:

grep -n "breakout_level\|bars_since_breakout\|distance_from_breakout_pct" breakout_sender.py
4. Logging improved
Search:

grep -n "PREP" breakout_sender.py
Acceptance criteria
Sender never invents direction
Sender forwards scanner-produced enrichment cleanly
Payload contains enough information for receiver to validate without starving
Sender remains a transport layer, not an analysis layer

---

# 3) `prompts/CLAUDE_CODE_BREAKOUT_8C_RECEIVER_EXEC_GATE.md`

```md
# CLAUDE CODE — BREAKOUT PHASE 8C
**Focus:** Receiver becomes a thin execution gate, not the primary analyst

## Goal
Patch `core/breakout_receiver.py` so it stops self-rejecting breakout signals due to missing soft-check data.

The scanner should own setup analysis.
The receiver should perform fast execution-safety gating only.

---

## Current confirmed problem

The receiver currently requires:
```python
MIN_SOFT_PASSES = 2
But current breakout payloads often arrive with:

no RSI
no SMA200
no market context
Result:

RSI -> SKIP
SMA200 -> SKIP
market context -> SKIP
soft_passes = 0
signal rejected
So even after the broker-field patch, the pipeline still blocks itself.

Desired final architecture
Scanner owns:
setup quality
direction
candle anatomy
breakout context
soft market filters
Receiver owns:
payload validity
freshness / TTL
no open position
cooldown
trading active
live price drift check
stop sanity
final execution handoff
That is all.

Required code changes in core/breakout_receiver.py
A. Remove soft-pass requirement as a blocker
Current:

MIN_SOFT_PASSES = 2
End state:

missing soft data must not block execution
soft checks become informational / advisory
receiver should not reject solely because RSI / SMA200 / market context are absent
Preferred options:

Set MIN_SOFT_PASSES = 0
Or remove the soft-pass gate entirely
Keep soft checks logged for visibility
Do not keep the current 2-pass requirement.

B. Preserve hard execution gates
These should remain blocking:

required field validation
TTL / freshness
no open position
not in cooldown
trading not halted
live price re-verify
structural stop sanity (when stop exists)
These are valid execution gates.

C. Reclassify analysis checks as advisory
These should no longer be mandatory blockers for breakout execution:

RSI confirms
trend alignment
market context
Recommended behavior:

PASS / FAIL / SKIP still logged
included in response checklist summary
but not required for execution eligibility
If you still want one last safety check, only fail when explicit data is present and clearly contradictory. Do not fail on absence.

D. Decide what to do with wick / gap / volume checks
Because scanner is being upgraded to own these checks, receiver should no longer be the primary place they live.

Recommended receiver behavior:

Keep as hard only if payload provides clear data:
price drift
structural stop sanity
For these:
volume elevated
wick rejection
gap trap
Either:

keep them as advisory if payload is missing data
or keep them as hard only when payload contains the required fields
But do not let missing enrichment cause blanket rejection.

E. Improve checklist summary logging
On rejection, log exactly whether it was:

invalid payload
hard execution gate fail
executor/risk/broker rejection
On success, log how many advisory checks passed/skipped.

F. Keep response structure stable
Preserve:

accepted
failure_class
reason
trade_id
checklist
Do not break API consumers.

Rules
Receiver must not become the main analyst again
Do not weaken real execution safety gates
Do not reintroduce fail-open price verification
Preserve structured failure classes
Preserve TTL behavior
Preserve executor handoff
Deliverables
Provide:

summary
files changed
which checks remain hard blockers
which checks are now advisory only
exact verification commands
sample accepted vs rejected log lines
Verification checklist
1. Soft-pass blocker removed
Search:

grep -n "MIN_SOFT_PASSES" core/breakout_receiver.py
Expected:

either 0
or no longer used as rejection gate
2. Hard gates still exist
Search:

grep -n "_check_freshness\|_check_no_open_position\|_check_not_in_cooldown\|_check_trading_not_halted\|_check_price_still_moving\|_check_structural_stop" core/breakout_receiver.py
3. Advisory soft checks still logged
Search:

grep -n "_check_rsi_confirms\|_check_trend_alignment\|_check_market_context" core/breakout_receiver.py
4. No self-rejection on missing RSI/SMA200/market context
Manual test:

send payload with valid hard fields but no RSI / no SMA200 / no market context
expected result: execution still eligible, not checklist-rejected for soft starvation
Suggested manual test payload
Use curl or the bot endpoint test harness with a payload containing:

valid symbol
valid direction
valid prices
fresh timestamp
volume_spike
confidence
no rsi
no sma200
no market_pct_change
Expected:

not rejected for “Only 0 soft PASS(es)”
Acceptance criteria
Breakout signals are no longer guaranteed to self-reject
Receiver only blocks on real execution-safety failures
Soft analytical data is logged but not required for execution
Pipeline becomes viable for fast breakout trades

---

## My recommendation on the actual target behavior
If you want the **fastest path to usable breakout trades**, tell Claude to aim for this end state:

- **Scanner** does the thinking
- **Sender** just forwards
- **Receiver** only protects execution

That’s the clean fix.

If you want, I can also give you a **fourth master file** like:

- `CLAUDE_CODE_BREAKOUT_MASTER_PATCH_PLAN.md`

that summarizes all 3 and tells Claude the order to run them in.