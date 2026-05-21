# Breakout Pipeline Implementation Plan
**Generated:** 2026-05-20  
**Pipeline:** BreakoutScanner.py → breakout_sender.py → core/breakout_receiver.py

---

## Part 1: Sub-Minute Signal Delivery

### What timestamp actually goes in the payload

`_build_payload()` is called synchronously inside `send_signal()`, before the background thread starts:

```python
now_utc = datetime.now(timezone.utc).isoformat()
"timestamp": now_utc,   # ← send moment, NOT detection moment
```

`payload["timestamp"]` = the moment the send begins, not `signal.timestamp` (which is set at detect_breakout() to `datetime.now()`). The receiver computes age as `(now_utc) − payload["timestamp"]`, which is localhost network latency (~1–50 ms). The 30-second watchlist delay is irrelevant to TTL. **The TTL check cannot fail under normal load.**

### Worst-case timeline

```
T=0s     detect_breakout() fires
         sig.timestamp = datetime.now()   ← display-only; never reaches receiver
         sig.enrichment built from current bars (RSI, OHLC, market_pct_change)
         _process_symbol() → watchlist.add(sig)
         NO SEND. Phase = WATCHLIST.

T=30s    scan_loop wakes (scan_interval_seconds=30)
         watchlist.check(pd)
         IF fav_move >= momentum_gate_pct(0.80%):
           promoted.phase = ALERTED
           escalation.register(promoted)
           send_alert(promoted, escalation=0)
             → should_send: esc=0 < _min_esc=2  ← BLOCKED by min_esc gate
           Net: esc=0 send DROPPED. Bot never sees this signal.

T=60s    scan wakes
         escalation.check() → fav_move >= 2.0% → new_lvl=1
         send_alert(sig, escalation=1)
           → should_send: esc=1 < _min_esc=2  ← BLOCKED

T=90s    scan wakes
         escalation.check() → fav_move >= 5.0% → new_lvl=2
         send_alert(sig, escalation=2)
           → should_send: esc=2 >= _min_esc=2  ✓
           → payload["timestamp"] = datetime.now(timezone.utc)   ← T=90s
           → background thread spawned, HTTP fires

T=90.5s  receiver.receive_signal() called
         signal_age_sec ≈ 0.5s  ← PASSES 60s TTL ✓
         BUT: payload carries enrichment from T=0 (90s stale RSI/OHLC) ← BUG #3
```

### The five actual bugs

| # | Bug | Worst-case impact | Fix |
|---|-----|-------------------|-----|
| 1 | `_min_esc=2` silently drops esc=0 and esc=1 | Bot misses 0–5% breakouts entirely | Lower `bot_min_escalation` to 0 |
| 2 | Dedup blocks esc=3 when it fires close to esc=2 | Rocket alerts silently dropped | Bypass dedup for `esc > 0` |
| 3 | Escalation re-sends use T=0 enrichment | Receiver uses 90s-old RSI/OHLC | Rebuild `sig.enrichment` from `pd` in `_process_symbol` |
| 4 | Dedup race: two threads could both pass before `_last_sent` stamped | Theoretical only under single-threaded scan | Harmless now; note for future |
| 5 | `_can_alert()` 30-min cooldown only protects esc=0 | Escalation storms not rate-limited | Acceptable — escalation is monotonic by design |

### Fix 1: Timestamp (keep as-is, add audit field)

Do **not** change the `now_utc` assignment. Optionally add audit field to `_build_payload()`:

```python
"source_timestamp": getattr(signal, "timestamp", None) and
                    signal.timestamp.astimezone(timezone.utc).isoformat(),
```

### Fix 2: Bypass dedup for escalation re-sends

In `breakout_sender.py`, `should_send()`:

```python
def should_send(self, signal, escalation: int) -> bool:
    if not self.ready:
        return False
    if escalation < self._min_esc:
        return False
    if escalation > 0:
        return True  # EscalationTracker already guarantees each level fires once
    last = self._last_sent.get(signal.symbol, 0)
    if time.time() - last < self._dedup_sec:
        return False
    return True
```

Still stamp `_last_sent` for all sends so esc=0 re-detection is still gated.

### Fix 3: Refresh enrichment before escalation sends

