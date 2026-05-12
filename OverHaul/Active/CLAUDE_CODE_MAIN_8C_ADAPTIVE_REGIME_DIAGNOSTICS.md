# 2) `prompts/CLAUDE_CODE_MAIN_8C_ADAPTIVE_REGIME_DIAGNOSTICS.md`

```md
# CLAUDE CODE — MAIN 8C
**Focus:** AdaptiveRegime diagnostics and visibility  
**Priority:** HIGH  
**Goal:** Explain why `adaptive_regime` behaves the way it does before tuning anything

---

## Context

Current backtests show important behavior but not enough explanation:

- `mean_rev` barely fires in many runs
- `early_loss` is a dominant exit bucket
- crypto gets chopped quickly
- long / short behavior differs by asset class
- many symbols have low trade counts, so we need better internal diagnostics

Before changing thresholds, we need to know:
- how often the strategy is in each regime
- why candidate setups are being rejected
- whether `mean_rev` is truly absent or just blocked by one gate
- how many entries come from trend vs mean_rev and long vs short

This pass is **diagnostics only**. Do not tune the strategy.

---

## Scope

Files:
- `strategies/adaptive_regime.py`
- `intelligence/backtester.py`

Optional:
- JSON export only if small and clean

---

## Required changes

### 1. Add per-run diagnostics inside `AdaptiveRegime`
Add lightweight counters that accumulate during `analyze()`.

Track at minimum:

#### Regime counts
- `trend_regime_bars`
- `range_regime_bars`
- `transition_regime_bars`

#### Trend-mode blocker counts
- volume gate failed
- EMA alignment failed
- Donchian breakout not triggered
- RSI blocked/exhausted
- signal emitted long
- signal emitted short

#### Mean-reversion blocker counts
- volume gate failed
- EMA side filter failed
- BB touch not reached
- RSI not extreme enough
- signal emitted long
- signal emitted short

Do this in a way that does **not** affect strategy behavior.

### 2. Expose diagnostics to backtester
When `strategy_name == adaptive_regime`, the backtester report should print a new section such as:

- regime bar distribution
- signal counts by mode
- blocker counts by mode
- top blocker(s)

Keep it readable and compact.

### 3. Add aggregate diagnostics in run-all summary
If all / most results are `adaptive_regime`, add an aggregate diagnostics footer below the existing aggregate trade breakdown.

This should answer questions like:
- was the run mostly trend regime?
- did mean_rev almost never fire because ADX rarely entered range mode?
- was BB touch the blocker?
- was RSI the blocker?
- was volume the blocker?

### 4. Keep diagnostics separate from trade results
Do not:
- change entries
- change scores
- change exits
- change ATR multipliers
- change ADX thresholds
- change volume thresholds

### 5. Optional: include diagnostics in JSON export
Only if it’s clean and not invasive.
If added, keep it under a single `diagnostics` object.

---

## Hard rules

- Diagnostics only — no tuning
- No behavioral changes to entries/exits
- No extra per-bar log spam at INFO level
- Counters must be safe for non-adaptive strategies
- Do not break current CSV trade export

---

## Deliverables

1. Summary
2. Files changed
3. Exact report sections added
4. Verification commands
5. Example of the new diagnostics output
6. Short issue table:
   - regime visibility
   - mean_rev blocker visibility
   - trend blocker visibility
   - aggregate diagnostics visibility

---

## Verification commands

### Syntax
```bash
python -m py_compile strategies/adaptive_regime.py intelligence/backtester.py && echo OK
Single-symbol stock
python intelligence/backtester.py --symbol NVDA --strategy adaptive_regime --days 730 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar
Single-symbol crypto
python intelligence/backtester.py --symbol BTC/USD --strategy adaptive_regime --days 730 --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar
Trend-only
python intelligence/backtester.py --symbol NVDA --strategy adaptive_regime --days 730 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar --mode trend
Mean-rev-only
python intelligence/backtester.py --symbol BTC/USD --strategy adaptive_regime --days 730 --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar --mode mean_rev
Run-all stocks
python intelligence/backtester.py --all --strategy adaptive_regime --days 730 --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar
Run-all crypto
python intelligence/backtester.py --all --strategy adaptive_regime --days 730 --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar
Acceptance criteria
Reports explain why mean_rev is scarce or absent
Reports explain major blocker buckets without changing behavior
Aggregate adaptive summary becomes materially more informative
No strategy logic changes are introduced
