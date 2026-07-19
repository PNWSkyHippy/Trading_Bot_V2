"""
breakout_sender.py  (hardened v2)
==================================
Sends validated BreakoutScanner signals to the Trading Bot V2 API server.

Changes from v1:
  - Payload now includes candle OHLC (required by hardened receiver wick check)
  - Tries to extract OHLC from signal.history if not passed as candle_data
  - volume_spike now uses signal.volume_spike (real ratio vs average)
  - Unicode arrows replaced with ASCII for Windows cp1252 compatibility
  - Structured response logging (failure_class aware)
  - TTL-aware: sends UTC ISO timestamp so receiver can compute signal age

Config keys (scanner_config.json):
    bot_api_url         str   e.g. "http://localhost:8181"
    bot_api_key         str   must match BOT_API_KEY in bot's config.py
    bot_min_escalation  int   minimum escalation to send (default: 1)
    bot_enabled         bool  master switch (default: true)
    bot_sender_queue_size int bounded pending-send capacity (default: 256)

PATCH NOTES — 2026-07-18, Step 8 (Reconciled Safe Patch Sequence, scoped —
see core/breakout_decision.py's own patch notes for the full rationale,
what was deliberately left untouched, and the back-out steps). Summary of
what changed in THIS file:
  - should_send()'s stale-breakout guard (`bars_since > MAX_BREAKOUT_AGE_BARS`)
    and its escalation-minimum check (`escalation < self._min_esc`) now call
    shared functions (`is_breakout_stale`, `escalation_meets_minimum`) from
    core.breakout_decision instead of comparing against a locally-defined
    `MAX_BREAKOUT_AGE_BARS` class constant — same value (3 bars), same
    semantics, single source of truth shared with
    core/breakout_receiver.py's _check_momentum_phase() and receive_signal().
  - The liquidity filter (MIN_USD_VOLUME_PER_CANDLE) and the `escalation > 4`
    upper bound are unchanged and remain sender-local — they have no
    confirmed duplicate elsewhere.
"""

import logging
import json
import copy
import hashlib
import math
import os
import queue
from pathlib import Path
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.breakout_decision import (
    is_breakout_stale,
    escalation_meets_minimum,
    MAX_BREAKOUT_AGE_BARS,
)
from core.event_identity import ensure_breakout_event_identity

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_BOT_URL        = "http://localhost:8181"
DEFAULT_MIN_ESCALATION = 1
SEND_TIMEOUT_SEC       = 5
DEFAULT_QUEUE_SIZE     = 256
DEFAULT_RETRY_ATTEMPTS = 3
BASE_DIR               = Path(__file__).resolve().parent
SCANNER_CONFIG_PATH    = BASE_DIR / "scanner_config.json"
DEFAULT_OUTBOX_DIR     = BASE_DIR / "data" / "breakout_sender_outbox"


