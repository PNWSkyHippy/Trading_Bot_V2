"""
fix_ghost_pnl.py — Retroactively fix reconciled_ghost trades by looking up
actual Alpaca fill prices and updating P&L in the DB.

Usage:
  python Scripts/fix_ghost_pnl.py           -- preview changes
  python Scripts/fix_ghost_pnl.py --apply   -- apply changes to DB
"""
import sys, os, argparse, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trading_bot.db')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply changes to DB')
    parser.add_argument('--days', type=int, default=1, help='How many days back to look (default 1)')
    args = parser.parse_args()

    import config
    import alpaca_trade_api as tradeapi
    from datetime import datetime, timezone, timedelta

    api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime('%Y-%m-%dT00:00:00Z')
    print(f'Fetching Alpaca closed orders since {since}...')
    try:
        orders = api.list_orders(status='closed', after=since, limit=500)
    except Exception as e:
        print(f'ERROR fetching orders: {e}')
        return

    # Build fill map — most recent fill per symbol
    fills = {}
    for o in orders:
        if o.status != 'filled':
            continue
        qty = float(o.filled_qty or 0)
        price = float(o.filled_avg_price or 0)
        if qty <= 0 or price <= 0:
            continue
        sym = o.symbol
        filled_at = str(o.filled_at or '')
        if sym not in fills or filled_at > fills[sym]['filled_at']:
            fills[sym] = {'price': price, 'side': o.side, 'filled_at': filled_at, 'qty': qty}

    print(f'Found {len(fills)} symbols with Alpaca fills\n')

    # Get ghost trades from DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    date_cutoff = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    c.execute(
        'SELECT id, trade_id, symbol, direction, entry_price, quantity, position_value, exit_time, pnl '
        'FROM trades WHERE exit_reason=? AND exit_time >= ?',
        ('reconciled_ghost', date_cutoff)
    )
    ghosts = [dict(r) for r in c.fetchall()]
    print(f'Ghost trades to fix: {len(ghosts)}\n')

    fixed = 0
    skipped = 0
    for t in ghosts:
        sym = t['symbol']
        fill = fills.get(sym)
        if not fill:
            print(f'  SKIP {sym}: no Alpaca fill found')
            skipped += 1
            continue

        entry = float(t['entry_price'] or 0)
        qty = float(t['quantity'] or 0)
        direction = t['direction']
        exit_price = fill['price']

        if direction == 'long':
            pnl = (exit_price - entry) * qty
            pnl_pct = (exit_price / entry - 1) * 100 if entry else 0
        else:
            pnl = (entry - exit_price) * qty
            pnl_pct = (1 - exit_price / entry) * 100 if entry else 0

        print(f'  FIX  {sym} {direction}: entry=${entry:.4f} exit=${exit_price:.4f} '
              f'qty={qty:.2f} => P&L ${pnl:+.2f} ({pnl_pct:+.2f}%)')

        if args.apply:
            c.execute(
                'UPDATE trades SET exit_price=?, pnl=?, pnl_pct=?, exit_reason=? WHERE trade_id=?',
                (round(exit_price, 6), round(pnl, 4), round(pnl_pct, 4), 'bracket_fill', t['trade_id'])
            )
            fixed += 1

    if args.apply:
        conn.commit()
        print(f'\nApplied: {fixed} fixed, {skipped} skipped (no fill data).')
    else:
        print(f'\nDry run — {len(ghosts)-skipped} fixable, {skipped} no fill data. Add --apply to commit.')

    conn.close()

if __name__ == '__main__':
    main()
