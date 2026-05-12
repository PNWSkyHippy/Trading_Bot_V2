CLAUDE\_REBUILD\_BRIEF.md
Project Rebuild Brief
Purpose
This project needs a trading-system integrity rebuild before any further strategy tuning or live deployment decisions.

A lot of code has already been built successfully. The issue is no longer “can features be added?” The issue is whether backtest, paper, and live behavior are actually aligned.

This brief defines the required audit, architecture corrections, implementation order, and acceptance criteria.

Core Instruction
Do not optimize indicators first.

Do not defend the current architecture.

Do not present improved backtest results as meaningful unless backtest, paper, and live are using the same:

candle semantics,
stop logic,
trade management rules,
and execution assumptions.
The priority is truth, parity, and realism.

Current Known Problems
The following issues have already been identified and should be treated as real until disproven by audit:

1. Backtest stop logic does not match live stop logic
Backtests use a dedicated 2-bar structural stop engine. Live/paper appears to use:

fixed-percent stop placement,
generic percent trailing logic,
current-price polling for stop exit,
and extra monitor exits.
This means the stop model that “won” backtests is not the same model being traded.

2. Backtester contains optimistic same-bar trail behavior
The current 2-bar backtest logic appears to:

update the stop from the current bar,
then allow that same bar to hit the updated stop.
This is too optimistic because OHLC bars do not reveal intrabar sequence.

3. 1-hour strategies may be trading on unfinished candles
The scanner runs more frequently than some strategy timeframes. Examples:
crypto scan every 5 minutes,
some crypto strategies use 1h candles,
stock scan every 60 seconds,
some stock strategies use 1h candles.
If unfinished candles are being evaluated, live/paper is not comparable to closed-bar backtests.
4. Live management timeframe may not match entry timeframe
Trades entered from 1h strategies may be managed using 5m data for some exit and monitoring logic. If that is intentional, it must be explicit and documented. If not intentional, it is a correctness bug.
5. Extra live exits may not exist in the backtester
Live monitoring includes rules like:
early loss exit,
pivot break exit,
stale ADX/DI exit,
momentum rider logic,
polling-based stop handling.
If backtests do not include the same lifecycle, performance comparisons are unreliable.
6. Backtest realism is insufficient
The system likely under-models:

spread,
slippage,
stop-fill degradation,
and portfolio capital contention.
This is especially dangerous for intraday crypto systems.

Non-Negotiable Principles
Principle 1: One strategy must mean one behavior
The same named strategy must behave consistently across:

backtest,
paper,
and live.
Principle 2: Closed-candle-only signal generation
No strategy may generate signals from unfinished candles unless that is explicitly designed, documented, and separately validated.

Principle 3: One production stop model
We may not backtest one stop model and trade another.

If production uses a 2-bar structural stop, then live/paper must use the same structural stop. If production uses a percent trailing stop, then backtests must use that same model.

Principle 4: Timeframe-aware management
A trade must carry its originating timeframe. Trade supervision must respect that timeframe unless a lower-timeframe management overlay is explicitly intentional and documented.

Principle 5: Realism over pretty metrics
A lower but more honest backtest is better than inflated results that fail in paper.

Required Deliverables
Create the following markdown files during the rebuild:

PARITY\_AUDIT.md
CANDLE\_INTEGRITY\_SPEC.md
STOP\_ENGINE\_SPEC.md
TIMEFRAME\_LIFECYCLE\_SPEC.md
BACKTEST\_REALISM\_NOTES.md
REBUILD\_IMPLEMENTATION\_PLAN.md
VERIFICATION\_REPORT.md
Required Work Sequence
Phase 1 — Audit Only
Do not change code first.

Produce PARITY\_AUDIT.md with these sections:

Backtest vs live mismatches
Candle integrity issues
Stop-loss and trailing-stop mismatches
Timeframe mismatches
Extra live exits not represented in backtest
Execution realism issues
Portfolio simulation limitations
Highest-priority fixes
Lowest-risk implementation order
For each issue, classify it as:

