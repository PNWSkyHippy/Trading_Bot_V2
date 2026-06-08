"""
reconcile_positions.py — Cross-reference DB open trades against actual broker positions.

Finds ghosts (DB open but broker has nothing) and orphans (broker has position but DB
doesn't know about it). For Alpaca paper/live. Kraken paper is local so it's always
reconciled. IBKR checked separately.

Usage:
  python Scripts/reconcile_positions.py           -- show mismatches, prompt to clean
  python Scripts/reconcile_positions.py --dry-run -- show only, no changes
  python Scripts/reconcile_positions.py --auto    -- clean all ghosts without prompting
"""

import argparse
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trading_bot.db')


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_alpaca_positions():
    """Return dict of symbol -> position info from Alpaca."""
    try:
        import config
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)
        positions = api.list_positions()
        return {p.symbol: p for p in positions}
    except Exception as e:
        print(f'  [ALPACA] Could not fetch positions: {e}')
        return None


def get_alpaca_orders():
    """Return set of symbols with open orders at Alpaca."""
    try:
        import config
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)
        orders = api.list_orders(status='open')
        return {o.symbol for o in orders}
    except Exception as e:
        print(f'  [ALPACA] Could not fetch orders: {e}')
        return set()


def get_db_open_trades(conn):
    c = conn.cursor()
    c.execute('SELECT * FROM trades WHERE status=? ORDER BY entry_time DESC', ('open',))
    return [dict(r) for r in c.fetchall()]


def normalize_symbol(symbol):
    """Alpaca uses SOLUSD, bot uses SOL/USD — strip the slash for comparison."""
    return symbol.replace('/', '').upper()


def remove_ghost(conn, trade):
    """Remove ghost trade from DB (no broker action needed — already confirmed not there)."""
    from Scripts.remove_trade import remove_trade
    changes = remove_trade(conn, trade, dry_run=False)
    return changes


