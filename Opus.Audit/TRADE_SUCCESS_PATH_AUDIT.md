# Trade-Success-Path Audit — addendum to OVERHAUL_LIVE_VS_PAPER.md

**Date:** 2026-05-29 · companion to OverHaul.PR.md, OVERHAUL_LIVE_VS_PAPER.md, BREAKOUT_RETUNE.md
**Scope (as requested):** "basically the entire program where it has to do with
trades being successful" — the full live execution path: position sizing
(`risk_manager`), order routing/close (`trade_executor`), the broker executors
(`kraken_executor`, `ibkr_executor`), per-broker capital (`broker_manager`),
P&L + tax accounting (`database`), settlement (`settlement_tracker`), and the
live OHLCV feed (`market_scanner`). Focus stays on **where live diverges from
paper/backtest** and **anything that quietly erodes realized profit**.

**No source files were modified.** Every fix is a `.diff` in this folder
(numbers continue the 09–15 series → 16–18). Anything that depends on persisted
DB state I cannot see, or that needs a design decision, is **Report-only
(R6+)** — flagged, not guessed, per your standing instruction.

---

## TL;DR

Three concrete, verified defects are safe to patch now (diffs 16–18). The rest
are real but state-dependent or larger-design — listed as Report-only with the
exact thing to check.

| Sev | Finding | Where | Fix |
|---|---|---|---|
| **High** | Orphaned Kraken stop after a normal crypto close → phantom order / unintended short | `trade_executor.close_trade` 705-712; `kraken_executor.close_position` 115-123 | **diff 16** |
| **High** | Tax ledger records `fees_paid = 0` → overstated taxable gains | `trade_executor` 797-803 → `database.record_tax_event` 572-574 | **diff 17** |
| **High** | IBKR balance never synced → `approve_trade` can hard-reject live IBKR entries | `broker_manager.sync_all_balances` 337-355 | **diff 18** (+R7) |
| Critical | Synthetic capital never reconciled to real broker equity | `risk_manager._get_capital` 77-102 | R6 |
| Med | `approve_trade` hard-rejects on $0 broker balance (deadlock if unseeded live) | `risk_manager.approve_trade` 251-273 | R8 |
| Med | Kraken places NO take-profit order; SL/TP args ignored on entry | `kraken_executor.submit_order` 44-101; `trade_executor` 626-640 | R9 (≈R5) |
| Med | Settlement reserves nothing on open; settled-capital ignores open invested | `settlement_tracker` | R10 |
| Low | IBKR integer-share rounding vs DB fractional qty | `ibkr_executor.submit_order` | R11 |

**Good news — no fix needed:** the live OHLCV feed (`market_scanner`:
`_strip_forming_bar` + `_last_bar_evaluated`, structural stop from the same
bars) has solid closed-bar parity with the backtest, and `stop_engine`
(`TwoBarStopEngine`) is a genuine shared source of truth for live/paper/backtest
stops. The live-vs-paper risk is in **order lifecycle and capital accounting**,
not in the data or the stop math.

---

## Confirmed defects (diffs 16–18)

### 16 — Orphaned Kraken stop order after a normal close  *(High)*
At entry, `execute_signal` places a resting Kraken **stop-market** order. On
exit, `close_trade`'s crypto branch calls `kraken.close_position(...)`, which in
LIVE mode (`kraken_executor.py:115-123`) sends **only a market close** — it does
**not** cancel the resting stop. The stop is cancelled in exactly one place: the
momentum-ride path (`position_monitor.py:1451-1453`). So every *other* crypto
exit — take_profit, the 30m/2h/5h/8h time stops, stale exit, pivot break, or an
SL the monitor catches — leaves the stop **live on Kraken**.
Consequence: later the orphaned stop can fire a phantom market order (rejected
on spot with no balance = log noise/API waste; on a margin pair = an
**unintended short**), while the DB shows the position flat.
→ diff 16 cancels `stop_order_id` after a successful live close.

### 17 — Tax ledger ignores fees → overstated gains  *(High)*
`close_trade` computes `fees_paid` (`:728`) and passes it to `db.close_trade`
(`:794`) correctly — trade P&L is right. But the tax event is built from a
*separate* dict, `full_trade = {**trade, ...}` (`:797-802`), which spreads the
original trade (no `fees_paid`). `record_tax_event` reads
`trade.get("fees_paid") or 0.0` (`database.py:572`) and computes
`gain_loss = proceeds - cost_basis - fees_paid`. Result: every tax-ledger row
has `fees_paid = 0` and an inflated `gain_loss`; Form 8949 / year summary
overstate taxable gains by the full fee total.
→ diff 17 adds `fees_paid` to the `full_trade` dict.

### 18 — IBKR balance never synced  *(High; pairs with R7)*
`sync_all_balances` has handlers for alpaca/coinbase/kraken only
(`broker_manager.py:346-353`); IBKR — the **preferred** stock broker — has none,
so `get_broker_balance("ibkr")` returns the `{available: 0.0}` default. The
per-broker cash check in `approve_trade` (`risk_manager.py:251-273`) can then
read that as "No available cash on ibkr" and **hard-reject live IBKR entries**.
`ibkr.get_account()` already returns equity/cash (`ibkr_executor.py:346-374`).
→ diff 18 adds a `_sync_ibkr` handler. **Caveat:** it is inert unless `ibkr` is
a *registered + enabled* broker — see R7.

