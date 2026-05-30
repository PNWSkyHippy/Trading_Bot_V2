# OverHaul — Live-vs-Paper Audit (strategies · backtester · optimizer · engines)

**Date:** 2026-05-29 · companion to OverHaul.PR.md and BREAKOUT_RETUNE.md
**Scope (as requested):** all strategies in `strategies/`, the backtester, the
param optimizer, and the engines that run the strategies — focused on **where
the system behaves differently LIVE than in PAPER/backtest**, specifically:
(1) per-broker asset tracking, (2) commissions/fees, (3) the fact that a live
take-profit cannot be edited in place, and (4) using the broker's own
trailing-stop where feasible.

**No source files were modified.** Every proposed change is a `.diff` in this
folder (numbers continue the existing 01–08 series). Apply with Sonnet/Haiku.

Where a fix would require guessing at structure I have not fully verified, I have
**not** written a diff — those are listed under "Report-only" with exactly what
still needs checking. (Per your standing instruction: flagged, not guessed.)

---

## TL;DR — the one finding that matters most

**The backtest you tune on and the bot you run live apply *different exit
logic* for ~16 of the 31 strategies.** Two coupled defects cause it:

1. **Custom exits are a backtester-only feature.** 18 strategies override
   `BaseStrategy.check_custom_exit()`. The backtester calls it on every bar
   (`intelligence/backtester.py:1258`). Live `position_monitor` only wires
   **two** of them by hand — `adaptive_regime` and `rsi_dip_spike_v4`
   (`position_monitor.py:1349`, `:1360`). The other 16 strategies' own exits
   **never fire live.**

2. **The time-stop exemption lists don't match.** The backtester exempts ~30
   strategies from the generic 30m/2h/5h/8h lifecycle stops
   (`backtester.py:1088-1120`) *because* those strategies exit on their own
   thesis. Live exempts only **6** (`position_monitor.py:532-535`). So live
   fires generic time stops on strategies the backtest never did.

Net effect for the affected strategies: **backtest** runs them to their thesis
(custom exit, no early generic stop); **live** cuts them on a generic 30-min /
2-hr / 8-hr stop and never applies their real exit. The params were optimised
against the backtest behaviour, so live expectancy cannot match. The worst cases
are `btc_v6_chandelier` and `ema_ribbon_breakout`, whose **entire risk model is
a chandelier trailing stop implemented inside `check_custom_exit`** — live runs
them on a plain fixed-% stop, a completely different risk profile.

**Fix:** diffs **09 + 10**, applied together. 09 aligns the live exemption list
to the backtester's; 10 adds a generic dispatch so every strategy's
`check_custom_exit` runs live via the same code path the backtester uses.
They are interdependent — see the warning header in diff 10.

---

## Findings by area

### A. Strategies (`strategies/` + `base_strategy.py`)

| # | Finding | Severity | Fix |
|---|---|---|---|
| A1 | 16 strategies' `check_custom_exit` never runs live (only 2 wired) | **Critical** | diff 10 |
| A2 | Live `TIME_STOP_EXEMPT` (6) ≠ backtester (30) | **Critical** | diff 09 |
| A3 | `btc_v6_chandelier` / `ema_ribbon_breakout` chandelier trail lives only in `check_custom_exit` → no trail live | **Critical** | covered by 09+10 |
| A4 | Per-strategy custom SL/TP may book below the crypto fee hurdle (0.62%) | Medium | Report-only (see R4) |

The signal-generation side (`analyze()`) is broker-agnostic and reads only
historical OHLCV; I found no lookahead in the dispatch path (the backtester uses
strict next-bar-open execution, `backtester.py:1160-1162`, and closed-bar
windows). The live-vs-paper risk in the strategy layer is **entirely in the exit
contract**, not in signal logic. That is why the fix is centralised (09+10)
rather than 16 separate strategy patches.

### B. Backtester

Two backtesters exist. **`intelligence/backtester.py`** (physically
`logs/intelligence/backtester.py`, 119 KB) is the real one used by
`run_backtest_matrix.py` and `param_sweep.py`. It is genuinely good: config-driven
round-trip fees (`:1001-1011, :1328`), SL fills at the stop level (`:926`),
intrabar high/low SL/TP detection, stop-wins-on-conflict, next-bar-open entry,
and it mirrors the live lifecycle stops.

