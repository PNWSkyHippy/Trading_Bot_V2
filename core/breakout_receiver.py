"""
core/breakout_receiver.py  (hardened v2.1)
=========================================
Receives inbound breakout signals from BreakoutScanner and injects them
into the trade executor after a fast validation checklist.

Changes from v1:
  - Fixed Signal(...) constructor crash: broker removed from top-level args,
    placed inside indicators["preferred_broker"] instead
  - Added reason= to Signal constructor (required field)
  - Required-field validation BEFORE checklist (3 failure classes)
  - Signal freshness / TTL check (hard gate)
  - Soft checks now use NEUTRAL status — skipped checks do NOT count as passes
  - Hard checks: SKIP = neutral (does not block), only FAIL blocks
  - Price re-verify now REJECTS on scanner unavailable (no longer fail-open)
  - Wick check: SKIP (neutral) when OHLC missing; FAIL when OHLC present but bad
  - Symmetric market context (blocks shorts in rallying market too)
  - Structural stop sanity check (stop must be on correct side of price)
  - Structured logging for every inbound signal
  - 3-class response: invalid_payload / checklist_rejected / injection_exception

Failure classes:
  1. invalid_payload        — missing required fields; signal not even evaluated
  2. checklist_rejected     — fields present but failed validation gate
  3. injection_exception    — all checks passed but executor threw an error
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List

import config
from data.database import db
from core.risk_manager import risk_manager
from core.trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

# ── Tuning constants ────────────────────────────────────────────────────────
SIGNAL_TTL_SEC          = 60      # reject signals older than this
VOLUME_SPIKE_MIN        = 1.5     # >= 1.5x 20-period average
WICK_BODY_MAX_RATIO     = 2.0     # wick <= 2x body (fakeout filter)
GAP_TRAP_MAX_PCT        = 30.0    # reject if total move > 30%
                                  # (was 15%; raised because crypto 15-25% moves are
                                  #  legitimate breakouts and were being blocked en masse.
                                  #  Truly manipulated/wash moves tend to be 50%+.)
PRICE_DRIFT_MAX_PCT     = 0.5     # price must not have reversed > 0.5%
STOP_MAX_DISTANCE_STOCK = 2.5     # max stop distance % for stocks
STOP_MAX_DISTANCE_CRYPTO= 5.0     # max stop distance % for crypto
                                  # (was 3.5%; raised to match two-bar structural trail
                                  #  which can place stops 4-6% away on volatile movers)
RSI_LONG_MIN            = 50.0
RSI_LONG_EXHAUST        = 82.0
RSI_SHORT_MAX           = 50.0
RSI_SHORT_EXHAUST       = 18.0
MARKET_CRASH_THRESHOLD  = -2.0
MARKET_RALLY_THRESHOLD  = +2.0
MIN_SOFT_PASSES         = 0       # need this many actual soft PASSes (skips neutral)

# Symbols permanently banned from breakout entries.
# MLN/USD: 6 consecutive losses — thin liquidity, erratic breakouts, never recovered.
BREAKOUT_SYMBOL_BLACKLIST = {"MLN/USD", "MLNUSD", "MLN/USDT", "MLNUSDT"}

REQUIRED_FIELDS = [
    "symbol", "asset_class", "direction",
    "entry_price", "current_price",
    "move_pct", "volume_spike",
    "confidence", "escalation", "timestamp",
]


class ChecklistResult:
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, status: str, reason: str):
        self.status = status
        self.passed = (status == self.PASS)
        self.reason = reason

    @classmethod
    def ok(cls, reason: str) -> "ChecklistResult":
        return cls(cls.PASS, reason)

    @classmethod
    def fail(cls, reason: str) -> "ChecklistResult":
        return cls(cls.FAIL, reason)

    @classmethod
    def skip(cls, reason: str) -> "ChecklistResult":
        return cls(cls.SKIP, reason)

    def __repr__(self):
        return f"[{self.status}] {self.reason}"


class BreakoutReceiver:

    def __init__(self):
        self._executor: Optional[TradeExecutor] = None
        self._scanner_ref = None

    def set_executor(self, executor: TradeExecutor):
        self._executor = executor

    def set_scanner(self, scanner):
        self._scanner_ref = scanner

    def receive_signal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sym           = payload.get("symbol", "?")
        direction     = payload.get("direction", "?")
        esc           = payload.get("escalation", 0)
        ts_in         = payload.get("timestamp", "")
        signal_age_sec = self._signal_age(ts_in)

        # Hard symbol blacklist — checked before everything else
        if sym.upper() in BREAKOUT_SYMBOL_BLACKLIST:
            logger.info(f"[BREAKOUT RECV] {sym} rejected — in permanent symbol blacklist (serial loser)")
            return {"status": "rejected", "reason": f"{sym} in breakout symbol blacklist"}

        logger.info(
            f"[BREAKOUT RECV] {sym} {str(direction).upper()} "
            f"esc={esc} move={payload.get('move_pct', 0):+.2f}% "
            f"age={signal_age_sec:.0f}s vol={payload.get('volume_spike', 0):.2f}x "
            f"stop={payload.get('structural_stop_price', 'none')} "
            f"bars_since={payload.get('bars_since_breakout', '?')}"
        )

        # Stage 1: Required field validation
        missing = [f for f in REQUIRED_FIELDS if payload.get(f) is None]
        if missing:
            reason = f"Missing required fields: {', '.join(missing)}"
            logger.warning(f"[BREAKOUT RECV] INVALID PAYLOAD {sym} — {reason}")
            return {
                "accepted": False, "execution_eligible": False,
                "failure_class": "invalid_payload",
                "reason": reason, "trade_id": None, "checklist": {},
            }

        # Stage 2: Checklist
        hard_results, soft_results = self._run_checklist(payload, signal_age_sec)

        # Hard: PASS or SKIP = OK, only FAIL blocks
        hard_passed  = all(
            r.status in (ChecklistResult.PASS, ChecklistResult.SKIP)
            for r in hard_results
        )
        hard_skips   = sum(1 for r in hard_results if r.status == ChecklistResult.SKIP)
        soft_passes  = sum(1 for r in soft_results if r.status == ChecklistResult.PASS)
        soft_skips   = sum(1 for r in soft_results if r.status == ChecklistResult.SKIP)

        for r in hard_results:
            lvl = logging.WARNING if r.status == ChecklistResult.FAIL else logging.INFO
            logger.log(lvl, f"  [HARD] {r}")
        for r in soft_results:
            logger.info(f"  [SOFT] {r}")

        checklist_summary = {
            "hard_passed":       hard_passed,
            "hard_skipped":      hard_skips,
            "soft_passed":       soft_passes,
            "soft_skipped":      soft_skips,
            "failed_hard_check": next(
                (r.reason for r in hard_results if r.status == ChecklistResult.FAIL), None
            ),
        }

        if not hard_passed:
            failed = next(r for r in hard_results if r.status == ChecklistResult.FAIL)
            reason = f"Hard check failed: {failed.reason}"
            logger.info(f"[BREAKOUT RECV] CHECKLIST REJECTED {sym} — {reason}")
            return {
                "accepted": False, "execution_eligible": True,
                "failure_class": "checklist_rejected",
                "reason": reason, "trade_id": None, "checklist": checklist_summary,
            }

        # Soft checks are advisory only (MIN_SOFT_PASSES = 0).
        # RSI / trend / market context are logged for visibility but never block execution.
        logger.info(
            f"[BREAKOUT RECV] CHECKLIST PASSED {sym} — "
            f"soft: {soft_passes} pass / {soft_skips} skip (advisory only)"
        )
        return self._inject_signal(payload, checklist_summary)

    def _run_checklist(
        self, p: Dict, signal_age_sec: float
    ) -> Tuple[List[ChecklistResult], List[ChecklistResult]]:
        hard = [
            self._check_freshness(p, signal_age_sec),
            self._check_no_open_position(p),
            self._check_daily_symbol_limit(p),   # cap MLN/USD-style serial losses
            self._check_not_in_cooldown(p),
            self._check_trading_not_halted(),
            self._check_price_still_moving(p),
            self._check_volume_elevated(p),
            self._check_no_wick_rejection(p),   # SKIP when OHLC missing (neutral)
            self._check_not_gap_trap(p),
            self._check_momentum_phase(p),      # reject late/exhausted parabolic entries
            self._check_structural_stop(p),
        ]
        soft = [
            self._check_rsi_confirms(p),
            self._check_trend_alignment(p),
            self._check_market_context(p),
        ]
        return hard, soft

    def _check_freshness(self, p: Dict, age_sec: float) -> ChecklistResult:
        if age_sec < 0:
            return ChecklistResult.fail("Signal timestamp missing or unparsable")
        if age_sec > SIGNAL_TTL_SEC:
            return ChecklistResult.fail(
                f"Signal stale — {age_sec:.0f}s old (TTL={SIGNAL_TTL_SEC}s)"
            )
        return ChecklistResult.ok(f"Signal fresh ({age_sec:.0f}s old)")

    def _check_no_open_position(self, p: Dict) -> ChecklistResult:
        sym = p["symbol"]
        if any(t["symbol"] == sym for t in (db.get_open_trades() or [])):
            return ChecklistResult.fail(f"Already have open position on {sym}")
        return ChecklistResult.ok(f"No existing position on {sym}")

    def _check_daily_symbol_limit(self, p: Dict) -> ChecklistResult:
        """
        Cap breakout_scanner trades per symbol per day at MAX_DAILY_PER_SYMBOL.
        Prevents MLN/USD-style serial losses where the 10-min cooldown keeps
        resetting and the same symbol gets traded 6+ times in one session.
        """
        MAX_DAILY_PER_SYMBOL = 2
        sym = p["symbol"]
        try:
            today = __import__("datetime").date.today().isoformat()
            count = len([
                t for t in (db.get_trades_for_date(today) or [])
                if t.get("symbol") == sym
                and t.get("strategy_name") == "breakout_scanner"
            ])
            if count >= MAX_DAILY_PER_SYMBOL:
                return ChecklistResult.fail(
                    f"{sym} already traded {count}× today via breakout_scanner "
                    f"(daily limit={MAX_DAILY_PER_SYMBOL})"
                )
        except Exception as e:
            logger.debug(f"[DAILY LIMIT] Could not check daily trade count: {e}")
        return ChecklistResult.ok(f"Daily symbol limit OK")

    def _check_not_in_cooldown(self, p: Dict) -> ChecklistResult:
        sym  = p["symbol"]
        last = getattr(risk_manager, "_last_closed", {}).get(sym)
        if last:
            elapsed  = time.time() - last.get("time", 0)
            cooldown = 120 if last.get("won") else 600
            if elapsed < cooldown:
                return ChecklistResult.fail(
                    f"{sym} in cooldown — {int((cooldown-elapsed)/60)}min remaining"
                )
        return ChecklistResult.ok(f"{sym} not in cooldown")

    def _check_trading_not_halted(self) -> ChecklistResult:
        today   = datetime.now().date().isoformat()
        session = db.get_session(today) or {}
        if session.get("trading_halted"):
            return ChecklistResult.fail(
                f"Trading halted: {session.get('halt_reason', 'unknown')}"
            )
        consec = session.get("consecutive_losses", 0)
        if consec >= getattr(config, "MAX_CONSECUTIVE_LOSSES", 3):
            return ChecklistResult.fail(f"Consecutive loss limit hit ({consec})")
        return ChecklistResult.ok("Trading active")

    def _check_price_still_moving(self, p: Dict) -> ChecklistResult:
        sym       = p["symbol"]
        asset     = p.get("asset_class", "crypto")
        # Use current_price as the reference (it's the price when the signal fired),
        # falling back to entry_price so pre-BREAKOUT-8A payloads still work.
        ref_price = float(p.get("current_price") or p.get("entry_price", 0))
        direction = p.get("direction", "long")

        if not self._scanner_ref:
            return ChecklistResult.fail(
                "Price re-verify impossible — scanner not wired to receiver"
            )
        if ref_price <= 0:
            return ChecklistResult.fail("current_price/entry_price is zero or missing")

        try:
            current = self._scanner_ref.get_current_price(sym, asset)
            if not current:
                # Price unfetchable for this specific symbol (common for /USDC pairs
                # that Kraken doesn't list as /USDC — not a scanner infrastructure
                # failure, just an illiquid or USDC-quoted pair).  SKIP = neutral;
                # the scanner-not-wired case above is the true infrastructure failure.
                return ChecklistResult.skip(
                    f"Could not fetch live price for {sym} — skipping price drift check"
                )
            drift_pct = ((current - ref_price) / ref_price) * 100
            if direction == "long" and drift_pct < -PRICE_DRIFT_MAX_PCT:
                return ChecklistResult.fail(
                    f"{sym} reversed {drift_pct:.2f}% from signal price "
                    f"(limit -{PRICE_DRIFT_MAX_PCT}%)"
                )
            if direction == "short" and drift_pct > PRICE_DRIFT_MAX_PCT:
                return ChecklistResult.fail(
                    f"{sym} reversed +{drift_pct:.2f}% from signal price "
                    f"(limit +{PRICE_DRIFT_MAX_PCT}%)"
                )
            return ChecklistResult.ok(f"{sym} still moving (drift={drift_pct:+.2f}%)")
        except Exception as e:
            return ChecklistResult.fail(f"Price re-verify exception: {e}")

    def _check_volume_elevated(self, p: Dict) -> ChecklistResult:
        vol = float(p.get("volume_spike", 0))
        # vol == 1.0 exactly is the _vol_spike() default fallback when there is
        # no volume history (e.g. CoinGecko-sourced ticks with volume=0).
        # It is NOT a real measurement, so treat it as "no data" → SKIP, not FAIL.
        if vol == 1.0:
            return ChecklistResult.skip(
                "Volume spike is 1.00x (default fallback — no volume history) — skipping"
            )
        if vol < VOLUME_SPIKE_MIN:
            return ChecklistResult.fail(
                f"Volume spike {vol:.2f}x below minimum {VOLUME_SPIKE_MIN}x"
            )
        return ChecklistResult.ok(f"Volume elevated {vol:.2f}x")

    def _check_no_wick_rejection(self, p: Dict) -> ChecklistResult:
        """
        SKIP (neutral) if OHLC not provided — scanner needs upgrade to send it.
        FAIL if OHLC present and shows fakeout wick.
        TODO: Change skip to fail once scanner reliably sends OHLC.
        """
        o, h, l, c = p.get("candle_open"), p.get("candle_high"), \
                     p.get("candle_low"),  p.get("candle_close")

        if not all(v is not None for v in [o, h, l, c]):
            return ChecklistResult.skip(
                "Wick check skipped — OHLC not in payload (scanner upgrade needed)"
            )

        o, h, l, c = float(o), float(h), float(l), float(c)
        body = abs(c - o)
        if body == 0:
            return ChecklistResult.fail("Doji candle — no body (fakeout risk)")

        direction = p.get("direction", "long")
        if direction == "long":
            wick = h - max(o, c)
            if wick > body * WICK_BODY_MAX_RATIO:
                return ChecklistResult.fail(
                    f"Upper wick {wick:.4f} > {WICK_BODY_MAX_RATIO}x body {body:.4f}"
                )
        else:
            wick = min(o, c) - l
            if wick > body * WICK_BODY_MAX_RATIO:
                return ChecklistResult.fail(
                    f"Lower wick {wick:.4f} > {WICK_BODY_MAX_RATIO}x body {body:.4f}"
                )
        return ChecklistResult.ok("Candle body valid")

    def _check_not_gap_trap(self, p: Dict) -> ChecklistResult:
        move = abs(float(p.get("move_pct", 0)))
        if move > GAP_TRAP_MAX_PCT:
            return ChecklistResult.fail(
                f"Move {move:.1f}% > gap trap threshold {GAP_TRAP_MAX_PCT}%"
            )
        return ChecklistResult.ok(f"Move {move:.1f}% within range")

    def _check_momentum_phase(self, p: Dict) -> ChecklistResult:
        """
        Reject entries that are LATE in a parabolic move.

        The scanner fires after detecting a large price move. If we're already
        many bars past the breakout level, or RSI is exhausted, we're buying
        the top (long) or selling the bottom (short) — exactly the wrong side.

        Thresholds derived from breakout scanner analysis:
        - bars_since_breakout > 4: move is 4+ bars old, most momentum consumed
        - distance_from_breakout_pct > 8%: price has moved 8%+ from the level;
          a normal continuation trade targets 5-7% — that's already gone
        - RSI exhaustion: >78 for longs (overbought), <22 for shorts (oversold)
        """
        direction   = p.get("direction", "long")
        bars_since  = p.get("bars_since_breakout")
        dist_pct    = p.get("distance_from_breakout_pct")
        rsi         = p.get("rsi")

        MAX_BARS_SINCE    = 4
        MAX_DIST_FROM_LVL = 8.0   # %
        RSI_EXHAUST_LONG  = 78
        RSI_EXHAUST_SHORT = 22

        if bars_since is not None:
            bars_since = int(bars_since)
            if bars_since > MAX_BARS_SINCE:
                return ChecklistResult.fail(
                    f"Move is {bars_since} bars old — too late to enter "
                    f"(max {MAX_BARS_SINCE} bars from breakout level)"
                )

        if dist_pct is not None:
            dist = abs(float(dist_pct))
            if dist > MAX_DIST_FROM_LVL:
                return ChecklistResult.fail(
                    f"Price already {dist:.1f}% from breakout level — chasing "
                    f"(max {MAX_DIST_FROM_LVL}% allowed)"
                )

        if rsi is not None:
            rsi_f = float(rsi)
            if direction == "long" and rsi_f >= RSI_EXHAUST_LONG:
                return ChecklistResult.fail(
                    f"RSI {rsi_f:.1f} overbought — parabolic up likely exhausted "
                    f"(long rejected, threshold={RSI_EXHAUST_LONG})"
                )
            if direction == "short" and rsi_f <= RSI_EXHAUST_SHORT:
                return ChecklistResult.fail(
                    f"RSI {rsi_f:.1f} oversold — parabolic down likely exhausted "
                    f"(short rejected, threshold={RSI_EXHAUST_SHORT})"
                )

        return ChecklistResult.ok(
            f"Momentum phase OK: bars_since={bars_since} dist={dist_pct}% rsi={rsi}"
        )

    def _check_structural_stop(self, p: Dict) -> ChecklistResult:
        stop      = p.get("structural_stop_price")
        price     = float(p.get("current_price") or p.get("entry_price", 0))
        direction = p.get("direction", "long")
        asset     = p.get("asset_class", "crypto")

        if stop is None:
            return ChecklistResult.ok("No structural stop — executor computes percent-based")

        stop = float(stop)
        if price <= 0:
            return ChecklistResult.ok("Stop sanity skipped — no price")

        if direction == "long" and stop >= price:
            return ChecklistResult.fail(
                f"Stop {stop:.4f} >= price {price:.4f} — already broken for long"
            )
        if direction == "short" and stop <= price:
            return ChecklistResult.fail(
                f"Stop {stop:.4f} <= price {price:.4f} — already broken for short"
            )

        max_dist = STOP_MAX_DISTANCE_CRYPTO if asset == "crypto" else STOP_MAX_DISTANCE_STOCK
        dist_pct = abs(price - stop) / price * 100
        if dist_pct > max_dist:
            return ChecklistResult.fail(
                f"Stop too far: {dist_pct:.2f}% > max {max_dist}%"
            )
        return ChecklistResult.ok(f"Stop valid: {stop:.4f} ({dist_pct:.2f}% away)")

    def _check_rsi_confirms(self, p: Dict) -> ChecklistResult:
        rsi       = p.get("rsi")
        direction = p.get("direction", "long")
        if rsi is None:
            return ChecklistResult.skip("RSI not provided — neutral")
        rsi = float(rsi)
        if direction == "long":
            if rsi >= RSI_LONG_EXHAUST:
                return ChecklistResult.fail(f"RSI {rsi:.1f} overbought")
            if rsi < RSI_LONG_MIN:
                return ChecklistResult.fail(f"RSI {rsi:.1f} below {RSI_LONG_MIN}")
        else:
            if rsi <= RSI_SHORT_EXHAUST:
                return ChecklistResult.fail(f"RSI {rsi:.1f} oversold")
            if rsi > RSI_SHORT_MAX:
                return ChecklistResult.fail(f"RSI {rsi:.1f} above {RSI_SHORT_MAX}")
        return ChecklistResult.ok(f"RSI {rsi:.1f} confirms {direction}")

    def _check_trend_alignment(self, p: Dict) -> ChecklistResult:
        sma200    = p.get("sma200")
        price     = float(p.get("current_price") or p.get("entry_price", 0))
        direction = p.get("direction", "long")
        if sma200 is None or price <= 0:
            return ChecklistResult.skip("SMA200 not provided — neutral")
        sma200 = float(sma200)
        if direction == "long" and price < sma200:
            return ChecklistResult.fail(f"Price below SMA200 — counter-trend long")
        if direction == "short" and price > sma200:
            return ChecklistResult.fail(f"Price above SMA200 — counter-trend short")
        return ChecklistResult.ok("Trend aligned")

    def _check_market_context(self, p: Dict) -> ChecklistResult:
        mkt_chg   = p.get("market_pct_change")
        direction = p.get("direction", "long")
        if mkt_chg is None:
            return ChecklistResult.skip("Market context not provided — neutral")
        mkt_chg = float(mkt_chg)
        if direction == "long" and mkt_chg < MARKET_CRASH_THRESHOLD:
            return ChecklistResult.fail(f"Market down {mkt_chg:.1f}% — bad for longs")
        if direction == "short" and mkt_chg > MARKET_RALLY_THRESHOLD:
            return ChecklistResult.fail(f"Market up {mkt_chg:.1f}% — bad for shorts")
        return ChecklistResult.ok(f"Market context OK ({mkt_chg:+.1f}%)")

    def _inject_signal(self, p: Dict, checklist: dict) -> Dict:
        if not self._executor:
            logger.error("[BREAKOUT RECV] Executor not set")
            return {
                "accepted": False, "failure_class": "injection_exception",
                "reason": "Executor not configured", "trade_id": None,
                "checklist": checklist,
            }

        try:
            from scanners.market_scanner import Signal

            asset_class = p.get("asset_class", "crypto")
            direction   = p.get("direction", "long")
            sym         = p["symbol"]
            price       = float(p.get("current_price") or p.get("entry_price"))
            esc         = p.get("escalation", 0)
            broker_hint = str(p.get("broker", "kraken")).lower()

            # ── Move-proportional stop loss ───────────────────────────────
            # Default 1.5% fixed stop bleeds on crypto: after a 5-10% move,
            # normal pullbacks hit it. Use a stop proportional to the move
            # so the trade has room to breathe.
            # Formula: max(move_pct * 0.30, 2.0), capped at 4.5%.
            # Only applied when no structural stop is already provided
            # (structural stop is more precise and always preferred).
            # Stocks keep the existing default — this only applies to crypto
            # where the serial-loss pattern was observed.
            move_pct_abs = abs(float(p.get("move_pct", 0)))
            has_structural_stop = p.get("structural_stop_price") is not None
            if asset_class == "crypto" and not has_structural_stop:
                custom_stop = round(min(max(move_pct_abs * 0.30, 2.0), 4.5), 2)
                logger.info(
                    f"[BREAKOUT RECV] {sym} custom_stop_loss_pct={custom_stop}% "
                    f"(move={move_pct_abs:.1f}%, no structural stop)"
                )
            else:
                custom_stop = None  # use structural stop or executor default

            signal = Signal(
                symbol        = sym,
                asset_class   = asset_class,
                direction     = direction,
                score         = min(float(p.get("confidence", 0.7)) + 0.1, 1.0),
                current_price = price,
                reason        = (
                    f"breakout_scanner esc={esc} "
                    f"move={p.get('move_pct', 0):+.1f}% "
                    f"vol={p.get('volume_spike', 0):.1f}x"
                ),
                indicators    = {
                    "strategy_name":              "breakout_scanner",
                    "timeframe":                  "5m" if asset_class == "crypto" else "5Min",
                    "signal_source":              "breakout_scanner",
                    "preferred_broker":           broker_hint,
                    "escalation":                 esc,
                    "move_pct":                   p.get("move_pct", 0),
                    "volume_spike":               p.get("volume_spike", 0),
                    "momentum_score":             p.get("momentum_score", 0),
                    "pattern":                    p.get("pattern", "breakout"),
                    "rsi":                        p.get("rsi"),
                    "sma200":                     p.get("sma200"),
                    "structural_stop_price":      p.get("structural_stop_price"),
                    "breakout_level":             p.get("breakout_level"),
                    "bars_since_breakout":        p.get("bars_since_breakout"),
                    "distance_from_breakout_pct": p.get("distance_from_breakout_pct"),
                    # Move-proportional stop: wider than default 1.5% for crypto
                    # when no structural stop exists. None = use structural/default.
                    "custom_stop_loss_pct":       custom_stop,
                },
            )

            logger.info(
                f"[BREAKOUT RECV] INJECTING {sym} {direction.upper()} "
                f"@ ${price:.4f} | esc={esc} move={p.get('move_pct',0):+.2f}% "
                f"preferred_broker={broker_hint}"
            )

            trade_id = self._executor.execute_signal(signal)

            if trade_id:
                logger.info(f"[BREAKOUT RECV] EXECUTED {sym} -> trade_id={trade_id}")
                return {
                    "accepted": True, "execution_eligible": True,
                    "failure_class": None, "reason": "Signal executed",
                    "trade_id": trade_id, "checklist": checklist,
                }
            else:
                logger.warning(f"[BREAKOUT RECV] Executor rejected {sym}")
                return {
                    "accepted": False, "execution_eligible": True,
                    "failure_class": "checklist_rejected",
                    "reason": "Executor rejected (risk manager or broker)",
                    "trade_id": None, "checklist": checklist,
                }

        except Exception as e:
            logger.error(
                f"[BREAKOUT RECV] Injection exception for {p.get('symbol')}: {e}",
                exc_info=True,
            )
            return {
                "accepted": False, "execution_eligible": True,
                "failure_class": "injection_exception",
                "reason": f"Injection exception: {e}",
                "trade_id": None, "checklist": checklist,
            }

    @staticmethod
    def _signal_age(timestamp_str: str) -> float:
        if not timestamp_str:
            return -1.0
        try:
            ts = datetime.fromisoformat(
                str(timestamp_str).replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc) if ts.tzinfo else datetime.now()
            return (now - ts).total_seconds()
        except Exception:
            return -1.0


# Module singleton
breakout_receiver = BreakoutReceiver()
