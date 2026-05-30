# Breakout Pipeline Retune — more trades, winners run full, losers cut

**Date:** 2026-05-29 · companion to OverHaul.PR.md
**Goal:** restore the original behavior — take many trades, let winners run to
full fruition, cut losers at ~half the average win — *without* re-opening the
40-50% equal-size-loser regime.

I read the whole path: `BreakoutScanner.py` → `breakout_sender.py` →
`/api/breakout_signal` → `core/breakout_receiver.py` → `risk_manager.approve_trade`
→ `trade_executor` → `core/position_monitor.py` (exits).

---

## Where the trades are actually being lost (in priority order)

### THROTTLE-1 — `MAX_CONCURRENT_BREAKOUTS = 2` — THE dominant bottleneck
- **File:** `core/breakout_receiver.py:44`
- This caps open breakout positions to **2 at a time**. Since the whole point is
  to let winners *run for hours*, 2 slots means the pipeline is full almost all
  day and rejects nearly every new signal with "already 2 in-flight." This single
  constant explains most of the 100→20 trades/day collapse. The sender fires
  fine; the receiver throws them on the floor for lack of a slot.
- **Fix (diff 07):** raise to **8** (tune later). With a tight protective stop and
  2% position sizing, 8 concurrent breakouts = 16% capital at risk worst-case,
  which is within your circuit breakers.

### THROTTLE-2 — `MAX_DAILY_PER_SYMBOL = 2`
- **File:** `core/breakout_receiver.py:350`
- A fast-moving symbol that breaks out, wins, pulls back, and breaks out again is
  blocked after 2 trades/day. The original scanner re-entered momentum names
  repeatedly. **Fix (diff 07):** raise to **4**.

### THROTTLE-3 — Inverted win cooldown (already in diff 04)
- **File:** `core/breakout_receiver.py:373` — 30-min lockout on *winners*.
  Already patched in `04_breakout_receiver_cooldown.diff` (win 2min / loss 10min).

### THROTTLE-4 — `VOLUME_SPIKE_MIN = 2.0` (raised from 1.5)
- **File:** `core/breakout_receiver.py:30`
- The comment admits it was raised. 2x volume rejects legitimate early breakouts
  that haven't fully ramped volume yet. **Fix (diff 07):** return to **1.5**.

### THROTTLE-5 — Quiet hours block 5h/day of crypto
- **File:** `core/breakout_receiver.py:51-52` (00:00–05:00 UTC)
- Defensible (thin liquidity), but it removes ~21% of the crypto trading day. If
  you want max trade count, narrow to 00:00–03:00 UTC. **Optional — not patched;
  your call based on whether thin-hour breakouts actually lose in backtest.**

### NOT a throttle (verified fine)
- Sender `bot_min_escalation` = **1** in `scanner_config.json:63` — already
  permissive. Not the bottleneck.
- `PRICE_DRIFT_MAX_PCT = 0.5` only rejects *reversals* (price moving against the
  signal), not continuation. Correct — leave it.
- Sender `MAX_BREAKOUT_AGE_BARS = 6`, `MIN_USD_VOLUME_PER_CANDLE = 500` — sane
  liquidity/staleness guards. Leave them.

---

## Letting winners run to full fruition (the exit side)

The asymmetry config is **already correct**: `DEFAULT_STOP_LOSS_PCT = 1.5`,
`DEFAULT_TAKE_PROFIT_PCT = 3.0` → losers are half the size of full winners (1:2),
exactly your stated goal. The momentum rider also extends TP so big winners run
past 3%. **The problem is the exits that truncate winners before they get there:**

### WINNER-KILLER-1 — Reversal-candle exit fires on winners
- **File:** `core/position_monitor.py:647-723` (`_check_reversal_candles`)
- It exits on 2 consecutive against-direction candles in the first 30 min
  **regardless of P&L**. A winner that pulls back two candles and then resumes is
  killed at the pullback. This is the single biggest "cut the winner too" rule.
- **Fix (diff 08):** only fire when the trade is **non-positive**. A reversal on a
  *losing* trade = thesis failed, cut it (limits losers). A pullback on a
  *winning* trade = noise, hold it (lets winners run). This is precisely the
  "cut losers, don't touch winners" behavior you asked for and didn't get.

### WINNER-KILLER-2 — Sub-fee trailing lock + crypto time stops
- Already addressed: `03_risk_manager_profit_gate.diff` (no sub-fee trailing
  exits) and `02_position_monitor_timestops.diff` (crypto 2hr stop only fires
  when negative). Together these stop the "exit a green trade for a tiny,
  fee-eaten gain" behavior.

### WINNER-KILLER-3 — `_check_breakout_fast_fail`
- Already disabled at `position_monitor.py:748` (early `return None`). Good —
  leave it disabled. It was cutting dips that recover.

### The loss-cutter you KEEP
- `_check_early_loss` (`position_monitor.py:607-635`) only fires when P&L is worse
  than −0.5% **AND** price is still moving against you across 3 bars. That is a
  clean loser-cutter that does not touch winners. Keep it as-is.
- The protective structural stop (`high×1.003` short / `low×0.997` long) stays —
  that's your hard loss cap.

---

## Net effect after THROTTLE 1-4 + WINNER-KILLER 1-2 fixes

- Trade count: 2 concurrent → 8, 2/symbol → 4, winners no longer lock the symbol
  for 30 min → expect a return toward 60-100/day.
- Winners: ride through early pullbacks to the 3% TP (and beyond via the momentum
  rider), no longer cut at a 2-candle wiggle or a sub-fee trailing tick.
- Losers: still cut hard by the structural stop and the negative-only early-loss
  check — capped at ~half the full-winner distance.
- Expectancy: a 50% win rate at 1:2 (after the 0.62% crypto fee, ~2.38% win /
  ~2.12% loss) is solidly positive. That is the math you described.

---

## Patches in this folder for the breakout retune

| File | Target | What it does |
|---|---|---|
| `04_breakout_receiver_cooldown.diff` | receiver:373 | win cooldown 30min→2min (already listed) |
| `07_breakout_receiver_throttles.diff` | receiver:30,44,350 | concurrent 2→8, per-symbol 2→4, volume 2.0→1.5 |
| `08_position_monitor_reversal_gate.diff` | monitor:647-723 + caller | reversal exit only on non-positive trades |

**Apply order:** 04, 07, 08, then re-run the breakout backtest. Tune
`MAX_CONCURRENT_BREAKOUTS` (6/8/10) and `VOLUME_SPIKE_MIN` (1.5/1.75) against the
result — these are the two knobs that trade volume-of-trades against win quality.
Do NOT loosen the gap-trap / pump-and-dump caps yet; those genuinely protect you
from the worst losers. Loosen concurrency and the reversal exit first; that alone
should restore most of the lost trade count and winner size.
