#!/usr/bin/env python3
"""
db_panel_tui.py
===============
Terminal DB Browser for trading_bot_v2.  No X11 / display needed.
Works over SSH on Ubuntu or any headless server.

Usage:  python db_panel_tui.py [--db /path/to/trading_bot.db]
Deps:   pip install rich   (falls back to plain text if missing)
"""
from __future__ import annotations
import argparse, sqlite3, sys, time
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "trading_bot.db"

# ── rich (optional) ───────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table  import Table
    from rich        import box as rbox
    RICH = True
    con  = Console()
except ImportError:
    RICH = False
    import re as _re
    class _Con:
        def print(self, *a, **kw):
            print(_re.sub(r'\[/?[^\]]*\]', '', " ".join(str(x) for x in a)))
        def rule(self, t=""):
            print("─" * 60 + (f"  {t}" if t else ""))
    con = _Con()  # type: ignore[assignment]

# ── quick queries ─────────────────────────────────────────────────────────────
QUICK = [
    ("Open Today", "trades",
     """SELECT trade_id,symbol,direction,status,strategy_name,
               entry_time,entry_price,stop_loss,take_profit,position_value,broker
        FROM trades WHERE status='open' AND DATE(entry_time)=DATE('now','localtime')
        ORDER BY entry_time DESC"""),

    ("Closed Today", "trades",
     """SELECT trade_id,symbol,direction,status,strategy_name,
               entry_time,exit_time,entry_price,exit_price,pnl,pnl_pct,exit_reason,broker
        FROM trades WHERE status='closed' AND DATE(exit_time)=DATE('now','localtime')
        ORDER BY exit_time DESC"""),

    ("All Open", "trades",
     """SELECT trade_id,symbol,direction,status,strategy_name,
               entry_time,entry_price,stop_loss,take_profit,position_value,broker
        FROM trades WHERE status='open' ORDER BY entry_time DESC"""),

    ("Ghost Trades", "trades",
     """SELECT trade_id,symbol,direction,status,strategy_name,entry_time,entry_price,
               position_value,broker,
               ROUND((julianday('now','localtime')-julianday(entry_time))*24,1) AS hours_open
        FROM trades WHERE status='open'
          AND entry_time < datetime('now','-8 hours','localtime')
        ORDER BY entry_time ASC"""),

    ("Capital Today", "capital",
     """SELECT timestamp,total_capital,available_cash,invested_value,daily_pnl,total_pnl,note
        FROM capital WHERE DATE(timestamp)=DATE('now','localtime')
        ORDER BY timestamp DESC"""),

    ("Settlement Queue", "settlement_queue",
     "SELECT * FROM settlement_queue ORDER BY rowid DESC LIMIT 300"),

    ("By Strategy", "trades",
     """SELECT trade_id,symbol,direction,status,strategy_name,entry_time,
               exit_time,entry_price,exit_price,pnl,broker
        FROM trades ORDER BY entry_time DESC LIMIT 500"""),

    ("Strategies", "_strategies",
     """SELECT replace(key,'strategy_','') AS strategy, UPPER(value) AS enabled
        FROM bot_state WHERE key LIKE 'strategy_%_enabled' ORDER BY strategy"""),

    ("Daily P&L", "daily_summaries",
     """SELECT trade_date,daily_pnl,daily_pnl_pct,total_trades,winning_trades,
               losing_trades,win_rate,largest_win,largest_loss,starting_capital,ending_capital
        FROM daily_summaries ORDER BY trade_date DESC LIMIT 60"""),

    ("Signal Reviews", "ai_signal_reviews",
     """SELECT timestamp,symbol,direction,strategy_name,reviewer,
               signal_score,decision,confidence,reasoning
        FROM ai_signal_reviews ORDER BY timestamp DESC LIMIT 200"""),

    ("Trend Filter", "ai_signal_reviews",
     """SELECT timestamp,symbol,direction,strategy_name,decision,
               confidence AS indicators_passed,reasoning
        FROM ai_signal_reviews WHERE reviewer='trend_confirm'
        ORDER BY timestamp DESC LIMIT 500"""),

    ("Yesterday Closed", "trades",
     """SELECT trade_id,symbol,direction,strategy_name,entry_time,exit_time,
               entry_price,exit_price,pnl,pnl_pct,exit_reason,broker
        FROM trades WHERE status='closed'
          AND DATE(exit_time)=DATE('now','-1 day','localtime')
        ORDER BY exit_time DESC"""),

    ("This Week Trades", "trades",
     """SELECT trade_id,symbol,direction,strategy_name,entry_time,exit_time,
               entry_price,exit_price,pnl,pnl_pct,exit_reason,broker
        FROM trades WHERE status='closed'
          AND DATE(exit_time)>=DATE('now','-7 days','localtime')
        ORDER BY exit_time DESC"""),

    ("Strategy P&L", "trades",
     """SELECT strategy_name, COUNT(*) AS trades,
               SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS losses,
               ROUND(100.0*SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS win_pct,
               ROUND(SUM(pnl),2) AS total_pnl,
               ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END),2) AS gross_wins,
               ROUND(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),2) AS gross_losses,
               ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)
                     /NULLIF(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),0),3) AS profit_factor
        FROM trades WHERE status='closed' GROUP BY strategy_name ORDER BY total_pnl DESC"""),

    ("Financials", "capital",
     """SELECT label,value,detail FROM
        (SELECT 'Total Capital' AS label,
                '$'||printf('%.2f',total_capital) AS value,
                'Cash: $'||printf('%.2f',available_cash)||
                '   Invested: $'||printf('%.2f',invested_value) AS detail
         FROM capital ORDER BY timestamp DESC LIMIT 1)
        UNION ALL SELECT label,value,detail FROM
        (SELECT 'Daily P&L (tracker)' AS label,
                (CASE WHEN daily_pnl>=0 THEN '+' ELSE '' END)||
                '$'||printf('%.2f',daily_pnl) AS value,
                'Cumulative: '||
                (CASE WHEN total_pnl>=0 THEN '+' ELSE '' END)||
                '$'||printf('%.2f',total_pnl) AS detail
         FROM capital ORDER BY timestamp DESC LIMIT 1)
        UNION ALL
        SELECT 'In Open Trades',
               '$'||printf('%.2f',COALESCE(SUM(position_value),0)),
               CAST(COUNT(*) AS TEXT)||' open positions'
        FROM trades WHERE status='open'
        UNION ALL
        SELECT 'In Settlement',
               '$'||printf('%.2f',COALESCE(SUM(amount),0)),
               CAST(COUNT(*) AS TEXT)||' unsettled items'
        FROM settlement_queue WHERE settled=0
        UNION ALL
        SELECT 'Today Closed P&L',
               (CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE ''END)||
               '$'||printf('%.2f',COALESCE(SUM(pnl),0)),
               CAST(COUNT(*) AS TEXT)||' trades  '||
               CAST(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS TEXT)||'W / '||
               CAST(SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS TEXT)||'L'
        FROM trades WHERE status='closed' AND DATE(exit_time)=DATE('now','localtime')
        UNION ALL
        SELECT 'Yesterday P&L',
               (CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE ''END)||
               '$'||printf('%.2f',COALESCE(SUM(pnl),0)),
               CAST(COUNT(*) AS TEXT)||' trades  '||
               CAST(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS TEXT)||'W / '||
               CAST(SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS TEXT)||'L'
        FROM trades WHERE status='closed'
          AND DATE(exit_time)=DATE('now','-1 day','localtime')
        UNION ALL
        SELECT 'This Week P&L',
               (CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE ''END)||
               '$'||printf('%.2f',COALESCE(SUM(pnl),0)),
               CAST(COUNT(*) AS TEXT)||' trades'
        FROM trades WHERE status='closed'
          AND DATE(exit_time)>=DATE('now','-7 days','localtime')
        UNION ALL
        SELECT 'This Month P&L',
               (CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE ''END)||
               '$'||printf('%.2f',COALESCE(SUM(pnl),0)),
               CAST(COUNT(*) AS TEXT)||' trades'
        FROM trades WHERE status='closed'
          AND strftime('%Y-%m',exit_time)=strftime('%Y-%m','now','localtime')"""),
]

