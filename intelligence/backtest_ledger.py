"""
Append-only per-run/per-trade event ledger — backtester parity patch step 3
(reports/agent_pipeline/20260717-085541/final_unified_report.md §6 item 3).

Shadow-only by construction: a RunLedger only ever *records* values the
simulation already computed for its own purposes. Nothing in
intelligence/backtester.py branches on ledger content, and passing
ledger=None (the default at every existing call site) costs one `if ledger`
check per event site — zero behavior change for the ~13 pre-existing
callers that don't know this module exists.

Event types (per report §6 item 3): signal, decision, order, fill,
level_mutation, partial, mfe_mae, exit. `partial` is defined here for
schema completeness but is never emitted today — the backtester has no
partial-fill/partial-exit model yet.
"""

import itertools
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

EVENT_TYPES = frozenset({
    "signal", "decision", "order", "fill",
    "level_mutation", "partial", "mfe_mae", "exit",
})

_seq_counter = itertools.count()


@dataclass(frozen=True)
class LedgerEvent:
    seq: int
    run_id: str
    trade_id: str
    symbol: str
    strategy: str
    event_type: str
    bar_index: int
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)


class RunLedger:
    """Append-only event log for one backtest run.

    One RunLedger belongs to one run, the same isolation contract as
    BacktestRunContext (report step 2) — never share a RunLedger across
    concurrently-running backtests.
    """

    def __init__(self, run_id: str = None):
        self.run_id = run_id or "unlabeled"
        self._events: List[LedgerEvent] = []
        self._lock = threading.Lock()

    def record(self, trade_id: str, symbol: str, strategy: str,
               event_type: str, bar_index: int, timestamp: str,
               **payload) -> None:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown ledger event_type: {event_type!r}")
        evt = LedgerEvent(
            seq=next(_seq_counter),
            run_id=self.run_id,
            trade_id=trade_id,
            symbol=symbol,
            strategy=strategy,
            event_type=event_type,
            bar_index=bar_index,
            timestamp=timestamp,
            payload=dict(payload),
        )
        with self._lock:
            self._events.append(evt)

    def events(self) -> List[LedgerEvent]:
        with self._lock:
            return list(self._events)

    def events_for_trade(self, trade_id: str) -> List[LedgerEvent]:
        return [e for e in self.events() if e.trade_id == trade_id]

    def events_by_type(self, event_type: str) -> List[LedgerEvent]:
        return [e for e in self.events() if e.event_type == event_type]

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)
