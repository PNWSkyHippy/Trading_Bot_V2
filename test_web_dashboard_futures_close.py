import json
import unittest
from unittest.mock import patch

import web_dashboard


def paper_trade():
    return {
        "id": 42,
        "trade_id": "EAT-PAPER-TEST",
        "symbol": "MNQU6",
        "asset_class": "future",
        "direction": "long",
        "entry_price": 100.0,
        "quantity": 2,
        "position_value": 100.0,
        "strategy_name": "eat",
        "broker": "paper_eat",
        "indicators_json": json.dumps({
            "root_symbol": "MNQ",
            "point_value": 2.0,
        }),
        "status": "open",
    }


class FakeDB:
    def __init__(self, trade):
        self.trade = dict(trade)
        self.close_calls = []

    def get_open_trades(self):
        return [self.trade] if self.trade["status"] == "open" else []

    def close_trade(self, trade_id, price, reason, pnl, pnl_pct):
        self.close_calls.append((trade_id, price, reason, pnl, pnl_pct))
        self.trade.update({
            "status": "closed",
            "exit_price": price,
            "exit_reason": reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    def get_trade(self, trade_id):
        return self.trade if self.trade["trade_id"] == trade_id else None


class FuturesPaperCloseTests(unittest.TestCase):
    def test_ninja_or_live_futures_are_not_classified_as_vps_paper(self):
        trade = paper_trade()
        trade["broker"] = "ninjatrader"
        self.assertIsNone(web_dashboard._paper_futures_identity(trade))
        trade["broker"] = "tradovate"
        self.assertIsNone(web_dashboard._paper_futures_identity(trade))

    def test_active_trade_closes_through_scanner_not_stock_executor(self):
        fake_db = FakeDB(paper_trade())
        scanner_result = {
            "ok": True,
            "trade": {
                "exit_price": 101.0,
                "realized_pnl": 4.0,
            },
        }

        def scanner_close_result(_payload):
            fake_db.trade["status"] = "closed"
            return scanner_result

        with (
            patch.object(web_dashboard, "db", fake_db),
            patch.object(
                web_dashboard,
                "_scanner_close_strategy_trade",
                side_effect=scanner_close_result,
            ) as scanner_close,
            patch.object(web_dashboard, "get_current_price") as stock_price,
        ):
            ok, message = web_dashboard.close_position("EAT-PAPER-TEST")

        self.assertTrue(ok)
        self.assertIn("Closed EAT MNQ paper trade", message)
        scanner_close.assert_called_once_with({
            "strategy": "eat",
            "symbol": "MNQ",
            "trade_id": "EAT-PAPER-TEST",
        })
        stock_price.assert_not_called()

    def test_confirmed_orphan_is_reconciled_in_central_db(self):
        fake_db = FakeDB(paper_trade())
        status = {
            "ok": True,
            "strategies": {
                "eat": {
                    "state": {
                        "active_trade": None,
                        "last_live_price": 101.0,
                    }
                }
            },
        }
        with (
            patch.object(web_dashboard, "db", fake_db),
            patch.object(
                web_dashboard,
                "_scanner_close_strategy_trade",
                return_value={
                    "ok": False,
                    "code": "trade_not_active",
                    "error": "not active",
                },
            ),
            patch.object(
                web_dashboard, "_scanner_strategy_status", return_value=status
            ),
        ):
            ok, message = web_dashboard.close_position("EAT-PAPER-TEST")

        self.assertTrue(ok)
        self.assertIn("Reconciled orphaned EAT MNQ", message)
        self.assertEqual(len(fake_db.close_calls), 1)
        self.assertEqual(fake_db.close_calls[0][2], "manual_orphan_reconcile")
        self.assertEqual(fake_db.close_calls[0][3], 4.0)

    def test_scanner_failure_never_marks_paper_trade_closed(self):
        fake_db = FakeDB(paper_trade())
        with (
            patch.object(web_dashboard, "db", fake_db),
            patch.object(
                web_dashboard,
                "_scanner_close_strategy_trade",
                return_value={
                    "ok": False,
                    "code": "scanner_unavailable",
                    "error": "connection refused",
                },
            ),
        ):
            ok, message = web_dashboard.close_position("EAT-PAPER-TEST")

        self.assertFalse(ok)
        self.assertEqual(message, "connection refused")
        self.assertEqual(fake_db.close_calls, [])
        self.assertEqual(fake_db.trade["status"], "open")


if __name__ == "__main__":
    unittest.main()
