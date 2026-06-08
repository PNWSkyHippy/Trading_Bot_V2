"""Summarize best results from all param sweep JSON files."""
import json, glob, os

sweep_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'param_sweeps')

best = {}

for f in sorted(glob.glob(os.path.join(sweep_dir, '*.json'))):
    try:
        with open(f) as fp:
            data = json.load(fp)
        results = data.get('results', [])
        if not results:
            continue
        top = results[0]
        meta = data.get('meta', {})
        strategy = meta.get('strategy') or data.get('strategy') or os.path.basename(f).rsplit('_2026', 1)[0]
        score  = float(top.get('score', 0) or 0)
        pf     = float(top.get('avg_profit_factor', top.get('profit_factor', 0)) or 0)
        wr     = float(top.get('avg_win_rate',      top.get('win_rate', 0))      or 0)
        raw_c  = top.get('consistency', top.get('consistency_pct', 0)) or 0
        cons   = float(raw_c) * 100 if float(raw_c) <= 1.0 else float(raw_c)
        params = top.get('params', {})
        fname  = os.path.basename(f)
        if score > -999 and (strategy not in best or score > best[strategy]['score']):
            best[strategy] = dict(score=score, pf=pf, wr=wr, cons=cons, params=params, file=fname)
    except Exception as e:
        print('  Error reading', f, ':', e)

print('BEST RESULTS PER STRATEGY:')
print('-' * 80)
for strat in sorted(best):
    b = best[strat]
    verdict = 'APPLY' if b['pf'] >= 1.3 and b['cons'] >= 60 else ('WEAK' if b['pf'] >= 1.0 else 'NO EDGE')
    print('[%s] %s' % (verdict, strat))
    print('  Score=%.2f  PF=%.2f  WR=%.1f%%  Consistency=%.0f%%' % (b['score'], b['pf'], b['wr'], b['cons']))
    print('  Params:', b['params'])
    print('  From:', b['file'])
    print()
