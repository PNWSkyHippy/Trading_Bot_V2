prompts/CLAUDE_CODE_PHASE7_MASTER.md

# CLAUDE CODE — PHASE 7 MASTER PASS
**Project:** trading_bot_v2  
**Mode:** Direct repo patching  
**Priority:** Parity / pre-live blocker cleanup before any major strategy redesign

---

## Operating Instructions

You are working directly in the repository.

**Do the file edits yourself. Do not give me vague instructions or partial snippets unless I explicitly ask for them.**

When finished, return:

1. A concise summary of what changed
2. The exact files changed
3. Any schema or config changes
4. Exact commands I should run to verify
5. A short updated issue-status table:
   - fixed
   - improved with residual gap
   - still open

---

## Mission

We are **NOT** doing the big Phase 8 strategy redesign yet.

First objective is to close the remaining **parity / pre-live blockers** so that:

- backtest
- paper
- live

are mechanically comparable enough to evaluate strategies honestly.

This pass is about **execution honesty**, **reconciliation correctness**, and **backtest/live comparability**.

---

## Ground Rules

- Preserve the current architecture where possible
- Do **not** invent new thresholds
- Use the current live thresholds/constants as source of truth
- Prefer direct file patches over theoretical recommendations
- If an audit item is already fixed in current code, report that and do not re-break it
- Keep logs, comments, and docstrings aligned with runtime behavior
- When touching the backtester, preserve the Phase 5 friction model already added
- Do not begin broad strategy redesign/refactor in this pass
- If a task turns out larger than expected, finish the highest-priority safe subset and report clearly what remains

---

# PASS 1 — Mechanical / Pre-Live Blockers

## Task 1 — Fix startup reconciler crypto broker mismatch

### Problem
Startup reconciliation for crypto still appears to use Coinbase-style logic, while live crypto execution uses Kraken.

### Requirements
- Reconcile crypto positions against **Kraken**, not Coinbase
- Use Kraken symbols / pair handling consistently
- Avoid false “position not found” outcomes caused by wrong exchange assumptions
- Update any class/doc naming if needed to reduce confusion
- Preserve existing stock reconciliation behavior unless directly required

### Likely files
- `core/startup_reconciler.py`
- any helper it calls

### Acceptance
- No Coinbase-based crypto reconciliation remains if Kraken is the active crypto broker
- Code comments/docstrings accurately describe the broker actually used
- Reconciliation logic is internally consistent with the execution layer

---

## Task 2 — Recompute structural stop after actual fill

### Problem
`structural_stop_price` is embedded at signal time, but actual entry may differ from signal price. This can make the stored stop stale or even invalid relative to the real fill.

### Requirements
In `trade_executor.execute_signal()`:

- after actual broker fill price is known
- fetch fresh bars on the signal/trade entry timeframe
- recompute structural stop using `stop_engine.initial_stop_from_tail()`
- validate stop is on the correct side of actual fill
- apply a minimum-distance guard or safe fallback if recomputed stop is invalid or too close
- persist the **final stop actually used**
- keep logging explicit enough that we can confirm the recompute occurred

### Likely files
- `core/trade_executor.py`
- `core/stop_engine.py`
- `scanners/market_scanner.py`
- maybe `core/risk_manager.py`

### Acceptance
- Structural stop is based on actual fill context, not stale signal-time context
- No immediate wrong-side stop can be stored after adverse fill drift
- Final persisted stop matches the execution-time validated stop

---

## Task 3 — Clean stale docs/logs/comments in position_monitor

### Problem
Comments/logs/docstrings still mention old thresholds like:
- 20 min
- 1 hour
- 3 hours
- 3.5 hours

while actual code uses:
- 30 min
- 2 hours
- 5 hours
- 8 hours

### Requirements
- Update all stale docstrings
- Update all stale inline comments
- Update stale logger strings
- Ensure top-of-file header matches actual runtime logic
- Do **not** change live thresholds unless a genuine bug is found

### File
- `core/position_monitor.py`

### Acceptance
- No stale 3.5hr references remain
- No stale 20m / 1h / 3h threshold text remains
- Docs/logs reflect actual runtime values exactly

---

## Task 4 — Re-verify duplicate cooldown issue before patching

