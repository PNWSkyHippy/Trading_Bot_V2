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
const csvCell = (v) => {
  const text = v === null || v === undefined ? '' : String(v);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};
const exportCsv = (filename, columns, rows) => {
  const body = [
    columns.map(c => csvCell(c.label)).join(','),
    ...rows.map(row => columns.map(c => csvCell(typeof c.value === 'function' ? c.value(row) : row[c.value])).join(',')),
  ].join('\r\n');
  const blob = new Blob([body], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};
window.exportCsv = exportCsv;

// ============ TblWrap — table container with mirrored top scrollbar ============
// Renders a thin native scrollbar above the table so users don't have to scroll
// to the bottom to pan wide tables.  Mouse-wheel vertical scroll is unaffected.
function TblWrap({ children }) {
  const topRef   = useR(null);
  const bodyRef  = useR(null);
  const dummyRef = useR(null);

  useE(() => {
    const top   = topRef.current;
    const body  = bodyRef.current;
    const dummy = dummyRef.current;
    if (!top || !body || !dummy) return;

    // Keep dummy width in sync with actual table scrollWidth
    const syncWidth = () => { dummy.style.width = body.scrollWidth + 'px'; };

    // Bidirectional scroll — the `!==` guard prevents infinite bounce
    const onTop  = () => { if (body.scrollLeft !== top.scrollLeft)  body.scrollLeft  = top.scrollLeft; };
    const onBody = () => { if (top.scrollLeft  !== body.scrollLeft) top.scrollLeft   = body.scrollLeft; };

    top.addEventListener('scroll',  onTop,  { passive: true });
    body.addEventListener('scroll', onBody, { passive: true });

    const ro = new ResizeObserver(syncWidth);
    ro.observe(body);   // fires on panel resize
    syncWidth();        // initial size

    return () => {
      top.removeEventListener('scroll',  onTop);
      body.removeEventListener('scroll', onBody);
      ro.disconnect();
    };
  }, []);

  return (
    <div>
      {/* Top scrollbar mirror — just tall enough for the native scroll handle */}
      <div ref={topRef} style={{
        overflowX: 'auto', overflowY: 'hidden',
        height: 10, marginBottom: -1,
      }}>
        <div ref={dummyRef} style={{ height: 1 }} />
      </div>
      {/* Actual scrollable table area */}
      <div ref={bodyRef} className="tbl-wrap">
        {children}
      </div>
    </div>
  );
}

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
        plugins: {
          legend: {
            position: 'bottom',
            onClick: null,
            labels: { color: '#b8bfca', font: { size: 11 }, boxWidth: 10, padding: 12 }
          },
          tooltip: { backgroundColor: '#161a1f', borderColor: '#232830', borderWidth: 1, padding: 10 }
        }
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
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
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
              <button
                className="btn ghost sm"
                style={{ padding: '3px 8px', fontSize: 10.5 }}
                title="Export capital history to CSV"
                onClick={() => exportCsv(`capital-growth-${capitalRange}.csv`, [
                  { label: 'Date', value: r => r.date },
                  { label: 'Capital', value: r => Number(r.capital).toFixed(2) },
                ], chartData.map(d => ({ date: d.date.toISOString().slice(0, 10), capital: d.capital })))}
              >
                <Icon name="download" size={10} />CSV
              </button>
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
  const [refreshing, setRefreshing] = useS(false);
  const [lastRefresh, setLastRefresh] = useS('');
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
    slRaised: Number(p.sl_raise_count || 0),
    tpExt:    Number(p.tp_ext_count   || 0),
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
  const loadPositions = async (requestedSort, opts = {}) => {
    const manual = !!opts.manual;
    const nextSort = requestedSort?.key ? requestedSort : sortRef.current;
    setLoading(true);
    if (manual) {
      setRefreshing(true);
      setTimeout(() => setRefreshing(false), 650);
      setMsg('Refreshing open positions...');
    }
    try {
      const params = new URLSearchParams({ sort_by: nextSort.key, sort_dir: nextSort.dir });
      const data = await panelApi(`/api/open_positions?${params.toString()}`);
      const rows = Array.isArray(data.positions) ? data.positions.map(mapPos) : [];
      setPositions(applySort(rows, sortRef.current || nextSort));
      setMsg(rows.length ? '' : 'No open positions.');
      setLastRefresh(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
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
            {loading ? 'Loading live positions...' : `${positions.length} active`} · Sorted by {sort.key} {sort.dir}{lastRefresh ? ` · refreshed ${lastRefresh}` : ''} · sort v2
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <SortButton k="opened">Opened</SortButton>
          <SortButton k="symbol">Symbol</SortButton>
          <SortButton k="pnlD">Unreal P&L</SortButton>
          <button className="btn ghost sm" onClick={() => open('manage-positions')}><Icon name="sliders" size={12} />Manage Positions</button>
          <button className="btn ghost sm" onClick={() => exportCsv('open-positions.csv', [
            { label: 'Opened', value: 'opened' },
            { label: 'Symbol', value: 'symbol' },
            { label: 'Type', value: 'type' },
            { label: 'Dir', value: 'dir' },
            { label: 'Entry', value: r => fmtN(r.entry) },
            { label: 'Current', value: r => fmtN(r.current) },
            { label: 'SL', value: r => fmtN(r.sl) },
            { label: 'TP', value: r => fmtN(r.tp) },
            { label: 'Unreal P&L', value: r => r.pnlD.toFixed(2) },
            { label: 'P&L %', value: r => r.pnlP.toFixed(2) },
            { label: 'To SL %', value: r => r.toSL.toFixed(2) },
            { label: 'To TP %', value: r => r.toTP.toFixed(2) },
          ], positions)}><Icon name="download" size={12} />CSV</button>
          <button className="btn sm" onClick={() => loadPositions(null, { manual: true })}><Icon name="refresh" size={12} />{refreshing ? 'Refreshing...' : 'Refresh'}</button>
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 10px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <TblWrap>
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
                <td className="num muted" title={p.tpExt > 0 ? `Take-profit extended ${p.tpExt}× by momentum rider` : undefined}>
                  {fmtN(p.tp)}{p.tpExt > 0 && <span style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', background:'#e53935', color:'#fff', borderRadius:'50%', fontSize:9, fontWeight:700, width:14, height:14, marginLeft:4, lineHeight:1 }}>{p.tpExt}</span>}
                </td>
                <td className={cls('num', p.pnlD > 0 && 'pos', p.pnlD < 0 && 'neg')}>{fmt$Sign(p.pnlD)}</td>
                <td className={cls('num', p.pnlP > 0 && 'pos', p.pnlP < 0 && 'neg')}>{fmtP(p.pnlP)}</td>
                <td className="num muted">{p.toSL.toFixed(2)}%</td>
                <td className="num muted">{p.toTP.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TblWrap>
    </div>
  );
}

// ============ Manual Trade Entry ============
function ManualTradePanel() {
  const [form, setForm] = useS({ symbol: '', size: '2000.00', sl: '1.50', dir: 'long', broker: 'ibkr', tp: '3.00', asset: 'stock', overnight: false, label: 'manual' });
  const [cfg, setCfg] = useS({ brokers: ['ibkr', 'alpaca', 'coinbase', 'kraken', 'paper'], directions: ['long', 'short'], asset_classes: ['stock', 'crypto'], default_broker: 'ibkr' });
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
      .catch(() => setForm(f => ({ ...f, broker: f.broker || 'ibkr' })));
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
              <div>
                <strong>Live Price:</strong>{' '}
                <span style={{ fontFamily: 'var(--mono)' }}>{fmt$(Number(preview.entry_price || 0), 6)}</span>
                <span style={{ color: 'var(--text-2)', margin: '0 6px' }}>·</span>
                <span style={{ color: 'var(--text-2)' }}>Broker: </span>
                <strong style={{ fontFamily: 'var(--mono)' }}>{form.broker}</strong>
              </div>
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
  const [loading, setLoading] = useS(false);
  const [refreshing, setRefreshing] = useS(false);
  const [lastRefresh, setLastRefresh] = useS('');
  const [sort, setSort] = useS({ key: 'closed', dir: 'desc' });
  const sortRef = useR({ key: 'closed', dir: 'desc' });
  const apiBase = () => {
    const configured = (window.DASHBOARD_API_BASE || '').replace(/\/$/, '');
    if (configured) return configured;
    if (window.location.protocol === 'file:') return 'http://localhost:8125';
    return '';
  };
  const loadTrades = async ({ manual = false, quiet = false } = {}) => {
    setLoading(true);
    if (manual) {
      setRefreshing(true);
      setTimeout(() => setRefreshing(false), 650);
      setMsg('Refreshing trade log...');
    }
    try {
      const res = await fetch(`${apiBase()}/api/trade_log/today`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || data.error || `HTTP ${res.status}`);
      const rows = Array.isArray(data.trades) ? data.trades : [];
      setTrades(rows);
      setLastRefresh(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      setMsg(rows.length ? '' : 'No closed trades today.');
    } catch (e) {
      setMsg(`Trade log failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };
  useE(() => {
    loadTrades();
    const t = setInterval(() => loadTrades({ quiet: true }), 15000);
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
  const toggleSort = (key) => {
    const current = sortRef.current || sort;
    const next = { key, dir: current.key === key && current.dir === 'asc' ? 'desc' : 'asc' };
    sortRef.current = next;
    setSort(next);
  };
  useE(() => {
    const handler = (e) => {
      const target = e.target.closest?.('[data-trade-sort]');
      if (!target) return;
      e.preventDefault();
      e.stopPropagation();
      toggleSort(target.dataset.tradeSort);
    };
    document.addEventListener('pointerdown', handler, true);
    return () => document.removeEventListener('pointerdown', handler, true);
  }, []);
  const SortHead = ({ k, children, num }) => (
    <th
      data-trade-sort={k}
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
    <div style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="panel-sub" style={{ margin: 0 }}>
          {loading ? 'Refreshing closed trades...' : `${trades.length} closed trades today`} · Sorted by {sort.key} {sort.dir}{lastRefresh ? ` · refreshed ${lastRefresh}` : ''}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn ghost sm" onClick={() => exportCsv('todays-trade-log.csv', [
            { label: 'Opened', value: 'opened' },
            { label: 'Closed', value: 'closed' },
            { label: 'Duration', value: 'duration' },
            { label: 'Symbol', value: 'symbol' },
            { label: 'Dir', value: 'direction' },
            { label: 'Strategy', value: 'strategy' },
            { label: 'Entry', value: r => fmtN(r.entry_price) },
            { label: 'Exit', value: r => fmtN(r.exit_price) },
            { label: 'Reason', value: 'reason' },
            { label: 'P&L $', value: r => Number(r.pnl || 0).toFixed(2) },
            { label: 'P&L %', value: r => Number(r.pnl_pct || 0).toFixed(2) },
            { label: 'Result', value: r => Number(r.pnl || 0) > 0 ? 'Win' : 'Loss' },
          ], sortedTrades)}><Icon name="download" size={12} />CSV</button>
          <button className="btn ghost sm" onClick={() => loadTrades({ manual: true })}><Icon name="refresh" size={12} />{refreshing ? 'Refreshing...' : 'Refresh'}</button>
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 10px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <TblWrap>
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
                  <td className="num" title={t.tp_hit_count > 0 ? `Take-profit extended ${t.tp_hit_count}× by momentum rider` : undefined}>
                    {fmtN(t.exit_price)}{t.tp_hit_count > 0 && <span style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', background:'#e53935', color:'#fff', borderRadius:'50%', fontSize:9, fontWeight:700, width:14, height:14, marginLeft:4, lineHeight:1 }}>{t.tp_hit_count}</span>}
                  </td>
                  <td className="muted">{t.reason}</td>
                  <td className={cls('num', t.pnl > 0 && 'pos', t.pnl < 0 && 'neg')}>{fmt$Sign(t.pnl)}</td>
                  <td className={cls('num', t.pnl_pct > 0 && 'pos', t.pnl_pct < 0 && 'neg')}>{fmtP(t.pnl_pct)}</td>
                  <td className="result-cell"><span className={cls('pill', 'result-pill', resultClass)}>{resultText}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TblWrap>
    </div>
  );
}

// ============ Recent Daily Performance ============
function DailyPerfPanel() {
  const [rows, setRows] = useS([]);
  const [msg, setMsg] = useS('Loading daily performance...');
  const [loading, setLoading] = useS(false);
  const [refreshing, setRefreshing] = useS(false);
  const [lastRefresh, setLastRefresh] = useS('');
  const [range, setRange] = useS('30D');
  const [sort, setSort] = useS({ key: 'date', dir: 'desc' });
  const sortRef = useR({ key: 'date', dir: 'desc' });
  const loadDaily = async ({ manual = false } = {}) => {
    setLoading(true);
    if (manual) {
      setRefreshing(true);
      setTimeout(() => setRefreshing(false), 650);
      setMsg('Refreshing daily performance...');
    }
    try {
      const data = await panelApi('/api/overview');
      const perf = Array.isArray(data.daily_performance) ? data.daily_performance : [];
      setRows(perf);
      setLastRefresh(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      setMsg(perf.length ? '' : 'No daily summaries yet.');
    } catch (e) {
      setMsg(`Daily performance failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };
  useE(() => {
    loadDaily();
    const t = setInterval(() => loadDaily(), 30000);
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
  const toggleSort = (key) => {
    const current = sortRef.current || sort;
    const next = { key, dir: current.key === key && current.dir === 'asc' ? 'desc' : 'asc' };
    sortRef.current = next;
    setSort(next);
  };
  useE(() => {
    const handler = (e) => {
      const target = e.target.closest?.('[data-daily-sort]');
      if (!target) return;
      e.preventDefault();
      e.stopPropagation();
      toggleSort(target.dataset.dailySort);
    };
    document.addEventListener('pointerdown', handler, true);
    return () => document.removeEventListener('pointerdown', handler, true);
  }, []);
  const SortHead = ({ k, children, num }) => (
    <th
      data-daily-sort={k}
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
    <div style={{ padding: 0 }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div className="panel-sub" style={{ margin: 0 }}>
          {loading ? 'Refreshing daily performance...' : `${visibleRows.length} of ${rows.length} sessions`} · Sorted by {sort.key} {sort.dir} · {totals.trades} trades · {totals.wins}W/{totals.losses}L · {fmt$Sign(totals.pnl)}{lastRefresh ? ` · refreshed ${lastRefresh}` : ''}
        </div>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {Object.keys(ranges).map(k => (
            <button key={k} className={cls('btn', 'sm', range === k ? 'primary' : 'ghost')} style={{ padding: '3px 8px', fontSize: 10.5 }} onClick={() => setRange(k)}>
              {k}
            </button>
          ))}
          <button className="btn ghost sm" onClick={() => exportCsv(`recent-daily-performance-${range}.csv`, [
            { label: 'Date', value: 'date' },
            { label: 'Trades', value: 'trades' },
            { label: 'Wins', value: 'wins' },
            { label: 'Losses', value: 'losses' },
            { label: 'Win Rate', value: r => Number(r.win_rate || 0).toFixed(1) + '%' },
            { label: 'P&L $', value: r => Number(r.pnl || 0).toFixed(2) },
            { label: 'P&L %', value: r => Number(r.pnl_pct || 0).toFixed(2) },
            { label: 'Capital', value: r => Number(r.capital || 0).toFixed(2) },
          ], visibleRows)}><Icon name="download" size={12} />CSV</button>
          <button className="btn ghost sm" onClick={() => loadDaily({ manual: true })}><Icon name="refresh" size={12} />{refreshing ? 'Refreshing...' : 'Refresh'}</button>
        </div>
      </div>
      {msg && <div style={{ padding: '0 16px 10px', fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <TblWrap>
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
      </TblWrap>
    </div>
  );
}

// ============ Strategy Backtester ============
function BacktestCharts({ row }) {
  const equityRef = useR(null);
  const drawdownRef = useR(null);
  const returnsRef = useR(null);
  const chartsRef = useR([]);
  const curve = Array.isArray(row?.equity_curve) ? row.equity_curve : [];
  const sig = `${row?.symbol || ''}|${row?.strategy || ''}|${curve.length}|${curve[0]?.t || ''}|${curve[curve.length - 1]?.t || ''}`;
  useE(() => {
    chartsRef.current.forEach(c => c?.destroy?.());
    chartsRef.current = [];
    if (!window.Chart || !curve.length || !equityRef.current || !drawdownRef.current || !returnsRef.current) return;
    const labels = curve.map(p => p.t || '');
    const axis = {
      grid: { color: 'rgba(255,255,255,0.04)' },
      ticks: { color: '#7d8593', font: { size: 10, family: 'JetBrains Mono' }, maxRotation: 0, autoSkipPadding: 28 },
      border: { color: '#232830' },
    };
    const base = {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: '#161a1f', borderColor: '#232830', borderWidth: 1, titleColor: '#f3f5f8', bodyColor: '#b8bfca', padding: 10 },
      },
    };
    chartsRef.current = [
      new Chart(equityRef.current.getContext('2d'), {
        type: 'line',
        data: { labels, datasets: [{ data: curve.map(p => Number(p.e || 0)), borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.16)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.15 }] },
        options: { ...base, scales: { x: axis, y: { ...axis, ticks: { ...axis.ticks, callback: v => '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }) } } } },
      }),
      new Chart(drawdownRef.current.getContext('2d'), {
        type: 'line',
        data: { labels, datasets: [{ data: curve.map(p => Number(p.d || 0)), borderColor: '#f43f5e', backgroundColor: 'rgba(244, 63, 94, 0.16)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.12 }] },
        options: { ...base, scales: { x: axis, y: { ...axis, ticks: { ...axis.ticks, callback: v => Number(v).toFixed(2) + '%' } } } },
      }),
      new Chart(returnsRef.current.getContext('2d'), {
        type: 'bar',
        data: { labels, datasets: [{ data: curve.map(p => Number(p.r || 0)), backgroundColor: curve.map(p => Number(p.r || 0) >= 0 ? 'rgba(16, 185, 129, 0.78)' : 'rgba(244, 63, 94, 0.78)'), borderWidth: 0 }] },
        options: { ...base, scales: { x: axis, y: { ...axis, ticks: { ...axis.ticks, callback: v => Number(v).toFixed(2) + '%' } } } },
      }),
    ];
    return () => {
      chartsRef.current.forEach(c => c?.destroy?.());
      chartsRef.current = [];
    };
  }, [sig]);
  if (!curve.length) return <div className="empty" style={{ marginTop: 14 }}>No equity curve returned for the selected result.</div>;
  return (
    <div style={{ marginTop: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', margin: 0 }}>Equity Charts — {row.symbol} / {row.strategy} / Stop: {row.stop}</h3>
        <button className="btn ghost sm" onClick={() => exportCsv('backtest-equity-curve.csv', [
          { label: 'Time', value: 't' },
          { label: 'Equity', value: p => Number(p.e || 0).toFixed(2) },
          { label: 'Drawdown %', value: p => Number(p.d || 0).toFixed(4) },
          { label: 'Return Per Bar %', value: p => Number(p.r || 0).toFixed(4) },
        ], curve)}><Icon name="download" size={12} />Curve CSV</button>
      </div>
      <div style={{ height: 150, background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 8, marginBottom: 8 }}>
        <canvas ref={equityRef}></canvas>
      </div>
      <div className="grid-2" style={{ gap: 8 }}>
        <div style={{ height: 130, background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 8 }}><canvas ref={drawdownRef}></canvas></div>
        <div style={{ height: 130, background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 8 }}><canvas ref={returnsRef}></canvas></div>
      </div>
    </div>
  );
}

function BacktesterPanel() {
  const [form, setForm] = useS({ asset: 'Stocks', strategy: 'ALL strategies', tf: '1h', cap: '100000.00', symbol: 'ALL', duration: '90d (3mo)', mode: 'standard', lookback: '2', side: 'all', entry_mode: 'all', initial_stop: 'auto', trail: 'auto', commission: '', slippage: '' });
  const [running, setRunning] = useS(false);
  const [cancelling, setCancelling] = useS(false);
  const [result, setResult] = useS(null);
  const [msg, setMsg] = useS('');
  const [btConfig, setBtConfig] = useS(null);
  const [selectedRun, setSelectedRun] = useS(0);
  const [runLog, setRunLog] = useS([]);
  const [showRunLog, setShowRunLog] = useS(false);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const assetClasses = btConfig?.asset_classes || MOCK.ASSET_CLASSES.filter(a => a !== 'Both');
  const strategies = btConfig?.strategies || MOCK.STRATEGIES;
  const timeframes = btConfig?.timeframes || MOCK.TIMEFRAMES;
  const durations = btConfig?.durations || MOCK.DURATIONS;
  const symbolOptions = btConfig?.symbols?.[form.asset] || ['ALL', ...(form.asset === 'Crypto' ? ['BTC/USD', 'ETH/USD'] : ['AAPL', 'MSFT'])];
  const detailRows = Array.isArray(result?.results) ? result.results : [];
  const selectedDetail = detailRows[Math.min(selectedRun, Math.max(0, detailRows.length - 1))];
  const stopLabel = form.mode === 'trailing' ? `${form.lookback}-bar trailing stop` : 'standard stop';
  const backtestColumns = [
    { label: 'Symbol', value: 'symbol' },
    { label: 'Strategy', value: 'strategy' },
    { label: 'Stop', value: 'stop' },
    { label: 'Period', value: 'period' },
    { label: 'Start $', value: r => Number(r.starting_capital || 0).toFixed(2) },
    { label: 'End $', value: r => Number(r.ending_capital || 0).toFixed(2) },
    { label: 'Return %', value: r => Number(r.pnlP || 0).toFixed(2) },
    { label: 'Win Rate', value: r => Number(r.winRate || 0).toFixed(1) + '%' },
    { label: 'Trades', value: 'totalTrades' },
    { label: 'W/L', value: 'wl' },
    { label: 'Profit Factor', value: r => Number(r.profitFactor || 0).toFixed(2) },
    { label: 'Max Drawdown', value: r => Number(r.maxDD || 0).toFixed(2) + '%' },
    { label: 'Sharpe', value: r => Number(r.sharpe || 0).toFixed(2) },
    { label: 'Sortino', value: r => Number(r.sortino || 0).toFixed(2) },
    { label: 'Verdict', value: 'verdict' },
  ];
  const cancel = async () => {
    setCancelling(true);
    setRunLog(lines => [...lines.slice(-4), 'Sending cancel signal…']);
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 5000);
      const data = await panelApi('/api/backtest/cancel', { method: 'POST', signal: ctrl.signal });
      clearTimeout(timer);
      setRunLog(lines => [...lines.slice(-4), data.message || 'Cancel signal sent — waiting for checkpoint…']);
      setMsg(data.message || 'Cancel signal sent — waiting for checkpoint…');
    } catch (e) {
      setRunLog(lines => [...lines.slice(-4), `Cancel request did not return: ${e.message}`]);
      setMsg(`Cancel request did not return: ${e.message}`);
    } finally {
      setCancelling(false);
    }
  };
  const run = async () => {
    setRunning(true);
    setCancelling(false);
    setResult(null);
    setShowRunLog(true);
    const sideLabel  = form.side !== 'all'         ? ` · ${form.side}-only`             : '';
    const modeLabel  = form.entry_mode !== 'all'   ? ` · mode:${form.entry_mode}`       : '';
    const trailLabel = form.trail !== 'auto'        ? ` · trail:${form.trail}`           : '';
    const stopLabel2 = form.initial_stop !== 'auto' ? ` · init-stop:${form.initial_stop}`: '';
    setRunLog([
      `Queued ${form.symbol} / ${form.strategy} / ${form.tf} / ${form.duration}${sideLabel}${modeLabel}${trailLabel}${stopLabel2}`,
      'Sending request to backtest engine...',
    ]);
    setMsg('Running backtest...');
    try {
      const data = await panelApi('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      setResult(data.cancelled ? null : data);
      setSelectedRun(0);
      setRunLog(lines => [...lines.slice(-4), data.message || 'Backtest complete.']);
      setMsg(data.message || 'Backtest complete.');
      setTimeout(() => setShowRunLog(false), data.cancelled ? 2500 : 1400);
    } catch (e) {
      setRunLog(lines => [...lines.slice(-4), `Backtest failed: ${e.message}`]);
      setMsg(`Backtest failed: ${e.message}`);
      setShowRunLog(true);
    } finally {
      setRunning(false);
      setCancelling(false);
    }
  };
  useE(() => {
    panelApi('/api/backtest/config')
      .then(data => setBtConfig(data))
      .catch(() => {});
  }, []);
  useE(() => {
    if (!symbolOptions.includes(form.symbol)) set('symbol', 'ALL');
  }, [form.asset, btConfig]);
  useE(() => {
    if (!running) return;
    const beats = [
      'Fetching historical candles...',
      'Replaying strategy entries and exits...',
      'Applying stop rules and fees...',
      'Compiling portfolio statistics...',
      'Waiting for backtest engine response...',
    ];
    let i = 0;
    const t = setInterval(() => {
      setRunLog(lines => [...lines.slice(-4), beats[i++ % beats.length]]);
    }, 1800);
    return () => clearInterval(t);
  }, [running]);
  return (
    <div style={{ padding: 16 }}>
      <div className="panel-sub" style={{ marginBottom: 14 }}>Test any strategy on historical data. Compare Standard vs 2-Bar Trailing stop to find the best exit approach.</div>
      <div className="grid-4" style={{ marginBottom: 12 }}>
        <div className="field"><label>Asset Class</label><select className="select input" value={form.asset} onChange={e => setForm(f => ({ ...f, asset: e.target.value, symbol: 'ALL' }))}>{assetClasses.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Strategy</label><select className="select input" value={form.strategy} onChange={e => set('strategy', e.target.value)}>{strategies.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Timeframe</label><select className="select input" value={form.tf} onChange={e => set('tf', e.target.value)}>{timeframes.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Starting Capital ($)</label><input className="input" value={form.cap} onChange={e => set('cap', e.target.value)} /></div>
      </div>
      <div className="grid-3" style={{ marginBottom: 12 }}>
        <div className="field"><label>Symbol</label><select className="select input" value={form.symbol} onChange={e => set('symbol', e.target.value)}>{symbolOptions.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field"><label>Duration</label><select className="select input" value={form.duration} onChange={e => set('duration', e.target.value)}>{durations.map(a => <option key={a}>{a}</option>)}</select></div>
        <div className="field" style={{ justifyContent: 'flex-end', flexDirection: 'row', gap: 8 }}>
          <button className="btn primary full" onClick={run} disabled={running} style={{ flex: 1 }}>{running ? <><Icon name="cpu" size={13} /> Running…</> : <><Icon name="play" size={13} /> Run Backtest</>}</button>
          {running && <button className="btn danger" onClick={cancel} disabled={cancelling} style={{ whiteSpace: 'nowrap' }}>{cancelling ? 'Cancelling…' : <><Icon name="x" size={13} /> Cancel</>}</button>}
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
      <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12, padding: '10px 12px', background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
        <span style={{ fontSize: 11, color: 'var(--text-2)', whiteSpace: 'nowrap' }}>Entry Filters:</span>
        <div className="radio-group">
          <span style={{ fontSize: 11, color: 'var(--text-2)', marginRight: 4 }}>Side:</span>
          <label><input type="radio" name="side" checked={form.side === 'all'}   onChange={() => set('side', 'all')}   /> Both</label>
          <label><input type="radio" name="side" checked={form.side === 'long'}  onChange={() => set('side', 'long')}  /> Long only</label>
          <label><input type="radio" name="side" checked={form.side === 'short'} onChange={() => set('side', 'short')} /> Short only</label>
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label style={{ whiteSpace: 'nowrap', fontSize: 11 }}>Mode (adaptive):</label>
          <select className="select input" style={{ width: 120 }} value={form.entry_mode} onChange={e => set('entry_mode', e.target.value)}>
            <option value="all">All</option>
            <option value="trend">Trend only</option>
            <option value="mean_rev">Mean Rev only</option>
          </select>
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label style={{ whiteSpace: 'nowrap', fontSize: 11 }}>Initial Stop:</label>
          <select className="select input" style={{ width: 130 }} value={form.initial_stop} onChange={e => set('initial_stop', e.target.value)}>
            <option value="auto">Auto</option>
            <option value="percent">Fixed %</option>
            <option value="signal_structural">Structural (ATR)</option>
            <option value="two_bar">N-Bar</option>
          </select>
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label style={{ whiteSpace: 'nowrap', fontSize: 11 }}>Trail Mode:</label>
          <select className="select input" style={{ width: 110 }} value={form.trail} onChange={e => set('trail', e.target.value)}>
            <option value="auto">Auto</option>
            <option value="percent">% Ratchet</option>
            <option value="two_bar">N-Bar</option>
            <option value="none">None</option>
          </select>
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label style={{ whiteSpace: 'nowrap', fontSize: 11 }}>Commission %:</label>
          <input className="input" style={{ width: 60 }} placeholder="default" value={form.commission} onChange={e => set('commission', e.target.value)} />
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label style={{ whiteSpace: 'nowrap', fontSize: 11 }}>Slippage %:</label>
          <input className="input" style={{ width: 60 }} placeholder="default" value={form.slippage} onChange={e => set('slippage', e.target.value)} />
        </div>
      </div>
      {(running || showRunLog) && (
        <div className="bt-run-log" aria-label="Backtest status log">
          {runLog.slice(-5).map((line, i, arr) => (
            <div key={`${line}-${i}`} className={cls('bt-run-line', running && i === arr.length - 1 && 'active')}>
              <span></span>{line}
            </div>
          ))}
        </div>
      )}
      {msg && <div style={{ marginBottom: 10, fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}

      {result && (
        <div className="bt-result">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 12 }}>
            <div>
              <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Backtest Results · {form.duration}</h3>
              <div className="panel-sub" style={{ margin: 0 }}>
                {form.asset} {form.symbol}, {form.tf} candles, {stopLabel} · {detailRows.length} detailed run(s)
              </div>
            </div>
            <button className="btn ghost sm" onClick={() => exportCsv('backtest-results.csv', backtestColumns, detailRows)}>
              <Icon name="download" size={12} />CSV
            </button>
          </div>
          <div className="grid-4">
            <div className="bt-stat"><span className="label">Total Trades</span><span className="value">{result.totalTrades}</span></div>
            <div className="bt-stat"><span className="label">Win Rate</span><span className={cls('value', result.winRate >= 50 ? 'pos' : 'neg')}>{result.winRate}%</span></div>
            <div className="bt-stat"><span className="label">Total P&L</span><span className={cls('value', result.pnlD >= 0 ? 'pos' : 'neg')}>{fmt$Sign(result.pnlD)}</span></div>
            <div className="bt-stat"><span className="label">Return</span><span className={cls('value', result.pnlP >= 0 ? 'pos' : 'neg')}>{fmtP(result.pnlP)}</span></div>
            <div className="bt-stat"><span className="label">Sharpe Ratio</span><span className="value">{result.sharpe}</span></div>
            <div className="bt-stat"><span className="label">Max Drawdown</span><span className="value" style={{ color: 'var(--red)' }}>{fmtP(result.maxDD)}</span></div>
            <div className="bt-stat"><span className="label">Profit Factor</span><span className="value">{result.profitFactor}</span></div>
            <div className="bt-stat"><span className="label">Avg Win / Loss</span><span className="value" style={{ fontSize: 13 }}>{fmt$(result.avgWin)} / <span style={{ color: 'var(--red)' }}>{fmt$(result.avgLoss)}</span></span></div>
          </div>
          <div style={{ marginTop: 18 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Results Table</h3>
            <TblWrap>
              <table className="tbl">
                <thead><tr>
                  <th>Symbol</th><th>Strategy</th><th>Stop</th><th>Period</th><th className="num">Start $</th><th className="num">End $</th><th className="num">Return %</th><th className="num">Win Rate</th><th className="num">Trades</th><th>W/L</th><th className="num">Profit Factor</th><th className="num">Max Drawdown</th><th className="num">Sharpe</th><th className="num">Sortino</th><th>Verdict</th>
                </tr></thead>
                <tbody>
                  {detailRows.map((r, i) => (
                    <tr key={`${r.symbol}-${r.strategy}-${r.stop}-${r.period}-${i}`} onClick={() => setSelectedRun(i)} className={cls(selectedRun === i && 'bt-selected-row')} style={{ cursor: 'pointer' }}>
                      <td><strong>{r.symbol}</strong></td>
                      <td className="muted">{r.strategy}</td>
                      <td>{r.stop || 'Standard'}</td>
                      <td className="muted">{r.period}</td>
                      <td className="num">{fmt$(Number(r.starting_capital || 0))}</td>
                      <td className="num">{fmt$(Number(r.ending_capital || 0))}</td>
                      <td className={cls('num', r.pnlP > 0 && 'pos', r.pnlP < 0 && 'neg')}>{fmtP(Number(r.pnlP || 0))}</td>
                      <td className="num">{Number(r.winRate || 0).toFixed(1)}%</td>
                      <td className="num">{r.totalTrades}</td>
                      <td>{r.wl || `${r.wins || 0}W/${r.losses || 0}L`}</td>
                      <td className="num">{Number(r.profitFactor || 0).toFixed(2)}</td>
                      <td className={cls('num', r.maxDD < 0 && 'neg')}>{fmtP(Number(r.maxDD || 0))}</td>
                      <td className={cls('num', r.sharpe > 0 && 'pos', r.sharpe < 0 && 'neg')}>{Number(r.sharpe || 0).toFixed(2)}</td>
                      <td className={cls('num', r.sortino > 0 && 'pos', r.sortino < 0 && 'neg')}>{Number(r.sortino || 0).toFixed(2)}</td>
                      <td><span className={cls('pill', r.verdict === 'GO' ? 'win' : 'loss')}>{r.verdict === 'GO' ? 'GO' : 'TUNE'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TblWrap>
          </div>
          {selectedDetail && <BacktestCharts row={selectedDetail} />}
        </div>
      )}
      {!result && !running && <div className="empty">Configure parameters and click <strong>Run Backtest</strong> to see results.</div>}
    </div>
  );
}

// ============ Chat with Bot ============
const CHAT_LOCAL_COMMANDS = {
  'list commands': [
    'Available bot commands:',
    '  status               — capital, P&L, open positions',
    '  positions            — list open positions with P&L',
    '  performance          — win rate and P&L summary for today',
    '  trades today         — count of closed trades today',
    '  pause trading        — halt new trade entries',
    '  resume trading       — re-enable trade entries',
    '  restart bot          — restart the bot engine',
    '  ml status            — ML scorer stage and progress',
    '  list commands        — show this help (no AI call)',
    '  list commands auto   — compact quick-reference (no AI call)',
    '',
    'Tip: plain English also works — the bot understands natural language.',
  ].join('\n'),
  'list commands auto': [
    'Quick-reference (no AI):',
    '  status · positions · performance · trades today',
    '  pause trading · resume trading · restart bot',
    '  ml status · list commands · list commands auto',
  ].join('\n'),
};

function ChatPanel() {
  const [msgs, setMsgs] = useS([
    { role: 'bot', text: "Hi — I'm your trading bot. Ask me about active positions, performance, strategies, or have me pause/resume trading. What would you like to know?\n\nType  list commands  to see what I can do without calling AI." }
  ]);
  const [input, setInput] = useS('');
  const [thinking, setThinking] = useS(false);
  const endRef = useR(null);
  useE(() => endRef.current?.scrollIntoView({ block: 'nearest' }), [msgs, thinking]);
  const send = async () => {
    if (!input.trim() || thinking) return;
    const q = input.trim();
    setInput('');

    // Local command handling — no API call needed
    const localReply = CHAT_LOCAL_COMMANDS[q.toLowerCase()];
    if (localReply) {
      setMsgs(m => [...m, { role: 'user', text: q }, { role: 'bot', text: localReply }]);
      return;
    }

    setMsgs(m => [...m, { role: 'user', text: q }]);
    setThinking(true);
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
  const onChatKey = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();  // prevents workspace scroll-to-bottom on Enter
      send();
    }
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
        <input className="input" style={{ flex: 1 }} placeholder="Ask your bot anything… (type 'list commands' for help)" value={input} onChange={e => setInput(e.target.value)} onKeyDown={onChatKey} />
        <button className="btn primary" onClick={send} disabled={!input.trim() || thinking}><Icon name="send" size={13} /></button>
      </div>
    </div>
  );
}

// ============ Chart Panel ============
function calcEMA(bars, period) {
  if (!bars || bars.length < period) return [];
  const k = 2 / (period + 1);
  let ema = 0;
  const result = [];
  bars.forEach((b, i) => {
    if (i < period) {
      ema += b.close / period;
      if (i === period - 1) result.push({ time: b.time, value: ema });
    } else {
      ema = b.close * k + ema * (1 - k);
      result.push({ time: b.time, value: ema });
    }
  });
  return result;
}

function calcSMA(bars, period) {
  if (!bars || bars.length < period) return [];
  const result = [];
  let sum = 0;
  bars.forEach((b, i) => {
    sum += b.close;
    if (i >= period) sum -= bars[i - period].close;
    if (i >= period - 1) result.push({ time: b.time, value: sum / period });
  });
  return result;
}

function calcRSI(bars, period) {
  if (!bars || bars.length <= period) return [];
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = bars[i].close - bars[i - 1].close;
    if (d >= 0) gain += d; else loss -= d;
  }
  gain /= period; loss /= period;
  const result = [{ time: bars[period].time, value: loss === 0 ? 100 : 100 - (100 / (1 + gain / loss)) }];
  for (let i = period + 1; i < bars.length; i++) {
    const d = bars[i].close - bars[i - 1].close;
    gain = (gain * (period - 1) + Math.max(d, 0)) / period;
    loss = (loss * (period - 1) + Math.max(-d, 0)) / period;
    result.push({ time: bars[i].time, value: loss === 0 ? 100 : 100 - (100 / (1 + gain / loss)) });
  }
  return result;
}

function calcBB(bars, period, mult = 2) {
  if (!bars || bars.length < period) return { upper: [], mid: [], lower: [] };
  const upper = [], mid = [], lower = [];
  for (let i = period - 1; i < bars.length; i++) {
    const slice = bars.slice(i - period + 1, i + 1).map(b => b.close);
    const avg = slice.reduce((a, b) => a + b, 0) / period;
    const variance = slice.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / period;
    const sd = Math.sqrt(variance);
    mid.push({ time: bars[i].time, value: avg });
    upper.push({ time: bars[i].time, value: avg + sd * mult });
    lower.push({ time: bars[i].time, value: avg - sd * mult });
  }
  return { upper, mid, lower };
}

function calcMACD(bars, fast = 12, slow = 26, signal = 9, histUpColor = '#26a69a66', histDownColor = '#ef535066') {
  const fastE = calcEMA(bars, fast);
  const slowE = calcEMA(bars, slow);
  const slowByTime = new Map(slowE.map(p => [p.time, p.value]));
  const macd = fastE
    .filter(p => slowByTime.has(p.time))
    .map(p => ({ time: p.time, value: p.value - slowByTime.get(p.time) }));
  const signalInput = macd.map(p => ({ time: p.time, close: p.value }));
  const signalLine = calcEMA(signalInput, signal);
  const sigByTime = new Map(signalLine.map(p => [p.time, p.value]));
  const hist = macd
    .filter(p => sigByTime.has(p.time))
    .map(p => ({ time: p.time, value: p.value - sigByTime.get(p.time),
                 color: p.value >= sigByTime.get(p.time) ? histUpColor : histDownColor }));
  return { macd, signal: signalLine, hist };
}

function calcATR(bars, period = 14) {
  if (!bars || bars.length <= period) return [];
  const tr = [];
  for (let i = 0; i < bars.length; i++) {
    const prevClose = i > 0 ? bars[i - 1].close : bars[i].close;
    tr.push(Math.max(
      bars[i].high - bars[i].low,
      Math.abs(bars[i].high - prevClose),
      Math.abs(bars[i].low - prevClose)
    ));
  }
  let atr = tr.slice(1, period + 1).reduce((a, b) => a + b, 0) / period;
  const result = [{ time: bars[period].time, value: atr }];
  for (let i = period + 1; i < bars.length; i++) {
    atr = ((atr * (period - 1)) + tr[i]) / period;
    result.push({ time: bars[i].time, value: atr });
  }
  return result;
}

function calcADX(bars, period = 14) {
  if (!bars || bars.length <= period * 2) return [];
  const plusDM = [0], minusDM = [0], tr = [0];
  for (let i = 1; i < bars.length; i++) {
    const up = bars[i].high - bars[i - 1].high;
    const down = bars[i - 1].low - bars[i].low;
    plusDM.push(up > down && up > 0 ? up : 0);
    minusDM.push(down > up && down > 0 ? down : 0);
    tr.push(Math.max(
      bars[i].high - bars[i].low,
      Math.abs(bars[i].high - bars[i - 1].close),
      Math.abs(bars[i].low - bars[i - 1].close)
    ));
  }
  let atr = tr.slice(1, period + 1).reduce((a, b) => a + b, 0);
  let pDM = plusDM.slice(1, period + 1).reduce((a, b) => a + b, 0);
  let mDM = minusDM.slice(1, period + 1).reduce((a, b) => a + b, 0);
  const dx = [];
  for (let i = period + 1; i < bars.length; i++) {
    atr = atr - (atr / period) + tr[i];
    pDM = pDM - (pDM / period) + plusDM[i];
    mDM = mDM - (mDM / period) + minusDM[i];
    const pDI = atr ? 100 * pDM / atr : 0;
    const mDI = atr ? 100 * mDM / atr : 0;
    const denom = pDI + mDI;
    dx.push({ time: bars[i].time, value: denom ? 100 * Math.abs(pDI - mDI) / denom : 0 });
  }
  if (dx.length < period) return [];
  let adx = dx.slice(0, period).reduce((a, b) => a + b.value, 0) / period;
  const result = [{ time: dx[period - 1].time, value: adx }];
  for (let i = period; i < dx.length; i++) {
    adx = ((adx * (period - 1)) + dx[i].value) / period;
    result.push({ time: dx[i].time, value: adx });
  }
  return result;
}

function chartSourceValue(bar, source = 'hlc3') {
  if (source === 'open') return bar.open;
  if (source === 'high') return bar.high;
  if (source === 'low') return bar.low;
  if (source === 'close') return bar.close;
  if (source === 'hl2') return (bar.high + bar.low) / 2;
  if (source === 'ohlc4') return (bar.open + bar.high + bar.low + bar.close) / 4;
  return (bar.high + bar.low + bar.close) / 3;
}

function vwapAnchorKey(time, anchor = 'session') {
  const d = new Date(time * 1000);
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth();
  if (anchor === 'decade') return `${Math.floor(y / 10) * 10}`;
  if (anchor === 'year') return `${y}`;
  if (anchor === 'quarter') return `${y}-Q${Math.floor(m / 3) + 1}`;
  if (anchor === 'month') return `${y}-${m}`;
  if (anchor === 'week') {
    const day = d.getUTCDay() || 7;
    const monday = new Date(Date.UTC(y, m, d.getUTCDate() - day + 1));
    return monday.toISOString().slice(0, 10);
  }
  return d.toISOString().slice(0, 10);
}

function calcVWAP(bars, anchor = 'session', source = 'hlc3') {
  if (!bars || !bars.length) return [];
  let pv = 0, vol = 0;
  let activeAnchor = null;
  return bars.map(b => {
    const anchorKey = vwapAnchorKey(b.time, anchor);
    if (anchorKey !== activeAnchor) {
      activeAnchor = anchorKey;
      pv = 0;
      vol = 0;
    }
    const typical = chartSourceValue(b, source);
    const v = Number(b.volume || 0);
    pv += typical * v;
    vol += v;
    return { time: b.time, value: vol ? pv / vol : typical };
  });
}

function calcSuperTrend(bars, period = 10, mult = 3) {
  const atr = calcATR(bars, period);
  if (!atr.length) return { up: [], down: [] };
  const atrByTime = new Map(atr.map(p => [p.time, p.value]));
  const up = [], down = [];
  let finalUpper = 0, finalLower = 0, trendUp = true;
  for (let i = 0; i < bars.length; i++) {
    const a = atrByTime.get(bars[i].time);
    if (!a) continue;
    const hl2 = (bars[i].high + bars[i].low) / 2;
    const basicUpper = hl2 + mult * a;
    const basicLower = hl2 - mult * a;
    if (!finalUpper || basicUpper < finalUpper || bars[i - 1]?.close > finalUpper) finalUpper = basicUpper;
    if (!finalLower || basicLower > finalLower || bars[i - 1]?.close < finalLower) finalLower = basicLower;
    if (bars[i].close > finalUpper) trendUp = true;
    else if (bars[i].close < finalLower) trendUp = false;
    const point = { time: bars[i].time, value: trendUp ? finalLower : finalUpper };
    if (trendUp) up.push(point); else down.push(point);
  }
  return { up, down };
}

const STOCK_BROKERS  = [
  { id: 'alpaca',   label: 'Alpaca'   },
  { id: 'ibkr',     label: 'IBKR'     },
  { id: 'yfinance', label: 'yFinance' },
];
const CRYPTO_BROKERS = [
  { id: 'kraken',   label: 'Kraken'   },
  { id: 'coinbase', label: 'Coinbase' },
  { id: 'yfinance', label: 'yFinance' },
];

const chartLimitForTf = (tf) => ({
  '1m': 720,    // 12 hours
  '5m': 900,    // a little over 3 days
  '15m': 700,   // about 1 week
  '30m': 700,   // about 2 weeks
  '1h': 1000,   // about 6 weeks
  '4h': 900,    // about 5 months
  '1D': 420,    // about 14 months
}[tf] || 300);

const chartVisibleBarsForTf = (tf) => ({
  '1m': 180,
  '5m': 180,
  '15m': 160,
  '30m': 150,
  '1h': 180,
  '4h': 160,
  '1D': 180,
}[tf] || 160);

const DEFAULT_CHART_INDICATORS = [
  { id: 'ema9', type: 'EMA', period: 9, color: '#f59e0b', place: 'main', visible: true },
  { id: 'ema21', type: 'EMA', period: 21, color: '#60a5fa', place: 'main', visible: true },
  { id: 'rsi14', type: 'RSI', period: 14, overbought: 70, oversold: 30, color: '#a78bfa', place: 'lower1', visible: false },
  { id: 'adx14', type: 'ADX', period: 14, threshold: 20, color: '#f97316', thresholdColor: '#8b949e66', place: 'lower1', visible: false },
  { id: 'macd', type: 'MACD', period: 12, fast: 12, slow: 26, signal: 9, color: '#38bdf8', signalColor: '#f59e0b', histUpColor: '#26a69a66', histDownColor: '#ef535066', place: 'lower2', visible: false },
  { id: 'atr14', type: 'ATR', period: 14, color: '#14b8a6', place: 'lower2', visible: false },
  { id: 'vwap', type: 'VWAP', period: 1, anchor: 'session', source: 'hlc3', color: '#eab308', place: 'main', visible: false },
  { id: 'supertrend', type: 'SuperTrend', period: 10, mult: 3, color: '#22c55e', downColor: '#ef5350', place: 'main', visible: false },
];

const IND_TYPES = ['EMA', 'SMA', 'RSI', 'MACD', 'BB', 'ADX', 'ATR', 'VWAP', 'SuperTrend'];
const IND_PLACES = [
  ['main', 'Main'],
  ['lower1', 'Lower 1'],
  ['lower2', 'Lower 2'],
];
const IND_TYPE_DEFAULTS = {
  EMA:        { period: 50, color: '#22d3ee', place: 'main' },
  SMA:        { period: 50, color: '#94a3b8', place: 'main' },
  RSI:        { period: 14, overbought: 70, oversold: 30, color: '#a78bfa', place: 'lower1' },
  MACD:       { period: 12, fast: 12, slow: 26, signal: 9, color: '#38bdf8', signalColor: '#f59e0b', histUpColor: '#26a69a66', histDownColor: '#ef535066', place: 'lower2' },
  BB:         { period: 20, mult: 2, color: '#f472b6', midColor: '#8b949e88', place: 'main' },
  ADX:        { period: 14, threshold: 20, color: '#f97316', thresholdColor: '#8b949e66', place: 'lower1' },
  ATR:        { period: 14, color: '#14b8a6', place: 'lower2' },
  VWAP:       { period: 1, anchor: 'session', source: 'hlc3', color: '#eab308', place: 'main' },
  SuperTrend: { period: 10, mult: 3, color: '#22c55e', downColor: '#ef5350', place: 'main' },
};
const IND_PARAM_DEFS = {
  EMA:        [{ key: 'period', label: 'Period', min: 1, max: 300, fallback: 50 }],
  SMA:        [{ key: 'period', label: 'Period', min: 1, max: 300, fallback: 50 }],
  RSI:        [
    { key: 'period', label: 'Period', min: 1, max: 100, fallback: 14 },
    { key: 'overbought', label: 'High', min: 1, max: 100, fallback: 70 },
    { key: 'oversold', label: 'Low', min: 1, max: 100, fallback: 30 },
  ],
  MACD:       [
    { key: 'fast', label: 'Fast', min: 2, max: 80, fallback: 12 },
    { key: 'slow', label: 'Slow', min: 2, max: 120, fallback: 26 },
    { key: 'signal', label: 'Signal', min: 1, max: 60, fallback: 9 },
    { key: 'signalColor', label: 'Sig', type: 'color', fallback: '#f59e0b' },
    { key: 'histUpColor', label: 'Hist+', type: 'color', fallback: '#26a69a66' },
    { key: 'histDownColor', label: 'Hist-', type: 'color', fallback: '#ef535066' },
  ],
  BB:         [
    { key: 'period', label: 'Period', min: 1, max: 300, fallback: 20 },
    { key: 'mult', label: 'Std', min: 0.1, max: 10, step: 0.1, fallback: 2 },
    { key: 'midColor', label: 'Mid', type: 'color', fallback: '#8b949e88' },
  ],
  ADX:        [
    { key: 'period', label: 'Period', min: 1, max: 100, fallback: 14 },
    { key: 'threshold', label: 'Level', min: 1, max: 100, fallback: 20 },
    { key: 'thresholdColor', label: 'Level', type: 'color', fallback: '#8b949e66' },
  ],
  ATR:        [{ key: 'period', label: 'Period', min: 1, max: 100, fallback: 14 }],
  VWAP:       [
    { key: 'anchor', label: 'Anchor', type: 'select', fallback: 'session', options: [
      ['session', 'Session'],
      ['week', 'Week'],
      ['month', 'Month'],
      ['quarter', 'Quarter'],
      ['year', 'Year'],
      ['decade', 'Decade'],
    ] },
    { key: 'source', label: 'Source', type: 'select', fallback: 'hlc3', options: [
      ['open', 'Open'],
      ['high', 'High'],
      ['low', 'Low'],
      ['close', 'Close'],
      ['hl2', 'HL2'],
      ['hlc3', 'HLC3'],
      ['ohlc4', 'OHLC4'],
    ] },
  ],
  SuperTrend: [
    { key: 'period', label: 'ATR', min: 1, max: 100, fallback: 10 },
    { key: 'mult', label: 'Mult', min: 0.1, max: 10, step: 0.1, fallback: 3 },
    { key: 'downColor', label: 'Down', type: 'color', fallback: '#ef5350' },
  ],
};
const indicatorParamDefs = (type) => IND_PARAM_DEFS[type] || IND_PARAM_DEFS.EMA;
const PRICE_OVERLAY_INDICATORS = new Set(['EMA', 'SMA', 'BB', 'VWAP', 'SuperTrend']);
const LOWER_BAND_INDICATORS = new Set(['RSI', 'MACD', 'ADX', 'ATR']);
const indicatorPlaceOptions = (type) => (
  PRICE_OVERLAY_INDICATORS.has(type)
    ? [['main', 'Main']]
    : IND_PLACES.filter(([value]) => value !== 'main')
);
const effectiveIndicatorPlace = (ind) => (
  PRICE_OVERLAY_INDICATORS.has(ind.type)
    ? 'main'
    : (ind.place === 'lower2' ? 'lower2' : 'lower1')
);
const cloneIndicator = (ind) => ({ ...ind });
const cloneDefaultIndicators = () => DEFAULT_CHART_INDICATORS.map(cloneIndicator);
const isDefaultIndicator = (id) => DEFAULT_CHART_INDICATORS.some(ind => ind.id === id);
const makeCustomIndicatorId = (list) => {
  const existing = new Set((list || []).map(ind => ind.id));
  for (let i = 0; i < 1000; i += 1) {
    const id = `ind_${Date.now().toString(36)}_${i}`;
    if (!existing.has(id)) return id;
  }
  return `ind_${Math.random().toString(36).slice(2)}`;
};

const loadChartIndicators = () => {
  try {
    const saved = JSON.parse(localStorage.getItem('chart_indicators_v1') || 'null');
    if (Array.isArray(saved) && saved.length) {
      const savedIds = new Set(saved.map(ind => ind.id));
      return [
        ...saved.map(cloneIndicator),
        ...DEFAULT_CHART_INDICATORS.filter(ind => !savedIds.has(ind.id)).map(cloneIndicator),
      ];
    }
  } catch (_) {}
  return cloneDefaultIndicators();
};

const DRAW_TOOLS = [
  ['cursor', 'Cursor'],
  ['trend', 'Trend'],
  ['hline', 'H'],
  ['vline', 'V'],
  ['rect', 'Box'],
  ['eraser', 'Erase'],
];
const drawingStoreKey = (symbol, tf) => `chart_drawings_v1:${symbol}:${tf}`;
const makeDrawingId = () => `draw_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
const priceFormatForBars = (bars = []) => {
  const prices = bars
    .flatMap(b => [b.open, b.high, b.low, b.close])
    .map(Number)
    .filter(n => Number.isFinite(n) && n > 0);
  if (!prices.length) return { type: 'price', precision: 2, minMove: 0.01 };
  const mid = prices.reduce((a, b) => a + b, 0) / prices.length;
  if (mid < 0.001) return { type: 'price', precision: 8, minMove: 0.00000001 };
  if (mid < 0.01) return { type: 'price', precision: 6, minMove: 0.000001 };
  if (mid < 1) return { type: 'price', precision: 4, minMove: 0.0001 };
  return { type: 'price', precision: 2, minMove: 0.01 };
};
const drawingDistance = (d, pt) => {
  if (!d || !pt) return Infinity;
  if (d.type === 'hline') return Math.abs(d.p1.price - pt.price);
  if (d.type === 'vline') return Math.abs(d.p1.time - pt.time);
  const p1 = d.p1 || {};
  const p2 = d.p2 || p1;
  const tMin = Math.min(p1.time, p2.time), tMax = Math.max(p1.time, p2.time);
  const pMin = Math.min(p1.price, p2.price), pMax = Math.max(p1.price, p2.price);
  if (d.type === 'rect') {
    const inBox = pt.time >= tMin && pt.time <= tMax && pt.price >= pMin && pt.price <= pMax;
    if (inBox) return 0;
  }
  const tSpan = Math.max(1, tMax - tMin);
  const pSpan = Math.max(0.0000001, pMax - pMin);
  const midT = (tMin + tMax) / 2;
  const midP = (pMin + pMax) / 2;
  return Math.abs((pt.time - midT) / tSpan) + Math.abs((pt.price - midP) / pSpan);
};

function ChartPanel({ defaultSymbol }) {
  const [symbol, setSymbol]   = useS(defaultSymbol || 'BTC/USD');
  const [tf, setTf]           = useS('5m');
  const [broker, setBroker]   = useS('kraken');   // default for BTC/USD
  const [bars, setBars]       = useS([]);
  const [marks, setMarks]     = useS([]);
  const [openPositions, setOpenPositions] = useS([]);
  const [loading, setLoading] = useS(false);
  const [err, setErr]         = useS(null);
  const [searchVal, setSearch] = useS('');
  const [dropOpen, setDrop]   = useS(false);
  const [allSymbols, setAllSyms] = useS([]);
  const [indicators, setIndicators] = useS(loadChartIndicators);
  const [showIndEditor, setShowIndEditor] = useS(false);
  const [drawTool, setDrawTool] = useS('cursor');
  const [drawings, setDrawings] = useS([]);
  const [draftDrawing, setDraftDrawing] = useS(null);
  const [drawingsHidden, setDrawingsHidden] = useS(false);
  const [drawingsLocked, setDrawingsLocked] = useS(false);
  const [chartType, setChartType] = useS('candles'); // 'candles' | 'heikin_ashi' | 'line'

  const isCrypto = symbol.includes('/');

  const containerRef = useR(null);
  const drawingCanvasRef = useR(null);
  const lower1ContainerRef = useR(null);
  const lower2ContainerRef = useR(null);
  const chartRef     = useR(null);
  const lower1ChartRef = useR(null);
  const lower2ChartRef = useR(null);
  const candleRef    = useR(null);
  const volRef       = useR(null);
  const indicatorSeriesRef = useR([]);
  const livePriceLinesRef = useR([]);
  const rObsRef      = useR(null);
  const drawingsRef = useR([]);
  const draftDrawingRef = useR(null);
  const drawingsHiddenRef = useR(false);
  const drawingKeyRef = useR('');
  const marksRef = useR([]);
  const openPositionsRef = useR([]);
  const cleanBarsRef = useR([]);
  const chartSeriesTypeRef = useR('candles'); // tracks what type candleRef.current actually is

  // Init Lightweight Charts once on mount.
  // The Window component returns null when closed, so ChartPanel always mounts
  // with real pixel dimensions — no display:none timing issue.
  // We skip autoSize (it ignores manual resize() calls) and manage size ourselves
  // with an explicit ResizeObserver instead.
  useE(() => {
    if (!containerRef.current || !window.LightweightCharts) return;

    const LC        = window.LightweightCharts;
    const container = containerRef.current;
    const lower1Container = lower1ContainerRef.current;
    const lower2Container = lower2ContainerRef.current;
    const baseChartOptions = (el, showTime = true) => ({
      width:  el.offsetWidth  || 900,
      height: el.offsetHeight || (showTime ? 500 : 120),
      layout: { background: { type: 'solid', color: '#0d1117' }, textColor: '#8b949e', fontSize: 11 },
      grid:   { vertLines: { color: '#1a2035' }, horzLines: { color: '#1a2035' } },
      crosshair: { mode: LC.CrosshairMode.Normal },
      handleScale: { axisPressedMouseMove: { time: true, price: true }, mouseWheel: true, pinch: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      rightPriceScale: { borderColor: '#2a3347', autoScale: true },
      timeScale: {
        borderColor: '#2a3347', timeVisible: true, secondsVisible: false,
        // tickMarkFormatter controls the axis tick labels (timeFormatter only affects crosshair)
        tickMarkFormatter: (ts, tickMarkType) => {
          const d = new Date(ts * 1000);
          const tz = { timeZone: 'America/Los_Angeles' };
          // tickMarkType: 0=Year  1=Month  2=DayOfMonth  3=Time  4=TimeWithSeconds
          if (tickMarkType === 0) return d.toLocaleDateString('en-US', { ...tz, year: 'numeric' });
          if (tickMarkType === 1) return d.toLocaleDateString('en-US', { ...tz, month: 'short', year: 'numeric' });
          if (tickMarkType === 2) return d.toLocaleDateString('en-US', { ...tz, month: 'numeric', day: 'numeric' });
          return d.toLocaleTimeString('en-US', { ...tz, hour: 'numeric', minute: '2-digit', hour12: true });
        },
      },
      localization: {
        // Controls the crosshair time label
        timeFormatter: ts => new Date(ts * 1000).toLocaleString('en-US', {
          timeZone: 'America/Los_Angeles',
          month: 'numeric', day: 'numeric',
          hour: 'numeric', minute: '2-digit', hour12: true,
        }),
      },
    });

    const chart = LC.createChart(container, baseChartOptions(container, true));
    chartRef.current = chart;
    if (lower1Container) {
      lower1ChartRef.current = LC.createChart(lower1Container, baseChartOptions(lower1Container, false));
    }
    if (lower2Container) {
      lower2ChartRef.current = LC.createChart(lower2Container, baseChartOptions(lower2Container, false));
    }

    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (!range) return;
      try { lower1ChartRef.current?.timeScale().setVisibleLogicalRange(range); } catch (_) {}
      try { lower2ChartRef.current?.timeScale().setVisibleLogicalRange(range); } catch (_) {}
    });

    // ResizeObserver keeps chart in sync when user drags or maximizes the window
    const ro = new ResizeObserver(entries => {
      entries.forEach(entry => {
        const { width, height } = entry.contentRect;
        if (width <= 0 || height <= 0) return;
        if (entry.target === container && chartRef.current) chartRef.current.resize(width, height);
        if (entry.target === lower1Container && lower1ChartRef.current) lower1ChartRef.current.resize(width, height);
        if (entry.target === lower2Container && lower2ChartRef.current) lower2ChartRef.current.resize(width, height);
      });
    });
    ro.observe(container);
    if (lower1Container) ro.observe(lower1Container);
    if (lower2Container) ro.observe(lower2Container);
    rObsRef.current = ro;

    // Candle series
    candleRef.current = chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
      priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
    });

    // Volume in bottom 22% of the same pane
    volRef.current = chart.addHistogramSeries({
      priceFormat: { type: 'volume' }, priceScaleId: 'vol',
    });
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.05, bottom: 0.22 } });

    return () => {
      rObsRef.current?.disconnect();
      rObsRef.current = null;
      indicatorSeriesRef.current.forEach(item => {
        try { item.chart.removeSeries(item.series); } catch (_) {}
      });
      indicatorSeriesRef.current = [];
      livePriceLinesRef.current.forEach(line => {
        try { candleRef.current?.removePriceLine(line); } catch (_) {}
      });
      livePriceLinesRef.current = [];
      chart.remove();
      try { lower1ChartRef.current?.remove(); } catch (_) {}
      try { lower2ChartRef.current?.remove(); } catch (_) {}
      chartRef.current = null; candleRef.current = null; volRef.current = null;
      lower1ChartRef.current = null; lower2ChartRef.current = null;
    };
  }, []);

  useE(() => {
    try { localStorage.setItem('chart_indicators_v1', JSON.stringify(indicators)); } catch (_) {}
  }, [indicators]);

  useE(() => {
    const key = drawingStoreKey(symbol, tf);
    drawingKeyRef.current = key;
    try {
      const saved = JSON.parse(localStorage.getItem(key) || '[]');
      setDrawings(Array.isArray(saved) ? saved : []);
      setDraftDrawing(null);
    } catch (_) {
      setDrawings([]);
      setDraftDrawing(null);
    }
  }, [symbol, tf]);

  useE(() => {
    drawingsRef.current = drawings;
    const key = drawingStoreKey(symbol, tf);
    if (drawingKeyRef.current !== key) return;
    try { localStorage.setItem(key, JSON.stringify(drawings)); } catch (_) {}
  }, [drawings, symbol, tf]);

  useE(() => { draftDrawingRef.current = draftDrawing; }, [draftDrawing]);
  useE(() => { drawingsHiddenRef.current = drawingsHidden; }, [drawingsHidden]);
  useE(() => { marksRef.current = marks; }, [marks]);
  useE(() => { openPositionsRef.current = openPositions; }, [openPositions]);
  useE(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setDraftDrawing(null);
        setDrawTool('cursor');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Heikin Ashi conversion
  const toHeikinAshi = (bars) => {
    const ha = [];
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      const haClose = (b.open + b.high + b.low + b.close) / 4;
      const haOpen  = i === 0
        ? (b.open + b.close) / 2
        : (ha[i - 1].open + ha[i - 1].close) / 2;
      const haHigh  = Math.max(b.high, haOpen, haClose);
      const haLow   = Math.min(b.low,  haOpen, haClose);
      ha.push({ time: b.time, open: haOpen, high: haHigh, low: haLow, close: haClose, volume: b.volume });
    }
    return ha;
  };

  // Fetch data when symbol, timeframe, or broker changes
  useE(() => {
    let cancelled = false;
    // Clear stale bars immediately so old chart doesn't persist while loading
    setBars([]); setMarks([]); setOpenPositions([]);
    setLoading(true); setErr(null);
    const limit = chartLimitForTf(tf);
    panelApi(`/api/chart?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}&limit=${limit}&broker=${broker}`)
      .then(d => {
        if (cancelled) return;
        const b = d.bars || [];
        if (!b.length) setErr(`No data returned for ${symbol} (${broker})`);
        setBars(b);
        setMarks(d.markers || []);
        setOpenPositions(d.open_positions || []);
      })
      .catch(e => { if (!cancelled) setErr(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [symbol, tf, broker]);

  // Load symbol list once
  useE(() => {
    panelApi('/api/chart/symbols').then(d => setAllSyms(d.symbols || [])).catch(() => {});
  }, []);

  // Update chart whenever bars, markers, live positions, or indicator settings change
  useE(() => {
    if (!chartRef.current || !candleRef.current) return;

    // Always resize — even on empty bars (e.g. after asset-type switch that
    // changes toolbar height). requestAnimationFrame ensures the DOM has
    // fully reflowed (toolbar broker buttons may have swapped rows) before
    // we measure the container, so the canvas fills the correct area.
    const doResize = () => {
      if (!containerRef.current || !chartRef.current) return;
      const w = containerRef.current.offsetWidth;
      const h = containerRef.current.offsetHeight;
      if (w > 0 && h > 0) chartRef.current.resize(w, h);
      const w1 = lower1ContainerRef.current?.offsetWidth || 0;
      const h1 = lower1ContainerRef.current?.offsetHeight || 0;
      if (w1 > 0 && h1 > 0) lower1ChartRef.current?.resize(w1, h1);
      const w2 = lower2ContainerRef.current?.offsetWidth || 0;
      const h2 = lower2ContainerRef.current?.offsetHeight || 0;
      if (w2 > 0 && h2 > 0) lower2ChartRef.current?.resize(w2, h2);
    };
    requestAnimationFrame(doResize);

    if (!bars.length) return;  // nothing to plot, but resize above still ran

    // Deduplicate + sort on the client side as a safety net
    // (LightweightCharts v4 aborts CandlestickSeries.setData on duplicate timestamps)
    const seen = new Set();
    const cleanBars = bars
      .slice().sort((a, b) => a.time - b.time)
      .filter(b => { if (seen.has(b.time)) return false; seen.add(b.time); return true; });
    cleanBarsRef.current = cleanBars;
    const priceFormat = priceFormatForBars(cleanBars);

    // Recreate main series if chart type changed (lightweight-charts series type is immutable)
    if (chartSeriesTypeRef.current !== chartType && chartRef.current && candleRef.current) {
      try { chartRef.current.removeSeries(candleRef.current); } catch (_) {}
      if (chartType === 'line') {
        candleRef.current = chartRef.current.addLineSeries({
          color: '#26a69a', lineWidth: 2,
          priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
          lastValueVisible: true, priceLineVisible: true,
        });
      } else {
        candleRef.current = chartRef.current.addCandlestickSeries({
          upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
          wickUpColor: '#26a69a', wickDownColor: '#ef5350',
          priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
        });
      }
      chartSeriesTypeRef.current = chartType;
      // Re-attach price scale margins after series recreation
      try { chartRef.current.priceScale('right').applyOptions({ scaleMargins: { top: 0.05, bottom: 0.22 } }); } catch (_) {}
    }

    // Convert bars for display
    const displayBars = chartType === 'heikin_ashi' ? toHeikinAshi(cleanBars) : cleanBars;

    try {
      candleRef.current.applyOptions({ priceFormat });
      if (chartType === 'line') {
        candleRef.current.setData(displayBars.map(b => ({ time: b.time, value: b.close })));
      } else {
        candleRef.current.setData(displayBars);
      }
    }
    catch(e) { console.warn('ChartPanel series setData failed:', e); }

    volRef.current?.setData(cleanBars.map(b => ({
      time: b.time, value: b.volume || 0,
      color: b.close >= b.open ? '#26a69a55' : '#ef535055',
    })));

    indicatorSeriesRef.current.forEach(item => { try { item.chart.removeSeries(item.series); } catch (_) {} });
    indicatorSeriesRef.current = [];
    livePriceLinesRef.current.forEach(line => {
      try { candleRef.current.removePriceLine(line); } catch (_) {}
    });
    livePriceLinesRef.current = [];

    const panelForIndicator = (ind) => {
      if (['RSI', 'ADX'].includes(ind.type)) return ind.place === 'lower2' ? 'lower2' : 'lower1';
      if (['MACD', 'ATR'].includes(ind.type)) return ind.place === 'lower1' ? 'lower1' : 'lower2';
      return 'main';
    };
    const chartForPlace = (place) => {
      if (place === 'lower1') return lower1ChartRef.current || chartRef.current;
      if (place === 'lower2') return lower2ChartRef.current || chartRef.current;
      return chartRef.current;
    };
    const scaleForPlace = (place) => {
      if (place === 'main') return 'right';
      return 'right';
    };
    const addLine = (data, color, place, width = 1) => {
      if (!data.length) return;
      const targetChart = chartForPlace(place);
      if (!targetChart) return;
      const priceScaleId = scaleForPlace(place);
      const s = targetChart.addLineSeries({
        color, lineWidth: width, priceScaleId,
        priceFormat,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      });
      s.setData(data);
      indicatorSeriesRef.current.push({ chart: targetChart, series: s });
    };
    const addHist = (data, place) => {
      if (!data.length) return;
      const targetChart = chartForPlace(place);
      if (!targetChart) return;
      const s = targetChart.addHistogramSeries({
        priceScaleId: scaleForPlace(place),
        priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
      });
      s.setData(data);
      indicatorSeriesRef.current.push({ chart: targetChart, series: s });
    };

    chartRef.current.priceScale('right').applyOptions({
      autoScale: true,
      scaleMargins: { top: 0.05, bottom: 0.22 },
    });
    [chartRef.current, lower1ChartRef.current, lower2ChartRef.current].forEach(ch => {
      try {
        ch?.applyOptions({
          handleScale: { axisPressedMouseMove: { time: true, price: true }, mouseWheel: true, pinch: true },
          handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
        });
        ch?.priceScale('right').applyOptions({ autoScale: true });
      } catch (_) {}
    });

    indicators.filter(ind => ind.visible).forEach(ind => {
      const period = Math.max(1, Number(ind.period) || 14);
      const place = panelForIndicator(ind);
      const color = ind.color || '#60a5fa';
      if (ind.type === 'EMA') addLine(calcEMA(cleanBars, period), color, place);
      if (ind.type === 'SMA') addLine(calcSMA(cleanBars, period), color, place);
      if (ind.type === 'RSI') {
        addLine(calcRSI(cleanBars, period), color, place);
        addLine(cleanBars.map(b => ({ time: b.time, value: Number(ind.overbought) || 70 })), '#ef535055', place);
        addLine(cleanBars.map(b => ({ time: b.time, value: Number(ind.oversold) || 30 })), '#26a69a55', place);
      }
      if (ind.type === 'BB') {
        const bb = calcBB(cleanBars, period, Number(ind.mult) || 2);
        addLine(bb.upper, color, 'main');
        addLine(bb.mid, ind.midColor || '#8b949e88', 'main');
        addLine(bb.lower, color, 'main');
      }
      if (ind.type === 'MACD') {
        const m = calcMACD(
          cleanBars,
          Number(ind.fast) || 12,
          Number(ind.slow) || 26,
          Number(ind.signal) || 9,
          ind.histUpColor || '#26a69a66',
          ind.histDownColor || '#ef535066'
        );
        addHist(m.hist, place);
        addLine(m.macd, color, place);
        addLine(m.signal, ind.signalColor || '#f59e0b', place);
      }
      if (ind.type === 'ADX') {
        addLine(calcADX(cleanBars, period), color, place);
        addLine(cleanBars.map(b => ({ time: b.time, value: Number(ind.threshold) || 20 })), ind.thresholdColor || '#8b949e66', place);
      }
      if (ind.type === 'ATR') {
        addLine(calcATR(cleanBars, period), color, place);
      }
      if (ind.type === 'VWAP') {
        addLine(calcVWAP(cleanBars, ind.anchor || 'session', ind.source || 'hlc3'), color, 'main', 2);
      }
      if (ind.type === 'SuperTrend') {
        const st = calcSuperTrend(cleanBars, period, Number(ind.mult) || 3);
        addLine(st.up, color, 'main', 2);
        addLine(st.down, ind.downColor || '#ef5350', 'main', 2);
      }
    });

    const fmtLinePrice = (v) => {
      const n = Number(v || 0);
      if (!Number.isFinite(n) || n <= 0) return '';
      if (n < 0.01) return n.toFixed(6);
      if (n < 1) return n.toFixed(4);
      return n.toFixed(2);
    };
    const addLiveLine = (price, color, title, style = 0) => {
      const n = Number(price || 0);
      if (!Number.isFinite(n) || n <= 0) return;
      try {
        const line = candleRef.current.createPriceLine({
          price: n,
          color,
          lineWidth: 1,
          lineStyle: style,
          axisLabelVisible: true,
          title,
        });
        livePriceLinesRef.current.push(line);
      } catch (_) {}
    };
    openPositions.forEach((p, idx) => {
      const suffix = openPositions.length > 1 ? ` ${idx + 1}` : '';
      const dir = String(p.direction || '').toUpperCase();
      addLiveLine(p.entry_price, '#38bdf8', `${dir} entry${suffix} ${fmtLinePrice(p.entry_price)}`, 2);
      addLiveLine(p.stop_loss, '#ef5350', `SL${suffix} ${fmtLinePrice(p.stop_loss)}`, 1);
      addLiveLine(p.take_profit, '#22c55e', `TP${suffix} ${fmtLinePrice(p.take_profit)}`, 1);
    });

    // Lightweight's built-in markers are candle-time annotations only; they do
    // not honor the marker price.  Closed trade fills are drawn price-true on
    // the overlay canvas below.
    const liveMarkers = openPositions
      .filter(p => p.entry_ts)
      .map(p => ({
        time: p.entry_ts,
        type: 'live_entry',
        direction: p.direction || 'long',
        price: Number(p.entry_price || 0),
        pnl: 0,
      }));
    const processed = liveMarkers
      .filter(m => m.time)
      .sort((a, b) => a.time - b.time)
      .map(m => ({
        time: m.time,
        position: (m.type === 'entry' || m.type === 'live_entry')
          ? (m.direction === 'long' ? 'belowBar' : 'aboveBar')
          : (m.direction === 'long' ? 'aboveBar' : 'belowBar'),
        color: '#38bdf8',
        shape: (m.type === 'entry' || m.type === 'live_entry')
          ? (m.direction === 'long' ? 'arrowUp' : 'arrowDown')
          : 'circle',
        text: 'LIVE',
        size: 1,
      }));
    candleRef.current.setMarkers(processed);

    const visibleBars = Math.min(chartVisibleBarsForTf(tf), cleanBars.length);
    chartRef.current.timeScale().setVisibleLogicalRange({
      from: Math.max(0, cleanBars.length - visibleBars),
      to: cleanBars.length + 5,
    });
  }, [bars, marks, openPositions, tf, indicators, chartType]);

  // Symbol search filter
  const filtered = useM(() => {
    const q = searchVal.toLowerCase();
    if (!q) return allSymbols.slice(0, 40);
    return allSymbols.filter(s => s.symbol.toLowerCase().includes(q)).slice(0, 25);
  }, [allSymbols, searchVal]);

  const pickSymbol = (sym) => {
    const newIsCrypto = sym.includes('/');
    // Reset broker to sensible default when switching asset type
    if (newIsCrypto !== isCrypto) setBroker(newIsCrypto ? 'kraken' : 'ibkr');
    setSymbol(sym); setSearch(''); setDrop(false);
  };

  const drawOverlay = useC(() => {
    const canvas = drawingCanvasRef.current;
    const chart = chartRef.current;
    const series = candleRef.current;
    const host = containerRef.current;
    if (!canvas || !chart || !series || !host) return;
    const rect = host.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const toXY = (p) => {
      if (!p) return null;
      let x = chart.timeScale().timeToCoordinate(p.time);
      if ((x === null || x === undefined) && cleanBarsRef.current.length) {
        const t = Number(p.time);
        let nearest = cleanBarsRef.current[0];
        let best = Math.abs(Number(nearest.time) - t);
        for (const b of cleanBarsRef.current) {
          const dist = Math.abs(Number(b.time) - t);
          if (dist < best) {
            nearest = b;
            best = dist;
          }
        }
        x = chart.timeScale().timeToCoordinate(nearest.time);
      }
      const y = series.priceToCoordinate(p.price);
      if (x === null || x === undefined || y === null || y === undefined) return null;
      return { x, y };
    };
    const lineColor = '#f8fafc';
    const fillColor = 'rgba(56, 189, 248, 0.10)';
    const drawTradeFill = (m) => {
      const price = Number(m?.price || 0);
      if (!m?.time || !Number.isFinite(price) || price <= 0) return;
      const pt = toXY({ time: m.time, price });
      if (!pt) return;

      const isEntry    = m.type === 'entry' || m.type === 'live_entry';
      const isWin      = Number(m.pnl || 0) >= 0;
      const isLong     = (m.direction || '').toLowerCase() !== 'short';

      // Badge colours: entry=teal, win-exit=green, loss-exit=red
      const bgColor    = isEntry ? '#0e7490' : (isWin ? '#15803d' : '#9f1239');
      const borderCol  = isEntry ? '#22d3ee' : (isWin ? '#4ade80' : '#fb7185');
      const textColor  = '#ffffff';

      // Label: entry shows BUY/SELL, exit shows P&L
      const pnl        = Number(m.pnl || 0);
      const pnlStr     = pnl >= 0 ? `+$${pnl.toFixed(0)}` : `-$${Math.abs(pnl).toFixed(0)}`;
      const label      = isEntry
        ? (isLong ? '▲ BUY' : '▼ SELL')
        : (isWin  ? `✓ ${pnlStr}` : `✗ ${pnlStr}`);

      // Offset: entries go above price, exits below — separates same-bar rebuy+sell
      const offsetY    = isEntry ? -22 : 10;

      ctx.save();
      ctx.font = 'bold 10px JetBrains Mono, monospace';
      const textW      = ctx.measureText(label).width;
      const padX = 5, padY = 3;
      const bw = textW + padX * 2;
      const bh = 16;
      const bx = pt.x - bw / 2;
      const by = pt.y + offsetY - bh / 2;

      // Shadow for depth against any candle colour
      ctx.shadowColor   = 'rgba(0,0,0,0.7)';
      ctx.shadowBlur    = 4;
      ctx.shadowOffsetX = 1;
      ctx.shadowOffsetY = 1;

      // Filled badge
      ctx.fillStyle    = bgColor;
      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 3);
      ctx.fill();

      // Coloured border
      ctx.shadowBlur   = 0;
      ctx.strokeStyle  = borderCol;
      ctx.lineWidth    = 1.5;
      ctx.stroke();

      // Text
      ctx.fillStyle    = textColor;
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'middle';
      ctx.shadowBlur   = 0;
      ctx.fillText(label, pt.x, by + bh / 2);

      // Thin connector line from badge to price level
      ctx.strokeStyle  = borderCol;
      ctx.lineWidth    = 1;
      ctx.setLineDash([2, 2]);
      ctx.beginPath();
      ctx.moveTo(pt.x, by + (isEntry ? bh : 0));
      ctx.lineTo(pt.x, pt.y);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.restore();
    };

    [...marksRef.current, ...openPositionsRef.current
      .filter(p => p.entry_ts)
      .map(p => ({
        time: p.entry_ts,
        type: 'live_entry',
        price: Number(p.entry_price || 0),
        pnl: 0,
      }))
    ].forEach(drawTradeFill);

    if (drawingsHiddenRef.current) return;

    const drawOne = (d, isDraft = false) => {
      if (!d || !d.p1) return;
      const color = isDraft ? '#38bdf8' : (d.color || lineColor);
      ctx.save();
      ctx.lineWidth = isDraft ? 1.5 : 1.25;
      ctx.strokeStyle = color;
      ctx.fillStyle = d.fill || fillColor;
      ctx.setLineDash(isDraft ? [4, 4] : []);

      if (d.type === 'hline') {
        const y = series.priceToCoordinate(d.p1.price);
        if (y !== null && y !== undefined) {
          ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        }
      } else if (d.type === 'vline') {
        const x = chart.timeScale().timeToCoordinate(d.p1.time);
        if (x !== null && x !== undefined) {
          ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
        }
      } else if (d.type === 'rect') {
        const a = toXY(d.p1), b = toXY(d.p2 || d.p1);
        if (a && b) {
          const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
          const rw = Math.abs(a.x - b.x), rh = Math.abs(a.y - b.y);
          ctx.fillRect(x, y, rw, rh);
          ctx.strokeRect(x, y, rw, rh);
        }
      } else {
        const a = toXY(d.p1), b = toXY(d.p2 || d.p1);
        if (a && b) {
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          ctx.beginPath(); ctx.arc(a.x, a.y, 3, 0, Math.PI * 2); ctx.fill();
          ctx.beginPath(); ctx.arc(b.x, b.y, 3, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.restore();
    };
    drawingsRef.current.forEach(d => drawOne(d, false));
    drawOne(draftDrawingRef.current, true);
  }, []);

  useE(() => {
    drawOverlay();
    const chart = chartRef.current;
    const host = containerRef.current;
    if (!chart) return;
    const handler = () => requestAnimationFrame(drawOverlay);
    let ro = null;
    try { chart.timeScale().subscribeVisibleLogicalRangeChange(handler); } catch (_) {}
    if (host) {
      ro = new ResizeObserver(handler);
      ro.observe(host);
    }
    return () => {
      try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(handler); } catch (_) {}
      try { ro?.disconnect(); } catch (_) {}
    };
  }, [drawOverlay, drawings, draftDrawing, drawingsHidden, bars, marks, openPositions, tf, lower1Visible, lower2Visible]);

  const chartPointFromEvent = (e) => {
    const canvas = drawingCanvasRef.current;
    const chart = chartRef.current;
    const series = candleRef.current;
    if (!canvas || !chart || !series) return null;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const time = chart.timeScale().coordinateToTime(x);
    const price = series.coordinateToPrice(y);
    if (time === null || time === undefined || price === null || price === undefined) return null;
    return { time: typeof time === 'number' ? time : time.timestamp, price: Number(price), x, y };
  };

  const onDrawPointerDown = (e) => {
    if (drawTool === 'cursor' || drawingsLocked) return;
    const pt = chartPointFromEvent(e);
    if (!pt) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    if (drawTool === 'eraser') {
      setDrawings(list => {
        if (!list.length) return list;
        let bestIdx = -1, bestDist = Infinity;
        list.forEach((d, i) => {
          const dist = drawingDistance(d, pt);
          if (dist < bestDist) { bestDist = dist; bestIdx = i; }
        });
        if (bestIdx < 0) return list;
        return list.filter((_, i) => i !== bestIdx);
      });
      setDrawTool('cursor');
      return;
    }
    const type = drawTool === 'hline' || drawTool === 'vline' ? drawTool : (drawTool === 'rect' ? 'rect' : 'trend');
    const next = { id: makeDrawingId(), type, p1: { time: pt.time, price: pt.price }, p2: { time: pt.time, price: pt.price } };
    setDraftDrawing(next);
  };

  const onDrawPointerMove = (e) => {
    if (!draftDrawingRef.current || drawingsLocked) return;
    const pt = chartPointFromEvent(e);
    if (!pt) return;
    e.preventDefault();
    const d = draftDrawingRef.current;
    const next = { ...d, p2: { time: pt.time, price: pt.price } };
    if (d.type === 'hline') next.p2 = next.p1;
    if (d.type === 'vline') next.p2 = next.p1;
    setDraftDrawing(next);
  };

  const finishDraftDrawing = () => {
    const d = draftDrawingRef.current;
    if (!d) return;
    setDraftDrawing(null);
    setDrawings(list => [...list, d]);
    setDrawTool('cursor');
  };

  const onDrawPointerUp = (e) => {
    if (!draftDrawingRef.current) return;
    e.preventDefault();
    e.currentTarget.releasePointerCapture?.(e.pointerId);
    finishDraftDrawing();
  };

  const onDrawContextMenu = (e) => {
    e.preventDefault();
    setDraftDrawing(null);
    setDrawTool('cursor');
  };

  useE(() => {
    const onWindowPointerUp = () => finishDraftDrawing();
    const onWindowBlur = () => setDraftDrawing(null);
    window.addEventListener('pointerup', onWindowPointerUp);
    window.addEventListener('blur', onWindowBlur);
    return () => {
      window.removeEventListener('pointerup', onWindowPointerUp);
      window.removeEventListener('blur', onWindowBlur);
    };
  }, []);

  const lower1Visible = indicators.some(ind =>
    ind.visible && LOWER_BAND_INDICATORS.has(ind.type) && effectiveIndicatorPlace(ind) === 'lower1'
  );
  const lower2Visible = indicators.some(ind =>
    ind.visible && LOWER_BAND_INDICATORS.has(ind.type) && effectiveIndicatorPlace(ind) === 'lower2'
  );
  const quickIndicators = DEFAULT_CHART_INDICATORS
    .map(def => indicators.find(ind => ind.id === def.id))
    .filter(Boolean)
    .slice(0, 6);

  const TFS = ['1m','5m','15m','30m','1h','4h','1D'];
  const updateIndicator = (id, patch) => {
    setIndicators(list => list.map(ind => ind.id === id ? { ...ind, ...patch } : ind));
  };
  const addIndicator = () => {
    setIndicators(list => {
      const existing = new Set(list.map(ind => ind.id));
      const missingDefault = DEFAULT_CHART_INDICATORS.find(ind => !existing.has(ind.id));
      if (missingDefault) return [...list, { ...missingDefault, visible: true }];
      const customDefaults = IND_TYPE_DEFAULTS.EMA;
      return [
        ...list,
        {
          id: makeCustomIndicatorId(list),
          type: 'EMA',
          ...customDefaults,
          visible: true,
        },
      ];
    });
    setShowIndEditor(true);
  };
  const removeIndicator = (id) => {
    setIndicators(list => list.map(ind => (
      ind.id === id && isDefaultIndicator(id)
        ? { ...ind, visible: false }
        : ind
    )).filter(ind => ind.id !== id || isDefaultIndicator(id)));
  };
  const resetIndicators = () => setIndicators(cloneDefaultIndicators());
  const clearDrawings = () => { setDrawings([]); setDraftDrawing(null); };
  const clearIndicators = () => setIndicators(cloneDefaultIndicators().map(ind => ({ ...ind, visible: false })));
  const clearDrawingsAndIndicators = () => { clearDrawings(); clearIndicators(); };

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', background:'#0d1117', overflow:'hidden' }}>

      {/* ── Toolbar ── */}
      <div style={{ display:'flex', flexDirection:'column', gap:4, padding:'5px 8px',
                    borderBottom:'1px solid #1a2035', flexShrink:0 }}>
      <div style={{ display:'flex', alignItems:'center', gap:5, flexWrap:'wrap', minHeight:26 }}>

        {/* Symbol search */}
        <div style={{ position:'relative' }}>
          <input
            className="input"
            style={{ width:118, fontSize:12, padding:'3px 7px', fontFamily:'var(--mono)', fontWeight:600, letterSpacing:.5 }}
            value={dropOpen ? searchVal : symbol}
            placeholder="Symbol…"
            onFocus={() => { setDrop(true); setSearch(''); }}
            onBlur={() => setTimeout(() => setDrop(false), 160)}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && searchVal.trim()) pickSymbol(searchVal.trim().toUpperCase()); }}
          />
          {dropOpen && (
            <div style={{ position:'absolute', top:'100%', left:0, zIndex:9999,
                          background:'#161b27', border:'1px solid #2a3347', borderRadius:6,
                          width:210, maxHeight:270, overflowY:'auto', boxShadow:'0 8px 28px #000c' }}>
              {filtered.map(s => (
                <div key={s.symbol}
                  onMouseDown={() => pickSymbol(s.symbol)}
                  style={{ padding:'5px 10px', cursor:'pointer', fontSize:12, display:'flex',
                           justifyContent:'space-between', borderBottom:'1px solid #1a2035' }}>
                  <span style={{ fontFamily:'var(--mono)', fontWeight:600 }}>{s.symbol}</span>
                  <span style={{ fontSize:10, opacity:.45, textTransform:'uppercase' }}>{s.type}</span>
                </div>
              ))}
              {!filtered.length && (
                <div style={{ padding:'7px 10px', fontSize:11, opacity:.4 }}>
                  Press Enter → {searchVal.toUpperCase()}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Timeframe buttons */}
        <div style={{ display:'flex', gap:2 }}>
          {TFS.map(t => (
            <button key={t}
              className={cls('btn', t === tf ? 'primary' : 'ghost', 'sm')}
              style={{ padding:'2px 7px', fontSize:11, minWidth:32 }}
              onClick={() => setTf(t)}
            >{t}</button>
          ))}
        </div>

        <div style={{ width:1, height:16, background:'#2a3347', margin:'0 2px' }} />

        {/* Chart type toggle */}
        <div style={{ display:'flex', gap:2 }}>
          {[['candles','Candles'],['heikin_ashi','HA'],['line','Line']].map(([ct, label]) => (
            <button key={ct}
              className={cls('btn', ct === chartType ? 'primary' : 'ghost', 'sm')}
              style={{ padding:'2px 7px', fontSize:11 }}
              onClick={() => setChartType(ct)}
              title={ct === 'candles' ? 'Standard candlestick' : ct === 'heikin_ashi' ? 'Heikin Ashi candles (smoothed, good for trend reading)' : 'Line chart (close price)'}
            >{label}</button>
          ))}
        </div>

        <div style={{ width:1, height:16, background:'#2a3347', margin:'0 2px' }} />

        {/* Broker selector — shows relevant brokers for current asset type */}
        <div style={{ display:'flex', gap:2 }}>
          {(isCrypto ? CRYPTO_BROKERS : STOCK_BROKERS).map(b => (
            <button key={b.id}
              className={cls('btn', b.id === broker ? 'primary' : 'ghost', 'sm')}
              style={{ padding:'2px 7px', fontSize:11 }}
              onClick={() => setBroker(b.id)}
              title={`Fetch chart data from ${b.label}`}
            >{b.label}</button>
          ))}
        </div>

        <div style={{ width:1, height:16, background:'#2a3347', margin:'0 2px' }} />

        {/* Indicator quick toggles */}
        {quickIndicators.map(ind => (
          <button key={ind.id}
            className="btn ghost sm"
            style={{ padding:'2px 7px', fontSize:11,
                     color: ind.visible ? ind.color : '#4b5563',
                     borderColor: ind.visible ? ind.color+'88' : undefined,
                     opacity: ind.visible ? 1 : 0.55 }}
            onClick={() => updateIndicator(ind.id, { visible: !ind.visible })}
            title={`${ind.type}${ind.period ? ` ${ind.period}` : ''} (${ind.place || 'main'})`}
          >{ind.type}{ind.period || ''}</button>
        ))}

        <button className="btn ghost sm" style={{ padding:'2px 7px', fontSize:11 }}
          onClick={() => setShowIndEditor(v => !v)}
          title={showIndEditor ? "Close indicator editor" : "Edit indicators"}>
          {showIndEditor ? "Close Indicators" : "Indicators"}
        </button>

        <div style={{ flex:1 }} />

        {loading && <span style={{ fontSize:10, opacity:.45 }}>Loading…</span>}
        {err     && <span style={{ fontSize:10, color:'var(--red)', maxWidth:160, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{err}</span>}
        <button className="btn ghost sm" style={{ padding:'2px 6px' }}
          onClick={() => { setBars([]); setMarks([]); setLoading(true); setErr(null);
            const limit = chartLimitForTf(tf);
            panelApi(`/api/chart?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}&limit=${limit}&broker=${broker}`)
              .then(d => { setBars(d.bars||[]); setMarks(d.markers||[]); })
              .catch(e => setErr(e.message))
              .finally(() => setLoading(false)); }}
          title="Refresh chart">
          <Icon name="refresh" size={11} />
        </button>
      </div>

      <div style={{ display:'flex', alignItems:'center', gap:5, flexWrap:'wrap', minHeight:24 }}>
        <span style={{ fontSize:10, color:'#6b7280', textTransform:'uppercase', fontWeight:700, letterSpacing:0 }}>
          Draw
        </span>

        {DRAW_TOOLS.map(([tool, label]) => (
          <button key={tool}
            className={cls('btn', drawTool === tool ? 'primary' : 'ghost', 'sm')}
            style={{ padding:'2px 7px', fontSize:11, minWidth: tool === 'cursor' ? 52 : 30 }}
            onClick={() => setDrawTool(tool)}
            title={`Drawing tool: ${label}`}
          >{label}</button>
        ))}
        <button className={cls('btn', drawingsLocked ? 'primary' : 'ghost', 'sm')}
          style={{ padding:'2px 7px', fontSize:11 }}
          onClick={() => setDrawingsLocked(v => !v)}
          title={drawingsLocked ? "Unlock drawings" : "Lock drawings"}>
          {drawingsLocked ? "Locked" : "Lock"}
        </button>
        <button className={cls('btn', drawingsHidden ? 'primary' : 'ghost', 'sm')}
          style={{ padding:'2px 7px', fontSize:11 }}
          onClick={() => setDrawingsHidden(v => !v)}
          title={drawingsHidden ? "Show drawings" : "Hide drawings"}>
          {drawingsHidden ? "Show" : "Hide"}
        </button>
        <button className="btn ghost sm" style={{ padding:'2px 7px', fontSize:11 }}
          onClick={clearDrawings}
          title="Remove drawings only">
          Clear Draw
        </button>
        <button className="btn ghost sm" style={{ padding:'2px 7px', fontSize:11 }}
          onClick={clearIndicators}
          title="Remove indicators only">
          Clear Ind
        </button>
        <button className="btn ghost sm" style={{ padding:'2px 7px', fontSize:11 }}
          onClick={clearDrawingsAndIndicators}
          title="Remove drawings and indicators">
          Clear Both
        </button>
      </div>
      </div>

      {showIndEditor && (
        <div style={{ display:'flex', flexDirection:'column', gap:6, padding:'7px 8px',
                      borderBottom:'1px solid #1a2035', background:'#111827', flexShrink:0 }}>
          {indicators.map(ind => (
            <div key={ind.id} style={{ display:'grid',
              gridTemplateColumns:'22px 82px 74px 74px minmax(280px, 1fr) 28px',
              gap:5, alignItems:'center' }}>
              <input type="checkbox" checked={!!ind.visible}
                onChange={e => updateIndicator(ind.id, { visible: e.target.checked })} />
              <select className="select input" value={ind.type}
                onChange={e => {
                  const nextType = e.target.value;
                  const defaults = IND_TYPE_DEFAULTS[nextType] || {};
                  updateIndicator(ind.id, {
                    ...defaults,
                    type: nextType,
                    place: PRICE_OVERLAY_INDICATORS.has(nextType) ? 'main' : (defaults.place || 'lower1'),
                  });
                }}
                style={{ height:24, fontSize:11, padding:'2px 5px' }}>
                {IND_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
              <input className="input" type="color" value={ind.color || '#60a5fa'}
                onChange={e => updateIndicator(ind.id, { color: e.target.value })}
                style={{ height:24, padding:2 }} />
              <select className="select input" value={effectiveIndicatorPlace(ind)}
                onChange={e => updateIndicator(ind.id, { place: e.target.value })}
                style={{ height:24, fontSize:11, padding:'2px 5px' }}>
                {indicatorPlaceOptions(ind.type).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
              </select>
              <div style={{ display:'flex', gap:5, alignItems:'center', flexWrap:'wrap' }}>
                {indicatorParamDefs(ind.type).map(def => (
                  <label key={def.key} style={{ display:'flex', alignItems:'center', gap:3, fontSize:10, color:'#8b949e' }}>
                    <span>{def.label}</span>
                    {def.type === 'color' ? (
                      <input className="input" type="color"
                        value={ind[def.key] || def.fallback}
                        onChange={e => updateIndicator(ind.id, { [def.key]: e.target.value })}
                        style={{ width:34, height:24, padding:2 }} />
                    ) : def.type === 'select' ? (
                      <select className="select input"
                        value={ind[def.key] || def.fallback}
                        onChange={e => updateIndicator(ind.id, { [def.key]: e.target.value })}
                        style={{ height:24, fontSize:11, padding:'2px 5px', minWidth:76 }}>
                        {(def.options || []).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    ) : (
                      <input className="input" type="number"
                        min={def.min} max={def.max} step={def.step || 1}
                        value={ind[def.key] ?? def.fallback}
                        onChange={e => updateIndicator(ind.id, { [def.key]: Number(e.target.value) || def.fallback })}
                        style={{ width:52, height:24, fontSize:11, padding:'2px 5px' }} />
                    )}
                  </label>
                ))}
                {!indicatorParamDefs(ind.type).length && (
                  <span style={{ fontSize:10, color:'#6b7280' }}>Session VWAP</span>
                )}
              </div>
              <button className="btn ghost sm" style={{ height:24, padding:'2px 6px' }}
                onClick={() => removeIndicator(ind.id)}
                title={isDefaultIndicator(ind.id) ? "Hide built-in indicator" : "Remove custom indicator"}>
                {isDefaultIndicator(ind.id) ? "−" : "×"}
              </button>
            </div>
          ))}
          <div style={{ display:'flex', gap:6 }}>
            <button className="btn ghost sm" onClick={addIndicator}>Add Indicator</button>
            <button className="btn ghost sm" onClick={resetIndicators}>Reset Defaults</button>
            <button className="btn ghost sm" onClick={() => setShowIndEditor(false)}>Close</button>
          </div>
        </div>
      )}

      {/* ── Chart panes ── */}
      <div style={{ flex:1, minHeight:220, position:'relative' }}>
        <div ref={containerRef} style={{ position:'absolute', inset:0 }} />
        <canvas
          ref={drawingCanvasRef}
          onPointerDown={onDrawPointerDown}
          onPointerMove={onDrawPointerMove}
          onPointerUp={onDrawPointerUp}
          onPointerCancel={() => setDraftDrawing(null)}
          onContextMenu={onDrawContextMenu}
          style={{
            position:'absolute',
            inset:0,
            zIndex:5,
            pointerEvents: drawTool === 'cursor' || drawingsLocked || drawingsHidden ? 'none' : 'auto',
            cursor: drawTool === 'eraser' ? 'not-allowed' : 'crosshair',
            userSelect:'none',
            touchAction:'none',
          }}
        />
      </div>
      <div
        ref={lower1ContainerRef}
        style={{
          height: lower1Visible ? 122 : 0,
          minHeight: lower1Visible ? 92 : 0,
          overflow: 'hidden',
          borderTop: lower1Visible ? '1px solid #1a2035' : '0',
          flexShrink: 0,
        }}
      />
      <div
        ref={lower2ContainerRef}
        style={{
          height: lower2Visible ? 132 : 0,
          minHeight: lower2Visible ? 98 : 0,
          overflow: 'hidden',
          borderTop: lower2Visible ? '1px solid #1a2035' : '0',
          flexShrink: 0,
        }}
      />
    </div>
  );
}

window.Panels = { TopOverview, OpenPositionsPanel, ManualTradePanel, TradeLogPanel, DailyPerfPanel, BacktesterPanel, ChatPanel, ChartPanel };
window.fmt = { fmt$, fmt$Sign, fmtP, fmtN, cls };
