"""
=============================================================
  METRICS — Patch A telemetry
  reports/agent_pipeline/20260716-082429/final_unified_report.md

  Lightweight, dependency-free counters plus a rate-limited alert helper for
  fail-closed gate failures (the calendar authority and, in a later patch,
  the broker-position snapshot). This module does not change any fetch
  routing — it is instrumentation only, wired into the new Patch A components
  (core/candle_validation.py, core/stock_calendar_authority.py) so their
  behavior is observable rather than silently invisible when they correctly
  suppress an action out of uncertainty.

  Ron's implementation-time clarification #3: "Calendar-authority and
  broker-position-authority failures must emit prominent metrics and
  rate-limited alerts so fail-closed entry suppression cannot remain
  operationally invisible." A fail-closed suppression is the right safety
  behavior, but must not look identical to "the bot is idle because there was
  nothing to do."
=============================================================
"""

import logging
import threading
import time
from typing import Dict

import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_counters: Dict[str, int] = {}
_last_alert_epoch: Dict[str, int] = {}


def increment(name: str, n: int = 1) -> None:
    """Increment a named counter. Thread-safe."""
    with _lock:
        _counters[name] = _counters.get(name, 0) + n


def get_snapshot() -> Dict[str, int]:
    """Return a copy of all counters (for dashboards/tests)."""
    with _lock:
        return dict(_counters)


def reset() -> None:
    """Clear all counters and alert-cooldown state. Test use only."""
    with _lock:
        _counters.clear()
        _last_alert_epoch.clear()


def alert_gate_failure(category: str, reason: str, now_epoch: int = None) -> bool:
    """
    Report a fail-closed gate failure (e.g. calendar authority stale, broker
    position snapshot unavailable). Always increments a counter and logs at
    CRITICAL so the failure is never silent in the logs. Sends a dedicated
    "gate failure" alert (email/SMS via reporting.alerts.alert_manager —
    distinct from trading_halted(), see AlertManager.gate_failure()'s
    docstring for why) at most once per config.GATE_FAILURE_ALERT_COOLDOWN_SEC
    per category, so a persistent failure does not spam an alert every scan
    cycle.

    Cooldown/retry semantics: the cooldown timestamp is recorded only AFTER
    a successful delivery, never merely on attempting one. A failed send
    (e.g. an SMTP outage) does not consume the cooldown window — the very
    next call for that category will retry immediately rather than being
    silently suppressed for the full cooldown period despite no alert ever
    having actually reached anyone. (An earlier version of this function
    recorded the cooldown timestamp before attempting delivery, which meant
    a single failed send during, say, an email-credential outage would
    black out every subsequent alert for that category for the entire
    cooldown window — the operator would get zero notifications for up to
    config.GATE_FAILURE_ALERT_COOLDOWN_SEC even though delivery never once
    succeeded.)

    Returns True if an external alert was actually, successfully sent this
    call (useful for tests), False if it was suppressed by the cooldown, the
    delivery attempt failed, or alerts aren't configured.
    """
    now_epoch = now_epoch if now_epoch is not None else int(time.time())
    increment(f"gate_failure.{category}")
    logger.critical(f"[GATE FAILURE] {category}: {reason}")

    cooldown = getattr(config, "GATE_FAILURE_ALERT_COOLDOWN_SEC", 900)
    with _lock:
        last = _last_alert_epoch.get(category)
        if last is not None and (now_epoch - last) < cooldown:
            return False

    try:
        from reporting.alerts import alert_manager
        delivered = alert_manager.gate_failure(category, reason)
    except Exception as e:
        # gate_failure()/_send_now() are designed not to raise for a delivery
        # failure (they catch and log internally so other alert call sites
        # can remain fire-and-forget) — this except is a defensive backstop
        # for an unexpected coding error, not the expected way delivery
        # failures are detected. Treat it the same as a failed delivery.
        logger.warning(f"[GATE FAILURE] alert delivery raised unexpectedly for {category}: {e}")
        delivered = False

    if not delivered:
        return False

    # Only a successful delivery consumes the cooldown window.
    with _lock:
        _last_alert_epoch[category] = now_epoch
    return True
