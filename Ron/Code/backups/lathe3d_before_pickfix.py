"""lathe3d.py - spin a 2D profile around an axis into a 3D surface (viewer-side).

Lathe3d       the shape: a profile of (r, h) points beside an axis, swept round it
LatheTool     the editor window: draw the profile beside the axis line, pick the number
              of segments, watch it in the main view, add it to the scene

The shape is held by three Point3ds (base, axis tip, zero-angle reference), so the
library's own move / rotate / scale work on it.  |tip - base| is the size factor:
profile units are multiplied by it.

CSV row (kind lathe3d):
    bx,by,bz, ax,ay,az (axis, its length = size), ux,uy,uz (zero-angle direction),
    segments, sweep deg, flags (1 = curved profile, 2 = faceted in POV), r1,h1, r2,h2, ...
"""
import math
import tkinter as tk
from tkinter import ttk

import numpy as np

from class3d import Point3d, _Geometry3d

SUB = 8                                  # spline samples per profile span
PRESETS = {
    "Hourglass": [(0, 0), (1.6, 0), (1.8, 0.6), (1.5, 1.6), (0.35, 2.5), (1.5, 3.4),
                  (1.8, 4.4), (1.6, 5), (0, 5)],
    "Vase":      [(0, 0), (1.2, 0), (1.9, 1.2), (1.6, 2.8), (0.8, 4), (0.9, 4.6), (1.3, 5)],
    "Goblet":    [(0, 0), (1.5, 0), (1.4, 0.15), (0.25, 0.5), (0.2, 2.2), (0.4, 2.6),
                  (1.4, 3.2), (1.8, 4.4), (1.9, 5)],
    "Bowl":      [(0, 0), (0.9, 0), (1.0, 0.15), (2.2, 0.8), (2.8, 2.0)],
    "Bottle":    [(0, 0), (1.3, 0), (1.4, 0.3), (1.4, 3), (0.5, 4.2), (0.45, 5.2), (0.55, 5.4), (0, 5.4)],
    "Ring":      [(2, -0.5), (2.6, -0.5), (2.6, 0.5), (2, 0.5), (2, -0.5)],
    "Ball":      [(0, -2), (1.41, -1.41), (2, 0), (1.41, 1.41), (0, 2)],
    "Cone":      [(0, 0), (2, 0), (0, 4)],
}


def _unit(v, what="vector"):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError(f"{what} cannot be zero")
    return v / n


def _perp(n):
    return _unit(np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0)))


def catmull_rom(pts, sub=SUB):
    """Smooth curve through every control point (ends held)."""
    P = [np.asarray(p, float) for p in pts]
    P = [P[0]] + P + [P[-1]]
    out = []
    for k in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[k - 1:k + 3]
        for s in range(sub):
            t = s / sub
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


