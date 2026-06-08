# SFR — Structural Fakeout Reversal (option B) — Spec

**Date:** 2026-05-29 · Opus · patch-only deliverable
**Files:** `20_sfr_structural_fakeout_new_strategy.diff` (new strategy) ·
`21_strategy_engine_register_sfr.diff` (registration)
**Standing workflow:** no source edits — diffs only, into `Opus.Audit\`.

---

## What you asked for (option B)

Fade a **false break of a STRUCTURAL level** (ORB high/low, prior-day high/low,
range top/bottom): price pokes beyond the level (rejection wick / stop-hunt
liquidity grab), then **closes back inside within 1–2 bars** → enter the
**opposite** direction toward the other side of the range, stop beyond the
fakeout extreme.

This is delivered as `sfr_structural_fakeout.py`, modeled on `mr_03_fbs`'s
structure (snap-back detection + sentiment gate + time stop) but keyed off
**structural levels instead of Bollinger Bands**.

---

## ⚠️ READ FIRST — overlap with an existing strategy (FELS)

While building this I found **`fels_strategy.py` ("Failed Extension Liquidity
Sweep", Strategy 30)** already in the registry — currently **disabled
(WATCHLIST)**. It is *conceptually adjacent*: it also fades a failed breakout
and stops beyond the wick. My prior audit memo flagged only `mr_03_fbs` (BB
fade) as the existing fakeout-fader; **FELS was not called out, so I'm surfacing
it now rather than shipping a near-twin silently** (your standing rule:
"if something looks suspicious but you can't confirm it's broken, say so").

It is **not a duplicate** — the two differ on three concrete axes:

| Axis | FELS (existing, disabled) | SFR (this deliverable) |
|---|---|---|
| **Level faded** | rolling **N-bar** high/low (a moving window extreme) | **named structural levels**: ORB high/low, prior-day high/low |
| **Confirmation** | **single bar**; close may stay **within 1 ATR *outside*** the level | poke then **close back strictly *inside*** within 1–2 bars |
| **Target** | fixed **partial** revert (0.5× of sweep range) | toward the **opposite structural level** (0.75× the distance), RR-floored |
| **Regime gate** | ADX < 28 (range filter) | morning-sentiment gate (block shorts in BULLISH, longs in BEARISH) |

**Recommendation:** these are distinct edges and can coexist, but if **both**
are ever enabled live, watch for correlated signals on the same symbol/bar.
If you'd rather not maintain two fakeout-faders, the alternative is to **retune
FELS** to key off ORB/prior-day levels instead of standing up SFR — your call.
I built SFR because your spec (named structural levels + close-back-inside +
opposite-side target) is materially different from what FELS does today.

---

## How SFR works

**Levels computed each bar** (`_structural_levels`):
- **ORB high / low** — first `orb_bars` of the current session (4×15m crypto /
  6×5m stock — same window as `orb_breakout`). Session anchored UTC (crypto) /
  09:30–16:00 ET (stock), mirroring `orb_breakout._normalise_index`.
- **Prior-day high / low** — full range of the previous calendar/session day.

**Trigger** (on the latest closed bar):
- *Upside fakeout* of a resistance level (ORB high / PDH): some bar in the last
  `snap_bars` pokes its **high** above the level by `poke_min_atr…poke_max_atr`
  ATR, **and the current bar closes back below it** → **SHORT**.
- *Downside fakeout* of a support level (ORB low / PDL): symmetric → **LONG**.
- If several levels trigger, the one with the **largest poke (in ATR)** wins
  (biggest trap).

**Conviction filter:** the poke window's volume must be ≥ `vol_spike_min`×
its 20-bar average (a real trap carries volume).

**Stop:** just beyond the fakeout extreme — `poke_high + sl_atr_buffer×ATR`
(short) / `poke_low − sl_atr_buffer×ATR` (long). Emitted as
`structural_stop_price` + `preferred_initial_stop_mode = "signal_structural"`,
matching the metadata contract `orb_breakout`/`mr_03` already use.

**Target:** toward the opposite structural level — `tp_range_frac` (0.75) of the
distance to the nearest opposite level, but never less than `tp_min_rr` (1.5)×
the structural risk. Falls back to a pure RR target if no opposite level exists.

**Exit:** `check_custom_exit` returns `sfr_time_stop` after `max_bars` (24).
(Same caveat as the rest of the book — see "Open question" below.)

**Gates / flags** (mirrors siblings):
`reviewer_exempt=True`, `ml_exempt=True`, `auto_disable_exempt=True` (incubation
protection, like `orb_breakout`), `time_stop_profile="strategy_defined"`,
`enabled=False` (WATCHLIST), `crypto_enabled=True`, `stock_enabled=False`.

---

## Parameters (`SFRParams`) — all UNTUNED first-pass defaults

| Param | Default | Meaning |
|---|---|---|
| `snap_bars` | 2 | poke must close back inside within this many bars |
| `orb_bars_crypto` / `orb_bars_stock` | 4 / 6 | opening-range window (15m / 5m) |
| `atr_len` | 14 | ATR period (EWM, matches mr_03/fels) |
| `poke_min_atr` | 0.10 | min poke beyond level (filter noise) |
| `poke_max_atr` | 2.5 | max poke beyond level (else it's a real break/gap) |
| `sl_atr_buffer` | 0.25 | stop offset beyond the fakeout extreme |
| `vol_spike_min` | 1.20 | poke-window volume vs 20-bar avg |
| `tp_range_frac` | 0.75 | fraction of distance to the opposite level |
| `tp_min_rr` | 1.5 | reward floor in R |
| `max_bars` | 24 | time stop |
| `long_only` | False | both directions (sentiment gate handles regime) |

---

## Apply order

1. `20_sfr_structural_fakeout_new_strategy.diff` — creates the file.
2. `21_strategy_engine_register_sfr.diff` — imports + appends `SFRStrategy()`.
   (Trivial 2-line manual insert if `git apply` balks on the column-aligned
   comment whitespace — see the note in that diff.)

Loads **disabled**; flip the DB state (`strategy_sfr_structural_fakeout_enabled`)
or `self.enabled` only after a backtest.

---

## Before trusting it live

- **Backtest first.** Defaults are hypotheses, not tuned values. Run the same
  1h/15m crypto matrix used for `mr_03`/`fels` and compare PF/WR/expectancy.
- **Decide the FELS question** (above) before enabling both.

### Live-wiring checks — VERIFIED 2026-05-29 (both PASS)

The two caveats I originally raised here turned out to be already handled by
the codebase. Verified by reading the live path, not assumed:

- **Time-stop fires live. ✅** `position_monitor._check_generic_custom_exit`
  (`position_monitor.py:1100`) is invoked in the live per-trade exit cascade
  (`:1493`). It looks the strategy up via `strategy_engine._get_strategy`
  (matches on `strategy_name`), injects `_bars_held = age_seconds / bar_sec`
  (15m → 900s), fetches 15m bars, and calls `check_custom_exit`. The exclusion
  list at `:1492` is only `{adaptive_regime, rsi_dip_spike_v4, orb_breakout}` —
  `sfr_structural_fakeout` is **not** excluded, so its `sfr_time_stop` at 24
  bars will fire live. (This is the generic dispatcher added in the same
  2026-05-29 audit / diff 09 — the hook gap I'd flagged for other strategies is
  closed.)
- **15m crypto feed is provided. ✅** `CryptoScanner.scan`
  (`scanners/market_scanner.py:483-493`) builds the timeframe→strategies map
  dynamically from every **enabled** crypto strategy's `crypto_candle_timeframe`
  and fetches each unique timeframe once into `bar_cache`, honoring the max
  `candle_limit` in the group (SFR asks 300). `orb_breakout` already pulls 15m,
  so the path is proven. **Note:** the map skips disabled strategies, so SFR
  contributes its timeframe only once `enabled=True` — expected, since it ships
  disabled pending backtest. Bars are closed-bar-stripped (`_strip_forming_bar`)
  for backtest parity.
