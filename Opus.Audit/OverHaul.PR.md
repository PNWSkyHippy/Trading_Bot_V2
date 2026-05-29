# OverHaul.PR — Opus Quant Audit of trading_bot_v2

**Date:** 2026-05-29
**Scope:** Cold read of the live trading stack. Priority on short-side SL/TP
direction logic and the "ETH/USD SHORT exited profitable-direction but booked a
loss" symptom. Secondary: why win rate and trade count collapsed after the
external audit.
**No source files were modified.** All proposed changes are delivered as
unified `.diff` patches in this folder. Apply with Sonnet/Haiku.

---

## TL;DR — the headline finding

**There is NO short-side direction-inversion bug.** I traced every SL/TP/P&L
path for shorts and they are all correct (proof in §2). The thing that is
quietly bleeding the account is a **fee-hurdle problem**: crypto round-trip cost
is **0.62%**, but the profit-locking and time-stop logic books exits at gains
*below* that hurdle. A trade can move the right way, get "stopped" by a trailing
stop in the profit zone, and still be net-negative after fees. That is exactly
what happened to the ETH/USD short — and it is the same mechanism that turned
the breakout scanner from "+$90–180 winners" into "90% small losers averaging
$20–30."

The external audit didn't break the *direction* logic. It (a) added aggressive
profit-locks / time-stops that truncate winners below the fee hurdle, and
(b) bolted a 15-gate hard checklist + inverted cooldown onto the breakout
receiver that throttled trade count from ~100/day to ~20/day.

---

## 1. The ETH/USD SHORT symptom — fully explained

**Reported:** SHORT, entry 2015.39, exit 2007.16 (below entry = the *profitable*
direction for a short), reason `"Stop Loss"`, negative P&L after fees.

### What actually happened (verified, not guessed)

1. The short was opened with a correct protective stop **above** entry
   (`risk_manager.approve_trade` and `trade_executor` both place short stops at
   `entry × (1 + sl_pct)` — verified §2).
2. Price fell (profit for the short). The two-bar structural trailing stop
   (`core/stop_engine.py:120-125`) ratcheted the stop **down** to
   `max(prior-N highs)`, which is the correct behavior — it locks profit by
   moving the stop into the below-entry zone (2007.16).
3. Price retraced **up** to 2007.16. `risk_manager.check_sl_exit`
   (`core/risk_manager.py:499`) correctly fired: `short and current_price >= sl`.
   Fill recorded at the stop level (`position_monitor.py:1328`).
4. Gross P&L: `(entry − exit) × qty = (2015.39 − 2007.16) = +8.23/unit`
   = **+0.408%** — a real, positive, correctly-signed gain
   (`trade_executor.py:721`, `position_monitor.py:446`).
5. **Crypto round-trip fee** = `(BT_COMMISSION_CRYPTO_PCT + BT_SLIPPAGE_CRYPTO_PCT) × 2`
   = `(0.26 + 0.05) × 2` = **0.62%** (`config.py:173-175`, applied at
   `trade_executor.py:725-729`).
6. **Net P&L** = `+0.408% − 0.62%` = **−0.21%**. Negative.

### Root cause

Two independent, correct mechanisms combined into a bad outcome:

- The trailing stop has **no profit-activation floor**. It will tighten into the
  profit zone and lock a gain *smaller than the 0.62% fee hurdle*. Locking
  +0.41% on crypto is a guaranteed net loss.
- The exit reason string is **generic**. `check_sl_exit` returns `"stop_loss"`
  for both the protective stop and the trailing stop. So a *profit-locking
  trailing exit* is logged identically to a *protective loss*, which is why this
  looked like a directional bug. It is not — it is a sub-fee trailing exit
  mislabeled as a stop loss.

### Fix (see diffs 01, 02, 03, 05)

- Add a fee-aware **profit-activation gate**: the trailing stop may not tighten
  into a level that locks less than `round-trip-fee + min_net_profit` (proposed
  buffer makes the *minimum* locked gain ≈ 1.0% on crypto, 0.3% on stock). Until
  price clears that gate, the original protective stop stands.
- Give trailing-stop exits a distinct reason (`trailing_stop`) so net-of-fee
  profit-locks are not confused with protective stop-outs in the logs/DB.

---