### Problem
Prior audit reported a duplicate symbol cooldown block in `risk_manager.approve_trade()`. Current code may already have this fixed.

### Requirements
- Inspect current `core/risk_manager.py`
- If duplicate block still exists, remove it safely
- If already fixed, state that clearly in final report and do not make unnecessary edits

### Acceptance
- Final report explicitly states whether ISSUE-18 was already fixed or was fixed in this pass

---

# PASS 2 — Backtester Lifecycle Parity

## Goal
Backtester must model the major live exit stack in approximately the same order and with the same thresholds.

### Add the following live exit behaviors to `intelligence/backtester.py`

1. EOD close for stock positions
2. early loss exit
3. performance time stop 1 (2hr, need >= 0.2%)
4. performance time stop 2 (5hr, need >= 1.0%)
5. hard time stop (8hr)
6. pivot point break exit
7. stale ADX/DI exit
8. ORB VWAP cross exit

### Requirements
- Use bar timestamps, not wall clock
- Respect stock-only vs crypto behavior
- Preserve strategy-specific exemptions already present in live code
- Keep exit priority aligned with live as closely as practical
- Do not remove existing custom strategy exit hook support
- Produce clear `exit_reason` values so results can be analyzed later
- Reuse existing thresholds/constants when possible instead of duplicating drifting values

### Likely files
- `intelligence/backtester.py`
- optionally shared helpers if you choose to extract them

### Important note
Do **not** blindly paste large chunks of `position_monitor.py` into the backtester if that creates long-term drift risk. If practical, centralize shared logic or clearly mirror it with comments.

### Acceptance
- These exit reasons can appear in backtest results
- Strategy hold times and exit distributions materially resemble live logic more closely
- No threshold drift introduced
- Time-stop exemptions behave the same way as live

---

# PASS 3 — Backtester Execution Realism

## Task — Shift entry to next bar open

### Problem
Backtester still signals on bar `i` and enters at bar `i` close, which is execution lookahead optimism.

### Requirements
- Signal generated from closed bar `i`
- Entry occurs at bar `i+1` open
- Position sizing uses actual entry price
- Stop / TP use actual executed entry context
- Friction model remains intact
- Avoid off-by-one errors near dataset end
- Preserve compatibility with strategy-specific metadata like structural stops

### File
- `intelligence/backtester.py`

### Acceptance
- No more signal-and-fill on the same bar
- Report output remains coherent
- Trade timestamps/prices reflect next-bar execution
- Backtest realism note remains accurate after the change

---

# Non-Goals For This Pass

Do **NOT** do the big Phase 8 redesign yet:

- no `range_engine.py`
- no broad `filters.py` refactor
- no large strategy consolidation
- no DCA → DipBuy rename unless needed for a blocker
- no broad strategy behavior changes unrelated to parity/mechanics
- no speculative threshold tuning

This pass is strictly about parity, realism, and pre-live safety.

---

# Reference Constraints From Existing Audit Trail

Use the current repo state and existing notes as guidance:

- Phase 2 already fixed closed-candle semantics
- Phase 3 already unified structural trailing stop logic
- Phase 4 already added `entry_timeframe` and structural trailing stop timeframe handling
- Phase 5 already added friction modeling

This pass should **build on those**, not undo them.

---

# Preferred Work Order

If all tasks fit comfortably, complete all three passes in this order:

1. Mechanical / pre-live blockers
2. Backtester lifecycle parity
3. Backtester execution realism

If context or risk becomes too large, complete **PASS 1 first**, stop cleanly, and report remaining work rather than making sloppy partial changes to all three passes.

---

# Final Deliverables

When done, return:

## 1. Summary
A concise paragraph of what changed overall

## 2. Files changed
Exact relative paths

## 3. Schema/config changes
Any DB migration, config constant, or serialized field change

## 4. Verification commands
Exact commands to run, such as:
- bot startup checks
- grep/ripgrep commands
- backtest commands
- paper-mode sanity checks

## 5. Issue status table
Use this format:

| Issue | Status | Notes |
|---|---|---|
| ISSUE-19 | Fixed | Kraken reconciler now used |
| ISSUE-06 | Still Open | next-bar execution not yet implemented |
| ... | ... | ... |

## 6. Risk notes
Anything that still blocks live deployment after this pass