correctness-critical,
realism-critical,
or strategy-quality-critical.
Also identify which current performance claims should be considered unreliable until parity is fixed.

Phase 2 — Candle Integrity
Implement a strict closed-candle contract.

Requirements:

No strategy may evaluate an unfinished candle.
1h strategies must only evaluate fully closed 1h candles.
If the scanner runs more frequently than the strategy timeframe, it must not repeatedly evaluate the still-forming candle.
This behavior must be explicit and testable.
Deliver:

code changes,
CANDLE\_INTEGRITY\_SPEC.md,
verification notes.
Acceptance criteria:

crypto 1h strategies are not re-evaluating the same forming 1h candle every 5 minutes,
stock 1h strategies are not re-evaluating forming hourly candles every 60 seconds,
logs clearly indicate when a bar is closed and eligible.
Phase 3 — Unified Stop Engine
Implement one shared stop engine across backtest, paper, and live.

Requirements:

Decide the production stop model:
true 2-bar structural trailing stop, or
percent trailing stop.
Do not keep one model in backtest and another in live.
Remove same-bar optimistic trail-update-then-hit behavior from the backtester.
A stop updated from a closed bar becomes active on the next bar, not retroactively on the same bar.
Document stop sequencing clearly.
STOP\_ENGINE\_SPEC.md must define:

initial stop calculation,
stop update trigger,
activation timing,
stop hit logic,
fill assumptions,
live/paper/backtest parity expectations.
Acceptance criteria:

no same-bar optimistic stop activation,
same stop update rules across environments,
same stop activation timing across environments,
documented fill assumptions.
Phase 4 — Timeframe-Aware Trade Lifecycle
Implement timeframe-aware trade management.

Requirements:

Every trade must store the originating strategy timeframe.
Management logic must know the trade timeframe.
A 1h trade may not silently be supervised as a 5m trade by accident.
If lower-timeframe management is intentional, it must be explicit and documented as a hybrid design.
Deliver:

schema or state changes if needed,
updated trade creation logic,
updated position monitoring logic,
TIMEFRAME\_LIFECYCLE\_SPEC.md.
Acceptance criteria:

logs show the entry timeframe for each open trade,
1h entries are not accidentally managed as 5m trades,
hybrid management, if used, is deliberate and documented.
Phase 5 — Backtest Realism
After parity is fixed, harden realism.

Requirements:

configurable fees/commission,
configurable spread/slippage,
explicit stop fill assumptions,
clear distinction between per-symbol isolated tests and true shared-capital portfolio tests.
Do not over-engineer this phase. Aim for honest realism, not perfect market microstructure simulation.

Deliver:

implementation,
config knobs,
BACKTEST\_REALISM\_NOTES.md,
before/after comparison showing impact of realism assumptions.
Acceptance criteria:

intraday crypto systems are not evaluated friction-free,
reports clearly state assumptions,
portfolio summaries cannot be mistaken for true shared-capital portfolio tests if they are not.
Phase 6 — Verification
Produce VERIFICATION\_REPORT.md.

It must answer:

What mismatches were found?
What was fixed?
What still differs across backtest, paper, and live?
Can we honestly say that the same strategy now runs under the same candle semantics and stop rules across environments?
If the answer is not fully yes, explain exactly what still differs.

Specific Files to Audit First
Start with these files:

intelligence/backtester.py
core/position\_monitor.py
core/risk\_manager.py
scanners/market\_scanner.py
any execution-layer code affecting:
stop updates,
stop fills,
entry timing,
candle selection,
and broker reconciliation
Specific Findings That Must Be Addressed
A. Backtester 2-bar logic
Investigate and correct the behavior where the stop may be:

updated from the current bar,
then checked against that same bar.
This is a critical realism issue.