| # | Finding | Severity | Fix |
|---|---|---|---|
| B1 | Take-profit fills at **bar close**, not the TP level (`:929`) — live TP is a limit fill AT the level | Medium | diff 11 |
| B2 | Legacy `Scripts/backtester.py`: **zero fees**, daily bars only, bespoke scorer, "approve if win_rate≥50 & PF≥1.2" gate | **High (trap)** | Report-only (R1) |

> **Path note:** the `intelligence` package lives under `logs/intelligence/`,
> and `tools/run_backtest_matrix.py` does `from intelligence.backtester import …`
> with `ROOT = trading_bot_v2` on `sys.path` — there is no `trading_bot_v2/intelligence`.
> The import therefore relies on an external `PYTHONPATH`/run-dir I could not
> confirm. **Verify the matrix/sweep tools actually import the file you think
> they do** before trusting any sweep output. Flagged, not assumed.

### C. Param optimizer (`intelligence/optimizer.py`, `Scripts/param_sweep.py`)

| # | Finding | Severity | Fix |
|---|---|---|---|
| C1 | **No in-sample / out-of-sample split** — every combo scored on the full history; the "best" params are curve-fit | **Critical** | Report-only (R2) |
| C2 | A symbol result counts as valid at `total_trades > 0` — a 2-trade 100%-win combo can top the board | High | diff 12 |
| C3 | Default optimisation metric is `profit_factor`/`win_rate`, not `expectancy` — rewards hit-rate over the asymmetry that is your actual edge | High | diff 13 |

C1 is the single biggest optimiser risk and the most direct "great in paper,
fails live" mechanism, but a correct fix needs train/test plumbing inside
`run_strategy` (date-range splitting) that I will not patch blind — see R2.

### D. Engines (`bot_engine.py`, `strategies/strategy_engine.py`, `signal_engine.py`)

| # | Finding | Severity | Fix |
|---|---|---|---|
| D1 | `strategy_engine._evaluate_strategy` auto-disables on **win rate** — kills profitable low-hit-rate strategies | **Critical** | diff 14 |
| D2 | `bot_engine._reconcile_positions` is **Alpaca-only** — IBKR (preferred stock broker) and Kraken DB trades never reconciled except at EOD | High | diff 15 (IBKR); R3 (crypto) |
| D3 | Capital snapshot skipped when `total == 0`, which is the paper default (broker balances unseeded) → paper capital tracking silently empty | Medium | Report-only (R3) |
| D4 | `signal_engine.py` is dead legacy (tiny price-delta helper), not on the live path | Info | none |

D1 is the engine-layer twin of C3: the system actively removes exactly the kind
of strategy your stated edge depends on.

---

## The four things you specifically asked about

1. **Track each broker asset separately** — routing is correct (stocks→IBKR/Alpaca,
   crypto→Kraken in `trade_executor._submit`), and `broker_manager` keeps
   per-broker balances. The gaps are *reconciliation* (D2, Alpaca-only) and
   *paper seeding* (D3), not routing. Fix: diff 15 + R3.

2. **Account for commissions/fees** — the production backtester does (config
   round-trip). Risks: the legacy backtester has none (B2/R1), and live
   `trade_executor.close_trade` *also* simulates a fee on the entry notional even
   for live fills, double-counting against the broker's real fee (carried over
   from OverHaul.PR.md §"fee hurdle"; reconcile against diff 03). Strategies that
   set a TP below the 0.62% crypto hurdle book net losses on "wins" (A4/R4).

3. **Can't change take-profit on a live trade** — confirmed real exposure. The
   momentum rider "moves" TP. For **live crypto** it does close+reopen (cancel
   resting stop first) — acceptable but pays an extra round-trip fee per
   extension. For **live stocks** the TP is the IBKR/Alpaca bracket limit, which
   is **immutable** — the rider's DB-side TP extension diverges from the resting
   bracket. This is the live-vs-paper TP behaviour you flagged; handled in
   OverHaul.PR.md §"momentum rider" and diff 03 — re-confirmed here, no new diff.

