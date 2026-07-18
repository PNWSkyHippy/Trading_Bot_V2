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
from typing import Any, Dict

# Receiver scratch / identity fields that must never affect the payload hash.
# event_id is the row's primary key already; _drift_state is per-request
# scratch state the receiver attaches during checklist processing and pops
# before this point, but is excluded here too as defense in depth.
_HASH_EXCLUDED_FIELDS = {"event_id", "_drift_state"}


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
