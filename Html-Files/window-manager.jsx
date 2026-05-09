// Window manager — full OS-style draggable, resizable, minimizable, maximizable windows
const { useState, useEffect, useRef, useCallback, useMemo, createContext, useContext } = React;

const STORAGE_KEY = 'tbot.windows.v2';

const WindowContext = createContext(null);
const useWindows = () => useContext(WindowContext);

function loadState() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
  catch { return {}; }
}
function saveState(s) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch {}
}

function WindowProvider({ children, defs }) {
  // defs: { id, title, icon, defaultPos, defaultSize, content, openByDefault }
  const persisted = useMemo(() => loadState(), []);

  const [windows, setWindows] = useState(() => {
    const obj = {};
    defs.forEach(d => {
      const p = persisted[d.id] || {};
      obj[d.id] = {
        id: d.id,
        title: d.title,
        icon: d.icon,
        x: p.x ?? d.defaultPos.x,
        y: p.y ?? d.defaultPos.y,
        w: p.w ?? d.defaultSize.w,
        h: p.h ?? d.defaultSize.h,
        open: p.open ?? !!d.openByDefault,
        minimized: p.minimized ?? false,
        maximized: p.maximized ?? false,
        z: p.z ?? 1,
      };
    });
    return obj;
  });
  const [focusedId, setFocusedId] = useState(null);
  const zCounter = useRef(
    Math.max(100, ...Object.values(persisted).map(w => Number(w?.z) || 0))
  );

  // Persist
  useEffect(() => {
    const toSave = {};
    Object.entries(windows).forEach(([id, w]) => {
      toSave[id] = { x: w.x, y: w.y, w: w.w, h: w.h, open: w.open, minimized: w.minimized, maximized: w.maximized, z: w.z };
    });
    saveState(toSave);
  }, [windows]);

  const focus = useCallback((id) => {
    zCounter.current += 1;
    const z = zCounter.current;
    setWindows(prev => ({ ...prev, [id]: { ...prev[id], z, minimized: false, open: true } }));
    setFocusedId(id);
  }, []);

  const open = useCallback((id) => {
    zCounter.current += 1;
    const z = zCounter.current;
    setWindows(prev => ({ ...prev, [id]: { ...prev[id], open: true, minimized: false, z } }));
    setFocusedId(id);
  }, []);

  const close = useCallback((id) => {
    setWindows(prev => ({ ...prev, [id]: { ...prev[id], open: false, minimized: false } }));
    setFocusedId(prev => prev === id ? null : prev);
  }, []);

  const toggleMin = useCallback((id) => {
    setWindows(prev => ({ ...prev, [id]: { ...prev[id], minimized: !prev[id].minimized } }));
  }, []);

  const toggleMax = useCallback((id) => {
    zCounter.current += 1;
    const z = zCounter.current;
    setWindows(prev => ({ ...prev, [id]: { ...prev[id], maximized: !prev[id].maximized, minimized: false, z } }));
    setFocusedId(id);
  }, []);

  const updateGeometry = useCallback((id, geom) => {
    setWindows(prev => ({ ...prev, [id]: { ...prev[id], ...geom } }));
  }, []);

  const ctx = { windows, focus, open, close, toggleMin, toggleMax, updateGeometry, focusedId };

  return (
    <WindowContext.Provider value={ctx}>{children}</WindowContext.Provider>
  );
}

function Window({ id, children }) {
  const { windows, focus, close, toggleMin, toggleMax, updateGeometry, focusedId } = useWindows();
  const w = windows[id];
  const ref = useRef(null);
  const drag = useRef(null);
  const wRef = useRef(w);
  useEffect(() => { wRef.current = w; }, [w]);

  useEffect(() => {
    const onMove = (e) => {
      const d = drag.current; if (!d) return;
      const cur = wRef.current; if (!cur) return;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      if (d.type === 'move') {
        const newX = Math.max(-cur.w + 80, Math.min(window.innerWidth - 80, d.origX + dx));
        const newY = Math.max(0, Math.min(window.innerHeight - 80 - 36, d.origY + dy));
        updateGeometry(id, { x: newX, y: newY });
      } else if (d.type === 'resize') {
        let nx = d.origX, ny = d.origY, nw = d.origW, nh = d.origH;
        if (d.dir.includes('e')) nw = Math.max(320, d.origW + dx);
        if (d.dir.includes('s')) nh = Math.max(160, d.origH + dy);
        if (d.dir.includes('w')) {
          nw = Math.max(320, d.origW - dx);
          nx = d.origX + (d.origW - nw);
        }
        if (d.dir.includes('n')) {
          nh = Math.max(160, d.origH - dy);
          ny = Math.max(0, d.origY + (d.origH - nh));
        }
        updateGeometry(id, { x: nx, y: ny, w: nw, h: nh });
      }
    };
    const onUp = () => { drag.current = null; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [id, updateGeometry]);

  if (!w || !w.open || w.minimized) return null;

  const onTitleMouseDown = (e) => {
    if (e.target.closest('.win-controls')) return;
    if (w.maximized) return;
    focus(id);
    drag.current = {
      type: 'move',
      startX: e.clientX, startY: e.clientY,
      origX: w.x, origY: w.y,
    };
  };

  const onResizeStart = (e, dir) => {
    e.stopPropagation();
    focus(id);
    drag.current = {
      type: 'resize', dir,
      startX: e.clientX, startY: e.clientY,
      origX: w.x, origY: w.y, origW: w.w, origH: w.h,
    };
  };

  const style = w.maximized
    ? { left: 0, top: 0, width: '100%', height: '100%', zIndex: w.z }
    : { left: w.x, top: w.y, width: w.w, height: w.h, zIndex: w.z };

  const focused = focusedId === id;

  return (
    <div ref={ref}
      className={`win ${focused ? 'focused' : ''} ${w.maximized ? 'maximized' : ''}`}
      style={style}
      onMouseDown={() => focus(id)}>
      <div className="win-titlebar" onMouseDown={onTitleMouseDown} onDoubleClick={() => toggleMax(id)}>
        <div className="win-title">
          <Icon name={w.icon} size={13} />
          <span className="label">{w.title}</span>
        </div>
        <div className="win-controls">
          <button onClick={() => toggleMin(id)} title="Minimize"><Icon name="minus" size={12} /></button>
          <button onClick={() => toggleMax(id)} title="Maximize"><Icon name="square" size={11} /></button>
          <button className="close" onClick={() => close(id)} title="Close"><Icon name="x" size={12} /></button>
        </div>
      </div>
      <div className="win-body">{children}</div>
      {!w.maximized && (
        <>
          <div className="win-resize-edge n" onMouseDown={(e) => onResizeStart(e, 'n')} />
          <div className="win-resize-edge s" onMouseDown={(e) => onResizeStart(e, 's')} />
          <div className="win-resize-edge e" onMouseDown={(e) => onResizeStart(e, 'e')} />
          <div className="win-resize-edge w" onMouseDown={(e) => onResizeStart(e, 'w')} />
          <div className="win-resize-edge ne" onMouseDown={(e) => onResizeStart(e, 'ne')} />
          <div className="win-resize-edge nw" onMouseDown={(e) => onResizeStart(e, 'nw')} />
          <div className="win-resize-edge se" onMouseDown={(e) => onResizeStart(e, 'se')} />
          <div className="win-resize-edge sw" onMouseDown={(e) => onResizeStart(e, 'sw')} />
        </>
      )}
    </div>
  );
}

window.WindowProvider = WindowProvider;
window.Window = Window;
window.useWindows = useWindows;