4. **Use the server's trailing-stop where feasible** — currently **not used at
   all**. Kraken (`trailing-stop` order type) and IBKR (`TrailStop`) both support
   native server-side trailing; the bot instead trails by cancel/replace from
   `position_monitor` (crypto) or DB-only (stocks). Native trailing would survive
   a bot/network outage and remove the cancel/replace fee churn. This is a
   genuine enhancement but a sizeable executor change — Report-only (R5), with
   the exact call sites to change.

---

## Patches in this folder (this audit)

| File | Target | What it does |
|---|---|---|
| `09_position_monitor_time_stop_exempt.diff` | position_monitor.py:532 | live `TIME_STOP_EXEMPT` ← backtester's full list |
| `10_position_monitor_generic_custom_exit.diff` | position_monitor.py:1044,1356 | generic `check_custom_exit` dispatch live (pairs with 09) |
| `11_backtester_tp_fill_at_level.diff` | intelligence/backtester.py:929 | TP fills at the TP level, not bar close |
| `12_optimizer_min_trades_gate.diff` | intelligence/optimizer.py:226 | require ≥20 trades/symbol to score |
| `13_optimizer_default_metric_expectancy.diff` | intelligence/optimizer.py:315 | default metric → expectancy |
| `14_strategy_engine_expectancy_disable.diff` | strategy_engine.py:340 | auto-disable on profitability, not win rate |
| `15_bot_engine_ibkr_reconcile.diff` | bot_engine.py:321 | reconcile IBKR positions, not just Alpaca |

**Apply order:** 09 and 10 **together** (interdependent), then 11–15 in any order.
Re-run the matrix backtest after 11; re-run a sweep after 12–13. After 09+10,
**paper-trade at least one full session** and confirm the live exit-reason
distribution shifts toward strategy-specific exits before going live.

---

## Report-only (no diff — needs a decision or a check I won't guess on)

- **R1 — Deprecate/neuter `Scripts/backtester.py`.** It has zero fees, daily
  bars only, a bespoke RSI/MACD scorer (not the real strategies), and a
  win-rate/PF "STRATEGY APPROVED" gate that contradicts the asymmetry philosophy.
  Anyone who runs it gets optimistic, misleading results. Recommend either a
  loud import-time deprecation banner pointing at `intelligence.backtester`, or
  deletion. I did not patch it because I can't tell from the tree whether
  anything still imports it — **grep the repo for `Scripts.backtester` /
  `from backtester` first.**

- **R2 — Add an out-of-sample split to the optimizer (C1).** The robust fix:
  split each symbol's history into train/test by date, optimise on train, then
  *report the test-window score* and rank on it (or on min(train,test)). This
  needs `Backtester.run_strategy` to accept a date sub-range, which I have not
  fully traced. High value — this is the core "overfit in paper, fail live"
  guard — but it must be built against the real `run_strategy` signature.

- **R3 — Crypto/Kraken periodic reconcile (D2) + paper balance seeding (D3).**
  `position_monitor` reconciles broker-side crypto SL/TP fills opportunistically,
  but there is no engine-level Kraken position sweep like the Alpaca/IBKR one.
  And `broker_manager` never seeds paper balances (start at 0), so
  `_sync_capital`'s `if total > 0` skips snapshots in paper. Both want a small
  change but against `broker_manager` internals I'd be guessing at the balance
  store API — confirm `get_state` keys first.

- **R4 — Centralised fee-hurdle TP floor.** Rather than auditing all 31
  strategies' TP settings, enforce one rule at the signal/executor boundary:
  reject or widen any TP whose gross target < the asset's round-trip fee +
  buffer (crypto 0.62%, stock 0.02%). Partly covered by diff 01/03; recommend a
  single guard in `trade_executor.execute_signal` so no strategy can ever book a
  sub-fee "win". See `project_trading_bot_fee_hurdle` memory.

- **R5 — Native server-side trailing stops.** Replace the cancel/replace trail
  (crypto: `position_monitor.py:1596-1617`) and the DB-only stock trail with
  native `trailing-stop` (Kraken `kraken_executor.submit_order`, currently
  ignores SL/TP entirely) and `TrailStop` (IBKR `ibkr_executor.submit_order`
  bracket). Survives outages; removes fee churn. Sizeable — design first.