class Lathe3d(_Geometry3d):
    def __init__(self, base=(0, 0, 0), axis=(0, 0, 1), ref=None, profile=None, segments=24,
                 sweep=360.0, curved=True, faceted=False, bc="white", fc="tan", name="Lathe3d"):
        b = np.asarray(base, float)
        a = np.asarray(axis, float)
        s = np.linalg.norm(a)
        an = _unit(a, "Axis")
        u = _perp(an) if ref is None else np.asarray(ref, float)
        u = u - (u @ an) * an
        u = _perp(an) if np.linalg.norm(u) < 1e-9 else u / np.linalg.norm(u)
        self._base = Point3d(*b)
        self._tip = Point3d(*(b + a))
        self._ref = Point3d(*(b + u * s))
        self.set_profile(PRESETS["Hourglass"] if profile is None else profile)
        self._segments = max(3, min(256, int(segments)))
        self._sweep = float(sweep)
        if not 0 < self._sweep <= 360:
            raise ValueError("Sweep must be > 0 and <= 360 degrees")
        self._curved, self._faceted = bool(curved), bool(faceted)
        self._bc, self._fc, self._name = bc, fc, name

    # --- stored points (what move / rotate / scale act on)
    def _points(self):
        return [self._base, self._tip, self._ref]

    def frame(self):
        """(base, unit axis, unit zero-angle dir, unit 90-degree dir, size)."""
        b, t, rf = (np.array(p.get_xyz(), float) for p in self._points())
        a = t - b
        s = float(np.linalg.norm(a))
        an = a / s
        u = rf - b - ((rf - b) @ an) * an
        u = _perp(an) if np.linalg.norm(u) < 1e-9 else u / np.linalg.norm(u)
        return b, an, u, np.cross(an, u), s

    # --- getters / setters
    def get_base(self):
        return self._base

    def get_tip(self):
        return self._tip

    def get_axis(self):
        return tuple(self.frame()[1])

    def get_size(self):
        return self.frame()[4]

    def get_profile(self):
        return list(self._profile)

    def set_profile(self, profile):
        prof = [(max(0.0, float(r)), float(h)) for r, h in profile]
        if len(prof) < 2:
            raise ValueError("A profile needs at least 2 points")
        self._profile = prof

    def get_segments(self):
        return self._segments

    def get_sweep(self):
        return self._sweep

    def is_curved(self):
        return self._curved

    def is_faceted(self):
        return self._faceted

    def get_bc(self):
        return self._bc

    def get_fc(self):
        return self._fc

    def get_name(self):
        return self._name

    def get_center(self):
        """On the axis, halfway up the profile."""
        b, an, _u, _v, s = self.frame()
        hs = [h for _r, h in self._profile]
        return Point3d(*(b + an * s * (min(hs) + max(hs)) / 2))

    def __str__(self):
        b, an, _u, _v, s = self.frame()
        return (f"Lathe3d {self._name}: base ({', '.join(f'{c:g}' for c in np.round(b, 3))}), "
                f"axis ({', '.join(f'{c:g}' for c in np.round(an, 3))}) x{s:g}, "
                f"{len(self._profile)} profile points, {self._segments} segments, sweep {self._sweep:g} deg")

    # --- geometry
    def samples(self):
        """Profile points actually swept: the spline through the control points, or the points."""
        if self._curved and len(self._profile) >= 3:
            pts = catmull_rom(self._profile)
            return [(max(0.0, float(r)), float(h)) for r, h in pts]
        return list(self._profile)

    def angles(self):
        return np.radians(self._sweep) * np.arange(self._segments + 1) / self._segments

    def mesh(self):
        """G (samples, segments+1, 3) world points and N (samples-1, segments, 3) face normals.
        Normals point to the right of the profile's direction: list it bottom to top and
        they point outward."""
        b, an, u, v, s = self.frame()
        prof = np.array(self.samples(), float)
        th = self.angles()
        radial = np.cos(th)[:, None] * u + np.sin(th)[:, None] * v
        G = b + s * (prof[:, 1, None, None] * an + prof[:, 0, None, None] * radial[None])
        n2 = self._span_normals(prof)
        thm = (th[:-1] + th[1:]) / 2
        radm = np.cos(thm)[:, None] * u + np.sin(thm)[:, None] * v
        N = n2[:, 0, None, None] * radm[None] + n2[:, 1, None, None] * an
        return G, N

    @staticmethod
    def _span_normals(prof):
        d = np.diff(prof, axis=0)
        n2 = np.stack([d[:, 1], -d[:, 0]], 1)
        ln = np.linalg.norm(n2, axis=1, keepdims=True)
        return np.where(ln > 1e-12, n2 / np.maximum(ln, 1e-12), 0.0)

    def vertex_normals(self):
        """Smooth normals at every mesh point (for POV smooth triangles)."""
        b, an, u, v, s = self.frame()
        prof = np.array(self.samples(), float)
        n2 = self._span_normals(prof)
        vn = np.zeros((len(prof), 2))
        vn[:-1] += n2
        vn[1:] += n2
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
        th = self.angles()
        radial = np.cos(th)[:, None] * u + np.sin(th)[:, None] * v
        return vn[:, 0, None, None] * radial[None] + vn[:, 1, None, None] * an

    # --- CSV numbers
    def to_nums(self):
        b, t, rf = (np.array(p.get_xyz(), float) for p in self._points())
        flags = (1 if self._curved else 0) + (2 if self._faceted else 0)
        return (list(b) + list(t - b) + list(_unit(rf - b)) + [self._segments, self._sweep, flags]
                + [c for p in self._profile for c in p])

    @classmethod
    def from_nums(cls, n, bc=None, fc=None, name="Lathe3d"):
        n = [float(x) for x in n]
        if len(n) < 16:
            raise ValueError("lathe3d needs base, axis, ref, segments, sweep, flags and 2+ profile points")
        flags = int(round(n[11]))
        prof = [(n[i], n[i + 1]) for i in range(12, len(n) - 1, 2)]
        return cls(n[0:3], n[3:6], n[6:9], prof, int(round(n[9])), n[10],
                   curved=bool(flags & 1), faceted=bool(flags & 2), bc=bc, fc=fc, name=name)


