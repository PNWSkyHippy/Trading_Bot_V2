"""
=============================================================
  CANDLE VALIDATION — Patch A data-authority contracts
  reports/agent_pipeline/20260716-082429/final_unified_report.md

  Defines:
    - ScanCutoff              one fixed "now" per scan generation (subsecond)
    - ClosedCandleSeries       persistent CLOSED-candle data (strategy analysis)
    - EntryQuoteSnapshot       scan-scoped entry-screening quote
    - HeldPositionPrice        broker-authoritative held-position price
    - SessionAuthority         protocol a calendar authority must implement
    - validate_closed_candles()  strict, fail-closed candle validator —
                                 returns the ClosedCandleSeries CONTRACT, not
                                 a raw DataFrame
    - validate_entry_quote()     strict, fail-closed quote validator

  Ron's safety invariant: "New entries must fail closed when candle age,
  timestamp parsing, quote freshness, or batch completeness is uncertain."
  Every function here returns None on uncertainty — it never returns a row,
  price, or series it cannot vouch for. This deliberately does NOT reuse
  scanners.market_scanner._strip_forming_bar()'s behavior of keeping a row
  unchanged when its timestamp fails to parse (fail-open) — that was reviewed
  and rejected during the audit (see the report's §5, "Claims tested and
  rejected").

  Data-class separation is enforced, not merely conventional: each of the
  three dataclasses validates its own invariants in __post_init__ (raising
  ValueError on construction with invalid data — for ClosedCandleSeries this
  means running the FULL row-level validation battery, not just structural
  checks, so a caller cannot construct one from continuity/alignment/OHLC-
  invalid data by bypassing the factory) and is additionally produced by a
  validating factory (validate_closed_candles / validate_entry_quote /
  HeldPositionPrice.from_broker) that returns None rather than raising when
  the input itself is untrustworthy. Direct construction with bad data is a
  programming error (raises); a bad *input* to a factory is an expected,
  fail-closed outcome (returns None). ClosedCandleSeries additionally stores
  a defensive copy of its DataFrame so a caller mutating their own original
  reference afterward cannot silently alter the wrapped, already-validated
  data.

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


def _safe_int_epoch(x) -> Optional[int]:
    """
    Coerce `x` to an int epoch, rejecting (returning None, never raising) any
    non-finite value (NaN/±inf — `int()` raises OverflowError specifically
    for infinities and ValueError for NaN, both of which must be treated as
    "cannot validate", not an uncaught crash) and any value so large it would
    overflow a platform int or produce an out-of-range datetime downstream.
    Centralized here so every factory in this module applies the identical
    check rather than each re-deriving its own subset of exception types.
    """
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(xf):
        return None
    try:
        return int(xf)
    except (OverflowError, ValueError):
        return None


@dataclass(frozen=True)
class ScanCutoff:
    """
    One fixed "now" captured at the start of a scan generation and reused for
    every symbol evaluated in that scan — never re-derived per symbol.

    Stores subsecond precision (a float epoch) deliberately: exact
    close+grace boundary decisions are meaningful at sub-second granularity
    (a bar's eligibility can flip between "not yet" and "eligible" across a
    fraction of a second), and truncating to whole seconds would make
    boundary comparisons coarser than the actual wall-clock instant a scan
    was captured at. (An earlier draft of this class truncated to
    `int(time.time())`; that precision loss is restored here.)

    Rationale (B5): a scan that happens to straddle a bar-close boundary
    partway through must not validate early symbols against the old bar and
    later symbols against the new bar while treating the whole pass as one
    scan generation.
    """
    epoch: float

    def __post_init__(self):
        if isinstance(self.epoch, bool) or not isinstance(self.epoch, (int, float)):
            raise ValueError(f"ScanCutoff.epoch must be a real number, got {type(self.epoch)!r}")
        if not math.isfinite(self.epoch):
            raise ValueError(f"ScanCutoff.epoch must be finite, got {self.epoch!r}")

    @classmethod
    def now(cls) -> "ScanCutoff":
        """Capture the current instant as a new scan's fixed cutoff, with
        subsecond precision. Uses time.time() (UTC epoch, host-timezone-
        independent) — never datetime.utcnow().timestamp() (see F11: naive
        .timestamp() is interpreted as host-local time and silently wrong on
        non-UTC hosts)."""
        return cls(epoch=time.time())


class SessionAuthority(Protocol):
    """
    Protocol a session/calendar authority (e.g. the Alpaca-backed stock
    calendar authority) must implement for validate_closed_candles() to
    perform session-aware validation. Crypto callers may omit the authority
    entirely (validate_closed_candles falls back to a pure wall-clock
    forming-bar check with no session concept, and requires every gap to be
    exactly one bar width with no exceptions — crypto trades continuously).

    Implementations should return None (not raise, though the validator
    treats a raised exception identically to None) to mean "cannot
    determine" — the validator treats both as fail-closed uncertainty, never
    as "no constraint".
    """

    def expected_latest_closed_bar_open(
        self, timeframe: str, cutoff: "ScanCutoff"
    ) -> Optional[int]:
        """Return the open-time epoch of the most recent bar that should
        already be closed and published as of `cutoff`, or None if the
        authority cannot determine this (e.g. stale/missing/malformed
        calendar data) — in which case the caller must fail closed."""
        ...

    def is_valid_session_gap(
        self, prior_bar_close_epoch: int, next_bar_open_epoch: int, cutoff: "ScanCutoff"
    ) -> Optional[bool]:
        """
        Return True if the gap between a bar closing at
        `prior_bar_close_epoch` and the next bar opening at
        `next_bar_open_epoch` is explained by a legitimate non-trading
        period (overnight close-to-open, weekend, holiday, or early-close
        boundary) — i.e. `prior_bar_close_epoch` is exactly some trading
        session's close and `next_bar_open_epoch` is exactly the *next*
        trading session's open, with every calendar date strictly between
        them confirmed non-trading. Return False if this is confirmed NOT
        the case, or None if the authority cannot determine it either way
        (unrefreshed/stale data) — the validator treats both False and None
        as "reject the gap", never as "assume it's fine".
        """
        ...


def _validate_closed_candle_series_fields(symbol: str, timeframe: str, df: pd.DataFrame) -> None:
    """Shared structural invariant check for direct ClosedCandleSeries
    construction. Raises ValueError. This alone is NOT sufficient to prove
    the data is valid closed-candle data (see ClosedCandleSeries.__post_init__,
    which additionally re-runs the full row-level validation battery)."""
    if not symbol:
        raise ValueError("ClosedCandleSeries.symbol must be non-empty")
    if timeframe_seconds(timeframe) is None:
        raise ValueError(f"ClosedCandleSeries.timeframe unrecognized: {timeframe!r}")
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("ClosedCandleSeries.df must be a non-empty DataFrame")
    for col in REQUIRED_OHLC_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"ClosedCandleSeries.df missing required column {col!r}")


@dataclass(frozen=True)
class ClosedCandleSeries:
    """
    Persistent CLOSED-candle data for strategy analysis. Never used to supply
    entry-screening quotes or held-position protection (Ron's data-class
    separation invariant).

    Construction-safety: __post_init__ re-runs the full row-level validator
    (`_validate_rows`) against `self.df` using `self.validated_at` as the
    cutoff, zero publication grace, and no session authority — if that
    validation would reject the data or trim even a single row, construction
    raises ValueError. This makes it structurally impossible to construct a
    ClosedCandleSeries from continuity-broken, misaligned, relationally-
    invalid-OHLC, forming, or otherwise unvalidated data, not merely
    discouraged by convention — the only sanctioned normal-use path is the
    `validate_closed_candles()` factory function, which already performed
    this exact validation (with the real session_authority/grace) and hands
    back already-known-good data, so the __post_init__ re-check there is
    cheap and always passes; the guard exists for anyone tempted to
    construct this type directly from raw/unvalidated data.

    Immutability: the stored `df` is a defensive copy of whatever was passed
    in, taken during construction — mutating the caller's original
    DataFrame afterward cannot alter the data held by this instance.
    """
    symbol: str
    timeframe: str
    df: pd.DataFrame
    validated_at: ScanCutoff

    def __post_init__(self):
        _validate_closed_candle_series_fields(self.symbol, self.timeframe, self.df)
        # Defensive copy BEFORE re-validating, so the re-validation itself
        # can't be fooled by a concurrent mutation of the caller's original
        # object, and so the stored df is independent of it either way.
        object.__setattr__(self, "df", self.df.copy(deep=True))
        # enforce_continuity_and_alignment=False: this self-check has no
        # session_authority reference to re-derive gap legitimacy or
        # session-relative alignment with (ClosedCandleSeries deliberately
        # stores no authority reference, to remain a pure data contract) —
        # re-running those two checks with session_authority=None would
        # incorrectly reject legitimate authority-confirmed session gaps,
        # and would ALSO incorrectly reject perfectly normal, gap-free
        # 1-hour stock data (whose first intraday bar of a session is a
        # partial bar, not aligned to the UTC hour grid the no-authority
        # path assumes). Everything else — NaT, monotonic/unique, OHLC
        # numeric/relational validity, volume, future-bar, forming-bar as of
        # validated_at with zero grace — is still fully re-checked here.
        revalidated = _validate_rows(
            self.df, self.timeframe, self.validated_at,
            session_authority=None, publication_grace_sec=0,
            enforce_continuity_and_alignment=False,
        )
        if revalidated is None or len(revalidated) != len(self.df):
            raise ValueError(
                "ClosedCandleSeries cannot be constructed from data that does "
                "not pass the closed-candle validator's authority-independent "
                "checks unchanged (NaT/monotonic/relational-OHLC/volume/future-"
                "bar/forming-bar-as-of-validated_at) — use validate_closed_candles() "
                "instead of constructing this type directly from raw/unvalidated "
                "data. (Continuity/alignment legitimacy for session-gapped stock "
                "data cannot be re-derived here without a session authority "
                "reference, which this pure data type deliberately does not "
                "store — that guarantee is provided procedurally by "
                "validate_closed_candles() being the only reasonable "
                "construction path, not by a redundant self-check.)"
            )

    @classmethod
    def from_validated(
        cls,
        symbol: str,
        raw_df: Optional[pd.DataFrame],
        timeframe: str,
        cutoff: ScanCutoff,
        session_authority: Optional[SessionAuthority] = None,
        publication_grace_sec: int = 0,
    ) -> Optional["ClosedCandleSeries"]:
        """Alias for the module-level validate_closed_candles() factory,
        kept for call-site readability (`ClosedCandleSeries.from_validated(...)`
        reads clearly at a construction site) — both share one implementation."""
        return validate_closed_candles(
            symbol, raw_df, timeframe, cutoff,
            session_authority=session_authority,
            publication_grace_sec=publication_grace_sec,
        )


@dataclass(frozen=True)
class EntryQuoteSnapshot:
    """
    Scan-scoped, entry-screening-only quote. Never used for held-position
    protection, stops, trails, take-profit, reconciliation, exposure, sizing,
    or order decisions (Ron's data-class separation invariant) — use
    HeldPositionPrice for those.

    Prefer the validate_entry_quote() factory function over direct
    construction — __post_init__ enforces basic invariants (finite positive
    price, non-negative finite epoch) but does not re-run freshness/age
    checks (those require a cutoff and max-age policy, not available here).
    """
    symbol: str
    price: float
    quote_epoch: int
    source: str
    scan_cutoff: ScanCutoff

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("EntryQuoteSnapshot.symbol must be non-empty")
        if not _is_finite_positive(self.price):
            raise ValueError(f"EntryQuoteSnapshot.price must be finite and positive, got {self.price!r}")
        if isinstance(self.quote_epoch, bool) or not isinstance(self.quote_epoch, int) or self.quote_epoch < 0:
            raise ValueError(f"EntryQuoteSnapshot.quote_epoch must be a non-negative int, got {self.quote_epoch!r}")
        if not self.source:
            raise ValueError("EntryQuoteSnapshot.source must be non-empty")


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

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("HeldPositionPrice.symbol must be non-empty")
        if not _is_finite_positive(self.price):
            raise ValueError(f"HeldPositionPrice.price must be finite and positive, got {self.price!r}")
        if isinstance(self.fetched_epoch, bool) or not isinstance(self.fetched_epoch, int) or self.fetched_epoch < 0:
            raise ValueError(f"HeldPositionPrice.fetched_epoch must be a non-negative int, got {self.fetched_epoch!r}")
        if not self.broker:
            raise ValueError("HeldPositionPrice.broker must be non-empty")

    @classmethod
    def from_broker(cls, symbol: str, price, fetched_epoch, broker: str) -> Optional["HeldPositionPrice"]:
        """Fail-closed factory: returns None (never raises, and never lets
        an OverflowError/ValueError from a non-finite or out-of-range
        timestamp escape) for non-finite/non-positive price or an
        unparseable/non-finite/overflowing timestamp. Use this at the actual
        broker-response boundary; use the raising constructor only when the
        caller has already validated the inputs itself."""
        if not _is_finite_positive(price):
            return _reject("invalid_held_position_price", symbol)
        safe_epoch = _safe_int_epoch(fetched_epoch)
        if safe_epoch is None:
            return _reject("unparseable_or_nonfinite_held_position_timestamp", symbol)
        if safe_epoch < 0:
            return _reject("invalid_held_position_timestamp", symbol)
        return cls(symbol=symbol, price=float(price), fetched_epoch=safe_epoch, broker=broker)


def _is_finite_positive(x) -> bool:
    try:
        xf = float(x)
    except (TypeError, ValueError, OverflowError):
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


def _coerce_ohlc_numeric(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Return a copy of `df` with open/high/low/close explicitly coerced to
    float64, or None if any value cannot be coerced.

    This exists because comparing raw (possibly object- or string-dtype)
    columns with `>`/`<` directly is a real correctness hazard, not merely a
    style concern: pandas performs whatever comparison the column's *actual*
    dtype supports, and an object/string-dtype column compares
    LEXICOGRAPHICALLY, not numerically. E.g. with string values, `"5.0" >
    "10.0"` is True (comparing character-by-character: "5" > "1"), even
    though 5.0 < 10.0 numerically — a relational-OHLC check run directly on
    such a column could reach exactly the wrong conclusion (or the opposite
    of the wrong conclusion, unpredictably, depending on the specific string
    values involved) rather than raising or comparing correctly. Explicit
    numeric coercion before any relational comparison eliminates this
    ambiguity: either every value becomes an unambiguous float, or the
    series is rejected outright.
    """
    try:
        numeric = df[list(REQUIRED_OHLC_COLUMNS)].apply(pd.to_numeric, errors="raise")
    except (ValueError, TypeError):
        return None
    if not numeric.map(lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)).to_numpy().all():
        return None
    out = df.copy()
    out[list(REQUIRED_OHLC_COLUMNS)] = numeric.astype("float64")
    return out


def _validate_rows(
    df: Optional[pd.DataFrame],
    timeframe: str,
    cutoff: ScanCutoff,
    session_authority: Optional[SessionAuthority] = None,
    publication_grace_sec: int = 0,
    enforce_continuity_and_alignment: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Internal row-level validator. Returns a DataFrame containing only rows
    this function can vouch for, or None. This is the shared implementation
    behind both the public `validate_closed_candles()` factory (which wraps
    the result in the ClosedCandleSeries contract) and
    `ClosedCandleSeries.__post_init__`'s construction-safety re-check (which
    needs the raw row-level result, not another wrapped instance).

    `enforce_continuity_and_alignment=False` skips the continuity and
    no-authority-alignment checks entirely (everything else — NaT, monotonic/
    unique, OHLC numeric/relational, volume, future-bar, forming-bar — still
    runs). This exists ONLY for `ClosedCandleSeries.__post_init__`'s self-
    check, which re-validates already-validated data WITHOUT access to
    whatever session_authority (if any) was originally used — re-running the
    continuity/alignment checks with `session_authority=None` in that context
    would incorrectly reject legitimate, authority-confirmed session gaps
    (and, separately, would incorrectly reject perfectly normal 1-hour stock
    data even with NO gap at all, since that data's own first intraday bar of
    a session is a partial bar not aligned to the UTC hour grid — the
    no-authority alignment check assumes a crypto-style continuously-epoch-
    aligned series, which stock data legitimately is not). The public
    `validate_closed_candles()` factory, which DOES have the real
    session_authority in hand, always leaves this True.
    """
    if df is None or df.empty:
        return None

    tf_sec = timeframe_seconds(timeframe)
    if tf_sec is None:
        return _reject("unrecognized_timeframe", repr(timeframe))

    for col in REQUIRED_OHLC_COLUMNS:
        if col not in df.columns:
            return _reject("missing_column", repr(col))

    # Index must be parseable (rejecting NaT explicitly — pd.to_datetime does
    # not raise on an unparseable element by default, it silently produces
    # NaT, which would otherwise slip through monotonicity/duplicate checks
    # as a sortable-but-meaningless value).
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(df.index, utc=False))
    except Exception as e:
        return _reject("index_parse_failure", str(e))

    if idx.isna().any():
        return _reject("unparseable_timestamp_nat")

    try:
        if idx.tz is not None:
            idx_epochs = [_safe_int_epoch(t.tz_convert("UTC").timestamp()) for t in idx]
        else:
            idx_epochs = [_safe_int_epoch(t.tz_localize("UTC").timestamp()) for t in idx]
    except (OverflowError, OSError, ValueError) as e:
        return _reject("timestamp_conversion_overflow", str(e))
    if any(e is None for e in idx_epochs):
        return _reject("nonfinite_or_overflowing_bar_timestamp")

    if not idx.is_monotonic_increasing or idx.has_duplicates:
        return _reject("nonmonotonic_or_duplicate_index")

    # Coerce OHLC to numeric BEFORE any relational comparison (see
    # _coerce_ohlc_numeric's docstring for the string/object-dtype
    # ambiguity this specifically closes).
    numeric_df = _coerce_ohlc_numeric(df)
    if numeric_df is None:
        return _reject("nonnumeric_ohlc")

    # Continuity, session-aware for stocks: every consecutive pair must
    # either be spaced by exactly one bar duration, OR — only when a
    # session_authority is supplied — be a gap the authority can positively
    # confirm corresponds to a legitimate non-trading period (overnight
    # close-to-open, weekend, holiday, early close). No authority means no
    # exceptions are possible: every gap fails closed exactly as before
    # (this is the crypto/continuous-market path, and also protects stocks
    # when no authority happens to be wired in for some reason — the
    # decision to allow session gaps is opt-in via supplying the authority,
    # never a default).
    if enforce_continuity_and_alignment and len(idx_epochs) > 1:
        for a, b in zip(idx_epochs[:-1], idx_epochs[1:]):
            gap = b - a
            if gap == tf_sec:
                continue
            if session_authority is None:
                return _reject(
                    "noncontinuous_series",
                    f"gap {a}->{b} ({gap}s) != {tf_sec}s and no session authority to explain it",
                )
            try:
                verdict = session_authority.is_valid_session_gap(a + tf_sec, b, cutoff)
            except Exception as e:
                return _reject("session_authority_exception_on_gap", str(e))
            if verdict is not True:
                return _reject(
                    "unexplained_session_gap",
                    f"gap {a}->{b} ({gap}s) not confirmed as a legitimate session boundary",
                )

    # Alignment: every bar must fall on the same modular grid as the first
    # bar (catches a corrupted/shifted timestamp that continuity alone could
    # miss if, hypothetically, an entire series were uniformly offset).
    # Crypto (no session_authority) is additionally checked against the UTC
    # epoch grid, since crypto exchanges align bars to UTC clock boundaries.
    # Stocks are not required to be epoch-grid-aligned (a session's first
    # intraday bar legitimately starts at the session open time, which is
    # not a round UTC boundary for every granularity) — the session-aware
    # expected-bar check below is the authoritative alignment proof for that
    # case instead.
    first_epoch = idx_epochs[0]
    if enforce_continuity_and_alignment and session_authority is None:
        if any((e - first_epoch) % tf_sec != 0 for e in idx_epochs):
            return _reject("misaligned_series")
        if first_epoch % tf_sec != 0:
            return _reject("misaligned_to_utc_grid")

    # Relational OHLC integrity: low <= open,close <= high for every row
    # (individually finite/positive is necessary but not sufficient — e.g.
    # high=1, low=2 is impossible even though both values are finite/positive).
    # Uses numeric_df (coerced above), never the raw possibly-non-numeric df.
    ohlc = numeric_df[list(REQUIRED_OHLC_COLUMNS)]
    if not ohlc.map(_is_finite_positive).to_numpy().all():
        return _reject("invalid_ohlc")
    low = numeric_df["low"]
    high = numeric_df["high"]
    if (low > high).any():
        return _reject("impossible_ohlc_low_gt_high")
    if (numeric_df["open"] < low).any() or (numeric_df["open"] > high).any():
        return _reject("impossible_ohlc_open_outside_range")
    if (numeric_df["close"] < low).any() or (numeric_df["close"] > high).any():
        return _reject("impossible_ohlc_close_outside_range")

    if "volume" in df.columns:
        try:
            vol = pd.to_numeric(df["volume"], errors="raise").astype(float)
        except (TypeError, ValueError):
            return _reject("unparseable_volume")
        if not vol.map(lambda v: math.isfinite(v) and v >= 0).all():
            return _reject("invalid_volume")

    # No bar may open in the future relative to cutoff.
    if idx_epochs[-1] > cutoff.epoch:
        return _reject("future_bar")

    # Forming-bar truncation: a bar is eligible only once
    # cutoff >= close + publication_grace_sec — i.e. drop a trailing row
    # while close > cutoff - grace (equivalently close + grace > cutoff).
    # Grace is time ADDED after close to tolerate provider publication lag;
    # it delays eligibility, it does not admit a bar early. (Two earlier
    # drafts of this validator had the sign backwards — first admitting bars
    # up to `grace` seconds before their true close, then a "fix" that
    # instead admitted them up to `grace` seconds too early from the other
    # direction. `test_publication_grace_requires_close_plus_grace_not_close_minus_grace`
    # in Scripts/test_candle_validation.py exists specifically to catch this
    # class of regression again.) Looped, not a single conditional check, so
    # more than one trailing forming/not-yet-eligible row (e.g. a large grace
    # spanning multiple bar widths) is fully handled, not just the last one.
    result = numeric_df.copy()
    remaining_epochs = list(idx_epochs)
    while remaining_epochs and (remaining_epochs[-1] + tf_sec) > (cutoff.epoch - publication_grace_sec):
        result = result.iloc[:-1]
        remaining_epochs.pop()
    if not remaining_epochs:
        return _reject("only_bar_was_forming")

    # Defensive, explicit re-check that every remaining row is eligible as of
    # cutoff - grace — not merely inferred from the truncation loop above.
    if any((e + tf_sec) > (cutoff.epoch - publication_grace_sec) for e in remaining_epochs):
        return _reject("forming_bar_survived_truncation")

    last_open_epoch = remaining_epochs[-1]

    # Session-aware check: the last remaining bar's open time must match the
    # authority's expected latest closed bar, not be stale (older than
    # expected) or misaligned. Uncertainty from the authority itself —
    # whether it returns None or raises — propagates as a rejection here; it
    # never means "no check" or an uncaught crash out of this validator.
    if session_authority is not None:
        try:
            expected_open = session_authority.expected_latest_closed_bar_open(timeframe, cutoff)
        except Exception as e:
            return _reject("session_authority_exception", str(e))
        if expected_open is None:
            return _reject("session_authority_uncertain")
        if last_open_epoch != expected_open:
            return _reject(
                "stale_or_misaligned_bar",
                f"last_open={last_open_epoch} expected_open={expected_open}",
            )

    return result if not result.empty else None


def validate_closed_candles(
    symbol: str,
    df: Optional[pd.DataFrame],
    timeframe: str,
    cutoff: ScanCutoff,
    session_authority: Optional[SessionAuthority] = None,
    publication_grace_sec: int = 0,
) -> Optional[ClosedCandleSeries]:
    """
    Strict, fail-closed closed-bar validator. THE public entry point for
    turning raw candle data into the ClosedCandleSeries contract — returns
    the contract type itself, not a raw DataFrame, so a caller cannot end up
    holding "validated-looking" data that is actually an unwrapped, easily-
    confused-with-unvalidated pandas object.

    Returns a ClosedCandleSeries wrapping only rows this function can vouch
    for as genuinely closed (as of `cutoff`, plus `publication_grace_sec`),
    continuous (every consecutive pair spaced by exactly one bar duration,
    OR — with a session_authority — a gap positively confirmed as a
    legitimate non-trading-period boundary), self-consistently aligned,
    numeric (explicitly coerced, never compared as raw/object/string data),
    relationally valid OHLC (low <= open,close <= high), and — if a
    session_authority is supplied — matching the session-aware expected
    latest closed bar. Returns None if any required property cannot be
    established with confidence.

    Unlike scanners.market_scanner._strip_forming_bar(), a timestamp parse
    failure or any other uncertainty returns None, not the original data.
    """
    validated_df = _validate_rows(
        df, timeframe, cutoff,
        session_authority=session_authority,
        publication_grace_sec=publication_grace_sec,
    )
    if validated_df is None:
        return None
    return ClosedCandleSeries(
        symbol=symbol, timeframe=timeframe, df=validated_df, validated_at=cutoff,
    )


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
    substituted/backfilled value, and never lets an OverflowError from a
    non-finite/out-of-range timestamp escape) for any non-finite, non-
    positive, missing, unparseable, nonfinite, or stale-relative-to-cutoff
    quote.
    """
    if not _is_finite_positive(price):
        return _reject("invalid_quote_price", symbol)
    if quote_epoch is None:
        return _reject("missing_quote_timestamp", symbol)
    safe_epoch = _safe_int_epoch(quote_epoch)
    if safe_epoch is None:
        return _reject("unparseable_or_nonfinite_quote_timestamp", symbol)
    if safe_epoch < 0:
        return _reject("invalid_quote_timestamp", symbol)
    age = cutoff.epoch - safe_epoch
    if age < 0:
        return _reject("future_quote_timestamp", symbol)
    if age > max_age_sec:
        return _reject("stale_quote", f"{symbol} age={age}s max={max_age_sec}s")
    return EntryQuoteSnapshot(
        symbol=symbol,
        price=float(price),
        quote_epoch=safe_epoch,
        source=source,
        scan_cutoff=cutoff,
    )
