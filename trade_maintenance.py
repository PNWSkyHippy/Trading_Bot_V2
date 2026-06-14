"""
trade_maintenance.py
====================
Advanced trade management engine — 4-mode signal generator.

STATUS: INCUBATE — signals only, NEVER executes orders directly.
                   Wire into position_monitor once backtested.

The 4 modes
-----------
  REVERSE      Close + open opposite on high-confidence reversal pattern.
               Fires when macro-TF (15m/1h) pattern confidence ≥ REVERSE_THRESHOLD
               AND pattern direction opposes the current position.

  EARLY_EXIT   Close before stop on moderate reversal signal.
               Fires when macro pattern confidence ≥ EXIT_THRESHOLD but below
               REVERSE_THRESHOLD — "get out clean, don't flip yet."

  SCALE_IN     Add a tranche to a winning position on confirmed dip.
               Requires DipTracker SCALE_IN signal on micro-TF (1m/5m).
               Tranche size shrinks when dips are expanding.
               Optionally requires SetupFilter qualification (low-float setups only).

  OPTIONS      Sell covered calls when late-stage bearish exhaustion detected.
               Phase 3 — stub only. Requires IBKR options routing.

Usage:
    engine = TradeMaintenanceEngine()
    signals = engine.evaluate(position, macro_bars, micro_bars)
    for sig in signals:
        logging.info(f"[MAINTENANCE] {sig}")
        # DO NOT execute — route to human review or future auto-executor
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from dip_tracker import DipTracker, DipSignal
from setup_filter import SetupFilter, SetupScore

try:
    from chart_patterns import PatternDetector, PatternResult
except ImportError:
    PatternDetector = None  # type: ignore
    PatternResult   = None  # type: ignore

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class MaintenanceSignal:
    symbol:       str
    mode:         str          # "REVERSE" | "EARLY_EXIT" | "SCALE_IN" | "OPTIONS" | "NONE"
    direction:    str          # "LONG" | "SHORT" | "CLOSE"
    confidence:   float        # 0.0 – 1.0
    trigger:      str          # human-readable reason
    pattern_name: str  = ""
    dip_signal:   Optional[DipSignal]   = field(default=None, repr=False)
    setup_score:  Optional[SetupScore]  = field(default=None, repr=False)

    def __str__(self):
        return (f"[{self.mode}] {self.symbol} → {self.direction} "
                f"({self.confidence:.0%}) — {self.trigger}")


# ── Thresholds ────────────────────────────────────────────────────────────────

REVERSE_THRESHOLD = 0.75    # pattern confidence needed to flip position
EXIT_THRESHOLD    = 0.50    # pattern confidence needed for early exit

# Tranche sizes as % of original position
SCALE_TRANCHE_NORMAL   = 0.25   # normal dip → add 25% of original size
SCALE_TRANCHE_WARN     = 0.10   # expanding dip → add small probe only

# Bearish exhaustion confidence for options signal
OPTIONS_EXHAUSTION_MIN = 0.60


# ── Main engine ───────────────────────────────────────────────────────────────

class TradeMaintenanceEngine:
    """
    Evaluates open positions against pattern signals and dip signals.

    Stateful: owns a DipTracker instance so dip history persists across calls.
    Create one instance per bot session and reuse it.
    """

    def __init__(self, require_setup_filter: bool = False):
        """
        require_setup_filter — if True, SCALE_IN only fires on stocks that
                               pass SetupFilter (news + float + rvol).
                               Default False until float/news data is wired.
        """
        self._dip_tracker    = DipTracker()
        self._setup_filter   = SetupFilter()
        self._require_setup  = require_setup_filter
        self._detector       = PatternDetector() if PatternDetector else None

    # ── Public ────────────────────────────────────────────────────────────────

    def evaluate(self,
                 position:    dict,
                 macro_bars:  List[dict],
                 micro_bars:  List[dict],
                 live_price:  Optional[float] = None) -> List[MaintenanceSignal]:
        """
        Evaluate an open position and return maintenance signals.

        position   — dict with at least: symbol, direction ("LONG"|"SHORT"),
                     entry_price, current_price, size
        macro_bars — 15m or 1h bars for pattern detection (direction check)
        micro_bars — 1m or 5m bars for dip analysis (execution timing)
        live_price — current tick price for intrabar dip confirmation

        Returns a list of MaintenanceSignal (may be empty = no action needed).
        """
        symbol    = position.get('symbol', '')
        direction = position.get('direction', 'LONG').upper()
        signals: List[MaintenanceSignal] = []

        # ── Mode 1 & 2: pattern-based reversal / exit ─────────────────────────
        pattern_sigs = self._check_reversal_patterns(symbol, direction, macro_bars)
        signals.extend(pattern_sigs)

        # If we're already signalling REVERSE, skip scale-in checks
        if any(s.mode == 'REVERSE' for s in pattern_sigs):
            return signals

        # ── Mode 3: dip scale-in ──────────────────────────────────────────────
        scale_sig = self._check_scale_in(symbol, direction, micro_bars, live_price)
        if scale_sig:
            signals.append(scale_sig)

        # ── Mode 4: options hedge (stub) ──────────────────────────────────────
        options_sig = self._check_options_hedge(symbol, direction, macro_bars)
        if options_sig:
            signals.append(options_sig)

        return signals

    def on_position_opened(self, symbol: str):
        """Call when a new position is opened to reset dip history."""
        self._dip_tracker.reset(symbol)

    # ── Mode 1 & 2 internals ─────────────────────────────────────────────────

    def _check_reversal_patterns(self,
                                 symbol:    str,
                                 direction: str,
                                 bars:      List[dict]) -> List[MaintenanceSignal]:
        if not self._detector or len(bars) < 20:
            return []

        closes  = [float(b.get('close') or 0) for b in bars]
        volumes = [float(b.get('volume') or 0) for b in bars]
        opens   = [float(b.get('open')   or 0) for b in bars]
        highs   = [float(b.get('high')   or 0) for b in bars]
        lows    = [float(b.get('low')    or 0) for b in bars]

        try:
            results: List[PatternResult] = self._detector.detect(
                closes, volumes, opens=opens, highs=highs, lows=lows,
                min_confidence=EXIT_THRESHOLD
            )
        except Exception as e:
            logger.warning(f"[maintenance] pattern detect failed for {symbol}: {e}")
            return []

        signals = []
        for r in results:
            opposes = (direction == 'LONG'  and r.direction == 'SHORT') or \
                      (direction == 'SHORT' and r.direction == 'LONG')
            if not opposes:
                continue

            if r.confidence >= REVERSE_THRESHOLD:
                signals.append(MaintenanceSignal(
                    symbol      = symbol,
                    mode        = 'REVERSE',
                    direction   = r.direction,
                    confidence  = r.confidence,
                    trigger     = f"{r.name} ({r.confidence:.0%}) opposes {direction} — flip position",
                    pattern_name= r.name,
                ))
                break   # one reverse signal is enough

            signals.append(MaintenanceSignal(
                symbol      = symbol,
                mode        = 'EARLY_EXIT',
                direction   = 'CLOSE',
                confidence  = r.confidence,
                trigger     = f"{r.name} ({r.confidence:.0%}) — exit before stop",
                pattern_name= r.name,
            ))

        return signals

    # ── Mode 3 internals ─────────────────────────────────────────────────────

    def _check_scale_in(self,
                        symbol:     str,
                        direction:  str,
                        bars:       List[dict],
                        live_price: Optional[float]) -> Optional[MaintenanceSignal]:
        # Only scale into longs for now (shorts need separate dip-rip logic)
        if direction != 'LONG':
            return None

        # Optional setup filter gate
        if self._require_setup:
            setup = self._setup_filter.score(symbol, bars)
            if not setup.qualified:
                return MaintenanceSignal(
                    symbol     = symbol,
                    mode       = 'NONE',
                    direction  = 'LONG',
                    confidence = 0.0,
                    trigger    = f"setup filter fail: {setup.note}",
                    setup_score= setup,
                )

        dip = self._dip_tracker.check(symbol, bars, live_price)

        if dip.action == 'SCALE_IN':
            return MaintenanceSignal(
                symbol     = symbol,
                mode       = 'SCALE_IN',
                direction  = 'LONG',
                confidence = 0.70,
                trigger    = dip.note,
                dip_signal = dip,
            )

        if dip.action == 'WARN_EXPANDING':
            return MaintenanceSignal(
                symbol     = symbol,
                mode       = 'SCALE_IN',
                direction  = 'LONG',
                confidence = 0.35,    # lower confidence → smaller tranche
                trigger    = f"WARN: {dip.note} — small probe only",
                dip_signal = dip,
            )

        if dip.action == 'TOO_DEEP':
            return MaintenanceSignal(
                symbol     = symbol,
                mode       = 'EARLY_EXIT',
                direction  = 'CLOSE',
                confidence = 0.55,
                trigger    = dip.note,
                dip_signal = dip,
            )

        return None

    # ── Mode 4 stub ───────────────────────────────────────────────────────────

    def _check_options_hedge(self,
                             symbol:    str,
                             direction: str,
                             bars:      List[dict]) -> Optional[MaintenanceSignal]:
        """
        Stub: detect late-stage bearish exhaustion on long positions and
        suggest selling covered calls to lock profit.

        TODO (Phase 3):
          - Wire IBKR options chain lookup for nearest OTM call
          - Confirm delta/IV thresholds before suggesting strike
          - Only for stocks (not crypto — no options)
        """
        if not self._detector or direction != 'LONG' or len(bars) < 10:
            return None

        closes  = [float(b.get('close') or 0) for b in bars]
        volumes = [float(b.get('volume') or 0) for b in bars]
        opens   = [float(b.get('open')   or 0) for b in bars]
        highs   = [float(b.get('high')   or 0) for b in bars]
        lows    = [float(b.get('low')    or 0) for b in bars]

        try:
            results = self._detector.detect(
                closes, volumes, opens=opens, highs=highs, lows=lows,
                min_confidence=OPTIONS_EXHAUSTION_MIN
            )
        except Exception:
            return None

        exhaustion = next((r for r in results
                           if r.name == 'Bearish Exhaustion' and r.direction == 'SHORT'),
                          None)
        if not exhaustion:
            return None

        return MaintenanceSignal(
            symbol      = symbol,
            mode        = 'OPTIONS',
            direction   = 'LONG',    # still long, just hedging with calls
            confidence  = exhaustion.confidence,
            trigger     = (f"Bearish Exhaustion ({exhaustion.confidence:.0%}) — "
                           f"consider selling covered calls to lock profit. "
                           f"[STUB: IBKR options routing not yet wired]"),
            pattern_name= exhaustion.name,
        )


# ── Convenience: tranche size helper ─────────────────────────────────────────

def tranche_size(signal: MaintenanceSignal, base_size: float) -> float:
    """
    Return the recommended add size given a SCALE_IN signal.

    base_size — original position size in shares/contracts/units.
    """
    if signal.mode != 'SCALE_IN':
        return 0.0
    dip = signal.dip_signal
    if dip and dip.expanding:
        return base_size * SCALE_TRANCHE_WARN
    return base_size * SCALE_TRANCHE_NORMAL
