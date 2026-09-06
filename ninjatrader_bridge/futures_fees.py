"""Shared, explicit futures-fee calculation for the EAT and EMT mirrors."""

from __future__ import annotations

import math

import config


def futures_product_root(symbol: object) -> str:
    """Return the configured root for a Tradovate contract or root symbol.

    Examples: ``MNQU6`` and ``MNQ 09-26`` both resolve to ``MNQ``.  A missing
    rate is an accounting configuration error, never a silent zero-fee trade.
    """
    text = "".join(str(symbol or "").upper().split())
    for root in sorted(config.TRADOVATE_ALL_IN_FEE_PER_SIDE_USD, key=len, reverse=True):
        if text == root or text.startswith(root):
            return root
    raise ValueError(
        f"No Tradovate all-in fee rate configured for futures symbol {symbol!r}"
    )


def tradovate_round_trip_fee(symbol: object, quantity: object) -> float:
    """Return the published all-in entry plus exit fee for filled contracts."""
    contracts = float(quantity)
    if not math.isfinite(contracts) or contracts <= 0:
        raise ValueError(f"Futures contract quantity must be positive, got {quantity!r}")
    root = futures_product_root(symbol)
    return round(
        float(config.TRADOVATE_ALL_IN_FEE_PER_SIDE_USD[root]) * contracts * 2,
        4,
    )
