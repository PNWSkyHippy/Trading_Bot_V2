import argparse
import copy
import csv
import os
import re
import sqlite3
import sys

DB_PATH = "c:/Users/Linda/trading_bot_v2/data/trading_bot.db"

def connect():
    """Open  up the database or quit if cant"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("SELECT 1 FROM trades LIMIT 1")
    except sqlite3.OperationalError as e:
        print(f"Database error: {DB_PATH}: {e}")
        sys.exit()
    return conn


def get_closed_trades(conn):
    """Read from he database using SQL"""
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC",
        ("closed",),
    )
    return [dict(r) for r in c.fetchall()]


def get_open_trades(conn):
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY entry_time DESC",
        ("open",),
    )
    return [dict(r) for r in c.fetchall()]



def query_trades(conn,query):
    print(f"Querying trades with sql query: {query}")
    c = conn.cursor()
    c.execute(query)
    return [dict(r) for r in c.fetchall()]


def main():

    def wide_formatter(prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    parser = argparse.ArgumentParser(
        description="List PnL based on search criteria",
        epilog="""\
Usage examples:
  trades_list.py -k strategy_name -1 emt
  trades_list.py -k strategy_name,symbol -1 emt -2 ESU6
  trades_list.py -k entry_price -1 ">=40000"
  trades_list.py -k strategy_name -1 ALL -o report.txt
  trades_list.py -N
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument(
        "-i",
        "--infile",
        metavar="",
        help="\tpath and name of database file",
    )

    parser.add_argument(
        "-op",
        "--open",
        action="store_true",
        help="List open trades instead of closed",
    )

    parser.add_argument(
        "-q",
        "--query",
        metavar="",
        help="\tquery trades using SQL query",
    )

    args = parser.parse_args()

    global DB_PATH
    mode = "open" if args.open else "closed"
    DB_PATH = args.infile if args.infile else DB_PATH
    db_query = args.query if args.query else None

    conn = connect()
    trades_list = {}
    if db_query:
        try:
            trades_list = query_trades(conn, db_query)
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
            conn.close()
#            sys.exit(1)
    else:
        try:
            trades_list = get_open_trades(conn) if mode == "open" else get_closed_trades(conn)
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
            conn.close()
#            sys.exit(1)

    if not trades_list:
        print("No closed trades found.") if (mode == "closed") else print(
            "No open trades found."
        )
    
        conn.close()

    print(f"Query: {db_query}")
    for trade in trades_list:
        print(trade)

if __name__ == "__main__":
    main()
