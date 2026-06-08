"""
=================================================================
  MATRIX FROM CACHE  —  run strategy matrix against every symbol
  already in the local candle_store.db, no API calls needed.

  Queries data/candle_store.db for all symbols that have candle
  data on the requested timeframe, then runs the full condition
  matrix (symbol × direction) using the existing backtester +
  strategy_matrix reporting pipeline.

  USAGE
  -----
    # BMR-357 against everything cached at 15m, long+short
    python Scripts/matrix_from_cache.py --strategy bmr_357

    # Specify timeframe / directions / days
    python Scripts/matrix_from_cache.py --strategy bmr_357 \\
        --timeframe 15m --directions long,short --days 180

    # Crypto only or stocks only
    python Scripts/matrix_from_cache.py --strategy bmr_357 --crypto-only
    python Scripts/matrix_from_cache.py --strategy bmr_357 --stocks-only

    # Minimum bar count filter (skip symbols with sparse data)
    python Scripts/matrix_from_cache.py --strategy bmr_357 --min-bars 200

    # Override strategy params
    python Scripts/matrix_from_cache.py --strategy bmr_357 \\
        --param stop_loss_pct=1.2 --param take_profit_pct=3.0

  OUTPUT
  ------
    Same as strategy_matrix.py:
      reports/strategy_matrix/<strategy>_<timestamp>_cache.txt
      reports/strategy_matrix/<strategy>_<timestamp>_cache.csv
      reports/strategy_matrix/<strategy>_<timestamp>_cache.json

  WHY USE THIS INSTEAD OF strategy_matrix.py?
  --------------------------------------------
    • No API rate limits — reads local SQLite only
    • Runs against your ACTUAL cached universe (whatever the bot
      has been collecting), not a hand-picked symbol list
    • Much faster — cache hits are instant vs. network fetches
    • Automatically picks up new symbols as the cache grows
=================================================================
"""

import argparse
import os
import sys
import sqlite3
from datetime import datetime

# ---------------------------------------------------------------------------
# Path setup — project root must be on sys.path for imports
# ---------------------------------------------------------------------------
_script_dir   = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

# Import the full matrix machinery from strategy_matrix
from Scripts.strategy_matrix import (   # noqa: E402
    run_cell,
    run_matrix,
    build_report,
    save_reports,
    write_text_report,
    _avg,
    EDGE_THRESHOLD,
    MIN_TRADES,
)

# ---------------------------------------------------------------------------
# Candle DB helpers
# ---------------------------------------------------------------------------

_CANDLE_DB = os.path.join(_project_root, "data", "candle_store.db")


