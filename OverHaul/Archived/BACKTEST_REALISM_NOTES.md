# BACKTEST REALISM NOTES — Phase 5: Realism Hardening

**Status:** Implemented  
**Date:** 2026-05-10  
**Affects:** config.py · intelligence/backtester.py  

---

## What Was Wrong Before

The backtester was entirely friction-free: zero commissions, zero slippage, perfect fills at bar close prices. Every trade's gross PnL was also its net PnL.

For stocks this understates costs only mildly (Alpaca charges no commissions; spreads on liquid equities are tiny). For crypto, the omission was material: Kraken's standard taker fee is **0.26% per leg** — meaning every round-trip trade incurs a floor cost of **0.62%** before slippage. A scalp strategy averaging +0.8% gross wins was actually producing +0.18% net. The prior results were not tradeable.

Additionally: `print_portfolio_summary()` printed a heading implying shared-capital portfolio performance when each symbol actually ran with the full starting capital independently. Comparing multi-symbol averages without noting this is misleading.

---

## What Was Added

### 1. Friction assumptions in `config.py`

```python
BT_COMMISSION_STOCK_PCT  = 0.00   # Alpaca is commission-free
BT_COMMISSION_CRYPTO_PCT = 0.26   # Kraken standard taker fee
BT_SLIPPAGE_STOCK_PCT    = 0.01   # NBBO half-spread estimate for stocks
BT_SLIPPAGE_CRYPTO_PCT   = 0.05   # bid-ask half-spread estimate for crypto
```

Set all to `0.0` to reproduce the old friction-free (optimistic) baseline.

### 2. Round-trip cost deducted per trade in `_simulate()`

```
round_trip_cost = position_value × (commission_pct + slippage_pct) / 100 × 2
```

**Deduction is at close only — no fee is subtracted at entry.** The full round-trip cost (both the entry leg and the exit leg) is applied as a single PnL reduction when the trade closes. Capital is not touched at entry; only the closing PnL is reduced.

This is a deliberate simplification. The more precise approach would model entry slippage as a worse fill price (e.g. `entry_price × (1 + slippage)` for longs), which would slightly widen the stop distance and affect TP distance. For Phase 5 that additional complexity is not warranted: the dollar impact on PnL is identical, and the stop/TP distance error from using the unadjusted price is sub-pip for the 0.01–0.05% slippage values in use.

Applied at every exit, including `backtest_end` forced closes. Deducted from PnL before updating capital. Stored in `BacktestTrade.fees` and summed into `BacktestResult.fees_paid`.

The friction is **position-value-scaled**: a $200 position on a $10k account incurs far less friction than a $2k position. This correctly reflects that larger positions pay proportionally larger spreads and fees.

### 3. New fields on `BacktestTrade` and `BacktestResult`

| Field | Where | Content |
|---|---|---|
| `BacktestTrade.fees` | per trade | round-trip friction cost in dollars |
| `BacktestResult.fees_paid` | per run | total friction paid across all trades |
| `BacktestResult.commission_pct` | per run | per-leg commission used |
| `BacktestResult.slippage_pct` | per run | per-leg slippage used |

### 4. Friction visible in `print_report()`

Every report now shows an explicit FRICTION block:

```
  FRICTION ASSUMPTIONS (applied each leg, round-trip = 2x):
    Commission    : 0.26% per leg
    Slippage      : 0.05% per leg
    Total per leg : 0.31%  |  Round-trip: 0.62%
    Total fees    : $342.17  over 48 trades
    Avg per trade : $7.13
```

If `--no-fees` is passed, the block instead warns clearly:

```
  FRICTION        : NONE — zero-commission, zero-slippage run
                    Results are OPTIMISTIC.
```

### 5. Honest portfolio label in `print_portfolio_summary()`

Header changed from `PORTFOLIO SUMMARY` to `ISOLATED SYMBOL RESULTS`, with an explicit disclaimer:

```
  ISOLATED SYMBOL RESULTS — 12 symbol(s)
  NOTE: Each symbol ran with full starting capital independently.
        This is NOT a shared-capital portfolio simulation.
        Averages below do not represent a real portfolio return.
```

### 6. Friction fields in `export_json()`

```json
"friction": {
  "commission_pct_per_leg": 0.26,
  "slippage_pct_per_leg": 0.05,
  "round_trip_pct": 0.62,
  "total_fees_paid": 342.17,
  "friction_free": false
}
```

### 7. `--no-fees` CLI flag

```
python intelligence/backtester.py --symbol BTC/USD --asset-class crypto --tf 1h --no-fees
```

Passes `commission_pct=0.0, slippage_pct=0.0` explicitly. Use this to reproduce the pre-Phase-5 baseline for direct comparison.

