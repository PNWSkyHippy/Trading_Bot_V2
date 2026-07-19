"""
core/breakout_receiver.py  (hardened v2.2)
=========================================
Receives inbound breakout signals from BreakoutScanner and injects them
into the trade executor after a fast validation checklist.

v2.2 additions:
  - Understands sender's source_broker / source_price / source_timestamp
  - No longer relies solely on scanner.get_current_price(); falls back to
    scanner fetchers directly
  - Normalizes broker names and preserves both preferred_broker + source_broker
  - Blacklist rejections now return the same structured response shape

PATCH NOTES — 2026-07-18, Step 8 (Reconciled Safe Patch Sequence, scoped —
see core/breakout_decision.py's own patch notes for the full rationale,
what was deliberately left untouched, and the back-out steps). Summary of
what changed in THIS file:
  - `ChecklistResult` is now imported from core.breakout_decision instead
    of being defined here (identical class, one definition).
  - The `min_escalation` gate in receive_signal() and the bars-since-
    breakout staleness check in _check_momentum_phase() now call shared
    functions (`escalation_meets_minimum`, `is_breakout_stale`) from
    core.breakout_decision instead of comparing against locally-inlined
    thresholds — same values (3 bars), same semantics, single source of
    truth shared with breakout_sender.py's should_send().
  - No other check's logic, DB access, network call, side effect, or
    ordering changed.
"""

import json
import logging
import math
import threading
import time
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, Tuple, List

import config
from core.scanner_controls import is_scanner_enabled
from data.database import db
from core.risk_manager import risk_manager
from core.trade_executor import TradeExecutor
from core.event_identity import (
    hash_breakout_payload,
    derive_client_order_id,
)
from core.breakout_decision import (
    ChecklistResult,
    MAX_BREAKOUT_AGE_BARS,
    is_breakout_stale,
    escalation_meets_minimum,
)
from core.crypto_quote import live_ticker_reference

logger = logging.getLogger(__name__)


def _optional_finite_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    """Coerce optional scanner telemetry without letting bad data crash a request."""
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default

# ── Tuning constants ────────────────────────────────────────────────────────
SIGNAL_TTL_SEC          = 60
VOLUME_SPIKE_MIN        = 1.2   # Opus retune: 2.0 was filtering too many valid breakouts;
WICK_BODY_MAX_RATIO     = 2.0
GAP_TRAP_MAX_PCT        = 30.0
PRICE_DRIFT_MAX_PCT     = 0.5
STOP_MAX_DISTANCE_STOCK = 2.5
STOP_MAX_DISTANCE_CRYPTO= 3.5
RSI_LONG_MIN            = 50.0
RSI_LONG_EXHAUST        = 82.0
RSI_SHORT_MAX           = 50.0
RSI_SHORT_EXHAUST       = 18.0
MARKET_CRASH_THRESHOLD  = -2.0
MARKET_RALLY_THRESHOLD  = +2.0
MIN_SOFT_PASSES         = 0
MIN_PRICE_CRYPTO        = 0.0001
MAX_CONCURRENT_BREAKOUTS= 15     # breakout gets half the 30-slot system budget; leaves room for other strategies
MAX_CONCURRENT_CRYPTO   = 15     # same — crypto breakouts share the same 15-slot cap
PUMP_VOLUME_SPIKE_MAX   = 15.0   # volume spike above this = coordinated pump (organic breaks rarely > 10x)
PUMP_MOVE_MAX_CRYPTO    = 15.0   # crypto move above this % = likely already at pump peak, not start

# Quiet hours — block crypto during the truly thin overnight window.
# 02:00–12:00 UTC = 10pm ET to 8am ET — dead zone (post-US, pre-London).
# Allows: US session (12:00–02:00 UTC next day = 8am–10pm ET) + early London open.
# Blocks: the genuinely dead 10pm–8am ET window that caused 25 overnight losses.
QUIET_HOURS_START_UTC   = 11       # 2am UTC = 2am PST
QUIET_HOURS_END_UTC     = 12     # noon UTC = 6m PST


BREAKOUT_SYMBOL_BLACKLIST = {"MLN/USD", "MLNUSD", "MLN/USDT", "MLNUSDT",
                             "XBT/USD", "XBTUSD"}  # Kraken BTC alias — position monitor gets 0.0002 bad tick

# Reject any symbol whose quote currency is not USD.
# USDC, USDT, BUSD pairs can't be priced by Kraken's USD feed and get stuck
# in the position monitor indefinitely, jamming the scan loop.
_REJECTED_QUOTE_CURRENCIES = {"/USDC", "/USDT", "/BUSD", "/DAI", "/TUSD", "USDC", "USDT"}

def _is_bad_quote_currency(symbol: str) -> bool:
    s = symbol.upper()
    return any(s.endswith(q) for q in _REJECTED_QUOTE_CURRENCIES)

def _is_breakout_scanner_payload(p: Dict[str, Any]) -> bool:
    return (
        p.get("signal_source") == "breakout_scanner"
        or p.get("strategy_name") == "breakout_scanner"
        or p.get("source") == "breakout_scanner"
    )

REQUIRED_FIELDS = [
    "symbol", "asset_class", "direction",
    "entry_price", "current_price",
    "move_pct", "volume_spike",
    "confidence", "escalation", "timestamp",
]

EXECUTION_BROKERS = {"kraken", "coinbase", "alpaca", "ibkr"}
BROKER_ALIASES = {
    "krakenpro": "kraken",
    "coinbasepro": "coinbase",
    "coinbase_advanced": "coinbase",
    "interactivebrokers": "ibkr",
    "interactive_brokers": "ibkr",
    "ib": "ibkr",
    "ibkr": "ibkr",
    "alpaca_markets": "alpaca",
}