# ----------------------------------------------------------------------------
# POV-Ray: a true lathe for a smooth full turn, else a triangle mesh
# ----------------------------------------------------------------------------
def pov_shape(nums, vec, fmt):
    """(head, body, frame or None).  vec/fmt are pov_export's vector / number formatters."""
    obj = Lathe3d.from_nums(nums)
    b, an, u, v, s = obj.frame()
    if obj.get_sweep() >= 360 - 1e-6 and not obj.is_faceted():
        pts = obj.samples()
        body = f"linear_spline {len(pts)},\n" + ",\n".join(f"<{fmt(r)}, {fmt(h)}>" for r, h in pts)
        return "lathe", body, (u * s, an * s, v * s, b)   # (u, a, a x u) is left-handed, as POV needs
    G, _N = obj.mesh()
    VN = obj.vertex_normals()
    smooth = not obj.is_faceted()
    tris = []
    for i in range(G.shape[0] - 1):
        for j in range(G.shape[1] - 1):
            for (a, c, d) in (((i, j), (i + 1, j), (i + 1, j + 1)), ((i, j), (i + 1, j + 1), (i, j + 1))):
                p = [G[a], G[c], G[d]]
                if np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) < 1e-12:
                    continue                                # collapsed on the axis
                nn = [VN[a], VN[c], VN[d]]
                if smooth and all(np.linalg.norm(x) > 1e-9 for x in nn):
                    tris.append("smooth_triangle { " + ", ".join(f"{vec(q)}, {vec(m)}" for q, m in zip(p, nn)) + " }")
                    continue
                tris.append("triangle { " + ", ".join(vec(q) for q in p) + " }")
    return "mesh", "\n".join(tris), None


