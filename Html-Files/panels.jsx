// Trading Bot Dashboard panels
const { useState: useS, useEffect: useE, useRef: useR, useMemo: useM, useCallback: useC } = React;

// Format helpers
const fmt$ = (n, d = 2) => {
  if (n === null || n === undefined || isNaN(n)) return '—';
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  return sign + '$' + abs.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
};
const fmt$Sign = (n, d = 2) => (n >= 0 ? '+' : '') + fmt$(n, d);
const fmtP = (n, d = 2) => (n >= 0 ? '+' : '') + n.toFixed(d) + '%';
const fmtN = (n, d = 4) => Number(n).toFixed(d);
const cls = (...a) => a.filter(Boolean).join(' ');

// ============ KPI Bar ============
function KPIBar({ kpis }) {
  return (
    <div className="kpi-row">
      {kpis.map((k, i) => (
        <div key={i} className="kpi">
          <div className="kpi-label">{k.label}</div>
          <div className={cls('kpi-value', k.tone)}>{k.value}</div>
          {k.meta && <div className="kpi-meta">{k.meta}</div>}
        </div>
      ))}
    </div>
  );
}

// ============ Capital Growth Chart ============
function CapitalChart({ data }) {
  const ref = useR(null);
  const chartRef = useR(null);
  useE(() => {
    if (!ref.current || !window.Chart) return;
    if (chartRef.current) chartRef.current.destroy();
    const ctx = ref.current.getContext('2d');
    const labels = data.map(d => d.date.toLocaleDateString('en', { month: 'short', day: 'numeric' }));
    const values = data.map(d => d.capital);
    const grad = ctx.createLinearGradient(0, 0, 0, 200);
    grad.addColorStop(0, 'rgba(20, 184, 166, 0.3)');
    grad.addColorStop(1, 'rgba(20, 184, 166, 0)');
    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ data: values, borderColor: '#14b8a6', backgroundColor: grad, borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0, pointHoverRadius: 4, pointHoverBackgroundColor: '#2dd4bf' }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: '#161a1f', borderColor: '#232830', borderWidth: 1, titleColor: '#f3f5f8', bodyColor: '#b8bfca', padding: 10, displayColors: false, callbacks: { label: (c) => '$' + c.parsed.y.toLocaleString('en', { maximumFractionDigits: 2 }) } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#7d8593', font: { size: 10, family: 'JetBrains Mono' }, maxRotation: 0, autoSkipPadding: 20 }, border: { color: '#232830' } },
          y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#7d8593', font: { size: 10, family: 'JetBrains Mono' }, callback: (v) => '$' + (v / 1000).toFixed(0) + 'k' }, border: { color: '#232830' } }
        }
      }
    });
    return () => chartRef.current && chartRef.current.destroy();
  }, [data]);
  return <canvas ref={ref} />;
}

