prompts/CLAUDE_CODE_PHASE7A_MECHANICAL.md
# CLAUDE CODE — PHASE 7A
**Focus:** Mechanical / pre-live blockers only

Patch files directly in the repo. Do not give vague instructions.

## Tasks
1. Fix crypto startup reconciliation to use Kraken, not Coinbase-style logic
2. Recompute structural stop after actual fill in trade execution
3. Clean stale 3.5hr / old threshold docs/logs/comments in position_monitor
4. Re-verify whether duplicate cooldown in risk_manager still exists before patching

## Deliverables
- summary
- files changed
- schema/config changes
- exact verification commands
- issue table for ISSUE-15/16/18/19 + structural-stop fill-time limitation