In `MarketScanner._process_symbol()` (~line 1691–1698):

```python
result = self.escalation.check(pd)
if result:
    sig, level = result
    # Refresh stale enrichment with current bar data
    sig.enrichment   = self.detector._build_enrichment(pd)
    sig.volume_spike = self.detector.vol_spike(pd)
    logger.warning(f"[ESCALATE {level}] {broker} {sym} move={sig.best_move_pct:+.2f}%")
    self.alert_system.send_alert(sig, escalation=level)
    return
```

---

## Part 2: Complete Enrichment Payload

### Key constraint: `history_length = 50`

SMA(200) is structurally impossible without raising this cap (see sma200 section below).

### Full field inventory

| Field | Receiver check | Hard/Soft/Required | Currently sent? | If missing |
|-------|---------------|-------------------|-----------------|------------|
| `symbol` | multiple | Required | YES | FAIL — invalid_payload |
| `asset_class` | multiple | Required | YES | FAIL — invalid_payload |
| `direction` | multiple | Required | YES | FAIL — invalid_payload |
| `entry_price` | multiple | Required | YES | FAIL — invalid_payload |
| `current_price` | multiple | Required | YES | FAIL — invalid_payload |
| `move_pct` | `_check_not_gap_trap` | Required | YES | FAIL — invalid_payload |
| `volume_spike` | `_check_volume_elevated` | Required | YES | FAIL — invalid_payload |
| `confidence` | `_inject_signal` | Required | YES | FAIL — invalid_payload |
| `escalation` | `_inject_signal` | Required | YES | FAIL — invalid_payload |
| `timestamp` | `_check_freshness` | Required | YES | FAIL — invalid_payload |
| `broker` | receive_signal (log) | Soft | YES | default "" → fallback |
| `source_broker` | `_inject_signal` | Inject-only | **NO** | defaults to broker_hint |
| `candle_open` | `_check_no_wick_rejection` | Hard | YES (post-8A) | SKIP wick check |
| `candle_high` | `_check_no_wick_rejection` | Hard | YES (post-8A) | SKIP wick check |
| `candle_low` | `_check_no_wick_rejection` | Hard | YES (post-8A) | SKIP wick check |
| `candle_close` | `_check_no_wick_rejection` | Hard | YES (post-8A) | SKIP wick check |
| `bars_since_breakout` | `_check_momentum_phase` | Hard | **NO** | SKIP momentum-phase age sub-check |
| `distance_from_breakout_pct` | `_check_momentum_phase` | Hard | **NO** | SKIP momentum-phase distance sub-check |
| `rsi` | `_check_momentum_phase`, `_check_rsi_confirms` | Hard + Soft | YES | SKIP both RSI sub-checks |
| `structural_stop_price` | `_check_structural_stop` | Hard | **NO** | OK — falls through to percent-based stop |
| `sma200` | `_check_trend_alignment` | Soft | **NO** | SKIP trend-alignment |
| `market_pct_change` | `_check_market_context` | Soft | PARTIAL (crypto only) | SKIP for stocks |
| `momentum_score` | `_inject_signal` | Inject-only | YES | default 0 |
| `pattern` | `_inject_signal` | Inject-only | YES | default "breakout" |
| `breakout_level` | `_inject_signal` | Inject-only | **NO** | None stored |
| `source_price` | `_inject_signal` | Inject-only | **NO** | fallback to `current_price` |
| `source_timestamp` | `_inject_signal` | Inject-only | **NO** | fallback to `timestamp` |

### Per-field fix specifications

#### `bars_since_breakout`

Three-line change to `EscalationTracker`:

```python
# register() — add counter to entry dict:
self._tracked[signal.symbol] = {"signal": signal, "level": 0, "bars_since": 0}

# check() — increment at top of method body:
entry["bars_since"] += 1

# check() — stamp it on the signal before return:
sig.bars_since_breakout = entry["bars_since"]
return sig, new_lvl
```

Add field to `BreakoutSignal` dataclass:
```python
bars_since_breakout: int = 0
```

#### `breakout_level` and `distance_from_breakout_pct`

Add to `BreakoutSignal` dataclass:
```python
breakout_level:             float = 0.0
distance_from_breakout_pct: float = 0.0
```

