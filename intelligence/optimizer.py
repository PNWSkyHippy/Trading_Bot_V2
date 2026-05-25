"""
optimizer.py
============
Multi-symbol parameter sweep optimizer for trading strategies.
Plugs into the existing Backtester.run_strategy() via param_overrides.

Search methods
--------------
  random     — Pick N random combinations from the full parameter space.
               Fast broad scan, may miss good regions without enough iterations.

  all_random — Same as random but deduplicates so every tested combo is unique.
               Use when you want maximum coverage within the iteration budget.

  annealing  — Simulated annealing: starts with wide random exploration, then
               narrows around promising regions as "temperature" drops.
               Avoids getting stuck in local optima.  Best general-purpose method.

  sequential — Coordinate descent: hold all params fixed, sweep one at a time,
               keep the best value, repeat.  Methodical but slower with many params.

Scoring
-------
  Each combination is run across every symbol in the basket.
  score = avg_metric * (0.5 + 0.5 * consistency)

  Consistency = fraction of symbols that were profitable.
  This penalises param sets that are great on one symbol but weak on others,
  rewarding genuinely robust combinations.

  Available metrics: profit_factor, win_rate, net_pnl, sharpe, expectancy,
                     consistency_score (profit_factor × win_rate)

Usage (standalone)
------------------
  from intelligence.backtester import Backtester
  from intelligence.optimizer import StrategyOptimizer, ParamRange

  bt  = Backtester()
  opt = StrategyOptimizer(bt)

  ranges = [
      ParamRange('rsi_period',    10, 30, 2,   is_int=True),
      ParamRange('rsi_oversold',  20, 40, 5,   is_int=True),
      ParamRange('stop_pct',     0.5,  3, 0.5),
  ]

  results = opt.optimize(
      strategy_name = 'rsi_dip_spike_v4',
      param_ranges  = ranges,
      symbols       = ['BTC/USD', 'ETH/USD', 'SOL/USD'],
      metric        = 'profit_factor',
      method        = 'annealing',
      iterations    = 60,
      run_kwargs    = {'days': 365, 'timeframe': '1h', 'asset_class': 'crypto'},
  )

  for r in results[:10]:
      print(r.params, f"score={r.score:.3f} pf={r.avg_profit_factor:.2f} "
            f"wr={r.avg_win_rate:.1f}% consistent={r.consistency:.0%}")
"""

import random
import math
import logging
import itertools
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parameter range definition
# ---------------------------------------------------------------------------

@dataclass
class ParamRange:
    """
    Search space for one strategy parameter.

    name    : matches a key in config.SIGNAL_TUNING or strategy_obj.params
    min_val : inclusive lower bound
    max_val : inclusive upper bound
    step    : grid step size
    is_int  : cast sampled values to int (e.g. for period / lookback)
    """
    name:    str
    min_val: float
    max_val: float
    step:    float
    is_int:  bool = False

    def values(self) -> List[Any]:
        """All discrete values in this range."""
        vals = []
        v = self.min_val
        while v <= self.max_val + 1e-9:
            vals.append(int(round(v)) if self.is_int else round(v, 8))
            v = round(v + self.step, 8)
        return vals

    def random_value(self) -> Any:
        """Uniform random sample from the discrete grid."""
        vs = self.values()
        return random.choice(vs)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OptimizeResult:
    """
    Performance summary for one parameter combination across the symbol basket.
    """
    params:              Dict[str, Any]
    score:               float    # composite score — higher = better
    metric_value:        float    # average raw value of the chosen metric
    symbols_tested:      int
    symbols_profitable:  int
    consistency:         float    # fraction of symbols that were net-profitable
    avg_profit_factor:   float
    avg_win_rate:        float
    avg_net_pnl:         float
    per_symbol:          List[dict] = field(default_factory=list)

    def summary(self) -> str:
        parts = [f"{k}={v}" for k, v in self.params.items()]
        return (
            f"[{', '.join(parts)}] "
            f"score={self.score:.3f} "
            f"pf={self.avg_profit_factor:.2f} "
            f"wr={self.avg_win_rate:.1f}% "
            f"pnl={self.avg_net_pnl:+.1f} "
            f"consistent={self.consistency:.0%} "
            f"({self.symbols_profitable}/{self.symbols_tested} symbols)"
        )


# ---------------------------------------------------------------------------
# Core optimizer
# ---------------------------------------------------------------------------

