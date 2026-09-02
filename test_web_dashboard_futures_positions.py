import json
import unittest
from pathlib import Path
from unittest.mock import patch

import web_dashboard


def futures_trade(strategy="eat", direction="long"):
    return {
        "id": 42,
        "trade_id": f"{strategy.upper()}-PAPER-TEST",
        "symbol": "MNQU6" if strategy == "eat" else "NQU6",
        "asset_class": "future",
        "direction": direction,
        "entry_price": 100.0,
        "current_price": 100.0,
        "quantity": 10.0 if strategy == "eat" else 2.0,
        "position_value": 500.0,
        "stop_loss": 95.0,
        "take_profit": 105.0,
        "strategy_name": strategy,
        "broker": f"paper_{strategy}",
        "indicators_json": json.dumps({
            "root_symbol": "MNQ" if strategy == "eat" else "NQ",
            "point_value": 2.0 if strategy == "eat" else 20.0,
        }),
        "unrealized_pnl": 0.0,
        "pnl_pct": 0.0,
    }


def strategy_status(snapshot, strategy, symbol):
    return {
        "ok": snapshot.get("ok", False),
        "bridge": snapshot.get("bridge", {}),
        "strategies": {
            strategy: {
                "state": (snapshot.get(f"{strategy}_strategies") or {}).get(
                    symbol, {}
                )
            }
        },
    }