In `EscalationTracker.register()` — record level at graduation from watchlist:
```python
def register(self, signal: BreakoutSignal):
    signal.breakout_level = signal.entry_price  # price at initial detection
    self._tracked[signal.symbol] = {"signal": signal, "level": 0, "bars_since": 0}
```

In `EscalationTracker.check()` — recompute distance on every cycle:
```python
if sig.breakout_level > 0:
    raw = (pd.price - sig.breakout_level) / sig.breakout_level * 100
    sig.distance_from_breakout_pct = raw if sig.direction == "long" else -raw
```

#### `structural_stop_price`

Add to `_build_enrichment()`, after the OHLC lines:

```python
direction = getattr(pd, "_pattern_dir", None)
if direction not in ("long", "short"):
    p_list = list(self.price_history.get(pd.symbol, []))
    direction = "short" if self._momentum(p_list) < -0.5 else "long"

if direction == "long" and pd.low and pd.low > 0:
    data["structural_stop_price"] = round(pd.low * 0.997, 6)
elif direction == "short" and pd.high and pd.high > 0:
    data["structural_stop_price"] = round(pd.high * 1.003, 6)
```

The 0.3% buffer keeps the stop below the wick low/above the wick high. Validation: for a crypto at $1.00 with `pd.low = 0.98`, stop = 0.977, distance = 2.3% — within the 5% crypto limit.

#### `sma200` (optional — requires raising history cap)

To enable, raise `history_length` to at least 200 in `BreakoutDetector.__init__`, then add to `_build_enrichment()`:

```python
if len(prices) >= 200:
    data["sma200"] = round(sum(prices[-200:]) / 200, 6)
```

**Trade-off:** 4× more history per symbol across ~200 symbols for one advisory soft check. Recommend keeping at 50 for now.

#### `market_pct_change` for stocks

In `_build_enrichment()`, after the existing BTC block:

```python
if pd.asset_type == AssetType.STOCK or "/" not in sym:
    for spy_key in ("SPY", "QQQ"):
        spy_hist = self.price_history.get(spy_key)
        if spy_hist and len(spy_hist) >= 2:
            try:
                spy = list(spy_hist)
                if spy[0] > 0:
                    data["market_pct_change"] = round(
                        (spy[-1] - spy[0]) / spy[0] * 100, 4
                    )
            except Exception:
                pass
            break
```

Requires SPY to be seeded into `price_history` via an explicit fetch at the top of `_scan_stocks()` if it's not already in the movers list.

#### `source_broker`, `source_price`, `source_timestamp` (low priority)

Add to `_build_payload()`:
```python
"source_broker":    signal.broker.lower(),
"source_price":     signal.current_price,
"source_timestamp": signal.timestamp.astimezone(timezone.utc).isoformat()
                    if hasattr(signal.timestamp, "isoformat") else str(signal.timestamp),
```

---

## Part 3: Direction Flip Logic (Long → Short When Breakout Reverses)

### Design rationale

Key constraints from the code:
- `_check_price_still_moving()` returns a `ChecklistResult` — can't also return a payload
- The flip must live in `receive_signal()`, not inside the check
- All hard/soft checks read `direction` from the payload dict — a shallow clone with `p["direction"] = flipped` automatically corrects every downstream check
- `structural_stop_price` is side-specific — must null it on flip
- `_check_momentum_phase()` uses `abs(dist_pct)` — negating `distance_from_breakout_pct` is safe

The `_drift_state` side-channel keeps the check method clean while giving the caller the live price without a second network round-trip.

### Implementation

#### 1. Add `_drift_state` to `__init__`

```python
def __init__(self):
    self._executor: Optional[TradeExecutor] = None
    self._scanner_ref = None
    # Ephemeral — set by _check_price_still_moving() when it detects adverse drift,
    # consumed and cleared by receive_signal() within the same call.
    self._drift_state: Dict[str, Any] = {}
```

#### 2. `_check_price_still_moving()` — stash state before returning fail

Replace the two `return ChecklistResult.fail(...)` drift lines:

```python
if direction == "long" and drift_pct < -PRICE_DRIFT_MAX_PCT:
    self._drift_state = {"live_price": current, "drift_pct": drift_pct}
    return ChecklistResult.fail(
        f"{sym} reversed {drift_pct:.2f}% from signal price "
        f"(limit -{PRICE_DRIFT_MAX_PCT}%)"
    )
if direction == "short" and drift_pct > PRICE_DRIFT_MAX_PCT:
    self._drift_state = {"live_price": current, "drift_pct": drift_pct}
    return ChecklistResult.fail(
        f"{sym} reversed +{drift_pct:.2f}% from signal price "
        f"(limit +{PRICE_DRIFT_MAX_PCT}%)"
    )
```

#### 3. `receive_signal()` — two targeted edits

```python
def receive_signal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    ...
    # EDIT 1: clear any drift state left over from a previous call
    self._drift_state = {}

    ... (blacklist / bad quote / missing fields checks unchanged) ...

    hard_results, soft_results = self._run_checklist(payload, signal_age_sec)
    hard_passed = all(...)
    ...

    if not hard_passed:
        failed = next(r for r in hard_results if r.status == ChecklistResult.FAIL)

        # EDIT 2: attempt direction flip if drift state was populated
        drift = self._drift_state
        self._drift_state = {}          # consume — must clear regardless of outcome
        if drift:
            flip_result = self._try_direction_flip(
                payload,
                drift["live_price"],
                drift["drift_pct"],
                signal_age_sec,
            )
            if flip_result is not None:
                return flip_result

        reason = f"Hard check failed: {failed.reason}"
        ...
```

#### 4. New method: `_try_direction_flip()`

```python
def _try_direction_flip(
    self,
    payload: Dict[str, Any],
    live_price: float,
    drift_pct: float,
    signal_age_sec: float,
) -> Optional[Dict[str, Any]]:
    """
    Called when _check_price_still_moving() rejects due to adverse drift.
    Evaluates 3 criteria for a direction reversal; requires 2/3 to proceed.
    Works symmetrically for LONG→SHORT and SHORT→LONG.
    """
    sym      = payload.get("symbol", "?")
    orig_dir = payload.get("direction", "long")
    flipped  = "short" if orig_dir == "long" else "long"

    # ── Evaluate 3 flip criteria ─────────────────────────────────────────
    criteria_met = 0

    # 1) Volume still elevated — confirms a real move, not a liquidity gap
    vol = float(payload.get("volume_spike", 0))
    c1  = vol >= VOLUME_SPIKE_MIN
    if c1: criteria_met += 1

    # 2) Momentum has reversed sign
    momentum = float(payload.get("momentum_score", 0))
    c2 = (momentum < 0) if orig_dir == "long" else (momentum > 0)
    if c2: criteria_met += 1

    # 3) Live price crossed candle_open — confirms bearish/bullish body forming
    candle_open = payload.get("candle_open")
    if candle_open is not None:
        co = float(candle_open)
        c3 = (live_price < co) if orig_dir == "long" else (live_price > co)
    else:
        c3 = False
    if c3: criteria_met += 1

    logger.info(
        f"[BREAKOUT RECV] FLIP EVAL {sym}: {orig_dir.upper()}→{flipped.upper()} "
        f"criteria={criteria_met}/3  "
        f"vol={vol:.2f}x≥{VOLUME_SPIKE_MIN}:{c1}  "
        f"momentum={momentum:.3f} reversed:{c2}  "
        f"candle_open={float(candle_open):.4f if candle_open is not None else 'N/A'}  "
        f"live={live_price:.4f} body_confirms:{c3}"
    )

    if criteria_met < 2:
        logger.info(
            f"[BREAKOUT RECV] FLIP DENIED {sym}: only {criteria_met}/3 criteria met — "
            f"rejecting as original {orig_dir.upper()}"
        )
        return None

    # ── Build the flipped payload ────────────────────────────────────────
    p = dict(payload)   # shallow clone — all values are scalars or None

    p["direction"]     = flipped
    p["current_price"] = live_price
    p["entry_price"]   = live_price
    p["move_pct"]      = round(drift_pct, 4)

    # Negate distance — magnitude check in momentum_phase uses abs(), so safe
    dist = payload.get("distance_from_breakout_pct")
    if dist is not None:
        p["distance_from_breakout_pct"] = -float(dist)

    # Null structural_stop — original side's stop is now on wrong side of entry
    p["structural_stop_price"] = None

    logger.info(
        f"[BREAKOUT RECV] DIRECTION FLIP {sym}: {orig_dir.upper()}→{flipped.upper()} "
        f"(drift={drift_pct:+.2f}%, criteria_met={criteria_met}/3) "
        f"entry={live_price:.4f} move_pct={p['move_pct']:+.4f}%"
    )

    # ── Re-run full checklist on the mutated payload ─────────────────────
    hard_results, soft_results = self._run_checklist(p, signal_age_sec)
    hard_passed = all(
        r.status in (ChecklistResult.PASS, ChecklistResult.SKIP)
        for r in hard_results
    )
    hard_skips  = sum(1 for r in hard_results if r.status == ChecklistResult.SKIP)
    soft_passes = sum(1 for r in soft_results if r.status == ChecklistResult.PASS)
    soft_skips  = sum(1 for r in soft_results if r.status == ChecklistResult.SKIP)

    for r in hard_results:
        lvl = logging.WARNING if r.status == ChecklistResult.FAIL else logging.INFO
        logger.log(lvl, f"  [FLIP HARD] {r}")
    for r in soft_results:
        logger.info(f"  [FLIP SOFT] {r}")

    checklist_summary = {
        "hard_passed":       hard_passed,
        "hard_skipped":      hard_skips,
        "soft_passed":       soft_passes,
        "soft_skipped":      soft_skips,
        "failed_hard_check": next(
            (r.reason for r in hard_results if r.status == ChecklistResult.FAIL), None
        ),
        "direction_flip": f"{orig_dir}→{flipped}",
    }

    if not hard_passed:
        failed = next(r for r in hard_results if r.status == ChecklistResult.FAIL)
        logger.info(f"[BREAKOUT RECV] FLIP CHECKLIST REJECTED {sym} — {failed.reason}")
        return {
            "accepted":            False,
            "execution_eligible":  True,
            "failure_class":       "flip_checklist_rejected",
            "reason":              f"Direction flip failed checklist: {failed.reason}",
            "trade_id":            None,
            "checklist":           checklist_summary,
        }

    logger.info(
        f"[BREAKOUT RECV] FLIP CHECKLIST PASSED {sym} — "
        f"injecting {flipped.upper()} "
        f"soft: {soft_passes} pass / {soft_skips} skip (advisory only)"
    )
    return self._inject_signal(p, checklist_summary)
```

