prompts/CLAUDE_CODE_PHASE7B_BACKTEST_LIFECYCLE.md
# CLAUDE CODE — PHASE 7B
**Focus:** Backtester lifecycle parity

Patch files directly in the repo.

## Goal
Mirror the major live exit stack inside intelligence/backtester.py.

## Add these exits
1. EOD close for stocks
2. early loss exit
3. performance time stop 1 (2hr, need >= 0.2%)
4. performance time stop 2 (5hr, need >= 1.0%)
5. hard time stop (8hr)
6. pivot point break exit
7. stale ADX/DI exit
8. ORB VWAP cross exit

## Rules
- use bar timestamps
- preserve strategy exemptions
- keep exit priority aligned with live
- preserve custom exit hook support
- do not invent thresholds

## Deliverables
- summary
- files changed
- exact backtest commands to verify
- sample exit reasons now visible
- issue table for ISSUE-03 / ISSUE-11