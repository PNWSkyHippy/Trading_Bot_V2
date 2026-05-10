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
const panelApiBase = () => {
  const configured = (window.DASHBOARD_API_BASE || '').replace(/\/$/, '');
  if (configured) return configured;
  if (window.location.protocol === 'file:') return 'http://localhost:8125';
  return '';
};
const panelApi = async (path, opts = {}) => {
  const res = await fetch(`${panelApiBase()}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || data?.error || `HTTP ${res.status}`);
  return data;
};

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
  const validData = data.filter(d => d.date instanceof Date && !isNaN(d.date.getTime()) && !isNaN(Number(d.capital)));
  const sig = validData.map(d => `${d.date.toISOString().slice(0, 10)}:${Number(d.capital || 0).toFixed(2)}`).join('|');
  useE(() => {
    if (!ref.current || !window.Chart) return;
    const labels = validData.map(d => d.date.toLocaleDateString('en', { month: 'short', day: 'numeric' }));
    const values = validData.map(d => d.capital);
    if (!labels.length) return;
    if (chartRef.current) {
      chartRef.current.data.labels = labels;
      chartRef.current.data.datasets[0].data = values;
      chartRef.current.update('none');
      return;
    }
    const ctx = ref.current.getContext('2d');
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
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [sig]);
  return <canvas ref={ref} />;
}

// ============ Win/Loss Donut ============
function WinLossDonut({ wins, losses }) {
  const ref = useR(null);
  const chartRef = useR(null);
  useE(() => {
    if (!ref.current || !window.Chart) return;
    if (chartRef.current) {
      chartRef.current.data.datasets[0].data = [wins, losses];
      chartRef.current.update('none');
      return;
    }
    chartRef.current = new Chart(ref.current.getContext('2d'), {
      type: 'doughnut',
      data: { labels: ['Wins', 'Losses'], datasets: [{ data: [wins, losses], backgroundColor: ['#10b981', '#f43f5e'], borderColor: '#0b0d10', borderWidth: 3, hoverOffset: 6 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '70%',
        plugins: { legend: { position: 'bottom', labels: { color: '#b8bfca', font: { size: 11 }, boxWidth: 10, padding: 12 } }, tooltip: { backgroundColor: '#161a1f', borderColor: '#232830', borderWidth: 1, padding: 10 } }
      }
    });
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [wins, losses]);
  return <canvas ref={ref} />;
}

// ============ Top Bar (KPIs + charts) ============
function TopOverview({ live }) {
  const [capitalRange, setCapitalRange] = useS('30D');
  const [overview, setOverview] = useS({
    capital: live?.capital || 0,
    daily_pnl: live?.dailyPnl || 0,
    daily_pnl_pct: live?.dailyPnlP || 0,
    open_positions: 0,
    trades_today: 0,
    wins_today: 0,
    losses_today: 0,
    win_rate_today: 0,
    consecutive_losses: 0,
    trading_active: true,
    halt_reason: '',
    bot_process_running: false,
    capital_history: [],
  });
  const [msg, setMsg] = useS('');
  const loadOverview = async () => {
    try {
      const data = await panelApi('/api/overview');
      setOverview(o => ({ ...o, ...data }));
      setMsg('');
    } catch (e) {
      setMsg(`Overview failed: ${e.message}`);
    }
  };
  useE(() => {
    loadOverview();
    const t = setInterval(loadOverview, 10000);
    return () => clearInterval(t);
  }, []);
  const winRate = overview.win_rate_today || 0;
  const wins = overview.wins_today || 0;
  const losses = overview.losses_today || 0;
  const capitalRanges = {
    '7D': { label: '7 Days', days: 7 },
    '30D': { label: '30 Days', days: 30 },
    '90D': { label: '90 Days', days: 90 },
    'YTD': { label: 'YTD', ytd: true },
  };
  const chartData = useM(() => {
    const rows = (overview.capital_history || [])
      .map(d => ({ date: new Date(d.date), capital: Number(d.capital || 0) }))
      .filter(d => d.date instanceof Date && !isNaN(d.date.getTime()) && !isNaN(d.capital))
      .sort((a, b) => a.date - b.date);
    if (!rows.length) return [];
    const selected = capitalRanges[capitalRange] || capitalRanges['30D'];
    const latest = rows[rows.length - 1].date;
    const cutoff = selected.ytd
      ? new Date(latest.getFullYear(), 0, 1)
      : new Date(latest.getTime() - (selected.days - 1) * 86400000);
    return rows.filter(d => d.date >= cutoff);
  }, [overview.capital_history, capitalRange]);
  const rangeLabel = (capitalRanges[capitalRange] || capitalRanges['30D']).label;
  const statusText = overview.trading_active
    ? 'Trading Active'
    : `Trading Paused${overview.halt_reason ? `: ${overview.halt_reason}` : ''}`;
  const kpis = [
    { label: 'Total Capital', value: fmt$(overview.capital), tone: 'accent', meta: 'Live DB' },
    { label: 'Daily P&L', value: fmt$Sign(overview.daily_pnl), tone: overview.daily_pnl >= 0 ? 'pos' : 'neg', meta: 'Today' },
    { label: 'Daily P&L %', value: fmtP(overview.daily_pnl_pct), tone: overview.daily_pnl_pct >= 0 ? 'pos' : 'neg', meta: 'vs locked start' },
    { label: 'Open Positions', value: String(overview.open_positions || 0), meta: 'Live' },
    { label: 'Trades Today', value: String(overview.trades_today || 0), meta: 'session counter' },
    { label: 'Consec. Losses', value: String(overview.consecutive_losses || 0), tone: (overview.consecutive_losses || 0) >= 2 ? 'warn' : 'pos', meta: 'risk counter' },
  ];
  return (
    <>
      <div className="banner-row">
        <div className={cls('banner', overview.trading_active ? 'success' : 'warn')}>
          <span className="dot" style={{ width: 8, height: 8, borderRadius: '50%', background: overview.trading_active ? '#10b981' : '#f59e0b', boxShadow: overview.trading_active ? '0 0 8px #10b981' : '0 0 8px #f59e0b' }}></span>
          <strong>{statusText}</strong> — Bot {overview.bot_process_running ? 'running' : 'not running'} · {overview.open_positions || 0} open position(s)
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 8px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <KPIBar kpis={kpis} />
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 10, padding: '0 16px 14px' }}>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, height: 240 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Capital Growth ({rangeLabel})</h3>
            <div style={{ display: 'flex', gap: 4 }}>
              {Object.keys(capitalRanges).map(p => (
                <button
                  key={p}
                  className={cls('btn', 'sm', p === capitalRange && 'primary')}
                  style={{ padding: '3px 8px', fontSize: 10.5 }}
                  onClick={() => setCapitalRange(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div style={{ height: 180 }}>
            {chartData.length ? <CapitalChart data={chartData} /> : <div className="empty" style={{ height: '100%', display: 'grid', placeItems: 'center' }}>No capital history yet.</div>}
          </div>
        </div>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, height: 240 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Win/Loss Distribution</h3>
            <span style={{ fontSize: 11, color: 'var(--text-2)' }}>Today · {winRate.toFixed(1)}% win rate</span>
          </div>
          <div style={{ height: 180 }}><WinLossDonut wins={wins} losses={losses} /></div>
        </div>
      </div>
    </>
  );
}

// ============ Open Positions ============
function OpenPositionsPanel() {
  const [positions, setPositions] = useS([]);
  const [msg, setMsg] = useS('Loading open positions...');
  const [loading, setLoading] = useS(false);
  const [sort, setSort] = useS({ key: 'opened', dir: 'desc' });
  const sortRef = useR({ key: 'opened', dir: 'desc' });
  const { open } = useWindows();

  const mapPos = (p) => ({
    id: p.trade_id || p.id || '',
    opened: p.entry_time ? String(p.entry_time).replace('T', ' ').slice(5, 16) : '—',
    openedRaw: p.entry_time || '',
    symbol: p.symbol || '?',
    type: (p.asset_class || 'crypto').replace(/^./, c => c.toUpperCase()),
    dir: String(p.direction || p.side || 'long').toUpperCase(),
    entry: Number(p.entry_price || 0),
    current: Number(p.current_price || p.entry_price || 0),
    sl: Number(p.stop_loss || p.entry_price || 0),
    tp: Number(p.take_profit || p.entry_price || 0),
    pnlD: Number(p.unrealized_pnl || 0),
    pnlP: Number(p.pnl_pct || 0),
    toSL: Number(p.distance_to_sl || 0),
    toTP: Number(p.distance_to_tp || 0),
  });
  const sortValue = (row, key) => {
    if (key === 'opened') {
      const parsed = Date.parse(row.openedRaw);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    if (['entry', 'current', 'sl', 'tp', 'pnlD', 'pnlP', 'toSL', 'toTP'].includes(key)) return Number(row[key] || 0);
    return String(row[key] || '').toLowerCase();
  };
  const applySort = (rows, nextSort) => {
    const dir = nextSort.dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = sortValue(a, nextSort.key);
      const bv = sortValue(b, nextSort.key);
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return String(a.symbol || '').localeCompare(String(b.symbol || ''));
    });
  };
  const loadPositions = async (requestedSort) => {
    const nextSort = requestedSort?.key ? requestedSort : sortRef.current;
    setLoading(true);
    try {
      const params = new URLSearchParams({ sort_by: nextSort.key, sort_dir: nextSort.dir });
      const data = await panelApi(`/api/open_positions?${params.toString()}`);
      const rows = Array.isArray(data.positions) ? data.positions.map(mapPos) : [];
      setPositions(applySort(rows, sortRef.current || nextSort));
      setMsg(rows.length ? '' : 'No open positions.');
    } catch (e) {
      setMsg(`Open positions failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };
  useE(() => {
    loadPositions();
    const t = setInterval(() => loadPositions(), 10000);
    return () => clearInterval(t);
  }, []);

  const forceSort = (key) => {
    const current = sortRef.current || sort;
    const next = { key, dir: current.key === key && current.dir === 'asc' ? 'desc' : 'asc' };
    sortRef.current = next;
    setSort(next);
    setPositions(rows => applySort(rows, next));
    setMsg(`Sorting by ${key} ${next.dir}...`);
    loadPositions(next);
  };
  useE(() => {
    const handler = (e) => {
      const target = e.target.closest?.('[data-pos-sort]');
      if (!target) return;
      e.preventDefault();
      e.stopPropagation();
      forceSort(target.dataset.posSort);
    };
    document.addEventListener('pointerdown', handler, true);
    return () => document.removeEventListener('pointerdown', handler, true);
  }, []);
  const SortButton = ({ k, children }) => (
    <button
      data-pos-sort={k}
      className={cls('btn sm', sort.key === k ? 'primary' : 'ghost')}
      title={`Sort by ${children}`}
    >
      {children}{sort.key === k ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
    </button>
  );
  const SortHead = ({ k, children, num }) => (
    <th
      data-pos-sort={k}
      className={num ? 'num' : ''}
      style={{ cursor: 'pointer', userSelect: 'none' }}
    >
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, justifyContent: num ? 'flex-end' : 'flex-start', width: '100%' }}>
        <span>{children}</span>
        {sort.key === k && <span style={{ color: 'var(--accent-bright)', fontSize: 10 }}>{sort.dir === 'asc' ? '▲' : '▼'}</span>}
      </span>
    </th>
  );

  return (
    <div className="panel-section" style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 3 }}>Open Positions</h3>
          <div className="panel-sub" style={{ margin: 0 }}>
            {loading ? 'Loading live positions...' : `${positions.length} active`} · Sorted by {sort.key} {sort.dir} · sort v2
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <SortButton k="opened">Opened</SortButton>
          <SortButton k="symbol">Symbol</SortButton>
          <SortButton k="pnlD">Unreal P&L</SortButton>
          <button className="btn ghost sm" onClick={() => open('manage-positions')}><Icon name="sliders" size={12} />Manage Positions</button>
          <button className="btn sm" onClick={() => loadPositions()}><Icon name="refresh" size={12} />Refresh</button>
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 10px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <SortHead k="opened">Opened</SortHead><SortHead k="symbol">Symbol</SortHead><SortHead k="type">Type</SortHead><SortHead k="dir">Dir</SortHead>
            <SortHead k="entry" num>Entry</SortHead><SortHead k="current" num>Current</SortHead><SortHead k="sl" num>SL</SortHead><SortHead k="tp" num>TP</SortHead>
            <SortHead k="pnlD" num>Unreal P&L</SortHead><SortHead k="pnlP" num>P&L %</SortHead><SortHead k="toSL" num>→ SL</SortHead><SortHead k="toTP" num>→ TP</SortHead>
          </tr></thead>
          <tbody>
            {positions.map((p, i) => (
              <tr key={p.id || `${p.symbol}-${p.openedRaw}-${p.entry}-${i}`}>
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
  const [form, setForm] = useS({ symbol: '', size: '2000.00', sl: '1.50', dir: 'long', broker: '', tp: '3.00', asset: 'stock', overnight: false, label: 'manual' });
  const [cfg, setCfg] = useS({ brokers: ['alpaca', 'coinbase', 'kraken', 'paper'], directions: ['long', 'short'], asset_classes: ['stock', 'crypto'], default_broker: 'alpaca' });
  const [preview, setPreview] = useS(null);
  const [previewMsg, setPreviewMsg] = useS('');
  const [msg, setMsg] = useS('');
  const [busy, setBusy] = useS(false);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  useE(() => {
    let live = true;
    panelApi('/api/manual_trade/config')
      .then(data => {
        if (!live) return;
        const brokers = Array.isArray(data.brokers) && data.brokers.length ? data.brokers : cfg.brokers;
        setCfg({ ...data, brokers });
        setForm(f => ({ ...f, broker: f.broker && brokers.includes(f.broker) ? f.broker : (data.default_broker || brokers[0]) }));
      })
      .catch(() => setForm(f => ({ ...f, broker: f.broker || 'alpaca' })));
    return () => { live = false; };
  }, []);
  useE(() => {
    const symbol = form.symbol.trim();
    const size = Number(form.size);
    const sl = Number(form.sl);
    const tp = Number(form.tp);
    setPreview(null);
    if (!symbol || !size || !sl || !tp) {
      setPreviewMsg('');
      return;
    }
    setPreviewMsg('Fetching live price...');
    const t = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          symbol,
          asset: form.asset,
          dir: form.dir,
          size: form.size,
          sl: form.sl,
          tp: form.tp,
        });
        const data = await panelApi(`/api/manual_trade/preview?${params.toString()}`);
        setPreview(data);
        setPreviewMsg('');
      } catch (e) {
        setPreviewMsg(e.message);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [form.symbol, form.asset, form.dir, form.size, form.sl, form.tp]);
  const openTrade = async () => {
    setBusy(true);
    setMsg('Submitting manual trade...');
    try {
      const data = await panelApi('/api/trades/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
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
        <div className="field"><label>Direction</label><select className="select input" value={form.dir} onChange={e => set('dir', e.target.value)}>{(cfg.directions || MOCK.DIRECTIONS).map(d => <option key={d}>{d}</option>)}</select></div>
        <div className="field"><label>Broker / Route Label</label><select className="select input" value={form.broker} onChange={e => set('broker', e.target.value)}>{(cfg.brokers || MOCK.BROKERS).map(b => <option key={b}>{b}</option>)}</select></div>
        <div className="field"><label>Take Profit %</label><input className="input" value={form.tp} onChange={e => set('tp', e.target.value)} /></div>
      </div>
      <div className="grid-3" style={{ marginBottom: 16 }}>
        <div className="field"><label>Asset Class</label><select className="select input" value={form.asset} onChange={e => set('asset', e.target.value)}>{(cfg.asset_classes || ['stock', 'crypto']).map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label style={{ visibility: 'hidden' }}>—</label><label className="checkbox" style={{ paddingTop: 8 }}><input type="checkbox" checked={form.overnight} onChange={e => set('overnight', e.target.checked)} /> Hold Overnight (Day Trade)</label></div>
        <div className="field"><label>Strategy Label</label><input className="input" value={form.label} onChange={e => set('label', e.target.value)} /></div>
      </div>
      {(preview || previewMsg) && (
        <div style={{ background: preview ? 'rgba(34, 197, 94, 0.10)' : 'var(--bg-2)', border: `1px solid ${preview ? 'rgba(34, 197, 94, 0.28)' : 'var(--border)'}`, borderRadius: 'var(--radius)', padding: 12, marginBottom: 14, fontSize: 12, lineHeight: 1.7 }}>
          {preview ? (
            <>
              <div><strong>Live Price:</strong> <span style={{ fontFamily: 'var(--mono)' }}>{fmt$(Number(preview.entry_price || 0), 6)}</span></div>
              <div><strong>Stop Loss:</strong> <span style={{ fontFamily: 'var(--mono)', color: 'var(--red)' }}>{fmt$(Number(preview.stop_loss || 0), 6)}</span> <span style={{ color: 'var(--text-2)' }}> / </span><strong>Take Profit:</strong> <span style={{ fontFamily: 'var(--mono)', color: 'var(--green)' }}>{fmt$(Number(preview.take_profit || 0), 6)}</span></div>
              <div><strong>Position:</strong> <span style={{ fontFamily: 'var(--mono)' }}>{Number(preview.quantity || 0).toFixed(4)} units @ {fmt$(Number(preview.entry_price || 0), 6)}</span></div>
            </>
          ) : (
            <span style={{ color: 'var(--text-2)' }}>{previewMsg}</span>
          )}
        </div>
      )}
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
    if (key === 'result') return Number(row.pnl || 0) > 0 ? 1 : 0;
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
            {sortedTrades.map((t, i) => {
              const resultClass = Number(t.pnl || 0) > 0 ? 'win' : 'loss';
              const resultText = Number(t.pnl || 0) > 0 ? 'Win' : 'Loss';
              const rowKey = t.trade_id || t.id || `${t.symbol}-${t.opened}-${t.closed}-${t.entry_price}-${t.exit_price}-${i}`;
              return (
                <tr key={rowKey}>
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
                  <td className="result-cell"><span className={cls('pill', 'result-pill', resultClass)}>{resultText}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ Recent Daily Performance ============
function DailyPerfPanel() {
  const [rows, setRows] = useS([]);
  const [msg, setMsg] = useS('Loading daily performance...');
  const [range, setRange] = useS('30D');
  const [sort, setSort] = useS({ key: 'date', dir: 'desc' });
  const loadDaily = async () => {
    try {
      const data = await panelApi('/api/overview');
      const perf = Array.isArray(data.daily_performance) ? data.daily_performance : [];
      setRows(perf);
      setMsg(perf.length ? '' : 'No daily summaries yet.');
    } catch (e) {
      setMsg(`Daily performance failed: ${e.message}`);
    }
  };
  useE(() => {
    loadDaily();
    const t = setInterval(loadDaily, 30000);
    return () => clearInterval(t);
  }, []);
  const ranges = {
    '7D': { label: '7 sessions', days: 7 },
    '30D': { label: '30 sessions', days: 30 },
    '90D': { label: '90 sessions', days: 90 },
    'YTD': { label: 'YTD', ytd: true },
  };
  const visibleRows = useM(() => {
    const parsed = rows
      .map(r => ({ ...r, _date: new Date(r.date) }))
      .filter(r => r._date instanceof Date && !isNaN(r._date.getTime()));
    if (!parsed.length) return [];
    const latest = parsed.reduce((max, r) => r._date > max ? r._date : max, parsed[0]._date);
    const selected = ranges[range] || ranges['30D'];
    const cutoff = selected.ytd
      ? new Date(latest.getFullYear(), 0, 1)
      : new Date(latest.getTime() - (selected.days - 1) * 86400000);
    const filtered = parsed.filter(r => r._date >= cutoff);
    const dir = sort.dir === 'asc' ? 1 : -1;
    const numeric = ['trades', 'wins', 'losses', 'win_rate', 'pnl', 'pnl_pct', 'capital'];
    return filtered.sort((a, b) => {
      const av = sort.key === 'date' ? a._date.getTime() : numeric.includes(sort.key) ? Number(a[sort.key] || 0) : String(a[sort.key] || '').toLowerCase();
      const bv = sort.key === 'date' ? b._date.getTime() : numeric.includes(sort.key) ? Number(b[sort.key] || 0) : String(b[sort.key] || '').toLowerCase();
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
  }, [rows, range, sort]);
  const totals = visibleRows.reduce((acc, d) => {
    acc.trades += Number(d.trades || 0);
    acc.wins += Number(d.wins || 0);
    acc.losses += Number(d.losses || 0);
    acc.pnl += Number(d.pnl || 0);
    return acc;
  }, { trades: 0, wins: 0, losses: 0, pnl: 0 });
  const toggleSort = (key) => setSort(s => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }));
  const SortHead = ({ k, children, num }) => (
    <th className={num ? 'num' : ''}>
      <button onClick={() => toggleSort(k)} style={{ all: 'unset', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4, justifyContent: num ? 'flex-end' : 'flex-start', width: '100%' }}>
        <span>{children}</span>
        {sort.key === k && <span style={{ color: 'var(--accent-bright)', fontSize: 10 }}>{sort.dir === 'asc' ? '▲' : '▼'}</span>}
      </button>
    </th>
  );

  return (
    <div style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div className="panel-sub" style={{ margin: 0 }}>
          {visibleRows.length} of {rows.length} sessions · {totals.trades} trades · {totals.wins}W/{totals.losses}L · {fmt$Sign(totals.pnl)}
        </div>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {Object.keys(ranges).map(k => (
            <button key={k} className={cls('btn', 'sm', range === k ? 'primary' : 'ghost')} style={{ padding: '3px 8px', fontSize: 10.5 }} onClick={() => setRange(k)}>
              {k}
            </button>
          ))}
          <button className="btn ghost sm" onClick={loadDaily}><Icon name="refresh" size={12} />Refresh</button>
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 10px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <SortHead k="date">Date</SortHead><SortHead k="trades" num>Trades</SortHead><SortHead k="wins" num>Wins</SortHead><SortHead k="losses" num>Losses</SortHead><SortHead k="win_rate" num>Win Rate</SortHead><SortHead k="pnl" num>P&L $</SortHead><SortHead k="pnl_pct" num>P&L %</SortHead><SortHead k="capital" num>Capital</SortHead>
          </tr></thead>
          <tbody>
            {visibleRows.map((d) => (
              <tr key={d.date || `${d.trades}-${d.pnl}-${d.capital}`}>
                <td><strong>{d.date || '—'}</strong></td>
                <td className="num">{d.trades}</td>
                <td className="num pos">{d.wins}</td>
                <td className="num neg">{d.losses}</td>
                <td className="num">{Number(d.win_rate || 0).toFixed(1)}%</td>
                <td className={cls('num', d.pnl > 0 && 'pos', d.pnl < 0 && 'neg')}>{fmt$Sign(Number(d.pnl || 0))}</td>
                <td className={cls('num', d.pnl_pct > 0 && 'pos', d.pnl_pct < 0 && 'neg')}>{fmtP(Number(d.pnl_pct || 0))}</td>
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
  const [msg, setMsg] = useS('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const run = async () => {
    setRunning(true);
    setResult(null);
    setMsg('Running backtest...');
    try {
      const data = await panelApi('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      setResult(data);
      setMsg(data.message || 'Backtest complete.');
    } catch (e) {
      setMsg(`Backtest failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
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
      {msg && <div style={{ marginBottom: 10, fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}

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
      const data = await panelApi('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q }),
      });
      setMsgs(m => [...m, { role: 'bot', text: data.reply || data.message || "No response returned." }]);
    } catch (e) {
      setMsgs(m => [...m, { role: 'bot', text: `Chat failed: ${e.message}` }]);
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
