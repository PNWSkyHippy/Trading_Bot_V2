# ADAPTIVE REGIME — BACKTEST UPGRADE SPEC
**Status:** Ready for implementation  
**Owner:** Ron  
**Target:** Claude Code  
**Purpose:** Improve backtest usefulness for `adaptive_regime` before strategy tuning decisions are made.

---

## 1. Goal

We do **not** want to tune `adaptive_regime` blindly from a single aggregate result like:

- all stocks
- 1h
- 365d
- standard stop
- one total P&L / win rate

That is not granular enough to answer the real questions:

1. Is **trend mode** working?
2. Is **mean reversion mode** working?
3. Is the problem in **stocks**, **crypto**, or both?
4. Is the problem in **longs**, **shorts**, or both?
5. Are losses mostly from:
   - stop loss
   - custom exits
   - backtest end
   - weak symbols
6. Does `adaptive_regime` improve under:
   - ATR initial stop + percent trail
   - ATR initial stop + two-bar trail
   - full two-bar initial + two-bar trail
7. Is one mode good enough to keep while the other mode should be disabled or split out?

This pass is about **analytics quality and stop-architecture correctness**, not premature strategy tuning.

---

## 2. Critical Design Note — Stop Architecture Must Be Decoupled

### Problem
The current backtester appears to treat `stop_mode == two_bar` as both:
- **initial stop selection**
- **trailing stop behavior**

That is wrong for `adaptive_regime`.

### Why it matters
`adaptive_regime` was intentionally designed with:

- **initial stop from ATR structure** via `signal.metadata["structural_stop_price"]`
- **custom strategy exits**
- optional **two-bar structural trailing** after entry

If `--stop two_bar` replaces the ATR initial stop with a generic two-bar initial stop, then we are no longer testing the intended strategy.

### Required fix
Separate backtest stop behavior into **two independent layers**:

#### A. Initial stop source
Support:
- `percent`
- `signal_structural`
- `two_bar`

#### B. Trail engine
Support:
- `none`
- `percent`
- `two_bar`

### Canonical profile for adaptive_regime
The main “correct” test profile for `adaptive_regime` should be:

- **initial stop = signal_structural**
- **trail engine = two_bar**
- **custom exits = enabled**

That matches the design intent:
- ATR-based initial invalidation
- structural trail after entry
- strategy-specific exits still active

### Backward compatibility
Keep the existing `--stop standard` and `--stop two_bar` behavior for old strategies if needed, but add a more explicit interface.

### Preferred CLI additions
Examples:

```bash
python intelligence/backtester.py --symbol AAPL --strategy adaptive_regime --tf 1h --asset-class stock --initial-stop signal_structural --trail-stop two_bar
python intelligence/backtester.py --symbol BTC/USD --strategy adaptive_regime --tf 1h --asset-class crypto --initial-stop signal_structural --trail-stop two_bar