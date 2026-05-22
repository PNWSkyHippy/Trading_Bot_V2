// Main App — assembles top bar, taskbar, dock, and all windows
const { useState: $S, useEffect: $E, useRef: $R, useMemo: $M } = React;

const { TopOverview, OpenPositionsPanel, ManualTradePanel, TradeLogPanel, DailyPerfPanel, BacktesterPanel, ChatPanel, ChartPanel } = window.Panels;
const { ManagePositionsPanel, InjectSymbolsPanel, QuickControlsPanel, TerminalPanel, DBBrowserPanel } = window.SidePanels;

// Window definitions
const WINDOW_DEFS = [
  { id: 'overview',         title: 'Overview · Capital & KPIs',  icon: 'activity',  defaultPos: { x: 20, y: 10 },    defaultSize: { w: 1180, h: 360 }, openByDefault: true },
  { id: 'open-positions',   title: 'Open Positions',              icon: 'pin',       defaultPos: { x: 20, y: 380 },   defaultSize: { w: 1180, h: 320 }, openByDefault: true },
  { id: 'manual-trade',     title: 'Manual Trade Entry',          icon: 'edit',      defaultPos: { x: 1210, y: 10 },  defaultSize: { w: 520, h: 420 },  openByDefault: true },
  { id: 'trade-log',        title: "Today's Trade Log",           icon: 'log',       defaultPos: { x: 1210, y: 440 }, defaultSize: { w: 560, h: 360 },  openByDefault: true },
  { id: 'daily-perf',       title: 'Recent Daily Performance',    icon: 'calendar',  defaultPos: { x: 20, y: 710 },   defaultSize: { w: 820, h: 290 },  openByDefault: true },
  { id: 'backtester',       title: 'Strategy Backtester',         icon: 'flask',     defaultPos: { x: 850, y: 810 },  defaultSize: { w: 680, h: 420 },  openByDefault: true },
  { id: 'chat',             title: 'Chat with Bot',               icon: 'chat',      defaultPos: { x: 20, y: 1010 },  defaultSize: { w: 800, h: 300 },  openByDefault: true },
  { id: 'manage-positions', title: 'Manage Positions',            icon: 'sliders',   defaultPos: { x: 360, y: 80 },   defaultSize: { w: 760, h: 540 },  openByDefault: false },
  { id: 'inject-symbols',   title: 'Inject Symbols Into Watchlist',icon: 'telescope',defaultPos: { x: 420, y: 100 },  defaultSize: { w: 740, h: 540 },  openByDefault: false },
  { id: 'terminal',         title: 'PowerShell Workspace',         icon: 'terminal',  defaultPos: { x: 180, y: 140 },  defaultSize: { w: 520, h: 560 },  openByDefault: false },
  { id: 'quick-controls',   title: 'Quick Controls',              icon: 'settings',  defaultPos: { x: 100, y: 50 },   defaultSize: { w: 360, h: 720 },  openByDefault: false },
  { id: 'chart',            title: 'Chart',                       icon: 'activity',  defaultPos: { x: 300, y: 60 },   defaultSize: { w: 1000, h: 600 }, openByDefault: false },
  { id: 'db-browser',       title: 'Database Browser',            icon: 'log',       defaultPos: { x: 260, y: 80 },   defaultSize: { w: 1060, h: 660 }, openByDefault: false },
];

// =========== App Shell ===========
function AppShell() {
  return (
    <WindowProvider defs={WINDOW_DEFS}>
      <Inner />
    </WindowProvider>
  );
}

function Inner() {
  const [now, setNow] = $S(new Date());
  $E(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: '2-digit', year: 'numeric' });
  const timeStr = now.toLocaleTimeString('en-US', { hour12: false });

  return (
    <div className="app">
      <Topbar dateStr={dateStr} timeStr={timeStr} />
      <Workspace />
      <Taskbar />
    </div>
  );
}

function Topbar({ dateStr, timeStr }) {
  const { open } = useWindows();
  return (
    <div className="topbar">
      <div className="brand">
        <span className="brand-mark"></span>
        Autonomous Trading AI
      </div>
      <div className="menu">
        <button onClick={() => open('overview')}>Overview</button>
        <button onClick={() => open('open-positions')}>Positions</button>
        <button onClick={() => open('trade-log')}>Trade Log</button>
        <button onClick={() => open('backtester')}>Backtester</button>
        <button onClick={() => open('terminal')}>Shell</button>
        <button onClick={() => open('chart')}>Chart</button>
        <button onClick={() => open('chat')}>Chat</button>
        <button onClick={() => open('db-browser')}>Database</button>
      </div>
      <div className="spacer"></div>
      <div className="status-pill">
        <span className="dot"></span>
        Trading Active
      </div>
      <div className="clock">{dateStr} · {timeStr} PT</div>
    </div>
  );
}