### 8. `--asset-class` CLI flag

```
python intelligence/backtester.py --symbol BTC/USD --asset-class crypto --tf 1h
```

Routes to `fetch_history_crypto()` and applies crypto friction defaults.

---

## Before / After Comparison (Estimated)

These are theoretical estimates based on the friction model, not live backtest runs. Run with and without `--no-fees` to see the actual impact for a given strategy.

### Crypto — Kraken standard tier (0.26% + 0.05% = 0.31% per leg, 0.62% round-trip)

| Metric | Zero-friction (old) | With friction (new) | Notes |
|---|---|---|---|
| Avg win %  | +2.00% | +1.38% | −0.62pp per winner |
| Avg loss % | −1.50% | −2.12% | −0.62pp per loser |
| Breakeven threshold | 0% gross | +0.62% gross | Trade must win by >0.62% to be profitable |
| Profit factor (PF) | 1.80 | ~1.10–1.30 | Highly sensitive to trade frequency |
| High-frequency scalpers | viable | **likely unprofitable** | Every turn costs 0.62% |
| Swing (few trades/week) | viable | viable but reduced | PF impact is smaller |

**Critical finding:** Any crypto strategy averaging fewer than ~0.80% gross per trade is likely unprofitable after Kraken fees at standard tier. The pre-Phase-5 results for short-timeframe crypto strategies should be treated as unreliable.

### Stocks — Alpaca (0% + 0.01% = 0.01% per leg, 0.02% round-trip)

| Metric | Zero-friction (old) | With friction (new) | Notes |
|---|---|---|---|
| Avg win %  | +2.00% | +1.98% | Negligible impact |
| Avg loss % | −1.50% | −1.52% | Negligible impact |
| Profit factor | minimal change | minimal change | Stocks are nearly friction-free on Alpaca |

Stock backtests are not materially affected. The slippage assumption (1bp half-spread) is conservative for liquid large-caps; could be higher for micro-caps or during volatility events.

---

## Stop Fill Assumption — Documented

The backtester fills stop loss exits at `trade["current_sl"]` (the stop price), not the bar close. This was fixed in Phase 3 and correctly models a stop-limit order that fills at the stop level.

**Caveat not modeled:** In fast markets, stop orders can gap past the stop price and fill worse (gap-down through a long stop). This is not modeled. The stop fill is treated as exact. This is a known optimistic assumption, particularly relevant for:
- Crypto during news events (gapping common)
- Stocks at open gap (overnight holds with stop — out of scope, tracked as ISSUE-15)

---

## What Is Still Not Modeled

| Gap | Notes | Phase |
|---|---|---|
| Market impact on large positions | Assumes fills at quoted price regardless of size | Future |
| Overnight gap risk (stocks) | Stop price may not be honored through overnight gap | Phase 6 |
| Partial fills | All orders assumed fully filled | Future |
| Execution timing lag | Entry at bar `i` close; real entry at bar `i+1` open | Phase 5 scope — see note |
| True shared-capital portfolio | run_all() is still isolated per symbol | See note |
| Slippage on high-vol events | Spread widens significantly at news; fixed % assumption | Future |
| Funding rates (crypto perpetuals) | Not applicable on Kraken spot; relevant if perpetuals added | Future |

### Execution timing lag (ISSUE-06/14)

The backtester still signals AND enters at bar `i` close. In live trading, the signal fires at bar `i` close and the order fills at bar `i+1` open. This is the remaining execution lag bias. It is documented here because it interacts with friction: the next-bar entry price may be better or worse than the signal price, independently of spread/commission costs. Fixing this requires a structural change to the simulation loop and is deferred post-Phase-5-approval.

### True portfolio simulation

`run_all()` still runs each symbol with full starting capital. Building a true shared-capital simulation (with concurrent position tracking, capital allocation across symbols, and correlated drawdown) is a significant architectural change beyond Phase 5's scope.

---

## Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | Crypto trades are not friction-free | ✅ 0.62% round-trip applied |
| 2 | Friction assumptions visible in every report | ✅ FRICTION block in print_report() |
| 3 | Portfolio summary labeled honestly | ✅ "ISOLATED SYMBOL RESULTS" + disclaimer |
| 4 | Zero-friction run still available for comparison | ✅ --no-fees flag |
| 5 | Friction fields in JSON export | ✅ friction{} object |
| 6 | Friction scales with position size | ✅ applied to position_value |
| 7 | Stop fill assumptions documented | ✅ this document |
| 8 | What is NOT modeled is documented | ✅ table above |
| 9 | No strategy thresholds changed | ✅ |