# ----------------------------------------------------------------------------
# the editor window
# ----------------------------------------------------------------------------
def _f(v):
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class LatheTool:
    """Profile editor.  Opens on the selected lathe (live edit) or a new one (ghost in the
    main view until 'Add to scene')."""
    W, H = 420, 520

    def __init__(self, app, entry=None):
        self.app = app
        self.entry = entry
        self.orig = (list(entry.nums), entry.c1, entry.c2) if entry is not None else None
        self.top = tk.Toplevel(app.root)
        self.top.transient(app.root)
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.profile = [tuple(p) for p in PRESETS["Hourglass"]]
        self.ppu, self.drag, self._pending = 40.0, None, None
        self._build()
        if entry is not None and entry.obj is not None:
            self.load_entry(entry)
        self.fit()
        self.changed()

    # --- layout
    def _build(self):
        frm = ttk.Frame(self.top, padding=6)
        frm.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.cv = tk.Canvas(left, width=self.W, height=self.H, bg="#15171c", highlightthickness=0)
        self.cv.pack(fill=tk.BOTH, expand=True)
        ttk.Label(left, foreground="#888", text="click: add point at the end   drag: move   "
                  "Shift-click: insert   right-click: delete").pack(anchor="w")
        self.cv.bind("<Configure>", lambda _e: self.draw())
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<Shift-ButtonPress-1>", lambda e: self.press(e, insert=True))
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<ButtonRelease-1>", lambda _e: setattr(self, "drag", None))
        self.cv.bind("<ButtonPress-3>", self.delete_point)
        self.cv.bind("<ButtonPress-2>", self.delete_point)

        right = ttk.Frame(frm, padding=(8, 0, 0, 0))
        right.pack(side=tk.LEFT, fill=tk.Y)
        g = 0
        self.lbl_mode = ttk.Label(right, font=("Segoe UI", 9, "bold"))
        self.lbl_mode.grid(row=g, column=0, columnspan=4, sticky="w")
        g += 1
        ttk.Label(right, text="Name").grid(row=g, column=0, sticky="w")
        self.v_name = tk.StringVar(value=self.app.unique_name("lathe1"))
        ttk.Entry(right, textvariable=self.v_name, width=14).grid(row=g, column=1, columnspan=3, sticky="we")
        g += 1
        ttk.Label(right, text="Preset").grid(row=g, column=0, sticky="w")
        self.v_preset = tk.StringVar(value="Hourglass")
        cb = ttk.Combobox(right, textvariable=self.v_preset, values=list(PRESETS), width=12, state="readonly")
        cb.grid(row=g, column=1, columnspan=3, sticky="we")
        cb.bind("<<ComboboxSelected>>", lambda _e: self.use_preset())
        g += 1
        self.v_seg = tk.StringVar(value="24")
        self.v_sweep = tk.StringVar(value="360")
        for text, var, lo, hi, inc in (("Segments", self.v_seg, 3, 128, 1), ("Sweep deg", self.v_sweep, 10, 360, 10)):
            ttk.Label(right, text=text).grid(row=g, column=0, sticky="w")
            ttk.Spinbox(right, from_=lo, to=hi, increment=inc, textvariable=var, width=6,
                        command=self.changed).grid(row=g, column=1, sticky="w")
            var.trace_add("write", lambda *_a: self.changed())
            g += 1
        self.v_curved = tk.BooleanVar(value=True)
        self.v_faceted = tk.BooleanVar(value=False)
        self.v_snap = tk.BooleanVar(value=True)
        self.v_step = tk.StringVar(value="0.1")
        ttk.Checkbutton(right, text="Curved (spline through the points)", variable=self.v_curved,
                        command=self.changed).grid(row=g, column=0, columnspan=4, sticky="w")
        g += 1
        ttk.Checkbutton(right, text="Faceted in POV (else smooth)", variable=self.v_faceted,
                        command=self.changed).grid(row=g, column=0, columnspan=4, sticky="w")
        g += 1
        ttk.Checkbutton(right, text="Snap", variable=self.v_snap).grid(row=g, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.v_step, width=6).grid(row=g, column=1, sticky="w")
        g += 1
        ttk.Separator(right).grid(row=g, column=0, columnspan=4, sticky="we", pady=4)
        g += 1
        self.v_base = self._xyz(right, g, "Base", (0, 0, 0))
        g += 1
        self.v_axis = self._xyz(right, g, "Axis", (0, 0, 1))
        g += 1
        ttk.Label(right, text="(axis length = size factor)", foreground="#888").grid(
            row=g, column=0, columnspan=4, sticky="w")
        g += 1
        self.v_bc, self.v_fc = tk.StringVar(value="white"), tk.StringVar(value="sandybrown")
        for text, var in (("Border", self.v_bc), ("Fill", self.v_fc)):
            ttk.Label(right, text=text).grid(row=g, column=0, sticky="w")
            ttk.Entry(right, textvariable=var, width=12).grid(row=g, column=1, columnspan=2, sticky="we")
            ttk.Button(right, text="...", width=3, command=lambda v=var: (self.app.pick(v), self.changed())
                       ).grid(row=g, column=3)
            g += 1
        ttk.Separator(right).grid(row=g, column=0, columnspan=4, sticky="we", pady=4)
        g += 1
        self.pts_lb = tk.Listbox(right, height=9, width=22, font=("Consolas", 8))
        self.pts_lb.grid(row=g, column=0, columnspan=4, sticky="we")
        g += 1
        bar = ttk.Frame(right)
        bar.grid(row=g, column=0, columnspan=4, sticky="we", pady=(6, 0))
        self.btn_ok = ttk.Button(bar, command=self.commit)
        self.btn_ok.pack(side=tk.LEFT)
        ttk.Button(bar, text="Fit", command=self.fit).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Clear", command=self.clear).pack(side=tk.LEFT)
        ttk.Button(bar, text="Close", command=self.close).pack(side=tk.RIGHT)
        g += 1
        self.status = ttk.Label(right, foreground="#888", wraplength=220)
        self.status.grid(row=g, column=0, columnspan=4, sticky="w", pady=(4, 0))
        for v in self.v_base + self.v_axis + [self.v_bc, self.v_fc]:
            v.trace_add("write", lambda *_a: self.changed())
        self._mode()

    def _xyz(self, parent, row, label, vals):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        vs = []
        for i, d in enumerate(vals):
            v = tk.StringVar(value=_f(d))
            ttk.Entry(parent, textvariable=v, width=6).grid(row=row, column=1 + i)
            vs.append(v)
        return vs

    def _mode(self):
        if self.entry is None:
            self.top.title("Lathe tool - new shape")
            self.lbl_mode.configure(text="New lathe (ghost in the main view)")
            self.btn_ok.configure(text="Add to scene")
        else:
            self.top.title(f"Lathe tool - {self.entry.name}")
            self.lbl_mode.configure(text=f"Editing {self.entry.name} (live)")
            self.btn_ok.configure(text="Apply")

    def load_entry(self, e):
        o = Lathe3d.from_nums(e.nums)
        n = e.nums
        self.profile = o.get_profile()
        self.v_name.set(e.name)
        self.v_seg.set(str(o.get_segments()))
        self.v_sweep.set(_f(o.get_sweep()))
        self.v_curved.set(o.is_curved())
        self.v_faceted.set(o.is_faceted())
        for v, x in zip(self.v_base + self.v_axis, n[0:6]):
            v.set(_f(x))
        self.v_bc.set(e.c1)
        self.v_fc.set(e.c2)
        self._ref = n[6:9]

    # --- profile canvas: axis line in the middle, right side is the profile, left its mirror
    def origin(self):
        w, h = max(self.cv.winfo_width(), 10), max(self.cv.winfo_height(), 10)
        return w / 2, h - 30

    def to_screen(self, r, h):
        x0, y0 = self.origin()
        return x0 + r * self.ppu, y0 - (h - self.h0) * self.ppu

    def to_profile(self, x, y):
        x0, y0 = self.origin()
        r, h = abs(x - x0) / self.ppu, (y0 - y) / self.ppu + self.h0
        if self.v_snap.get():
            try:
                st = float(self.v_step.get())
            except ValueError:
                st = 0
            if st > 0:
                r, h = round(r / st) * st, round(h / st) * st
        return round(r, 4), round(h, 4)

    def fit(self):
        self.cv.update_idletasks()
        rs = [r for r, _h in self.profile] + [1.0]
        hs = [h for _r, h in self.profile]
        self.h0 = min(hs + [0.0])
        w, ht = max(self.cv.winfo_width(), self.W), max(self.cv.winfo_height(), self.H)
        span_h = max(max(hs) - self.h0, 1.0)
        self.ppu = max(5.0, min((w / 2 - 20) / (max(rs) * 1.15), (ht - 60) / (span_h * 1.1)))
        self.draw()

    def nearest(self, x, y, tol=9):
        best, bi = tol, None
        for i, (r, h) in enumerate(self.profile):
            for sx, sy in (self.to_screen(r, h), self.to_screen(-r, h)):
                d = math.hypot(sx - x, sy - y)
                if d < best:
                    best, bi = d, i
        return bi

    def press(self, ev, insert=False):
        i = self.nearest(ev.x, ev.y)
        if i is not None and not insert:
            self.drag = i
            return "break"
        p = self.to_profile(ev.x, ev.y)
        if insert and len(self.profile) >= 2:     # into the closest span
            q = np.array(p)
            best, at = math.inf, len(self.profile)
            for k in range(len(self.profile) - 1):
                a, b = np.array(self.profile[k]), np.array(self.profile[k + 1])
                ab = b - a
                t = min(1.0, max(0.0, float((q - a) @ ab) / (float(ab @ ab) + 1e-12)))
                d = np.linalg.norm(q - (a + t * ab))
                if d < best:
                    best, at = d, k + 1
            self.profile.insert(at, p)
            self.drag = at
        else:
            self.profile.append(p)
            self.drag = len(self.profile) - 1
        self.changed()
        return "break"

    def motion(self, ev):
        if self.drag is None or self.drag >= len(self.profile):
            return
        self.profile[self.drag] = self.to_profile(ev.x, ev.y)
        self.changed()

    def delete_point(self, ev):
        i = self.nearest(ev.x, ev.y)
        if i is not None and len(self.profile) > 2:
            del self.profile[i]
            self.changed()

    def use_preset(self):
        self.profile = [tuple(p) for p in PRESETS[self.v_preset.get()]]
        self.fit()
        self.changed()

    def clear(self):
        self.profile = []
        self.draw()
        self.status.configure(text="Click beside the axis to place points, bottom to top")

    def draw(self):
        c = self.cv
        c.delete("all")
        if not hasattr(self, "h0"):
            return
        w, ht = c.winfo_width(), c.winfo_height()
        x0, y0 = self.origin()
        step = next(s for s in (0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50, 100) if s * self.ppu >= 18)
        k = 0
        while True:                                   # grid
            xr = x0 + k * step * self.ppu
            if xr > w:
                break
            for x in {xr, 2 * x0 - xr}:
                c.create_line(x, 0, x, ht, fill="#262a33" if k else "#3b4252")
            k += 1
        hmin = self.h0 - y0 / self.ppu
        k = math.floor(hmin / step)
        while True:
            y = self.to_screen(0, k * step)[1]
            if y < 0:
                break
            if y <= ht:
                c.create_line(0, y, w, y, fill="#3b4252" if abs(k * step) < 1e-9 else "#262a33")
                if k % 2 == 0:
                    c.create_text(4, y - 2, anchor="sw", fill="#5c6370", text=_f(k * step), font=("Segoe UI", 7))
            k += 1
        c.create_line(x0, 0, x0, ht, fill="#e06c75", dash=(6, 4), width=2)       # the spin axis
        c.create_text(x0 + 4, 4, anchor="nw", fill="#e06c75", text="axis", font=("Segoe UI", 8))
        if len(self.profile) >= 2:
            pts = catmull_rom(self.profile) if self.v_curved.get() and len(self.profile) >= 3 else self.profile
            for side, col, wd in ((-1, "#5a4a3a", 1), (1, "#f0c674", 2)):
                xy = [v for r, h in pts for v in self.to_screen(side * max(r, 0), h)]
                c.create_line(*xy, fill=col, width=wd)
            if self.v_curved.get():
                xy = [v for r, h in self.profile for v in self.to_screen(r, h)]
                c.create_line(*xy, fill="#4b5263", dash=(2, 3))
        for i, (r, h) in enumerate(self.profile):
            sx, sy = self.to_screen(r, h)
            col = "#98c379" if i == 0 else "#e06c75" if i == len(self.profile) - 1 else "#61afef"
            c.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill=col, outline="#000")
            c.create_text(sx + 7, sy, anchor="w", fill="#8f98a6", text=str(i + 1), font=("Segoe UI", 7))
        self.pts_lb.delete(0, "end")
        for i, (r, h) in enumerate(self.profile):
            self.pts_lb.insert("end", f"{i + 1:>2}  r {_f(r):>6}  h {_f(h):>6}")

    # --- shape <-> main view
    def make(self):
        base = [float(v.get()) for v in self.v_base]
        axis = [float(v.get()) for v in self.v_axis]
        ref = getattr(self, "_ref", None)
        return Lathe3d(base, axis, ref, self.profile, int(float(self.v_seg.get())), float(self.v_sweep.get()),
                       curved=self.v_curved.get(), faceted=self.v_faceted.get(),
                       bc=self.v_bc.get().strip() or None, fc=self.v_fc.get().strip() or None,
                       name=self.v_name.get().strip() or "lathe")

    def changed(self):
        self.draw()
        if self._pending is None:                    # coalesce bursts of drag events
            self._pending = self.top.after(25, self._update_view)

    def _update_view(self):
        self._pending = None
        try:
            obj = self.make()
        except (ValueError, TypeError) as exc:
            self.status.configure(text=str(exc))
            self.app.ghosts = []
            self.app.redraw()
            return
        self.status.configure(text=f"{len(obj.samples())} profile samples x {obj.get_segments()} segments")
        if self.entry is None:
            self.app.ghosts = [(obj.get_name(), obj)]
        else:
            e = self.entry
            e.nums = obj.to_nums()
            e.c1, e.c2 = self.v_bc.get().strip(), self.v_fc.get().strip()
            self.app.rebuild(e)
        self.app.redraw()

    def commit(self):
        try:
            obj = self.make()
        except (ValueError, TypeError) as exc:
            print(f"Lathe: {exc}")
            return
        app = self.app
        if self.entry is None:
            name = obj.get_name()
            if any(e.name == name for e in app.entries):
                print(f"Lathe: name '{name}' already used")
                return
            e = app.make_entry("lathe3d", name, self.v_bc.get().strip(), self.v_fc.get().strip(), obj.to_nums())
            app.rebuild(e)
            app.entries.append(e)
            app.ghosts = []
            self.entry = e
            self._mode()
            print(f"Added {name}: {e.obj}")
        else:
            e = self.entry
            e.nums = obj.to_nums()
            app.rebuild(e)
            print(f"{e.name} updated: {e.obj}")
        self.orig = (list(self.entry.nums), self.entry.c1, self.entry.c2)
        app.save()
        app.selected = ("s", self.entry)
        app.refresh()

    def close(self):
        if self._pending is not None:
            self.top.after_cancel(self._pending)
        app = self.app
        app.ghosts = []
        e = self.entry
        if e is not None and self.orig is not None and (list(e.nums), e.c1, e.c2) != self.orig:
            e.nums, e.c1, e.c2 = list(self.orig[0]), self.orig[1], self.orig[2]   # not applied: put it back
            app.rebuild(e)
        app.lathe_tool = None
        self.top.destroy()
        app.redraw()
