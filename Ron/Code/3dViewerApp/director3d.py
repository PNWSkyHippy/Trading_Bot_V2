"""director3d.py - the RayTrace Camera Director, inside viewer3d.

Camera moves (Line / Arc through B), aim points, field of view, roll and lights,
edited against the REAL viewer scene:
  * the main 3D view shows the path, handles (drag them), lights and the camera frustum
  * the preview shows the actual objects as the director camera sees them
  * Render frame / Render movie run POV-Ray on the viewer's own .pov scene

Shots use the same dictionary as RayTrace/src/camera_path.py.  Inside this window
they are in viewer coordinates (Z up); project files and rayincludes.py presets are
written in POV coordinates (Y up), so tkray_tracer's director opens them too.
"""
import copy
import glob
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog

import numpy as np

import pov_export
import ui_scroll

HERE = os.path.dirname(os.path.abspath(__file__))
RAYTRACE_SRC = os.path.join(HERE, "..", "RayTrace", "src")
if RAYTRACE_SRC not in sys.path:
    sys.path.append(RAYTRACE_SRC)
import camera_path as cp  # noqa: E402

PRESET_FILE = os.path.join(RAYTRACE_SRC, "rayincludes.py")
VEC_KEYS = ("a", "b", "c", "target_a", "target_c")
START = {"a": "c", "target_a": "target_c", "fov_a": "fov_c"}      # start key -> previous move's end key
HANDLE_COL = {"a": "#51cf66", "b": "#ffd43b", "c": "#ff6b6b", "target_a": "#4dd0e1",
              "target_c": "#4dd0e1", "light": "#fff3a0"}
HANDLE_TXT = {"a": "start", "b": "through", "c": "end", "target_a": "aim start", "target_c": "aim end"}


# ----------------------------------------------------------------------------
# coordinates: viewer (Z up) <-> POV / camera_path (Y up) is a y/z swap both ways
# ----------------------------------------------------------------------------
def swap(p):
    return [float(p[0]), float(p[2]), float(p[1])]


def swap_shot(shot):
    s = copy.deepcopy(shot)
    for seg in s["segments"]:
        for k in VEC_KEYS:
            seg[k] = swap(seg[k])
    for lt in s["lights"]:
        lt["position"] = swap(lt["position"])
    if "object" in s:
        s["object"]["position"] = swap(s["object"]["position"])
    return s


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def basis(eye, target, roll=0.0):
    """right, up, fwd for a Z-up world (matches camera_path.camera_basis after the swap)."""
    fwd = unit(np.asarray(target, float) - np.asarray(eye, float))
    right = np.cross(fwd, (0.0, 0.0, 1.0))
    if np.linalg.norm(right) < 1e-6:                  # looking straight up / down
        right = np.array((1.0, 0.0, 0.0))
    right = unit(right)
    up = np.cross(right, fwd)
    a = math.radians(roll)
    return (right * math.cos(a) + up * math.sin(a), up * math.cos(a) - right * math.sin(a), fwd)


def default_shot(app):
    """An arc sweeping round the front of whatever the viewer is looking at."""
    t = np.array(app.target, float)
    fwd, _lv, right = app._cam_axes()
    eye = t - fwd * app.dist * 0.5            # in front of the 3D view's own camera, so it's visible
    r = max(app.dist * 0.5, 1.0)
    a = eye - right * r * 0.6
    c = eye + right * r * 0.6
    b = eye + (0.0, 0.0, r * 0.25)
    return {"name": "Viewer shot",
            "segments": [{"kind": "Arc", "a": list(a), "b": list(b), "c": list(c),
                          "target_a": list(t), "target_c": list(t),
                          "steps": 48, "fov_a": 45, "fov_c": 45}],
            "object": {"kind": "Sphere", "position": list(t), "size": 1, "color": "#75baff"},
            "lights": [], "fps": 24, "ground_y": 0, "roll": 0}


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "shot"