// ============ Win/Loss Donut ============
function WinLossDonut({ wins, losses }) {
  const ref = useR(null);
  const chartRef = useR(null);
  useE(() => {
    if (!ref.current || !window.Chart) return;
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new Chart(ref.current.getContext('2d'), {
      type: 'doughnut',
      data: { labels: ['Wins', 'Losses'], datasets: [{ data: [wins, losses], backgroundColor: ['#10b981', '#f43f5e'], borderColor: '#0b0d10', borderWidth: 3, hoverOffset: 6 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '70%',
        plugins: { legend: { position: 'bottom', labels: { color: '#b8bfca', font: { size: 11 }, boxWidth: 10, padding: 12 } }, tooltip: { backgroundColor: '#161a1f', borderColor: '#232830', borderWidth: 1, padding: 10 } }
      }
    });
    return () => chartRef.current && chartRef.current.destroy();
  }, [wins, losses]);
  return <canvas ref={ref} />;
}

// ============ Top Bar (KPIs + charts) ============
function TopOverview({ live }) {
  const winRate = 25;
  const wins = 25 * 0.25;
  const losses = 25 * 0.75;
  const kpis = [
    { label: 'Total Capital', value: fmt$(live.capital), tone: 'accent', meta: <span><span className="delta neg">−$796.99</span> from start</span> },
    { label: 'Daily P&L', value: fmt$Sign(live.dailyPnl), tone: live.dailyPnl >= 0 ? 'pos' : 'neg', meta: 'Today' },
    { label: 'Daily P&L %', value: fmtP(live.dailyPnlP), tone: live.dailyPnlP >= 0 ? 'pos' : 'neg', meta: 'vs start of day' },
    { label: 'Open Positions', value: '16', meta: '12 long · 4 short' },
    { label: 'Trades Today', value: '25', meta: '6W · 19L' },
    { label: 'Consec. Losses', value: '4', tone: 'warn', meta: 'threshold: 6' },
  ];
  return (
    <>
      <div className="banner-row">
        <div className="banner success">
          <span className="dot" style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }}></span>
          <strong>Trading Active</strong> — Bot is running and scanning markets · PID 11552 · ML active at 30% weight (112 trades to full ML)
        </div>
      </div>
      <KPIBar kpis={kpis} />
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 10, padding: '0 16px 14px' }}>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, height: 240 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Capital Growth (30 Days)</h3>
            <div style={{ display: 'flex', gap: 4 }}>
              {['7D', '30D', '90D', 'YTD'].map(p => <button key={p} className={cls('btn', 'sm', p === '30D' && 'primary')} style={{ padding: '3px 8px', fontSize: 10.5 }}>{p}</button>)}
            </div>
          </div>
          <div style={{ height: 180 }}><CapitalChart data={MOCK.CAPITAL_HISTORY} /></div>
        </div>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, height: 240 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Win/Loss Distribution</h3>
            <span style={{ fontSize: 11, color: 'var(--text-2)' }}>Today · {winRate}% win rate</span>
          </div>
          <div style={{ height: 180 }}><WinLossDonut wins={wins} losses={losses} /></div>
        </div>
      </div>
    </>
  );
}

