// Side-panel windows: Manage Positions, Inject Symbols, Quick Controls (Tax/Reports/Withdrawal)
const { useState: uS, useEffect: uE, useRef: uR } = React;

// ---------- Shared API helpers ----------
const apiBase = () => {
  const configured = (window.DASHBOARD_API_BASE || '').replace(/\/$/, '');
  if (configured) return configured;
  if (window.location.protocol === 'file:') return 'http://localhost:8125';
  return '';
};

const apiCall = async (path, opts = {}) => {
  const res = await fetch(`${apiBase()}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || data?.error || `HTTP ${res.status}`);
  return data;
};

const normalizePos = (p) => ({
  id: p.trade_id || p.id,
  dbId: p.id,
  symbol: p.symbol || '?',
  type: p.asset_class || p.type || 'LIVE',
  assetClass: p.asset_class || 'crypto',
  dir: (p.direction || p.side || p.dir || 'LONG').toString().toUpperCase(),
  entry: Number(p.entry_price ?? p.entry ?? 0),
  current: Number(p.current_price ?? p.current ?? p.entry_price ?? p.entry ?? 0),
  sl: Number(p.stop_loss ?? p.sl ?? p.entry_price ?? p.entry ?? 0),
  tp: Number(p.take_profit ?? p.tp ?? p.entry_price ?? p.entry ?? 0),
  pnlD: Number(p.unrealized_pnl ?? p.pnlD ?? 0),
  pnlP: Number(p.pnl_pct ?? p.pnlP ?? 0),
  opened: p.entry_time || p.opened || '—',
  toSL: Number(p.distance_to_sl ?? p.toSL ?? 0),
  toTP: Number(p.distance_to_tp ?? p.toTP ?? 0),
});

// ===== Manage Positions =====
function ManagePositionsPanel() {
  const [positions, setPositions] = uS([]);
  const [chartSym, setChartSym] = uS(null);
  const [candleSize, setCandleSize] = uS('5 Min');
  const [msg, setMsg] = uS('');
  const [busy, setBusy] = uS(false);

  const loadPositions = async () => {
    try {
      const data = await apiCall('/api/open_positions');
      const rows = Array.isArray(data.positions) ? data.positions.map(normalizePos) : [];
      setPositions(rows);
      setMsg(`Loaded ${rows.length} live position(s)`);
    } catch (e) {
      setMsg(`Load failed: ${e.message}`);
    }
  };

  uE(() => {
    loadPositions();
    const t = setInterval(loadPositions, 10000);
    return () => clearInterval(t);
  }, []);

  const closeNow = async (p) => {
    if (!p?.id) {
      setMsg(`Cannot close ${p?.symbol || '?'}: missing position id`);
      return;
    }
    setBusy(true);
    try {
      const data = await apiCall('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'close_position', position_id: p.id }),
      });
      setMsg(data.message || `Closed ${p.symbol}`);
      await loadPositions();
    } catch (e) {
      setMsg(`Close failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const closeAll = async () => {
    setBusy(true);
    try {
      for (const p of positions) {
        if (p.id != null) {
          await apiCall('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'close_position', position_id: p.id }),
          });
        }
      }
      setMsg('Close-all requested.');
      await loadPositions();
    } catch (e) {
      setMsg(`Close-all failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 14 }}>
      <div className="banner info" style={{ marginBottom: 12 }}>
        <Icon name="alert" size={14} />
        <span>Live backend mode: Close actions hit /api/control. Refresh pulls /api/open_positions.</span>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button className="btn ghost sm" onClick={loadPositions} disabled={busy}><Icon name="refresh" size={12} />Refresh</button>
        <button className="btn danger sm" onClick={closeAll} disabled={busy || positions.length === 0}><Icon name="x" size={12} />Close All</button>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-2)' }}>{positions.length} open</span>
      </div>

      {msg && <div style={{ marginBottom: 10, fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}

      {positions.map((p, i) => {
        const slPct = Math.abs((p.current - p.sl) / (p.entry || 1) * 100);
        const tpPct = Math.abs((p.current - p.tp) / (p.entry || 1) * 100);
        const total = Math.max(0.0001, slPct + tpPct);
        const slBar = (slPct / total) * 100;
        const isChart = chartSym === p.symbol;
        return (
          <div key={p.id ?? `${p.symbol}-${i}`} className="pos-card">
            <div className="row1">
              <span className="sym">{p.symbol}</span>
              <span className={cls('pill', p.dir.toLowerCase())} style={{ fontSize: 9.5 }}>{p.dir}</span>
              <span className="meta">ID {p.id ?? '—'} · Entry {fmtN(p.entry)} · Cur {fmtN(p.current)} · SL {fmtN(p.sl)} · TP {fmtN(p.tp)}</span>
              <span className={cls('pnl', p.pnlD >= 0 ? 'pos' : 'neg')} style={{ color: p.pnlD >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {fmt$Sign(p.pnlD)} ({fmtP(p.pnlP)})
              </span>
            </div>

            <div className="progress"><div style={{ width: slBar + '%', background: 'linear-gradient(90deg, var(--red), var(--yellow), var(--green))' }} /></div>

            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <button className="btn ghost sm" onClick={() => setChartSym(isChart ? null : p.symbol)}>
                <Icon name="candles" size={12} /> {isChart ? 'Hide chart' : 'View chart'}
              </button>
              <button className="btn ghost sm"><Icon name="edit" size={12} />Adjust SL/TP</button>
              <span className="spacer" />
              <button className="btn danger sm" onClick={() => closeNow(p)} disabled={busy || p.id == null}>
                <Icon name="x" size={12} />Close Now
              </button>
            </div>

            {isChart && (
              <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-1)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <label style={{ fontSize: 11, color: 'var(--text-2)' }}>Candle size:</label>
                  <select className="select input" style={{ padding: '4px 8px', fontSize: 11 }} value={candleSize} onChange={e => setCandleSize(e.target.value)}>
                    {['1 Min', '5 Min', '15 Min', '1 H', '4 H', '1 D'].map(c => <option key={c}>{c}</option>)}
                  </select>
                  <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
                    {['1H', '6H', '12H', '1D', '3D', 'ALL'].map(per => <button key={per} className="btn ghost sm" style={{ padding: '3px 8px', fontSize: 10 }}>{per}</button>)}
                  </div>
                </div>
                <MiniCandleChart symbol={p.symbol} assetClass={p.assetClass} timeframe={candleSize} dir={p.dir} entry={p.entry} sl={p.sl} tp={p.tp} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function MiniCandleChart({ symbol, assetClass, timeframe, dir, entry, sl, tp }) {
  const [candles, setCandles] = uS([]);
  const [status, setStatus] = uS('Loading chart...');

  uE(() => {
    let cancelled = false;
    const load = async () => {
      setStatus('Loading chart...');
      try {
        const qs = new URLSearchParams({ symbol, asset_class: assetClass || 'crypto', timeframe: timeframe || '5 Min', limit: '120' });
        const data = await apiCall(`/api/candles?${qs.toString()}`);
        const rows = Array.isArray(data.candles) ? data.candles.map(c => ({
          o: Number(c.open),
          h: Number(c.high),
          l: Number(c.low),
          c: Number(c.close),
        })).filter(c => c.o && c.h && c.l && c.c) : [];
        if (!cancelled) {
          setCandles(rows);
          setStatus(rows.length ? '' : 'No chart data available.');
        }
      } catch (e) {
        if (!cancelled) setStatus(`Chart failed: ${e.message}`);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [symbol, assetClass, timeframe]);

  if (!candles.length) {
    return <div style={{ height: 140, display: 'grid', placeItems: 'center', background: 'var(--bg-0)', borderRadius: 4, border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 11 }}>{status}</div>;
  }

  const max = Math.max(...candles.map(c => c.h), entry, sl, tp) * 1.001;
  const min = Math.min(...candles.map(c => c.l), entry, sl, tp) * 0.999;
  const range = max - min;
  const W = 100, H = 30;
  const yScale = (v) => ((max - v) / range) * H;

  return (
    <svg viewBox={`0 0 ${W} ${H + 4}`} style={{ width: '100%', height: 140, background: 'var(--bg-0)', borderRadius: 4, border: '1px solid var(--border)' }} preserveAspectRatio="none">
      <line x1="0" x2={W} y1={yScale(sl)} y2={yScale(sl)} stroke="#f43f5e" strokeWidth="0.15" strokeDasharray="0.5,0.5" />
      <line x1="0" x2={W} y1={yScale(tp)} y2={yScale(tp)} stroke="#10b981" strokeWidth="0.15" strokeDasharray="0.5,0.5" />
      <line x1="0" x2={W} y1={yScale(entry)} y2={yScale(entry)} stroke="#60a5fa" strokeWidth="0.15" strokeDasharray="0.5,0.5" />
      {candles.map((c, i) => {
        const x = (i / candles.length) * W;
        const wide = W / candles.length * 0.7;
        const up = c.c >= c.o;
        return (
          <g key={i}>
            <line x1={x + wide / 2} x2={x + wide / 2} y1={yScale(c.h)} y2={yScale(c.l)} stroke={up ? '#10b981' : '#f43f5e'} strokeWidth="0.1" />
            <rect x={x} y={yScale(Math.max(c.o, c.c))} width={wide} height={Math.max(0.2, Math.abs(yScale(c.o) - yScale(c.c)))} fill={up ? '#10b981' : '#f43f5e'} />
          </g>
        );
      })}
      <text x={W - 0.5} y={yScale(sl) - 0.3} fill="#f43f5e" fontSize="1.4" textAnchor="end" fontFamily="JetBrains Mono">SL</text>
      <text x={W - 0.5} y={yScale(tp) - 0.3} fill="#10b981" fontSize="1.4" textAnchor="end" fontFamily="JetBrains Mono">TP</text>
      <text x={W - 0.5} y={yScale(entry) - 0.3} fill="#60a5fa" fontSize="1.4" textAnchor="end" fontFamily="JetBrains Mono">Entry</text>
    </svg>
  );
}

// ===== Inject Symbols =====
function InjectSymbolsPanel() {
  const [stocks, setStocks] = uS([]);
  const [crypto, setCrypto] = uS([]);
  const [stockInput, setStockInput] = uS('AAPL\nMSFT\nNVDA');
  const [cryptoInput, setCryptoInput] = uS('BTC\nETH\nSOL');
  const [msg, setMsg] = uS('');
  const [busy, setBusy] = uS(false);

  const loadInjected = async () => {
    try {
      const data = await apiCall('/api/injected_symbols');
      setStocks(Array.isArray(data.stocks) ? data.stocks : []);
      setCrypto(Array.isArray(data.crypto) ? data.crypto : []);
    } catch (e) {
      setMsg(`Load failed: ${e.message}`);
    }
  };

  uE(() => { loadInjected(); }, []);

  const inject = async (kind) => {
    const raw = (kind === 'stock' ? stockInput : cryptoInput).split(/[\n,]/).map(s => s.trim()).filter(Boolean);
    setBusy(true);
    try {
      const data = await apiCall('/api/injected_symbols', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, symbols: raw }),
      });
      setStocks(Array.isArray(data.stocks) ? data.stocks : []);
      setCrypto(Array.isArray(data.crypto) ? data.crypto : []);
      setMsg(data.message || 'Injected symbols updated.');
    } catch (e) {
      setMsg(`Inject failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const clearInjected = async () => {
    setBusy(true);
    try {
      const data = await apiCall('/api/injected_symbols/clear', { method: 'POST' });
      setStocks(Array.isArray(data.stocks) ? data.stocks : []);
      setCrypto(Array.isArray(data.crypto) ? data.crypto : []);
      setMsg(data.message || 'Injected symbols cleared.');
    } catch (e) {
      setMsg(`Clear failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <div className="panel-sub" style={{ marginBottom: 14 }}>
        Spotted something? Add it here — temporary for today only. Resets on next scan or reboot.
      </div>
      {msg && <div style={{ marginBottom: 10, fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--blue)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="trending" size={13} />Stocks
          </h3>
          <div className="field" style={{ marginBottom: 10 }}>
            <label>Tickers</label>
            <textarea className="input textarea" rows={4} value={stockInput} onChange={e => setStockInput(e.target.value)} />
          </div>
          <button className="btn primary full" onClick={() => inject('stock')} disabled={busy}><Icon name="plus" size={12} />Inject Stocks</button>
        </div>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--yellow)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="coins" size={13} />Crypto
          </h3>
          <div className="field" style={{ marginBottom: 10 }}>
            <label>Symbols</label>
            <textarea className="input textarea" rows={4} value={cryptoInput} onChange={e => setCryptoInput(e.target.value)} />
          </div>
          <button className="btn primary full" onClick={() => inject('crypto')} disabled={busy}><Icon name="plus" size={12} />Inject Crypto</button>
        </div>
      </div>
      {(stocks.length > 0 || crypto.length > 0) && (
        <div style={{ marginBottom: 12, display: 'grid', gap: 8 }}>
          {stocks.length > 0 && <div className="banner info"><Icon name="trending" size={13} /><span>Stocks ({stocks.length}): {stocks.join(', ')}</span></div>}
          {crypto.length > 0 && <div className="banner info"><Icon name="coins" size={13} /><span>Crypto ({crypto.length}): {crypto.join(', ')}</span></div>}
        </div>
      )}
      <button className="btn ghost full" onClick={clearInjected} disabled={busy}><Icon name="trash" size={12} />Clear All Injected Symbols</button>
    </div>
  );
}

// ===== Quick Controls (Bot, Risk, Tax, Withdrawal) =====
function QuickControlsPanel() {
  const [running, setRunning] = uS(true);
  const [paused, setPaused] = uS(false);
  const [maxPos, setMaxPos] = uS(2);
  const [taxYear, setTaxYear] = uS(2026);
  const [wAmount, setWAmount] = uS('0.00');
  const [wReason, setWReason] = uS('Living expenses');
  const [mlTraining, setMlTraining] = uS(false);
  const [busy, setBusy] = uS(false);
  const [msg, setMsg] = uS('');

  const refreshSnapshot = async () => {
    try {
      const snap = await apiCall('/api/snapshot');
      setRunning(!!snap.bot_process_running);
      if (snap.bot_status === 'PAUSED') setPaused(true);
      if (snap.bot_status === 'ACTIVE') setPaused(false);
    } catch {}
  };

  uE(() => { refreshSnapshot(); }, []);

  const callControl = async (action, extras = {}) => {
    setBusy(true);
    try {
      const data = await apiCall('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...extras })
      });
      setMsg(data.message || data.error || 'Done');
      await refreshSnapshot();
    } catch (e) {
      setMsg(`Control failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const triggerML = () => {
    setMlTraining(true);
    setTimeout(() => setMlTraining(false), 2200);
  };

  return (
    <div style={{ padding: 14 }}>
      {/* Bot Process Control */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="cpu" size={13} />Bot Process Control
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <span className="dot" style={{ width: 8, height: 8, borderRadius: '50%', background: running ? 'var(--green)' : 'var(--red)', boxShadow: running ? '0 0 8px var(--green)' : 'none' }}></span>
          <span style={{ fontSize: 12, fontWeight: 500 }}>{running ? 'Bot Running' : 'Bot Stopped'}</span>
          <span className="tag" style={{ marginLeft: 'auto' }}>{busy ? 'Working…' : 'Live'}</span>
        </div>
        <div className="grid-2">
          <button className="btn ghost" onClick={() => callControl('restart_bot')} disabled={busy}>
            <Icon name="refresh" size={12} />Restart Bot
          </button>
          <button className="btn danger" onClick={() => callControl('stop_bot')} disabled={busy}>
            <Icon name="stop" size={12} />Stop Bot
          </button>
        </div>
        {msg && <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-2)' }}>{msg}</div>}
      </div>

      {/* Trading Control */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="activity" size={13} />Trading Control
        </h3>
        <button
          className={cls('btn full', paused ? 'primary' : 'ghost')}
          onClick={() => callControl(paused ? 'resume_trading' : 'pause_trading')}
          disabled={busy}
        >
          {paused ? <><Icon name="play" size={12} />Resume Trading</> : <><Icon name="pause" size={12} />Pause Trading</>}
        </button>
      </div>

      {/* Risk Settings */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="sliders" size={13} />Risk Settings
        </h3>
        <div className="field">
          <label style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Max Position %</span>
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--accent-bright)' }}>{maxPos}%</span>
          </label>
          <input type="range" min="0.5" max="10" step="0.5" value={maxPos} onChange={e => setMaxPos(+e.target.value)} />
        </div>
      </div>

      {/* ML Scorer */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="layers" size={13} />ML Scorer
        </h3>
        <button className="btn ghost full" onClick={triggerML} disabled={mlTraining}>{mlTraining ? <><Icon name="cpu" size={12} />Training…</> : <><Icon name="cpu" size={12} />Train ML Now</>}</button>
      </div>

      {/* Tax & Reports */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="file" size={13} />Tax & Reports
        </h3>
        <button className="btn ghost full" style={{ marginBottom: 10 }}><Icon name="file" size={12} />Generate Today's Report</button>
        <div className="field" style={{ marginBottom: 10 }}>
          <label>Tax Year</label>
          <input className="input" type="number" value={taxYear} onChange={e => setTaxYear(+e.target.value)} />
        </div>
      </div>

      {/* Withdrawal */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="wallet" size={13} />Withdrawal
        </h3>
        <div className="field" style={{ marginBottom: 10 }}>
          <label>Amount ($)</label>
          <input className="input" value={wAmount} onChange={e => setWAmount(e.target.value)} />
        </div>
        <div className="field" style={{ marginBottom: 10 }}>
          <label>Reason</label>
          <input className="input" value={wReason} onChange={e => setWReason(e.target.value)} />
        </div>
        <button className="btn primary full" disabled={parseFloat(wAmount) <= 0}><Icon name="arrow" size={12} />Process Withdrawal</button>
      </div>
    </div>
  );
}

window.SidePanels = { ManagePositionsPanel, InjectSymbolsPanel, QuickControlsPanel };
