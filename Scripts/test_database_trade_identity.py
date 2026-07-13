"""Deterministic tests for non-destructive trade-open identity handling."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database


def _trade(**changes):
    value = {
        "trade_id": "IDENTITY-1", "symbol": "BTC/USD", "asset_class": "crypto",
        "direction": "long", "entry_time": "2026-07-12T12:00:00",
        "entry_price": 100.0, "quantity": 2.0, "position_value": 200.0,
        "stop_loss": 95.0, "take_profit": 110.0, "signal_score": 0.9,
        "indicators": {}, "broker": "kraken", "broker_order_id": "ORDER-1",
        "strategy_name": "test", "entry_timeframe": "5m",
    }
    value.update(changes)
    return value


def _row(database):
    with database._conn() as conn:
        return dict(conn.execute(
            "SELECT * FROM trades WHERE trade_id='IDENTITY-1'"
        ).fetchone())


def run():
    path = os.path.join(tempfile.gettempdir(), f"trade_identity_{os.getpid()}.db")
    for suffix in ("", "-shm", "-wal"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass
    try:
        database = Database(path)
        assert database.open_trade(_trade())["status"] == "inserted"
        assert _row(database)["broker_order_id"] == "ORDER-1"
        assert database.open_trade(_trade())["status"] == "idempotent"
        assert database.open_trade(_trade(broker_order_id="ORDER-2"))["status"] == "conflict"
        assert database.open_trade(_trade(entry_price=101.0))["status"] == "conflict"

        database.record_partial_exit(
            "IDENTITY-1", "BTC/USD", 105.0, 0.5, 52.5, 2.5, 5.0
        )
        before = _row(database)
        assert database.open_trade(_trade())["status"] == "existing_processed"
        after = _row(database)
        assert after["quantity"] == before["quantity"] == 1.5
        assert after["partial_exit_count"] == before["partial_exit_count"] == 1

        database.close_trade("IDENTITY-1", 110.0, "test", 15.0, 7.5)
        before = _row(database)
        assert database.open_trade(_trade())["status"] == "existing_processed"
        after = _row(database)
        assert after["status"] == "closed"
        assert after["exit_price"] == before["exit_price"] == 110.0
        assert after["pnl"] == before["pnl"]

        null_trade = _trade(trade_id="IDENTITY-NULL", broker_order_id=None)
        assert database.open_trade(null_trade)["status"] == "inserted"
        assert database.open_trade(null_trade)["status"] == "idempotent"
        assert database.open_trade({**null_trade, "broker_order_id": "LATE-ID"})["status"] == "conflict"
        print("8/8 database trade identity checks passed")
    finally:
        for suffix in ("", "-shm", "-wal"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    run()