## 2. Short-side direction logic — VERIFIED CORRECT (no bug)

You feared a flipped-sign bug for shorts. I checked every path. All correct:

| Location | Code | Verdict |
|---|---|---|
| `risk_manager.approve_trade:346` | short SL = `entry × (1+pct)` (above) | ✅ |
| `risk_manager.approve_trade:351` | short TP = `entry × (1−pct)` (below) | ✅ |
| `risk_manager.approve_trade:296-304` | structural-stop wrong-side guard for short | ✅ |
| `risk_manager.approve_trade:371-382` | min-distance / wrong-side correction for short | ✅ |
| `risk_manager.check_sl_exit:499` | short stop hit = `price >= sl` | ✅ |
| `risk_manager.check_exit_conditions:511-513` | short SL/TP both correct | ✅ |
| `risk_manager.calculate_trailing_stop:484-491` | short trail only tightens downward | ✅ |
| `stop_engine.initial_stop_from_tail:77-83` | short stop = high side, wrong-side fallback | ✅ |
| `stop_engine.check_for_trail_update:120-125` | short trail = `max(prior highs)`, only if `< current_stop` | ✅ |
| `trade_executor.execute_signal:553-566` | short stop-guard floor `entry × (1+pct)` | ✅ |
| `trade_executor.close_trade:721` | short P&L = `(entry − exit) × qty` | ✅ |
| `trade_executor.close_trade:736` | short pnl_pct = `−raw_move_pct` | ✅ |
| `position_monitor._attempt_close:317-319` | paper clamp for short (TP=max, SL=min) | ✅ |
| `position_monitor:1414` | short TP exit = `price <= tp` | ✅ |

**Conclusion:** the short SL/TP/P&L stack is sound. Do not "fix" it — changing
any of these would *introduce* the inversion you were worried about.

---

## 3. Numbered bug / defect list

> Severity key: **CRITICAL** = directly causes net losses or capital risk ·
> **MEDIUM** = degrades profitability or trade count · **MINOR** = correctness
> hygiene / future-fragility.

### BUG-1 — CRITICAL — Sub-fee profit locks guarantee net losses (crypto)
- **Files:** `config.py:184`, `core/position_monitor.py:80`, `core/risk_manager.py:446-493`, `core/stop_engine.py:120-125`
- **Problem:** crypto round-trip fee is **0.62%**, but:
  - `MOMENTUM_RIDER_MIN_LOCK_PCT = 0.25` (config.py:184) — locks a 0.25% gain → **−0.37% net**.
  - `PERF_CHECK_2HR_MIN_PCT = 0.2` (position_monitor.py:80) — closes "profitable" 2hr trades at 0.2% → **−0.42% net**.
  - Two-bar trailing stop has no profit floor → locks any gain, including sub-fee ones (the ETH case).
- **Why it's wrong:** any exit that books < 0.62% gross on crypto is a *loss*. The bot treats these as wins/scratch and even resets the consecutive-loss counter on a "win" that lost money (`risk_manager.record_trade_result` keys off `pnl > 0`, which is correct *after* fees — but the lock thresholds make sure pnl is negative).
- **Fix:** diffs 01 (config: fee-aware floors), 02 (position_monitor: raise crypto time-stop floors above fee hurdle), 03 (risk_manager: profit-activation gate on trailing stop).

### BUG-2 — CRITICAL — Reward:risk is inverted vs. your stated goal
- **Files:** `config.py:158-160`, `core/position_monitor.py:80-96`
- **Problem:** you want *winners to run full distance, losers cut at half the win*.
  Current behavior is the opposite: TP is fixed at 3% but **time-stops and the
  trailing stop truncate the average win far below 3%**, while losses are allowed
  to run to the full 1.5% stop + 0.62% fees = ~2.12%. Net asymmetry is *winners
  small, losers full* — the exact inversion of the edge you described from the
  original scanner.
- **Math (crypto, current settings):** TP 3% → +2.38% net; SL 1.5% → −2.12% net.
  Breakeven win rate = 2.12 / (2.38+2.12) = **47%**. At the observed 10% WR this
  is catastrophic; even at 35% it loses. The original scanner won because the
  *average win* was multiples of the average loss — that asymmetry has been
  truncated away.
