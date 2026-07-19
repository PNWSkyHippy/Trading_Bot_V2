"""Real-strategy/profile ledger comparison using Hostinger-derived cases.

This is an explicit integration test: it loads each strategy's real class and
uses the symbol/timeframe most recently observed in Hostinger's read-only trade
history (or a representative symbol for enabled strategies with no trades).
It never submits orders and does not touch the trading database.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intelligence.backtest_ledger import RunLedger
from intelligence.backtester import (
    BEHAVIOR_ISOLATED_V1,
    BEHAVIOR_LIVE_PARITY_V2,
    Backtester,
)


# Enabled + actually instantiated by StrategyEngine on Hostinger, verified
# read-only 2026-07-19. marc_strategy/vdmr_strategy have stale enabled DB keys
# but are not instantiated by StrategyEngine and therefore are not live cases.
LIVE_CASES = {
    "bmr_357":                ("SAND/USD", "crypto", "15m", 59),
    "bollinger_breakout":    ("RIVN",     "stock",  "5m",  58),
    "hammer_reversal":       ("RIVN",     "stock",  "5m",  58),
    "orb_breakout":          ("ALAB",     "stock",  "15m", 59),
    "pll_cycle":             ("BTC/USD",  "crypto", "1h",  365),
    "scalp_master":          ("MSFT",     "stock",  "5m",  58),
    "vwap_momentum":         ("NIO",      "stock",  "1h",  365),
}


def _event_summary(ledger: RunLedger):
    events = ledger.events()
    return {
        "event_counts": dict(sorted(Counter(e.event_type for e in events).items())),
        "exit_reasons": dict(sorted(Counter(
            e.payload.get("exit_reason", "")
            for e in events if e.event_type == "exit"
        ).items())),
        "trade_ids": sorted({e.trade_id for e in events}),
    }


def run_live_strategy_deltas():
    bt = Backtester(starting_capital=10_000.0)
    manifest = {}
    for strategy, (symbol, asset_class, timeframe, days) in LIVE_CASES.items():
        profiles = {}
        for profile in (BEHAVIOR_ISOLATED_V1, BEHAVIOR_LIVE_PARITY_V2):
            ledger = RunLedger(f"p1a-{strategy}-{profile}")
            result = bt.run_strategy(
                symbol=symbol,
                strategy_name=strategy,
                days=days,
                timeframe=timeframe,
                asset_class=asset_class,
                behavior_profile=profile,
                ledger=ledger,
            )
            if result is None:
                raise AssertionError(
                    f"real-strategy replay failed: {strategy}/{symbol}/{timeframe}/{profile}"
                )
            profiles[profile] = {
                "total_trades": result.total_trades,
                "ending_capital": result.ending_capital,
                "total_return_pct": result.total_return_pct,
                **_event_summary(ledger),
            }
        manifest[strategy] = {
            "symbol": symbol,
            "asset_class": asset_class,
            "timeframe": timeframe,
            "days": days,
            "profiles": profiles,
            "changed": profiles[BEHAVIOR_ISOLATED_V1] != profiles[BEHAVIOR_LIVE_PARITY_V2],
        }
    if set(manifest) != set(LIVE_CASES):
        raise AssertionError("live-strategy delta manifest is incomplete")
    return manifest


if __name__ == "__main__":
    output = run_live_strategy_deltas()
    print(json.dumps(output, indent=2, sort_keys=True))
    print(f"PASS: real classes/profile ledgers captured for {len(output)} live strategies")
