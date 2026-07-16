"""
=============================================================
  CANDLE VALIDATION — Patch A data-authority contracts
  reports/agent_pipeline/20260716-082429/final_unified_report.md

  Defines:
    - ScanCutoff              one fixed "now" per scan generation
    - ClosedCandleSeries       persistent CLOSED-candle data (strategy analysis)
    - EntryQuoteSnapshot       scan-scoped entry-screening quote
    - HeldPositionPrice        broker-authoritative held-position price
    - SessionAuthority         protocol a calendar authority must implement
    - validate_closed_candles()  strict, fail-closed candle validator
    - validate_entry_quote()     strict, fail-closed quote validator

  Ron's safety invariant: "New entries must fail closed when candle age,
  timestamp parsing, quote freshness, or batch completeness is uncertain."
  Every function here returns None on uncertainty — it never returns a row,
  price, or series it cannot vouch for. This deliberately does NOT reuse
  scanners.market_scanner._strip_forming_bar()'s behavior of keeping a row
  unchanged when its timestamp fails to parse (fail-open) — that was reviewed
  and rejected during the audit (see the report's §5, "Claims tested and
  rejected").

  This module is pure (no I/O, no network, no SQLite) and is not yet wired
  into any live fetch/scan path — Patch A is contracts and tests only.
=============================================================
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Dict, Optional, Protocol

import pandas as pd

from core import metrics

logger = logging.getLogger(__name__)

REQUIRED_OHLC_COLUMNS = ("open", "high", "low", "close")

# Timeframe-string → bar duration in seconds. Deliberately self-contained
# rather than importing scanners.market_scanner._TF_SECONDS: core/ modules
# should not depend on scanners/ (the dependency runs the other way in this
# codebase), and this table already exists in more than one place historically
# (see the audit's F9 finding on CRYPTO_BLACKLIST duplication) — flagged here
# as a candidate for consolidation into one shared location in a later patch,
# not attempted in Patch A to keep this patch's diff focused on the contracts
# it specifically introduces.
_TF_SECONDS: Dict[str, int] = {
    "1m": 60, "1min": 60, "1minute": 60,
    "5m": 300, "5min": 300, "5minute": 300,
    "15m": 900, "15min": 900,
    "30m": 1800, "30min": 1800,
    "1h": 3600, "1hour": 3600, "60m": 3600, "60min": 3600,
    "2h": 7200, "2hour": 7200,
    "4h": 14400, "4hour": 14400,
    "1d": 86400, "1day": 86400, "daily": 86400,
}


def timeframe_seconds(timeframe: str) -> Optional[int]:
    """Bar duration in seconds for a recognized timeframe string, else None
    (an unrecognized timeframe is an uncertainty, not a guess — callers must
    treat None as "cannot validate", never silently default to some duration)."""
    if not timeframe:
        return None
    return _TF_SECONDS.get(timeframe.strip().lower().replace(" ", ""))


@dataclass(frozen=True)
class ScanCutoff:
    """
    One fixed "now" captured at the start of a scan generation and reused for
    every symbol evaluated in that scan — never re-derived per symbol.

    Rationale (B5): a scan that happens to straddle a bar-close boundary
    partway through must not validate early symbols against the old bar and
    later symbols against the new bar while treating the whole pass as one
    scan generation.
    """
    epoch: int

    @classmethod
    def now(cls) -> "ScanCutoff":
        """Capture the current instant as a new scan's fixed cutoff.
        Uses time.time() (UTC epoch, host-timezone-independent) — never
        datetime.utcnow().timestamp() (see F11: naive .timestamp() is
        interpreted as host-local time and silently wrong on non-UTC hosts)."""
        return cls(epoch=int(time.time()))


class SessionAuthority(Protocol):
    """
    Protocol a session/calendar authority (e.g. the Alpaca-backed stock
    calendar authority, Patch A item 2) must implement for
    validate_closed_candles() to perform the session-aware "is this actually
    the latest expected closed bar" check. Crypto callers may omit the
    authority entirely (validate_closed_candles falls back to a pure
    wall-clock forming-bar check with no session concept).

    Implementations MUST return None to mean "cannot determine" — the
    validator treats None as fail-closed uncertainty, not as "no constraint".
    """

    def expected_latest_closed_bar_open(
        self, timeframe: str, cutoff: ScanCutoff
    ) -> Optional[int]:
        """Return the open-time epoch of the most recent bar that should
        already be closed and published as of `cutoff`, or None if the
        authority cannot determine this (e.g. stale/missing/malformed
        calendar data) — in which case the caller must fail closed."""
        ...


@dataclass(frozen=True)
class ClosedCandleSeries:
    """
    Persistent CLOSED-candle data for strategy analysis. Never used to supply
    entry-screening quotes or held-position protection (Ron's data-class
    separation invariant).
    """
    symbol: str
    timeframe: str
    df: pd.DataFrame
    validated_at: ScanCutoff


@dataclass(frozen=True)
class EntryQuoteSnapshot:
    """
    Scan-scoped, entry-screening-only quote. Never used for held-position
    protection, stops, trails, take-profit, reconciliation, exposure, sizing,
    or order decisions (Ron's data-class separation invariant) — use
    HeldPositionPrice for those.
    """
    symbol: str
    price: float
    quote_epoch: int
    source: str
    scan_cutoff: ScanCutoff


@dataclass(frozen=True)
class HeldPositionPrice:
    """
    Broker-authoritative price for an already-held position. The only price
    type permitted to drive stops/trails/take-profit/reconciliation/exposure/
    sizing/order decisions. Never sourced from a candle close or an
    EntryQuoteSnapshot.
    """
    symbol: str
    price: float
    fetched_epoch: int
    broker: str


def _is_finite_positive(x) -> bool:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(xf) and xf > 0


def _reject(reason: str, detail: str = "") -> None:
    """Log + count a validator rejection, then return None (the caller
    always `return`s this). Centralizing this keeps every rejection reason
    visible in metrics, not just in a debug log line (implementation-time
    clarification #3: fail-closed suppression must not be operationally
    invisible)."""
    metrics.increment(f"candle_validation.reject.{reason}")
    logger.debug(f"[candle_validation] rejecting ({reason}){': ' + detail if detail else ''}")
    return None


def validate_closed_candles(
    df: Optional[pd.DataFrame],
    timeframe: str,
    cutoff: ScanCutoff,
    session_authority: Optional[SessionAuthority] = None,
    publication_grace_sec: int = 0,
) -> Optional[pd.DataFrame]:
    """
    Strict, fail-closed closed-bar validator.

    Returns a DataFrame containing only rows this function can vouch for as
    genuinely closed, non-malformed, and (if a session_authority is supplied)
    matching the session-aware expected latest closed bar — or None if any
    required property cannot be established with confidence.

    Unlike scanners.market_scanner._strip_forming_bar(), a timestamp parse
    failure or any other uncertainty returns None, not the original data.
    """
    if df is None or df.empty:
        return None

    tf_sec = timeframe_seconds(timeframe)
    if tf_sec is None:
        return _reject("unrecognized_timeframe", repr(timeframe))

    for col in REQUIRED_OHLC_COLUMNS:
        if col not in df.columns:
            return _reject("missing_column", repr(col))

    # Index must be parseable, monotonic, and unique.
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(df.index, utc=False))
    except Exception as e:
        return _reject("index_parse_failure", str(e))

    if idx.tz is not None:
        idx_naive_utc_epochs = [int(t.tz_convert("UTC").timestamp()) for t in idx]
    else:
        idx_naive_utc_epochs = [int(t.tz_localize("UTC").timestamp()) for t in idx]

    if not idx.is_monotonic_increasing or idx.has_duplicates:
        return _reject("nonmonotonic_or_duplicate_index")

    # OHLC must be finite and positive; volume (if present) finite and non-negative.
    ohlc = df[list(REQUIRED_OHLC_COLUMNS)]
    if not ohlc.map(_is_finite_positive).to_numpy().all():
        return _reject("invalid_ohlc")
    if "volume" in df.columns:
        try:
            vol = df["volume"].astype(float)
        except (TypeError, ValueError):
            return _reject("unparseable_volume")
        if not vol.map(lambda v: math.isfinite(v) and v >= 0).all():
            return _reject("invalid_volume")

    # No bar may open in the future relative to cutoff.
    if idx_naive_utc_epochs[-1] > cutoff.epoch:
        return _reject("future_bar")

    result = df.copy()
    last_open_epoch = idx_naive_utc_epochs[-1]
    last_close_epoch = last_open_epoch + tf_sec

    # Drop a still-forming last bar (bar_close is still ahead of cutoff+grace).
    if last_close_epoch > cutoff.epoch + publication_grace_sec:
        result = result.iloc[:-1]
        idx_naive_utc_epochs = idx_naive_utc_epochs[:-1]
        if result.empty:
            return _reject("only_bar_was_forming")
        last_open_epoch = idx_naive_utc_epochs[-1]

    # Session-aware check: the last remaining bar's open time must match the
    # authority's expected latest closed bar (within the publication grace),
    # not be stale (older than expected). Uncertainty from the authority
    # itself propagates as a rejection here — it does not mean "no check".
    if session_authority is not None:
        expected_open = session_authority.expected_latest_closed_bar_open(timeframe, cutoff)
        if expected_open is None:
            return _reject("session_authority_uncertain")
        if last_open_epoch != expected_open:
            return _reject(
                "stale_or_misaligned_bar",
                f"last_open={last_open_epoch} expected_open={expected_open}",
            )

    return result if not result.empty else None


def validate_entry_quote(
    symbol: str,
    price,
    quote_epoch: Optional[int],
    cutoff: ScanCutoff,
    max_age_sec: int,
    source: str,
) -> Optional[EntryQuoteSnapshot]:
    """
    Strict, fail-closed entry-quote validator. Returns None (never a
    substituted/backfilled value) for any non-finite, non-positive, missing,
    unparseable, or stale-relative-to-cutoff quote.
    """
    if not _is_finite_positive(price):
        return _reject("invalid_quote_price", symbol)
    if quote_epoch is None:
        return _reject("missing_quote_timestamp", symbol)
    try:
        quote_epoch = int(quote_epoch)
    except (TypeError, ValueError):
        return _reject("unparseable_quote_timestamp", symbol)
    age = cutoff.epoch - quote_epoch
    if age < 0:
        return _reject("future_quote_timestamp", symbol)
    if age > max_age_sec:
        return _reject("stale_quote", f"{symbol} age={age}s max={max_age_sec}s")
    return EntryQuoteSnapshot(
        symbol=symbol,
        price=float(price),
        quote_epoch=quote_epoch,
        source=source,
        scan_cutoff=cutoff,
    )