- **Fix:** diff 02 — (a) disable/raise the 2hr & 5hr performance time-stops for
  breakout & crypto trades so winners aren't culled for being "slow"; (b) let the
  momentum rider extend TP (already present) but gate the profit-lock above the
  fee hurdle; (c) keep the protective stop tight. Net effect: small controlled
  losers, full-distance winners. Re-backtest to confirm the asymmetry returns.

### BUG-3 — MEDIUM — Breakout receiver win-cooldown is inverted (throttles re-entries)
- **File:** `core/breakout_receiver.py:373`
- **Code:** `cooldown = 1800 if last.get("won") else 600  # win=30min, loss=10min`
- **Problem:** this blocks re-entry on a **winning** symbol for **30 minutes** but
  only **10 minutes** after a loss. `risk_manager` uses the opposite and correct
  policy (win = 2 min to allow momentum continuation, loss = 10 min revenge
  prevention — `risk_manager.py:387-388`). The receiver gate is the binding one
  for breakout signals, so winning fast-movers get locked out for half an hour —
  a direct contributor to the 100→20 trades/day collapse.
- **Fix:** diff 04 — swap to `600 if won else 1800` (or align to risk_manager's
  120/600). Recommend 120s win / 600s loss to match the rest of the system.

### BUG-4 — MEDIUM — 15 hard checklist gates + 2/day/symbol cap over-throttle entries
- **File:** `core/breakout_receiver.py:310-326`, `:349-366`
- **Problem:** every one of 15 hard checks must PASS/SKIP or the signal is
  rejected. Several are legitimately protective (halt, open-position, freshness),
  but `_check_not_gap_trap`, `_check_not_pump_and_dump`, `_check_no_wick_rejection`,
  `_check_momentum_phase` are aggressive momentum filters that, combined with the
  `MAX_DAILY_PER_SYMBOL = 2` cap, strip out the volatile fast-movers the scanner
  exists to catch. This is the funnel that cut trade count ~5×.
- **Recommendation (not auto-patched — needs your judgment + backtest):**
  reclassify `gap_trap` / `pump_and_dump` / `wick_rejection` from **hard** to
  **soft** (advisory, scored) and raise `MAX_DAILY_PER_SYMBOL` to 4. Then re-run
  the breakout backtest and compare trade count & PF. I did not patch this blind
  because loosening gates without a backtest can re-introduce the 40-50% loser
  regime — see §4 for the disciplined path.

### BUG-5 — MINOR — Structural-stop direction derived from two different momentum functions
- **File:** `BreakoutScanner.py:1245-1253` vs `:1289-1294`
- **Problem:** in `_build_data` the structural-stop direction falls back to
  `self._momentum(prices) < -0.5`; in `detect_breakout` the signal direction
  falls back to `self.momentum_val(pd) < -0.5`. These are **different functions**.
  If they disagree at the boundary, the structural stop is computed for the wrong
  side (e.g. `low × 0.997` for what becomes a short).
- **Impact:** currently **contained** — `trade_executor.py:507-525` and
  `risk_manager.py:296-304` both re-validate the stop side and fall back to the
  percent stop, so no wrong-side stop reaches the broker. But it is fragile and
  will silently degrade structural-stop quality on shorts.
- **You asked specifically:** *is `high × 1.003` always taken for shorts?* —
  Yes, **when `direction == "short"` in `_build_data`** (line 1252). The risk is
  only that `direction` there can disagree with the final signal direction. Make
  both paths call the same momentum function. (diff 06)

### BUG-6 — MINOR — Trailing-stop exits mislabeled "stop_loss"
- **File:** `core/risk_manager.py:495-500`, `core/position_monitor.py:1322-1336`
- **Problem:** a profit-locking trailing-stop exit and a protective stop-out both
  log/record `"stop_loss"`. This is why the ETH exit looked like a directional
  bug. Pure diagnostics, but it cost you real debugging time and pollutes
  win/loss attribution.
- **Fix:** diff 05 — `check_sl_exit` returns `"trailing_stop"` when the current
  stop is on the profit side of entry, else `"stop_loss"`.

### Housekeeping observations (no patch, flagged for cleanup)
- `core/trade_executor - Copy.py` and `BreakoutScannerBACKUP.py` are stale dead
  copies in the live tree — risk of accidental import/edit. Recommend moving to
  an `archive/` folder.
