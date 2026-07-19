"""
core/event_identity.py
=======================
Shared helpers for durable breakout-event identity: payload canonicalization
and hashing (for atomic claim/conflict detection), and deterministic
client-order-id derivation (for broker-native idempotency).

Kept in its own module (no dependency on breakout_receiver or trade_executor)
so both can import it without a circular import.
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Dict

# Receiver scratch / identity fields that must never affect the payload hash.
# event_id is the row's primary key already; _drift_state is per-request
# scratch state the receiver attaches during checklist processing and pops
# before this point, but is excluded here too as defense in depth.
_HASH_EXCLUDED_FIELDS = {"event_id", "_drift_state"}


def _identity_component(value: Any, field: str) -> str:
    """Return a stable, non-empty text component for producer identity."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"{field} datetime must be timezone-aware")
        value = value.astimezone(timezone.utc).isoformat()
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required for breakout event identity")
    return text


def derive_breakout_event_ids(
    producer: str,
    source_event_key: Any,
    symbol: str,
    direction: str,
    child_key: Any = None,
) -> tuple[str, str]:
    """
    Derive a stable semantic root ID and delivery/event ID.

    ``source_event_key`` is owned by the producer that first recognizes the
    event (for example the original signal timestamp, closed-bar timestamp,
    or persisted setup registration time).  Mutable enrichment, send time,
    price and retry count are deliberately excluded.

    Escalations are child events because their payloads change.  Reusing the
    root ID for changed payloads would correctly trip the receiver's conflict
    hash.  The child key makes each escalation distinct while every retry of
    that escalation derives the same ID.
    """
    components = (
        _identity_component(producer, "producer").lower(),
        _identity_component(symbol, "symbol").upper(),
        _identity_component(direction, "direction").lower(),
        _identity_component(source_event_key, "source_event_key"),
    )
    root_blob = "\x1f".join(components).encode("utf-8")
    root_id = "boevt-" + hashlib.sha256(root_blob).hexdigest()[:32]
    if child_key is None:
        return root_id, root_id
    child = _identity_component(child_key, "child_key")
    child_blob = f"{root_id}\x1f{child}".encode("utf-8")
    event_id = root_id + "-" + hashlib.sha256(child_blob).hexdigest()[:12]
    return root_id, event_id


def ensure_breakout_event_identity(
    payload: Dict[str, Any],
    *,
    producer: str | None = None,
    source_event_key: Any = None,
    child_key: Any = None,
) -> Dict[str, Any]:
    """Populate stable identity on a producer-owned payload copy.

    Existing non-blank IDs are preserved.  This function never invents a
    transport-time UUID.  Callers without a producer-owned semantic key fail
    closed instead of turning retries into new trades.
    """
    result = dict(payload)
    existing = str(result.get("event_id") or "").strip()
    if existing:
        result["event_id"] = existing
        root = str(result.get("root_event_id") or existing).strip()
        result["root_event_id"] = root
        return result

    producer_name = producer or result.get("signal_source")
    key = source_event_key
    if key is None:
        key = result.get("source_event_key")
    if key is None:
        key = result.get("source_timestamp")
    if key is None:
        key = result.get("timestamp")
    if child_key is None and result.get("escalation") is not None:
        child_key = f"escalation:{result['escalation']}"

    root_id, event_id = derive_breakout_event_ids(
        producer_name,
        key,
        result.get("symbol"),
        result.get("direction"),
        child_key,
    )
    result["source_event_key"] = _identity_component(key, "source_event_key")
    result["root_event_id"] = root_id
    result["event_id"] = event_id
    return result


def _validate_finite(value: Any, path: str) -> None:
    """Raise ValueError on any NaN/Infinity found anywhere in the payload."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Non-finite value at {path}: {value!r}")
    elif isinstance(value, dict):
        for k, v in value.items():
            _validate_finite(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _validate_finite(v, f"{path}[{i}]")


def canonicalize_breakout_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Immutable, hash-stable view of a breakout payload: excludes receiver
    scratch/identity fields and rejects non-finite numeric values anywhere
    in the structure (NaN/Infinity are never valid signal data and must
    never silently poison the conflict-detection hash).
    """
    canonical = {k: v for k, v in payload.items() if k not in _HASH_EXCLUDED_FIELDS}
    _validate_finite(canonical, "payload")
    return canonical


def hash_breakout_payload(payload: Dict[str, Any]) -> str:
    """Stable sha256 of the canonicalized payload. Same event_id + same
    hash => replay. Same event_id + different hash => permanent conflict."""
    canonical = canonicalize_breakout_payload(payload)
    blob = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), default=str,
        allow_nan=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def derive_client_order_id(event_id: str) -> str:
    """
    Deterministic client-order id derived from event_id. Stable across
    delivery attempts and process restarts. Used as the broker-native
    idempotency key for Alpaca (client_order_id) and IBKR (orderRef).
    """
    return "bo-" + hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:24]


def derive_kraken_userref(event_id: str) -> int:
    """
    Kraken's userref field is a 32-bit integer, not a string, so it cannot
    reuse derive_client_order_id() directly. Deterministically derived from
    the same event_id so the two identities stay linkable for a given event.
    Masked to stay within a positive signed 32-bit range.
    """
    digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF
