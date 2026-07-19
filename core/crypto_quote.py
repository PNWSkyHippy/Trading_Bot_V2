"""Venue-local crypto quote helpers.

Never use this helper to compare or substitute prices across exchanges.  It
only chooses the freshest usable reference contained in one venue's ticker.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional


def live_ticker_reference(ticker: Mapping[str, Any]) -> Optional[float]:
    """Prefer a sane live bid/ask midpoint; otherwise return venue-local last."""
    try:
        bid = float(ticker.get("bid") or 0)
        ask = float(ticker.get("ask") or 0)
    except (TypeError, ValueError, OverflowError):
        bid = ask = 0.0

    if (
        math.isfinite(bid)
        and math.isfinite(ask)
        and bid > 0
        and ask > 0
        and bid < ask
    ):
        return (bid + ask) / 2.0

    try:
        last = float(ticker.get("last") or ticker.get("close") or 0)
    except (TypeError, ValueError, OverflowError):
        return None
    return last if math.isfinite(last) and last > 0 else None