- `_check_breakout_fast_fail` (position_monitor.py:729-748) is already disabled
  with an early `return None` but the dead body (lines 750+) remains. Either
  delete the dead code or remove the early return after re-validation. Right now
  it's harmless but misleading.

---

## 4. The profitability path (what I'd actually do, in order)

Your target: **+2% of capital/day**, willing to accept low win rate if the
*expectancy* is positive. The edge is asymmetry (big wins, small losses), not
win rate. Here is the disciplined sequence:

1. **Apply diffs 01-05** (fee-aware floors, profit-activation trailing gate,
   cooldown fix, exit labeling). This stops the bleed: no more sub-fee "wins,"
   no more 30-min winner lockouts. *Low risk — these only prevent provably
   negative-expectancy exits.*

2. **Re-backtest the breakout scanner** with the profit-activation gate, on the
   crypto + stock windows you already have. Confirm the average-win/average-loss
   ratio climbs back toward the original 2-3× asymmetry. The matrix harness
   already exists (`tools/run_backtest_matrix.py`).

3. **Loosen the receiver funnel (BUG-4) one gate at a time**, backtesting each.
   Reclassify gap_trap / pump_and_dump / wick_rejection hard→soft, raise the
   per-symbol cap. Target ~60-100 trades/day again without re-introducing the
   symmetric-loss regime.

4. **Strategy stack & crypto coverage** — this is a *separate, larger phase* and
   I am deliberately NOT fabricating per-strategy patches here. The honest
   position: of 19 enabled strategies, your own matrix (memory: 2026-05-26) shows
   only `btc_v6_chandelier`, `rsi_dip_simple`, `rsi_dip_spike_v4`, `mr_03_fbs`
   carrying real edge, and most of those are stock-side. The right move is:
   - Keep the 4 proven edges, demote the rest to watchlist (don't trade live).
   - Port the two best mean-reversion stock strategies to crypto with crypto-fee-
     aware thresholds (every threshold must clear 0.62%).
   - Re-run param sweep Pass 2 (your noted #1 next-session task) to lock params.
   I can produce that as a follow-on `STRATEGY_CRYPTO_PORT.md` with concrete,
   backtested specs once diffs 01-05 are in and the breakout re-backtest confirms
   the gate works. Designing 30 strategy rewrites *before* the fee-hurdle fix is
   validated would be guessing.

---

## 5. Patch index (this folder)

| File | Target | Severity | What it does |
|---|---|---|---|
| `01_config_fee_hurdle.diff` | `config.py` | CRITICAL | Adds crypto/stock round-trip fee constants + `MIN_NET_PROFIT_PCT` floors; raises momentum min-lock above fee hurdle |
| `02_position_monitor_timestops.diff` | `core/position_monitor.py` | CRITICAL | Raises crypto/breakout performance time-stop floors above fee hurdle; lets winners run |
| `03_risk_manager_profit_gate.diff` | `core/risk_manager.py` | CRITICAL | Profit-activation gate on the trailing stop (won't lock sub-fee gains) |
| `04_breakout_receiver_cooldown.diff` | `core/breakout_receiver.py` | MEDIUM | Fixes inverted win/loss cooldown |
| `05_exit_reason_labels.diff` | `core/risk_manager.py` | MINOR | Distinguishes `trailing_stop` from `stop_loss` |
| `06_breakout_scanner_direction.diff` | `BreakoutScanner.py` | MINOR | Uses one momentum function for structural-stop direction |

All diffs are **proposals**. They are anchored to the current code as of
2026-05-29. Review each before applying; re-run the backtest matrix after 01-03.

---

## 6. What I did NOT find (so you can stop worrying about it)

- No sign-flip in short P&L. No inverted SL/TP placement for shorts. No inverted
  paper-mode clamp. No broken structural-stop side for shorts at the executor.
- The `high × 1.003` short structural-stop path *is* taken for shorts (BUG-5 is a
  fragility, not an active wrong-side bug — downstream validation catches it).
- The fill-price logic (stop fills at stop price, TP fills at TP price) is
  correct and matches the backtester.

The codebase logic is fundamentally sound. The losses are an *economics*
problem (fee hurdle + truncated winners), not a *correctness* problem.
