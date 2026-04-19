"""
=============================================================
  T+2 SETTLEMENT TRACKER
  Implements cash account settlement rules to avoid PDT.

  How it works:
  - Stock trade opens  → funds reserved from settled pool
  - Stock trade closes → funds enter T+2 settlement queue
  - 2 business days later → funds return to settled pool
  - Before any stock trade → check settled pool has enough

  Crypto trades are completely unaffected — separate pool.

  This lets the bot make unlimited stock day trades as long
  as it never reuses unsettled funds. This is legal cash
  account operation — no PDT rules apply.

  Config:
    CASH_ACCOUNT_MODE = True   (in config.py)
    SETTLEMENT_DAYS   = 2      (T+2 standard)
=============================================================
"""

import logging
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Number of business days for settlement
SETTLEMENT_DAYS = getattr(config, "SETTLEMENT_DAYS", 2)
CASH_ACCOUNT_MODE = getattr(config, "CASH_ACCOUNT_MODE", True)


def _add_business_days(from_date: date, days: int) -> date:
    """Add N business days to a date, skipping weekends."""
    current = from_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday=0, Friday=4
            added += 1
    return current


class SettlementTracker:
    """
    Tracks T+2 settlement for stock trades in cash account mode.
    Uses its own SQLite table separate from main trade records.
    """

    def __init__(self):
        self.db_path = config.DB_PATH
        self._init_table()
        if CASH_ACCOUNT_MODE:
            logger.info(
                f"Settlement tracker active — T+{SETTLEMENT_DAYS} cash account mode"
            )
        else:
            logger.info("Settlement tracker disabled — margin account mode")

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        """Create settlement_queue table if it doesn't exist."""
        conn = self._conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settlement_queue (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id            TEXT NOT NULL,
                    symbol              TEXT NOT NULL,
                    amount              REAL NOT NULL,
                    closed_date         TEXT NOT NULL,
                    settles_date        TEXT NOT NULL,
                    settled             INTEGER DEFAULT 0,
                    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ----------------------------------------------------------
    #  CORE METHODS
    # ----------------------------------------------------------

    def get_settled_capital(self) -> float:
        """
        Return the amount of stock capital available to trade right now.
        = Total stock capital - funds currently in settlement queue.
        """
        if not CASH_ACCOUNT_MODE:
            return config.STARTING_CAPITAL  # No restriction in margin mode

        total_stock_capital = self._get_total_stock_capital()
        settling = self._get_settling_amount()
        settled = max(0.0, total_stock_capital - settling)

        logger.debug(
            f"Settlement: total=${total_stock_capital:,.2f} | "
            f"settling=${settling:,.2f} | available=${settled:,.2f}"
        )
        return settled

    def can_open_trade(self, position_value: float) -> tuple:
        """
        Check if enough settled capital exists to open a stock trade.
        Returns (allowed: bool, reason: str, available: float)
        """
        if not CASH_ACCOUNT_MODE:
            return True, "Margin mode — no settlement restriction", 0.0

        available = self.get_settled_capital()
        if position_value > available:
            return (
                False,
                f"Insufficient settled capital: need ${position_value:,.2f} "
                f"but only ${available:,.2f} settled "
                f"(T+{SETTLEMENT_DAYS} cash account)",
                available
            )
        return True, "Settled capital available", available

    def record_trade_closed(self, trade_id: str, symbol: str,
                            position_value: float):
        """
        Record that a stock trade closed and its funds are now settling.
        Call this immediately when a stock position closes.
        """
        if not CASH_ACCOUNT_MODE:
            return

        today = date.today()
        settles = _add_business_days(today, SETTLEMENT_DAYS)

        conn = self._conn()
        try:
            conn.execute("""
                INSERT INTO settlement_queue
                    (trade_id, symbol, amount, closed_date, settles_date, settled)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (trade_id, symbol, position_value,
                  today.isoformat(), settles.isoformat()))
            conn.commit()
            logger.info(
                f"Settlement: ${position_value:,.2f} from {symbol} "
                f"settles on {settles.isoformat()} (T+{SETTLEMENT_DAYS})"
            )
        finally:
            conn.close()

    def process_settlements(self):
        """
        Mark funds as settled if their settlement date has passed.
        Call this daily at market open or on each capital sync.
        """
        if not CASH_ACCOUNT_MODE:
            return

        today = date.today().isoformat()
        conn = self._conn()
        try:
            # Find unsettled records whose settle date has passed
            rows = conn.execute("""
                SELECT id, symbol, amount, settles_date
                FROM settlement_queue
                WHERE settled = 0 AND settles_date <= ?
            """, (today,)).fetchall()

            for row in rows:
                conn.execute(
                    "UPDATE settlement_queue SET settled=1 WHERE id=?",
                    (row["id"],)
                )
                logger.info(
                    f"Settlement complete: ${row['amount']:,.2f} "
                    f"from {row['symbol']} is now available"
                )
            if rows:
                conn.commit()
                logger.info(f"Processed {len(rows)} settlements")
        finally:
            conn.close()

    def get_settlement_status(self) -> dict:
        """Return a summary of current settlement status."""
        conn = self._conn()
        try:
            # Unsettled amounts
            unsettled = conn.execute("""
                SELECT SUM(amount) as total, COUNT(*) as count
                FROM settlement_queue
                WHERE settled = 0
            """).fetchone()

            # Recently settled
            recently = conn.execute("""
                SELECT SUM(amount) as total, COUNT(*) as count
                FROM settlement_queue
                WHERE settled = 1
                AND date(settles_date) >= date('now', '-7 days')
            """).fetchone()

            # Upcoming settlements
            upcoming = conn.execute("""
                SELECT symbol, amount, settles_date
                FROM settlement_queue
                WHERE settled = 0
                ORDER BY settles_date ASC
                LIMIT 10
            """).fetchall()

            return {
                "mode":            "cash" if CASH_ACCOUNT_MODE else "margin",
                "settling_amount": unsettled["total"] or 0.0,
                "settling_count":  unsettled["count"] or 0,
                "settled_recently": recently["total"] or 0.0,
                "available_capital": self.get_settled_capital(),
                "upcoming": [
                    {
                        "symbol":       r["symbol"],
                        "amount":       r["amount"],
                        "settles_date": r["settles_date"]
                    }
                    for r in upcoming
                ]
            }
        finally:
            conn.close()

    # ----------------------------------------------------------
    #  INTERNAL HELPERS
    # ----------------------------------------------------------

    def _get_total_stock_capital(self) -> float:
        """Total capital allocated to stock trading."""
        # Use BOT_CAPITAL_ALLOCATION if set, else STARTING_CAPITAL
        allocation = getattr(config, "BOT_CAPITAL_ALLOCATION", 0)
        if allocation and allocation > 0:
            return allocation
        return config.STARTING_CAPITAL

    def _get_settling_amount(self) -> float:
        """Sum of all funds currently in the settlement queue."""
        conn = self._conn()
        try:
            row = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM settlement_queue
                WHERE settled = 0
            """).fetchone()
            return row["total"] or 0.0
        finally:
            conn.close()


# Singleton
settlement_tracker = SettlementTracker()
