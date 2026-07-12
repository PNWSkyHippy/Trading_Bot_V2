# CLAUDE.md — System Rules & Workflow Protocol

## 1. Development & Deployment Workflow
- ALL programming must happen strictly inside the local repository workspace: /mnt/c/users/linda/trading_bot_v2
- NEVER execute a 'git push origin main' or 'git push' command automatically.
- After implementing any local code changes, stage the files, commit them locally, and immediately display 'git diff HEAD~1' to the terminal screen. 
- Wait for explicit human review and manual keyboard authorization before any live production deployment occurs.

## 2. The 3-Way Standoff Review Protocol
Before editing any core trading scripts, entry signal engines, or risk configurations, engage the 3-Way Audit format:
- Parse files line-by-line for local memory stale-states and logical regressions.
- Constantly account for cross-file dependency ripples (cross-referencing class imports and system reference maps across the workspace).
- When executing peer-reviews alongside Codex (GPT-5.6 Sol) and Cursor Composer, run explicit safety audits to check if an exemption or patch accidentally strips risk boundaries (like the 30-minute early loss protection) from other active algorithmic strategies (e.g., scalp_master, grid_bot).
