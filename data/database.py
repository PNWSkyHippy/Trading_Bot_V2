"""
=============================================================
  DATABASE LAYER
  Manages all persistent storage: trades, capital, tax records,
  daily summaries, withdrawal history, strategy results,
  fund events, broker balance tracking, and Claude chat actions.
=============================================================
"""

import sqlite3
import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import config

logger = logging.getLogger(__name__)


class Database:
    """Central database manager using SQLite (local, no server needed)."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB error: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Create all tables if they don't exist."""
        with self._conn() as conn:
            conn.executescript("""
                -- Capital tracking
                CREATE TABLE IF NOT EXISTS capital (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    total_capital   REAL NOT NULL,
                    available_cash  REAL NOT NULL,
                    invested_value  REAL NOT NULL,
                    daily_pnl       REAL DEFAULT 0,
                    total_pnl       REAL DEFAULT 0,
                    note            TEXT
                );

                -- Every trade ever taken
                CREATE TABLE IF NOT EXISTS trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id        TEXT UNIQUE NOT NULL,
                    symbol          TEXT NOT NULL,
                    asset_class     TEXT NOT NULL,
                    direction       TEXT NOT NULL,
                    status          TEXT NOT NULL,
                    entry_time      TEXT,
                    exit_time       TEXT,
                    entry_price     REAL,
                    exit_price      REAL,
                    quantity        REAL NOT NULL,
                    position_value  REAL NOT NULL,
                    stop_loss       REAL,
                    take_profit     REAL,
                    pnl             REAL DEFAULT 0,
                    pnl_pct         REAL DEFAULT 0,
                    exit_reason     TEXT,
                    signal_score    REAL,
                    indicators_json TEXT,
                    broker          TEXT,
                    strategy_name   TEXT DEFAULT 'original',
                    is_overnight    INTEGER DEFAULT 0,
                    broker_order_id TEXT,
                    tp_hit_count    INTEGER DEFAULT 0
                );

                -- Daily session summaries
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date          TEXT UNIQUE NOT NULL,
                    starting_capital    REAL NOT NULL,
                    ending_capital      REAL NOT NULL,
                    daily_pnl           REAL NOT NULL,
                    daily_pnl_pct       REAL NOT NULL,
                    total_trades        INTEGER DEFAULT 0,
                    winning_trades      INTEGER DEFAULT 0,
                    losing_trades       INTEGER DEFAULT 0,
                    win_rate            REAL DEFAULT 0,
                    largest_win         REAL DEFAULT 0,
                    largest_loss        REAL DEFAULT 0,
                    trading_halted      INTEGER DEFAULT 0,
                    halt_reason         TEXT,
                    goal_met            INTEGER DEFAULT 0
                );

                -- Tax ledger (IRS Form 8949 compatible)
                CREATE TABLE IF NOT EXISTS tax_ledger (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id        TEXT NOT NULL,
                    symbol          TEXT NOT NULL,
                    open_date       TEXT NOT NULL,
                    close_date      TEXT NOT NULL,
                    proceeds        REAL NOT NULL,
                    cost_basis      REAL NOT NULL,
                    gain_loss       REAL NOT NULL,
                    hold_days       INTEGER NOT NULL,
                    term            TEXT NOT NULL,
                    tax_year        INTEGER NOT NULL
                );

                -- Withdrawal history
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    amount          REAL NOT NULL,
                    reason          TEXT,
                    capital_before  REAL NOT NULL,
                    capital_after   REAL NOT NULL
                );

                -- Bot state & settings (key-value store)
                CREATE TABLE IF NOT EXISTS bot_state (
                    key     TEXT PRIMARY KEY,
                    value   TEXT NOT NULL,
                    updated TEXT NOT NULL
                );

                -- Daily session tracking
                -- starting_capital_today: stored ONCE at market open each day,
                -- never recalculated on restart. This is the fix for the
                -- P&L percentage dropping after reboots.
                CREATE TABLE IF NOT EXISTS session_state (
                    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date            TEXT UNIQUE NOT NULL,
                    consecutive_losses      INTEGER DEFAULT 0,
                    trades_today            INTEGER DEFAULT 0,
                    pnl_today               REAL DEFAULT 0,
                    trading_halted          INTEGER DEFAULT 0,
                    halt_reason             TEXT,
                    starting_capital_today  REAL DEFAULT 0
                );

                -- Strategy performance tracking
                CREATE TABLE IF NOT EXISTS strategy_results (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name   TEXT NOT NULL,
                    trade_date      TEXT NOT NULL,
                    pnl             REAL NOT NULL,
                    won             INTEGER NOT NULL,
                    recorded_at     TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Fund injection / withdrawal tracking per broker
                CREATE TABLE IF NOT EXISTS fund_events (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    broker_name     TEXT NOT NULL,
                    event_type      TEXT NOT NULL,
                    amount          REAL NOT NULL,
                    reason          TEXT,
                    balance_before  REAL NOT NULL,
                    balance_after   REAL NOT NULL
                );

                -- Claude AI chat action log
                CREATE TABLE IF NOT EXISTS chat_actions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    action_date     TEXT NOT NULL,
                    user_message    TEXT,
                    action_type     TEXT NOT NULL,
                    action_detail   TEXT,
                    result          TEXT
                );
            """)

            # Safe migrations — add new columns to existing DBs
            migrations = [
                "ALTER TABLE trades ADD COLUMN strategy_name   TEXT    DEFAULT 'original'",
                "ALTER TABLE trades ADD COLUMN is_overnight    INTEGER DEFAULT 0",
                "ALTER TABLE trades ADD COLUMN broker_order_id TEXT",
                "ALTER TABLE trades ADD COLUMN tp_hit_count    INTEGER DEFAULT 0",
                # Fix for P&L restart bug — store starting capital explicitly
                "ALTER TABLE session_state ADD COLUMN starting_capital_today REAL DEFAULT 0",
            ]
            for sql in migrations:
                try:
                    conn.execute(sql)
                except Exception:
                    pass

        logger.info("Database initialized successfully.")

    # --- CAPITAL -------------------------------------------------------

    def log_capital(self, total: float, available: float, invested: float,
                    daily_pnl: float = 0, total_pnl: float = 0, note: str = ""):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO capital
                    (timestamp, total_capital, available_cash,
                     invested_value, daily_pnl, total_pnl, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (datetime.utcnow().isoformat(), total, available,
                  invested, daily_pnl, total_pnl, note))

    def record_capital_snapshot(self, total: float):
        self.log_capital(total=total, available=total, invested=0)

    def get_latest_capital(self) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM capital ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    # --- TRADES --------------------------------------------------------

    def open_trade(self, trade: Dict[str, Any]):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trades
                    (trade_id, symbol, asset_class, direction, status,
                     entry_time, entry_price, quantity, position_value,
                     stop_loss, take_profit, signal_score,
                     indicators_json, broker, strategy_name)
                VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade["trade_id"], trade["symbol"], trade["asset_class"],
                trade["direction"], trade["entry_time"], trade["entry_price"],
                trade["quantity"], trade["position_value"],
                trade["stop_loss"], trade["take_profit"],
                trade.get("signal_score"),
                json.dumps(trade.get("indicators", {})),
                trade.get("broker", "alpaca"),
                trade.get("strategy_name", "original")
            ))
        logger.info(f"Trade opened: {trade['symbol']} @ {trade['entry_price']}")

    def close_trade(self, trade_id: str, exit_price: float,
                    exit_reason: str, pnl: float, pnl_pct: float):
        with self._conn() as conn:
            conn.execute("""
                UPDATE trades SET
                    status      = 'closed',
                    exit_time   = ?,
                    exit_price  = ?,
                    exit_reason = ?,
                    pnl         = ?,
                    pnl_pct     = ?
                WHERE trade_id = ?
            """, (datetime.utcnow().isoformat(), exit_price, exit_reason,
                  pnl, pnl_pct, trade_id))

    def update_trade_order_ids(self, trade_id: str,
                               stop_order_id: str = None,
                               tp_order_id:   str = None):
        """Store broker order IDs for stop and TP orders."""
        sets, vals = [], []
        if stop_order_id is not None:
            sets.append("stop_order_id = ?"); vals.append(stop_order_id)
        if tp_order_id is not None:
            sets.append("tp_order_id = ?");   vals.append(tp_order_id)
        if not sets:
            return
        vals.append(trade_id)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE trades SET {', '.join(sets)} WHERE trade_id = ?", vals
            )

    def update_trade_levels(self, trade_id: str,
                             stop_loss: float = None,
                             take_profit: float = None):
        with self._conn() as conn:
            if stop_loss and take_profit:
                conn.execute(
                    "UPDATE trades SET stop_loss=?, take_profit=? WHERE trade_id=?",
                    (stop_loss, take_profit, trade_id)
                )
            elif stop_loss:
                conn.execute(
                    "UPDATE trades SET stop_loss=? WHERE trade_id=?",
                    (stop_loss, trade_id)
                )
            elif take_profit:
                conn.execute(
                    "UPDATE trades SET take_profit=? WHERE trade_id=?",
                    (take_profit, trade_id)
                )

    def get_open_trades(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='open'"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_trades_for_date(self, trade_date: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE date(entry_time)=? ORDER BY entry_time",
                (trade_date,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_closed_trades(self, limit: int = 500) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='closed' "
                "ORDER BY exit_time DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- SESSION STATE -------------------------------------------------

    def get_session(self, session_date: str = None) -> Dict:
        today = session_date or date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM session_state WHERE session_date=?", (today,)
            ).fetchone()
            if row:
                return dict(row)
            conn.execute(
                "INSERT INTO session_state (session_date) VALUES (?)", (today,)
            )
            return {
                "session_date":          today,
                "consecutive_losses":    0,
                "trades_today":          0,
                "pnl_today":             0.0,
                "trading_halted":        0,
                "halt_reason":           None,
                "starting_capital_today": 0.0,
            }

    def update_session(self, session_date: str, **kwargs):
        set_clause = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [session_date]
        with self._conn() as conn:
            conn.execute(
                f"UPDATE session_state SET {set_clause} WHERE session_date=?",
                values
            )

    def set_starting_capital_today(self, capital: float):
        """
        Store today's starting capital ONCE at the beginning of the trading day.
        This value never changes during the day regardless of restarts.
        Used by dashboard to calculate P&L% correctly after reboots.
        """
        today = date.today().isoformat()
        with self._conn() as conn:
            # Only set if not already set today (i.e. first run of the day)
            row = conn.execute(
                "SELECT starting_capital_today FROM session_state WHERE session_date=?",
                (today,)
            ).fetchone()
            if row and float(row["starting_capital_today"] or 0) > 0:
                logger.debug(
                    f"Starting capital already set for today: "
                    f"${row['starting_capital_today']:,.2f} — skipping"
                )
                return
            conn.execute(
                "UPDATE session_state SET starting_capital_today=? "
                "WHERE session_date=?",
                (capital, today)
            )
            logger.info(f"Starting capital locked for today: ${capital:,.2f}")

    def get_starting_capital_today(self) -> float:
        """
        Return today's locked starting capital.
        Returns 0.0 if not set yet (first run before market open).
        """
        today = date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT starting_capital_today FROM session_state "
                "WHERE session_date=?",
                (today,)
            ).fetchone()
            if row:
                return float(row["starting_capital_today"] or 0.0)
            return 0.0

    def reset_session_state(self):
        today = date.today().isoformat()
        self.update_session(today,
            trading_halted          = 0,
            halt_reason             = None,
            consecutive_losses      = 0,
            pnl_today               = 0.0,
            trades_today            = 0,
            starting_capital_today  = 0.0   # Reset for next day
        )

    # --- DAILY SUMMARY -------------------------------------------------

    def save_daily_summary(self, summary: Dict[str, Any]):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries
                    (trade_date, starting_capital, ending_capital, daily_pnl,
                     daily_pnl_pct, total_trades, winning_trades, losing_trades,
                     win_rate, largest_win, largest_loss, trading_halted,
                     halt_reason, goal_met)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary["trade_date"], summary["starting_capital"],
                summary["ending_capital"], summary["daily_pnl"],
                summary["daily_pnl_pct"], summary["total_trades"],
                summary["winning_trades"], summary["losing_trades"],
                summary["win_rate"], summary["largest_win"],
                summary["largest_loss"], summary.get("trading_halted", 0),
                summary.get("halt_reason"), summary.get("goal_met", 0)
            ))

    def get_daily_summaries(self, days: int = 30) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_summaries ORDER BY trade_date DESC LIMIT ?",
                (days,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- TAX LEDGER ----------------------------------------------------

    def record_tax_event(self, trade: Dict[str, Any]):
        if trade["status"] != "closed" or not trade.get("exit_time"):
            return
        open_dt   = datetime.fromisoformat(trade["entry_time"])
        close_dt  = datetime.fromisoformat(trade["exit_time"])
        hold_days = (close_dt - open_dt).days
        proceeds  = trade["exit_price"] * trade["quantity"]
        cost_basis= trade["entry_price"] * trade["quantity"]
        gain_loss = proceeds - cost_basis
        term      = "long" if hold_days >= 365 else "short"
        tax_year  = close_dt.year
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tax_ledger
                    (trade_id, symbol, open_date, close_date, proceeds,
                     cost_basis, gain_loss, hold_days, term, tax_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade["trade_id"], trade["symbol"],
                open_dt.date().isoformat(), close_dt.date().isoformat(),
                proceeds, cost_basis, gain_loss, hold_days, term, tax_year
            ))

    def get_tax_year_summary(self, year: int) -> Dict:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)                                               AS total_trades,
                    SUM(CASE WHEN term='short' THEN gain_loss ELSE 0 END) AS short_term_gains,
                    SUM(CASE WHEN term='long'  THEN gain_loss ELSE 0 END) AS long_term_gains,
                    SUM(gain_loss)                                         AS total_gains,
                    SUM(CASE WHEN gain_loss > 0 THEN gain_loss ELSE 0 END) AS gross_profits,
                    SUM(CASE WHEN gain_loss < 0 THEN gain_loss ELSE 0 END) AS gross_losses
                FROM tax_ledger WHERE tax_year=?
            """, (year,)).fetchone()
            return dict(row) if row else {}

    def export_8949_csv(self, year: int, filepath: str):
        import csv
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT symbol, open_date, close_date, proceeds,
                       cost_basis, gain_loss, term
                FROM tax_ledger WHERE tax_year=?
                ORDER BY close_date
            """, (year,)).fetchall()
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Description", "Date Acquired", "Date Sold",
                             "Proceeds", "Cost Basis", "Gain/Loss", "Term"])
            for r in rows:
                writer.writerow(list(r))
        logger.info(f"Form 8949 CSV exported: {filepath}")

    # --- WITHDRAWALS ---------------------------------------------------

    def record_withdrawal(self, amount: float, reason: str,
                           capital_before: float, capital_after: float):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO withdrawals
                    (timestamp, amount, reason, capital_before, capital_after)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.utcnow().isoformat(), amount, reason,
                  capital_before, capital_after))
        logger.info(f"Withdrawal recorded: ${amount:.2f}")

    # --- BOT STATE -----------------------------------------------------

    def set_state(self, key: str, value: Any):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO bot_state (key, value, updated)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.utcnow().isoformat()))

    def get_state(self, key: str, default=None) -> Any:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM bot_state WHERE key=?", (key,)
            ).fetchone()
            return json.loads(row["value"]) if row else default

    # --- STRATEGY TRACKING ---------------------------------------------

    def record_strategy_result(self, strategy_name: str, trade_date: str,
                                pnl: float, won: bool):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO strategy_results "
                "(strategy_name, trade_date, pnl, won) VALUES (?, ?, ?, ?)",
                (strategy_name, trade_date, pnl, int(won))
            )

    def get_strategy_results(self, strategy_name: str,
                              limit: int = 500) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT strategy_name, trade_date, pnl, won "
                "FROM strategy_results "
                "WHERE strategy_name = ? ORDER BY id DESC LIMIT ?",
                (strategy_name, limit)
            ).fetchall()
            return [
                {"strategy_name": r[0], "trade_date": r[1],
                 "pnl": r[2], "won": bool(r[3])}
                for r in rows
            ]

    # --- FUND EVENTS ---------------------------------------------------

    def record_fund_event(self, broker_name: str, event_type: str,
                           amount: float, reason: str,
                           balance_before: float, balance_after: float):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO fund_events
                    (timestamp, broker_name, event_type, amount, reason,
                     balance_before, balance_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (datetime.utcnow().isoformat(), broker_name, event_type,
                  amount, reason, balance_before, balance_after))
        logger.info(f"Fund event: {event_type} ${amount:.2f} @ {broker_name}")

    def get_fund_history(self, broker_name: str = None,
                          limit: int = 100) -> List[Dict]:
        with self._conn() as conn:
            if broker_name:
                rows = conn.execute(
                    "SELECT * FROM fund_events WHERE broker_name=? "
                    "ORDER BY id DESC LIMIT ?",
                    (broker_name, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM fund_events ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    # --- CLAUDE CHAT ACTION TRACKING -----------------------------------

    def log_chat_action(self, user_message: str, action_type: str,
                         action_detail: str = "", result: str = ""):
        today = date.today().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO chat_actions
                    (timestamp, action_date, user_message, action_type,
                     action_detail, result)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(), today,
                user_message[:200] if user_message else "",
                action_type, action_detail[:500] if action_detail else "",
                result[:200] if result else ""
            ))

    def get_chat_actions_for_date(self, action_date: str = None) -> List[Dict]:
        today = action_date or date.today().isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_actions WHERE action_date=? ORDER BY id",
                (today,)
            ).fetchall()
            return [dict(r) for r in rows]


# Singleton instance
db = Database()