function Workspace() {
  const { canvasSize } = useWindows();
  const wsRef = $R(null);
  const panRef = $R(null);

  // Shift+wheel → horizontal scroll; plain wheel → vertical scroll (panels handle their own)
  $E(() => {
    const el = wsRef.current;
    if (!el) return;
    const onWheel = (e) => {
      if (e.shiftKey) {
        e.preventDefault();
        el.scrollLeft += e.deltaY || e.deltaX;
      }
      // plain wheel: let workspace scroll vertically (default), panels stop propagation themselves
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // Middle-mouse-button or alt+drag on workspace background → pan canvas
  $E(() => {
    const el = wsRef.current;
    if (!el) return;
    const onPointerDown = (e) => {
      // Only pan on workspace background (not on windows) with middle button or alt+left
      const isBackground = e.target === el || e.target.classList.contains('workspace-canvas') || e.target.classList.contains('dock');
      if (!isBackground) return;
      if (e.button !== 1 && !(e.button === 0 && e.altKey)) return;
      e.preventDefault();
      panRef.current = { x: e.clientX, y: e.clientY, sl: el.scrollLeft, st: el.scrollTop };
      el.style.cursor = 'grabbing';
    };
    const onPointerMove = (e) => {
      const d = panRef.current;
      if (!d) return;
      el.scrollLeft = d.sl - (e.clientX - d.x);
      el.scrollTop = d.st - (e.clientY - d.y);
    };
    const onPointerUp = () => {
      panRef.current = null;
      el.style.cursor = '';
    };
    el.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    return () => {
      el.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, []);

  return (
    <div
      ref={wsRef}
      className="workspace"
      style={{
        '--workspace-w': `${Math.ceil(canvasSize?.width || window.innerWidth)}px`,
        '--workspace-h': `${Math.ceil(canvasSize?.height || window.innerHeight)}px`,
      }}
    >
      <div className="workspace-canvas" />
      <Dock />
      <Window id="overview"><TopOverview live={{ capital: 99203.01, dailyPnl: -331.74, dailyPnlP: -0.33 }} /></Window>
      <Window id="open-positions"><OpenPositionsPanel /></Window>
      <Window id="manual-trade"><ManualTradePanel /></Window>
      <Window id="trade-log"><TradeLogPanel /></Window>
      <Window id="daily-perf"><DailyPerfPanel /></Window>
      <Window id="backtester"><BacktesterPanel /></Window>
      <Window id="chat"><ChatPanel /></Window>
      <Window id="manage-positions"><ManagePositionsPanel /></Window>
      <Window id="inject-symbols"><InjectSymbolsPanel /></Window>
      <Window id="terminal"><TerminalPanel /></Window>
      <Window id="quick-controls"><QuickControlsPanel /></Window>
      <Window id="chart"><ChartPanel /></Window>
      <Window id="db-browser"><DBBrowserPanel /></Window>
    </div>
  );
}

function Dock() {
  const { windows, open, focus } = useWindows();
  const items = [
    { id: 'overview', label: 'Overview', icon: 'activity' },
    { id: 'open-positions', label: 'Positions', icon: 'pin' },
    { id: 'manage-positions', label: 'Manage Positions', icon: 'sliders' },
    { id: 'manual-trade', label: 'Manual Trade', icon: 'edit' },
    { id: 'inject-symbols', label: 'Inject Symbols', icon: 'telescope' },
    { id: 'terminal', label: 'PowerShell', icon: 'terminal' },
    { id: 'trade-log', label: 'Trade Log', icon: 'log' },
    { id: 'daily-perf', label: 'Daily Performance', icon: 'calendar' },
    { id: 'backtester', label: 'Backtester', icon: 'flask' },
    { id: 'chat', label: 'Chat', icon: 'chat' },
    { id: 'chart',          label: 'Chart',           icon: 'activity' },
    { id: 'quick-controls', label: 'Quick Controls', icon: 'settings' },
    { id: 'db-browser',     label: 'Database Browser', icon: 'log' },
  ];
  return (
    <div className="dock">
      {items.map(it => {
        const w = windows[it.id];
        const active = w && w.open && !w.minimized;
        return (
          <button key={it.id} className={cls('dock-btn', active && 'active')} onClick={() => active ? focus(it.id) : open(it.id)} title={it.label}>
            <Icon name={it.icon} size={18} />
            <span className="tip">{it.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function Taskbar() {
  const { windows, focus, toggleMin, open, focusedId } = useWindows();
  const wins = Object.values(windows).filter(w => w.open);
  const cpu = $M(() => 12 + Math.floor(Math.random() * 8), []);
  const resetLayout = () => {
    if (confirm('Reset all windows to their default positions and sizes?')) {
      localStorage.removeItem('tbot.windows.v2');
      location.reload();
    }
  };
  return (
    <div className="taskbar">
      <button className="start-btn" onClick={() => open('quick-controls')}>
        <Icon name="grid" size={12} />
        Apps
      </button>
      <div className="divider"></div>
      {wins.map(w => {
        const isActive = !w.minimized && focusedId === w.id;
        return (
          <div key={w.id} className={cls('task', !w.minimized && 'active', w.minimized && 'minimized')} onClick={() => isActive ? toggleMin(w.id) : focus(w.id)}>
            <Icon name={w.icon} size={11} />
            <span className="label">{w.title}</span>
          </div>
        );
      })}
      <div className="tray">
        <button className="btn ghost sm" onClick={resetLayout} title="Reset all windows to default positions"><Icon name="refresh" size={11} />Reset Layout</button>
        <div className="item"><span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }}></span> Bot · PID 11552</div>
        <div className="item"><Icon name="cpu" size={11} /> CPU {cpu}%</div>
        <div className="item"><Icon name="layers" size={11} /> ML 30%</div>
        <div className="item">$99,203.01</div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<AppShell />);