def _get_cached_symbols(timeframe: str,
                        min_bars: int = 50,
                        crypto_only: bool = False,
                        stocks_only: bool = False) -> tuple:
    """
    Query candle_store.db for all symbols that have >= min_bars rows
    on the requested timeframe.

    Returns (crypto_symbols, stock_symbols) as sorted lists.
    Crypto symbols contain '/' (e.g. BTC/USD); stocks do not.
    """
    if not os.path.exists(_CANDLE_DB):
        print(f"[ERROR] Candle DB not found at {_CANDLE_DB}")
        sys.exit(1)

    conn = sqlite3.connect(_CANDLE_DB)
    cur  = conn.cursor()

    # Normalise timeframe to what the DB uses
    # (candle_manager stores '5m','15m','1h' etc.)
    tf_variants = {timeframe}
    _tf_map = {
        "15Min": "15m", "5Min": "5m", "1Hour": "1h",
        "15m": "15m",   "5m":  "5m",  "1h":   "1h",
        "4h": "4h", "1d": "1d",
    }
    tf_norm = _tf_map.get(timeframe, timeframe)
    tf_variants.add(tf_norm)

    placeholders = ",".join("?" * len(tf_variants))
    cur.execute(
        f"""
        SELECT symbol, COUNT(*) as bars
        FROM   candles
        WHERE  timeframe IN ({placeholders})
        GROUP  BY symbol
        HAVING bars >= ?
        ORDER  BY symbol
        """,
        (*sorted(tf_variants), min_bars),
    )
    rows = cur.fetchall()
    conn.close()

    crypto_syms = []
    stock_syms  = []
    for sym, bars in rows:
        if "/" in sym:
            crypto_syms.append(sym)
        else:
            stock_syms.append(sym)

    if crypto_only:
        stock_syms = []
    if stocks_only:
        crypto_syms = []

    return sorted(crypto_syms), sorted(stock_syms)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run strategy matrix against all symbols in the local candle cache.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--strategy",    required=True, metavar="NAME",
                        help="Strategy name (e.g. bmr_357)")
    parser.add_argument("--timeframe",   default="15m", metavar="TF",
                        help="Timeframe to query from cache and backtest on (default: 15m)")
    parser.add_argument("--directions",  default="long,short",
                        help="Comma-separated directions: long,short,both (default: long,short)")
    parser.add_argument("--days",        type=int, default=180,
                        help="Days of history per cell (default: 180)")
    parser.add_argument("--min-bars",    type=int, default=100, dest="min_bars",
                        help="Min bars in cache to include a symbol (default: 100)")
    parser.add_argument("--crypto-only", action="store_true",
                        help="Only run crypto symbols (contains /)")
    parser.add_argument("--stocks-only", action="store_true",
                        help="Only run stock symbols (no /)")
    parser.add_argument("--param",       metavar="name=value", action="append",
                        default=[], dest="params",
                        help="Override a strategy param (repeatable)")
    parser.add_argument("--edge-threshold", type=float, default=EDGE_THRESHOLD,
                        help=f"PF threshold for edge cells (default: {EDGE_THRESHOLD})")

    args = parser.parse_args()

    # Parse param overrides
    param_overrides = {}
    for p in args.params:
        if "=" not in p:
            print(f"[WARN] Ignoring malformed --param '{p}' (expected name=value)")
            continue
        k, v = p.split("=", 1)
        try:
            param_overrides[k.strip()] = float(v.strip())
        except ValueError:
            param_overrides[k.strip()] = v.strip()

    directions = [d.strip() for d in args.directions.split(",")]

    # ── Discover symbols from cache ──────────────────────────────────────────
    print(f"\n  Querying candle cache: {_CANDLE_DB}")
    crypto_syms, stock_syms = _get_cached_symbols(
        timeframe   = args.timeframe,
        min_bars    = args.min_bars,
        crypto_only = args.crypto_only,
        stocks_only = args.stocks_only,
    )

    total_syms = len(crypto_syms) + len(stock_syms)
    if total_syms == 0:
        print(f"[ERROR] No symbols found in cache with timeframe={args.timeframe} "
              f"and min_bars={args.min_bars}.")
        print("        Run the bot first to populate the candle cache, or lower --min-bars.")
        sys.exit(1)

    print(f"  Found {len(crypto_syms)} crypto + {len(stock_syms)} stock symbols "
          f"with {args.timeframe} data (min {args.min_bars} bars)")
    print(f"  Strategy  : {args.strategy}")
    print(f"  Timeframe : {args.timeframe}")
    print(f"  Directions: {', '.join(directions)}")
    print(f"  Days      : {args.days}")
    if param_overrides:
        print(f"  Params    : {param_overrides}")
    print(f"  Total cells: {total_syms * len(directions)}")
    print()

    # ── Initialise backtester ────────────────────────────────────────────────
    try:
        from logs.intelligence.backtester import Backtester
    except ImportError:
        from intelligence.backtester import Backtester

    bt = Backtester()

    started_at = datetime.now().isoformat(timespec="seconds")

    # ── Run matrix ───────────────────────────────────────────────────────────
    results, total_cells, done_cells = run_matrix(
        bt              = bt,
        strategy_name   = args.strategy,
        crypto_symbols  = crypto_syms,
        stock_symbols   = stock_syms,
        timeframes      = [args.timeframe],
        directions      = directions,
        days            = args.days,
        param_overrides = param_overrides,
    )

    finished_at = datetime.now().isoformat(timespec="seconds")

    # ── Build + save report ──────────────────────────────────────────────────
    report = build_report(
        strategy_name   = args.strategy,
        results         = results,
        crypto_symbols  = crypto_syms,
        stock_symbols   = stock_syms,
        timeframes      = [args.timeframe],
        directions      = directions,
        days            = args.days,
        param_overrides = param_overrides,
        total_cells     = total_cells,
        done_cells      = done_cells,
        cancelled       = (done_cells < total_cells),
        started_at      = started_at,
        finished_at     = finished_at,
        edge_threshold  = args.edge_threshold,
        min_trades      = MIN_TRADES,
    )

    out_dir = os.path.join(_project_root, "reports", "strategy_matrix")
    json_path, csv_path, txt_path = save_reports(
        report        = report,
        strategy_name = args.strategy,
        out_dir       = out_dir,
        label         = "cache",
    )

    # ── Print summary to terminal ─────────────────────────────────────────────
    s = report["summary"]
    print(f"\n{'='*60}")
    print(f"  {args.strategy.upper()}  |  {args.timeframe}  |  {args.days}d  "
          f"|  {total_syms} symbols from cache")
    print(f"{'='*60}")
    print(f"  Overall avg PF : {s['overall_avg_pf']:.3f}")
    print(f"  Edge rate      : {s['overall_edge_rate']:.1f}%  "
          f"({s['overall_n_edge']}/{s['total_valid_cells']} cells PF>={args.edge_threshold})")
    print()
    print("  Top 10 symbols by avg PF:")
    for sym_stat in s["best_symbols"][:10]:
        sym = sym_stat["symbol"]
        print(f"    {sym:<16}  PF={sym_stat['avg_pf']:.3f}  "
              f"WR={sym_stat['avg_wr']:.0f}%  "
              f"edge={sym_stat['edge_rate']:.0f}%")
    print()
    print(f"  Reports saved to:")
    print(f"    {txt_path}")
    print(f"    {csv_path}")
    print(f"    {json_path}")
    print()


if __name__ == "__main__":
    main()