---

## Report-only (no diff — needs a check or a decision)

- **R6 — Synthetic capital is never reconciled to real broker equity (Critical).**
  `risk_manager._get_capital` (`:77-102`) returns
  `STARTING_CAPITAL + Σ(closed-trade pnl)` — a *synthetic* ledger used for ALL
  position sizing. In live this is never reconciled against the brokers' actual
  equity (`broker_manager` / `get_account`). Any drift (fees, slippage, manual
  moves, partial fills, the diff-17 fee math, deposits/withdrawals) makes live
  size on a number that isn't the real account. This is the single biggest
  live-vs-paper *capital* divergence. Fix is a design choice: either size from
  real broker equity in live, or run a periodic reconcile that corrects the
  synthetic ledger. I won't patch blind — decide the source of truth first.

- **R7 — Register `ibkr` (and `kraken`) as brokers (pairs with diff 18).**
  `_register_defaults` (`broker_manager.py:43-67`) registers only `alpaca` and
  `coinbase`, and `_load_brokers` restores *persisted* registrations on every
  existing install — so adding to `_register_defaults` would help **fresh
  installs only**. **Check first:** run `broker_manager.list_brokers()` (or read
  `db.get_state("registered_brokers")`) to see whether `ibkr`/`kraken` are
  already registered. If not, register once via `register_broker(...)`. I did
  not write that diff because it also needs the real Kraken config var names
  (I did not verify `KRAKEN_API_KEY`/`KRAKEN_SECRET_KEY` exist) — confirm those
  before registering kraken.

- **R8 — `approve_trade` hard-reject on $0 broker balance (deadlock risk).**
  `approve_trade` (`:251-273`) rejects when `broker_available <= 0`. In paper,
  Kraken `get_balance` returns 0.0 (`kraken_executor.py:126-127`) and IBKR isn't
  synced (R7/diff 18) — so if the per-broker balance store is unseeded, *no
  trade can ever open*, which would look like "the bot stopped trading" rather
  than an error. Whether this actually bites depends on persisted
  `broker_balance_*` state I can't see. **Check:** confirm the live/paper broker
  balances are seeded > 0 before relying on routing; if paper balances start at
  0, seed them or exempt paper mode from the hard reject.

- **R9 — Kraken places no take-profit; SL/TP args ignored (≈ R5).**
  `kraken_executor.submit_order` (`:44-101`) places only a market order and
  **ignores** the `stop_loss`/`take_profit` it's handed. `execute_signal`
  (`trade_executor.py:626-640`) then places a stop **but no TP** for crypto.
  So live crypto TP is enforced only by `position_monitor` polling — a real
  live-vs-paper gap (backtest fills TP at the level; live can miss it between
  polls and the diff-11 backtest TP-at-level change widens that gap). A native
  Kraken `take-profit`/`take-profit-limit` order at entry would close it.
  Sizeable executor change — design alongside R5 (native trailing).

- **R10 — Settlement: no reserve on open; settled-capital ignores open invested.**
  `settlement_tracker.can_open_trade` only *checks* (doesn't reserve on open),
  and `get_settled_capital = total_stock_capital − settling` doesn't subtract
  currently-open invested value. In live this can over-allocate (approve a trade
  the settled cash can't actually fund) under T+1. Crypto is correctly excluded
  (instant settle). Confirm the intended reservation model before changing —
  this interacts with R6 (which capital number is authoritative).

- **R11 — IBKR integer-share rounding vs DB fractional qty (Low).**
  `ibkr_executor.submit_order` rounds to `shares = max(1, int(round(qty)))`
  while the DB may store a fractional `qty`. Close/PnL math then uses a slightly
  different quantity than was actually filled — a small accounting drift, worst
  on low-priced/high-share or fractional-intent orders. Decide whether to store
  the broker-rounded share count back to the DB at fill time.

---

## Carried-over / cross-references (already covered, re-confirmed here)
- Fee double-count vs the broker's real fee in live: `close_trade` simulates a
  round-trip fee on entry notional (`:723-729`) even for live fills — reconcile
  against **diff 03** / OverHaul.PR.md §"fee hurdle". Re-confirmed; no new diff.
- Live TP immutability on stock brackets and the momentum-rider close+reopen
  fee on crypto: see OVERHAUL_LIVE_VS_PAPER.md §"four things" #3 and diff 03.
- Native server-side trailing unused (Kraken/IBKR): R5 in OVERHAUL_LIVE_VS_PAPER.md.

---

## Apply order
16, 17, 18 are independent of each other and of 09–15 — apply in any order.
After 18, action R7 (register/confirm `ibkr`) or the handler stays inert.
Before trusting live sizing, resolve R6 (capital source of truth) — it gates
how much every other fix is worth in live.