class BreakoutReceiver:
    # Class-level slot counter — shared across all threads, prevents burst race.
    # When 5 FundingScanner signals arrive simultaneously, each grabs a slot
    # BEFORE any is committed to the DB, so _check_concurrent_breakouts using
    # DB-only counts would allow all 5 through.  This counter reserves in-flight
    # slots atomically; it is decremented after the trade completes or fails.
    _slot_lock        = threading.Lock()
    _slots_used       = 0    # breakout positions currently open OR being processed
    _slots_reserved   = set()  # symbols whose slot is currently held (thread-safe via _slot_lock)

    def __init__(self):
        self._executor: Optional[TradeExecutor] = None
        self._scanner_ref = None
        self._pending_lock  = threading.Lock()
        self._pending_symbols: set = set()  # symbols mid-processing (race guard)

    def set_executor(self, executor: TradeExecutor):
        self._executor = executor

    def set_scanner(self, scanner):
        self._scanner_ref = scanner

    def _is_receiver_enabled(self, payload: Dict[str, Any]) -> bool:
        signal_source = payload.get("signal_source", "breakout_scanner")
        return is_scanner_enabled(signal_source)

    # ──────────────────────────────────────────────────────────────────────
    # Public entry
    # ──────────────────────────────────────────────────────────────────────

    def receive_signal(self, payload: Dict[str, Any],
                       min_escalation: Optional[int] = None) -> Dict[str, Any]:
        # Each API request owns its payload copy. Checklist scratch state must
        # never live on the shared receiver instance where concurrent requests
        # can overwrite one another.
        payload        = dict(payload)
        sym            = payload.get("symbol", "?")
        direction      = payload.get("direction", "?")
        esc            = payload.get("escalation", 0)
        ts_in          = payload.get("timestamp", "")
        signal_age_sec = self._signal_age(ts_in)
        signal_source  = payload.get("signal_source", "breakout_scanner")

        event_id = payload.get("event_id")
        if not event_id or not str(event_id).strip():
            reason = "event_id is required for durable delivery"
            logger.warning(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "missing_event_id",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }
        event_id = str(event_id).strip()

        try:
            payload_hash = hash_breakout_payload(payload)
        except ValueError as e:
            reason = f"Payload rejected before hashing: {e}"
            logger.warning(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "invalid_payload",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }

        client_order_id = derive_client_order_id(event_id)

        # ── Durable atomic claim — MUST happen before any checklist/policy
        # execution (including the disabled-scanner and duplicate-symbol
        # checks below), so every rejection reason becomes part of the
        # replayable stored response for this event_id.
        claim = db.claim_breakout_event(
            event_id, payload_hash, sym, str(direction), signal_source,
            client_order_id,
        )

        if claim["status"] == "conflict":
            reason = (
                f"event_id {event_id} was already claimed with a different "
                "payload — refusing to process as a new or replayed event"
            )
            logger.warning(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "event_conflict",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }

        if claim["status"] == "replay_in_progress":
            reason = (
                f"event_id {event_id} is still {claim['state']} from a "
                "prior delivery attempt — failing closed, not resubmitting"
            )
            logger.warning(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "event_in_progress",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }

        if claim["status"] == "replay_terminal":
            logger.info(
                f"[BREAKOUT RECV] {sym} event_id={event_id} replay of "
                f"terminal state {claim['state']} — returning stored response"
            )
            stored = claim.get("response_json")
            if stored:
                try:
                    return json.loads(stored)
                except Exception:
                    logger.error(
                        f"[BREAKOUT RECV] event_id={event_id}: stored "
                        "response_json could not be parsed — returning a "
                        "minimal safe replay marker instead of reprocessing"
                    )
            return {
                "accepted":           claim["state"] == "ACCEPTED",
                "execution_eligible": False,
                "failure_class":      None if claim["state"] == "ACCEPTED" else "checklist_rejected",
                "reason":             f"Replay of terminal event ({claim['state']})",
                "trade_id":           claim.get("trade_id"),
                "checklist":          {},
            }

        # claim["status"] == "claimed" — brand new event_id, proceed.

        if not self._is_receiver_enabled(payload):
            reason = f"{signal_source} disabled by bot_state"
            logger.warning(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            result = {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "breakout_disabled",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }
            self._finalize_event(event_id, result, None)
            return result

        if not escalation_meets_minimum(esc, min_escalation):
            reason = f"Escalation {esc} below minimum {min_escalation}"
            logger.info(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            result = {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "escalation_below_minimum",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }
            self._finalize_event(event_id, result, None)
            return result

        # ── Duplicate-signal race guard ──────────────────────────────────────
        # Prevents two signals for the same symbol arriving within the same
        # second from both passing _check_no_open_position before the first
        # trade is committed to the DB. This is a fast in-process check —
        # the durable claim above is what actually makes cross-process /
        # cross-restart submission safe.
        with self._pending_lock:
            if sym in self._pending_symbols:
                reason = f"Duplicate signal rejected — {sym} already being processed"
                logger.warning(f"[BREAKOUT RECV] {reason}")
                result = {
                    "accepted": False,
                    "execution_eligible": False,
                    "failure_class": "duplicate_signal",
                    "reason": reason,
                    "trade_id": None,
                    "checklist": {},
                }
                self._finalize_event(event_id, result, None)
                return result
            self._pending_symbols.add(sym)
        try:
            result = self._receive_signal_inner(
                payload, sym, direction, esc, ts_in, signal_age_sec,
                event_id, client_order_id,
            )
            disposition = result.pop("_broker_disposition", None)
            # Log rejected breakout/gap signals to scanner_alerts (opened trades
            # are already logged inside _inject_signal; only log rejections here)
            if not result.get("accepted"):
                if signal_source in ("breakout_scanner", "gap_scanner"):
                    try:
                        from data.database import db as _db
                        _db.log_scanner_alert({
                            "alert_type":  "gap" if signal_source == "gap_scanner" else "breakout",
                            "symbol":      sym,
                            "asset_class": payload.get("asset_class", ""),
                            "direction":   direction,
                            "status":      "rejected",
                            "vol_spike":   float(payload.get("volume_spike", 0) or 0),
                            "score":       float(payload.get("confidence", 0) or 0),
                            "broker":      payload.get("broker", ""),
                            "source":      signal_source,
                            "reason":      result.get("reason", "")[:200],
                            "gap_pct":     payload.get("gap_pct"),
                            "gap_type":    payload.get("gap_type"),
                            "metadata":    {"move_pct": payload.get("move_pct"),
                                            "escalation": payload.get("escalation")},
                        })
                    except Exception as _e:
                        logger.debug("[BREAKOUT RECV] rejected signal DB log failed: %s", _e)
            self._finalize_event(event_id, result, disposition)
            return result
        except Exception:
            # Broker call may or may not have happened before this exception —
            # never assume no exposure. Leave the event in whatever state the
            # DB has (CLAIMED or SUBMITTING); it will be picked up by
            # reconciliation / fail closed on any replay, never silently lost.
            try:
                db.finish_breakout_event(
                    event_id, "SUBMISSION_UNKNOWN",
                    last_error="Unhandled exception during signal processing",
                )
            except Exception:
                logger.exception(
                    f"[BREAKOUT RECV] event_id={event_id}: failed to persist "
                    "SUBMISSION_UNKNOWN after unhandled exception"
                )
            raise
        finally:
            with self._pending_lock:
                self._pending_symbols.discard(sym)
            # Release the slot only if this signal reserved one (i.e., passed the
            # concurrent check).  Signals that failed before reaching that check
            # never took a slot and must NOT decrement.
            with BreakoutReceiver._slot_lock:
                if sym in BreakoutReceiver._slots_reserved:
                    BreakoutReceiver._slots_reserved.discard(sym)
                    BreakoutReceiver._slots_used = max(0, BreakoutReceiver._slots_used - 1)

    def _finalize_event(self, event_id: str, result: Dict[str, Any],
                        disposition: Optional[str]) -> None:
        """
        Persist the terminal (or SUBMISSION_UNKNOWN) state and, for terminal
        states, the exact response body future replays of this event_id must
        return. Never called for claim["status"] in
        ("conflict", "replay_in_progress", "replay_terminal") — those never
        reach a fresh claim in the first place.
        """
        try:
            if disposition == "submission_unknown":
                db.finish_breakout_event(
                    event_id, "SUBMISSION_UNKNOWN",
                    last_error=result.get("reason"),
                )
                return

            resp_json = json.dumps(result)
            if disposition == "accepted" or (result.get("accepted") and result.get("trade_id")):
                db.finish_breakout_event(
                    event_id, "ACCEPTED", response_json=resp_json,
                    broker_order_id=result.get("broker_order_id"),
                    trade_id=result.get("trade_id"),
                )
            else:
                # Any provably-no-exposure terminal outcome — rejected before
                # submission, or rejected/zero-fill after a broker call that
                # definitively proved no exposure was created.
                db.finish_breakout_event(
                    event_id, "PRE_SUBMISSION_REJECTED", response_json=resp_json,
                    last_error=result.get("reason"),
                )
        except Exception:
            logger.exception(
                f"[BREAKOUT RECV] event_id={event_id}: failed to persist "
                "terminal event state — treat as SUBMISSION_UNKNOWN until "
                "manually reconciled"
            )

    def _receive_signal_inner(
        self,
        payload: Dict[str, Any],
        sym: str,
        direction: str,
        esc: int,
        ts_in: str,
        signal_age_sec: float,
        event_id: str,
        client_order_id: str,
    ) -> Dict[str, Any]:

        broker_hint   = self._normalize_broker_name(payload.get("broker", ""))
        source_broker = self._normalize_broker_name(
            payload.get("source_broker", broker_hint or "")
        )

        if sym.upper() in BREAKOUT_SYMBOL_BLACKLIST:
            reason = f"{sym} in breakout symbol blacklist"
            logger.info(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "checklist_rejected",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }

        if _is_bad_quote_currency(sym):
            reason = f"{sym} has non-USD quote currency — unpriceable by Kraken feed"
            logger.warning(f"[BREAKOUT RECV] {sym} rejected — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "bad_quote_currency",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }

        # ── move_pct overflow guard ───────────────────────────────────────────
        # Funding scanner uses funding_rate * 100 as move_pct.  If Kraken returns
        # a non-normalised rate (e.g. 1.47 billion %) the value floods the log and
        # confuses checklist comparisons.  Clamp to 500% — anything higher is
        # a data error, not a real market move.
        _raw_move = payload.get("move_pct", 0) or 0
        if abs(float(_raw_move)) > 500.0:
            logger.warning(
                f"[MOVE OVERFLOW] {sym}: move_pct={_raw_move} clamped to 500 "
                f"— check price/rate data (entry={payload.get('entry_price')}, "
                f"current={payload.get('current_price')})"
            )
            payload["move_pct"] = 500.0

        self._normalize_volume_fields(payload)

        logger.info(
            f"[BREAKOUT RECV] {sym} {str(direction).upper()} "
            f"esc={esc} move={payload.get('move_pct', 0):+.2f}% "
            f"age={signal_age_sec:.0f}s vol={payload.get('volume_spike', 0):.2f}x "
            f"vol_src={payload.get('volume_source') or 'unknown'} "
            f"broker={broker_hint or 'none'} source_broker={source_broker or 'none'} "
            f"stop={payload.get('structural_stop_price', 'none')} "
            f"bars_since={payload.get('bars_since_breakout', '?')}"
        )

        missing = [f for f in REQUIRED_FIELDS if payload.get(f) is None]
        if missing:
            reason = f"Missing required fields: {', '.join(missing)}"
            logger.warning(f"[BREAKOUT RECV] INVALID PAYLOAD {sym} — {reason}")
            return {
                "accepted": False,
                "execution_eligible": False,
                "failure_class": "invalid_payload",
                "reason": reason,
                "trade_id": None,
                "checklist": {},
            }

        hard_results, soft_results = self._run_checklist(payload, signal_age_sec)

        hard_passed = all(
            r.status in (ChecklistResult.PASS, ChecklistResult.SKIP)
            for r in hard_results
        )
        hard_skips  = sum(1 for r in hard_results if r.status == ChecklistResult.SKIP)
        soft_passes = sum(1 for r in soft_results if r.status == ChecklistResult.PASS)
        soft_skips  = sum(1 for r in soft_results if r.status == ChecklistResult.SKIP)

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

            drift = payload.pop("_drift_state", {})
            if drift:
                flip_result = self._try_direction_flip(
                    payload,
                    drift["live_price"],
                    drift["drift_pct"],
                    signal_age_sec,
                    event_id,
                    client_order_id,
                )
                if flip_result is not None:
                    return flip_result

            reason = f"Hard check failed: {failed.reason}"
            logger.info(f"[BREAKOUT RECV] CHECKLIST REJECTED {sym} — {reason}")
            return {
                "accepted": False,
                "execution_eligible": True,
                "failure_class": "checklist_rejected",
                "reason": reason,
                "trade_id": None,
                "checklist": checklist_summary,
            }

        logger.info(
            f"[BREAKOUT RECV] CHECKLIST PASSED {sym} — "
            f"soft: {soft_passes} pass / {soft_skips} skip (advisory only)"
        )
        return self._inject_signal(payload, checklist_summary, event_id, client_order_id)

    # ──────────────────────────────────────────────────────────────────────
    # Checklist
    # ──────────────────────────────────────────────────────────────────────

    def _run_checklist(
        self, p: Dict, signal_age_sec: float
    ) -> Tuple[List[ChecklistResult], List[ChecklistResult]]:
        hard = [
            self._check_freshness(p, signal_age_sec),
            self._check_no_open_position(p),
            self._check_daily_symbol_limit(p),
            self._check_not_in_cooldown(p),
            self._check_trading_not_halted(),
            self._check_concurrent_breakouts(p),
            self._check_min_price(p),
            self._check_price_still_moving(p),
            self._check_volume_elevated(p),
            self._check_no_wick_rejection(p),
            self._check_not_gap_trap(p),
            self._check_not_pump_and_dump(p),
            self._check_momentum_phase(p),
            self._check_structural_stop(p),
        ]
        soft = [
            self._check_rsi_confirms(p),
            self._check_trend_alignment(p),
            self._check_market_context(p),
            # Trend confirmation is advisory only — breakout scanner catches EARLY moves
            # before all 4 indicators confirm. Moving this to soft logs the opinion
            # without blocking entries that pass all other hard checks.
            self._check_trend_confirmation(p),
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
        with BreakoutReceiver._slot_lock:
            if sym in BreakoutReceiver._slots_reserved:
                return ChecklistResult.fail(f"Already have in-flight signal for {sym}")
        return ChecklistResult.ok(f"No existing position on {sym}")

    def _check_daily_symbol_limit(self, p: Dict) -> ChecklistResult:
        MAX_CONSECUTIVE_LOSSES = 4  # block symbol after this many losses in a row; resets on any win
        sym = p["symbol"]
        # Funding scanner uses a completely different edge (funding rate extremes).
        # Breakout_scanner losses on the same symbol are irrelevant — don't cross-pollute.
        if p.get("signal_source") == "funding_scanner":
            return ChecklistResult.skip(
                "Daily symbol loss limit N/A for funding_scanner (different edge)"
            )
        try:
            today = date.today().isoformat()
            trades = sorted(
                [
                    t for t in (db.get_trades_for_date(today) or [])
                    if t.get("symbol") == sym
                    and t.get("strategy_name") == "breakout_scanner"
                    and t.get("status") == "closed"
                ],
                key=lambda t: t.get("exit_time") or "",
            )
            # Count consecutive losses from the most recent trade backwards
            consecutive = 0
            for t in reversed(trades):
                if (t.get("pnl") or 0) > 0:
                    break  # win resets the streak
                consecutive += 1
            if consecutive >= MAX_CONSECUTIVE_LOSSES:
                return ChecklistResult.fail(
                    f"{sym} has {consecutive} consecutive losses today via breakout_scanner "
                    f"— blocked until a win resets the counter (max={MAX_CONSECUTIVE_LOSSES})"
                )
        except Exception as e:
            logger.debug(f"[DAILY LIMIT] Could not check daily trade count: {e}")
        return ChecklistResult.ok("Daily symbol limit OK")

    def _check_not_in_cooldown(self, p: Dict) -> ChecklistResult:
        sym  = p["symbol"]
        last = getattr(risk_manager, "_last_closed", {}).get(sym)
        if last:
            elapsed  = time.time() - last.get("time", 0)
            # FIXED (Opus audit 2026-05-29): was INVERTED — locked winning symbols
            # out for 30min, losers only 10min. A breakout winner is the fast-mover
            # we want to re-enter. Align to risk_manager policy (win=2min, loss=10min).
            cooldown = 120 if last.get("won") else 600   # win=2min, loss=10min
            if elapsed < cooldown:
                esc = int(p.get("escalation") or 0)
                if last.get("won") and p.get("bypass_win_cooldown"):
                    p["bypass_win_cooldown"] = True
                    return ChecklistResult.ok(
                        f"{sym} won {int(elapsed)}s ago — breakout re-entry bypass"
                    )
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
        ref_price = float(p.get("current_price") or p.get("entry_price", 0))
        direction = p.get("direction", "long")

        if asset == "crypto":
            source_broker = self._normalize_broker_name(
                p.get("source_broker", "")
            )
            broker_hint = self._normalize_broker_name(p.get("broker", ""))
            if source_broker and source_broker not in EXECUTION_BROKERS:
                return ChecklistResult.fail(
                    f"{sym} source venue {source_broker} is not execution-capable; "
                    f"cannot verify identity for {broker_hint or 'crypto broker'}"
                )

        if not self._scanner_ref:
            return ChecklistResult.fail(
                "Price re-verify impossible — scanner not wired to receiver"
            )
        if ref_price <= 0:
            return ChecklistResult.fail("current_price/entry_price is zero or missing")

        try:
            current = self._fetch_live_price_from_scanner(p)

            if not current:
                return ChecklistResult.skip(
                    f"Could not fetch live price for {sym} — skipping price drift check"
                )

            drift_pct = ((current - ref_price) / ref_price) * 100

            if direction == "long" and drift_pct < -PRICE_DRIFT_MAX_PCT:
                p["_drift_state"] = {
                    "live_price": current, "drift_pct": drift_pct,
                }
                return ChecklistResult.fail(
                    f"{sym} reversed {drift_pct:.2f}% from signal price "
                    f"(limit -{PRICE_DRIFT_MAX_PCT}%)"
                )
            if direction == "short" and drift_pct > PRICE_DRIFT_MAX_PCT:
                p["_drift_state"] = {
                    "live_price": current, "drift_pct": drift_pct,
                }
                return ChecklistResult.fail(
                    f"{sym} reversed +{drift_pct:.2f}% from signal price "
                    f"(limit +{PRICE_DRIFT_MAX_PCT}%)"
                )

            return ChecklistResult.ok(f"{sym} still moving (drift={drift_pct:+.2f}%)")
        except Exception as e:
            return ChecklistResult.fail(f"Price re-verify failed")

 
    def _check_concurrent_breakouts(self, p: Dict) -> ChecklistResult:
        """Limit simultaneous open breakout_scanner positions to MAX_CONCURRENT_BREAKOUTS.

        Uses a class-level slot counter (not just DB count) to handle bursts where
        5 signals arrive simultaneously before any are committed to the DB.
        Slots are reserved here (by adding sym to _slots_reserved) and released in
        receive_signal's finally block.  Only signals that pass this check hold a slot.
        """
        sym = p.get("symbol", "?")
        with BreakoutReceiver._slot_lock:
            # True sync: DB is ground truth for committed open trades.
            # in_flight = symbols currently being processed (reserved slot, not yet in DB).
            # Set _slots_used = db_count + in_flight so the counter goes DOWN when trades
            # close via SL/TP/manual/script — the old max() only ever drove it upward,
            # causing "10/30 used" when only 5 trades were actually open.
            open_trades = db.get_open_trades() or []
            db_count = len([t for t in open_trades
                            if t.get("strategy_name") == "breakout_scanner"])
            in_flight = len(BreakoutReceiver._slots_reserved)   # processing but not yet in DB
            BreakoutReceiver._slots_used = db_count + in_flight
            current = BreakoutReceiver._slots_used
            # Crypto gets a tighter concurrent cap than stocks
            is_crypto = "/" in sym or "crypto" in str(p.get("asset_class", "")).lower()
            cap = MAX_CONCURRENT_CRYPTO if is_crypto else MAX_CONCURRENT_BREAKOUTS
            if current >= cap:
                return ChecklistResult.fail(
                    f"Already {current} breakout_scanner position(s) in-flight/open "
                    f"(max={cap} for {'crypto' if is_crypto else 'stock'}) — "
                    f"wait for one to close before adding more"
                )
            # Reserve a slot — this is the atomic claim that prevents burst races.
            BreakoutReceiver._slots_used += 1
            BreakoutReceiver._slots_reserved.add(sym)

        return ChecklistResult.ok(
            f"Concurrent breakouts: {current}/{cap} (slot reserved)"
        )

    def _check_min_price(self, p: Dict) -> ChecklistResult:
        asset = str(p.get("asset_class", "")).lower()
        price = float(p.get("current_price") or p.get("entry_price") or 0)
        if "crypto" in asset and price > 0 and price < MIN_PRICE_CRYPTO:
            return ChecklistResult.fail(
                f"Price ${price:.6f} below MIN_PRICE_CRYPTO ${MIN_PRICE_CRYPTO} — micro-cap rejected"
            )
        return ChecklistResult.ok(f"Price ${price:.6f} passes min price check")

    def _check_volume_elevated(self, p: Dict) -> ChecklistResult:
        vol = float(p.get("volume_spike", 0))
        if vol <= 0 or vol == 1.0:
            # FundingScanner: edge is funding rate extremes, not breakout momentum
            if p.get("signal_source") == "funding_scanner":
                return ChecklistResult.skip(
                    f"Volume spike is {vol:.2f}x (funding scanner — volume N/A, rate-based signal)"
                )
            # GapScanner gap_fill: deliberately fades low-volume moves — skip volume check
            if p.get("signal_source") == "gap_scanner" and p.get("gap_type") == "gap_fill":
                return ChecklistResult.skip(
                    f"Volume spike {vol:.2f}x (gap fill — fading low-volume reversal, volume check N/A)"
                )
            cur_vol = p.get("current_volume") or p.get("bar_volume")
            avg_vol = p.get("avg_volume")
            source  = p.get("volume_source") or "unknown"
            return ChecklistResult.fail(
                f"No volume baseline available ({vol:.2f}x, source={source}, "
                f"current_volume={cur_vol}, avg_volume={avg_vol}) — cannot confirm breakout volume. "
                f"Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation."
            )
        if vol < VOLUME_SPIKE_MIN:
            # Gap fills trade on fading volume by design — don't require breakout-level vol
            if p.get("signal_source") == "gap_scanner" and p.get("gap_type") == "gap_fill":
                return ChecklistResult.skip(
                    f"Volume spike {vol:.2f}x (gap fill — low volume expected on reversal)"
                )
            esc = int(p.get("escalation") or 0)
            move = abs(float(p.get("move_pct") or 0))
            if _is_breakout_scanner_payload(p) and (esc >= 2 or move >= 5.0):
                return ChecklistResult.skip(
                    f"Volume spike {vol:.2f}x below {VOLUME_SPIKE_MIN}x, "
                    f"but breakout is already escalated/moving — advisory only"
                )
            return ChecklistResult.fail(
                f"Volume spike {vol:.2f}x below minimum {VOLUME_SPIKE_MIN}x"
            )
        return ChecklistResult.ok(f"Volume elevated {vol:.2f}x")

    def _normalize_volume_fields(self, p: Dict) -> None:
        """Recover equivalent volume ratio fields before checklist evaluation."""
        try:
            vol = float(p.get("volume_spike") or 0)
        except (TypeError, ValueError):
            vol = 0.0

        if vol > 0:
            return

        for key in ("vol_mult",):
            try:
                candidate = float(p.get(key) or 0)
            except (TypeError, ValueError):
                candidate = 0.0
            if candidate > 0:
                p["volume_spike"] = candidate
                p["volume_source"] = p.get("volume_source") or key
                logger.info(
                    "[BREAKOUT RECV] %s volume_spike recovered from %s=%.3fx",
                    p.get("symbol", "?"), key, candidate
                )
                return

        try:
            cur = float((p.get("current_volume") or p.get("bar_volume") or 0))
            avg = float(p.get("avg_volume") or 0)
        except (TypeError, ValueError):
            cur = avg = 0.0

        if cur > 0 and avg > 0:
            p["volume_spike"] = cur / avg
            p["volume_source"] = p.get("volume_source") or "current_volume/avg_volume"
            logger.info(
                "[BREAKOUT RECV] %s volume_spike recovered from current/avg volume %.3fx",
                p.get("symbol", "?"), p["volume_spike"]
            )

    def _check_no_wick_rejection(self, p: Dict) -> ChecklistResult:
        o, h, l, c = (
            p.get("candle_open"),
            p.get("candle_high"),
            p.get("candle_low"),
            p.get("candle_close"),
        )

        if not all(v is not None for v in [o, h, l, c]):
            return ChecklistResult.skip(
                "Wick check skipped — OHLC not in payload"
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

    def _check_not_pump_and_dump(self, p: Dict) -> ChecklistResult:
        """Reject signals that look like coordinated pump & dump activity.

        Two tells that organic breakouts on liquid tokens almost never show:
          1. Volume spike way above normal — legitimate breakouts on mid/large-cap
             crypto run 3–8x volume. 15x+ is consistent with wash-trading or a
             small group ramping a thin-float token.
          2. Crypto move already > 18% — by the time the scanner fires, the pump is
             likely at peak. Real breakout entries are 2–8% off base, not 18%+.
             (Stocks use the existing GAP_TRAP_MAX_PCT = 30% which is fine for
             pre-market gaps; this tighter crypto cap targets intraday pumps.)
        """
        asset  = str(p.get("asset_class", "")).lower()
        vol    = float(p.get("volume_spike", 0) or 0)
        move   = abs(float(p.get("move_pct", 0) or 0))

        if vol > 0 and vol != 1.0 and vol > PUMP_VOLUME_SPIKE_MAX:
            return ChecklistResult.fail(
                f"Volume spike {vol:.1f}x exceeds PUMP_VOLUME_SPIKE_MAX {PUMP_VOLUME_SPIKE_MAX}x "
                f"— possible wash-trade or thin-float pump"
            )

        if "crypto" in asset and move > PUMP_MOVE_MAX_CRYPTO:
            return ChecklistResult.fail(
                f"Crypto move {move:.1f}% exceeds PUMP_MOVE_MAX_CRYPTO {PUMP_MOVE_MAX_CRYPTO}% "
                f"— likely at pump peak, not breakout entry"
            )

        return ChecklistResult.ok(
            f"P&D check passed — vol={vol:.1f}x move={move:.1f}%"
        )

    def _check_momentum_phase(self, p: Dict) -> ChecklistResult:
        direction   = p.get("direction", "long")
        bars_since  = p.get("bars_since_breakout")
        dist_pct    = p.get("distance_from_breakout_pct")
        rsi         = p.get("rsi")

        # MAX_BARS_SINCE reverted: 2 was too tight, scanner was silent — 3 bars = 15m on 5m.
        # Sourced from core.breakout_decision so this and breakout_sender.py's
        # stale-breakout guard can never drift apart on the same threshold.
        MAX_DIST_FROM_LVL = 6.0  # reverted: 2.0% killed nearly all signals — 6.0% is the proven working cap
        RSI_EXHAUST_LONG  = 78
        RSI_EXHAUST_SHORT = 22

        if bars_since is not None:
            bars_since = int(bars_since)
            if is_breakout_stale(bars_since):
                return ChecklistResult.fail(
                    f"Move is {bars_since} bars old — too late to enter "
                    f"(max {MAX_BREAKOUT_AGE_BARS} bars from breakout level)"
                )
        else:
            # bars_since missing from payload — rely on candle direction check below
            symbol_dbg = p.get("symbol", "?")
            logger.debug(
                f"[MOMENTUM] {symbol_dbg}: bars_since_breakout not in payload "
                f"— staleness check skipped, candle trend check is backstop"
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
            esc = int(p.get("escalation") or 0)
            move = abs(float(p.get("move_pct") or 0))
            breakout_runaway = _is_breakout_scanner_payload(p) and (esc >= 2 or move >= 5.0)
            if direction == "long" and rsi_f >= RSI_EXHAUST_LONG:
                if breakout_runaway:
                    return ChecklistResult.skip(
                        f"RSI {rsi_f:.1f} overbought, but escalated breakout can stay "
                        "parabolic — advisory only"
                    )
                return ChecklistResult.fail(
                    f"RSI {rsi_f:.1f} overbought — parabolic up likely exhausted "
                    f"(long rejected, threshold={RSI_EXHAUST_LONG})"
                )
            if direction == "short" and rsi_f <= RSI_EXHAUST_SHORT:
                if breakout_runaway:
                    return ChecklistResult.skip(
                        f"RSI {rsi_f:.1f} oversold, but escalated breakdown can continue "
                        "parabolic — advisory only"
                    )
                return ChecklistResult.fail(
                    f"RSI {rsi_f:.1f} oversold — parabolic down likely exhausted "
                    f"(short rejected, threshold={RSI_EXHAUST_SHORT})"
                )

        # ── Recent candle trend check ─────────────────────────────────────────
        # Even if bars_since is within limit, the last 2-3 candles may already
        # be moving against the signal direction (move peaked, now reversing).
        # Reject if 2 of the last 3 closed candles are against our direction.
        symbol = p.get("symbol", "")
        tf     = p.get("timeframe", "5m") or "5m"
        if symbol:
            try:
                from core.candle_manager import candle_manager
                df = candle_manager.get(symbol, tf, limit=5)
                if df is not None and len(df) >= 3:
                    recent        = df.tail(3)
                    bearish_count = int((recent["close"] < recent["open"]).sum())
                    bullish_count = int((recent["close"] >= recent["open"]).sum())
                    if direction == "long" and bearish_count >= 2:
                        return ChecklistResult.fail(
                            f"Trend reversed — {bearish_count}/3 recent candles bearish "
                            f"on LONG signal ({symbol}/{tf})"
                        )
                    if direction == "short" and bullish_count >= 2:
                        return ChecklistResult.fail(
                            f"Trend reversed — {bullish_count}/3 recent candles bullish "
                            f"on SHORT signal ({symbol}/{tf})"
                        )
            except Exception:
                pass   # candle_manager unavailable — skip check, don't block signal

        return ChecklistResult.ok(
            f"Momentum phase OK: bars_since={bars_since} dist={dist_pct}% rsi={rsi}"
        )

    def _check_trend_confirmation(self, p: Dict) -> ChecklistResult:
        """
        Confirms trend health using 4 technical indicators before entry.
        Requires 3-of-4 to pass — same criteria used for manual entry decisions:
          1. EMA 9 > EMA 20 and spread widening  (trend direction + strength)
          2. RSI rising                           (momentum building)
          3. MACD line > signal AND histogram > 0 (bullish momentum confirmed)
          4. ADX >= 25                            (trend is strong, not choppy)

        For SHORT direction all conditions are mirrored.
        Skipped silently if candle data is unavailable.
        """
        symbol    = p.get("symbol", "")
        direction = p.get("direction", "long")
        tf        = p.get("timeframe", "5m") or "5m"
        MIN_PASS  = 3   # require 3-of-4 (adjust to 4 if too many bad entries slip through)

        if not symbol:
            return ChecklistResult.ok("No symbol — trend confirmation skipped")

        try:
            import pandas as pd
            from core.candle_manager import candle_manager
            df = candle_manager.get(symbol, tf, limit=60)
            if df is None or len(df) < 30:
                return ChecklistResult.ok(
                    f"Insufficient bars ({len(df) if df is not None else 0}) — skipped"
                )
        except Exception as _e:
            return ChecklistResult.ok(f"Candle fetch failed — trend confirmation skipped ({_e})")

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        # ── 1. EMA 9 / EMA 20 alignment + spread widening ────────────────
        ema9       = close.ewm(span=9,  adjust=False).mean()
        ema20      = close.ewm(span=20, adjust=False).mean()
        spread_now = float(ema9.iloc[-1] - ema20.iloc[-1])
        spread_prv = float(ema9.iloc[-2] - ema20.iloc[-2])
        if direction == "long":
            c_ema = spread_now > 0 and spread_now > spread_prv   # above & widening
        else:
            c_ema = spread_now < 0 and spread_now < spread_prv   # below & widening down

        # ── 2. RSI 14 rising / falling ───────────────────────────────────
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))
        rsi_now = float(rsi.iloc[-1])
        rsi_prv = float(rsi.iloc[-2])
        c_rsi = (rsi_now > rsi_prv) if direction == "long" else (rsi_now < rsi_prv)

        # ── 3. MACD (12/26/9) line > signal AND histogram aligned ────────
        macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        macd_sig  = macd_line.ewm(span=9, adjust=False).mean()
        hist_val  = float(macd_line.iloc[-1] - macd_sig.iloc[-1])
        if direction == "long":
            c_macd = float(macd_line.iloc[-1]) > float(macd_sig.iloc[-1]) and hist_val > 0
        else:
            c_macd = float(macd_line.iloc[-1]) < float(macd_sig.iloc[-1]) and hist_val < 0

        # ── 4. ADX 14 >= 25 (trend strength, direction-neutral) ──────────
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)
        prev_high = high.shift(1)
        prev_low  = low.shift(1)
        raw_dm_p  = high - prev_high
        raw_dm_m  = prev_low - low
        dm_plus   = raw_dm_p.where((raw_dm_p > raw_dm_m) & (raw_dm_p > 0), 0.0)
        dm_minus  = raw_dm_m.where((raw_dm_m > raw_dm_p) & (raw_dm_m > 0), 0.0)
        alpha     = 1 / 14
        atr_s     = tr.ewm(alpha=alpha, adjust=False).mean()
        di_plus   = 100 * dm_plus.ewm(alpha=alpha, adjust=False).mean()  / atr_s.replace(0, 1e-9)
        di_minus  = 100 * dm_minus.ewm(alpha=alpha, adjust=False).mean() / atr_s.replace(0, 1e-9)
        di_sum    = (di_plus + di_minus).replace(0, 1e-9)
        adx_val   = float((100 * (di_plus - di_minus).abs() / di_sum).ewm(alpha=alpha, adjust=False).mean().iloc[-1])
        c_adx     = adx_val >= 25

        # ── ADX hard block: ≤ 20 = no trend, refuse entry ────────────────
        # ADX < 20 = flat/choppy market, breakout is likely exhausted.
        # 20-25 = weak trend (advisory warn but allow), ≥ 25 = confirmed trend.
        if adx_val <= 20:
            logger.warning(
                f"[ADX BLOCK] {symbol} {direction}: ADX={adx_val:.1f} ≤ 20 — "
                f"no trend, hard block (late/exhausted breakout)"
            )
            return ChecklistResult.fail(
                f"ADX {adx_val:.1f} ≤ 20 — no trend (hard block)"
            )

        # ── Verdict ───────────────────────────────────────────────────────
        checks  = [c_ema, c_rsi, c_macd, c_adx]
        passed  = sum(checks)
        details = (
            f"EMA={'✓' if c_ema else '✗'}  "
            f"RSI={'✓' if c_rsi else '✗'}({rsi_now:.1f})  "
            f"MACD={'✓' if c_macd else '✗'}(hist={hist_val:+.5f})  "
            f"ADX={'✓' if c_adx else '✗'}({adx_val:.1f})"
        )

        decision = "APPROVE" if passed >= MIN_PASS else "BLOCK"

        # ── Log every result to ai_signal_reviews for post-trade analysis ─
        # reviewer="trend_confirm" — query this in db_panel to see how often
        # the check would have blocked a signal and whether those blocks were right.
        # trade_id is unknown at checklist time; joins can use symbol + timestamp proximity.
        try:
            from data.database import db as _db
            from datetime import datetime as _dt
            _db.record_ai_signal_review({
                "timestamp":          _dt.now().isoformat(),
                "trade_id":           None,   # unknown pre-execution; link manually if needed
                "symbol":             symbol,
                "asset_class":        p.get("asset_class", "crypto"),
                "direction":          direction,
                "strategy_name":      p.get("signal_source", "breakout_scanner"),
                "signal_score":       float(p.get("confidence", 0)),
                "reviewer":           "trend_confirm",
                "mode":               "advisory",
                "decision":           decision,
                "confidence":         passed,            # 0-4 indicators that passed
                "reasoning":          details,
                "suggested_size_pct": None,
                "warnings":           [f"failed: {n}" for n, ok in
                                       zip(["EMA","RSI","MACD","ADX"], checks) if not ok],
                "elapsed_ms":         0,
            })
        except Exception as _log_err:
            logger.debug(f"[TREND CONFIRM] DB log failed for {symbol}: {_log_err}")

        # Advisory-only — logs to ai_signal_reviews for analysis but never blocks.
        # Gate was too restrictive in live testing (2026-06-07); re-enable as hard
        # block by changing ChecklistResult.ok → fail in the branch below once
        # enough log data confirms the thresholds are correctly calibrated.
        if passed < MIN_PASS:
            logger.warning(
                f"[TREND WARN] {symbol} {direction}: {passed}/{len(checks)} — {details}"
            )
        return ChecklistResult.ok(
            f"Trend advisory {passed}/{len(checks)} — {details}"
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
            if _is_breakout_scanner_payload(p):
                p["structural_stop_price"] = None
                return ChecklistResult.skip(
                    f"Structural stop {stop:.4f} >= price {price:.4f}; "
                    "falling back to breakout percent stop"
                )
            return ChecklistResult.fail(
                f"Stop {stop:.4f} >= price {price:.4f} — already broken for long"
            )
        if direction == "short" and stop <= price:
            if _is_breakout_scanner_payload(p):
                p["structural_stop_price"] = None
                return ChecklistResult.skip(
                    f"Structural stop {stop:.4f} <= price {price:.4f}; "
                    "falling back to breakout percent stop"
                )
            return ChecklistResult.fail(
                f"Stop {stop:.4f} <= price {price:.4f} — already broken for short"
            )

        max_dist = STOP_MAX_DISTANCE_CRYPTO if asset == "crypto" else STOP_MAX_DISTANCE_STOCK
        dist_pct = abs(price - stop) / price * 100
        if dist_pct > max_dist:
            if _is_breakout_scanner_payload(p):
                p["structural_stop_price"] = None
                return ChecklistResult.skip(
                    f"Structural stop too far ({dist_pct:.2f}% > max {max_dist}%); "
                    "falling back to breakout percent stop"
                )
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

    # ──────────────────────────────────────────────────────────────────────
    # Direction flip
    # ──────────────────────────────────────────────────────────────────────

    def _try_direction_flip(
        self,
        payload: Dict[str, Any],
        live_price: float,
        drift_pct: float,
        signal_age_sec: float,
        event_id: str,
        client_order_id: str,
    ) -> Optional[Dict[str, Any]]:
        sym      = payload.get("symbol", "?")
        orig_dir = payload.get("direction", "long")
        flipped  = "short" if orig_dir == "long" else "long"

        # Evaluate 3 flip criteria (require 2/3)
        criteria_met = 0

        vol = _optional_finite_float(payload.get("volume_spike"), 0.0)
        c1  = vol >= VOLUME_SPIKE_MIN
        if c1:
            criteria_met += 1

        momentum = _optional_finite_float(payload.get("momentum_score"), 0.0)
        c2 = (momentum < 0) if orig_dir == "long" else (momentum > 0)
        if c2:
            criteria_met += 1

        candle_open = _optional_finite_float(payload.get("candle_open"), None)
        if candle_open is not None:
            co = candle_open
            c3 = (live_price < co) if orig_dir == "long" else (live_price > co)
        else:
            c3 = False
        if c3:
            criteria_met += 1

        logger.info(
            f"[BREAKOUT RECV] FLIP EVAL {sym}: {orig_dir.upper()}->{flipped.upper()} "
            f"criteria={criteria_met}/3  "
            f"vol={vol:.2f}x>={VOLUME_SPIKE_MIN}:{c1}  "
            f"momentum={momentum:.3f} reversed:{c2}  "
            f"candle_open={f'{candle_open:.4f}' if candle_open is not None else 'N/A'}  "
            f"live={live_price:.4f} body_confirms:{c3}"
        )

        if criteria_met < 2:
            logger.info(
                f"[BREAKOUT RECV] FLIP DENIED {sym}: only {criteria_met}/3 criteria met — "
                f"rejecting as original {orig_dir.upper()}"
            )
            return None

        # Build the flipped payload
        p = dict(payload)
        p["direction"]     = flipped
        p["current_price"] = live_price
        p["entry_price"]   = live_price
        p["move_pct"]      = round(drift_pct, 4)

        dist = payload.get("distance_from_breakout_pct")
        if dist is not None:
            dist_value = _optional_finite_float(dist, None)
            if dist_value is not None:
                p["distance_from_breakout_pct"] = -dist_value
            else:
                p["distance_from_breakout_pct"] = None

        p["structural_stop_price"] = None  # old side's stop is now on the wrong side

        logger.info(
            f"[BREAKOUT RECV] DIRECTION FLIP {sym}: {orig_dir.upper()}->{flipped.upper()} "
            f"(drift={drift_pct:+.2f}%, criteria_met={criteria_met}/3) "
            f"entry={live_price:.4f} move_pct={p['move_pct']:+.4f}%"
        )

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
            "direction_flip": f"{orig_dir}->{flipped}",
        }

        if not hard_passed:
            failed = next(r for r in hard_results if r.status == ChecklistResult.FAIL)
            logger.info(
                f"[BREAKOUT RECV] FLIP CHECKLIST REJECTED {sym} — {failed.reason}"
            )
            return {
                "accepted":           False,
                "execution_eligible": True,
                "failure_class":      "flip_checklist_rejected",
                "reason":             f"Direction flip failed checklist: {failed.reason}",
                "trade_id":           None,
                "checklist":          checklist_summary,
            }

        logger.info(
            f"[BREAKOUT RECV] FLIP CHECKLIST PASSED {sym} — "
            f"injecting {flipped.upper()} "
            f"soft: {soft_passes} pass / {soft_skips} skip (advisory only)"
        )
        return self._inject_signal(p, checklist_summary, event_id, client_order_id)

    # ──────────────────────────────────────────────────────────────────────
    # Injection
    # ──────────────────────────────────────────────────────────────────────

    def _inject_signal(self, p: Dict, checklist: dict, event_id: str,
                       client_order_id: str) -> Dict:
        if not self._executor:
            logger.error("[BREAKOUT RECV] Executor not set")
            return {
                "accepted": False,
                "failure_class": "injection_exception",
                "reason": "Executor not configured",
                "trade_id": None,
                "checklist": checklist,
                "_broker_disposition": "pre_submission_rejected",
            }

        try:
            from scanners.market_scanner import Signal

            asset_class   = p.get("asset_class", "crypto")
            direction     = p.get("direction", "long")
            sym           = p["symbol"]
            price         = float(p.get("current_price") or p.get("entry_price"))
            esc           = p.get("escalation", 0)

            broker_hint   = self._normalize_broker_name(p.get("broker", "kraken"))
            source_broker = self._normalize_broker_name(
                p.get("source_broker", broker_hint)
            )

            if broker_hint not in EXECUTION_BROKERS:
                broker_hint = "kraken" if asset_class == "crypto" else "alpaca"

            move_pct_abs = abs(float(p.get("move_pct", 0)))
            has_structural_stop = p.get("structural_stop_price") is not None
            signal_source = p.get("signal_source", "breakout_scanner")
            strategy_name = p.get("strategy_name") or signal_source or "breakout_scanner"
            original_direction = direction
            contrarian_flag_map = getattr(
                config,
                "BREAKOUT_CONTRARIAN_SOURCE_FLAGS",
                {
                    "breakout_scanner": "BREAKOUT_SCANNER_CONTRARIAN",
                    "funding_scanner":  "FUNDING_SCANNER_CONTRARIAN",
                    "gap_scanner":      "GAP_SCANNER_CONTRARIAN",
                },
            )
            contrarian_flag = contrarian_flag_map.get(signal_source)
            source_contrarian_enabled = (
                bool(getattr(config, contrarian_flag, False))
                if contrarian_flag
                else signal_source in set(getattr(
                    config,
                    "BREAKOUT_CONTRARIAN_SOURCES",
                    ("breakout_scanner",),
                ))
            )
            # Direction is intentionally manual right now: edit config.py flags
            # to flip a scanner. Do not let live performance stats auto-switch.
            flip_policy = "static_config"
            flip_decision = "CONTRARIAN" if source_contrarian_enabled else "FORWARD"
            logger.warning(
                "[BREAKOUT DIRECTION DECISION] %s source=%s policy=%s decision=%s "
                "incoming=%s adaptive_reason=%s",
                sym,
                signal_source,
                flip_policy,
                flip_decision,
                str(original_direction).upper(),
                "manual_config_flag",
            )

            if (
                getattr(config, "BREAKOUT_CONTRARIAN_MODE", False)
                and source_contrarian_enabled
                and not checklist.get("direction_flip")
                and str(direction).lower() in ("long", "short")
            ):
                direction = "short" if str(direction).lower() == "long" else "long"
                p["direction"] = direction
                p["contrarian_original_direction"] = original_direction
                p["contrarian_mode"] = True
                p["structural_stop_price"] = None
                has_structural_stop = False
                logger.warning(
                    f"[BREAKOUT CONTRARIAN] {sym}: flipping "
                    f"{str(original_direction).upper()}->{direction.upper()} "
                    f"after checklist pass source={signal_source}"
                )

            if asset_class == "crypto" and not has_structural_stop:
                custom_stop = round(min(max(move_pct_abs * 0.30, 2.0), 4.5), 2)
                logger.info(
                    f"[BREAKOUT RECV] {sym} custom_stop_loss_pct={custom_stop}% "
                    f"(move={move_pct_abs:.1f}%, no structural stop)"
                )
            else:
                custom_stop = None

            # TP ladder: start at 9% so true speed-runners have room again while
            # the ratchet trail remains the primary protective exit.
            # Bump TP as price proves the move — the escalation level from the
            # scanner tells us how far price has already traveled from the breakout:
            #   esc 1 → 2% move  → TP  9%  (base — old runner ceiling restored)
            #   esc 2 → 5% move  → TP 15%  (real momentum — let it breathe)
            #   esc 3 → 10% move → TP 21%  (strong trend — widen further)
            #   esc 4 → 15% move → TP 27%  (monster move — max ceiling)
            # Ratchet trail (original-SL-dist below peak) is the real exit for
            # runners — the TP is just a hard ceiling in case ratchet misfires.
            _esc_tp_map = {0: 9.0, 1: 9.0, 2: 15.0, 3: 21.0, 4: 27.0}
            custom_tp = _esc_tp_map.get(int(esc), 27.0 if int(esc) >= 4 else 9.0)

            signal = Signal(
                symbol        = sym,
                asset_class   = asset_class,
                direction     = direction,
                score         = min(float(p.get("confidence", 0.7)) + 0.1, 1.0),
                current_price = price,
                reason        = (
                    f"{signal_source} esc={esc} "
                    f"move={p.get('move_pct', 0):+.1f}% "
                    f"vol={p.get('volume_spike', 0):.1f}x "
                    f"dir_mode={flip_decision.lower()}"
                ),
                indicators    = {
                    "strategy_name":              strategy_name,
                    "timeframe":                  "5m" if asset_class == "crypto" else "5Min",
                    "signal_source":              signal_source,
                    "preferred_broker":           broker_hint,
                    "source_broker":              source_broker,
                    "source_price":               p.get("source_price", p.get("current_price")),
                    "source_timestamp":           p.get("source_timestamp", p.get("timestamp")),
                    "sender_timestamp":           p.get("timestamp"),
                    "escalation":                 esc,
                    "move_pct":                   p.get("move_pct", 0),
                    "volume_spike":               p.get("volume_spike", 0),
                    "momentum_score":             p.get("momentum_score", 0),
                    "pattern":                    p.get("pattern", "breakout"),
                    "rsi":                        p.get("rsi"),
                    "sma200":                     p.get("sma200"),
                    "structural_stop_price":      p.get("structural_stop_price"),
                    "contrarian_mode":            p.get("contrarian_mode", False),
                    "original_direction":         p.get("contrarian_original_direction"),
                    "direction_decision":         flip_decision.lower(),
                    "direction_policy":           flip_policy,
                    "breakout_level":             p.get("breakout_level"),
                    "bars_since_breakout":        p.get("bars_since_breakout"),
                    "distance_from_breakout_pct": p.get("distance_from_breakout_pct"),
                    "custom_stop_loss_pct":       custom_stop,
                    "custom_take_profit_pct":     custom_tp,
                    "bypass_win_cooldown":        p.get("bypass_win_cooldown", False),
                    "event_id":                   event_id,
                    "client_order_id":            client_order_id,
                },
            )

            logger.info(
                f"[BREAKOUT RECV] INJECTING {sym} {direction.upper()} "
                f"@ ${price:.4f} | esc={esc} move={p.get('move_pct',0):+.2f}% "
                f"preferred_broker={broker_hint} source_broker={source_broker}"
            )

            # Commit CLAIMED -> SUBMITTING before any broker call, so a crash
            # or timeout after this point is visible as SUBMITTING/
            # SUBMISSION_UNKNOWN on restart rather than looking untouched.
            db.mark_breakout_event_submitting(event_id)

            disposition = {"outcome": "pre_submission_rejected"}
            trade_id = self._executor.execute_signal(signal, disposition_out=disposition)
            broker_outcome = disposition.get("outcome", "submission_unknown")

            if trade_id:
                logger.info(f"[BREAKOUT RECV] EXECUTED {sym} -> trade_id={trade_id}")
                # Log to scanner_alerts DB
                try:
                    from data.database import db as _db
                    signal_source = p.get("signal_source", "breakout_scanner")
                    if signal_source == "gap_scanner":
                        # Gap alert was already logged in gap_watchlist — just link trade
                        _db.link_alert_to_trade(sym, trade_id)
                    else:
                        # Log new breakout alert with trade_id
                        _db.log_scanner_alert({
                            "alert_type":  "breakout",
                            "symbol":      sym,
                            "asset_class": asset_class,
                            "direction":   direction,
                            "status":      "fired",
                            "trade_id":    trade_id,
                            "score":       float(p.get("confidence", 0.7)),
                            "vol_spike":   float(p.get("volume_spike", 0)),
                            "broker":      broker_hint,
                            "source":      signal_source,
                            "metadata": {
                                "move_pct":   p.get("move_pct"),
                                "escalation": p.get("escalation"),
                                "pattern":    p.get("pattern"),
                            },
                        })
                except Exception as _e:
                    logger.debug("[BREAKOUT RECV] scanner_alert DB log failed: %s", _e)
                return {
                    "accepted": True,
                    "execution_eligible": True,
                    "failure_class": None,
                    "reason": "Signal executed",
                    "trade_id": trade_id,
                    "checklist": checklist,
                    "_broker_disposition": "accepted",
                }

            # trade_id is falsy — this does NOT by itself prove no exposure
            # exists. Trust the executor's disposition classification
            # (default-then-narrowed inside execute_signal): only
            # "pre_submission_rejected"/"rejected_no_exposure" are safe to
            # report as a clean rejection; anything else (including the
            # "submission_unknown" default that survives an unrecognized
            # broker result) must fail closed as unresolved exposure.
            if broker_outcome in ("pre_submission_rejected", "rejected_no_exposure"):
                logger.warning(f"[BREAKOUT RECV] Executor rejected {sym} — no exposure")
                return {
                    "accepted": False,
                    "execution_eligible": True,
                    "failure_class": "checklist_rejected",
                    "reason": "Executor rejected (risk manager or broker)",
                    "trade_id": None,
                    "checklist": checklist,
                    "_broker_disposition": "pre_submission_rejected",
                }

            logger.error(
                f"[BREAKOUT RECV] {sym} broker outcome unknown "
                f"(disposition={broker_outcome}) — no trade_id returned but "
                "exposure cannot be ruled out; leaving event SUBMISSION_UNKNOWN"
            )
            return {
                "accepted": False,
                "execution_eligible": True,
                "failure_class": "submission_unknown",
                "reason": "Broker submission outcome unknown — reconciliation required",
                "trade_id": None,
                "checklist": checklist,
                "_broker_disposition": "submission_unknown",
            }

        except Exception as e:
            logger.error(
                f"[BREAKOUT RECV] Injection exception for {p.get('symbol')}: {e}",
                exc_info=True,
            )
            return {
                "accepted": False,
                "execution_eligible": True,
                "failure_class": "injection_exception",
                "reason": f"Injection failed",
                "trade_id": None,
                "checklist": checklist,
                "_broker_disposition": "submission_unknown",
            }

    # ──────────────────────────────────────────────────────────────────────
    # Scanner price fallback helpers
    # ──────────────────────────────────────────────────────────────────────

    def _normalize_broker_name(self, raw: str) -> str:
        name = str(raw or "").strip().lower()
        return BROKER_ALIASES.get(name, name)

    def _fetch_live_price_from_scanner(self, p: Dict) -> Optional[float]:
        """
        Re-verify live price without crossing crypto venue identities.

        Order:
          1. stocks: scanner.get_current_price(), then stock history fallback
          2. crypto: exact source exchange, then exact execution exchange
          3. crypto without venue metadata: generic scanner hook as legacy fallback

        A generic crypto lookup is intentionally not used when the payload names a
        source/execution venue.  The main scanner checks CoinGecko first, where a
        ticker can identify a different asset from the Kraken/Coinbase instrument.
        """
        scanner = self._scanner_ref
        if not scanner:
            return None

        sym          = p["symbol"]
        asset_class  = p.get("asset_class", "crypto")
        broker_hint  = self._normalize_broker_name(p.get("broker", ""))
        source_broker= self._normalize_broker_name(p.get("source_broker", ""))

        # Stocks have a single instrument identity in the scanner abstraction.
        if asset_class == "stock":
            get_price = getattr(scanner, "get_current_price", None)
            if callable(get_price):
                try:
                    px = get_price(sym, asset_class)
                    if px:
                        return float(px)
                except Exception:
                    pass
            try:
                sf = getattr(scanner, "stock_fetcher", None)
                if sf and hasattr(sf, "get_historical_data"):
                    bars = sf.get_historical_data(sym)
                    if bars:
                        last = getattr(bars[-1], "price", None)
                        if last:
                            return float(last)
            except Exception:
                pass
            return None

        # Crypto must be checked on the venue that produced the signal.  The
        # receiver is wired to MarketScanner in production (crypto_scanner), but
        # tests/legacy wiring may provide BreakoutScanner (crypto_fetcher).
        try:
            cf = (
                getattr(scanner, "crypto_scanner", None)
                or getattr(scanner, "crypto_fetcher", None)
            )
            if not cf:
                cf = scanner

            exchanges = getattr(cf, "exchanges", {}) or {}
            primary   = getattr(cf, "exchange", None)
            primary_name = self._normalize_broker_name(getattr(cf, "exchange_name", ""))

            candidate_names = []
            for name in (source_broker, broker_hint):
                if name and name not in candidate_names:
                    candidate_names.append(name)

            # Named exchanges first
            for name in candidate_names:
                exc = exchanges.get(name.upper())
                if not exc and primary and name == primary_name:
                    exc = primary
                if not exc:
                    continue
                try:
                    symbols = getattr(exc, "symbols", []) or []
                    if symbols and sym not in symbols:
                        continue
                    ticker = exc.fetch_ticker(sym)
                    live_price = live_ticker_reference(ticker)
                    if live_price is not None:
                        return live_price
                except Exception:
                    continue

            # A payload with venue metadata must never fall through to another
            # venue merely because the exact venue lookup failed.
            if candidate_names:
                return None

            # Legacy payload without venue metadata: use the primary exchange,
            # then the scanner's generic hook if necessary.
            if primary:
                try:
                    ticker = primary.fetch_ticker(sym)
                    live_price = live_ticker_reference(ticker)
                    if live_price is not None:
                        return live_price
                except Exception:
                    pass

            get_price = getattr(scanner, "get_current_price", None)
            if callable(get_price):
                try:
                    px = get_price(sym, asset_class)
                    if px:
                        return float(px)
                except Exception:
                    pass

        except Exception:
            pass

        return None

    # ──────────────────────────────────────────────────────────────────────
    # Timestamp helper
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _signal_age(timestamp_str: str) -> float:
        if not timestamp_str:
            return -1.0
        try:
            ts = datetime.fromisoformat(str(timestamp_str).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc) if ts.tzinfo else datetime.now()
            return (now - ts).total_seconds()
        except Exception:
            return -1.0


# Module singleton
breakout_receiver = BreakoutReceiver()