def main():
    parser = argparse.ArgumentParser(description='Reconcile DB open trades vs broker positions.')
    parser.add_argument('--dry-run', action='store_true', help='Show mismatches only, no changes')
    parser.add_argument('--auto', action='store_true', help='Auto-remove all ghosts without prompting')
    args = parser.parse_args()

    conn = connect()
    db_trades = get_db_open_trades(conn)

    if not db_trades:
        print('No open trades in DB — nothing to reconcile.')
        conn.close()
        return

    print(f'\nDB has {len(db_trades)} open trade(s). Fetching broker positions...\n')

    # Split by broker
    alpaca_trades = [t for t in db_trades if 'alpaca' in (t.get('broker') or '').lower()]
    kraken_trades = [t for t in db_trades if 'kraken' in (t.get('broker') or '').lower()]
    ibkr_trades   = [t for t in db_trades if 'ibkr' in (t.get('broker') or '').lower()
                     or 'ib' in (t.get('broker') or '').lower()]
    other_trades  = [t for t in db_trades if t not in alpaca_trades + kraken_trades + ibkr_trades]

    ghosts   = []   # in DB, not at broker
    matched  = []   # in DB and at broker
    orphans  = []   # at broker, not in DB

    # ── ALPACA ────────────────────────────────────────────────────────────
    if alpaca_trades:
        print(f'Checking Alpaca ({len(alpaca_trades)} DB trades)...')
        alpaca_positions = get_alpaca_positions()
        open_orders = get_alpaca_orders()

        if alpaca_positions is None:
            print('  Could not connect to Alpaca — skipping Alpaca check.')
        else:
            alpaca_syms = {normalize_symbol(s): s for s in alpaca_positions.keys()}
            order_syms  = {normalize_symbol(s) for s in open_orders}

            for t in alpaca_trades:
                norm = normalize_symbol(t['symbol'])
                if norm in alpaca_syms:
                    pos = alpaca_positions[alpaca_syms[norm]]
                    matched.append((t, 'alpaca', pos))
                elif norm in order_syms:
                    # Order pending but not yet a position — not a ghost yet
                    matched.append((t, 'alpaca_pending_order', None))
                else:
                    ghosts.append((t, 'alpaca'))

            # Check for orphans — at Alpaca but not in DB
            db_norm_syms = {normalize_symbol(t['symbol']) for t in alpaca_trades}
            for sym, pos in alpaca_positions.items():
                if normalize_symbol(sym) not in db_norm_syms:
                    orphans.append(('alpaca', sym, pos))

    # ── KRAKEN ───────────────────────────────────────────────────────────
    if kraken_trades:
        print(f'Kraken: {len(kraken_trades)} DB trade(s) — paper mode (simulated locally, always matched).')
        for t in kraken_trades:
            matched.append((t, 'kraken', None))

    # ── IBKR ─────────────────────────────────────────────────────────────
    if ibkr_trades:
        print(f'IBKR: {len(ibkr_trades)} DB trade(s) — manual check required (connect to TWS).')
        for t in ibkr_trades:
            matched.append((t, 'ibkr_unverified', None))

    if other_trades:
        for t in other_trades:
            print(f'  Unknown broker: {t["symbol"]} broker={t.get("broker")} — skipping')

    # ── RESULTS ──────────────────────────────────────────────────────────
    print(f'\n{"="*60}')
    print(f'RECONCILIATION RESULTS')
    print(f'{"="*60}')
    print(f'  Matched (DB + broker):  {len(matched)}')
    print(f'  Ghosts  (DB only):      {len(ghosts)}')
    print(f'  Orphans (broker only):  {len(orphans)}')

    if matched:
        print(f'\nMATCHED ({len(matched)}):')
        for t, broker, pos in matched:
            broker_qty = f' | broker qty={float(pos.qty):.4f}' if pos else ''
            print(f'  [{t["id"]}] {t["symbol"]:<12} {broker:<20}{broker_qty}')

    if orphans:
        print(f'\nORPHANS -- at broker but NOT in DB ({len(orphans)}):')
        print('   These need manual investigation -- bot has no record of them.')
        for broker, sym, pos in orphans:
            print(f'  {sym:<12} broker={broker} qty={float(pos.qty):.4f} side={pos.side} '
                  f'avg_entry={float(pos.avg_entry_price):.4f}')

    if not ghosts:
        print('\nNo ghosts found -- DB and broker are in sync.')
        conn.close()
        return

    print(f'\nGHOSTS -- in DB but NOT at broker ({len(ghosts)}):')
    for t, broker in ghosts:
        age = ''
        if t.get('entry_time'):
            from datetime import datetime
            try:
                et = datetime.fromisoformat(t['entry_time'])
                hrs = (datetime.now() - et).total_seconds() / 3600
                age = f' | age={hrs:.1f}hr'
            except Exception:
                pass
        print(f'  [{t["id"]}] {t["symbol"]:<12} broker={broker} '
              f'strategy={t.get("strategy_name","?")} entry={t.get("entry_price",0):.4f}{age}')

    if args.dry_run:
        print('\n[dry-run] No changes made.')
        conn.close()
        return

    if args.auto:
        confirm = 'yes'
    else:
        print()
        confirm = input(f'Remove all {len(ghosts)} ghost(s) from DB? (yes/no): ').strip().lower()

    if confirm != 'yes':
        print('Cancelled — nothing changed.')
        conn.close()
        return

    print()
    removed = 0
    for t, broker in ghosts:
        try:
            # Import remove_trade logic inline to avoid circular import issues
            sys.path.insert(0, os.path.dirname(__file__))
            from remove_trade import remove_trade as _remove
            changes = _remove(conn, t, dry_run=False)
            print(f'  Removed ghost [{t["id"]}] {t["symbol"]}:')
            for ch in changes:
                print(f'  {ch}')
            removed += 1
        except Exception as e:
            print(f'  ERROR removing [{t["id"]}] {t["symbol"]}: {e}')

    print(f'\nDone. {removed}/{len(ghosts)} ghost(s) removed.')
    conn.close()


if __name__ == '__main__':
    main()
