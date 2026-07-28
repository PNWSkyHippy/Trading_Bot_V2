"""
fix_trade.py — Correct a closed trade's exit price (e.g. a bad-tick/phantom fill)
and recompute all dependent financial state, WITHOUT removing the trade.

Usage:
  python Scripts/fix_trade.py                  -- list last 50 closed trades
  python Scripts/fix_trade.py -n 100            -- list last 100 closed trades
  python Scripts/fix_trade.py --symbol ISRG     -- filter by symbol

The script will:
  1. Show a numbered list of closed trades
  2. Ask which trade to fix
  3. Ask for the corrected exit price (and optionally exit_reason)
  4. Recompute pnl / pnl_pct / fees_paid for that trade using the same
     formula as core/trade_executor.py's close_trade()
  5. Show a preview of every table/column that will change (trades,
     capital, session_state, daily_summaries, tax_ledger, strategy_results)
  6. Ask for confirmation, then apply the delta (not a full recompute of
     other rows) so unrelated trades are untouched
"""

import argparse
import os
import sqlite3
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trading_bot.db')


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_closed_trades(conn, n, symbol=None):
    c = conn.cursor()
    if symbol:
        c.execute(
            'SELECT * FROM trades WHERE status=? AND symbol=? ORDER BY exit_time DESC LIMIT ?',
            ('closed', symbol, n)
        )
    else:
        c.execute(
            'SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC LIMIT ?',
            ('closed', n)
        )
    return [dict(r) for r in c.fetchall()]


def print_table(trades):
    print(f"\n{'#':>3}  {'ID':>5}  {'Symbol':<10}  {'Dir':<6}  "
          f"{'Entry':>10}  {'Exit':>10}  {'PNL':>9}  {'PNL%':>7}  {'Exit Reason':<16}  {'Exit Time'}")
    print('-' * 130)
    for i, t in enumerate(trades, 1):
        pnl = t.get('pnl') or 0
        sign = '+' if pnl >= 0 else ''
        print(f"{i:>3}  {t['id']:>5}  {(t['symbol'] or '?'):<10}  "
              f"{(t['direction'] or '?').upper():<6}  "
              f"{(t['entry_price'] or 0):>10.4f}  "
              f"{(t['exit_price'] or 0):>10.4f}  "
              f"{sign}{pnl:>8.2f}  "
              f"{(t.get('pnl_pct') or 0):>6.2f}%  "
              f"{(t.get('exit_reason') or ''):<16}  "
              f"{t.get('exit_time') or ''}")


def compute_financials(trade, new_exit_price):
    """Mirror core/trade_executor.py close_trade()'s pnl/pnl_pct/fees_paid formula."""
    entry_price = float(trade['entry_price'])
    qty = float(trade['quantity'])
    direction = trade['direction']
    asset_class = trade.get('asset_class') or 'stock'

    if direction == 'long':
        pnl = (new_exit_price - entry_price) * qty
    else:
        pnl = (entry_price - new_exit_price) * qty

    if asset_class == 'crypto':
        fee_rt_pct = (config.BT_COMMISSION_CRYPTO_PCT + config.BT_SLIPPAGE_CRYPTO_PCT) / 100 * 2
    else:
        fee_rt_pct = (config.BT_COMMISSION_STOCK_PCT + config.BT_SLIPPAGE_STOCK_PCT) / 100 * 2
    fees_paid = round(entry_price * qty * fee_rt_pct, 4)
    pnl = pnl - fees_paid

    if entry_price > 0:
        raw_move_pct = ((new_exit_price - entry_price) / entry_price) * 100
        pnl_pct = raw_move_pct if direction == 'long' else -raw_move_pct
    else:
        pnl_pct = 0

    return round(pnl, 4), round(pnl_pct, 4), fees_paid