class BreakoutSender:
    """
    Sends breakout signals to the Trading Bot API.
    Non-blocking — validated sends enter one bounded background worker.
    """

    def __init__(self, config: dict):
        self._url      = config.get("bot_api_url",        DEFAULT_BOT_URL).rstrip("/")
        self._key      = config.get("bot_api_key",        "")
        try:
            self._min_esc = int(config.get("bot_min_escalation", DEFAULT_MIN_ESCALATION))
        except (TypeError, ValueError, OverflowError):
            self._min_esc = DEFAULT_MIN_ESCALATION
        self._enabled  = config.get("bot_enabled",        True)
        self._session  = requests.Session() if REQUESTS_AVAILABLE else None
        self._last_sent: Dict[tuple, float] = {}
        self._dedup_sec = 30
        self._last_disabled_log = 0.0
        self._state_lock = threading.RLock()
        try:
            retry_attempts = int(
                config.get("bot_sender_retry_attempts", DEFAULT_RETRY_ATTEMPTS)
            )
        except (TypeError, ValueError, OverflowError):
            retry_attempts = DEFAULT_RETRY_ATTEMPTS
        self._retry_attempts = max(1, min(retry_attempts, 5))
        try:
            queue_size = int(config.get("bot_sender_queue_size", DEFAULT_QUEUE_SIZE))
        except (TypeError, ValueError, OverflowError):
            queue_size = DEFAULT_QUEUE_SIZE
        self._queue = queue.Queue(maxsize=max(1, queue_size))
        configured_outbox = config.get("bot_sender_outbox_dir")
        self._outbox_dir = Path(configured_outbox) if configured_outbox else DEFAULT_OUTBOX_DIR
        self._stop_event = threading.Event()
        self._closed = False
        self._worker = None

        if self._session is not None:
            self._restore_pending_outbox()
            self._worker = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="breakout-sender-worker",
            )
            self._worker.start()

        if not REQUESTS_AVAILABLE:
            logger.warning("[SENDER] requests not installed — bot injection disabled")
        elif not self._key:
            logger.warning("[SENDER] bot_api_key not set — bot injection disabled")
        elif self._enabled:
            logger.info(
                f"[SENDER] Bot injection enabled -> {self._url} "
                f"(min escalation: {self._min_esc})"
            )

    @property
    def ready(self) -> bool:
        return (
            REQUESTS_AVAILABLE
            and bool(self._key)
            and self._live_enabled()
        )

    def _truthy_enabled(self, value, default: bool = True) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {
            "0", "false", "no", "off", "disabled"
        }

    def _live_enabled(self) -> bool:
        """
        Live kill switch. The standalone scanner can keep running for alerts,
        but bot injection must stop immediately when either switch is off.
        """
        try:
            from core.scanner_controls import is_scanner_enabled
            if not is_scanner_enabled("breakout_scanner"):
                self._log_disabled_once("bot_state.breakout_scanner_enabled=False")
                return False
        except Exception as exc:
            self._log_disabled_once(
                f"DB kill-switch unavailable ({type(exc).__name__})"
            )
            return False

        try:
            if SCANNER_CONFIG_PATH.exists():
                with open(SCANNER_CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                enabled = self._truthy_enabled(
                    cfg.get("bot_enabled", self._enabled), default=self._enabled
                )
                if not enabled:
                    self._log_disabled_once("scanner_config bot_enabled=False")
                    return False
            elif not self._truthy_enabled(self._enabled):
                self._log_disabled_once("startup bot_enabled=False")
                return False
        except Exception as exc:
            self._log_disabled_once(
                f"config kill-switch unavailable ({type(exc).__name__})"
            )
            return False

        return True

    def _log_disabled_once(self, reason: str):
        with self._state_lock:
            now = time.time()
            if now - self._last_disabled_log > 60:
                logger.warning("[SENDER] Bot injection disabled by %s", reason)
                self._last_disabled_log = now

    # Minimum average USD volume per candle to accept a signal.
    # Filters out illiquid micro-caps where one seller can cliff-drop the price
    # with no liquidity to absorb the move (e.g. KULA, SUNDOG).
    # avg_volume (units) * price = USD volume per candle.
    # At 500 USD/candle minimum: a $0.01 token needs 50,000 units/candle average.
    MIN_USD_VOLUME_PER_CANDLE = 500.0

    def should_send(self, signal, escalation: int) -> bool:
        if not self.ready:
            return False
        try:
            escalation = int(escalation)
        except (TypeError, ValueError):
            return False
        if not escalation_meets_minimum(escalation, self._min_esc) or escalation > 4:
            return False

        # Liquidity filter — reject illiquid tokens where price can cliff-drop
        # with no warning due to an empty order book.
        cd = copy.deepcopy(getattr(signal, "enrichment", {}) or {})
        vol_info = self._resolve_volume_info(signal, cd)
        price = self._finite_float(
            getattr(signal, "current_price", None), minimum=0.0, strict_min=True
        )
        if price is None:
            price = self._finite_float(
                getattr(signal, "entry_price", None), minimum=0.0, strict_min=True
            )
        avg_vol = self._finite_float(vol_info.get("avg_volume"), minimum=0.0)
        if price is None or avg_vol is None:
            logger.warning(
                "[SENDER] REJECTED %s — trustworthy price/volume baseline unavailable",
                getattr(signal, "symbol", "?"),
            )
            return False
        usd_vol = avg_vol * price
        if usd_vol < self.MIN_USD_VOLUME_PER_CANDLE:
            logger.info(
                f"[SENDER] REJECTED {signal.symbol} — insufficient liquidity "
                f"(avg {usd_vol:.1f} USD/candle < {self.MIN_USD_VOLUME_PER_CANDLE} min)"
            )
            return False

        # Stale breakout guard — drop signals where the breakout started too long ago.
        # bars_since_breakout is incremented by EscalationTracker on every scan cycle.
        bars_since = getattr(signal, "bars_since_breakout", 0)
        if is_breakout_stale(bars_since):
            logger.info(
                f"[SENDER] {signal.symbol} breakout is {bars_since} bars old "
                f"(max {MAX_BREAKOUT_AGE_BARS}) — stale signal, dropping send"
            )
            return False

        return True

    def _resolve_direction(self, signal) -> Optional[str]:
        """
        Return only an explicit valid direction. Direction inference belongs to the
        scanner; the transport boundary must never silently turn ambiguity into a trade.
        """
        direction = str(getattr(signal, "direction", "") or "").strip().lower()
        return direction if direction in {"long", "short"} else None

    def send_signal(self, signal, escalation: int, candle_data: dict = None):
        """
        Non-blocking send in background thread.

        signal:      BreakoutSignal from BreakoutScanner
        escalation:  0-4
        candle_data: optional fallback dict — used only if signal.enrichment absent
        """
        if not self.should_send(signal, escalation):
            return

        direction = self._resolve_direction(signal)
        if not direction:
            logger.warning(
                f"[SENDER] {signal.symbol} missing/invalid explicit direction — "
                f"dropping send (scanner must set long or short)"
            )
            return

        try:
            payload = self._build_payload(signal, escalation, direction, candle_data)
        except Exception as exc:
            logger.warning(
                "[SENDER] %s payload build rejected (%s)",
                getattr(signal, "symbol", "?"), type(exc).__name__,
            )
            return
        self._reserve_and_enqueue(payload)

    def _build_payload(self, signal, escalation: int, direction: str,
                       candle_data: dict = None) -> dict:
        """
        Build the API payload.

        Data priority for candle / analytical fields:
          1. signal.enrichment  — scanner-built at signal creation (BREAKOUT 8A)
          2. candle_data arg    — explicit override (AlertSystem compatibility)
          3. signal.history     — legacy fallback, logged when used
          4. None               — field omitted; receiver will SKIP soft checks
        """
        # ── Resolve enrichment source ────────────────────────────────────────
        enrichment = getattr(signal, "enrichment", {}) or {}
        if enrichment:
            cd = enrichment
            src = "enrichment"
        elif candle_data:
            cd = candle_data
            src = "candle_data"
        else:
            cd = {}
            src = "none"
            # Legacy: try to pull OHLC from signal.history if it exists
            if hasattr(signal, "history") and signal.history:
                try:
                    last_bar = signal.history[-1]
                    cd = {
                        "open":  getattr(last_bar, "open_price", None),
                        "high":  getattr(last_bar, "high",       None),
                        "low":   getattr(last_bar, "low",        None),
                        "close": getattr(last_bar, "price",      None),
                    }
                    src = "history_fallback"
                    logger.debug(f"[SENDER] {signal.symbol} using legacy history fallback")
                except Exception:
                    pass

        # ── Compact prep log ─────────────────────────────────────────────────
        has_ohlc   = all(cd.get(k) is not None for k in ("open", "high", "low", "close"))
        has_rsi    = cd.get("rsi") is not None
        has_market = cd.get("market_pct_change") is not None
        logger.info(
            f"[SENDER] PREP {signal.symbol} {direction} esc={escalation} "
            f"src={src} ohlc={'yes' if has_ohlc else 'no'} "
            f"rsi={'yes' if has_rsi else 'no'} "
            f"market={'yes' if has_market else 'no'}"
        )

        asset_value = getattr(getattr(signal, "asset_type", None), "value", None)
        asset_class = str(asset_value or "").strip().lower()
        source_broker = str(getattr(signal, "broker", "") or "").strip().lower()
        if source_broker in {"", "unknown"}:
            broker = ""
        elif asset_class == "stock":
            broker = source_broker if source_broker in {"alpaca", "ibkr"} else ""
        else:
            broker = (
                source_broker if source_broker in {"kraken", "coinbase"}
                else "kraken"
            )
        now_utc     = datetime.now(timezone.utc).isoformat()
        vol_info    = self._resolve_volume_info(signal, cd)

        sig_ts = getattr(signal, "timestamp", None)
        source_ts = self._aware_iso(sig_ts)

        payload = {
            # Identity
            "symbol":        signal.symbol,
            "broker":        broker,
            "source_broker": source_broker,
            "direction":     direction,
            "asset_class":   asset_class,
            "signal_source": "breakout_scanner",

            # Time — timestamp must remain send-time for receiver TTL; source_timestamp is audit only
            "timestamp":        now_utc,
            "source_timestamp": source_ts,

            # Price
            "entry_price":   signal.entry_price,
            "current_price": signal.current_price,
            "source_price":  signal.current_price,

            # Move context
            "move_pct":      signal.best_move_pct,
            "best_move_pct": signal.best_move_pct,
            "escalation":    escalation,

            # Quality
            "volume_spike":   vol_info["volume_spike"],
            "volume_source":  vol_info["volume_source"],
            "current_volume": vol_info["current_volume"],
            "bar_volume":     vol_info["current_volume"],
            "avg_volume":     vol_info["avg_volume"],
            "vol_mult":       vol_info["volume_spike"],
            "momentum_score": getattr(signal, "momentum_score", cd.get("momentum_score", 0.0)),
            "confidence":     getattr(signal, "confidence",     0.7),

            # Candle anatomy — from enrichment when available
            "candle_open":  cd.get("open"),
            "candle_high":  cd.get("high"),
            "candle_low":   cd.get("low"),
            "candle_close": cd.get("close"),

            # Analytical fields — from enrichment when available
            "rsi":                   cd.get("rsi"),
            "sma200":                cd.get("sma200"),
            "structural_stop_price": cd.get("structural_stop") or cd.get("structural_stop_price"),
            "market_pct_change":     cd.get("market_pct_change"),
            "pattern":               cd.get("pattern") or getattr(signal, "pattern_detected", None),

            # Breakout metadata (populated by scanner when available)
            "breakout_level":             getattr(signal, "breakout_level",             None),
            "bars_since_breakout":        getattr(signal, "bars_since_breakout",        None),
            "distance_from_breakout_pct": getattr(signal, "distance_from_breakout_pct", None),
        }
        # The signal timestamp is the immutable recognition time shared by
        # every escalation of this breakout.  Each escalation is a child
        # event because its payload changes; retries reuse the same child ID.
        return ensure_breakout_event_identity(
            payload,
            producer="breakout_scanner",
            source_event_key=source_ts,
            child_key=f"escalation:{escalation}",
        )

    def _to_float(self, value) -> Optional[float]:
        return self._finite_float(value)

    @staticmethod
    def _finite_float(value, minimum=None, maximum=None, strict_min=False) -> Optional[float]:
        try:
            if value is None or isinstance(value, bool):
                return None
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if minimum is not None:
            if strict_min and number <= minimum:
                return None
            if not strict_min and number < minimum:
                return None
        if maximum is not None and number > maximum:
            return None
        return number

    @staticmethod
    def _aware_iso(value) -> Optional[str]:
        if not isinstance(value, datetime) or value.tzinfo is None:
            return None
        try:
            return value.astimezone(timezone.utc).isoformat()
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def _first_present(*values):
        for value in values:
            if value is not None:
                return value
        return None

    def _resolve_volume_info(self, signal, cd: dict) -> dict:
        """Return the best non-zero volume ratio plus raw volume diagnostics."""
        cd = cd or {}
        hist = list(getattr(signal, "volume_history", []) or [])

        current_volume = self._first_present(
            self._finite_float(cd.get("current_volume"), minimum=0.0),
            self._finite_float(cd.get("bar_volume"), minimum=0.0),
            self._finite_float(cd.get("volume"), minimum=0.0),
            self._finite_float(hist[-1], minimum=0.0) if hist else None,
        )

        avg_volume = self._first_present(
            self._finite_float(getattr(signal, "avg_volume", None), minimum=0.0),
            self._finite_float(cd.get("avg_volume"), minimum=0.0),
        )
        if avg_volume is None and len(hist) > 1:
            prior = [
                parsed for value in hist[:-1]
                if (parsed := self._finite_float(value, minimum=0.0)) is not None
            ]
            if prior:
                avg_volume = sum(prior) / len(prior)

        candidates = [
            ("signal.volume_spike", self._to_float(getattr(signal, "volume_spike", None))),
            ("enrichment.volume_spike", self._to_float(cd.get("volume_spike"))),
            ("enrichment.vol_mult", self._to_float(cd.get("vol_mult"))),
        ]
        if current_volume is not None and avg_volume is not None and avg_volume > 0:
            candidates.append(("volume_history", current_volume / avg_volume))

        for source, value in candidates:
            if value is not None and value > 0:
                return {
                    "volume_spike": value,
                    "volume_source": source,
                    "current_volume": current_volume,
                    "avg_volume": avg_volume,
                }

        return {
            "volume_spike": 0.0,
            "volume_source": "missing",
            "current_volume": current_volume,
            "avg_volume": avg_volume,
        }

    @staticmethod
    def _parse_aware_timestamp(value) -> Optional[datetime]:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return None
        return parsed if parsed.tzinfo is not None else None

    def _validate_payload(self, payload: dict) -> Optional[dict]:
        """Return a detached normalized payload, or None when unsafe to send."""
        try:
            normalized = copy.deepcopy(payload)
        except Exception:
            return None
        if not isinstance(normalized, dict):
            return None

        symbol = str(normalized.get("symbol") or "").strip().upper()
        direction = str(normalized.get("direction") or "").strip().lower()
        asset_class = str(normalized.get("asset_class") or "").strip().lower()
        source = str(normalized.get("signal_source") or "").strip().lower()
        event_id = str(normalized.get("event_id") or "").strip()
        root_event_id = str(normalized.get("root_event_id") or "").strip()
        broker = str(normalized.get("broker") or "").strip().lower()
        aliases = {
            "krakenpro": "kraken", "coinbasepro": "coinbase",
            "coinbase_advanced": "coinbase", "alpaca_markets": "alpaca",
            "interactivebrokers": "ibkr", "ib": "ibkr",
        }
        broker = aliases.get(broker, broker)

        if not event_id or not root_event_id:
            return None
        if not symbol or direction not in {"long", "short"}:
            return None
        if asset_class not in {"stock", "crypto"} or not source:
            return None
        if asset_class == "stock" and broker not in {"alpaca", "ibkr"}:
            return None
        if asset_class == "crypto" and broker not in {"kraken", "coinbase"}:
            return None

        try:
            escalation = int(normalized.get("escalation"))
        except (TypeError, ValueError, OverflowError):
            return None
        if escalation < 0 or escalation > 4:
            return None

        required_positive = ("entry_price", "current_price")
        for field in required_positive:
            value = self._finite_float(
                normalized.get(field), minimum=0.0, strict_min=True
            )
            if value is None:
                return None
            normalized[field] = value

        for field in ("move_pct", "volume_spike", "confidence"):
            if normalized.get(field) is None:
                return None

        numeric_ranges = {
            "source_price": (0.0, None, True),
            "move_pct": (None, None, False),
            "best_move_pct": (None, None, False),
            "volume_spike": (0.0, None, False),
            "current_volume": (0.0, None, False),
            "bar_volume": (0.0, None, False),
            "avg_volume": (0.0, None, False),
            "vol_mult": (0.0, None, False),
            "momentum_score": (None, None, False),
            "confidence": (0.0, 1.0, False),
            "candle_open": (0.0, None, True),
            "candle_high": (0.0, None, True),
            "candle_low": (0.0, None, True),
            "candle_close": (0.0, None, True),
            "rsi": (0.0, 100.0, False),
            "sma200": (0.0, None, True),
            "structural_stop_price": (0.0, None, True),
            "market_pct_change": (None, None, False),
            "breakout_level": (0.0, None, False),
            "distance_from_breakout_pct": (None, None, False),
        }
        for field, (minimum, maximum, strict_min) in numeric_ranges.items():
            if normalized.get(field) is None:
                continue
            value = self._finite_float(
                normalized[field], minimum=minimum,
                maximum=maximum, strict_min=strict_min,
            )
            if value is None:
                return None
            normalized[field] = value

        bars_since = normalized.get("bars_since_breakout")
        if bars_since is not None:
            try:
                bars_since = int(bars_since)
            except (TypeError, ValueError, OverflowError):
                return None
            if bars_since < 0:
                return None
            normalized["bars_since_breakout"] = bars_since

        if self._parse_aware_timestamp(normalized.get("timestamp")) is None:
            return None
        source_timestamp = normalized.get("source_timestamp")
        if source_timestamp is not None and self._parse_aware_timestamp(source_timestamp) is None:
            return None

        normalized.update({
            "symbol": symbol,
            "direction": direction,
            "asset_class": asset_class,
            "signal_source": source,
            "broker": broker,
            "source_broker": str(
                normalized.get("source_broker") or broker
            ).strip().lower(),
            "event_id": event_id,
            "root_event_id": root_event_id,
            "escalation": escalation,
        })
        return normalized

    def _dedup_key(self, payload: dict) -> tuple:
        return (payload["event_id"],)

    def _outbox_path(self, event_id: str) -> Path:
        digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
        return self._outbox_dir / f"{digest}.json"

    def _persist_pending(self, payload: dict) -> bool:
        """Atomically persist before queueing so restart recovery is safe."""
        try:
            self._outbox_dir.mkdir(parents=True, exist_ok=True)
            target = self._outbox_path(payload["event_id"])
            temporary = target.with_suffix(
                f".{threading.get_ident()}.tmp"
            )
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(target)
            return True
        except Exception as exc:
            logger.error(
                "[SENDER] OUTBOX WRITE FAILED %s event_id=%s (%s)",
                payload.get("symbol", "?"), payload.get("event_id"),
                type(exc).__name__,
            )
            return False

    def _remove_pending(self, event_id: str) -> None:
        try:
            self._outbox_path(event_id).unlink(missing_ok=True)
        except Exception as exc:
            logger.error(
                "[SENDER] OUTBOX CLEANUP FAILED event_id=%s (%s)",
                event_id, type(exc).__name__,
            )

    def _restore_pending_outbox(self) -> None:
        """Load durable, previously unconfirmed deliveries before worker start."""
        if not self._outbox_dir.exists():
            return
        restored = 0
        for path in sorted(self._outbox_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                normalized = self._validate_payload(payload)
                if normalized is None:
                    logger.error("[SENDER] invalid outbox record quarantined: %s", path)
                    path.rename(path.with_suffix(".invalid"))
                    continue
                self._queue.put_nowait(normalized)
                restored += 1
            except queue.Full:
                logger.warning(
                    "[SENDER] outbox restore paused at queue capacity=%s",
                    self._queue.maxsize,
                )
                break
            except Exception as exc:
                logger.error(
                    "[SENDER] outbox restore failed for %s (%s)",
                    path, type(exc).__name__,
                )
        if restored:
            logger.warning("[SENDER] restored %s pending durable delivery item(s)", restored)

    def _reserve_and_enqueue(self, payload: dict) -> bool:
        try:
            payload = ensure_breakout_event_identity(payload)
        except (TypeError, ValueError):
            logger.warning(
                "[SENDER] INVALID IDENTITY %s — producer event key unavailable",
                payload.get("symbol", "?") if isinstance(payload, dict) else "?",
            )
            return False
        normalized = self._validate_payload(payload)
        if normalized is None:
            logger.warning(
                "[SENDER] INVALID PAYLOAD %s — local validation rejected dispatch",
                payload.get("symbol", "?") if isinstance(payload, dict) else "?",
            )
            return False

        key = self._dedup_key(normalized)
        now = time.monotonic()
        with self._state_lock:
            if self._closed:
                return False
            cutoff = now - self._dedup_sec
            self._last_sent = {
                old_key: sent_at for old_key, sent_at in self._last_sent.items()
                if sent_at >= cutoff
            }
            if self._last_sent.get(key, 0.0) >= cutoff:
                # A duplicate reservation did not create a new event. Keep the
                # existing outbox record for the already-queued delivery.
                logger.debug("[SENDER] duplicate suppressed: %s", key)
                return False
            if not self._persist_pending(normalized):
                return False
            self._last_sent[key] = now
            try:
                self._queue.put_nowait(normalized)
            except queue.Full:
                self._last_sent.pop(key, None)
                logger.error(
                    "[SENDER] QUEUE FULL — %s not attempted (capacity=%s)",
                    normalized["symbol"], self._queue.maxsize,
                )
                return False
        return True

    def send_raw_payload(self, payload: dict) -> None:
        """
        Send a pre-built payload dict directly to the bot API.
        Used by gap scanner and other event sources that build their own payloads.
        Non-blocking -- fires in a background thread.
        """
        if not self.ready:
            return
        if not isinstance(payload, dict):
            return
        frozen = copy.deepcopy(payload)
        try:
            frozen = ensure_breakout_event_identity(frozen)
        except (TypeError, ValueError):
            logger.warning(
                "[SENDER] RAW REJECTED %s — stable producer identity unavailable",
                frozen.get("symbol", "?"),
            )
            return
        sym = frozen.get("symbol", "?")
        logger.info(
            f"[SENDER] RAW QUEUE {sym} source={frozen.get('signal_source','?')} "
            f"dir={frozen.get('direction','?')} conf={frozen.get('confidence','?')}"
        )
        self._reserve_and_enqueue(frozen)

    def _worker_loop(self):
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                payload = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self._send_once(payload)
            finally:
                self._queue.task_done()

    def _send_once(self, payload: dict):
        """Worker-owned POST with bounded retries of the same durable ID."""
        if not self.ready:
            logger.warning(
                "[SENDER] NOT ATTEMPTED %s — injection disabled before POST",
                payload.get("symbol", "?"),
            )
            return
        url     = f"{self._url}/api/breakout_signal"
        headers = {"X-Api-Key": self._key, "Content-Type": "application/json"}
        sym     = payload.get("symbol", "?")
        esc     = payload.get("escalation", 0)

        resp = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                resp = self._session.post(
                    url, json=payload, headers=headers, timeout=SEND_TIMEOUT_SEC,
                )
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                logger.warning(
                    "[SENDER] DELIVERY UNCONFIRMED %s esc=%s event_id=%s "
                    "attempt=%s/%s (%s)",
                    sym, esc, payload.get("event_id"), attempt,
                    self._retry_attempts, type(exc).__name__,
                )
                if attempt < self._retry_attempts:
                    time.sleep(min(0.25 * attempt, 0.75))
            except Exception as exc:
                logger.warning(
                    "[SENDER] SEND ERROR %s esc=%s (%s)", sym, esc,
                    type(exc).__name__,
                )
                return
        if resp is None:
            logger.error(
                "[SENDER] DELIVERY UNRESOLVED %s esc=%s event_id=%s",
                sym, esc, payload.get("event_id"),
            )
            return

        if resp.status_code != 200:
            logger.warning("[SENDER] HTTP %s for %s esc=%s", resp.status_code, sym, esc)
            if resp.status_code in {400, 409, 422}:
                # Payload/conflict failures are terminal for this exact
                # event. Keep 401/403 and other operational responses in the
                # outbox because fixing credentials/config can make them
                # deliverable without changing identity.
                self._remove_pending(payload["event_id"])
            return
        try:
            result = resp.json()
        except Exception:
            logger.error("[SENDER] INVALID RESPONSE %s esc=%s — non-JSON body", sym, esc)
            return
        if not isinstance(result, dict):
            logger.error("[SENDER] INVALID RESPONSE %s esc=%s — JSON is not an object", sym, esc)
            return


        # Every well-formed 200 receiver response is terminal and replayable,
        # whether policy accepted or rejected the event.
        self._remove_pending(payload["event_id"])

        fc = result.get("failure_class")
        if result.get("accepted"):
            logger.info(
                "[SENDER] ACCEPTED %s esc=%s trade_id=%s",
                sym, esc, result.get("trade_id"),
            )
        elif fc == "invalid_payload":
            logger.warning("[SENDER] INVALID PAYLOAD %s esc=%s", sym, esc)
        elif fc == "injection_exception":
            logger.error("[SENDER] INJECTION ERROR %s esc=%s", sym, esc)
        else:
            logger.info("[SENDER] REJECTED %s esc=%s class=%s", sym, esc, fc or "policy")

    def close(self, drain: bool = True, timeout: float = 5.0):
        """Stop accepting work, optionally drain queued sends, and close sockets."""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._stop_event.set()
            worker = self._worker
        if worker and worker is not threading.current_thread():
            worker.join(timeout=max(0.0, float(timeout)) if drain else 0.0)
        if worker and worker.is_alive():
            logger.warning(
                "[SENDER] shutdown timed out with %s queued delivery item(s)",
                self._queue.qsize(),
            )
        elif self._session is not None:
            self._session.close()