class FakeMonitor:
    def __init__(self, rows):
        self.rows = rows

    def get_positions_summary(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def get_open_trades(self):
        return self.rows


class FuturesPositionValuationTests(unittest.TestCase):
    def test_eat_uses_exact_live_mark_remaining_quantity_and_point_value(self):
        trade = futures_trade("eat", "long")
        snapshot = {
            "ok": True,
            "bridge": {"alive": True},
            "eat_strategies": {
                "MNQ": {
                    "active_trade": {
                        "trade_id": trade["trade_id"],
                        "quantity": 10,
                        "remaining_quantity": 4,
                        "realized_pnl": 60.0,
                        "tp1_done": True,
                        "runner_stop": 101.5,
                    },
                    "last_live_price": 103.0,
                }
            },
        }
        with (
            patch.object(web_dashboard, "monitor", FakeMonitor([trade])),
            patch.object(
                web_dashboard,
                "_scanner_strategy_status",
                return_value=strategy_status(snapshot, "eat", "MNQ"),
            ),
        ):
            [position] = web_dashboard.get_open_positions()

        self.assertEqual(position["qty"], 4.0)
        self.assertEqual(position["current_price"], 103.0)
        self.assertEqual(position["unrealized_pnl"], 24.0)
        self.assertEqual(position["pnl_pct"], 4.8)
        self.assertEqual(position["realized_pnl"], 60.0)
        self.assertEqual(position["combined_pnl"], 84.0)
        self.assertEqual(position["stop_loss"], 101.5)
        self.assertEqual(position["contracts_open"], 4.0)
        self.assertEqual(position["contracts_initial"], 10.0)
        self.assertEqual(position["position_status"], "runner")
        self.assertEqual(position["take_profit_status"], "tp1_filled_runner")
        self.assertEqual(position["mark_status"], "live")
        self.assertEqual(position["mark_source"], "eat_scanner")

    def test_emt_short_uses_futures_point_value(self):
        trade = futures_trade("emt", "short")
        snapshot = {
            "ok": True,
            "bridge": {"alive": True},
            "emt_strategies": {
                "NQ": {
                    "active_trade": {
                        "trade_id": trade["trade_id"],
                        "quantity": 2,
                    },
                    "last_live_price": 98.5,
                }
            },
        }
        with (
            patch.object(web_dashboard, "monitor", FakeMonitor([trade])),
            patch.object(
                web_dashboard,
                "_scanner_strategy_status",
                return_value=strategy_status(snapshot, "emt", "NQ"),
            ),
        ):
            [position] = web_dashboard.get_open_positions()

        self.assertEqual(position["current_price"], 98.5)
        self.assertEqual(position["unrealized_pnl"], 60.0)
        self.assertEqual(position["pnl_pct"], 12.0)

    def test_trade_id_mismatch_never_applies_another_trade_mark(self):
        trade = futures_trade("eat", "long")
        snapshot = {
            "ok": True,
            "bridge": {"alive": True},
            "eat_strategies": {
                "MNQ": {
                    "active_trade": {"trade_id": "EAT-PAPER-OTHER"},
                    "last_live_price": 150.0,
                }
            },
        }
        with (
            patch.object(web_dashboard, "monitor", FakeMonitor([trade])),
            patch.object(
                web_dashboard,
                "_scanner_strategy_status",
                return_value=strategy_status(snapshot, "eat", "MNQ"),
            ),
        ):
            [position] = web_dashboard.get_open_positions()

        self.assertEqual(position["current_price"], 100.0)
        self.assertEqual(position["unrealized_pnl"], 0.0)
        self.assertEqual(position["mark_status"], "unavailable")
        self.assertEqual(position["mark_source"], "scanner_trade_mismatch")

    def test_zero_remaining_exact_trade_is_unavailable_and_exposes_zero_contracts(self):
        trade = futures_trade("eat", "long")
        snapshot = {
            "ok": True,
            "bridge": {"alive": True},
            "eat_strategies": {
                "MNQ": {
                    "active_trade": {
                        "trade_id": trade["trade_id"],
                        "quantity": 10,
                        "remaining_quantity": 0,
                        "realized_pnl": 60.0,
                        "tp1_done": True,
                    },
                    "last_live_price": 103.0,
                }
            },
        }
        [position] = web_dashboard._enrich_futures_strategy_positions(
            [trade], snapshot=snapshot
        )

        self.assertEqual(position["quantity"], 0.0)
        self.assertEqual(position["contracts_open"], 0.0)
        self.assertEqual(position["contracts_initial"], 10.0)
        self.assertEqual(position["unrealized_pnl"], 0.0)
        self.assertEqual(position["realized_pnl"], 60.0)
        self.assertEqual(position["combined_pnl"], 60.0)
        self.assertEqual(position["mark_status"], "unavailable")
        self.assertEqual(position["mark_source"], "zero_remaining_reconciliation")
        self.assertEqual(position["position_status"], "reconciling")

    def test_dead_bridge_labels_last_strategy_mark_stale(self):
        trade = futures_trade("eat", "long")
        snapshot = {
            "ok": True,
            "bridge": {"alive": False},
            "eat_strategies": {
                "MNQ": {
                    "active_trade": {"trade_id": trade["trade_id"]},
                    "last_live_price": 101.0,
                }
            },
        }
        [position] = web_dashboard._enrich_futures_strategy_positions(
            [trade], snapshot=snapshot
        )
        self.assertEqual(position["current_price"], 101.0)
        self.assertEqual(position["mark_status"], "stale")

    def test_db_fallback_keeps_contract_correct_futures_pnl(self):
        trade = futures_trade("emt", "short")
        snapshot = {
            "ok": True,
            "bridge": {"alive": True},
            "emt_strategies": {
                "NQ": {
                    "active_trade": {
                        "trade_id": trade["trade_id"],
                        "quantity": 2,
                    },
                    "last_live_price": 99.0,
                }
            },
        }
        with (
            patch.object(web_dashboard, "monitor", None),
            patch.object(web_dashboard, "db", FakeDB([trade])),
            patch.object(
                web_dashboard,
                "_scanner_strategy_status",
                return_value=strategy_status(snapshot, "emt", "NQ"),
            ),
            patch.object(web_dashboard, "get_current_price") as stock_price,
        ):
            [position] = web_dashboard.get_open_positions()

        self.assertEqual(position["current_price"], 99.0)
        self.assertEqual(position["unrealized_pnl"], 40.0)
        self.assertEqual(position["pnl_pct"], 8.0)
        stock_price.assert_not_called()

    def test_both_position_panels_render_runner_and_mark_status(self):
        root = Path(__file__).resolve().parent / "Html-Files"
        open_panel = (root / "panels.jsx").read_text(encoding="utf-8")
        manage_panel = (root / "side-panels.jsx").read_text(encoding="utf-8")
        for source in (open_panel, manage_panel):
            self.assertIn("position_status", source)
            self.assertIn("contracts_open", source)
            self.assertIn("mark_status", source)
            self.assertIn("RUNNER", source)
            self.assertIn("TP1 FILLED", source)
            self.assertIn("realizedPnl", source)
        self.assertIn("zeroExposureFuture", manage_panel)
        self.assertIn("!zeroExposureFuture(p)", manage_panel)
        self.assertIn("No contracts remain; awaiting reconciliation.", manage_panel)


if __name__ == "__main__":
    unittest.main()