def fix_trade(conn, trade, new_exit_price, new_exit_reason, dry_run=False):
    """Recompute financials for one trade and adjust all dependent tables/rows."""
    c = conn.cursor()
    trade_id = trade['trade_id']
    db_id = trade['id']
    symbol = trade['symbol']
    old_pnl = float(trade.get('pnl') or 0)
    old_exit_reason = trade.get('exit_reason')

    new_pnl, new_pnl_pct, new_fees_paid = compute_financials(trade, new_exit_price)
    pnl_delta = new_pnl - old_pnl
    exit_reason = new_exit_reason or old_exit_reason

    time_field = 'exit_time'
    trade_dt_str = trade.get(time_field) or ''
    trade_date = trade_dt_str[:10] if trade_dt_str else date.today().isoformat()
    today = date.today().isoformat()

    changes = []
    changes.append(
        f"  UPDATE trades id={db_id} ({symbol}): "
        f"exit_price {trade['exit_price']:.4f} -> {new_exit_price:.4f}  |  "
        f"pnl {old_pnl:+.4f} -> {new_pnl:+.4f}  |  "
        f"pnl_pct {(trade.get('pnl_pct') or 0):+.2f}% -> {new_pnl_pct:+.2f}%  |  "
        f"fees_paid {(trade.get('fees_paid') or 0):.4f} -> {new_fees_paid:.4f}"
    )
    if exit_reason != old_exit_reason:
        changes.append(f"  UPDATE trades id={db_id}: exit_reason '{old_exit_reason}' -> '{exit_reason}'")

    # capital (latest row only, if pnl changed)
    cap = None
    if pnl_delta != 0:
        c.execute('SELECT timestamp, total_capital, daily_pnl, total_pnl FROM capital ORDER BY timestamp DESC LIMIT 1')
        cap = c.fetchone()
        if cap:
            changes.append(
                f"  UPDATE capital: total_capital {cap['total_capital']:.2f} -> {cap['total_capital']+pnl_delta:.2f}"
                f"  |  daily_pnl {cap['daily_pnl']:.2f} -> {cap['daily_pnl']+pnl_delta:.2f}"
                f"  |  total_pnl {cap['total_pnl']:.2f} -> {cap['total_pnl']+pnl_delta:.2f}"
            )

    # session_state (today only, if pnl changed)
    sess = None
    if pnl_delta != 0 and trade_date == today:
        c.execute('SELECT pnl_today FROM session_state WHERE session_date=?', (today,))
        sess = c.fetchone()
        if sess:
            changes.append(
                f"  UPDATE session_state: pnl_today {sess['pnl_today']:.2f} -> {sess['pnl_today']+pnl_delta:.2f}"
            )

    # daily_summaries (win/loss flip handled if sign changes)
    ds = None
    won_before = old_pnl > 0
    won_after = new_pnl > 0
    if pnl_delta != 0 or won_before != won_after:
        c.execute('SELECT * FROM daily_summaries WHERE trade_date=?', (trade_date,))
        ds = c.fetchone()
        if ds:
            new_wins = ds['winning_trades'] + (1 if won_after and not won_before else 0) - (1 if won_before and not won_after else 0)
            new_losses = ds['losing_trades'] + (1 if not won_after and won_before else 0) - (1 if not won_before and won_after else 0)
            new_wins = max(0, new_wins)
            new_losses = max(0, new_losses)
            new_daily_pnl = ds['daily_pnl'] + pnl_delta
            new_wr = round(new_wins / ds['total_trades'] * 100, 1) if ds['total_trades'] > 0 else 0
            changes.append(
                f"  UPDATE daily_summaries {trade_date}: "
                f"wins {ds['winning_trades']}->{new_wins}  losses {ds['losing_trades']}->{new_losses}  "
                f"pnl {ds['daily_pnl']:+.2f}->{new_daily_pnl:+.2f}  wr {ds['win_rate']:.1f}%->{new_wr:.1f}%"
            )
            if trade['symbol'] and (abs(old_pnl - ds['largest_win']) < 0.01 or abs(old_pnl - ds['largest_loss']) < 0.01):
                changes.append(
                    "  NOTE: this trade may be daily_summaries.largest_win/largest_loss for "
                    f"{trade_date} — that column is NOT auto-recomputed; check manually."
                )

    # tax_ledger
    tl = None
    c.execute('SELECT * FROM tax_ledger WHERE trade_id=?', (trade_id,))
    tl = c.fetchone()
    if tl:
        qty = float(trade['quantity'])
        new_proceeds = round(new_exit_price * qty, 4)
        new_gain_loss = round(new_proceeds - tl['cost_basis'] - new_fees_paid, 4)
        changes.append(
            f"  UPDATE tax_ledger id={tl['id']}: proceeds {tl['proceeds']:.2f}->{new_proceeds:.2f}  "
            f"fees_paid {tl['fees_paid']:.4f}->{new_fees_paid:.4f}  "
            f"gain_loss {tl['gain_loss']:+.2f}->{new_gain_loss:+.2f}"
        )

    # strategy_results (matched by old pnl, same logic as remove_trade.py)
    sr = None
    strategy = trade.get('strategy_name') or ''
    if strategy and strategy not in ('original', 'manual'):
        c.execute('SELECT id, pnl, won FROM strategy_results WHERE strategy_name=? AND trade_date=? AND ABS(pnl-?)<?',
                  (strategy, trade_date, old_pnl, 0.01))
        sr = c.fetchone()
        if sr:
            changes.append(
                f"  UPDATE strategy_results id={sr['id']}: pnl {sr['pnl']:+.2f}->{new_pnl:+.2f}  "
                f"won {sr['won']}->{1 if won_after else 0}"
            )

    if dry_run:
        return changes

    # ── Apply changes ──────────────────────────────────────────────────────

    c.execute(
        'UPDATE trades SET exit_price=?, pnl=?, pnl_pct=?, fees_paid=?, exit_reason=? WHERE id=?',
        (new_exit_price, new_pnl, new_pnl_pct, new_fees_paid, exit_reason, db_id)
    )

    if cap:
        c.execute(
            'UPDATE capital SET total_capital=total_capital+?, daily_pnl=daily_pnl+?, total_pnl=total_pnl+? '
            'WHERE timestamp=(SELECT MAX(timestamp) FROM capital)',
            (pnl_delta, pnl_delta, pnl_delta)
        )

    if sess:
        c.execute(
            'UPDATE session_state SET pnl_today=pnl_today+? WHERE session_date=?',
            (pnl_delta, today)
        )

    if ds:
        new_wins = max(0, ds['winning_trades'] + (1 if won_after and not won_before else 0) - (1 if won_before and not won_after else 0))
        new_losses = max(0, ds['losing_trades'] + (1 if not won_after and won_before else 0) - (1 if not won_before and won_after else 0))
        c.execute(
            'UPDATE daily_summaries SET winning_trades=?, losing_trades=?, daily_pnl=daily_pnl+?, '
            'win_rate=CASE WHEN total_trades>0 THEN ROUND(?*100.0/total_trades,1) ELSE 0 END '
            'WHERE trade_date=?',
            (new_wins, new_losses, pnl_delta, new_wins, trade_date)
        )

    if tl:
        qty = float(trade['quantity'])
        new_proceeds = round(new_exit_price * qty, 4)
        new_gain_loss = round(new_proceeds - tl['cost_basis'] - new_fees_paid, 4)
        c.execute(
            'UPDATE tax_ledger SET proceeds=?, fees_paid=?, gain_loss=? WHERE id=?',
            (new_proceeds, new_fees_paid, new_gain_loss, tl['id'])
        )

    if sr:
        c.execute(
            'UPDATE strategy_results SET pnl=?, won=? WHERE id=?',
            (new_pnl, 1 if won_after else 0, sr['id'])
        )

    conn.commit()
    return changes