### Call-site flow

```
receive_signal()
│
├─ self._drift_state = {}              ← EDIT 1: wipe at call start
│
├─ _run_checklist()
│   └─ _check_price_still_moving()
│       ├─ if drift < -0.5% (LONG):  self._drift_state = {live_price, drift_pct}; return FAIL
│       └─ if drift > +0.5% (SHORT): self._drift_state = {live_price, drift_pct}; return FAIL
│
├─ if not hard_passed:
│   ├─ drift = self._drift_state; self._drift_state = {}   ← EDIT 2: consume
│   ├─ if drift:
│   │   └─ _try_direction_flip(payload, live_price, drift_pct, age)
│   │       ├─ eval 3 criteria (require ≥2)
│   │       ├─ clone + mutate payload (direction, current_price, entry_price,
│   │       │                          move_pct, distance_from_breakout_pct,
│   │       │                          structural_stop_price=None)
│   │       ├─ _run_checklist(mutated_payload)  ← full re-validation
│   │       └─ if passed → _inject_signal(); return response dict
│   │          if failed → return dict with failure_class="flip_checklist_rejected"
│   │          if criteria < 2 → return None → fall through to original rejection
│   └─ original CHECKLIST REJECTED response
│
└─ _inject_signal()
```

---

## Part 4: Re-Entry After Profitable Close

### Architecture

Two independent cooldowns block re-entry:
1. `risk_manager._last_closed` win cooldown = 120s (checked in `_check_not_in_cooldown()`)
2. `BreakoutScanner.MarketScanner._alerted_at` cooldown = 1800s (30 min) — **the bigger blocker**

Since BreakoutScanner is a separate process, the bot cannot call back into it. Instead, `scanners/market_scanner.py`'s `MarketScanner` (already wired via `set_scanner()`) synthesizes the signal and injects it directly into `breakout_receiver.receive_signal()`.