# ── DB helpers ────────────────────────────────────────────────────────────────
def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=3000")
    c.row_factory = sqlite3.Row
    return c

def _run(sql: str, params=()):
    t0 = time.perf_counter()
    try:
        with _conn() as c:
            cur  = c.execute(sql, params)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
        ms = int((time.perf_counter() - t0) * 1000)
        return cols, [list(r) for r in rows], ms, None
    except Exception as e:
        return [], [], int((time.perf_counter() - t0) * 1000), str(e)

def _write(sql: str, params=()):
    with _conn() as c:
        c.execute(sql, params)
        c.commit()

def _tables():
    with _conn() as c:
        rows = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    return [r[0] for r in rows]

# ── display ───────────────────────────────────────────────────────────────────
_MAX_W = 28

def show_table(cols, rows, title="", ms=0):
    if not rows:
        con.print(f"[dim]{title}  — no rows  ({ms}ms)[/dim]")
        return
    if RICH:
        t = Table(
            title=f"[yellow]{title}[/yellow]  [dim]({len(rows):,} rows · {ms}ms)[/dim]",
            box=rbox.SIMPLE_HEAVY, header_style="bold cyan",
            show_lines=False, expand=False,
        )
        t.add_column("[dim]#[/dim]", width=4, justify="right", style="dim")
        for c in cols:
            t.add_column(c, max_width=_MAX_W, overflow="fold")
        for i, row in enumerate(rows, 1):
            vals = ["" if v is None else str(v) for v in row]
            t.add_row(str(i), *vals)
        con.print(t)
    else:
        print(f"\n{title}  ({len(rows)} rows  {ms}ms)")
        header = f"{'#':<4}  " + "  ".join(c[:_MAX_W] for c in cols)
        print(header[:160])
        print("-" * min(len(header), 160))
        for i, row in enumerate(rows, 1):
            vals = [("" if v is None else str(v))[:_MAX_W] for v in row]
            print(f"{i:<4}  " + "  ".join(vals))

