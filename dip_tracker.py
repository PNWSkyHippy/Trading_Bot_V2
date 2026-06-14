"""
dip_tracker.py
==============
Per-position dip detection and scale-in confirmation.

STATUS: INCUBATE — returns signals only, never touches the broker.

Entry rule (trader spec):
  Don't scale into a dip until a green candle ENGULFS the last red —
  meaning the current (possibly forming) candle's price exceeds the
  HIGH of the most recent red candle.

Dip expansion rule:
  If each successive dip is >20% deeper than the last, the trend is
  deteriorating. Skip the add, return WARN_EXPANDING instead.

Usage:
    tracker = DipTracker()
    sig = tracker.check("AAPL", bars_1m, live_price=151.23)
    if sig.action == "SCALE_IN":
        # send to trade_maintenance engine — DO NOT execute orders here
        pass
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DipSignal:
    symbol:          str
    action:          str          # "SCALE_IN" | "HOLD" | "WARN_EXPANDING" | "TOO_DEEP"
    trigger_price:   float        # price level that fired (last red's high)
    last_red_high:   float        # confirmation level — green must exceed this
    dip_depth_pct:   float        # depth from recent swing high (%)
    dip_history:     List[float]  # past dip depths for this position [oldest → newest]
    expanding:       bool         # True if dips are getting progressively deeper
    note:            str = ""


# ── Main class ────────────────────────────────────────────────────────────────

class DipTracker:
    """
    Per-position dip analysis on low-timeframe bars (1m / 5m).

    Stateful: tracks swing highs and dip history per symbol so expansion
    detection works across multiple check() calls.

    Call reset() when a new position is opened to clear stale state.
    """

    # Dips growing >20% each step = deteriorating trend
    EXPANDING_THRESHOLD = 0.20

    # Dip deeper than this % from swing high → structure probably broken
    MAX_DIP_DEPTH_PCT = 5.0

    # Look this many bars back for the last red candle
    RED_LOOKBACK = 8

    def __init__(self):
        self._swing_highs: Dict[str, float] = {}
        self._dip_history: Dict[str, List[float]] = {}

    # ── Public ────────────────────────────────────────────────────────────────

    def check(self,
              symbol:     str,
              bars:       List[dict],
              live_price: Optional[float] = None) -> DipSignal:
        """
        Analyse recent bars for dip-confirmation trigger.

        bars       — list of OHLCV dicts, most recent last.
                     Each: {'time':..., 'open':..., 'high':..., 'low':..., 'close':...}
        live_price — current mid-price if available (enables intrabar trigger).
                     Falls back to bars[-1]['close'] when None.
        """
        if len(bars) < 3:
            return DipSignal(symbol, "HOLD", 0.0, 0.0, 0.0, [], False, "insufficient bars")

        closes = [float(b.get('close') or 0) for b in bars]
        opens  = [float(b.get('open')  or 0) for b in bars]
        highs  = [float(b.get('high')  or 0) for b in bars]

        price = live_price if live_price is not None else closes[-1]

        # Update swing high (rolling, never goes down within a position lifecycle)
        recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        prev_high   = self._swing_highs.get(symbol, 0.0)
        self._swing_highs[symbol] = max(prev_high, recent_high)
        swing_high = self._swing_highs[symbol]

        dip_depth_pct = ((swing_high - price) / swing_high * 100) if swing_high else 0.0

        # Find most recent red candle (skip the live/forming candle at [-1])
        last_red = None
        lookback_start = len(bars) - 2
        lookback_end   = max(len(bars) - 2 - self.RED_LOOKBACK, -1)
        for i in range(lookback_start, lookback_end, -1):
            if closes[i] < opens[i]:
                last_red = bars[i]
                break

        if last_red is None:
            return DipSignal(symbol, "HOLD", 0.0, 0.0, dip_depth_pct,
                             self._dip_history.get(symbol, []), False,
                             "no recent red candle — no dip detected")

        last_red_high = float(last_red.get('high') or last_red.get('close') or 0)

        # Bail out if dip is already too deep
        if dip_depth_pct > self.MAX_DIP_DEPTH_PCT:
            return DipSignal(symbol, "TOO_DEEP", last_red_high, last_red_high,
                             dip_depth_pct, self._dip_history.get(symbol, []),
                             False, f"dip {dip_depth_pct:.1f}% — may be trend reversal, not dip")

        # Confirmation: current candle is green AND price exceeds last red's HIGH
        current_open = float(bars[-1].get('open') or 0)
        is_green = price > current_open
        engulfs  = price > last_red_high

        history   = self._dip_history.get(symbol, [])
        expanding = self._is_expanding(history, dip_depth_pct)

        if is_green and engulfs:
            new_history = (history + [dip_depth_pct])[-10:]
            self._dip_history[symbol] = new_history

            if expanding:
                return DipSignal(
                    symbol, "WARN_EXPANDING", last_red_high, last_red_high,
                    dip_depth_pct, new_history, True,
                    "dip expanding: " + " → ".join(f"{d:.1f}%" for d in new_history[-4:])
                )

            return DipSignal(
                symbol, "SCALE_IN", last_red_high, last_red_high,
                dip_depth_pct, new_history, False,
                f"green engulfs last red high {last_red_high:.4f} ✓"
            )

        # Not yet triggered — report what we're waiting for
        if is_green:
            note = f"green forming but price {price:.4f} hasn't cleared red high {last_red_high:.4f}"
        else:
            note = f"waiting for green candle above {last_red_high:.4f}"

        return DipSignal(symbol, "HOLD", last_red_high, last_red_high,
                         dip_depth_pct, history, expanding, note)

    def reset(self, symbol: str):
        """Call when a new position is opened to clear stale swing-high / dip history."""
        self._swing_highs.pop(symbol, None)
        self._dip_history.pop(symbol, None)

    # ── Private ───────────────────────────────────────────────────────────────

    def _is_expanding(self, history: List[float], current_depth: float) -> bool:
        """True if the last 2 recorded dips PLUS the current one are each >20% deeper."""
        seq = history[-2:] + [current_depth]
        if len(seq) < 3:
            return False
        return all(seq[i] > seq[i - 1] * (1 + self.EXPANDING_THRESHOLD)
                   for i in range(1, len(seq)))
