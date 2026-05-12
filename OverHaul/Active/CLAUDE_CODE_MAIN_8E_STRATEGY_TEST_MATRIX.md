# 3) `prompts/CLAUDE_CODE_MAIN_8E_STRATEGY_TEST_MATRIX.md`

```md
# CLAUDE CODE — MAIN 8E
**Focus:** Standardized backtest command matrix  
**Priority:** MEDIUM-HIGH  
**Goal:** Create a repeatable testing playbook so strategy evaluation stops being ad hoc

---

## Context

The backtester is now materially stronger, but testing is still happening manually and inconsistently.
We need a single source of truth for:

- what commands to run
- which combinations matter
- what outputs to export
- how to interpret low-sample or distorted results
- how to compare stock vs crypto, long vs short, trend vs mean_rev, and stop architectures

This is mainly a **documentation / workflow** pass, not a trading-logic pass.

---

## Scope

Primary deliverable:
- `docs/BACKTEST_TEST_MATRIX.md`

Optional small helper only if truly useful and tiny:
- `scripts/run_backtest_matrix.ps1`

Do **not** change strategy logic in this pass.

---

## Required content for the matrix doc

### 1. Canonical command sets
Document copy-pasteable commands from repo root for:

#### A. Single-symbol sanity tests
- 1 stock
- 1 crypto
- 1h timeframe
- export trades enabled

#### B. All-stocks / all-crypto broad tests
- 365d
- 730d where relevant
- 1h
- realistic friction on
- optional `--no-fees` comparison

#### C. AdaptiveRegime-specific matrix
Must include commands for:

- all entries
- `--mode trend`
- `--mode mean_rev`
- `--side long`
- `--side short`
- `--stop standard`
- `--stop two_bar`
- canonical decoupled profile:
  - `--initial-stop signal_structural`
  - `--trail-stop two_bar`

#### D. Baseline comparison runs
- standard stop vs two_bar
- realistic friction vs `--no-fees`

### 2. Export discipline
For commands where trade review matters, include:
- `--export-trades`
- note where CSV lands
- note that combined CSV is available on `--all`

### 3. Interpretation rules
Add a section that tells the user how to read results honestly:

At minimum include:
- `< 10 trades = low sample`
- isolated symbol averages are not portfolio returns
- PF = 999 from tiny all-win samples is not meaningful
- corrupted-data-rejected symbols should be excluded, not hand-waved
- stock and crypto should be evaluated separately
- adaptive_regime should be reviewed by mode and side, not just total PnL

### 4. Recommended test order
Add an ordered workflow like:

1. single-symbol sanity
2. broad all-stock / all-crypto
3. long-only / short-only split
4. trend-only / mean_rev-only split
5. stop architecture comparison
6. fees on/off comparison
7. trade CSV review for exit buckets

### 5. Keep it concise
This should be a practical operator document, not a novel.

---

## Optional tiny helper
If useful and small, add a PowerShell helper:
- `scripts/run_backtest_matrix.ps1`

Only include a curated subset of the most useful commands.
Do not build a full framework unless it is genuinely tiny.

If the script adds complexity, skip it and just provide the markdown doc.

---

## Hard rules

- Do not change strategy thresholds
- Do not change backtester logic
- Document commands that already work in current codebase
- Prefer concise, operator-friendly guidance
- Keep the matrix aligned with current CLI args:
  - `--mode`
  - `--side`
  - `--export-trades`
  - `--initial-stop`
  - `--trail-stop`
  - `--no-fees`

---

## Deliverables

1. Summary
2. Files created/changed
3. The final doc path
4. Optional script path (if created)
5. A short example section from the doc
6. Verification commands showing the documented commands actually run

---

## Minimum command set that must appear in the doc

### AdaptiveRegime — stock broad run
```bash
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar --export-trades
AdaptiveRegime — crypto broad run
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar --export-trades
Trend-only
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar --mode trend
Mean-rev-only
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar --mode mean_rev
Long-only
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --stop two_bar --side long
Short-only
python intelligence/backtester.py --all --strategy adaptive_regime --days 365 --tf 1h --asset-class stock --stop two_bar --side short
Friction-free comparison
python intelligence/backtester.py --symbol BTC/USD --strategy adaptive_regime --days 365 --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar --no-fees
Acceptance criteria
A human can follow the doc without guessing command syntax
The matrix reflects the current backtester feature set
The doc reduces inconsistent testing and overreaction to weak samples
No code logic is changed unless a tiny optional helper script is added

---

## Recommendation on how to use them
Because of your token budget pain, feed them **one at a time** in this order:

1. **MAIN_8A_DATA_GUARDRAILS**
2. **MAIN_8C_ADAPTIVE_REGIME_DIAGNOSTICS**
3. **MAIN_8E_STRATEGY_TEST_MATRIX**

That order gives you:
- trustworthy data first
- visibility second
- clean workflow third

If you want, next I can do one more tiny thing for you:
**a single “MASTER PHASE-8 INDEX.md”** that just lists these 3 prompts in order with o