The receiver's checklist still works for synthetic signals:
- `volume_spike=1.0` → `_check_volume_elevated` returns **SKIP** (not FAIL) by design
- Omitting OHLC → `_check_no_wick_rejection` returns **SKIP**
- `timestamp=now()` → `_check_freshness` always passes (0s old)
- `bars_since_breakout=1` → `_check_momentum_phase` passes if price hasn't run >8% from level

### Component A — Trade close callback (position_monitor.py only)

```python
# ── PositionMonitor.__init__() ──────────────────────────────────────────────
self._on_breakout_win_closed: Optional[Callable] = None

def set_breakout_win_callback(self, cb: Callable[[str, bool, float, str], None]) -> None:
    self._on_breakout_win_closed = cb
```

**Injection point 1** — `_attempt_close()` success branch:
```python
if success:
    self._reset_close_attempts(trade_id)
    if self._on_breakout_win_closed and _is_breakout_trade(trade):
        direction = trade["direction"]
        entry     = trade["entry_price"]
        won = (
            (direction == "long"  and current_price > entry) or
            (direction == "short" and current_price < entry)
        )
        try:
            self._on_breakout_win_closed(symbol, won, current_price, direction)
        except Exception:
            pass
    return True
```

**Injection point 2** — `_record_close_in_db()` (IBKR fallback + reconciliation paths):
```python
risk_manager.record_trade_result(pnl=pnl, trade_won=(pnl > 0), symbol=symbol)
if self._on_breakout_win_closed and _is_breakout_trade(trade):
    try:
        self._on_breakout_win_closed(symbol, pnl > 0, exit_price, trade["direction"])
    except Exception:
        pass
```

**Helper** (file-level):
```python
import json as _json

def _is_breakout_trade(trade: Dict) -> bool:
    if trade.get("strategy_name") == "breakout_scanner":
        return True
    try:
        meta = _json.loads(trade.get("indicators_json") or "{}")
        return meta.get("strategy_name") == "breakout_scanner"
    except Exception:
        return False
```

### Component B — `MarketScanner.re_entry_scan()` (scanners/market_scanner.py)

```python
# New imports
import threading
from datetime import datetime, timezone

WIN_REENTRY_DELAY_SEC = 125   # 120s cooldown + 5s buffer

class MarketScanner:

    def __init__(self, ...):
        ...
        self._receiver_ref         = None
        self._pending_reentry: set = set()
        self._pending_lock         = threading.Lock()

    def set_reentry_receiver(self, receiver) -> None:
        self._receiver_ref = receiver

    def schedule_reentry(self, symbol: str, exit_price: float, direction: str) -> None:
        """Called from the position monitor thread. Only creates a Timer."""
        with self._pending_lock:
            if symbol in self._pending_reentry:
                logger.info(f"[REENTRY] {symbol}: already pending — skipped duplicate")
                return
            self._pending_reentry.add(symbol)

        t = threading.Timer(
            WIN_REENTRY_DELAY_SEC,
            self._safe_reentry_scan,
            args=[symbol, exit_price, direction],
        )
        t.daemon = True
        t.start()
        logger.info(
            f"[REENTRY] {symbol} {direction} re-entry scan "
            f"scheduled in {WIN_REENTRY_DELAY_SEC}s"
        )

    def _safe_reentry_scan(self, symbol: str, exit_price: float, direction: str) -> None:
        with self._pending_lock:
            self._pending_reentry.discard(symbol)
        try:
            self._do_reentry_scan(symbol, exit_price, direction)
        except Exception as e:
            logger.error(f"[REENTRY] {symbol}: scan failed: {e}", exc_info=True)

    def _do_reentry_scan(self, symbol: str, exit_price: float, direction: str) -> None:
        if not self._receiver_ref:
            logger.warning("[REENTRY] No receiver wired — skipping")
            return

        asset_class   = "crypto" if "/" in symbol else "stock"
        current_price = self.get_current_price(symbol, asset_class)

        if not current_price:
            logger.info(f"[REENTRY] {symbol}: could not fetch live price — aborting")
            return

        drift_pct = ((current_price - exit_price) / exit_price) * 100
        if direction == "long"  and drift_pct < -0.3:
            logger.info(f"[REENTRY] {symbol}: reversed {drift_pct:.2f}% since exit — skip")
            return
        if direction == "short" and drift_pct >  0.3:
            logger.info(f"[REENTRY] {symbol}: reversed {drift_pct:+.2f}% since exit — skip")
            return

        payload = {
            "symbol":                      symbol,
            "asset_class":                 asset_class,
            "direction":                   direction,
            "entry_price":                 current_price,
            "current_price":               current_price,
            "move_pct":                    drift_pct,
            "volume_spike":                1.0,       # receiver SKIPs 1.0
            "confidence":                  0.70,
            "escalation":                  1,
            "timestamp":                   datetime.now(timezone.utc).isoformat(),
            "broker":                      "kraken" if asset_class == "crypto" else "alpaca",
            "bars_since_breakout":         1,
            "distance_from_breakout_pct":  abs(drift_pct),
            # Omit OHLC → _check_no_wick_rejection SKIPs (neutral)
            # Omit rsi/sma200 → soft checks SKIP (advisory only)
        }

        logger.info(
            f"[REENTRY] Injecting {symbol} {direction} @ ${current_price:.4f} "
            f"(exited @ ${exit_price:.4f}, drift={drift_pct:+.2f}%)"
        )

        result = self._receiver_ref.receive_signal(payload)
        accepted = result.get("accepted", False)
        logger.info(
            f"[REENTRY] {symbol}: "
            f"{'ACCEPTED → trade_id=' + str(result.get('trade_id')) if accepted else 'REJECTED — ' + result.get('reason', '?')}"
        )
```