class StrategyOptimizer:
    """
    Multi-symbol parameter optimizer.  Pass it a Backtester instance.
    """

    SEARCH_METHODS = ('random', 'all_random', 'annealing', 'sequential')
    METRICS = ('profit_factor', 'win_rate', 'net_pnl', 'sharpe',
               'expectancy', 'consistency_score')

    def __init__(self, backtester):
        self.bt = backtester

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _combo_key(self, params: Dict) -> tuple:
        return tuple(sorted(params.items()))

    def _random_combo(self, param_ranges: List[ParamRange]) -> Dict:
        return {pr.name: pr.random_value() for pr in param_ranges}

    def _midpoint_combo(self, param_ranges: List[ParamRange]) -> Dict:
        """Starting point for sequential / annealing — midpoint of each range."""
        result = {}
        for pr in param_ranges:
            vs = pr.values()
            result[pr.name] = vs[len(vs) // 2]
        return result

    def _neighbor_combo(self, base: Dict, param_ranges: List[ParamRange],
                        temperature: float) -> Dict:
        """
        Perturb base combo for simulated annealing.
        Higher temperature → larger jumps; lower → fine-grained search.
        """
        result = dict(base)
        pr_map = {pr.name: pr for pr in param_ranges}
        n_perturb = 2 if temperature > 0.5 else 1
        names = random.sample(list(result.keys()), min(n_perturb, len(result)))
        for name in names:
            pr = pr_map[name]
            vs = pr.values()
            try:
                idx = vs.index(result[name])
            except ValueError:
                idx = len(vs) // 2
            max_jump = max(1, int(len(vs) * temperature * 0.4))
            delta = random.randint(-max_jump, max_jump)
            new_idx = max(0, min(len(vs) - 1, idx + delta))
            result[name] = vs[new_idx]
        return result

    def _get_metric_value(self, result, metric: str) -> float:
        """Extract the chosen metric from a BacktestResult."""
        if result is None or result.total_trades == 0:
            return 0.0
        if metric == 'profit_factor':
            return result.profit_factor if result.profit_factor < 900 else 0.0
        if metric == 'win_rate':
            return result.win_rate
        if metric == 'net_pnl':
            return result.ending_capital - result.starting_capital
        if metric == 'sharpe':
            return getattr(result, 'sharpe_ratio', 0.0)
        if metric == 'expectancy':
            return getattr(result, 'expectancy', 0.0)
        if metric == 'consistency_score':
            pf = result.profit_factor if result.profit_factor < 900 else 0.0
            return pf * (result.win_rate / 100.0)
        return result.profit_factor if result.profit_factor < 900 else 0.0

    def _score_basket(self, symbol_results: List, metric: str,
                      minimize: bool) -> Tuple[float, dict]:
        """
        Compute composite score across all symbol results.
        Returns (composite_score, stats_dict).
        """
        valid = [r for r in symbol_results
                 if r is not None and r.total_trades > 0]
        if not valid:
            return (-999.0 if not minimize else 999.0), {}

        raw_vals    = [self._get_metric_value(r, metric) for r in valid]
        avg_metric  = sum(raw_vals) / len(raw_vals)

        profitable  = sum(1 for r in valid if (r.ending_capital - r.starting_capital) > 0)
        consistency = profitable / len(valid)

        avg_pf  = sum(
            r.profit_factor if r.profit_factor < 900 else 0 for r in valid
        ) / len(valid)
        avg_wr  = sum(r.win_rate for r in valid) / len(valid)
        avg_pnl = sum(r.ending_capital - r.starting_capital for r in valid) / len(valid)

        # Composite: metric weighted by consistency.
        # A parameter set that works on every symbol scores higher than one
        # that peaks on a single symbol and fails everywhere else.
        composite = avg_metric * (0.5 + 0.5 * consistency)
        if minimize:
            composite = -composite

        stats = {
            'avg_metric':   round(avg_metric,  4),
            'consistency':  round(consistency, 3),
            'avg_pf':       round(avg_pf,      3),
            'avg_wr':       round(avg_wr,      1),
            'avg_pnl':      round(avg_pnl,     2),
            'n_valid':      len(valid),
            'n_profitable': profitable,
        }
        return composite, stats

    def _run_combo(self, strategy_name: str, symbols: List[str],
                   params: Dict, run_kwargs: Dict) -> List:
        """Run one parameter combo across every symbol in the basket."""
        results = []
        for sym in symbols:
            try:
                r = self.bt.run_strategy(
                    symbol             = sym,
                    strategy_name      = strategy_name,
                    param_overrides    = params,
                    skip_equity_curve  = True,   # optimizer doesn't need equity curves
                    **run_kwargs,
                )
            except Exception as exc:
                logger.warning(f"[OPTIMIZER] {sym} with {params} failed: {exc}")
                r = None
            results.append(r)
        return results

    def _build_opt_result(self, params: Dict, symbol_results: List,
                          symbols: List[str], metric: str,
                          minimize: bool) -> OptimizeResult:
        score, stats = self._score_basket(symbol_results, metric, minimize)
        per_sym = []
        for sym, r in zip(symbols, symbol_results):
            if r and r.total_trades > 0:
                per_sym.append({
                    'symbol':        sym,
                    'trades':        r.total_trades,
                    'win_rate':      round(r.win_rate, 1),
                    'profit_factor': round(r.profit_factor
                                          if r.profit_factor < 900 else 0, 2),
                    'net_pnl':       round(r.ending_capital - r.starting_capital, 2),
                })
        return OptimizeResult(
            params             = dict(params),
            score              = score,
            metric_value       = stats.get('avg_metric',   0.0),
            symbols_tested     = len(symbols),
            symbols_profitable = stats.get('n_profitable', 0),
            consistency        = stats.get('consistency',  0.0),
            avg_profit_factor  = stats.get('avg_pf',       0.0),
            avg_win_rate       = stats.get('avg_wr',       0.0),
            avg_net_pnl        = stats.get('avg_pnl',      0.0),
            per_symbol         = per_sym,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        strategy_name: str,
        param_ranges:  List[ParamRange],
        symbols:       List[str],
        metric:        str              = 'profit_factor',
        minimize:      bool             = False,
        method:        str              = 'annealing',
        iterations:    int              = 50,
        run_kwargs:    Dict             = None,
        progress_cb:   Optional[Callable[[int, int, float], None]] = None,
    ) -> List[OptimizeResult]:
        """
        Run parameter optimization across the symbol basket.

        Parameters
        ----------
        strategy_name : strategy key (e.g. 'rsi_dip_spike_v4')
        param_ranges  : list of ParamRange objects defining the search space
        symbols       : list of symbols to test each combo against
        metric        : performance metric to optimize (see METRICS)
        minimize      : True to minimise the metric (e.g. max_drawdown)
        method        : search algorithm ('random','all_random','annealing','sequential')
        iterations    : total number of backtests to run (shared across symbols)
                        actual combos tested = iterations (each combo run on all symbols)
        run_kwargs    : extra kwargs forwarded to Backtester.run_strategy()
                        e.g. {'days': 365, 'timeframe': '1h', 'asset_class': 'crypto'}
        progress_cb   : optional callback(current_iter, total_iters, best_score)

        Returns
        -------
        List of OptimizeResult sorted best-first.
        """
        if method not in self.SEARCH_METHODS:
            raise ValueError(f"Unknown method '{method}'. Choose from: {self.SEARCH_METHODS}")
        if metric not in self.METRICS:
            raise ValueError(f"Unknown metric '{metric}'. Choose from: {self.METRICS}")

        run_kwargs   = run_kwargs or {}
        all_results: List[OptimizeResult] = []
        self._partial_results = all_results   # expose for cancel/partial-result retrieval
        seen_combos: set = set()

        def _eval(params: Dict, iteration: int) -> float:
            key = self._combo_key(params)
            if key in seen_combos:
                return None   # signal: skip duplicate
            seen_combos.add(key)
            sym_results = self._run_combo(strategy_name, symbols, params, run_kwargs)
            opt_result  = self._build_opt_result(params, sym_results, symbols,
                                                  metric, minimize)
            all_results.append(opt_result)
            best = max(r.score for r in all_results)
            if progress_cb:
                progress_cb(len(all_results), iterations, best)
            logger.info(
                f"[OPTIMIZER] {method} #{len(all_results)}/{iterations} "
                f"score={opt_result.score:.4f}  {params}"
            )
            return opt_result.score

        # ── Random / All Random ──────────────────────────────────────
        if method in ('random', 'all_random'):
            attempts = 0
            max_attempts = iterations * 5   # avoid infinite loop on small grids
            while len(all_results) < iterations and attempts < max_attempts:
                attempts += 1
                combo = self._random_combo(param_ranges)
                _eval(combo, len(all_results))

        # ── Simulated Annealing ──────────────────────────────────────
        elif method == 'annealing':
            current        = self._midpoint_combo(param_ranges)
            current_score  = _eval(current, 0) or -999.0
            best_score     = current_score

            for i in range(1, iterations):
                temperature = 1.0 - (i / iterations)   # 1.0 → ~0.0
                candidate   = _neighbor_combo_fn = self._neighbor_combo(
                    current, param_ranges, temperature
                )
                score = _eval(candidate, i)
                if score is None:
                    # duplicate — try a fully random jump instead
                    candidate = self._random_combo(param_ranges)
                    score = _eval(candidate, i)
                if score is None:
                    continue

                if score > current_score:
                    current, current_score = candidate, score
                    if score > best_score:
                        best_score = score
                else:
                    # Accept worse solution with probability e^(Δ/T)
                    delta = score - current_score
                    prob  = math.exp(delta / max(temperature, 0.005))
                    if random.random() < prob:
                        current, current_score = candidate, score

        # ── Sequential (coordinate descent) ─────────────────────────
        elif method == 'sequential':
            current = self._midpoint_combo(param_ranges)
            # First: evaluate the starting midpoint
            _eval(current, 0)

            cycle = 0
            while len(all_results) < iterations:
                improved = False
                for pr in param_ranges:
                    if len(all_results) >= iterations:
                        break
                    best_val_for_param   = current[pr.name]
                    best_score_for_param = -999.0

                    for val in pr.values():
                        if len(all_results) >= iterations:
                            break
                        candidate = dict(current)
                        candidate[pr.name] = val
                        score = _eval(candidate, len(all_results))
                        if score is not None and score > best_score_for_param:
                            best_score_for_param = score
                            best_val_for_param   = val

                    if best_val_for_param != current[pr.name]:
                        current[pr.name] = best_val_for_param
                        improved = True

                cycle += 1
                if not improved:
                    # Converged — do a random restart to escape the local optimum
                    current = self._random_combo(param_ranges)

        # ── Sort best first and return ───────────────────────────────
        all_results.sort(key=lambda r: r.score, reverse=True)
        logger.info(
            f"[OPTIMIZER] done — {len(all_results)} combos tested across "
            f"{len(symbols)} symbols.  Best: {all_results[0].summary() if all_results else 'none'}"
        )
        return all_results

    def print_report(self, results: List[OptimizeResult], top_n: int = 10) -> None:
        """Print a formatted leaderboard of the top N results."""
        if not results:
            print("No optimization results.")
            return

        print("\n" + "=" * 80)
        print(f"  OPTIMIZER RESULTS — top {min(top_n, len(results))} of {len(results)} combos tested")
        print("=" * 80)

        # Header
        param_names = list(results[0].params.keys())
        param_w     = max(len(n) for n in param_names)
        print(f"  {'Rank':>4}  ", end="")
        for n in param_names:
            print(f"{n:>{max(param_w,6)}}  ", end="")
        print(f"{'Score':>7}  {'PF':>5}  {'WR%':>6}  {'PnL':>8}  {'Consist':>8}  {'Syms':>6}")
        print("-" * 80)

        for rank, r in enumerate(results[:top_n], 1):
            print(f"  {rank:>4}  ", end="")
            for n in param_names:
                v = r.params.get(n, "?")
                print(f"{str(v):>{max(param_w,6)}}  ", end="")
            print(
                f"{r.score:>7.3f}  "
                f"{r.avg_profit_factor:>5.2f}  "
                f"{r.avg_win_rate:>6.1f}  "
                f"{r.avg_net_pnl:>+8.1f}  "
                f"{r.consistency:>7.0%}  "
                f"{r.symbols_profitable:>3}/{r.symbols_tested:<3}"
            )

        print("=" * 80)
        best = results[0]
        print(f"\n  Best params: {best.params}")
        print(f"  Profit factor  : {best.avg_profit_factor:.2f}")
        print(f"  Win rate       : {best.avg_win_rate:.1f}%")
        print(f"  Avg PnL/symbol : {best.avg_net_pnl:+.2f}")
        print(f"  Consistency    : {best.consistency:.0%}  "
              f"({best.symbols_profitable}/{best.symbols_tested} symbols profitable)")
        print()
