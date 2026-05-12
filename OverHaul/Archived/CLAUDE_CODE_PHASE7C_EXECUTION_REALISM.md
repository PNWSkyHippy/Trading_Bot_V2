prompts/CLAUDE_CODE_PHASE7C_EXECUTION_REALISM.md
# CLAUDE CODE — PHASE 7C
**Focus:** Backtester execution realism

Patch files directly in the repo.

## Goal
Eliminate same-bar entry optimism in intelligence/backtester.py.

## Required change
- signal generated from closed bar i
- entry occurs at bar i+1 open
- sizing uses actual entry price
- stop/TP use actual executed entry context
- friction model remains intact

## Rules
- avoid off-by-one issues
- preserve structural stop support
- preserve custom exit hooks
- do not redesign strategy architecture

## Deliverables
- summary
- files changed
- exact backtest commands to compare before/after
- note any residual realism gaps still open
- issue table for ISSUE-06 / ISSUE-14