class Director(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Camera Director - real scene")
        self.geometry("1180x720")
        self.configure(bg="#1b1d22")
        self.state_file = os.path.join(app_pov_dir(), "director_shot.json")
        self.shot = self._load_last() or default_shot(app)
        self.frames = []
        self.frame = 0
        self.seg_i = 0
        self.light_i = 0
        self.playing = None
        self._grab = None
        self._handles = []
        self._hover = None
        self._preview_job = None
        self._job = None
        self._undo = []                       # shot copies before main-panel edits
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<F9>", lambda _e: self.render_frame())
        self.resample()
        self.fill_move()
        self.fill_light()
        app.director = self
        app.tree_director()
        app.redraw()

    # ------------------------------------------------------------------ UI
    def _build(self):
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(pw)
        pw.add(left, weight=3)
        self.prev = tk.Canvas(left, bg="#0d0f12", highlightthickness=0, width=760, height=430)
        self.prev.pack(fill=tk.BOTH, expand=True)
        self.prev.bind("<Configure>", lambda _e: self.draw_preview())
        self._steer = None
        self.prev.bind("<ButtonPress-1>", lambda e: self.steer_start(e, "turn"))
        self.prev.bind("<ButtonPress-3>", lambda e: self.steer_start(e, "pan"))
        self.prev.bind("<ButtonPress-2>", lambda e: self.steer_start(e, "pan"))
        for b in ("<B1-Motion>", "<B2-Motion>", "<B3-Motion>"):
            self.prev.bind(b, self.steer_move)
        for b in ("<ButtonRelease-1>", "<ButtonRelease-2>", "<ButtonRelease-3>"):
            self.prev.bind(b, lambda _e: self.steer_end())
        self.prev.bind("<MouseWheel>", self.steer_wheel)
        ui_scroll.x11_wheel(self.prev, self.steer_wheel)
        bar = ttk.Frame(left, padding=3)
        bar.pack(fill=tk.X)
        self.b_play = ttk.Button(bar, text="Play", width=6, command=self.toggle_play)
        self.b_play.pack(side=tk.LEFT)
        ttk.Button(bar, text="|<", width=3, command=lambda: self.goto(0)).pack(side=tk.LEFT)
        ttk.Button(bar, text=">|", width=3, command=lambda: self.goto(len(self.frames) - 1)).pack(side=tk.LEFT)
        ttk.Button(bar, text="Play in Taichi", command=lambda: self.app.open_preview(play=True)).pack(
            side=tk.LEFT, padx=(4, 0))
        self.v_frame = tk.DoubleVar(value=0)
        self.scrub = ttk.Scale(bar, from_=0, to=1, variable=self.v_frame,
                               command=lambda v: self.goto(int(round(float(v))), from_scale=True))
        self.scrub.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.l_frame = ttk.Label(bar, text="", width=16)
        self.l_frame.pack(side=tk.LEFT)
        bar2 = ttk.Frame(left, padding=(3, 0, 3, 3))
        bar2.pack(fill=tk.X)
        ttk.Label(bar2, text="FPS").pack(side=tk.LEFT)
        self.v_fps = tk.StringVar(value=str(self.shot.get("fps", 24)))
        ttk.Spinbox(bar2, from_=1, to=120, width=4, textvariable=self.v_fps,
                    command=self.apply_shot).pack(side=tk.LEFT, padx=2)
        ttk.Label(bar2, text="Roll").pack(side=tk.LEFT, padx=(8, 0))
        self.v_roll = tk.StringVar(value=str(self.shot.get("roll", 0)))
        e = ttk.Entry(bar2, textvariable=self.v_roll, width=6)
        e.pack(side=tk.LEFT, padx=2)
        e.bind("<Return>", lambda _e: self.apply_shot())
        self.v_pgrid = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar2, text="Grid", variable=self.v_pgrid, command=self.draw_preview).pack(side=tk.LEFT, padx=8)
        self.v_path = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar2, text="Path in 3D view", variable=self.v_path,
                        command=self.app.redraw).pack(side=tk.LEFT)
        ttk.Button(bar2, text="3D view = this frame", command=self.view_from_frame).pack(side=tk.RIGHT)

        holder, right = ui_scroll.scrollable(pw, padding=4)
        pw.add(holder, weight=2)
        # status + progress first, packed to the bottom, so a tall notebook can't push them off screen
        self.status = ttk.Label(right, text="Drag the handles in the 3D view (Shift-drag = in / out).\n"
                                            "Preview: left-drag turn, right-drag pan, wheel dolly, Ctrl-wheel zoom.",
                                foreground="#8f98a6", wraplength=380)
        self.status.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))
        self.progress = ttk.Progressbar(right, mode="determinate")
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))
        nb = ttk.Notebook(right)
        nb.pack(fill=tk.BOTH, expand=True)
        self._build_moves(nb)
        self._build_lights(nb)
        self._build_output(nb)

    def _vec_row(self, parent, row, label, key, extra=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        vs = [tk.StringVar() for _ in range(3)]
        for j, v in enumerate(vs):
            en = ttk.Entry(parent, textvariable=v, width=10)
            en.grid(row=row, column=1 + j, padx=1, pady=1)
            en.bind("<Return>", lambda _e: self.apply_move())
        if extra:
            ttk.Button(parent, text=extra[0], width=7, command=extra[1]).grid(row=row, column=4, padx=2)
        self.mv[key] = vs

    def _build_moves(self, nb):
        f = ttk.Frame(nb, padding=4)
        nb.add(f, text="Camera moves")
        top = ttk.Frame(f)
        top.pack(fill=tk.X)
        self.lb_moves = tk.Listbox(top, height=5, exportselection=False, bg="#111317", fg="#d8dde6")
        self.lb_moves.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lb_moves.bind("<<ListboxSelect>>", lambda _e: self._pick_move())
        bb = ttk.Frame(top)
        bb.pack(side=tk.LEFT, padx=4)
        ttk.Button(bb, text="+ Line", command=lambda: self.add_move("Line")).pack(fill=tk.X)
        ttk.Button(bb, text="+ Arc", command=lambda: self.add_move("Arc")).pack(fill=tk.X)
        ttk.Button(bb, text="Delete", command=self.delete_move).pack(fill=tk.X)

        g = ttk.Frame(f)
        g.pack(fill=tk.X, pady=6)
        self.mv = {}
        ttk.Label(g, text="Move type").grid(row=0, column=0, sticky="w")
        self.v_kind = tk.StringVar()
        cb = ttk.Combobox(g, textvariable=self.v_kind, values=("Line", "Arc"), width=6, state="readonly")
        cb.grid(row=0, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda _e: self.apply_move())
        for j, t in enumerate(("X", "Y", "Z")):
            ttk.Label(g, text=t).grid(row=1, column=1 + j)
        here = lambda k: (lambda: self.set_from_viewer(k))        # noqa: E731
        self._vec_row(g, 2, "Start A", "a", ("= view", here("a")))
        self._vec_row(g, 3, "Through B", "b", ("middle", self.b_middle))
        self._vec_row(g, 4, "End C", "c", ("= view", here("c")))
        self._vec_row(g, 5, "Aim start", "target_a", ("= view", here("target_a")))
        self._vec_row(g, 6, "Aim end", "target_c", ("= view", here("target_c")))
        ttk.Label(g, text="Frames").grid(row=7, column=0, sticky="w")
        self.v_steps = tk.StringVar()
        ttk.Entry(g, textvariable=self.v_steps, width=8).grid(row=7, column=1)
        ttk.Label(g, text="FOV start / end").grid(row=8, column=0, sticky="w")
        self.v_fova, self.v_fovc = tk.StringVar(), tk.StringVar()
        ttk.Entry(g, textvariable=self.v_fova, width=8).grid(row=8, column=1)
        ttk.Entry(g, textvariable=self.v_fovc, width=8).grid(row=8, column=2)
        for w in g.grid_slaves(row=7) + g.grid_slaves(row=8):
            if isinstance(w, ttk.Entry):
                w.bind("<Return>", lambda _e: self.apply_move())
        ttk.Button(f, text="Apply  [Enter]", command=self.apply_move).pack(anchor="w")
        ttk.Label(f, text="'= view' copies the main 3D view's eye (A/C) or focus point (aims).\n"
                          "Each move starts where the previous one ends - edits keep them joined.",
                  foreground="#8f98a6").pack(anchor="w", pady=4)

    def _build_lights(self, nb):
        f = ttk.Frame(nb, padding=4)
        nb.add(f, text="Lights")
        top = ttk.Frame(f)
        top.pack(fill=tk.X)
        self.lb_lights = tk.Listbox(top, height=5, exportselection=False, bg="#111317", fg="#d8dde6")
        self.lb_lights.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lb_lights.bind("<<ListboxSelect>>", lambda _e: self._pick_light())
        bb = ttk.Frame(top)
        bb.pack(side=tk.LEFT, padx=4)
        ttk.Button(bb, text="+ Light", command=self.add_light).pack(fill=tk.X)
        ttk.Button(bb, text="Delete", command=self.delete_light).pack(fill=tk.X)
        g = ttk.Frame(f)
        g.pack(fill=tk.X, pady=6)
        ttk.Label(g, text="Position").grid(row=0, column=0, sticky="w")
        self.v_lpos = [tk.StringVar() for _ in range(3)]
        for j, v in enumerate(self.v_lpos):
            en = ttk.Entry(g, textvariable=v, width=8)
            en.grid(row=0, column=1 + j, padx=1)
            en.bind("<Return>", lambda _e: self.apply_light())
        ttk.Label(g, text="Color").grid(row=1, column=0, sticky="w")
        self.v_lcol = tk.StringVar()
        ttk.Entry(g, textvariable=self.v_lcol, width=8).grid(row=1, column=1)
        ttk.Button(g, text="...", width=3, command=self.pick_light_color).grid(row=1, column=2, sticky="w")
        ttk.Label(g, text="Brightness").grid(row=2, column=0, sticky="w")
        self.v_lbri = tk.StringVar()
        en = ttk.Entry(g, textvariable=self.v_lbri, width=8)
        en.grid(row=2, column=1)
        en.bind("<Return>", lambda _e: self.apply_light())
        ttk.Button(f, text="Apply  [Enter]", command=self.apply_light).pack(anchor="w")
        ttk.Label(f, text="No lights = the viewer's own lighting: a key light plus a\n"
                          "fill light that rides along with the camera (good for tunnels).",
                  foreground="#8f98a6").pack(anchor="w", pady=4)

    def _build_output(self, nb):
        f = ttk.Frame(nb, padding=4)
        nb.add(f, text="Render / save")
        r = ttk.Frame(f)
        r.pack(fill=tk.X)
        ttk.Label(r, text="Size").pack(side=tk.LEFT)
        self.v_w, self.v_h = tk.StringVar(value="640"), tk.StringVar(value="360")
        for v in (self.v_w, self.v_h):
            en = ttk.Entry(r, textvariable=v, width=6)
            en.pack(side=tk.LEFT, padx=2)
            en.bind("<Return>", lambda _e: self.draw_preview())
        self.v_q = tk.StringVar(value="Draft")
        ttk.Combobox(r, textvariable=self.v_q, values=("Draft", "Final"), width=6,
                     state="readonly").pack(side=tk.LEFT, padx=4)
        ttk.Button(f, text="Render this frame  [F9]", command=self.render_frame).pack(fill=tk.X, pady=(8, 2))
        ttk.Button(f, text="Render movie (all frames + GIF)", command=self.render_movie).pack(fill=tk.X, pady=2)
        ttk.Button(f, text="Stop movie render", command=self.stop_movie).pack(fill=tk.X, pady=2)
        ttk.Button(f, text="Export POV animation (.pov + .ini)", command=self.export_animation).pack(fill=tk.X, pady=2)
        ttk.Separator(f).pack(fill=tk.X, pady=8)
        r = ttk.Frame(f)
        r.pack(fill=tk.X)
        ttk.Label(r, text="Shot name").pack(side=tk.LEFT)
        self.v_name = tk.StringVar(value=self.shot.get("name", "Viewer shot"))
        ttk.Entry(r, textvariable=self.v_name, width=24).pack(side=tk.LEFT, padx=4)
        ttk.Button(f, text="Save project .json...", command=self.save_project).pack(fill=tk.X, pady=2)
        ttk.Button(f, text="Load project .json...", command=self.load_project).pack(fill=tk.X, pady=2)
        ttk.Button(f, text="Save shot to rayincludes.py", command=self.save_preset).pack(fill=tk.X, pady=2)
        r = ttk.Frame(f)
        r.pack(fill=tk.X, pady=2)
        self.v_preset = tk.StringVar()
        self.cb_preset = ttk.Combobox(r, textvariable=self.v_preset, width=26, state="readonly")
        self.cb_preset.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(r, text="Load preset", command=self.load_preset).pack(side=tk.LEFT, padx=2)
        self._refresh_presets()
        ttk.Button(f, text="New shot from the 3D view", command=self.new_shot).pack(fill=tk.X, pady=(8, 2))
        ttk.Label(f, text="Projects / presets are stored Y-up (POV), so tkray_tracer's\n"
                          "Camera Director opens the same shots.",
                  foreground="#8f98a6").pack(anchor="w", pady=4)

    # ------------------------------------------------------------- shot data
    def _load_last(self):
        try:
            with open(self.state_file, encoding="utf-8") as fh:
                shot = swap_shot(json.load(fh))
            cp.sample_shot(swap_shot(shot))
            return shot
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def autosave(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as fh:
                json.dump(swap_shot(self.shot), fh, indent=2)
        except OSError:
            pass

    def resample(self):
        try:
            self.frames = cp.sample_shot(swap_shot(self.shot))       # validates too
        except ValueError as exc:
            self.say(str(exc), err=True)
            return False
        self.frames = [{"camera": swap(p["camera"]), "lookat": swap(p["lookat"]), "vfov": p["vfov"]}
                       for p in self.frames]
        self.frame = min(self.frame, len(self.frames) - 1)
        self.scrub.configure(to=max(1, len(self.frames) - 1))
        self.v_frame.set(self.frame)
        self.draw_preview()
        return True

    def changed(self):
        """After any edit: re-sample, redraw both views, remember the shot."""
        if self.resample():
            self.autosave()
        self.app.tree_director()
        self.app.redraw()
        self.app.preview_refresh()                     # Taichi preview open: new path

    def say(self, text, err=False):
        self.status.configure(text=text, foreground="#ff7b72" if err else "#8f98a6")

    def apply_shot(self):
        try:
            self.shot["fps"] = max(1, min(120, int(float(self.v_fps.get()))))
            self.shot["roll"] = float(self.v_roll.get())
        except ValueError:
            self.say("FPS and roll need numbers", err=True)
            return
        self.changed()

    def set_point(self, i, key, value):
        """Write one point and keep neighbouring moves joined (start of i == end of i-1)."""
        segs = self.shot["segments"]
        segs[i][key] = [float(v) for v in value]
        if key in START and i > 0:
            segs[i - 1][START[key]] = list(segs[i][key])
        end_to_start = {v: k for k, v in START.items()}
        if key in end_to_start and i + 1 < len(segs):
            segs[i + 1][end_to_start[key]] = list(segs[i][key])

    # --------------------------------------------------------------- moves
    def fill_move(self):
        segs = self.shot["segments"]
        self.seg_i = min(self.seg_i, len(segs) - 1)
        self.lb_moves.delete(0, "end")
        for i, s in enumerate(segs):
            self.lb_moves.insert("end", f"{i + 1}. {s['kind']}  {s['steps']} frames")
        self.lb_moves.selection_set(self.seg_i)
        s = segs[self.seg_i]
        self.v_kind.set(s["kind"])
        for k in VEC_KEYS:
            for v, val in zip(self.mv[k], s[k]):
                v.set(f"{val:.1f}".rstrip("0").rstrip(".") if abs(val) >= 100 else f"{val:.4g}")
        self.v_steps.set(str(s["steps"]))
        self.v_fova.set(f"{s['fov_a']:.4g}")
        self.v_fovc.set(f"{s['fov_c']:.4g}")

    def _pick_move(self):
        sel = self.lb_moves.curselection()
        if sel:
            self.seg_i = sel[0]
            self.fill_move()
            # jump the preview to the start of that move
            self.goto(sum(int(s["steps"]) for s in self.shot["segments"][:self.seg_i]))
            self.app.redraw()

    def apply_move(self):
        i = self.seg_i
        seg = self.shot["segments"][i]
        try:
            vals = {k: [float(v.get()) for v in self.mv[k]] for k in VEC_KEYS}
            steps = int(float(self.v_steps.get()))
            fa, fc = float(self.v_fova.get()), float(self.v_fovc.get())
        except ValueError:
            self.say("Every box needs a number", err=True)
            return
        seg["kind"] = self.v_kind.get() or "Line"
        seg["steps"] = max(1, min(2000, steps))
        for k in VEC_KEYS:
            if vals[k] != seg[k]:
                self.set_point(i, k, vals[k])
        for k, val in (("fov_a", fa), ("fov_c", fc)):
            seg[k] = max(1.0, min(170.0, val))
            self.set_point_scalar(i, k)
        self.fill_move()
        self.changed()
        self.say(f"Move {i + 1} updated - {len(self.frames)} frames in the shot")

    def set_point_scalar(self, i, key):
        segs = self.shot["segments"]
        if key == "fov_a" and i > 0:
            segs[i - 1]["fov_c"] = segs[i]["fov_a"]
        if key == "fov_c" and i + 1 < len(segs):
            segs[i + 1]["fov_a"] = segs[i]["fov_c"]

    def add_move(self, kind):
        last = self.shot["segments"][-1]
        a, ta = np.array(last["c"], float), np.array(last["target_c"], float)
        span = max(np.linalg.norm(a - ta), 1.0)
        right, _up, fwd = basis(a, ta, 0)
        c = a + right * span * 0.5 + fwd * span * 0.25
        self.shot["segments"].append({
            "kind": kind, "a": list(a), "b": list((a + c) / 2 + np.array((0, 0, span * 0.15 if kind == "Arc" else 0))),
            "c": list(c), "target_a": list(ta), "target_c": list(ta),
            "steps": 24, "fov_a": last["fov_c"], "fov_c": last["fov_c"]})
        self.seg_i = len(self.shot["segments"]) - 1
        self.fill_move()
        self.changed()

    def delete_move(self):
        segs = self.shot["segments"]
        if len(segs) == 1:
            self.say("A shot needs at least one move", err=True)
            return
        del segs[self.seg_i]
        if 0 < self.seg_i < len(segs):                    # close the gap left behind
            self.set_point(self.seg_i - 1, "c", segs[self.seg_i - 1]["c"])
            self.set_point(self.seg_i - 1, "target_c", segs[self.seg_i - 1]["target_c"])
            segs[self.seg_i]["fov_a"] = segs[self.seg_i - 1]["fov_c"]
        self.seg_i = max(0, self.seg_i - 1)
        self.fill_move()
        self.changed()

    def b_middle(self):
        s = self.shot["segments"][self.seg_i]
        self.set_point(self.seg_i, "b", list((np.array(s["a"]) + np.array(s["c"])) / 2))
        self.fill_move()
        self.changed()

    def set_from_viewer(self, key):
        app = self.app
        fwd, _lv, _rt = app._cam_axes()
        tgt = np.array(app.target, float)
        val = tgt if key.startswith("target") else tgt - fwd * app.dist
        self.set_point(self.seg_i, key, list(val))
        self.fill_move()
        self.changed()

    def new_shot(self):
        self.shot = default_shot(self.app)
        self.seg_i = self.light_i = self.frame = 0
        self.v_fps.set("24")
        self.v_roll.set("0")
        self.fill_move()
        self.fill_light()
        self.changed()

    # --------------------------------------------------------------- lights
    def fill_light(self):
        lts = self.shot["lights"]
        self.lb_lights.delete(0, "end")
        for i, lt in enumerate(lts):
            p = ", ".join(f"{v:.3g}" for v in lt["position"])
            self.lb_lights.insert("end", f"{i + 1}. ({p})  {lt['color']}  x{lt['brightness']:.3g}")
        if not lts:
            self.lb_lights.insert("end", "(none - viewer lighting)")
            for v in self.v_lpos:
                v.set("")
            self.v_lcol.set("")
            self.v_lbri.set("")
            return
        self.light_i = min(self.light_i, len(lts) - 1)
        self.lb_lights.selection_set(self.light_i)
        lt = lts[self.light_i]
        for v, val in zip(self.v_lpos, lt["position"]):
            v.set(f"{val:.4g}")
        self.v_lcol.set(lt["color"])
        self.v_lbri.set(f"{lt['brightness']:.3g}")

    def _pick_light(self):
        sel = self.lb_lights.curselection()
        if sel and self.shot["lights"]:
            self.light_i = sel[0]
            self.fill_light()

    def add_light(self):
        fr = self.frames[self.frame] if self.frames else None
        if fr:
            eye, tgt = np.array(fr["camera"]), np.array(fr["lookat"])
            right, up, _f = basis(eye, tgt, 0)
            span = max(np.linalg.norm(eye - tgt), 1.0)
            pos = eye + right * span * 0.4 + up * span * 0.5
        else:
            pos = np.array((0.0, 0.0, 10.0))
        self.shot["lights"].append({"position": list(pos), "color": "#ffffff", "brightness": 1.0})
        self.light_i = len(self.shot["lights"]) - 1
        self.fill_light()
        self.changed()

    def delete_light(self):
        if self.shot["lights"]:
            del self.shot["lights"][self.light_i]
            self.light_i = max(0, self.light_i - 1)
            self.fill_light()
            self.changed()

    def apply_light(self):
        if not self.shot["lights"]:
            return
        lt = self.shot["lights"][self.light_i]
        try:
            lt["position"] = [float(v.get()) for v in self.v_lpos]
            lt["brightness"] = max(0.0, float(self.v_lbri.get()))
            cp.rgb(self.v_lcol.get())
            lt["color"] = self.v_lcol.get()
        except ValueError as exc:
            self.say(f"Light: {exc}", err=True)
            return
        self.fill_light()
        self.changed()

    def pick_light_color(self):
        if not self.shot["lights"]:
            return
        col = colorchooser.askcolor(self.v_lcol.get() or "#ffffff", parent=self)[1]
        if col:
            self.v_lcol.set(col)
            self.apply_light()

    # ------------------------------------------------------------- preview
    def aspect(self):
        try:
            return max(16, float(self.v_w.get())) / max(16, float(self.v_h.get()))
        except ValueError:
            return 16 / 9

    def frame_view(self, fr, w, h):
        """The director camera for one frame, in the form App.draw_through wants."""
        eye, tgt = np.array(fr["camera"], float), np.array(fr["lookat"], float)
        right, up, fwd = basis(eye, tgt, self.shot.get("roll", 0))
        f = (h / 2) / math.tan(math.radians(fr["vfov"]) / 2)
        near = max(1e-4, 0.002 * float(np.linalg.norm(tgt - eye)))
        return {"eye": eye, "right": right, "up": up, "fwd": fwd, "f": f, "near": near}

    def draw_preview(self):
        c = self.prev
        if not self.frames or not c.winfo_exists():
            return
        cw, ch = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        asp = self.aspect()
        w, h = (cw, cw / asp) if cw / ch < asp else (ch * asp, ch)
        fr = self.frames[self.frame]
        try:
            self.app.draw_through(c, self.frame_view(fr, w, h), grid=self.v_pgrid.get())
        except Exception as exc:                          # noqa: BLE001 - keep the window alive
            c.delete("all")
            c.create_text(10, 10, anchor="nw", fill="#ff7b72", text=f"preview: {exc}")
            return
        x0, y0 = (cw - w) / 2, (ch - h) / 2                # letterbox: what POV will frame
        for box in ((0, 0, cw, y0), (0, y0 + h, cw, ch), (0, 0, x0, ch), (x0 + w, 0, cw, ch)):
            c.create_rectangle(*box, fill="#000000", outline="")
        c.create_rectangle(x0, y0, x0 + w, y0 + h, outline="#3a404b")
        cam = ", ".join(f"{v:.3g}" for v in fr["camera"])
        c.create_text(x0 + 6, y0 + 6, anchor="nw", fill="#8f98a6", font=("Segoe UI", 8),
                      text=f"frame {self.frame + 1}/{len(self.frames)}   cam ({cam})   fov {fr['vfov']:.3g}")
        self.l_frame.configure(text=f"{self.frame + 1} / {len(self.frames)}  "
                                    f"{self.frame / max(1, self.shot.get('fps', 24)):.2f}s")

    def goto(self, i, from_scale=False):
        if not self.frames:
            return
        self.frame = max(0, min(len(self.frames) - 1, i))
        if not from_scale:
            self.v_frame.set(self.frame)
        self.draw_preview()
        if self.v_path.get():
            self.app.redraw()

    def toggle_play(self):
        if self.playing:
            self.after_cancel(self.playing)
            self.playing = None
            self.b_play.configure(text="Play")
            return
        if self.frame >= len(self.frames) - 1:
            self.frame = 0
        self.b_play.configure(text="Stop")
        self._step()

    def _step(self):
        self.goto(self.frame)
        if self.frame >= len(self.frames) - 1:
            self.playing = None
            self.b_play.configure(text="Play")
            return
        self.frame += 1
        self.playing = self.after(int(1000 / max(1, self.shot.get("fps", 24))), self._step)

    def view_from_frame(self):
        """Put the main 3D view's orbit camera where the director camera is."""
        fr = self.frames[self.frame]
        eye, tgt = np.array(fr["camera"], float), np.array(fr["lookat"], float)
        d = tgt - eye
        app = self.app
        app.dist = max(float(np.linalg.norm(d)), 1e-3)
        app.target = tuple(tgt)
        app.yaw = math.atan2(d[0], d[1])
        app.pitch = max(-1.55, min(1.55, math.asin(max(-1.0, min(1.0, -d[2] / app.dist)))))
        h = max(app.canvas.winfo_height(), 50)
        app.scale = (h / 2) / math.tan(math.radians(fr["vfov"]) / 2) / app.dist
        app.redraw()

    # ------------------- the shot's cameras, aims and lights as objects in the main tree
    def tree_items(self):
        """(iid, label, kind) rows for the main viewer's object tree."""
        rows = [("d:shot", "Whole shot (path + lights)", "shot")]
        for j in range(len(self.shot["segments"]) + 1):
            rows.append((f"d:cam{j}", f"Camera key {j + 1}", "camera"))
            rows.append((f"d:aim{j}", f"Aim {j + 1}", "aim"))
        for i in range(len(self.shot["lights"])):
            rows.append((f"d:light{i}", f"Light {i + 1}", "light"))
        return rows

    def item_refs(self, iid):
        """Point slots an item covers: (move index, key) or ("light", index)."""
        what = iid[2:]
        if what == "shot":
            refs = [(i, k) for i, s in enumerate(self.shot["segments"])
                    for k in ("a", "b", "c", "target_a", "target_c") if k in s]
            return refs + [("light", i) for i in range(len(self.shot["lights"]))]
        if what.startswith("light"):
            return [("light", int(what[5:]))]
        i, ck, ak, _fk = self.key_ref(int(what[3:]))
        return [(i, ck), (i, ak)] if what.startswith("cam") else [(i, ak)]

    def _slot(self, r):
        return self.shot["lights"][r[1]]["position"] if r[0] == "light" else self.shot["segments"][r[0]][r[1]]

    def item_center(self, iid):
        """A camera key's center is its eye (so it turns in place); the whole shot uses the average."""
        pts = [np.array(self._slot(r), float) for r in self.item_refs(iid)]
        return sum(pts) / len(pts) if iid == "d:shot" else pts[0]

    def transform_item(self, iid, fn):
        """New position = fn(old) for every point of the item; one Undo step."""
        self._undo.append(copy.deepcopy(self.shot))
        refs = self.item_refs(iid)
        new = [[float(v) for v in fn(np.array(self._slot(r), float))] for r in refs]
        for r, p in zip(refs, new):
            if r[0] == "light":
                self.shot["lights"][r[1]]["position"] = p
            elif iid == "d:shot":                  # every point moves, joins stay joined
                self.shot["segments"][r[0]][r[1]] = p
            else:
                self.set_point(r[0], r[1], p)
        self.fill_move()
        self.fill_light()
        self.changed()

    def undo(self):
        if not self._undo:
            print("Director: nothing to undo")
            return
        self.shot = self._undo.pop()
        self.fill_move()
        self.fill_light()
        self.changed()
        print("Director: undone")

    def select_item(self, iid):
        """Tree picked a director item: show that key pose in the preview and the Moves tab."""
        what = iid[2:]
        if what.startswith(("cam", "aim")):
            j = int(what[3:])
            self.seg_i = self.key_ref(j)[0]
            self.fill_move()
            self.goto(self.key_frames()[j])
        elif what.startswith("light"):
            self.light_i = int(what[5:])
            self.fill_light()

    def look_through(self, iid):
        """Main 3D view = that camera key (aims: the key they belong to)."""
        what = iid[2:]
        if what.startswith(("cam", "aim")):
            self.goto(self.key_frames()[int(what[3:])])
        self.view_from_frame()

    def key_from_view(self, iid):
        """Put that camera key (eye + aim) where the main 3D view is looking from / at."""
        what = iid[2:]
        if not what.startswith(("cam", "aim")):
            print("Camera = 3D view: select a Camera key in the tree")
            return
        app = self.app
        fwd, _lv, _rt = app._cam_axes()
        tgt = np.array(app.target, float)
        self._undo.append(copy.deepcopy(self.shot))
        i, ck, ak, _fk = self.key_ref(int(what[3:]))
        self.set_point(i, ck, list(tgt - fwd * app.dist))
        self.set_point(i, ak, list(tgt))
        self.fill_move()
        self.changed()
        print(f"Camera key {int(what[3:]) + 1} = 3D view")

    # --------------------------------------- steering the camera in the preview
    def key_frames(self):
        """Frame index of every key pose: start of move 1, then the end of each move."""
        ks = [0]
        for s in self.shot["segments"]:
            ks.append(ks[-1] + int(s["steps"]))
        return ks

    def key_ref(self, j):
        """(move index, camera key, aim key, fov key) that key pose j is stored in."""
        n = len(self.shot["segments"])
        return (j, "a", "target_a", "fov_a") if j < n else (n - 1, "c", "target_c", "fov_c")

    def _snap_key(self):
        """Jump the preview to the key pose nearest the current frame and return its ref."""
        ks = self.key_frames()
        j = min(range(len(ks)), key=lambda k: abs(ks[k] - self.frame))
        self.goto(ks[j])
        ref = self.key_ref(j)
        self.seg_i = ref[0]
        self.fill_move()
        where = "start" if ref[1] == "a" else "end"
        self.say(f"Steering move {ref[0] + 1} {where} (frame {ks[j] + 1}) - scrub to another key to steer it")
        return ref

    def steer_start(self, ev, mode):
        if not self.frames:
            return
        self.prev.focus_set()
        self._steer = {"mode": mode, "x": ev.x, "y": ev.y, "ref": self._snap_key()}

    def steer_move(self, ev):
        st = self._steer
        if not st:
            return
        dx, dy = ev.x - st["x"], ev.y - st["y"]
        st["x"], st["y"] = ev.x, ev.y
        i, ck, ak, fk = st["ref"]
        seg = self.shot["segments"][i]
        eye, tgt = np.array(seg[ck], float), np.array(seg[ak], float)
        d = tgt - eye
        dist = max(float(np.linalg.norm(d)), 1e-6)
        if st["mode"] == "turn":                 # look around: the camera stays, the aim swings
            az = math.atan2(d[1], d[0]) - dx * 0.005
            el = max(-1.5, min(1.5, math.asin(max(-1.0, min(1.0, d[2] / dist))) - dy * 0.005))
            tgt = eye + dist * np.array((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
        else:                                    # pan: camera and aim slide together, scene follows the mouse
            right, up, _f = basis(eye, tgt, 0)
            px = dist * math.tan(math.radians(seg[fk]) / 2) * 2 / max(self.prev.winfo_height(), 50)
            move = (-right * dx + up * dy) * px
            eye, tgt = eye + move, tgt + move
        self.set_point(i, ck, eye)
        self.set_point(i, ak, tgt)
        self._live()

    def steer_wheel(self, ev):
        if not self.frames:
            return
        i, ck, ak, fk = self._snap_key()
        seg = self.shot["segments"][i]
        notch = 1 if ev.delta > 0 else -1
        if ev.state & 0x0004:                    # Ctrl: zoom lens (FOV)
            seg[fk] = max(1.0, min(170.0, seg[fk] * 0.92 ** notch))
            self.set_point_scalar(i, fk)
        else:                                    # dolly: move camera + aim along the view
            eye, tgt = np.array(seg[ck], float), np.array(seg[ak], float)
            d = tgt - eye
            move = d * 0.1 * notch
            self.set_point(i, ck, eye + move)
            self.set_point(i, ak, tgt + move)
        self.fill_move()
        self.changed()

    def steer_end(self):
        if self._steer:
            self._steer = None
            self.fill_move()
            self.changed()

    def _live(self):
        """Cheap re-sample while dragging (no autosave), redraw both views at most ~30x a second."""
        try:
            self.frames = [{"camera": swap(q["camera"]), "lookat": swap(q["lookat"]), "vfov": q["vfov"]}
                           for q in cp.sample_shot(swap_shot(self.shot))]
        except ValueError:
            return
        if self._preview_job is None:
            self._preview_job = self.after(33, self._drag_preview)

    # -------------------------------------------- drawing in the main 3D view
    def draw_in_viewer(self, c):
        """Called by App._paint: path, handles, lights and the current camera frustum."""
        self._handles = []
        if not self.v_path.get() or not self.frames:
            return
        app = self.app
        near = app.near()

        def line(a, b, **kw):
            s = app.seg2d(a, b)
            if s:
                c.create_line(*s[1], **kw)

        def at(p):
            return None if app.cam_d(p) < near else app.project(p)[:2]

        pts = [np.array(f["camera"], float) for f in self.frames]
        for a, b in zip(pts, pts[1:]):
            line(a, b, fill="#ff9f43", width=2)
        for i, s in enumerate(self.shot["segments"]):
            cur = i == self.seg_i
            keys = ("a", "b", "c", "target_a", "target_c") if s["kind"] == "Arc" else ("a", "c", "target_a", "target_c")
            if cur:
                line(s["a"], s["target_a"], fill="#4dd0e1", dash=(2, 4))
                line(s["c"], s["target_c"], fill="#4dd0e1", dash=(2, 4))
                if s["kind"] == "Arc":
                    line(s["a"], s["b"], fill="#ffd43b", dash=(1, 3))
                    line(s["b"], s["c"], fill="#ffd43b", dash=(1, 3))
            for k in keys:
                if not cur and k not in ("a", "c"):
                    continue
                q = at(s[k])
                if q is None:
                    continue
                r = 6 if cur else 4
                col = HANDLE_COL[k]
                if k.startswith("target"):
                    c.create_rectangle(q[0] - r, q[1] - r, q[0] + r, q[1] + r, outline=col, width=2)
                else:
                    c.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r, fill=col if cur else "", outline=col, width=2)
                if cur:
                    c.create_text(q[0] + 9, q[1] - 9, anchor="w", fill=col, font=("Segoe UI", 8),
                                  text=f"{i + 1} {HANDLE_TXT[k]}")
                self._handles.append((q[0], q[1], ("seg", i, k)))
        for i, lt in enumerate(self.shot["lights"]):
            q = at(lt["position"])
            if q is None:
                continue
            col = lt["color"] if app.rgb(lt["color"]) else HANDLE_COL["light"]
            for ang in range(0, 180, 45):
                dx, dy = 9 * math.cos(math.radians(ang)), 9 * math.sin(math.radians(ang))
                c.create_line(q[0] - dx, q[1] - dy, q[0] + dx, q[1] + dy, fill=col, width=2)
            c.create_text(q[0] + 11, q[1] - 9, anchor="w", fill=col, font=("Segoe UI", 8), text=f"light {i + 1}")
            self._handles.append((q[0], q[1], ("light", i, "position")))
        # current frame: camera body, frustum and aim line
        fr = self.frames[self.frame]
        eye, tgt = np.array(fr["camera"], float), np.array(fr["lookat"], float)
        right, up, fwd = basis(eye, tgt, self.shot.get("roll", 0))
        dist = float(np.linalg.norm(tgt - eye))
        size = max(dist * 0.12, 1e-3)
        th = math.tan(math.radians(fr["vfov"]) / 2)
        tw = th * self.aspect()
        corners = [eye + fwd * size + right * sx * tw * size + up * sy * th * size
                   for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for q in corners:
            line(eye, q, fill="#e8e8e8")
        for a, b in zip(corners, corners[1:] + corners[:1]):
            line(a, b, fill="#e8e8e8", width=2)
        line(eye + up * th * size * 1.1 + fwd * size, eye + up * th * size * 1.6 + fwd * size, fill="#e8e8e8", width=2)
        line(eye, tgt, fill="#e8e8e8", dash=(3, 4))
        q = at(eye)
        if q:
            c.create_oval(q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5, outline="#e8e8e8", width=2)
            c.create_text(q[0] + 8, q[1] + 10, anchor="w", fill="#e8e8e8", font=("Segoe UI", 8),
                          text=f"camera  frame {self.frame + 1}")
            self._handles.append((q[0], q[1], ("cam", None, None)))   # last: real handles win ties
        if self._hover is not None:
            hx, hy = self._hover
            c.create_oval(hx - 13, hy - 13, hx + 13, hy + 13, outline="#ffffff", width=1, dash=(2, 2))
        sel = app.selected
        if sel and sel[0] == "d":                       # picked in the tree: yellow ring
            try:
                q = at(self.item_center(sel[1]))
            except (IndexError, ValueError):
                q = None
            if q:
                c.create_oval(q[0] - 11, q[1] - 11, q[0] + 11, q[1] + 11, outline="#ffd75e", width=3)

    def handle_at(self, x, y):
        best = None
        for hx, hy, ref in self._handles:
            d = math.hypot(hx - x, hy - y)
            if d <= 14 and (best is None or d < best[0]):
                best = (d, (hx, hy), ref)
        return best

    def hover(self, x, y):
        """Main-view mouse move: ring + hand cursor over anything draggable."""
        best = self.handle_at(x, y)
        pos = best[1] if best else None
        if pos != self._hover:
            self._hover = pos
            self.app.canvas.configure(cursor="fleur" if pos else "")
            self.app.nav_redraw()

    def grab_handle(self, x, y):
        best = self.handle_at(x, y)
        self._grab = best[2] if best else None
        if self._grab and self._grab[0] == "cam":
            # the camera body: snap to the nearest key pose and drag that camera point
            i, ck, _ak, _fk = self._snap_key()
            self._grab = ("seg", i, ck)
        if self._grab and self._grab[0] == "seg" and self._grab[1] != self.seg_i:
            self.seg_i = self._grab[1]
            self.fill_move()
        return self._grab is not None

    def drag_handle(self, dx, dy, depth):
        """Move the grabbed point with the mouse in the 3D view's screen plane (Shift: toward / away)."""
        if not self._grab:
            return
        kind, i, key = self._grab
        app = self.app
        p = np.array(self.shot["segments"][i][key] if kind == "seg" else self.shot["lights"][i]["position"], float)
        cy, sy = math.cos(app.yaw), math.sin(app.yaw)
        cpi, spi = math.cos(app.pitch), math.sin(app.pitch)
        right = np.array((cy, -sy, 0.0))
        up = np.array((sy * spi, cy * spi, cpi))
        fwd, _lv, _rt = app._cam_axes()
        f = max(app.project(p)[3], 1e-9)
        p = p - fwd * dy / f if depth else p + right * dx / f - up * dy / f
        if kind == "seg":
            self.set_point(i, key, p)
            self.fill_move()
        else:
            self.shot["lights"][i]["position"] = list(p)
            self.fill_light()
        self._live()

    def _drag_preview(self):
        self._preview_job = None
        self.draw_preview()
        self.app.nav_redraw()

    def release_handle(self):
        if self._grab:
            self._grab = None
            self.changed()

    # ------------------------------------------------------------ POV-Ray
    def pov_cam(self, fr):
        eye, tgt = np.array(fr["camera"], float), np.array(fr["lookat"], float)
        _r, up, _f = basis(eye, tgt, self.shot.get("roll", 0))
        asp = self.aspect()
        hang = math.degrees(2 * math.atan(math.tan(math.radians(fr["vfov"]) / 2) * asp))
        return {"eye": eye, "target": tgt, "angle": hang, "aspect": asp, "sky": up}

    def lights_text(self, follow_camera=None):
        if self.shot["lights"]:
            out = []
            for lt in self.shot["lights"]:
                r, g, b = (x * lt["brightness"] for x in cp.rgb(lt["color"]))
                out.append(f"light_source {{ {pov_export.vec(lt['position'])}, color rgb <{r:.4g}, {g:.4g}, {b:.4g}> }}")
            return "\n".join(out) + "\n"
        cam = self.pov_cam(self.frames[0])
        if follow_camera is None:
            return pov_export.default_lights(self.pov_cam(self.frames[self.frame]))
        key = pov_export.default_lights(cam).splitlines()[0]
        return key + f"\nlight_source {{ {follow_camera}, color rgb <0.45, 0.48, 0.55> shadowless }}\n"

    def size(self):
        try:
            w = max(16, int(float(self.v_w.get())))
            h = max(16, int(float(self.v_h.get())))
        except ValueError:
            w, h = 640, 360
        return w, h

    def frame_text(self, fr):
        return pov_export.scene_pov(self.app.pov_items(), self.pov_cam(fr), self.app.rgb,
                                    background=app_bg(), lights=self.lights_text())

    def animation_text(self):
        """One .pov for the whole shot: frame_number picks the camera out of arrays."""
        n = len(self.frames)
        cams = [self.pov_cam(f) for f in self.frames]
        static = pov_export.camera_pov(cams[0])
        text = pov_export.scene_pov(self.app.pov_items(), cams[0], self.app.rgb, background=app_bg(),
                                    lights=self.lights_text(follow_camera="DIR_Camera[DIR_Index]"))
        arr = lambda key: ",\n    ".join(pov_export.vec(c[key]) for c in cams)   # noqa: E731
        fovs = ", ".join(f"{f['vfov']:.6g}" for f in self.frames)
        decl = (f"// Camera Director: {self.shot.get('name', 'shot')}, {n} frames\n"
                f"#declare DIR_Camera = array[{n}] {{\n    {arr('eye')} }};\n"
                f"#declare DIR_Target = array[{n}] {{\n    {arr('target')} }};\n"
                f"#declare DIR_Sky = array[{n}] {{\n    {arr('sky')} }};\n"
                f"#declare DIR_Fov = array[{n}] {{ {fovs} }};\n"
                f"#declare DIR_Index = min({n - 1}, max(0, frame_number - 1));\n"
                "camera {\n    perspective\n    location DIR_Camera[DIR_Index]\n"
                "    right x*image_width/image_height\n    up y\n    sky DIR_Sky[DIR_Index]\n"
                "    angle degrees(2*atan(tan(radians(DIR_Fov[DIR_Index]/2))*image_width/image_height))\n"
                "    look_at DIR_Target[DIR_Index]\n}\n")
        # light lines come before the camera's declarations in scene_pov: move the arrays to the top
        text = text.replace(static, "", 1)
        head, sep, rest = text.partition("global_settings")
        return head + decl + sep + rest

    def write_animation(self):
        os.makedirs(app_pov_dir(), exist_ok=True)
        name = safe_name(self.v_name.get())
        out_dir = os.path.join(app_pov_dir(), "director", name)
        os.makedirs(out_dir, exist_ok=True)
        pov_path = os.path.join(app_pov_dir(), f"director_{name}.pov")
        ini_path = pov_path[:-4] + ".ini"
        w, h = self.size()
        q = ["Quality=5", "Antialias=Off"] if self.v_q.get() == "Draft" else \
            ["Quality=9", "Antialias=On", "Antialias_Threshold=0.2", "Sampling_Method=2", "Antialias_Depth=3"]
        with open(pov_path, "w", encoding="utf-8") as fh:
            fh.write(self.animation_text())
        with open(ini_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join([
                f"Input_File_Name={os.path.basename(pov_path)}",
                f"Output_File_Name=director/{name}/frame_",
                "Output_File_Type=N", f"Width={w}", f"Height={h}", *q,
                "Initial_Frame=1", f"Final_Frame={len(self.frames)}",
                "Initial_Clock=0", "Final_Clock=1", "Display=Off", ""]))
        return pov_path, ini_path, out_dir

    def export_animation(self):
        if not self.resample():
            return
        pov_path, ini_path, _out = self.write_animation()
        self.say(f"Wrote {os.path.basename(pov_path)} + .ini in {app_pov_dir()} - open the .ini in POV-Ray")
        print(f"Director: animation {pov_path}\n          settings  {ini_path}")

    def render_frame(self):
        if self._job:
            self.say("A render is already running", err=True)
            return
        if not self.frames:
            return
        w, h = self.size()
        text = self.frame_text(self.frames[self.frame])
        quality = self.v_q.get().lower()
        result = {}
        self.say(f"Rendering frame {self.frame + 1} at {w}x{h}...")
        self._job = threading.Thread(
            target=lambda: result.update(out=pov_export.render(text, w, h, app_pov_dir(), quality)), daemon=True)
        self._job.start()

        def poll():
            if self._job.is_alive():
                self.after(200, poll)
                return
            self._job = None
            png, log = result.get("out", (None, "render thread failed"))
            if png is None:
                self.say("POV-Ray failed - see the viewer's output pane", err=True)
                print("POV-Ray failed:\n" + log, file=sys.stderr)
                return
            final = os.path.join(app_pov_dir(), "director_frame.png")
            os.replace(png, final)
            self.app.show_render(final)
            self.say(f"Frame {self.frame + 1} rendered -> {final}")
        poll()

    def render_movie(self):
        if self._job:
            self.say("A render is already running", err=True)
            return
        if not self.resample():
            return
        pov_path, ini_path, out_dir = self.write_animation()
        for old in glob.glob(os.path.join(out_dir, "frame_*.png")):
            os.remove(old)
        n = len(self.frames)
        cmd = (["wsl", "--cd", pov_export.wsl_path(app_pov_dir()), "povray", os.path.basename(ini_path)]
               if os.name == "nt" else ["povray", os.path.basename(ini_path)])
        try:
            self._proc = subprocess.Popen(cmd, cwd=app_pov_dir(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            self.say(f"Could not start POV-Ray: {exc}", err=True)
            return
        log = []
        self._job = threading.Thread(target=lambda: log.append(self._proc.communicate()[0]), daemon=True)
        self._job.start()
        print(f"Director: rendering {n} frames -> {out_dir}")
        self.progress.configure(maximum=n, value=0)
        self.say(f"Movie: starting POV-Ray for {n} frames...")
        t0 = time.time()
        shown = [None]

        def poll():
            files = sorted(glob.glob(os.path.join(out_dir, "frame_*.png")))
            alive = self._job.is_alive()
            # while POV runs, the newest file may still be half written: show the one before it
            ready = files if not alive else files[:-1]
            if ready and ready[-1] != shown[0]:
                shown[0] = ready[-1]
                self.show_png(ready[-1], f"rendered frame {len(ready)} / {n}")
            if alive:
                done = len(ready)
                el = time.time() - t0
                eta = f", ~{el / done * (n - done):.0f}s left" if done else ""
                self.say(f"Movie: {done} / {n} frames rendered ({el:.0f}s{eta})  - Stop movie render to cancel")
                self.progress.configure(value=done)
                self.title(f"Camera Director - rendering {done}/{n}")
                self.after(400, poll)
                return
            self._job = None
            self.title("Camera Director - real scene")
            self.progress.configure(value=len(files))
            if not files:
                text = (log[0] if log else b"").decode("utf-8", "replace")
                errs = [ln for ln in text.splitlines() if any(k in ln.lower() for k in ("error", "parse", "fatal"))]
                msg = "\n".join(errs) or text[-800:]
                print("POV-Ray movie failed:\n" + msg, file=sys.stderr)
                self.say("Movie render failed:\n" + (msg[-300:] or "no output from POV-Ray"), err=True)
                return
            gif = self.make_gif(files, out_dir)
            self.app.show_render(files[-1])
            self.say(f"Movie done: {len(files)} frames in {time.time() - t0:.0f}s -> {out_dir}"
                     + (f"\nGIF: {gif}" if gif else ""))
            print(f"Director: {len(files)} frames in {out_dir}" + (f"\n          GIF {gif}" if gif else ""))
        poll()

    def show_png(self, path, caption=""):
        """Put a rendered frame in the preview pane (scaled to fit)."""
        c = self.prev
        cw, ch = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
            im.thumbnail((cw, ch))
            self._png = ImageTk.PhotoImage(im)
        except Exception:                                 # noqa: BLE001 - no PIL / partial file
            try:
                self._png = tk.PhotoImage(file=path)
            except tk.TclError:
                return
        c.delete("all")
        c.create_image(cw / 2, ch / 2, image=self._png)
        if caption:
            c.create_text(8, 8, anchor="nw", fill="#ffd43b", font=("Segoe UI", 9, "bold"), text=caption)

    def stop_movie(self):
        proc = getattr(self, "_proc", None)
        if proc and proc.poll() is None:
            proc.kill()
            if os.name == "nt":                          # povray itself runs inside WSL
                subprocess.run(["wsl", "pkill", "-f", "povray"], capture_output=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.say("Movie render stopped")

    def make_gif(self, files, out_dir):
        try:
            from PIL import Image
        except ImportError:
            return None
        frames = [Image.open(f).convert("RGB") for f in files]
        path = os.path.join(out_dir, safe_name(self.v_name.get()) + ".gif")
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=round(1000 / max(1, self.shot.get("fps", 24))), loop=0)
        return path

    # ---------------------------------------------------------- save / load
    def _named(self):
        self.shot["name"] = self.v_name.get().strip() or "Viewer shot"
        return swap_shot(self.shot)

    def _use(self, pov_shot):
        self.shot = swap_shot(pov_shot)
        self.shot.setdefault("lights", [])
        self.shot.setdefault("roll", 0)
        self.v_name.set(self.shot.get("name", "shot"))
        self.v_fps.set(str(self.shot.get("fps", 24)))
        self.v_roll.set(str(self.shot.get("roll", 0)))
        self.seg_i = self.light_i = self.frame = 0
        self.fill_move()
        self.fill_light()
        self.changed()

    def save_project(self):
        path = filedialog.asksaveasfilename(parent=self, initialdir=app_pov_dir(),
                                            initialfile=safe_name(self.v_name.get()) + ".project.json",
                                            defaultextension=".json", filetypes=[("Director project", "*.json")])
        if path:
            try:
                cp.save_project(path, self._named())
                self.say(f"Saved {path}")
            except ValueError as exc:
                self.say(str(exc), err=True)

    def load_project(self):
        path = filedialog.askopenfilename(parent=self, initialdir=app_pov_dir(),
                                          filetypes=[("Director project", "*.json"), ("All files", "*.*")])
        if path:
            try:
                self._use(cp.load_project(path))
                self.say(f"Loaded {os.path.basename(path)}")
            except (ValueError, KeyError, OSError) as exc:
                self.say(f"Could not load: {exc}", err=True)

    def _refresh_presets(self):
        try:
            self._presets = cp.load_presets(PRESET_FILE)
        except (OSError, ValueError, SyntaxError):
            self._presets = {}
        self.cb_preset.configure(values=sorted(self._presets))

    def save_preset(self):
        try:
            cp.save_preset(PRESET_FILE, self._named())
        except (ValueError, OSError, SyntaxError) as exc:
            self.say(f"Could not save preset: {exc}", err=True)
            return
        self._refresh_presets()
        self.say(f"Saved '{self.shot['name']}' to rayincludes.py")

    def load_preset(self):
        shot = self._presets.get(self.v_preset.get())
        if shot:
            try:
                cp.sample_shot(shot)
                self._use(copy.deepcopy(shot))
            except (ValueError, KeyError) as exc:
                self.say(f"Preset: {exc}", err=True)

    # ---------------------------------------------------------------- close
    def close(self):
        if self.playing:
            self.after_cancel(self.playing)
        self.autosave()
        self.app.director = None
        self.destroy()
        self.app.tree_director()
        self.app.redraw()


def app_pov_dir():
    import viewer3d
    return viewer3d.POV_DIR


def app_bg():
    import viewer3d
    return viewer3d.BG