B. Live stop implementation
The live bot currently appears to use:

fixed stop placement,
percent trailing stop logic,
and current-price polling.
If production is supposed to be 2-bar structural trailing, this must be replaced or reconciled.

C. Scanner candle handling
Verify whether the scanners are passing unfinished candles to strategies. If they are, fix it.

D. Monitor timeframe mismatch
The monitor appears to use 5-minute bar context for various checks even for 1-hour strategies. This must either be:

corrected,
or formally documented as intentional hybrid behavior.
E. Backtest/live lifecycle drift
Ensure live-only exits are either:

represented in backtests,
or clearly excluded from performance comparisons.
Implementation Constraints
Constraint 1
Do not silently change strategy intent while fixing parity.

Constraint 2
Do not tune thresholds yet. Fix architecture first.

Constraint 3
Do not claim success based on higher backtest metrics alone.

Constraint 4
Keep changes modular and testable. Stop logic should be isolated enough to test independently.

Constraint 5
Document every behavioral change that could alter historical performance.

What Not To Do
Do not:

tune RSI thresholds,
tune EMA periods,
promote new win-rate claims,
add more indicator strategies,
defend “best performer” labels,
or optimize strategy scores
until the following are complete:

candle integrity,
stop-engine parity,
timeframe lifecycle integrity,
basic realism hardening.
Required Acceptance Standard
Before any strategy is considered for live deployment, the system must be able to honestly pass this statement:

“The strategy evaluated in backtest is the same strategy being run in paper/live, using the same candle semantics, the same stop model, the same trade lifecycle assumptions, and clearly documented execution realism.”

If that statement is not true, the system is not ready for live capital.

After Parity Is Fixed
Only after the above phases are complete, proceed to strategy redesign.

At that stage:

classify each current strategy as keep, merge, convert to filter, or remove,
reduce the strategy stack to a smaller production-quality set,
and build around:
one range/reversion engine,
one momentum/continuation engine,
one shared execution/risk layer,
one veto/filter layer.
Final Instruction
Truth first. Parity first. Then realism. Then strategy quality. Then optimization.

Not the other way around.



Phase 7 — Strategy Stack Review
Only begin this phase after parity and realism are approved.

You are working from CLAUDE\_REBUILD\_BRIEF.md and VERIFICATION\_REPORT.md.

Proceed with Phase 7 only: strategy stack review.

Objective: Reassess the strategy layer now that engine integrity has been improved.

Requirements:

do not treat textbook indicator systems as automatically valid standalone engines
classify each current strategy as:
keep
merge
convert to filter
remove
identify which strategy performance claims were probably artifacts of old engine mismatch
propose a smaller production-quality strategy stack
Deliverables:

STRATEGY\_STACK\_REVIEW.md
The review must include:

each existing strategy and its classification
why it should stay, merge, convert, or go
which strategies depend heavily on weak standalone indicator logic
recommended final architecture:
one range/reversion engine
one momentum/continuation engine
one shared risk/execution layer
one veto/filter layer
Do not implement strategy redesign yet unless explicitly approved. Stop and wait for approval.



Phase 8 — Strategy Redesign Plan
Only begin this phase after strategy review is approved.

You are working from CLAUDE\_REBUILD\_BRIEF.md and STRATEGY\_STACK\_REVIEW.md.

Proceed with Phase 8 only: strategy redesign planning.

Objective: Design the next-generation production strategy stack.

Requirements:

define the minimal high-quality strategy set for stocks and crypto
reduce unnecessary overlap
move weak standalone indicators into support/filter roles where appropriate
emphasize regime-aware design, execution realism, and risk coherence
Deliverables:

STRATEGY\_REDESIGN\_PLAN.md
Include:

target engines
entry logic concepts
exit logic concepts
regime filters
veto layer concepts
risk controls
migration path from current codebase
Do not implement redesign yet unless explicitly approved. Stop and wait for approval.





