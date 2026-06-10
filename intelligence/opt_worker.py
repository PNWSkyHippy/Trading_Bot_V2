"""
=============================================================
  OPTIMIZER WORKER  — runs as a subprocess
  Called by web_dashboard.py via subprocess.Popen so the
  heavy simulation loop runs in its own Python interpreter
  with its own GIL, leaving the web server 100% responsive.

  Usage (internal — do not call directly):
    python intelligence/opt_worker.py <config.json> <progress.json>

  config.json fields:
    strategy, symbols, params, method, iterations,
    days, timeframe, asset_class, metric, minimize

  progress.json is written on every iteration:
    {running, iteration, total, best_score, cancelled, error, results}
=============================================================
"""

import sys
import os
import json
import logging

# ---------------------------------------------------------------------------
# Path setup — works whether called from repo root or intelligence/
# ---------------------------------------------------------------------------
_this_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir  = os.path.normpath(os.path.join(_this_dir, '..'))
for _p in [_root_dir, _this_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [opt_worker] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _NumpyEncoder(json.JSONEncoder):
    """Serialize numpy scalars that standard json can't handle."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):  return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, np.ndarray):     return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)


def write_progress(path: str, data: dict):
    """Atomic-ish write: write to .tmp then rename."""
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w') as f:
            json.dump(data, f, cls=_NumpyEncoder)
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"write_progress FAILED — results may be lost: {e}", exc_info=True)


def result_to_dict(r) -> dict:
    return {
        'params':              r.params,
        'score':               round(r.score, 6),
        'avg_profit_factor':   round(r.avg_profit_factor, 4),
        'avg_win_rate':        round(r.avg_win_rate, 2),
        'avg_net_pnl':         round(r.avg_net_pnl, 2),
        'consistency':         round(r.consistency, 4),
        'symbols_tested':      r.symbols_tested,
        'symbols_profitable':  r.symbols_profitable,
        'per_symbol':          r.per_symbol,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: opt_worker.py <config.json> <progress.json>", file=sys.stderr)
        sys.exit(1)

    config_path   = sys.argv[1]
    progress_path = sys.argv[2]

    # Load config
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        write_progress(progress_path, {
            'running': False, 'done': True, 'error': f"Cannot read config: {e}", 'results': None,
        })
        sys.exit(1)

    strategy    = cfg['strategy']
    symbols     = cfg['symbols']
    params_cfg  = cfg['params']
    method      = cfg.get('method', 'annealing')
    iterations  = int(cfg.get('iterations', 40))
    days        = int(cfg.get('days', 365))
    timeframe   = cfg.get('timeframe', '1h')
    asset_class = cfg.get('asset_class', 'crypto')
    metric      = cfg.get('metric', 'profit_factor')
    minimize    = bool(cfg.get('minimize', False))

    write_progress(progress_path, {
        'running': False, 'iteration': 0, 'total': iterations,
        'best_score': None, 'cancelled': False, 'error': None, 'results': None,
        'phase': 'prefetch',
    })

    # Import heavy dependencies after writing initial progress
    try:
        from intelligence.backtester import Backtester
        from intelligence.optimizer  import StrategyOptimizer as Optimizer, ParamRange
    except Exception as e:
        write_progress(progress_path, {
            'running': False, 'done': True, 'error': f"Import failed: {e}", 'results': None,
        })
        sys.exit(1)

    bt  = Backtester()
    opt = Optimizer(bt)

    # ── Candle store status check ────────────────────────────────────────────
    try:
        from intelligence.candle_store import get_store as _gcs
        _cs = _gcs()
        _entries = {(e['symbol'], e['timeframe']): e for e in _cs.list_available()}
        for sym in symbols:
            key = (sym, timeframe)
            if key in _entries:
                e = _entries[key]
                logger.info(f"CandleStore: {sym} {timeframe} — {e['bar_count']:,} bars, age {e['age_hours']}h ✓")
            else:
                logger.warning(f"CandleStore: {sym} {timeframe} — NOT FOUND, will fetch from network")
    except Exception as _cse:
        logger.warning(f"CandleStore check failed: {_cse}")

    # Pre-fetch all symbols into cache / candle store
    logger.info(f"Pre-fetching {len(symbols)} symbol(s)...")
    for sym in symbols:
        try:
            if asset_class == 'crypto':
                df = bt.fetch_history_crypto(sym, days=days, timeframe=timeframe)
            else:
                df = bt.fetch_history(sym, days=days, timeframe=timeframe)
            if df is None or df.empty:
                raise ValueError(f"No data returned for {sym}")
            logger.info(f"  {sym}: {len(df):,} bars")
        except Exception as e:
            write_progress(progress_path, {
                'running': False, 'done': True,
                'error': f"Pre-fetch failed for {sym}: {e}", 'results': None,
            })
            sys.exit(1)

    # Build param ranges
    param_ranges = []
    for p in params_cfg:
        param_ranges.append(ParamRange(
            name   = p['name'],
            min_val= float(p['min']),
            max_val= float(p['max']),
            step   = float(p['step']),
            is_int = bool(p.get('is_int', False)),
        ))

    # Start optimization
    write_progress(progress_path, {
        'running': True, 'iteration': 0, 'total': iterations,
        'best_score': None, 'cancelled': False, 'error': None, 'results': None,
        'phase': 'optimizing',
    })

    def progress_cb(current: int, total: int, best: float):
        write_progress(progress_path, {
            'running':    True,
            'iteration':  current,
            'total':      total,
            'best_score': round(best, 4) if best is not None else None,
            'cancelled':  False,
            'error':      None,
            'results':    None,
            'phase':      'optimizing',
        })

    run_kwargs = {'days': days, 'timeframe': timeframe, 'asset_class': asset_class}

    try:
        results = opt.optimize(
            strategy_name = strategy,
            param_ranges  = param_ranges,
            symbols       = symbols,
            metric        = metric,
            minimize      = minimize,
            method        = method,
            iterations    = iterations,
            run_kwargs    = run_kwargs,
            progress_cb   = progress_cb,
        )
        out = [result_to_dict(r) for r in results]
        best = results[0] if results else None
        write_progress(progress_path, {
            'running':    False,
            'done':       True,
            'iteration':  len(results),
            'total':      iterations,
            'best_score': round(best.score, 4) if best else None,
            'cancelled':  False,
            'error':      None,
            'results': {
                'ok':       True,
                'strategy': strategy,
                'method':   method,
                'tested':   len(results),
                'cancelled':False,
                'results':  out,
            },
            'phase': 'done',
        })
        logger.info(f"Optimization complete — {len(results)} results")

    except KeyboardInterrupt:
        # SIGTERM / Ctrl-C — write whatever partial results exist
        partial = [result_to_dict(r) for r in sorted(
            getattr(opt, '_partial_results', []), key=lambda x: x.score, reverse=True
        )]
        write_progress(progress_path, {
            'running':    False,
            'done':       True,
            'iteration':  len(partial),
            'total':      iterations,
            'best_score': partial[0]['score'] if partial else None,
            'cancelled':  True,
            'error':      None,
            'results': {
                'ok':       True,
                'strategy': strategy,
                'method':   method,
                'tested':   len(partial),
                'cancelled':True,
                'results':  partial,
            },
            'phase': 'cancelled',
        })
        logger.info(f"Cancelled — {len(partial)} partial results saved")

    except Exception as e:
        logger.exception(f"Optimizer crashed: {e}")
        write_progress(progress_path, {
            'running': False, 'done': True, 'error': str(e), 'results': None,
        })
        sys.exit(1)


if __name__ == '__main__':
    main()