// ============ Open Positions ============
function OpenPositionsPanel() {
  const [positions, setPositions] = useS(MOCK.OPEN_POSITIONS);
  const { open } = useWindows();

  // Live price ticks
  useE(() => {
    const t = setInterval(() => {
      setPositions(prev => prev.map(p => {
        const drift = (Math.random() - 0.5) * 0.001;
        const newPrice = p.current * (1 + drift);
        const sign = p.dir === 'LONG' ? 1 : -1;
        const newPnl = ((newPrice - p.entry) / p.entry) * sign * 2000;
        const newPnlP = ((newPrice - p.entry) / p.entry) * sign * 100;
        return { ...p, current: newPrice, pnlD: newPnl, pnlP: newPnlP };
      }));
    }, 2500);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="panel-section" style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 3 }}>Open Positions</h3>
          <div className="panel-sub" style={{ margin: 0 }}>{positions.length} active · Newest first</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn ghost sm" onClick={() => open('manage-positions')}><Icon name="sliders" size={12} />Manage Positions</button>
          <button className="btn sm"><Icon name="refresh" size={12} />Refresh</button>
        </div>
      </div>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <th>Opened</th><th>Symbol</th><th>Type</th><th>Dir</th>
            <th className="num">Entry</th><th className="num">Current</th><th className="num">SL</th><th className="num">TP</th>
            <th className="num">Unreal P&L</th><th className="num">P&L %</th><th className="num">→ SL</th><th className="num">→ TP</th>
          </tr></thead>
          <tbody>
            {positions.map((p, i) => (
              <tr key={i}>
                <td className="muted">{p.opened}</td>
                <td><strong>{p.symbol}</strong></td>
                <td className="muted">{p.type}</td>
                <td><span className={cls('pill', p.dir.toLowerCase())}>{p.dir}</span></td>
                <td className="num">{fmtN(p.entry)}</td>
                <td className="num">{fmtN(p.current)}</td>
                <td className="num muted">{fmtN(p.sl)}</td>
                <td className="num muted">{fmtN(p.tp)}</td>
                <td className={cls('num', p.pnlD > 0 && 'pos', p.pnlD < 0 && 'neg')}>{fmt$Sign(p.pnlD)}</td>
                <td className={cls('num', p.pnlP > 0 && 'pos', p.pnlP < 0 && 'neg')}>{fmtP(p.pnlP)}</td>
                <td className="num muted">{p.toSL.toFixed(2)}%</td>
                <td className="num muted">{p.toTP.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ Manual Trade Entry ============
function ManualTradePanel() {
  const [form, setForm] = useS({ symbol: '', size: '2000.00', sl: '1.50', dir: 'long', broker: 'ibkr', tp: '3.00', asset: 'stock', overnight: false, label: 'manual' });
  const [msg, setMsg] = useS('');
  const [busy, setBusy] = useS(false);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const apiBase = () => {
    const configured = (window.DASHBOARD_API_BASE || '').replace(/\/$/, '');
    if (configured) return configured;
    if (window.location.protocol === 'file:') return 'http://localhost:8125';
    return '';
  };
  const openTrade = async () => {
    setBusy(true);
    setMsg('Submitting manual trade...');
    try {
      const res = await fetch(`${apiBase()}/api/trades/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || data.error || `HTTP ${res.status}`);
      setMsg(data.message || 'Manual trade opened.');
    } catch (e) {
      setMsg(`Manual trade failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div style={{ padding: 16 }}>
      <div className="panel-sub" style={{ marginBottom: 14 }}>Enter a trade you spotted yourself — bot submits to broker and manages it with trailing stops.</div>
      <div className="grid-3" style={{ marginBottom: 12 }}>
        <div className="field"><label>Symbol</label><input className="input" placeholder="RAVE/USD or SOXL" value={form.symbol} onChange={e => set('symbol', e.target.value)} /></div>
        <div className="field"><label>Position Size ($)</label><input className="input" value={form.size} onChange={e => set('size', e.target.value)} /></div>
        <div className="field"><label>Stop Loss %</label><input className="input" value={form.sl} onChange={e => set('sl', e.target.value)} /></div>
      </div>
      <div className="grid-3" style={{ marginBottom: 12 }}>
        <div className="field"><label>Direction</label><select className="select input" value={form.dir} onChange={e => set('dir', e.target.value)}>{MOCK.DIRECTIONS.map(d => <option key={d}>{d}</option>)}</select></div>
        <div className="field"><label>Broker</label><select className="select input" value={form.broker} onChange={e => set('broker', e.target.value)}>{MOCK.BROKERS.map(b => <option key={b}>{b}</option>)}</select></div>
        <div className="field"><label>Take Profit %</label><input className="input" value={form.tp} onChange={e => set('tp', e.target.value)} /></div>
      </div>
      <div className="grid-3" style={{ marginBottom: 16 }}>
        <div className="field"><label>Asset Class</label><select className="select input" value={form.asset} onChange={e => set('asset', e.target.value)}><option>stock</option><option>crypto</option></select></div>
        <div className="field"><label style={{ visibility: 'hidden' }}>—</label><label className="checkbox" style={{ paddingTop: 8 }}><input type="checkbox" checked={form.overnight} onChange={e => set('overnight', e.target.checked)} /> Hold Overnight (Day Trade)</label></div>
        <div className="field"><label>Strategy Label</label><input className="input" value={form.label} onChange={e => set('label', e.target.value)} /></div>
      </div>
      <button className="btn primary full" disabled={!form.symbol || busy} onClick={openTrade}><Icon name="send" size={13} /> {busy ? 'Submitting...' : 'Open Trade at Market Price'}</button>
      {msg && <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
    </div>
  );
}

// ============ Today's Trade Log ============
function TradeLogPanel() {
  const [trades, setTrades] = useS([]);
  const [msg, setMsg] = useS('Loading closed trades...');
  const [sort, setSort] = useS({ key: 'closed', dir: 'desc' });
  const apiBase = () => {
    const configured = (window.DASHBOARD_API_BASE || '').replace(/\/$/, '');
    if (configured) return configured;
    if (window.location.protocol === 'file:') return 'http://localhost:8125';
    return '';
  };
  const loadTrades = async () => {
    try {
      const res = await fetch(`${apiBase()}/api/trade_log/today`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || data.error || `HTTP ${res.status}`);
      const rows = Array.isArray(data.trades) ? data.trades : [];
      setTrades(rows);
      setMsg(rows.length ? '' : 'No closed trades today.');
    } catch (e) {
      setMsg(`Trade log failed: ${e.message}`);
    }
  };
  useE(() => {
    loadTrades();
    const t = setInterval(loadTrades, 15000);
    return () => clearInterval(t);
  }, []);
  const parseClock = (v) => {
    const m = String(v || '').match(/^(\d{2})\/(\d{2})\s+(\d{2}):(\d{2})$/);
    if (!m) return 0;
    return Number(`${m[1]}${m[2]}${m[3]}${m[4]}`);
  };
  const parseDuration = (v) => {
    const text = String(v || '');
    const h = Number((text.match(/(\d+)h/) || [0, 0])[1]);
    const m = Number((text.match(/(\d+)m/) || [0, 0])[1]);
    return h * 60 + m;
  };
  const sortValue = (row, key) => {
    if (key === 'opened' || key === 'closed') return parseClock(row[key]);
    if (key === 'duration') return parseDuration(row.duration);
    if (['entry_price', 'exit_price', 'pnl', 'pnl_pct'].includes(key)) return Number(row[key] || 0);
    return String(row[key] || '').toLowerCase();
  };
  const sortedTrades = useM(() => {
    const dir = sort.dir === 'asc' ? 1 : -1;
    return [...trades].sort((a, b) => {
      const av = sortValue(a, sort.key);
      const bv = sortValue(b, sort.key);
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
  }, [trades, sort]);
  const toggleSort = (key) => setSort(s => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }));
  const SortHead = ({ k, children, num }) => (
    <th className={num ? 'num' : ''}>
      <button onClick={() => toggleSort(k)} style={{ all: 'unset', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        <span>{children}</span>
        {sort.key === k && <span style={{ color: 'var(--accent-bright)', fontSize: 10 }}>{sort.dir === 'asc' ? '▲' : '▼'}</span>}
      </button>
    </th>
  );

  return (
    <div style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="panel-sub" style={{ margin: 0 }}>{trades.length} closed trades today · Newest first</div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn ghost sm" onClick={loadTrades}><Icon name="refresh" size={12} />Refresh</button>
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 10px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <SortHead k="opened">Opened</SortHead><SortHead k="closed">Closed</SortHead><SortHead k="duration">Duration</SortHead><SortHead k="symbol">Symbol</SortHead><SortHead k="direction">Dir</SortHead><SortHead k="strategy">Strategy</SortHead>
            <SortHead k="entry_price" num>Entry</SortHead><SortHead k="exit_price" num>Exit</SortHead><SortHead k="reason">Reason</SortHead><SortHead k="pnl" num>P&L $</SortHead><SortHead k="pnl_pct" num>P&L %</SortHead><SortHead k="result">Result</SortHead>
          </tr></thead>
          <tbody>
            {sortedTrades.map((t, i) => (
              <tr key={i}>
                <td className="muted">{t.opened}</td>
                <td className="muted">{t.closed}</td>
                <td className="muted">{t.duration}</td>
                <td><strong>{t.symbol}</strong></td>
                <td><span className={cls('pill', String(t.direction).toLowerCase())}>{t.direction}</span></td>
                <td className="muted">{t.strategy}</td>
                <td className="num">{fmtN(t.entry_price)}</td>
                <td className="num">{fmtN(t.exit_price)}</td>
                <td className="muted">{t.reason}</td>
                <td className={cls('num', t.pnl > 0 && 'pos', t.pnl < 0 && 'neg')}>{fmt$Sign(t.pnl)}</td>
                <td className={cls('num', t.pnl_pct > 0 && 'pos', t.pnl_pct < 0 && 'neg')}>{fmtP(t.pnl_pct)}</td>
                <td><span className={cls('pill', String(t.result).toLowerCase())}>{t.result}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ Recent Daily Performance ============
function DailyPerfPanel() {
  return (
    <div style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px' }} className="panel-sub">Last {MOCK.DAILY_PERF.length} sessions · Daily summaries from session close.</div>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <th>Date</th><th className="num">Trades</th><th className="num">Wins</th><th className="num">Losses</th><th className="num">Win Rate</th><th className="num">P&L $</th><th className="num">P&L %</th><th className="num">Capital</th>
          </tr></thead>
          <tbody>
            {MOCK.DAILY_PERF.map((d, i) => (
              <tr key={i}>
                <td><strong>{d.date}</strong></td>
                <td className="num">{d.trades}</td>
                <td className="num pos">{d.wins}</td>
                <td className="num neg">{d.losses}</td>
                <td className="num">{d.winRate.toFixed(1)}%</td>
                <td className={cls('num', d.pnlD > 0 && 'pos', d.pnlD < 0 && 'neg')}>{fmt$Sign(d.pnlD)}</td>
                <td className={cls('num', d.pnlP > 0 && 'pos', d.pnlP < 0 && 'neg')}>{fmtP(d.pnlP)}</td>
                <td className="num">{fmt$(d.capital)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ Strategy Backtester ============
function BacktesterPanel() {
  const [form, setForm] = useS({ asset: 'Stocks', strategy: 'ALL strategies', tf: '1h', cap: '100000.00', symbol: 'ALL', duration: '90d (3mo)', mode: 'standard', lookback: '2' });
  const [running, setRunning] = useS(false);
  const [result, setResult] = useS(null);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const run = () => {
    setRunning(true); setResult(null);
    setTimeout(() => {
      setRunning(false);
      setResult({ totalTrades: 247, winRate: 38.5, pnlD: 8243.50, pnlP: 8.24, sharpe: 1.42, maxDD: -4.18, profitFactor: 1.31, avgWin: 142.30, avgLoss: -87.10 });
    }, 1400);
  };
  return (
    <div style={{ padding: 16 }}>
      <div className="panel-sub" style={{ marginBottom: 14 }}>Test any strategy on historical data. Compare Standard vs 2-Bar Trailing stop to find the best exit approach.</div>
      <div className="grid-4" style={{ marginBottom: 12 }}>
        <div className="field"><label>Asset Class</label><select className="select input" value={form.asset} onChange={e => set('asset', e.target.value)}>{MOCK.ASSET_CLASSES.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Strategy</label><select className="select input" value={form.strategy} onChange={e => set('strategy', e.target.value)}>{MOCK.STRATEGIES.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Timeframe</label><select className="select input" value={form.tf} onChange={e => set('tf', e.target.value)}>{MOCK.TIMEFRAMES.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Starting Capital ($)</label><input className="input" value={form.cap} onChange={e => set('cap', e.target.value)} /></div>
      </div>
      <div className="grid-3" style={{ marginBottom: 12 }}>
        <div className="field"><label>Symbol</label><select className="select input" value={form.symbol} onChange={e => set('symbol', e.target.value)}><option>ALL</option><option>AAPL</option><option>MSFT</option><option>BTC/USD</option><option>ETH/USD</option></select></div>
        <div className="field"><label>Duration</label><select className="select input" value={form.duration} onChange={e => set('duration', e.target.value)}>{MOCK.DURATIONS.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field" style={{ justifyContent: 'flex-end' }}>
          <button className="btn primary full" onClick={run} disabled={running}>{running ? <><Icon name="cpu" size={13} /> Running…</> : <><Icon name="play" size={13} /> Run Backtest</>}</button>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 18, alignItems: 'center', marginBottom: 12, padding: '10px 12px', background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
        <span style={{ fontSize: 11, color: 'var(--text-2)' }}>Stop Loss Mode:</span>
        <div className="radio-group">
          <label><input type="radio" name="mode" checked={form.mode === 'standard'} onChange={() => set('mode', 'standard')} /> Standard %</label>
          <label><input type="radio" name="mode" checked={form.mode === 'trailing'} onChange={() => set('mode', 'trailing')} /> 2-Bar Trailing</label>
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <label style={{ whiteSpace: 'nowrap' }}>Lookback Bars (N)</label>
          <input className="input" style={{ width: 60 }} value={form.lookback} onChange={e => set('lookback', e.target.value)} />
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-2)' }}>Fixed % stop from strategy config; bot behavior unchanged.</div>
      </div>

      {result && (
        <div className="bt-result">
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Backtest Results · {form.duration}</h3>
          <div className="grid-4">
            <div className="bt-stat"><span className="label">Total Trades</span><span className="value">{result.totalTrades}</span></div>
            <div className="bt-stat"><span className="label">Win Rate</span><span className="value pos">{result.winRate}%</span></div>
            <div className="bt-stat"><span className="label">Total P&L</span><span className="value pos" style={{ color: 'var(--green)' }}>{fmt$Sign(result.pnlD)}</span></div>
            <div className="bt-stat"><span className="label">Return</span><span className="value pos" style={{ color: 'var(--green)' }}>{fmtP(result.pnlP)}</span></div>
            <div className="bt-stat"><span className="label">Sharpe Ratio</span><span className="value">{result.sharpe}</span></div>
            <div className="bt-stat"><span className="label">Max Drawdown</span><span className="value" style={{ color: 'var(--red)' }}>{fmtP(result.maxDD)}</span></div>
            <div className="bt-stat"><span className="label">Profit Factor</span><span className="value">{result.profitFactor}</span></div>
            <div className="bt-stat"><span className="label">Avg Win / Loss</span><span className="value" style={{ fontSize: 13 }}>{fmt$(result.avgWin)} / <span style={{ color: 'var(--red)' }}>{fmt$(result.avgLoss)}</span></span></div>
          </div>
        </div>
      )}
      {!result && !running && <div className="empty">Configure parameters and click <strong>Run Backtest</strong> to see results.</div>}
    </div>
  );
}

// ============ Chat with Bot ============
function ChatPanel() {
  const [msgs, setMsgs] = useS([
    { role: 'bot', text: "Hi — I'm your trading bot. Ask me about active positions, performance, strategies, or have me pause/resume trading. What would you like to know?" }
  ]);
  const [input, setInput] = useS('');
  const [thinking, setThinking] = useS(false);
  const endRef = useR(null);
  useE(() => endRef.current?.scrollIntoView({ block: 'end' }), [msgs, thinking]);
  const send = async () => {
    if (!input.trim() || thinking) return;
    const q = input.trim();
    setMsgs(m => [...m, { role: 'user', text: q }]);
    setInput(''); setThinking(true);
    try {
      const reply = await window.claude?.complete(`You are a trading bot assistant. The user has 16 open positions, 25 trades today (6W/19L), -$331.74 daily P&L, $99,203.01 total capital. Be concise and practical. User: ${q}`);
      setMsgs(m => [...m, { role: 'bot', text: reply || "I'd help, but my AI link is offline. Try again in a moment." }]);
    } catch {
      setMsgs(m => [...m, { role: 'bot', text: "Connection issue — try again." }]);
    }
    setThinking(false);
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="chat-stream" style={{ flex: 1, overflowY: 'auto' }}>
        {msgs.map((m, i) => (
          <div key={i} className={cls('chat-msg', m.role)}>
            <div className="who">{m.role === 'user' ? 'You' : 'TradingBot'}</div>
            {m.text}
          </div>
        ))}
        {thinking && <div className="chat-msg bot"><div className="who">TradingBot</div><span style={{ opacity: 0.6 }}>Thinking…</span></div>}
        <div ref={endRef} />
      </div>
      <div className="chat-input-row">
        <input className="input" style={{ flex: 1 }} placeholder="Ask your bot anything…" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} />
        <button className="btn primary" onClick={send} disabled={!input.trim() || thinking}><Icon name="send" size={13} /></button>
      </div>
    </div>
  );
}

window.Panels = { TopOverview, OpenPositionsPanel, ManualTradePanel, TradeLogPanel, DailyPerfPanel, BacktesterPanel, ChatPanel };
window.fmt = { fmt$, fmt$Sign, fmtP, fmtN, cls };
