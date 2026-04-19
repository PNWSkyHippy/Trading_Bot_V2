"""
=============================================================
  DATABASE ADDITIONS FOR STRATEGY TRACKING
  Add these methods to your existing data/database.py class.
  Also add the strategy_results table to your _create_tables()
  method.
=============================================================
"""

# ─────────────────────────────────────────────
#  ADD THIS TABLE to your _create_tables() method in database.py:
# ─────────────────────────────────────────────

CREATE_STRATEGY_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS strategy_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name   TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    pnl             REAL NOT NULL,
    won             INTEGER NOT NULL,
    recorded_at     TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# ─────────────────────────────────────────────
#  ADD THESE METHODS to your Database class in database.py:
# ─────────────────────────────────────────────

"""
def record_strategy_result(self, strategy_name: str, trade_date: str,
                           pnl: float, won: bool):
    self._execute(
        "INSERT INTO strategy_results (strategy_name, trade_date, pnl, won) VALUES (?, ?, ?, ?)",
        (strategy_name, trade_date, pnl, int(won))
    )

def get_strategy_results(self, strategy_name: str, limit: int = 500) -> list:
    rows = self._fetchall(
        "SELECT strategy_name, trade_date, pnl, won FROM strategy_results "
        "WHERE strategy_name = ? ORDER BY id DESC LIMIT ?",
        (strategy_name, limit)
    )
    return [{"strategy_name": r[0], "trade_date": r[1], "pnl": r[2], "won": bool(r[3])}
            for r in rows]
"""

# ─────────────────────────────────────────────
#  ADD 'strategy_name' COLUMN to your trades table:
# ─────────────────────────────────────────────

# In _create_tables(), after creating the trades table, add:
ALTER_TRADES_TABLE = """
ALTER TABLE trades ADD COLUMN strategy_name TEXT DEFAULT 'original';
"""
# Wrap in try/except since it will fail if column already exists:
# try:
#     self._execute(ALTER_TRADES_TABLE)
# except:
#     pass