def _inp(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"

# ── session state ─────────────────────────────────────────────────────────────
_st: dict = dict(cols=[], rows=[], table=None, view=None, sql=None, rowids=None)

# ── actions ───────────────────────────────────────────────────────────────────
def _lookup_rowid(table: str, cols: list, vals: list) -> Optional[int]:
    cm = dict(zip(cols, vals))
    for key in ("trade_id", "id", "key"):
        v = cm.get(key)
        if v:
            try:
                _, r2, _, _ = _run(
                    f"SELECT rowid FROM [{table}] WHERE [{key}]=? LIMIT 1", (v,)
                )
                if r2:
                    return r2[0][0]
            except Exception:
                pass
    return None

def action_edit(n: int):
    cols, rows, table = _st["cols"], _st["rows"], _st["table"]
    if not table or table.startswith("_"):
        print("Cannot edit: use 't' to browse a real table first.")
        return
    if not (1 <= n <= len(rows)):
        print(f"Row {n} out of range (1–{len(rows)}).")
        return
    row = rows[n - 1]

    # Resolve rowid: prefer stored rowids (from table browse), else look up by key col
    rowids = _st.get("rowids")
    rowid  = rowids[n - 1] if rowids else _lookup_rowid(table, cols, row)

    if rowid is None:
        print("Cannot find rowid. Browse the table directly with 't' to edit.")
        return

    print(f"\nEditing [{table}] rowid={rowid}")
    print("Press Enter to keep current value, or type a new value.")
    print()
    updates = {}
    for col, val in zip(cols, row):
        cur = "" if val is None else str(val)
        new = _inp(f"  {col} [{cur}]: ")
        if new and new != cur:
            updates[col] = new

    if not updates:
        print("No changes.")
        return

    print("\nChanges:")
    for k, v in updates.items():
        print(f"  {k} = {v!r}")
    if _inp("Save? [y/N]: ").lower() == "y":
        for col, val in updates.items():
            try:
                _write(f"UPDATE [{table}] SET [{col}]=? WHERE rowid=?", (val, rowid))
            except Exception as e:
                print(f"ERROR: {e}")
                return
        print("Saved.")
    else:
        print("Cancelled.")

def action_flush_ghost(n: int):
    cols, rows = _st["cols"], _st["rows"]
    if not (1 <= n <= len(rows)):
        print(f"Row {n} out of range.")
        return
    cm = dict(zip(cols, rows[n - 1]))
    trade_id    = cm.get("trade_id", "")
    symbol      = cm.get("symbol", "?")
    status      = cm.get("status", "")
    broker      = cm.get("broker", "")
    hours       = cm.get("hours_open", "")
    entry_price = cm.get("entry_price", "0")

    if status == "closed":
        print(f"{symbol} is already closed.")
        return

    print(f"\nFlush ghost trade:")
    print(f"  Symbol:     {symbol}")
    print(f"  Trade ID:   {trade_id}")
    print(f"  Broker:     {broker}")
    print(f"  Hours open: {hours}")
    print("\nThis marks it CLOSED in the DB (pnl=0). Does NOT cancel broker order.")
    if _inp("Confirm? [y/N]: ").lower() != "y":
        print("Cancelled.")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        _write(
            """UPDATE trades SET status='closed', exit_time=?, exit_price=?,
                   exit_reason='manual_flush_ghost', pnl=0, pnl_pct=0
               WHERE trade_id=?""",
            (now, entry_price, trade_id),
        )
        print(f"Flushed: {symbol} ({trade_id})")
    except Exception as e:
        print(f"ERROR: {e}")

def action_strategy(n: int, enable: bool):
    cols, rows = _st["cols"], _st["rows"]
    if not (1 <= n <= len(rows)):
        print(f"Row {n} out of range.")
        return
    cm  = dict(zip(cols, rows[n - 1]))
    strat = cm.get("strategy", "")
    key   = f"strategy_{strat}"
    if not key.endswith("_enabled"):
        print("Select a row from the Strategies view.")
        return
    name   = strat.replace("_enabled", "")
    action = "ENABLE" if enable else "DISABLE"
    if _inp(f"{action} strategy '{name}'? [y/N]: ").lower() != "y":
        print("Cancelled.")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        _write("UPDATE bot_state SET value=?, updated=? WHERE key=?",
               ("true" if enable else "false", now, key))
        print(f"{action}D: {name}  (bot picks up on next cycle)")
    except Exception as e:
        print(f"ERROR: {e}")

# ── result sub-loop ───────────────────────────────────────────────────────────
def result_loop():
    view  = _st.get("view", "")
    table = _st.get("table")
    is_trade    = table == "trades" or view in (
        "Open Today","Closed Today","All Open","Ghost Trades","By Strategy")
    is_strategy = view == "Strategies"

    hints = ["r=refresh", "m=menu"]
    if is_trade:
        hints = ["e <#>=edit", "f <#>=flush ghost"] + hints
    if is_strategy:
        hints = ["en <#>=enable", "dis <#>=disable"] + hints
    hint_str = "  ".join(hints)

    while True:
        con.print(f"\n  [dim]{hint_str}[/dim]")
        cmd = _inp("> ").lower()
        if cmd in ("m", "menu", "q", ""):
            return
        if cmd == "r":
            sql = _st.get("sql")
            if sql:
                cols, rows, ms, err = _run(sql)
                if err:
                    con.print(f"[red]{err}[/red]")
                else:
                    _st["cols"], _st["rows"] = cols, rows
                    show_table(cols, rows, _st.get("view", ""), ms)
            continue

        parts = cmd.split()
        if len(parts) == 2:
            verb, num_s = parts
            try:
                n = int(num_s)
            except ValueError:
                print(f"Expected a row number, got: {num_s!r}")
                continue
            if verb == "e":
                action_edit(n)
            elif verb == "f":
                action_flush_ghost(n)
            elif verb in ("en", "enable"):
                action_strategy(n, True)
            elif verb in ("dis", "disable"):
                action_strategy(n, False)
            else:
                print(f"Unknown command: {verb!r}")
        else:
            print("Unknown command. Type 'm' to return to the menu.")

# ── main menu ─────────────────────────────────────────────────────────────────
def show_menu():
    con.print(f"\n[bold yellow]DB PANEL[/bold yellow]  [dim]{DB_PATH}[/dim]")
    con.rule()
    mid = (len(QUICK) + 1) // 2
    for i in range(mid):
        left  = f"  {i+1:2}. {QUICK[i][0]:<22}"
        right = f"  {i+mid+1:2}. {QUICK[i+mid][0]}" if i + mid < len(QUICK) else ""
        con.print(left + right)
    con.print()
    con.print("   t  Browse table    s  Custom SQL    q  Quit")
    con.rule()

def run_quick(idx: int):
    label, table, sql = QUICK[idx]
    cols, rows, ms, err = _run(sql)
    if err:
        con.print(f"[red]ERROR: {err}[/red]")
        return
    _st.update(cols=cols, rows=rows,
               table=table if not table.startswith("_") else None,
               view=label, sql=sql, rowids=None)
    show_table(cols, rows, label, ms)
    result_loop()

def run_browse():
    tables = _tables()
    con.print("Tables: " + "  ".join(tables))
    name = _inp("Table: ")
    if name not in tables:
        print(f"Table '{name}' not found.")
        return
    sql  = f"SELECT rowid, * FROM [{name}] ORDER BY rowid DESC LIMIT 2000"
    cols, rows, ms, err = _run(sql)
    if err:
        con.print(f"[red]{err}[/red]")
        return
    if cols and cols[0] == "rowid":
        rowids = [r[0] for r in rows]
        dcols  = cols[1:]
        drows  = [r[1:] for r in rows]
    else:
        rowids, dcols, drows = None, cols, rows
    _st.update(cols=dcols, rows=drows, table=name, view=None, sql=sql, rowids=rowids)
    show_table(dcols, drows, name, ms)
    result_loop()

def run_sql():
    print("Enter SQL (blank line or ';' to run, 'cancel' to abort):")
    lines: list[str] = []
    while True:
        line = _inp("  sql> ")
        if line.lower() == "cancel":
            return
        lines.append(line)
        if not line or line.rstrip().endswith(";"):
            break
    sql = " ".join(lines).rstrip(";").strip()
    if not sql:
        return
    cols, rows, ms, err = _run(sql)
    if err:
        con.print(f"[red]{err}[/red]")
        return
    _st.update(cols=cols, rows=rows, table=None, view="Custom SQL", sql=sql, rowids=None)
    show_table(cols, rows, "Custom SQL", ms)
    result_loop()

# ── entry point ───────────────────────────────────────────────────────────────
def main():
    global DB_PATH
    ap = argparse.ArgumentParser(description="Terminal DB panel for trading_bot_v2")
    ap.add_argument("--db", default=str(DB_PATH),
                    help="Path to trading_bot.db (default: data/trading_bot.db beside this script)")
    args = ap.parse_args()
    DB_PATH = Path(args.db)

    if not DB_PATH.exists():
        print(f"ERROR: database not found: {DB_PATH}")
        sys.exit(1)

    if not RICH:
        print("Tip: pip install rich  for colour tables and better formatting\n")

    while True:
        show_menu()
        cmd = _inp("Choice: ").strip().lower()
        if cmd in ("q", "quit", "exit"):
            break
        if cmd == "t":
            run_browse()
        elif cmd == "s":
            run_sql()
        else:
            try:
                n = int(cmd)
                if 1 <= n <= len(QUICK):
                    run_quick(n - 1)
                else:
                    print(f"Enter 1–{len(QUICK)}, t, s, or q.")
            except ValueError:
                print("Unknown command.")

if __name__ == "__main__":
    main()
