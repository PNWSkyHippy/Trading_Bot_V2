const { useEffect, useState } = React;

function MetricCard({label, value}) {
  return <div className="card"><div className="muted">{label}</div><h2>{value}</h2></div>
}

function App() {
  const [snapshot, setSnapshot] = useState({ bot_status: "UNKNOWN", open_positions: 0, available_cash: 0 });
  const [msg, setMsg] = useState("Waiting for API...");

  const base = (window.DASHBOARD_API_BASE || "").replace(/\/$/, "");
  const api = (path) => `${base}${path}`;

  async function load() {
    try {
      const res = await fetch(api('/api/snapshot'));
      if (!res.ok) throw new Error(`snapshot failed: ${res.status}`);
      setSnapshot(await res.json());
      setMsg("Connected");
    } catch (e) {
      setMsg("API unavailable (running static mode only)");
    }
  }

  async function postControl(action) {
    try {
      const res = await fetch(api('/api/control'), {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action})
      });
      const data = await res.json();
      setMsg(data.message || data.error || 'done');
      await load();
    } catch {
      setMsg(`Control '${action}' queued (API offline in static mode)`);
    }
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, []);

  return <div className="wrap">
    <h1>Trading Bot Dashboard (Stage 2)</h1>
    <p className="muted">Hybrid migration: these panels are HTML; remaining features still in Streamlit.</p>
    <div className="grid">
      <MetricCard label="Bot Status" value={snapshot.bot_status} />
      <MetricCard label="Open Positions" value={snapshot.open_positions} />
      <MetricCard label="Available Cash" value={`$${Number(snapshot.available_cash || 0).toFixed(2)}`} />
      <MetricCard label="Bot Process" value={snapshot.bot_process_running ? 'RUNNING' : 'STOPPED'} />
    </div>

    <div className="card" style={{marginTop:'12px'}}>
      <h3>Controls (migrated)</h3>
      <button className="btn ok" onClick={() => postControl('refresh_scan')}>Run Market Scan</button>
      <button className="btn warn" onClick={() => postControl('pause_trading')}>Pause Trading</button>
      <button className="btn ok" onClick={() => postControl('resume_trading')}>Resume Trading</button>
      <button className="btn ok" onClick={() => postControl('start_bot')}>Start Bot</button>
      <button className="btn warn" onClick={() => postControl('stop_bot')}>Stop Bot</button>
      <button className="btn warn" onClick={() => postControl('restart_bot')}>Restart Bot</button>
      <div style={{marginTop:'8px'}}>{msg}</div>
    </div>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
