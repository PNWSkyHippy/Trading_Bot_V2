
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

got it so does these 3 over do thre need to  feed him BREAKOUT PIPELINE — REAL BLOCKERS.md


Reasoning
No — the 3 phase prompts are enough by themselves.

You do not need a big BREAKOUT PIPELINE — REAL BLOCKERS.md if token budget is tight.

Best approach
Use:

BREAKOUT_8A_SCANNER_ENRICHMENT.md
BREAKOUT_8B_SENDER_PAYLOAD.md
BREAKOUT_8C_RECEIVER_EXEC_GATE.md
One at a time. Not all at once.

What I’d recommend
Lean / cheapest on tokens
Just feed Claude Code the single phase prompt you want next.

That is enough because each prompt already includes:

current problem
target architecture
exact files
rules
verification
