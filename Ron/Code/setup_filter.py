"""
setup_filter.py
===============
Low-float + news catalyst + relative-volume pre-filter for
momentum day-trading setups.

STATUS: INCUBATE — float and news data sources are stubbed (see TODOs).
                   RVol is calculated from the bar window passed in.

The setup (as described by experienced day traders):
  1. News catalyst today  → stock is in play for a reason
  2. Float < 5M shares    → small supply; same buying pressure = bigger move
  3. RVol > 5x            → real participation, not thin-tape drift

When all three are present the setup is qualified for dip-add or momentum
entries. Without this filter the dip-entry rule fires on any red candle
on any random stock.

Usage:
    sf = SetupFilter()
    score = sf.score("AAPL", bars_5m)
    if score.qualified:
        # arm DipTracker
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

# ── Data class ────────────────────────────────────────────────────────────────


@dataclass
class SetupScore:
    symbol: str
    qualified: bool  # all three criteria met
    float_ok: bool
    rvol_ok: bool
    news_ok: bool
    float_shares: (
        float  # 0 = unknown (not yet wired)
    )
    rvol: float  # relative volume ratio
    note: str


# ── Main class ────────────────────────────────────────────────────────────────


class SetupFilter:
    """
    Momentum day-trade setup qualifier.

    Thresholds are conservative defaults — tune once backtested.
    """

    MAX_FLOAT = 5_000_000  # shares
    MIN_RVOL = 5.0  # × average volume

    def score(
        self, symbol: str, bars: List[dict]
    ) -> SetupScore:
        """
        Score a symbol against the three setup criteria.

        bars — recent OHLCV bars used for RVol calculation.
        """
        float_shares = self._get_float(symbol)
        rvol = self._calc_rvol(bars)
        has_news = self._check_news_today(symbol)

        float_ok = (float_shares > 0) and (
            float_shares < self.MAX_FLOAT
        )
        rvol_ok = rvol >= self.MIN_RVOL
        news_ok = has_news
        qualified = (
            float_ok and rvol_ok and news_ok
        )

        issues = []
        if not float_ok:
            label = (
                f"{float_shares/1e6:.1f}M"
                if float_shares > 0
                else "unknown"
            )
            issues.append(
                f"float={label} (need <5M)"
            )
        if not rvol_ok:
            issues.append(
                f"rvol={rvol:.1f}x (need ≥5x)"
            )
        if not news_ok:
            issues.append("no catalyst today")

        note = (
            "qualified ✓"
            if qualified
            else "; ".join(issues)
        )
        return SetupScore(
            symbol,
            qualified,
            float_ok,
            rvol_ok,
            news_ok,
            float_shares,
            rvol,
            note,
        )

    # ── Data stubs (wire these up) ────────────────────────────────────────────

    def _get_float(self, symbol: str) -> float:
        """
        TODO: wire to Polygon.io /v3/reference/tickers/{symbol}
              → field: share_class_shares_outstanding

        Returns 0.0 until wired — causes float_ok=False so setup never
        qualifies on float alone (safe default).
        """
        return 0.0

    def _calc_rvol(
        self, bars: List[dict]
    ) -> float:
        """
        Relative volume = current bar volume / average bar volume in window.

        Proper implementation: compare to same hour of day over 30 trading days.
        This approximation (avg of entire window) is good enough for INCUBATE.
        """
        if not bars:
            return 0.0
        volumes = [
            float(b.get("volume") or 0)
            for b in bars
        ]
        if not any(v > 0 for v in volumes):
            return 0.0
        avg = sum(volumes[:-1]) / max(
            len(volumes) - 1, 1
        )
        return (
            volumes[-1] / avg if avg > 0 else 0.0
        )

    def _check_news_today(
        self, symbol: str
    ) -> bool:
        """
        TODO: wire to Polygon.io /v2/reference/news?ticker={symbol}&limit=5
              Check if any result has published_utc matching today's date.

        Returns False until wired — setup never qualifies on news alone.
        """
        return False