### Component C — Wiring in bot_engine.py

```python
# After existing wiring:
breakout_receiver.set_executor(self.trade_executor)
breakout_receiver.set_scanner(self.market_scanner)

# NEW: wire re-entry path
self.market_scanner.set_reentry_receiver(breakout_receiver)

def _on_breakout_win_closed(symbol: str, won: bool,
                             exit_price: float, direction: str) -> None:
    if won:
        try:
            self.market_scanner.schedule_reentry(symbol, exit_price, direction)
        except Exception as e:
            logger.error(f"[REENTRY HOOK] schedule failed for {symbol}: {e}")

from core.position_monitor import monitor as _monitor
_monitor.set_breakout_win_callback(_on_breakout_win_closed)
```

### Thread safety

| Shared resource | Risk | Mitigation |
|----------------|------|-----------|
| `_pending_reentry` set | Read-write race | Protected by `_pending_lock` |
| `_receiver_ref` | None — set once at startup | Safe |
| `risk_manager._last_closed` | Timer fires at exactly 120s, stale read possible | 5s buffer makes this non-issue |
| Duplicate Timer same symbol | Double re-entry | `_pending_lock` + `_pending_reentry` blocks second |

### Implementation order

1. **Component A** (position_monitor callback hook) — isolated, testable, no new logic
2. **Component B** (MarketScanner) — test standalone by calling `schedule_reentry()` manually  
3. **Component C** (bot_engine wiring) — one block in `__init__`, done

---

## Implementation Priority

| Priority | Item | Files | Effort |
|----------|------|-------|--------|
| P1 | Fix 3: Refresh enrichment on escalation re-sends | `BreakoutScanner.py` | 3 lines |
| P1 | Fix 2: Bypass dedup for esc > 0 | `breakout_sender.py` | 4 lines |
| P2 | Add `bars_since_breakout` | `BreakoutScanner.py` | 5 lines |
| P2 | Add `breakout_level` + `distance_from_breakout_pct` | `BreakoutScanner.py` | 8 lines |
| P2 | Add `structural_stop_price` | `BreakoutScanner.py` | 6 lines |
| P3 | Direction flip logic | `core/breakout_receiver.py` | ~100 lines |
| P3 | Re-entry after profitable close | `core/position_monitor.py`, `scanners/market_scanner.py`, `bot_engine.py` | ~80 lines |
| P4 | `market_pct_change` for stocks | `BreakoutScanner.py` | 12 lines |
| P4 | `source_broker/price/timestamp` | `breakout_sender.py` | 3 lines |
| Skip | `sma200` | N/A | Not worth raising history_length to 200 |
