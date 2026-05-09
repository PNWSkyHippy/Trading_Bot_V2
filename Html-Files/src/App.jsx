const { useEffect, useState } = React;

function MetricCard({label, value}) {
  return <div className="card"><div className="muted">{label}</div><h2>{value}</h2></div>
}

function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [msg, setMsg] = useState("");

  async function load() {
    const res = await fetch('/api/snapshot');
    setSnapshot(await res.json());
  }

  async function postControl(action) {
    const res = await fetch('/api/control', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action})
    });
    const data = await res.json();
    setMsg(data.message || data.error || 'done');
    await load();
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, []);

  if (!snapshot) return <div className="wrap">Loading...</div>;

  return <div className="wrap">
    <h1>Trading Bot Dashboard (Stage 2)</h1>
    <p className="muted">This page is served by Python and is replacing Streamlit panel-by-panel.</p>
    <div className="grid">
      <MetricCard label="Bot Status" value={snapshot.bot_status} />
      <MetricCard label="Open Positions" value={snapshot.open_positions} />
      <MetricCard label="Available Cash" value={`$${snapshot.available_cash.toFixed(2)}`} />
    </div>

    <div className="card" style={{marginTop:'12px'}}>
      <h3>Controls (migrated)</h3>
      <button className="btn ok" onClick={() => postControl('refresh_scan')}>Run Market Scan</button>
      <button className="btn warn" onClick={() => postControl('pause_trading')}>Pause Trading</button>
      <div style={{marginTop:'8px'}}>{msg}</div>
    </div>
  </div>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
