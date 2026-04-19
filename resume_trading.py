"""
Flush a bad/stuck trade from the database.
Usage: python flush_trade.py
"""
from data.database import db
import sqlite3
import config
import datetime
#session_date= datetime.now().isoformat()
db.update_session("2026/05/25",
        trading_halted     = 0,
        halt_reason        = None,
        consecutive_losses = 0
    )



