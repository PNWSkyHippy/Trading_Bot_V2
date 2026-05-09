// Side-panel windows: Manage Positions, Inject Symbols, Quick Controls (Tax/Reports/Withdrawal)
const { useState: uS, useEffect: uE, useRef: uR } = React;

// ===== Manage Positions =====
function ManagePositionsPanel() {
  const [positions, setPositions] = uS(MOCK.OPEN_POSITIONS);
  const [chartSym, setChartSym] = uS(null);
  const [candleSize, setCandleSize] = uS('5 Min');

  const closeNow = (sym) => {
    setPositions(prev => prev.filter(p => p.symbol !== sym));
  };

  return (
    <div style={{ padding: 14 }}>
      <div className="banner info" style={{ marginBottom: 12 }}>
        <Icon name="alert" size={14} />
        <span>Stocks: cancels bracket orders first, then closes. Crypto: closes via exchange. <strong>STUCK</strong> = exceeded 3 failed close attempts; needs manual close.</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button className="btn ghost sm"><Icon name="refresh" size={12} />Refresh</button>
        <button className="btn danger sm"><Icon name="x" size={12} />Close All</button>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-2)' }}>{positions.length} open</span>
      </div>

      {positions.map((p, i) => {
        const slPct = Math.abs((p.current - p.sl) / p.entry * 100);
        const tpPct = Math.abs((p.current - p.tp) / p.entry * 100);
        const total = slPct + tpPct;
        const slBar = (slPct / total) * 100;
        const isChart = chartSym === p.symbol;
        return (
          <div key={i} className="pos-card">
            <div className="row1">
              <span className="sym">{p.symbol}</span>
              <span className={cls('pill', p.dir.toLowerCase())} style={{ fontSize: 9.5 }}>{p.dir}</span>
              <span className="meta">Entry {fmtN(p.entry)} · Cur {fmtN(p.current)} · SL {fmtN(p.sl)} · TP {fmtN(p.tp)} · {p.toSL.toFixed(2)}% to SL · {p.toTP.toFixed(2)}% to TP</span>
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
              <button className="btn danger sm" onClick={() => closeNow(p.symbol)}><Icon name="x" size={12} />Close Now</button>
            </div>
            {isChart && (
              <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-1)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <label style={{ fontSize: 11, color: 'var(--text-2)' }}>Candle size:</label>
                  <select className="select input" style={{ padding: '4px 8px', fontSize: 11 }} value={candleSize} onChange={e => setCandleSize(e.target.value)}>
                    {['1 Min', '5 Min', '15 Min', '1 H', '4 H', '1 D'].map(c => <option key={c}>{c}</option>)}
                  </select>
                  <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
                    {['1H', '6H', '12H', '1D', '3D', 'ALL'].map(p => <button key={p} className="btn ghost sm" style={{ padding: '3px 8px', fontSize: 10 }}>{p}</button>)}
                  </div>
                </div>
                <MiniCandleChart symbol={p.symbol} dir={p.dir} entry={p.entry} sl={p.sl} tp={p.tp} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function MiniCandleChart({ symbol, dir, entry, sl, tp }) {
  // Generate mock candles
  const candles = uS(() => {
    const out = []; let p = entry * (dir === 'LONG' ? 0.99 : 1.01);
    for (let i = 0; i < 80; i++) {
      const o = p, c = p + (Math.random() - 0.5) * entry * 0.005;
      const h = Math.max(o, c) + Math.random() * entry * 0.002;
      const l = Math.min(o, c) - Math.random() * entry * 0.002;
      out.push({ o, h, l, c });
      p = c;
    }
    return out;
  })[0];

  const max = Math.max(...candles.map(c => c.h), entry, sl, tp) * 1.001;
  const min = Math.min(...candles.map(c => c.l), entry, sl, tp) * 0.999;
  const range = max - min;
  const W = 100, H = 30;
  const yScale = (v) => ((max - v) / range) * H;

  return (
    <svg viewBox={`0 0 ${W} ${H + 4}`} style={{ width: '100%', height: 140, background: 'var(--bg-0)', borderRadius: 4, border: '1px solid var(--border)' }} preserveAspectRatio="none">
      {/* Reference lines */}
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
  const [stocks, setStocks] = uS(MOCK.INJECTED.stocks);
  const [crypto, setCrypto] = uS(MOCK.INJECTED.crypto);
  const [stockInput, setStockInput] = uS('AAPL\nMSFT\nNVDA');
  const [cryptoInput, setCryptoInput] = uS('BTC\nETH\nSOL');

  const inject = (kind) => {
    const raw = (kind === 'stock' ? stockInput : cryptoInput).split(/[\n,]/).map(s => s.trim()).filter(Boolean);
    if (kind === 'stock') setStocks(prev => Array.from(new Set([...prev, ...raw])));
    else setCrypto(prev => Array.from(new Set([...prev, ...raw.map(c => c.includes('/') ? c : c + '/USD')])));
  };

  return (
    <div style={{ padding: 16 }}>
      <div className="panel-sub" style={{ marginBottom: 14 }}>
        Spotted something? Add it here — temporary for today only. Resets on next scan or reboot. To make permanent, edit the master watchlist files.
      </div>
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--blue)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="trending" size={13} />Stocks
          </h3>
          <div className="field" style={{ marginBottom: 10 }}>
            <label>Tickers (one per line or comma-separated)</label>
            <textarea className="input textarea" rows={4} value={stockInput} onChange={e => setStockInput(e.target.value)} />
          </div>
          <button className="btn primary full" onClick={() => inject('stock')}><Icon name="plus" size={12} />Inject Stocks</button>
        </div>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--yellow)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="coins" size={13} />Crypto
          </h3>
          <div className="field" style={{ marginBottom: 10 }}>
            <label>Symbols (e.g. BTC or BTC/USD, one per line or comma-separated)</label>
            <textarea className="input textarea" rows={4} value={cryptoInput} onChange={e => setCryptoInput(e.target.value)} />
          </div>
          <button className="btn primary full" onClick={() => inject('crypto')}><Icon name="plus" size={12} />Inject Crypto</button>
        </div>
      </div>

      <div style={{ marginBottom: 8, fontSize: 11, color: 'var(--text-1)', fontWeight: 600 }}>Currently active injected symbols:</div>
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 10, marginBottom: 8 }}>
        <div style={{ fontSize: 11, color: 'var(--blue)', marginBottom: 6, fontWeight: 600 }}>Stocks ({stocks.length})</div>
        <div className="chip-list">
          {stocks.length === 0 && <span style={{ color: 'var(--text-3)', fontSize: 11 }}>No injected stocks.</span>}
          {stocks.map(s => <span key={s} className="chip stock">{s} <span className="x" onClick={() => setStocks(p => p.filter(x => x !== s))}>×</span></span>)}
        </div>
      </div>
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 10, marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: 'var(--yellow)', marginBottom: 6, fontWeight: 600 }}>Crypto ({crypto.length})</div>
        <div className="chip-list">
          {crypto.length === 0 && <span style={{ color: 'var(--text-3)', fontSize: 11 }}>No injected crypto.</span>}
          {crypto.map(c => <span key={c} className="chip crypto">{c} <span className="x" onClick={() => setCrypto(p => p.filter(x => x !== c))}>×</span></span>)}
        </div>
      </div>
      <button className="btn ghost full" onClick={() => { setStocks([]); setCrypto([]); }}><Icon name="trash" size={12} />Clear All Injected Symbols</button>
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
          <span className="tag" style={{ marginLeft: 'auto' }}>PID 11552</span>
        </div>
        <div className="grid-2">
          <button className="btn ghost"><Icon name="refresh" size={12} />Restart Bot</button>
          <button className="btn danger" onClick={() => setRunning(false)}><Icon name="stop" size={12} />Stop Bot</button>
        </div>
      </div>

      {/* Trading Control */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="activity" size={13} />Trading Control
        </h3>
        <button className={cls('btn full', paused ? 'primary' : 'ghost')} onClick={() => setPaused(p => !p)}>
          {paused ? <><Icon name="play" size={12} />Resume Trading</> : <><Icon name="pause" size={12} />Pause Trading</>}
        </button>
        <div style={{ fontSize: 11, color: 'var(--text-2)', marginTop: 8 }}>Pause stops new trades but keeps the bot running and monitoring open positions.</div>
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span className="dot" style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--blue)' }}></span>
          <span style={{ fontSize: 12 }}>Learning · 30% weight</span>
        </div>
        <div className="progress" style={{ height: 4, background: 'var(--bg-3)', borderRadius: 2, overflow: 'hidden', marginBottom: 8 }}>
          <div style={{ width: '30%', height: '100%', background: 'var(--accent)' }} />
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--text-2)', marginBottom: 10 }}>112 trades to full ML weight (target 1000)</div>
        <button className="btn ghost full" onClick={triggerML} disabled={mlTraining}>{mlTraining ? <><Icon name="cpu" size={12} />Training…</> : <><Icon name="cpu" size={12} />Train ML Now</>}</button>
      </div>

      {/* Market Condition */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14, marginBottom: 12 }}>
        <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="eye" size={13} />Market Condition
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span className="tag" style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--yellow)', borderColor: 'rgba(245, 158, 11, 0.25)', border: '1px solid' }}>Unknown</span>
          <span style={{ fontSize: 11, color: 'var(--text-2)' }}>ADX 0.0 · Scalar 50%</span>
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--text-2)' }}>Insufficient data for condition analysis.</div>
        <div className="banner warn" style={{ marginTop: 10, fontSize: 11 }}>
          Conditions unfavorable — bot is pausing new entries.
        </div>
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
        <button className="btn ghost full" style={{ marginBottom: 12 }}><Icon name="download" size={12} />Export Form 8949 CSV</button>
        <div style={{ background: 'var(--bg-3)', borderRadius: 'var(--radius-sm)', padding: 10, fontSize: 11 }}>
          <div style={{ color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: 10, marginBottom: 6 }}>YTD Tax Summary ({taxYear})</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}><span>Total Gains/Losses</span><strong style={{ color: 'var(--green)', fontFamily: 'var(--mono)' }}>$736.17</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}><span>Short-Term</span><span style={{ fontFamily: 'var(--mono)' }}>$736.17</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Long-Term</span><span style={{ fontFamily: 'var(--mono)' }}>$0.00</span></div>
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