def main():
    parser = argparse.ArgumentParser(description='Correct a closed trade exit price and recompute all financial state.')
    parser.add_argument('-n', type=int, default=50, help='Number of trades to list (default 50)')
    parser.add_argument('--symbol', type=str, default=None, help='Filter by symbol')
    args = parser.parse_args()

    conn = connect()
    trades = get_closed_trades(conn, args.n, args.symbol)
    if not trades:
        print('No closed trades found.')
        conn.close()
        return

    print(f'\nLast {len(trades)} closed trades:')
    print_table(trades)

    print()
    selection = input('Enter trade number to fix, or q to quit: ').strip()
    if selection.lower() == 'q' or not selection:
        print('Cancelled.')
        conn.close()
        return

    try:
        idx = int(selection.strip()) - 1
    except ValueError:
        print('Invalid selection.')
        conn.close()
        return

    if not (0 <= idx < len(trades)):
        print('Index out of range.')
        conn.close()
        return

    trade = trades[idx]
    print(f"\nSelected: [{trade['id']}] {trade['symbol']} {(trade['direction'] or '').upper()} "
          f"entry={trade['entry_price']:.4f} exit={trade['exit_price']:.4f} "
          f"pnl={float(trade.get('pnl') or 0):+.2f} reason={trade.get('exit_reason')}")

    new_exit_raw = input('Enter corrected exit price: ').strip()
    try:
        new_exit_price = float(new_exit_raw)
    except ValueError:
        print('Invalid price.')
        conn.close()
        return

    new_exit_reason = input(f"Exit reason [{trade.get('exit_reason')}] (blank = keep): ").strip()

    changes = fix_trade(conn, trade, new_exit_price, new_exit_reason, dry_run=True)
    print(f'\nPreview — changes for trade [{trade["id"]}] {trade["symbol"]}:')
    for ch in changes:
        print(ch)

    print()
    confirm = input('Apply these changes? (yes/no): ').strip().lower()
    if confirm != 'yes':
        print('Cancelled — nothing changed.')
        conn.close()
        return

    changes = fix_trade(conn, trade, new_exit_price, new_exit_reason, dry_run=False)
    print(f'\nDone. Trade [{trade["id"]}] {trade["symbol"]} corrected and all tables adjusted:')
    for ch in changes:
        print(ch)

    conn.close()


if __name__ == '__main__':
    main()
