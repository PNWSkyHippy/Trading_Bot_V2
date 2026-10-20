"""viewer3d.py - a small tkinter testbed for the class3d library.

Draws Point3d / ColoredPixel / Line3d / Vector3d / Square3d / Cube3d / Sphere3d
objects on a 3d grid, animates rotations in small steps, and keeps the scene in
scene3d.csv (one object row, followed by the transform rows applied to it).

    python viewer3d.py

First run (no scene3d.csv yet): test3d_lib.py is executed, every geometry
object left in its main() is dumped to scene3d.csv.

"Run script..." executes any .py file, shows its print() output in the bottom
pane, and replays every rotation/move the script made, step by step.
"""
import copy
import csv
import json
import math
import os
import queue
import re
import runpy
import shutil
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from class3d import (Point3d, ColoredPixel, Line3d, Vector3d, Square3d,  # noqa: E402
                     Cube3d, Sphere3d, _Geometry3d, _rotation_pivot)
import class3d  # noqa: E402
import pov_export  # noqa: E402
from lathe3d import Lathe3d, LatheTool  # noqa: E402
import solids3d  # noqa: E402  prisms, pyramids, polyhedra, ellipsoid, caps, truncated cone
import ui_scroll  # noqa: E402  scrollable side panels

Plane3d = getattr(class3d, "Plane3d", None)
Circle3d = getattr(class3d, "Circle3d", None)
Cylinder3d = getattr(class3d, "Cylinder3d", None)
Cone3d = getattr(class3d, "Cone3d", None)
ROUND_TYPES = tuple(c for c in (Circle3d, Cylinder3d, Cone3d) if c)   # Circle3d family
CurvedCylinder3d = getattr(class3d, "CurvedCylinder3d", None)
CurvedTorus3d = getattr(class3d, "CurvedTorus3d", None)
TUBE_TYPES = tuple(c for c in (CurvedCylinder3d, CurvedTorus3d) if c)  # bent tubes


def tube_bends(obj):
    """The CurvedCylinder3d pieces of a bend or curved torus, else None."""
    if CurvedTorus3d and isinstance(obj, CurvedTorus3d):
        return obj.get_bends()
    if CurvedCylinder3d and isinstance(obj, CurvedCylinder3d):
        return [obj]
    return None


def is_lib_plane(obj):
    return Plane3d is not None and isinstance(obj, Plane3d)


def is_round(obj):
    return bool(ROUND_TYPES) and isinstance(obj, ROUND_TYPES)

SCENE_FILE = os.path.join(HERE, "scene3d.csv")
DEFAULT_SCRIPT = os.path.join(HERE, "test3d_lib.py")
POV_DIR = os.path.join(HERE, "pov")              # renders, image maps, saved .pov files
POV_FILE = os.path.join(POV_DIR, "scene3d.pov")

# Rotation types are read from the library, so a new  ___rot  method shows up here.
ROT_TYPES = sorted((n for n in dir(_Geometry3d)
                    if n.endswith("rot") and callable(getattr(_Geometry3d, n))),
                   key=lambda n: (n == "vecrot", n))
KINDS = ("point3d", "line3d", "vector3d", "plane3d", "square3d", "cube3d", "sphere3d",
         "circle3d", "cylinder3d", "cone3d", "curvedcylinder3d", "curvedtorus3d", "lathe3d") + solids3d.KINDS
ALIASES = {"rotatex": "xrot", "rotatey": "yrot", "rotatez": "zrot",
           "rotatevec": "vecrot", "rotate": "vecrot", "translate": "move"}
GEOM_TYPES = (Point3d, Line3d, Square3d, Cube3d, Sphere3d) + ((Plane3d,) if Plane3d else ()) + ROUND_TYPES + TUBE_TYPES + (Lathe3d,) + solids3d.TYPES
WORLD_AXIS = {"xrot": (1, 0, 0), "yrot": (0, 1, 0), "zrot": (0, 0, 1)}

BG = "#1b1d22"
DEFAULT_LINE = "#c8ccd4"
DEFAULT_POINT = "#ffd54f"
FILL_ALPHA = 0.30

# NOTE: OpOverloaded makes every Point3d compare equal (==) and be falsy, so this
# file never uses  `if obj`,  `obj in list`  or  list.remove(obj)  - identity only.


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def xyz(p):
    return tuple(float(c) for c in p.get_xyz())


def fmt(v):
    s = f"{float(v):.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def num(v):
    """Number -> short CSV text."""
    s = f"{float(v):.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def chunks3(nums):
    return [tuple(nums[i:i + 3]) for i in range(0, len(nums) - 2, 3)]


def square_corners(sq):
    return [xyz(line.get_start()) for line in (sq._line1, sq._line2, sq._line3, sq._line4)]


def square_edges(sq):
    return [(xyz(line.get_start()), xyz(line.get_end()))
            for line in (sq._line1, sq._line2, sq._line3, sq._line4)]


def cube_faces(cube):
    return (cube._square1, cube._square2, cube._square3,
            cube._square4, cube._square5, cube._square6)


def points_of(obj):
    """Actual Point3d objects (unique) that make up obj."""
    if isinstance(obj, Point3d):
        return [obj]
    if isinstance(obj, Sphere3d):
        return [obj.get_center()]
    if is_lib_plane(obj):
        return [obj.get_vec1().get_start()]
    if is_round(obj) and not hasattr(obj, "_points"):
        return [obj.get_center()]
    return list({id(p): p for p in obj._points()}.values())


def center_of(obj):
    if isinstance(obj, Point3d):
        return xyz(obj)
    if is_lib_plane(obj):
        return xyz(obj.get_vec1().get_start())
    return xyz(obj.get_center())


def lib_plane_normal(obj):
    n = obj.get_norm()
    return tuple(float(c) for c in (xyz(n) if isinstance(n, Point3d) else n))


def round_geom(obj):
    """(center, unit normal, radius, height or None) of a Circle3d-family object,
    read through the library's own getters."""
    ctr = np.array(xyz(obj.get_center()), float)
    n = obj.get_norm()
    n = np.array(xyz(n) if isinstance(n, Point3d) else n, float)
    if not np.all(np.isfinite(n)) or np.linalg.norm(n) == 0:
        raise ValueError(f"get_norm() returned {n} - see get_perpendicular_vectors")
    n /= np.linalg.norm(n)
    h = float(obj.get_height()) if hasattr(obj, "get_height") else None
    return ctr, n, float(obj.get_radius()), h


def ring(ctr, n, r, k=48):
    """k+1 points around a circle (closed)."""
    u = np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0))
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return [ctr + r * (math.cos(2 * math.pi * i / k) * u + math.sin(2 * math.pi * i / k) * v)
            for i in range(k + 1)]


def color_of(obj):
    """(line/border color, fill color) as stored on the object."""
    if solids3d.is_solid(obj):
        return solids3d.colors(obj)
    if is_lib_plane(obj):
        return None, obj.get_color()
    if isinstance(obj, (Cube3d, Square3d, Lathe3d) + TUBE_TYPES) or is_round(obj):
        return obj.get_bc(), obj.get_fc()
    if isinstance(obj, (Line3d, Sphere3d, ColoredPixel)):
        return obj.get_color(), None
    return None, None


def call(obj, method, *args):
    """Call a library transform. Sphere3d has no _points(), so its center moves."""
    target = obj.get_center() if isinstance(obj, Sphere3d) else obj
    return getattr(target, method)(*args)


def scale_obj(obj, factor):
    if isinstance(obj, Sphere3d):
        obj.get_center().__imul__(factor)
        obj.set_static_radius(obj.get_radius() * factor)
    elif isinstance(obj, Point3d):
        obj.__imul__(factor)
    else:
        obj.scale(factor)


# ----------------------------------------------------------------------------
# transforms  (tf dict  <->  CSV row)
# ----------------------------------------------------------------------------
def _pivot_from(fields):
    if not fields or fields[0].lower() in ("", "default", "none"):
        return None
    mode = fields[0].lower()
    if mode == "center":
        return "center"
    if mode == "origin":
        return (0.0, 0.0, 0.0)
    if mode == "point":
        fields = fields[1:]
    return tuple(float(v) for v in fields[:3])


def _pivot_fields(pivot):
    if pivot is None:
        return ["default"]
    if isinstance(pivot, str):
        return [pivot]
    return ["point"] + [num(v) for v in pivot]


def parse_row(row):
    op = ALIASES.get(row[0].lower(), row[0].lower())
    if op == "move":
        return {"op": "move", "d": tuple(float(v) for v in row[1:4])}
    if op == "scale":
        return {"op": "scale", "f": float(row[1]), "pivot": _pivot_from(row[2:])}
    if op == "vecrot":
        vals = [float(v) for v in row[2:8]]
        return {"op": "vecrot", "deg": float(row[1]), "axis": (tuple(vals[:3]), tuple(vals[3:])),
                "pivot": _pivot_from(row[8:])}
    if op.endswith("rot"):
        return {"op": op, "deg": float(row[1]), "pivot": _pivot_from(row[2:])}
    raise ValueError(f"unknown transform '{row[0]}'")


def tf_to_row(tf):
    op = tf["op"]
    if op == "move":
        return ["move"] + [num(v) for v in tf["d"]]
    if op == "scale":
        piv = tf.get("pivot")
        return ["scale", num(tf["f"])] + (_pivot_fields(piv) if isinstance(piv, tuple) else [])
    if op == "vecrot":
        a, b = tf["axis"]
        return ["vecrot", num(tf["deg"])] + [num(v) for v in a + b] + _pivot_fields(tf["pivot"])
    return [op, num(tf["deg"])] + _pivot_fields(tf["pivot"])


def tf_text(tf):
    op = tf["op"]
    if op == "move":
        return "move(" + ", ".join(fmt(v) for v in tf["d"]) + ")"
    if op == "scale":
        piv = tf.get("pivot")
        return f"scale({fmt(tf['f'])})" + (
            " about (" + ", ".join(fmt(v) for v in piv) + ")" if isinstance(piv, tuple) else "")
    piv = tf["pivot"]
    piv = "default" if piv is None else piv if isinstance(piv, str) else \
        "(" + ", ".join(fmt(v) for v in piv) + ")"
    if op == "vecrot":
        a, b = tf["axis"]
        return (f"vecrot({fmt(tf['deg'])} deg, axis ({', '.join(fmt(v) for v in a)})->"
                f"({', '.join(fmt(v) for v in b)}), pivot={piv})")
    return f"{op}({fmt(tf['deg'])} deg, pivot={piv})"


def run_tf(obj, tf, frac=1.0):
    """Apply frac of a transform through the library's own methods."""
    op = tf["op"]
    if op == "move":
        call(obj, "move", *(d * frac for d in tf["d"]))
    elif op == "scale":
        piv = tf.get("pivot")
        if isinstance(piv, tuple):            # scale about a fixed point (group center)
            call(obj, "move", *(-v for v in piv))
            scale_obj(obj, tf["f"] ** frac)
            call(obj, "move", *piv)
        else:                                 # library default: about the origin
            scale_obj(obj, tf["f"] ** frac)
    elif op == "vecrot":
        call(obj, "vecrot", Line3d(*tf["axis"]), math.radians(tf["deg"]) * frac, tf["pivot"])
    else:
        call(obj, op, math.radians(tf["deg"]) * frac, tf["pivot"])


def pivot_point(obj, tf):
    """World position of the pivot a transform turns around."""
    piv = tf.get("pivot")
    if piv is None:
        return tf["axis"][0] if tf["op"] == "vecrot" else (0.0, 0.0, 0.0)
    if isinstance(piv, str):
        return center_of(obj)
    return tuple(piv)


_BEND_CACHE = {}


def _bend_samples(b):
    """b.surface_point(t/4, f*pi/2) for t 0..4, f 0..3 - the same sum, but the bend's frame worked
    out once, and remembered by its four points + angle (hundreds of bends made every refresh,
    save and grid update take seconds)."""
    try:
        c, s, e, nt = (tuple(float(v) for v in p.get_xyz()) for p in b._points())
        key = (c, s, e, nt, b.get_angle())
    except Exception:                         # noqa: BLE001 - not the bend we know: ask it
        return [xyz(b.surface_point(t / 4, f * math.pi / 2)) for t in range(5) for f in range(4)]
    hit = _BEND_CACHE.get(key)
    if hit is None:
        c, s, e, nt = (np.array(p) for p in (c, s, e, nt))
        e1 = s - c
        R = float(np.linalg.norm(e1))
        e1 = e1 / R
        n = (nt - c) / np.linalg.norm(nt - c)
        e2 = np.cross(n, e1)
        r = float(np.linalg.norm(e - s))
        hit = []
        for t in range(5):
            th = t / 4 * key[4]
            rd = math.cos(th) * e1 + math.sin(th) * e2
            hit += [tuple(float(v) for v in c + (R + r * math.cos(f * math.pi / 2)) * rd
                          + r * math.sin(f * math.pi / 2) * n) for f in range(4)]
        if len(_BEND_CACHE) > 50000:
            _BEND_CACHE.clear()
        _BEND_CACHE[key] = hit
    return list(hit)


_SP_MEMO = None                               # {id(obj): (obj, points)} while nothing can move (update_grid)


def sample_points(obj):
    """A handful of points spanning obj (fit view, grid size, twin extents)."""
    if _SP_MEMO is None:
        return _sample_points(obj)
    hit = _SP_MEMO.get(id(obj))
    if hit is None or hit[0] is not obj:
        hit = _SP_MEMO[id(obj)] = (obj, _sample_points(obj))
    return list(hit[1])


def _sample_points(obj):
    pts = []
    if isinstance(obj, Sphere3d):
        c, r = center_of(obj), obj.get_radius()
        pts += [tuple(np.add(c, s * r * np.eye(3)[i])) for i in range(3) for s in (-1, 1)]
    elif solids3d.is_solid(obj):
        pts += [tuple(q) for q in solids3d.mesh(obj, 12)[0]]
    elif isinstance(obj, Lathe3d):
        pts += [tuple(q) for q in obj.mesh()[0].reshape(-1, 3)]
    elif tube_bends(obj) is not None:
        for b in tube_bends(obj):
            pts += _bend_samples(b)
    elif is_round(obj):
        ctr, n, r, h = round_geom(obj)
        pts += [tuple(q) for q in ring(ctr, n, r, 8)]
        if h:
            pts.append(tuple(ctr + n * h))
    else:
        pts += [xyz(p) for p in points_of(obj)]
    return pts


TWIN_AXES = {"own": None, "Z": 2, "X": 0, "Y": 1}
CSG_OPS = ("none", "combine", "cut", "overlap")


def own_axis(obj):
    """The object's own normal (cones/cylinders/circles), else None."""
    if is_round(obj) and not solids3d.is_solid(obj):
        return np.array(round_geom(obj)[1], float)
    return None


def twin_turn(obj, axis, lift=None, n=None):
    """180 deg turn that mirrors obj end for end along an axis ("own" = the object's
    own normal for cones/cylinders/circles, else Z; n = that normal taken before a flip,
    so "below" stays on the same side).
    lift None: about its own middle (flip in place).  lift = % of its height: the turned
    copy lands below, overlapping by (100 - lift) % - 100 just touching, 50 half way in."""
    pts = np.array(sample_points(obj), float)
    if n is None and axis == "own":
        n = own_axis(obj)
    if axis == "own" and n is not None:
        n = np.array(n, float)
        n /= np.linalg.norm(n)
        t = pts @ n
        h = t.max() - t.min()
        s = t.min() + (h / 2 if lift is None else h * (1 - lift / 100) / 2)
        mid = (pts.min(axis=0) + pts.max(axis=0)) / 2
        piv = mid + n * (s - mid @ n)
        u = np.cross(n, np.eye(3)[int(np.argmin(np.abs(n)))])   # any axis square to n
        u /= np.linalg.norm(u)
        piv = tuple(float(v) for v in piv)
        return {"op": "vecrot", "deg": 180.0,
                "axis": (piv, tuple(float(v) for v in np.add(piv, u))), "pivot": piv}
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    k = TWIN_AXES.get(axis) if TWIN_AXES.get(axis) is not None else 2
    piv = (lo + hi) / 2
    h = hi[k] - lo[k]
    piv[k] = lo[k] + (h / 2 if lift is None else h * (1 - lift / 100) / 2)
    return {"op": "xrot" if k == 2 else "zrot", "deg": 180.0,
            "pivot": tuple(float(v) for v in piv)}


HOLLOW_OPEN = ("none", "top", "bottom", "both")
ALIGN_AXES = ("X", "Y", "Z", "XY", "XZ", "YZ", "XYZ")
ALIGN_HOW = ("center", "low sides", "high sides", "stack on")
_PRISMY = ("prism3d", "truncatedprism3d", "pyramid3d", "truncatedcone3d")


def _frame(n, u=None):
    """Orthonormal columns (a1, a2, a3) with a3 along n, a1 as close to u as it can be."""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    u = np.eye(3)[int(np.argmin(np.abs(n)))] if u is None else np.asarray(u, float)
    u = u - (u @ n) * n
    if np.linalg.norm(u) < 1e-9:
        u = np.eye(3)[int(np.argmin(np.abs(n)))]
        u = u - (u @ n) * n
    u /= np.linalg.norm(u)
    return np.column_stack([u, np.cross(n, u), n])


def hollow_inner(obj, t, opening="none"):
    """The inner copy a hollow object has cut out of it: every wall pulled in by t.
    Boxes, cylinders and spheres get even walls; cones, prisms and lathes shrink toward
    their axis (thinner where narrow).  opening: which end the inner copy pokes out of
    (top = along the object's own axis)."""
    k_name = solids3d.kind_of(obj) if solids3d.is_solid(obj) else None
    nums = solids3d.to_nums(obj) if k_name else None
    radial = True                              # same shrink both ways across the axis
    if k_name in _PRISMY:
        F = _frame(np.subtract(nums[6:9], nums[0:3]), np.subtract(nums[3:6], nums[0:3]))
    elif k_name == "ellipsoid3d":
        F, radial = _frame(np.subtract(nums[9:12], nums[0:3]), np.subtract(nums[3:6], nums[0:3])), False
    elif k_name in solids3d.POLY:
        F = _frame(np.cross(nums[4:7], nums[7:10]), nums[4:7])
    elif k_name:
        raise TypeError(f"hollow isn't supported for {k_name} yet")
    elif isinstance(obj, Lathe3d):
        _b, an, u, _v, _s = obj.frame()
        F = _frame(an, u)
    elif tube_bends(obj) is not None or is_lib_plane(obj) or getattr(obj, "_viewer_plane", False):
        raise TypeError("hollow works on solids (box, cylinder, cone, sphere, lathe, prism...)")
    elif is_round(obj):
        ctr, n, _r, h = round_geom(obj)
        if not h:
            raise TypeError("a flat circle has no inside")
        F = _frame(n, np.subtract(xyz(obj.get_vec1().get_end()), ctr))
    elif isinstance(obj, Cube3d):
        base, top = square_corners(obj._square1), square_corners(obj._square2)
        F = _frame(np.subtract(np.mean(top, 0), np.mean(base, 0)), np.subtract(base[1], base[0]))
        radial = False
    elif isinstance(obj, Sphere3d):
        F, radial = np.eye(3), False
    else:
        raise TypeError(f"hollow isn't supported for {type(obj).__name__}")
    s = np.array(sample_points(obj), float) @ F          # coordinates along a1, a2, a3
    lo, hi = s.min(0), s.max(0)
    span = hi - lo
    if np.any(span[:2] <= 2 * t) or span[2] <= (2 * t if opening != "both" else 0):
        raise ValueError(f"walls of {num(t)} leave no room inside (size {', '.join(fmt(v) for v in span)})")
    new_lo, new_hi = lo + t, hi - t
    if opening in ("top", "both"):
        new_hi[2] = hi[2] + t                  # pokes out the end: open
    if opening in ("bottom", "both"):
        new_lo[2] = lo[2] - t
    k = (new_hi - new_lo) / span
    if radial:
        k[0] = k[1] = min(k[0], k[1])
        mid = (lo + hi) / 2
        new_lo[:2] = mid[:2] - k[:2] * span[:2] / 2
    shift = F @ (new_lo - k * lo)
    A = F @ np.diag(k) @ F.T

    def m(p):                                  # world point -> inner copy
        return tuple(float(v) for v in A @ np.asarray(p, float) + shift)

    c1, c2 = (str(c) if c else "" for c in color_of(obj))
    name = getattr(obj, "_name", "") or "inner"
    if k_name in _PRISMY:
        return solids3d.build(k_name, list(m(nums[0:3])) + list(m(nums[3:6])) + list(m(nums[6:9]))
                              + nums[9:], c1, c2, name)
    if k_name == "ellipsoid3d":
        return solids3d.build(k_name, [v for i in (0, 3, 6, 9) for v in m(nums[i:i + 3])], c1, c2, name)
    if k_name in solids3d.POLY:                # can't stretch: shrink evenly to fit
        return solids3d.build(k_name, list(m(nums[0:3])) + [nums[3] * float(k.min())] + nums[4:], c1, c2, name)
    if isinstance(obj, Lathe3d):
        n2 = list(obj.to_nums())
        n2[0:3] = m(n2[0:3])
        n2[3:6] = [v * k[2] for v in n2[3:6]]
        n2[12::2] = [r * k[0] / k[2] for r in n2[12::2]]   # profile radii are in axis-length units
        return Lathe3d.from_nums(n2, bc=c1 or None, fc=c2 or None, name=name)
    if is_round(obj):
        ctr, n, r, h = round_geom(obj)
        edge = xyz(obj.get_vec1().get_end())
        e2 = Entry("cone3d" if Cone3d and isinstance(obj, Cone3d) else "cylinder3d", name, c1, c2,
                   list(m(ctr)) + list(m(edge)) + [h * k[2]] + list(n))
        return build(e2)
    if isinstance(obj, Cube3d):
        pts = square_corners(obj._square1) + square_corners(obj._square2)
        return make_cube(name, [m(p) for p in pts], c1 or None, c2 or None)
    c = center_of(obj)                         # sphere -> ellipsoid (open end stretches it)
    r = obj.get_radius()
    return solids3d.build("ellipsoid3d", list(m(c)) + [v for i in range(3) for v in
                                                       m(np.add(c, r * np.eye(3)[i]))], c1, c2, name)


def entry_center(e):
    """Object center; for a twin pair the middle of the two."""
    if e.twin_obj is None:
        return center_of(e.obj)
    return tuple(float(v) for v in (np.add(center_of(e.obj), center_of(e.twin_obj)) / 2))


def gsegs(e):
    """Group path as a list, outermost first: 'row/pawn_2' -> ['row', 'pawn_2']."""
    return [s for s in e.group.split("/") if s] if e.group else []


def bbox(es):
    """(low corner, high corner) around the entries' objects and twins."""
    pts = [p for e in es for o in (e.obj, e.twin_obj) if o is not None for p in sample_points(o)]
    arr = np.array(pts, float) if pts else np.zeros((1, 3))
    return arr.min(axis=0), arr.max(axis=0)


# ----------------------------------------------------------------------------
# scene entries  (one CSV object row + its transform rows)
# ----------------------------------------------------------------------------
class Entry:
    def __init__(self, kind, name, c1="", c2="", nums=(), transforms=None):
        self.kind = kind
        self.name = name
        self.c1 = c1 or ""
        self.c2 = c2 or ""
        self.nums = [float(v) for v in nums]
        self.transforms = transforms or []   # list of CSV rows
        self.mat, self.mat_scale = "", 1.0   # POV-Ray material spec (see pov_export.material)
        self.group = ""                      # ObjGroup3d name this object is tagged into
        self.twin = None                     # (lift %, axis Z|X|Y, flip first) - see twin_turn
        self.csg = None                      # (combine|cut|overlap, target name or @group, whole group is tool)
        self.hollow = None                   # (wall thickness, open end none|top|bottom|both)
        self.obj = None
        self.twin_obj = None

    def row(self):
        return [self.kind, self.name, self.c1, self.c2] + [num(v) for v in self.nums]


def make_square(corners, bc=None, fc=None):
    lines = [Line3d(tuple(corners[i]), tuple(corners[(i + 1) % 4])) for i in range(4)]
    return Square3d(*lines, bc=bc, fc=fc)


def plane_corners(p, n, size):
    p, n = np.array(p, float), np.array(n, float)
    if np.linalg.norm(n) == 0:
        raise ValueError("Plane normal cannot be zero.")
    n /= np.linalg.norm(n)
    helper = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, helper)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    h = size / 2
    return [tuple(p + su * h * u + sv * h * v) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def make_cube(name, pts, bc=None, fc=None):
    """Rebuild from 4 base + 4 top corners. Prefers Cube3d(base, height)."""
    base, top = pts[:4], pts[4:8]
    c0 = np.array(base[0], float)
    normal = np.cross(np.array(base[1]) - c0, np.array(base[3]) - c0)
    if np.linalg.norm(normal) > 0:
        normal /= np.linalg.norm(normal)
        if normal[np.argmax(np.abs(normal))] < 0:   # same sign rule as Cube3d._from_base
            normal = -normal
        height = float(np.dot(np.array(top[0]) - c0, normal))
        try:
            cube = Cube3d(make_square(base, bc, fc), height, name=name, bc=bc, fc=fc)
            if np.allclose(square_corners(cube._square2), top, atol=1e-6):
                return cube
        except (ValueError, TypeError):
            pass
    # Not a clean box (e.g. one face rotated on its own): use the six-face form.
    faces = [make_square(base, bc, fc), make_square(top, bc, fc)]
    faces += [make_square([base[i], base[(i + 1) % 4], top[(i + 1) % 4], top[i]], bc, fc)
              for i in range(4)]
    return Cube3d(*faces, name=name, bc=bc, fc=fc)


def build(e):
    n, c1, c2 = e.nums, e.c1 or None, e.c2 or None
    if e.kind in solids3d.KINDS:
        return solids3d.build(e.kind, n, c1, c2, e.name)
    if e.kind == "point3d":
        return ColoredPixel(*n[:3], c1) if c1 else Point3d(*n[:3])
    if e.kind == "line3d":
        return Line3d(tuple(n[0:3]), tuple(n[3:6]), color=c1)
    if e.kind == "vector3d":
        vec = Vector3d(Point3d(*n[0:3]), Point3d(*n[3:6]))
        vec.set_color(c1)
        return vec
    if e.kind == "square3d":
        return make_square(chunks3(n[:12]), c1, c2)
    if e.kind == "plane3d":
        sq = make_square(plane_corners(n[0:3], n[3:6], n[6]), c1, c2)
        sq._viewer_plane = True        # carrier square; drawn as an infinite plane
        return sq
    if e.kind == "cube3d":
        return make_cube(e.name, chunks3(n[:24]), c1, c2)
    if e.kind == "sphere3d":
        return Sphere3d(Point3d(*n[0:3]), n[3], name=e.name, color=c1)
    if e.kind in ("circle3d", "cylinder3d", "cone3d"):
        cls = {"circle3d": Circle3d, "cylinder3d": Cylinder3d, "cone3d": Cone3d}[e.kind]
        if cls is None:
            raise ValueError(f"class3d has no {e.kind[:-2].title()}3d")
        args = (Point3d(*n[0:3]), Point3d(*n[3:6])) + ((n[6],) if e.kind != "circle3d" else ())
        k = 6 if e.kind == "circle3d" else 7   # optional normal follows the numbers above
        normal = tuple(n[k:k + 3]) if len(n) >= k + 3 else None
        return cls(*args, bc=c1, fc=c2, normal=normal)
    if e.kind in ("curvedcylinder3d", "curvedtorus3d"):
        cls = CurvedCylinder3d if e.kind == "curvedcylinder3d" else CurvedTorus3d
        if cls is None:
            raise ValueError(f"class3d has no {e.kind}")
        normal = tuple(n[8:11]) if len(n) >= 11 else None
        third = math.radians(n[7]) if cls is CurvedCylinder3d else int(round(n[7]))
        return cls(Point3d(*n[0:3]), Point3d(*n[3:6]), n[6], third, bc=c1, fc=c2,
                   name=e.name, normal=normal)
    if e.kind == "lathe3d":
        return Lathe3d.from_nums(n, bc=c1, fc=c2, name=e.name)
    raise ValueError(f"unknown kind {e.kind}")


def entry_from_obj(name, obj):
    """Snapshot a live library object as a scene entry (current geometry)."""
    c1, c2 = (str(c) if c else "" for c in color_of(obj))
    if solids3d.is_solid(obj):         # before is_round: TruncatedCone3d is a Cylinder3d
        return Entry(solids3d.kind_of(obj), name, c1, c2, solids3d.to_nums(obj))
    if is_lib_plane(obj):
        return Entry("plane3d", name, c2, c2, list(center_of(obj)) + list(lib_plane_normal(obj)) + [10.0])
    if is_round(obj):                  # center, edge point (vec1's end), height
        kind = ("cone3d" if Cone3d and isinstance(obj, Cone3d) else
                "cylinder3d" if Cylinder3d and isinstance(obj, Cylinder3d) else "circle3d")
        nums = list(xyz(obj.get_center())) + list(xyz(obj.get_vec1().get_end()))
        nums += [obj.get_height()] if kind != "circle3d" else []
        return Entry(kind, name, c1, c2, nums + [float(v) for v in round_geom(obj)[1]])
    if tube_bends(obj) is not None:    # bend center/start, tube r, angle deg or segments, normal
        first = tube_bends(obj)[0]
        torus = CurvedTorus3d is not None and isinstance(obj, CurvedTorus3d)
        nums = (list(xyz(first.get_bend_center())) + list(xyz(first.get_spine_start()))
                + [first.get_tube_radius(),
                   len(obj.get_bends()) if torus else math.degrees(first.get_angle())]
                + [float(v) for v in first.get_norm()])
        return Entry("curvedtorus3d" if torus else "curvedcylinder3d", name, c1, c2, nums)
    if isinstance(obj, Lathe3d):
        return Entry("lathe3d", name, c1, c2, obj.to_nums())
    if isinstance(obj, Sphere3d):
        return Entry("sphere3d", name, c1, "", list(center_of(obj)) + [obj.get_radius()])
    if isinstance(obj, Cube3d):
        pts = square_corners(obj._square1) + square_corners(obj._square2)
        return Entry("cube3d", name, c1, c2, [v for p in pts for v in p])
    if isinstance(obj, Square3d):
        return Entry("square3d", name, c1, c2, [v for p in square_corners(obj) for v in p])
    if isinstance(obj, Vector3d):
        return Entry("vector3d", name, c1, "", xyz(obj.get_start()) + xyz(obj.get_end()))
    if isinstance(obj, Line3d):
        return Entry("line3d", name, c1, "", xyz(obj.get_start()) + xyz(obj.get_end()))
    if isinstance(obj, Point3d):
        return Entry("point3d", name, c1, "", xyz(obj))
    raise TypeError(type(obj).__name__)


def load_scene(path):
    entries = []
    with open(path, newline="") as f:
        for lineno, row in enumerate(csv.reader(f), 1):
            row = [c.strip() for c in row]
            while row and row[-1] == "":
                row.pop()
            if not row or row[0].startswith("#"):
                continue
            kind = row[0].lower()
            try:
                if kind in KINDS:
                    try:                       # short form:  point3d,5,6,7
                        float(row[1])
                        e = Entry(kind, f"{kind[:-2]}{len(entries) + 1}", "", "", row[1:])
                    except ValueError:
                        e = Entry(kind, row[1], row[2] if len(row) > 2 else "",
                                  row[3] if len(row) > 3 else "", [v for v in row[4:] if v])
                    entries.append(e)
                elif entries and kind == "pov":   # pov,<material spec>,<texture scale>
                    entries[-1].mat = row[1] if len(row) > 1 else ""
                    entries[-1].mat_scale = float(row[2]) if len(row) > 2 else 1.0
                elif entries and kind == "group":  # group,<name>
                    entries[-1].group = row[1] if len(row) > 1 else ""
                elif entries and kind == "twin":   # twin,<lift %>,<axis>,<flip first 0|1>
                    axis = row[2].strip() if len(row) > 2 else "Z"
                    axis = "own" if axis.lower() == "own" else axis.upper()
                    entries[-1].twin = (float(row[1]) if len(row) > 1 else 100.0,
                                        axis if axis in TWIN_AXES else "Z",
                                        len(row) > 3 and row[3] not in ("", "0"))
                elif entries and kind == "csg":    # csg,<combine|cut|overlap>,<target|@group>[,group]
                    g = row[3] if len(row) > 3 else ""   # group:<name>, or old plain 'group'
                    g = g[6:] if g.lower().startswith("group:") else \
                        (gsegs(entries[-1])[-1:] or [""])[0] if g.lower() == "group" else ""
                    entries[-1].csg = (row[1].lower(), row[2], g)
                elif entries and kind == "hollow":  # hollow,<wall thickness>,<none|top|bottom|both>
                    opening = row[2].lower() if len(row) > 2 else "none"
                    entries[-1].hollow = (float(row[1]), opening if opening in HOLLOW_OPEN else "none")
                elif entries:
                    parse_row(row)             # validate now, report the line number
                    entries[-1].transforms.append(row)
                else:
                    print(f"{os.path.basename(path)} line {lineno}: transform before any object, skipped")
            except (ValueError, IndexError) as exc:
                print(f"{os.path.basename(path)} line {lineno}: {exc} - skipped: {','.join(row)}")
    return entries


def save_scene(path, entries):
    with open(path, "w", newline="") as f:
        f.write("# viewer3d scene. Object rows: kind,name,color,fill,numbers...\n"
                "#   point3d x,y,z | line3d/vector3d x1,y1,z1,x2,y2,z2 | square3d 4 corners\n"
                "#   plane3d px,py,pz,nx,ny,nz,size | cube3d 4 base + 4 top corners | sphere3d cx,cy,cz,r\n"
                "#   circle3d cx,cy,cz,ex,ey,ez (center, edge point) | cylinder3d/cone3d same + height\n"
                "#     (both may end with an optional normal x,y,z)\n"
                "#   curvedcylinder3d bend cx,cy,cz, spine start x,y,z, tube r, angle deg, normal x,y,z\n"
                "#   curvedtorus3d cx,cy,cz, ring point x,y,z, tube r, segments, normal x,y,z\n"
                "#   lathe3d base x,y,z, axis x,y,z (length = size), zero-angle dir x,y,z, segments,\n"
                "#     sweep deg, flags (1 curved, 2 faceted), profile r1,h1,r2,h2,...\n"
                "#   prism3d/pyramid3d base center, base corner, top center (apex), sides\n"
                "#   truncatedprism3d same + top scale | truncatedcone3d base center, edge point, top center, top scale\n"
                "#   ellipsoid3d center, x tip, y tip, z tip | sphericalcap3d center, pole, cap height | hemisphere3d center, pole\n"
                "#   octahedron3d/dodecahedron3d/icosahedron3d/rhombicdodecahedron3d center, edge, x dir, y dir\n"
                "# Transform rows follow their object (degrees):\n"
                "#   xrot|yrot|zrot,deg,pivot   vecrot,deg,ax,ay,az,bx,by,bz,pivot   move,dx,dy,dz   scale,f\n"
                "#   pivot = default | center | origin | point,x,y,z\n"
                "#   (saved as a snapshot: each object's steps are merged into scale, vecrot, move)\n"
                "# pov,<material>,<texture scale> after an object row sets its POV-Ray material\n"
                "# group,<name> after an object row tags it into that group (moves/rotates as one);\n"
                "#   nested groups are a path, outermost first: group,row/pawn_2\n"
                "# twin,<lift %>,<own|Z|X|Y>,<flip first 0|1> adds a 180 deg turned copy below, merged into one\n"
                "# csg,<combine|cut|overlap>,<target name or @group>[,group:<name>]: this object (or with\n"
                "#   group:<name> that whole group) merges with / cuts / intersects the target\n"
                "# hollow,<wall thickness>,<none|top|bottom|both>: cut out an inner copy, walls that thick\n")
        w = csv.writer(f)
        for e in entries:
            w.writerow(e.row())
            if e.mat:
                w.writerow(["pov", e.mat, num(e.mat_scale)])
            if e.group:
                w.writerow(["group", e.group])
            if e.twin:
                w.writerow(["twin", num(e.twin[0]), e.twin[1], int(e.twin[2])])
            if e.csg:
                w.writerow(["csg", e.csg[0], e.csg[1]] + ([f"group:{e.csg[2]}"] if len(e.csg) > 2 and e.csg[2] else []))
            if e.hollow:
                w.writerow(["hollow", num(e.hollow[0]), e.hollow[1]])
            for t in snapshot_rows(e):
                w.writerow(t)


# ----------------------------------------------------------------------------
# save snapshot: an object's whole list of steps -> at most scale, one turn, move
# (the full list stays in memory for Undo; only the file gets the short form)
# ----------------------------------------------------------------------------
_SNAP_CACHE = {}


def _n12(v):
    s = f"{float(v):.12g}"
    return "0" if s in ("-0", "") else s


def _net_steps(e):
    """Replay e's steps on 4 probe points -> (f, R, t) with  x -> f*R*x + t."""
    obj = build(e)
    if e.twin and e.twin[2]:                  # same pre-flip as rebuild()
        run_tf(obj, twin_turn(obj, e.twin[1]), 1.0)
    probes = [Point3d(0.0, 0.0, 0.0), Point3d(1.0, 0.0, 0.0),
              Point3d(0.0, 1.0, 0.0), Point3d(0.0, 0.0, 1.0)]
    for row in e.transforms:
        tf = parse_row(row)
        if tf["op"] != "move" and tf.get("pivot") == "center":
            owner = obj.get_center() if isinstance(obj, Sphere3d) else obj
            tf = dict(tf, pivot=_rotation_pivot("center", owner))
        for p in probes:
            run_tf(p, tf, 1.0)
        run_tf(obj, tf, 1.0)
    P = np.array([xyz(p) for p in probes], float)
    M = (P[1:] - P[0]).T                      # columns = images of the unit axes
    det = np.linalg.det(M)
    if det <= 0:
        return None
    f = det ** (1 / 3)
    return f, M / f, P[0]


def _turn_row(R):
    """Rotation matrix -> vecrot row about an axis through the origin (or None)."""
    sk = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    ang = math.atan2(np.linalg.norm(sk) / 2, (np.trace(R) - 1) / 2)   # exact near 0 and 180
    if ang < 1e-10:
        return None
    w, v = np.linalg.eig(R)                   # axis = the direction R leaves alone
    ax = np.real(v[:, int(np.argmin(np.abs(w - 1)))])
    ax /= np.linalg.norm(ax)
    q = np.eye(3)[int(np.argmin(np.abs(ax)))]          # a test direction off the axis
    for deg in (math.degrees(ang), -math.degrees(ang)):   # pick the library's turn direction
        row = ["vecrot", _n12(deg), "0", "0", "0"] + [_n12(v) for v in ax] + ["default"]
        p = Point3d(*q)
        run_tf(p, parse_row(row), 1.0)
        if np.allclose(xyz(p), R @ q, atol=1e-9):
            return row
    return None


def snapshot_rows(e):
    """The fewest steps that put e where its full list does; the full list if unsure."""
    rows = e.transforms
    ops = [r[0] for r in rows]
    if len(rows) < 2 or (ops in (["scale", "vecrot", "move"], ["scale", "vecrot"], ["scale", "move"],
                                 ["vecrot", "move"]) and all(
            len(r) == 2 for r in rows if r[0] == "scale") and all(
            r[2:5] == ["0", "0", "0"] and r[8:] == ["default"] for r in rows if r[0] == "vecrot")):
        return rows                           # already a snapshot
    key = (e.kind, tuple(e.nums), e.twin, tuple(tuple(r) for r in rows))
    if key in _SNAP_CACHE:
        return _SNAP_CACHE[key]
    k = len(rows)
    while k and ALIASES.get(rows[k - 1][0].lower(), rows[k - 1][0].lower()) == "move":
        k -= 1
    if 0 < k < len(rows):                     # steps + trailing moves (a Replicate copy, a drag):
        head = copy.copy(e)                   # snapshot the steps, add the moves on - exact, and
        head.transforms = rows[:k]            # the steps are usually cached already
        out = [list(r) for r in snapshot_rows(head)]
        d = np.sum([parse_row(r)["d"] for r in rows[k:]], axis=0)
        if out and out[-1][0] == "move":
            d = d + np.array(parse_row(out.pop())["d"])
        if np.any(np.abs(d) > 1e-12):
            out.append(["move"] + [_n12(v) for v in d])
        out = out if len(out) < len(rows) else rows
        _SNAP_CACHE[key] = out
        return out
    out = rows
    try:
        net = _net_steps(e)
        if net:
            f, R, t = net
            short = [] if abs(f - 1) < 1e-12 else [["scale", _n12(f)]]
            turn = _turn_row(R)
            if turn is None and not np.allclose(R, np.eye(3), atol=1e-9):
                raise ValueError("turn not found")
            short += [turn] if turn else []
            if np.any(np.abs(t) > 1e-12):
                short.append(["move"] + [_n12(v) for v in t])
            if len(short) < len(rows) and _same_place(e, short):
                out = short
    except Exception as exc:                  # keep the full list - always safe
        print(f"{e.name}: kept full step list ({exc})")
    _SNAP_CACHE[key] = out
    return out


def _same_place(e, short):
    """Build e with its full and its short steps; True when they land on each other."""
    def placed(rows):
        tmp = copy.copy(e)
        tmp.transforms = rows
        obj = build(tmp)
        if tmp.twin and tmp.twin[2]:
            run_tf(obj, twin_turn(obj, tmp.twin[1]), 1.0)
        for row in rows:
            tf = parse_row(row)
            run_tf(obj, tf, 1.0)
        return np.array(sample_points(obj), float)
    a, b = placed(e.transforms), placed(short)
    if a.shape != b.shape or not a.size:
        return False
    size = max(float(np.ptp(a, axis=0).max()), 1.0)
    return bool(np.abs(a - b).max() <= 1e-6 * size)


# ----------------------------------------------------------------------------
# script recorder: wraps the library's transform methods while a script runs
# ----------------------------------------------------------------------------
class Event:
    def __init__(self, obj, tf, before, after):
        self.obj, self.tf, self.before, self.after = obj, tf, before, after


class Recorder:
    def __init__(self):
        self.events = []
        self.depth = 0
        self.saved = []

    def install(self):
        plan = {Point3d: tuple(ROT_TYPES) + ("move",),
                _Geometry3d: tuple(ROT_TYPES) + ("move", "scale")}
        for cls, names in plan.items():
            for name in names:
                if name in cls.__dict__:
                    orig = cls.__dict__[name]
                    self.saved.append((cls, name, orig))
                    setattr(cls, name, self._wrap(name, orig))

    def uninstall(self):
        for cls, name, orig in self.saved:
            setattr(cls, name, orig)
        self.saved = []

    def _wrap(rec, name, orig):
        def wrapper(self, *args, **kwargs):
            if rec.depth:                      # inner per-point calls pass straight through
                return orig(self, *args, **kwargs)
            try:
                pts = points_of(self)
                before = [(p, xyz(p)) for p in pts]
                tf = rec._describe(name, self, args, kwargs)
            except Exception:
                pts = None
            rec.depth += 1
            try:
                result = orig(self, *args, **kwargs)
            finally:
                rec.depth -= 1
            if pts is not None:
                rec.events.append(Event(self, tf, before, [(p, xyz(p)) for p in pts]))
            return result
        wrapper.__name__, wrapper.__doc__ = name, orig.__doc__
        return wrapper

    @staticmethod
    def _describe(name, obj, args, kwargs):
        def arg(i, *keys):
            if len(args) > i:
                return args[i]
            for k in keys:
                if k in kwargs:
                    return kwargs[k]
            return None
        if name == "move":
            return {"op": "move", "d": tuple(float(arg(i, k)) for i, k in enumerate(("dx", "dy", "dz")))}
        if name == "scale":
            return {"op": "scale", "f": float(arg(0, "factor"))}
        if name == "vecrot":
            axis = arg(0, "vecaxis")
            a, b = xyz(axis.get_start()), xyz(axis.get_end())
            piv = _rotation_pivot(arg(2, "pivot"), obj, default=a)
            return {"op": "vecrot", "deg": math.degrees(arg(1, "angle", "angle_rad")),
                    "axis": (a, b), "pivot": tuple(float(v) for v in piv)}
        piv = _rotation_pivot(arg(1, "pivot"), obj)
        return {"op": name, "deg": math.degrees(arg(0, "angle", "angle_rad")),
                "pivot": tuple(float(v) for v in piv)}


class PaneWriter:
    def __init__(self, text, tag=None):
        self.text, self.tag = text, tag

    def write(self, s):
        self.text.insert("end", s, self.tag)
        self.text.see("end")

    def flush(self):
        pass


# ----------------------------------------------------------------------------
# add-object dialog specs
# ----------------------------------------------------------------------------
ADD_SPECS = {
    "Point":  [("Position", "p", "xyz", (0, 0, 0)), ("Color", "c1", "color", "")],
    "Line":   [("Start", "a", "xyz", (0, 0, 0)), ("End", "b", "xyz", (5, 5, 5)),
               ("Color", "c1", "color", "orange")],
    "Vector": [("Origin", "a", "xyz", (0, 0, 0)), ("Direction (end point)", "b", "xyz", (0, 0, 5)),
               ("Color", "c1", "color", "yellow")],
    "Plane":  [("Point on plane", "p", "xyz", (0, 0, 0)), ("Normal", "n", "xyz", (0, 0, 1)),
               ("Size", "s", "num", 10), ("Border", "c1", "color", "cyan"),
               ("Fill", "c2", "color", "cyan")],
    "Square": [("Center", "p", "xyz", (0, 0, 0)), ("Side", "s", "num", 5),
               ("Facing", "o", ("XY", "XZ", "YZ"), "XY"), ("Border", "c1", "color", "white"),
               ("Fill", "c2", "color", "")],
    "Cube":   [("Base corner", "p", "xyz", (0, 0, 0)), ("Side", "s", "num", 4),
               ("Height (blank = side)", "h", "num", ""), ("Border", "c1", "color", "lime"),
               ("Fill", "c2", "color", "green")],
    "Sphere": [("Center", "p", "xyz", (0, 0, 0)), ("Radius", "r", "num", 3),
               ("Color", "c1", "color", "dodgerblue")],
}
for _label, _cls, _fill in (("Circle", Circle3d, "magenta"), ("Cylinder", Cylinder3d, "orange"),
                            ("Cone", Cone3d, "gold")):
    if _cls is not None:
        ADD_SPECS[_label] = ([("Center", "p", "xyz", (1, 1, 1)), ("Edge point", "e", "xyz", (4, 1, 1))]
                             + ([("Height", "h", "num", 5)] if _label != "Circle" else [])
                             + [("Border", "c1", "color", "white"), ("Fill", "c2", "color", _fill)])
if CurvedCylinder3d is not None:
    ADD_SPECS["Bend"] = [("Bend center", "p", "xyz", (0, 0, 0)), ("Spine start", "e", "xyz", (5, 0, 0)),
                         ("Normal", "n", "xyz", (0, 0, 1)), ("Tube radius", "r", "num", 1),
                         ("Bend angle (deg)", "a", "num", 90),
                         ("Chain from (skips the 3 xyz rows)", "src", "bendsrc", ""),
                         ("Twist (deg, chain)", "tw", "num", 0),
                         ("Bend radius (blank = center to start / same as chain)", "R", "num", ""),
                         ("Border", "c1", "color", "white"), ("Fill", "c2", "color", "orchid")]
if CurvedTorus3d is not None:
    ADD_SPECS["CurvedTorus"] = [("Center", "p", "xyz", (0, 0, 0)), ("Ring point", "e", "xyz", (5, 0, 0)),
                                ("Normal", "n", "xyz", (0, 0, 1)), ("Tube radius", "r", "num", 1),
                                ("Ring radius (must be > tube radius)", "R", "num", 5),
                                ("Segments", "s", "num", 4),
                                ("Border", "c1", "color", "white"), ("Fill", "c2", "color", "deepskyblue")]
ADD_SPECS["Lathe"] = []                  # opens the Lathe tool
ADD_SPECS.update(solids3d.ADD_SPECS)


def add_nums(label, v):
    if label == "Point":
        return list(v["p"])
    if label in ("Line", "Vector"):
        return list(v["a"]) + list(v["b"])
    if label == "Plane":
        return list(v["p"]) + list(v["n"]) + [v["s"]]
    if label == "Sphere":
        return list(v["p"]) + [v["r"]]
    if label in ("Circle", "Cylinder", "Cone"):
        return list(v["p"]) + list(v["e"]) + ([v["h"]] if label != "Circle" else [])
    if label in ("Bend", "CurvedTorus"):
        start = np.array(v["e"], float)
        if v["R"]:   # bend/ring radius given: slide spine start / ring point out or in to that distance
            d = start - np.array(v["p"], float)
            if np.linalg.norm(d) == 0:
                raise ValueError("Spine start must differ from bend center (it sets the direction)")
            start = np.array(v["p"], float) + d / np.linalg.norm(d) * v["R"]
        return list(v["p"]) + list(start) + [v["r"], v["a"] if label == "Bend" else v["s"]] + list(v["n"])
    if label == "Square":
        (cx, cy, cz), h = v["p"], v["s"] / 2
        corners = {"XY": [(cx - h, cy - h, cz), (cx + h, cy - h, cz), (cx + h, cy + h, cz), (cx - h, cy + h, cz)],
                   "XZ": [(cx - h, cy, cz - h), (cx + h, cy, cz - h), (cx + h, cy, cz + h), (cx - h, cy, cz + h)],
                   "YZ": [(cx, cy - h, cz - h), (cx, cy + h, cz - h), (cx, cy + h, cz + h), (cx, cy - h, cz + h)]}
        return [c for p in corners[v["o"]] for c in p]
    if label == "Cube":
        (x, y, z), s = v["p"], v["s"]
        h = s if v["h"] is None else v["h"]
        base = [(x, y, z), (x + s, y, z), (x + s, y + s, z), (x, y + s, z)]
        return [c for p in base + [(px, py, pz + h) for px, py, pz in base] for c in p]
    raise ValueError(label)


# ----------------------------------------------------------------------------
# Properties editor: the defining values of a live object, and new CSV numbers
# built from edited values (current geometry, so its transform rows get baked in)
# ----------------------------------------------------------------------------
def _unit(v, what="vector"):
    v = np.array(v, float)
    if np.linalg.norm(v) < 1e-12:
        raise ValueError(f"{what} cannot be zero")
    return v / np.linalg.norm(v)


def _perp_dir(old_dir, n):
    """old_dir made perpendicular to unit n (any perpendicular if they are parallel)."""
    d = np.array(old_dir, float) - np.dot(old_dir, n) * n
    if np.linalg.norm(d) < 1e-9:
        d = np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0))
    return d / np.linalg.norm(d)


def _box_basis(o, kind):
    """(origin, edge vectors) of a square / plane carrier (2 edges) or cube (3 edges)."""
    if kind == "cube3d":
        b, t = square_corners(o._square1), square_corners(o._square2)
        p = np.array(b[0], float)
        return p, [np.array(b[1]) - p, np.array(b[3]) - p, np.array(t[0]) - p], b + t
    c = square_corners(o)
    p = np.array(c[0], float)
    return p, [np.array(c[1]) - p, np.array(c[3]) - p], c


def prop_spec(e):
    """[(label, key, type, value)] for the selected entry; type is xyz / num / int / bool."""
    o, k = e.obj, e.kind
    if k in solids3d.KINDS:
        return solids3d.prop_spec(o, k)
    if k == "point3d":
        return [("Position", "p", "xyz", xyz(o))]
    if k in ("line3d", "vector3d"):
        a, b = xyz(o.get_start()), xyz(o.get_end())
        return [("Start", "a", "xyz", a), ("End", "b", "xyz", b),
                ("Length", "L", "num", float(np.linalg.norm(np.subtract(b, a))))]
    if k == "sphere3d":
        return [("Center", "p", "xyz", center_of(o)), ("Radius", "r", "num", float(o.get_radius()))]
    if k in ("circle3d", "cylinder3d", "cone3d"):
        ctr, n, r, h = round_geom(o)
        return ([("Center", "p", "xyz", tuple(ctr)), ("Radius", "r", "num", r)]
                + ([("Height", "h", "num", h)] if h is not None else [])
                + [("Normal / axis", "n", "xyz", tuple(n))])
    if k == "curvedcylinder3d":
        return [("Bend center", "p", "xyz", xyz(o.get_bend_center())),
                ("Bend radius", "R", "num", o.get_bend_radius()),
                ("Tube radius", "r", "num", o.get_tube_radius()),
                ("Bend angle (deg)", "a", "num", math.degrees(o.get_angle())),
                ("Normal", "n", "xyz", tuple(float(v) for v in o.get_norm())),
                ("Keep tube length (angle change straightens / curls it)", "keep", "bool", False),
                ("Move bends chained after this one along", "carry", "bool", True)]
    if k == "curvedtorus3d":
        return [("Center", "p", "xyz", xyz(o.get_center())),
                ("Ring radius", "R", "num", o.get_major_radius()),
                ("Tube radius", "r", "num", o.get_minor_radius()),
                ("Segments", "s", "int", len(o.get_bends())),
                ("Normal", "n", "xyz", tuple(float(v) for v in o.get_norm()))]
    if k in ("square3d", "plane3d"):
        p, (u, v), c = _box_basis(o, k)
        ctr = tuple(np.mean(np.array(c, float), axis=0))
        if k == "plane3d":
            return [("Point on plane", "p", "xyz", ctr),
                    ("Normal", "n", "xyz", tuple(_unit(np.cross(u, v)))),
                    ("Size", "s", "num", float(np.linalg.norm(u)))]
        return [("Center", "p", "xyz", ctr), ("Width (edge 1-2)", "w", "num", float(np.linalg.norm(u))),
                ("Height (edge 1-4)", "d", "num", float(np.linalg.norm(v)))]
    if k == "cube3d":
        p, edges, _c = _box_basis(o, k)
        return [("Base corner", "p", "xyz", tuple(p))] + [
            (label, key, "num", float(np.linalg.norm(ed)))
            for (label, key), ed in zip((("Width", "w"), ("Depth", "d"), ("Height", "h")), edges)]
    return []


def prop_nums(e, v, changed):
    """New CSV numbers for entry e from edited values v (changed = keys the user edited)."""
    o, k = e.obj, e.kind
    if k in solids3d.KINDS:
        return solids3d.prop_nums(o, k, v)
    if k == "point3d":
        return list(v["p"])
    if k in ("line3d", "vector3d"):
        a, b = np.array(v["a"], float), np.array(v["b"], float)
        if "L" in changed:
            if v["L"] <= 0:
                raise ValueError("Length must be > 0")
            b = a + _unit(b - a, "Start-to-end direction") * v["L"]
        return list(a) + list(b)
    if k == "sphere3d":
        if v["r"] <= 0:
            raise ValueError("Radius must be > 0")
        return list(v["p"]) + [v["r"]]
    if k in ("circle3d", "cylinder3d", "cone3d"):
        if v["r"] <= 0 or v.get("h", 1) <= 0:
            raise ValueError("Radius and height must be > 0")
        n = _unit(v["n"], "Normal")
        radial = np.subtract(xyz(o.get_vec1().get_end()), xyz(o.get_center()))
        edge = np.array(v["p"], float) + _perp_dir(radial, n) * v["r"]
        return list(v["p"]) + list(edge) + ([v["h"]] if "h" in v else []) + list(n)
    if k in ("curvedcylinder3d", "curvedtorus3d"):
        n = _unit(v["n"], "Normal")
        R = v["R"]
        if k == "curvedcylinder3d":
            if not 0 < v["a"] <= 360:
                raise ValueError("Bend angle must be > 0 and <= 360")
            if v.get("keep") and "a" in changed and "R" not in changed:
                R = o.get_bend_radius() * math.degrees(o.get_angle()) / v["a"]   # same arc length
            old_c, old_s = xyz(o.get_bend_center()), xyz(o.get_spine_start())
            last = v["a"]
        else:
            if v["s"] < 1:
                raise ValueError("Segments must be at least 1")
            first = o.get_bends()[0]
            old_c, old_s = xyz(first.get_bend_center()), xyz(first.get_spine_start())
            last = v["s"]
        if not 0 < v["r"] < R:
            raise ValueError(f"Tube radius ({fmt(v['r'])}) must be > 0 and smaller than the "
                             f"{'bend' if k == 'curvedcylinder3d' else 'ring'} radius ({fmt(R)})")
        start = np.array(v["p"], float) + _perp_dir(np.subtract(old_s, old_c), n) * R
        return list(v["p"]) + list(start) + [v["r"], last] + list(n)
    if k in ("square3d", "plane3d", "cube3d"):
        if k == "plane3d":
            if v["s"] <= 0:
                raise ValueError("Size must be > 0")
            return list(v["p"]) + list(_unit(v["n"], "Normal")) + [v["s"]]
        p, edges, corners = _box_basis(o, k)
        sizes = [v["w"], v["d"]] + ([v["h"]] if k == "cube3d" else [])
        if min(sizes) <= 0:
            raise ValueError("Sizes must be > 0")
        M = np.array(edges).T                  # corner = p + M @ coeffs
        if k == "square3d":                    # 2 edges: add the face normal to make it solvable
            M = np.column_stack([M, _unit(np.cross(edges[0], edges[1]), "Square face")])
            sizes.append(1.0)
            edges = edges + [M[:, 2]]
        scale = np.array([s / np.linalg.norm(ed) for s, ed in zip(sizes, edges)])
        coeffs = [np.linalg.solve(M, np.array(c, float) - p) for c in corners]
        newM = M * scale
        if k == "square3d":                    # keep the center where the user put it
            pts = [newM @ c for c in coeffs]
            off = np.array(v["p"], float) - np.mean(pts, axis=0)
            return [float(x) for q in pts for x in q + off]
        return [float(x) for c in coeffs for x in np.array(v["p"], float) + newM @ c]
    raise ValueError(f"no editable properties for {k}")


# ----------------------------------------------------------------------------
# the app
# ----------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("3D Testbed - class3d viewer")
        root.geometry("1450x920")
        self.entries = []
        self.script_objs = []          # [(name, obj)] from the last script run
        self.events = []
        self.selected = None           # ("s", Entry) or ("r", index)
        self.anim_target = None
        self.overlay = []
        self.jobs = []
        self.job_running = False
        self._rgb_cache = {}
        self._drag = None
        self._props = None             # Properties window: (Toplevel, body frame, fields) or None
        self.groups = {}               # name -> class3d.ObjGroup3d of the live member objects
        self.view = None               # director camera while drawing its preview, else None
        self.director = None           # open Camera Director window (director3d.Director)
        self.lathe_tool = None         # open Lathe tool window (lathe3d.LatheTool)
        self.ghosts = []               # [(name, obj)] previews drawn but not in the scene
        self.reset_camera()
        self.grid_step, self.grid_ext = 1.0, 10.0
        self._build_ui()
        if self._mac:   # started from Terminal, macOS can leave keyboard input with Terminal
            root.lift()
            root.attributes("-topmost", True)
            root.after(300, lambda: (root.attributes("-topmost", False), root.focus_force()))
        sys.stdout = PaneWriter(self.out)
        sys.stderr = PaneWriter(self.out, "err")
        root.report_callback_exception = lambda *exc: traceback.print_exception(*exc)
        self.load_or_bootstrap()
        root.after(100, self.fit_view)

    # ------------------------------------------------------------- UI layout
    def _build_ui(self):
        # left: 3D view over the Output pane; right: the side panel, full height and scrollable
        top = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        top.pack(fill=tk.BOTH, expand=True)
        outer = ttk.PanedWindow(top, orient=tk.VERTICAL)
        top.add(outer, weight=4)

        self.canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, width=950, height=640)
        outer.add(self.canvas, weight=4)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", lambda e: self._drag_start(e, "orbit"))
        self.canvas.bind("<ButtonPress-3>", lambda e: self._drag_start(e, "pan"))
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._release1)
        self.canvas.bind("<B3-Motion>", self._drag_move)
        self.canvas.bind("<Motion>", lambda e: self.director is not None and self.director.hover(e.x, e.y))
        self.canvas.bind("<MouseWheel>", self._wheel)
        ui_scroll.x11_wheel(self.canvas, self._wheel)
        try:                          # Tk 9: two-finger trackpad scroll arrives as its own event
            self.canvas.bind("<TouchpadScroll>", self._touch_scroll)
        except tk.TclError:
            pass
        self._mac = self.root.tk.call("tk", "windowingsystem") == "aqua"
        if self._mac:                  # Mac: right button is Button-2; Ctrl-click also pans
            for b in ("<ButtonPress-2>", "<Control-ButtonPress-1>"):
                self.canvas.bind(b, lambda e: self._drag_start(e, "pan"))
            self.canvas.bind("<B2-Motion>", self._drag_move)
            self.canvas.bind("<Control-B1-Motion>", self._drag_move)
        # Fly keys are bound on the window (Mac Tk won't give a canvas keyboard focus);
        # _fly ignores them while typing in an entry box. Shift = 4x step.
        for keys, args in ((("w", "W"), ("move", 0, 1, 0)), (("s", "S"), ("move", 0, -1, 0)),
                           (("a", "A"), ("move", -1, 0, 0)), (("d", "D"), ("move", 1, 0, 0)),
                           (("e", "E"), ("move", 0, 0, 1)), (("q", "Q"), ("move", 0, 0, -1)),
                           (("Left",), ("look", -1, 0)), (("Right",), ("look", 1, 0)),
                           (("Up",), ("look", 0, -1)), (("Down",), ("look", 0, 1))):
            for k in keys:
                self.root.bind(f"<KeyPress-{k}>", lambda ev, a=args: self._fly(ev, *a))
                self.root.bind(f"<Shift-KeyPress-{k}>", lambda ev, a=args: self._fly(ev, *a))

        holder, panel = ui_scroll.scrollable(top)
        top.add(holder, weight=1)
        self._build_panel(panel)

        outf = ttk.Frame(outer)
        outer.add(outf, weight=1)
        bar = ttk.Frame(outf)
        bar.pack(fill=tk.X)
        ttk.Label(bar, text="Output").pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Clear", command=lambda: self.out.delete("1.0", "end")).pack(side=tk.RIGHT)
        body = ttk.Frame(outf)
        body.pack(fill=tk.BOTH, expand=True)
        self.out = tk.Text(body, height=11, bg="#111317", fg="#d8dde6", insertbackground="#d8dde6",
                           font=("Consolas", 9), wrap="none")
        ys = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.out.yview)
        xs = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=self.out.xview)
        self.out.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.out.tag_configure("err", foreground="#ff7b72")
        ys.pack(side=tk.RIGHT, fill=tk.Y)
        xs.pack(side=tk.BOTTOM, fill=tk.X)
        self.out.pack(fill=tk.BOTH, expand=True)

    def _build_panel(self, p):
        r1 = ttk.Frame(p)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="Add:").pack(side=tk.LEFT)
        self.v_add = tk.StringVar(value="Cube")
        ttk.Combobox(r1, textvariable=self.v_add, values=list(ADD_SPECS), width=11,
                     state="readonly").pack(side=tk.LEFT, padx=3)
        ttk.Button(r1, text="Add...", command=self.add_dialog).pack(side=tk.LEFT)
        ttk.Button(r1, text="Lathe tool [F7]", command=self.open_lathe).pack(side=tk.LEFT, padx=3)
        self.root.bind("<F7>", lambda _e: self.open_lathe())

        r2 = ttk.Frame(p)
        r2.pack(fill=tk.X, pady=2)
        ttk.Button(r2, text="Run script...", command=self.ask_run_script).pack(side=tk.LEFT)
        ttk.Button(r2, text="Replay", command=self.replay).pack(side=tk.LEFT, padx=3)
        ttk.Button(r2, text="Keep script objs", command=self.keep_script_objs).pack(side=tk.LEFT)
        ttk.Button(r2, text="Undo [Ctrl+Z]", command=self.undo).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(r2, text="Redo [Ctrl+Y]", command=self.redo).pack(side=tk.LEFT, padx=3)

        r3 = ttk.Frame(p)
        r3.pack(fill=tk.X, pady=2)
        ttk.Button(r3, text="Fit view", command=self.fit_view).pack(side=tk.LEFT)
        ttk.Button(r3, text="Reset view", command=lambda: (self.reset_camera(), self.fit_view())
                   ).pack(side=tk.LEFT, padx=3)
        ttk.Label(r3, text="Step deg").pack(side=tk.LEFT, padx=(8, 2))
        self.v_step = tk.StringVar(value="360")
        ttk.Spinbox(r3, from_=1, to=90, textvariable=self.v_step, width=4).pack(side=tk.LEFT)
        ttk.Label(r3, text="ms").pack(side=tk.LEFT, padx=(6, 2))
        self.v_delay = tk.StringVar(value="0")
        ttk.Spinbox(r3, from_=5, to=500, increment=5, textvariable=self.v_delay, width=4).pack(side=tk.LEFT)

        r4 = ttk.Frame(p)
        r4.pack(fill=tk.X, pady=2)
        self.v_coords = tk.BooleanVar(value=True)
        self.v_grid = tk.BooleanVar(value=True)
        self.v_show_scene = tk.BooleanVar(value=True)
        self.v_show_script = tk.BooleanVar(value=True)
        for text, var in (("Coords", self.v_coords), ("Grid", self.v_grid),
                          ("Scene", self.v_show_scene), ("Script objs", self.v_show_script)):
            ttk.Checkbutton(r4, text=text, variable=var, command=self.redraw).pack(side=tk.LEFT)

        r5 = ttk.LabelFrame(p, text="POV-Ray", padding=3)
        r5.pack(fill=tk.X, pady=2)
        ttk.Button(r5, text="Render [F9]", command=self.render_pov).pack(side=tk.LEFT)
        self.v_pov_q = tk.StringVar(value="Draft")
        ttk.Combobox(r5, textvariable=self.v_pov_q, values=("Draft", "Final"), width=6,
                     state="readonly").pack(side=tk.LEFT, padx=2)
        self.v_pov_w = tk.StringVar(value="640")
        ttk.Combobox(r5, textvariable=self.v_pov_w, values=("320", "640", "1024", "1600", "1920"),
                     width=5).pack(side=tk.LEFT)
        ttk.Label(r5, text="px").pack(side=tk.LEFT, padx=(1, 4))
        ttk.Button(r5, text="Save .pov...", command=self.save_pov).pack(side=tk.LEFT)
        ttk.Button(r5, text="POV GUI", command=self.open_pov_gui).pack(side=tk.LEFT, padx=2)
        ttk.Button(r5, text="Camera Director [F8]", command=self.open_director).pack(side=tk.LEFT, padx=2)
        ttk.Button(r5, text="Taichi preview [F10]", command=self.open_preview).pack(side=tk.LEFT, padx=2)
        self.v_tk_draw = tk.BooleanVar(value=False)
        ttk.Checkbutton(r5, text="Draw here too", variable=self.v_tk_draw,
                        command=self.redraw).pack(side=tk.LEFT, padx=2)
        self.root.bind("<F10>", lambda _e: self.open_preview())
        self.root.bind("<F9>", lambda _e: self.render_pov())
        self.root.bind("<F8>", lambda _e: self.open_director())

        # where you stand: type an eye + look-at point, or jump to the selection.
        # With a director Camera key / Aim selected, the same boxes edit that key.
        cf = ttk.LabelFrame(p, text="View / camera key", padding=3)
        cf.pack(fill=tk.X, pady=2)
        self.v_eye = self._xyz_row(cf, 0, "Eye", ("0", "-20", "10"))
        self.v_look = self._xyz_row(cf, 1, "Look at", ("0", "0", "0"))
        ttk.Label(cf, text="FOV").grid(row=2, column=0, sticky="w")
        self.v_fov = tk.StringVar(value="45")
        ttk.Entry(cf, textvariable=self.v_fov, width=6).grid(row=2, column=1, sticky="we")
        ttk.Button(cf, text="Fill from view", command=self.view_fill).grid(row=2, column=2, columnspan=2, sticky="we")
        ttk.Button(cf, text="Go there", command=self.view_go).grid(row=0, column=4, sticky="we")
        ttk.Button(cf, text="Fly to selected", command=self.fly_to).grid(row=1, column=4, sticky="we")
        ttk.Button(cf, text="Set camera key", command=self.view_set_key).grid(row=2, column=4, sticky="we")
        for c in range(5):
            cf.columnconfigure(c, weight=1)

        tf = ttk.Frame(p)
        tf.pack(fill=tk.BOTH, expand=True, pady=4)
        # extended: Ctrl/Shift-click several objects, then "Tag" puts them all in one group
        self.tree = ttk.Treeview(tf, columns=("kind", "group"), height=11, selectmode="extended")
        self.tree.heading("#0", text="Object")
        self.tree.heading("kind", text="Type")
        self.tree.heading("group", text="Group")
        self.tree.column("#0", width=150)
        self.tree.column("kind", width=85)
        self.tree.column("group", width=60)
        sb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-Button-1>", lambda _e: self.open_props())
        # keys work anywhere in the main window except while typing in a box
        for seq, fn in (("<Delete>", self._delete_key), ("<Control-z>", self._ctrl_z),
                        ("<Control-Z>", self._ctrl_z), ("<Control-y>", self.redo),
                        ("<Control-Y>", self.redo), ("<Control-a>", self.select_all),
                        ("<Control-A>", self.select_all), ("<Escape>", self.select_none)):
            self.root.bind(seq, fn)

        ef = ttk.LabelFrame(p, text="Selected object", padding=4)
        ef.pack(fill=tk.X)
        self.edit_frame = ef
        g = 0
        self.v_name = tk.StringVar()
        ttk.Label(ef, text="Name").grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_name, width=14).grid(row=g, column=1, columnspan=2, sticky="we")
        ttk.Button(ef, text="Rename", command=self.rename).grid(row=g, column=3, sticky="we")
        ttk.Button(ef, text="Properties...", command=self.open_props).grid(row=g, column=4, sticky="we")
        g += 1
        self.v_c1, self.v_c2 = tk.StringVar(), tk.StringVar()
        ttk.Label(ef, text="Color").grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_c1, width=9).grid(row=g, column=1, sticky="we")
        ttk.Button(ef, text="...", width=3, command=lambda: self.pick(self.v_c1)).grid(row=g, column=2)
        g += 1
        ttk.Label(ef, text="Fill").grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_c2, width=9).grid(row=g, column=1, sticky="we")
        ttk.Button(ef, text="...", width=3, command=lambda: self.pick(self.v_c2)).grid(row=g, column=2)
        ttk.Button(ef, text="Apply colors", command=self.apply_colors).grid(row=g - 1, column=3,
                                                                          rowspan=2, sticky="nswe")
        g += 1
        self.v_mat_grp, self.v_mat_name, self.v_mat_scale = tk.StringVar(value="Color"), tk.StringVar(), tk.StringVar(value="1")
        ttk.Label(ef, text="Material").grid(row=g, column=0, sticky="w")
        self.cb_mat_grp = ttk.Combobox(ef, textvariable=self.v_mat_grp, width=8, state="readonly")
        self.cb_mat_grp.grid(row=g, column=1, columnspan=2, sticky="we")
        self.cb_mat_grp.bind("<<ComboboxSelected>>", lambda _e: self._mat_group_changed())
        self.cb_mat_name = ttk.Combobox(ef, textvariable=self.v_mat_name, width=16, state="readonly")
        self.cb_mat_name.grid(row=g, column=3, columnspan=2, sticky="we")
        g += 1
        ttk.Label(ef, text="Tex scale").grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_mat_scale, width=6).grid(row=g, column=1, sticky="we")
        ttk.Button(ef, text="Image...", command=self.pick_image).grid(row=g, column=2, columnspan=2, sticky="we")
        ttk.Button(ef, text="Apply material", command=self.apply_material).grid(row=g, column=4, sticky="we")
        self.pov_lib = {}                      # filled in the background (WSL may need to boot)
        self._mat_groups()
        threading.Thread(target=self._load_pov_lib, daemon=True).start()
        self.root.after(200, self._poll_pov_lib)
        g += 1
        ttk.Label(ef, text="Group").grid(row=g, column=0, sticky="w")
        self.v_group = tk.StringVar()
        self.cb_group = ttk.Combobox(ef, textvariable=self.v_group, width=10)
        self.cb_group.grid(row=g, column=1, columnspan=2, sticky="we")
        ttk.Button(ef, text="Tag", command=self.tag_group).grid(row=g, column=3, sticky="we")
        ttk.Button(ef, text="Untag", command=self.untag_group).grid(row=g, column=4, sticky="we")
        g += 1
        self.v_group_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(ef, text="Move / rotate / scale the whole group as one unit",
                        variable=self.v_group_mode, command=self.redraw).grid(
            row=g, column=0, columnspan=5, sticky="w")
        g += 1
        # twin: a 180 deg turned copy under the object, lifted 1-100 % of its height, one solid
        self.v_twin, self.v_twin_flip = tk.BooleanVar(), tk.BooleanVar()
        self.v_twin_pct, self.v_twin_axis = tk.StringVar(value="100"), tk.StringVar(value="own")
        ttk.Checkbutton(ef, text="Twin", variable=self.v_twin).grid(row=g, column=0, sticky="w")
        ttk.Spinbox(ef, from_=1, to=100, textvariable=self.v_twin_pct, width=4).grid(row=g, column=1, sticky="we")
        ttk.Combobox(ef, textvariable=self.v_twin_axis, values=tuple(TWIN_AXES), width=3,
                     state="readonly").grid(row=g, column=2, sticky="we")
        ttk.Checkbutton(ef, text="flip 1st", variable=self.v_twin_flip).grid(row=g, column=3, sticky="w")
        ttk.Button(ef, text="Apply twin", command=self.apply_twin).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Label(ef, text="  lift % (100 touching, 50 half overlap), axis", foreground="#7a828e").grid(
            row=g, column=0, columnspan=5, sticky="w")
        g += 1
        self.v_csg_op, self.v_csg_target = tk.StringVar(value="none"), tk.StringVar()
        ttk.Label(ef, text="CSG").grid(row=g, column=0, sticky="w")
        ttk.Combobox(ef, textvariable=self.v_csg_op, values=CSG_OPS, width=8,
                     state="readonly").grid(row=g, column=1, sticky="we")
        self.cb_csg_target = ttk.Combobox(ef, textvariable=self.v_csg_target, width=12, state="readonly")
        self.cb_csg_target.grid(row=g, column=2, columnspan=2, sticky="we")
        ttk.Button(ef, text="Apply CSG", command=self.apply_csg).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Label(ef, text="  combines with / cuts / overlaps the target (@name = a whole group;"
                           " 'whole group' on = the group is the tool)",
                  foreground="#7a828e").grid(row=g, column=0, columnspan=5, sticky="w")
        g += 1
        # hollow: an inner copy, every wall pulled in by the thickness, cut out of the object
        self.v_hollow, self.v_hollow_t, self.v_hollow_open = \
            tk.BooleanVar(), tk.StringVar(value="0.1"), tk.StringVar(value="none")
        ttk.Checkbutton(ef, text="Hollow", variable=self.v_hollow).grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_hollow_t, width=6).grid(row=g, column=1, sticky="we")
        ttk.Combobox(ef, textvariable=self.v_hollow_open, values=HOLLOW_OPEN, width=7,
                     state="readonly").grid(row=g, column=2, columnspan=2, sticky="we")
        ttk.Button(ef, text="Apply hollow", command=self.apply_hollow).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Label(ef, text="  wall thickness, open end (top = along the object's own axis)",
                  foreground="#7a828e").grid(row=g, column=0, columnspan=5, sticky="w")
        g += 1
        ttk.Button(ef, text="Look at it", command=self.dir_look).grid(row=g, column=0, columnspan=2, sticky="we")
        ttk.Button(ef, text="View through camera", command=self.dir_through).grid(
            row=g, column=2, columnspan=2, sticky="we")
        ttk.Button(ef, text="Camera = view", command=self.dir_from_view).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Separator(ef).grid(row=g, column=0, columnspan=4, sticky="we", pady=3)
        g += 1
        self.v_mv = self._xyz_row(ef, g, "Move by", ("0", "0", "0"))
        ttk.Button(ef, text="Move", command=self.move_by).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Button(ef, text="Move all by these (not planes)", command=self.move_all).grid(
            row=g, column=1, columnspan=4, sticky="we")
        g += 1
        # rescale the whole world about the origin: type the width you want it to be
        self.v_world = tk.StringVar(value="100")
        ttk.Label(ef, text="World width").grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_world, width=8).grid(row=g, column=1, sticky="we")
        self.l_world = ttk.Label(ef, text="", foreground="#7a828e")
        self.l_world.grid(row=g, column=2, columnspan=2, sticky="w")
        ttk.Button(ef, text="Rescale", command=self.rescale_world).grid(row=g, column=4, sticky="we")
        g += 1
        self.v_to = self._xyz_row(ef, g, "Center to", ("0", "0", "0"))
        ttk.Button(ef, text="Go", command=self.move_to).grid(row=g, column=4, sticky="we")
        g += 1
        # align: click the one that stays first, Ctrl/Shift-click the ones that move to it
        self.v_align_ax, self.v_align_how = tk.StringVar(value="XYZ"), tk.StringVar(value="center")
        ttk.Label(ef, text="Align").grid(row=g, column=0, sticky="w")
        ttk.Combobox(ef, textvariable=self.v_align_ax, values=ALIGN_AXES, width=4,
                     state="readonly").grid(row=g, column=1, sticky="we")
        ttk.Combobox(ef, textvariable=self.v_align_how, values=ALIGN_HOW, width=9,
                     state="readonly").grid(row=g, column=2, columnspan=2, sticky="we")
        ttk.Button(ef, text="Align", command=self.align).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Label(ef, text="  first clicked stays, Ctrl-clicked ones move to it ('stack on': last axis"
                           " sits on top)", foreground="#7a828e").grid(row=g, column=0, columnspan=5, sticky="w")
        g += 1
        self.v_rep_n = tk.StringVar(value="3")
        ttk.Label(ef, text="Replicate").grid(row=g, column=0, sticky="w")
        ttk.Spinbox(ef, from_=1, to=500, textvariable=self.v_rep_n, width=4).grid(row=g, column=1, sticky="we")
        ttk.Label(ef, text="copies, into group").grid(row=g, column=2, columnspan=2, sticky="w")
        self.v_rep_group = tk.StringVar()
        ttk.Entry(ef, textvariable=self.v_rep_group, width=8).grid(row=g, column=4, sticky="we")
        g += 1
        self.v_rep_step = self._xyz_row(ef, g, "  step", ("2", "0", "0"))
        ttk.Button(ef, text="Replicate", command=self.replicate).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Label(ef, text="  copies the selection (whole groups, CSG, twin, hollow), each one step further;"
                           " group box optional", foreground="#7a828e").grid(row=g, column=0, columnspan=5, sticky="w")
        g += 1
        ttk.Label(ef, text="Scale x").grid(row=g, column=0, sticky="w")
        self.v_scale = tk.StringVar(value="2")
        ttk.Entry(ef, textvariable=self.v_scale, width=6).grid(row=g, column=1, sticky="we")
        ttk.Label(ef, text="(origin; group: its center)").grid(row=g, column=2, columnspan=2, sticky="w")
        ttk.Button(ef, text="Scale", command=self.scale_by).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Separator(ef).grid(row=g, column=0, columnspan=5, sticky="we", pady=3)
        g += 1
        ttk.Label(ef, text="Rotate").grid(row=g, column=0, sticky="w")
        self.v_rot = tk.StringVar(value=ROT_TYPES[0])
        ttk.Combobox(ef, textvariable=self.v_rot, values=ROT_TYPES, width=7,
                     state="readonly").grid(row=g, column=1, sticky="we")
        ttk.Label(ef, text="deg").grid(row=g, column=2, sticky="e")
        self.v_deg = tk.StringVar(value="90")
        ttk.Entry(ef, textvariable=self.v_deg, width=6).grid(row=g, column=3, sticky="we")
        g += 1
        ttk.Label(ef, text="Pivot").grid(row=g, column=0, sticky="w")
        self.v_pivot = tk.StringVar(value="center")
        self.cb_pivot = ttk.Combobox(ef, textvariable=self.v_pivot, width=14)
        self.cb_pivot.grid(row=g, column=1, columnspan=3, sticky="we")
        g += 1
        self.v_pxyz = self._xyz_row(ef, g, "  point", ("0", "0", "0"))
        g += 1
        ttk.Label(ef, text="Axis").grid(row=g, column=0, sticky="w")
        self.v_axis = tk.StringVar(value="custom")
        self.cb_axis = ttk.Combobox(ef, textvariable=self.v_axis, width=14, state="readonly")
        self.cb_axis.grid(row=g, column=1, columnspan=3, sticky="we")
        g += 1
        self.v_axa = self._xyz_row(ef, g, "  from", ("0", "0", "0"))
        g += 1
        self.v_axb = self._xyz_row(ef, g, "  to", ("1", "1", "0"))
        g += 1
        ttk.Button(ef, text="Rotate  >", command=self.rotate).grid(row=g, column=0, columnspan=5,
                                                                    sticky="we", pady=3)
        g += 1
        ttk.Label(ef, text="Transforms (saved under the object):").grid(row=g, column=0, columnspan=5,
                                                                         sticky="w")
        g += 1
        self.lb_tf = tk.Listbox(ef, height=5, font=("Consolas", 8))
        self.lb_tf.grid(row=g, column=0, columnspan=5, sticky="we")
        g += 1
        ttk.Button(ef, text="Undo last transform", command=self.undo_tf).grid(row=g, column=0,
                                                                            columnspan=2, sticky="we")
        ttk.Button(ef, text="Delete object", command=self.delete_selected).grid(row=g, column=2,
                                                                              columnspan=3, sticky="we")
        for c in range(5):
            ef.columnconfigure(c, weight=1)

    def _xyz_row(self, parent, row, label, defaults):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        vars_ = []
        for i, d in enumerate(defaults):
            v = tk.StringVar(value=d)
            ttk.Entry(parent, textvariable=v, width=6).grid(row=row, column=1 + i, sticky="we")
            vars_.append(v)
        return vars_

    @staticmethod
    def _floats(vars_):
        return tuple(float(v.get()) for v in vars_)

    def pick(self, var, parent=None):
        # parent = the window the button is in, so the picker opens on top of it
        res = colorchooser.askcolor(color=var.get() or None, parent=parent or self.root)
        if res and res[1]:
            var.set(res[1])

    def valid_color(self, c):
        try:
            self.root.winfo_rgb(c)
            return True
        except tk.TclError:
            return False

    # ----------------------------------------------------- scene management
    def load_or_bootstrap(self):
        if os.path.exists(SCENE_FILE):
            self.entries = load_scene(SCENE_FILE)
            for e in self.entries:
                self.rebuild(e)
            print(f"Loaded {len(self.entries)} objects from {os.path.basename(SCENE_FILE)}")
        elif os.path.exists(DEFAULT_SCRIPT):
            print(f"No {os.path.basename(SCENE_FILE)} yet - building it from {os.path.basename(DEFAULT_SCRIPT)}")
            self.run_script(DEFAULT_SCRIPT, replay=False)
            self.keep_script_objs()
        else:
            self.save()
        self.refresh()

    def save(self):
        old = self._scene_text()
        try:
            save_scene(SCENE_FILE, self.entries)
        except OSError as exc:
            print(f"Could not save {SCENE_FILE}: {exc}")
        self._note_undo(old)
        self.preview_refresh()                            # Taichi preview open: send it the change

    # ------------------------------------------------- global undo / redo
    # Every change ends in save(), so undo keeps the scene file as it was before each one
    # (whole scene, last change first). Saves from one action count as one step.
    UNDO_MAX = 200

    @staticmethod
    def _scene_text():
        try:
            with open(SCENE_FILE, newline="") as f:
                return f.read()
        except OSError:
            return None

    def _note_undo(self, old):
        if old is None or getattr(self, "_undo_busy", False):
            return
        if old == self._scene_text():
            return
        if not getattr(self, "_undo_open", False):
            undo = self.__dict__.setdefault("undo_stack", [])
            undo.append(old)
            del undo[:-self.UNDO_MAX]
            self.__dict__.setdefault("redo_stack", []).clear()
            self._undo_open = True
            self.root.after_idle(lambda: setattr(self, "_undo_open", False))

    @staticmethod
    def _typing(ev):
        return ev is not None and ev.widget.winfo_class() in (
            "Entry", "TEntry", "Text", "TCombobox", "Listbox", "Spinbox", "TSpinbox")

    def undo(self, ev=None):
        return self._undo_redo(ev, "undo_stack", "redo_stack", "Undo")

    def redo(self, ev=None):
        return self._undo_redo(ev, "redo_stack", "undo_stack", "Redo")

    def _ctrl_z(self, ev):                    # Ctrl+Shift+Z = redo (Caps Lock alone doesn't count)
        return self.redo(ev) if ev.state & 0x0001 else self.undo(ev)

    @staticmethod
    def _call_job(fn):
        """fn() as a one-step job (runs after the jobs already queued)."""
        fn()
        return
        yield

    def _undo_redo(self, ev, src, dst, what, in_job=False):
        if self._typing(ev):
            return None                       # let the text box have its own key
        src, dst = self.__dict__.setdefault(src, []), self.__dict__.setdefault(dst, [])
        if not src:
            print(f"{what}: nothing to {what.lower()}")
            return "break"
        if self.job_running and not in_job:
            print(f"{what}: wait for the move in progress to finish")
            return "break"
        now = self._scene_text()
        text = src.pop()
        try:
            with open(SCENE_FILE, "w", newline="") as f:
                f.write(text)
        except OSError as exc:
            src.append(text)
            print(f"{what}: could not write {SCENE_FILE}: {exc}")
            return "break"
        if now is not None:
            dst.append(now)
        n_before = len(self.entries)
        self._undo_busy = True
        try:
            def same(e):                      # what the built object depends on
                return (tuple(e.row()), e.twin, tuple(tuple(r) for r in snapshot_rows(e)))
            built = {}                        # one undo usually changes one object: keep the rest
            for e in self.entries:
                if e.obj is not None:
                    built.setdefault(same(e), []).append((e.obj, e.twin_obj))
            self.entries = load_scene(SCENE_FILE)
            for e in self.entries:
                hit = built.get(same(e))
                if hit:
                    e.obj, e.twin_obj = hit.pop()
                else:
                    self.rebuild(e)
            self.selected = None
            self.refresh()
            self.preview_refresh()
        finally:
            self._undo_busy = False
        print(f"{what} ({len(self.entries)} objects, was {n_before}) - "
              f"{len(self.undo_stack)} undo / {len(self.redo_stack)} redo left")
        return "break"

    def select_all(self, ev=None):
        if self._typing(ev):
            return None
        self.tree.selection_set([f"s{i}" for i in range(len(self.entries))])
        return "break"

    def select_none(self, ev=None):
        if self._typing(ev):
            return None
        self.tree.selection_remove(*self.tree.selection())
        self.selected = None
        self.redraw()
        return "break"

    def _delete_key(self, ev=None):
        if self._typing(ev):
            return None
        self.delete_selected()
        return "break"

    def rebuild(self, e):
        """Recreate e.obj from its CSV row, then replay its transforms instantly."""
        e.twin_obj = twin = None
        try:
            obj = build(e)
            if e.twin:                         # pair is set up in the object's own frame first
                lift, axis, flip = e.twin
                n0 = own_axis(obj) if axis == "own" else None   # before any flip
                flip_tf = twin_turn(obj, axis) if flip else None
                if flip_tf:
                    run_tf(obj, flip_tf, 1.0)
                twin = build(e)
                if flip_tf:
                    run_tf(twin, flip_tf, 1.0)
                run_tf(twin, twin_turn(obj, axis, lift, n0), 1.0)
        except Exception as exc:
            print(f"{e.name}: cannot build {e.kind}: {exc}")
            e.obj = None
            return
        for row in e.transforms:
            try:
                tf = parse_row(row)
                if twin is not None and tf.get("pivot") == "center":
                    tf = dict(tf, pivot=tuple(center_of(obj)))   # same pivot for both keeps them together
                run_tf(obj, tf, 1.0)
                if twin is not None:
                    run_tf(twin, tf, 1.0)
            except Exception as exc:
                print(f"{e.name}: transform {','.join(row)} failed: {exc}")
        e.obj, e.twin_obj = obj, twin

    def unique_name(self, base):
        names = {e.name for e in self.entries}
        if base not in names:
            return base
        i = 2
        while f"{base}_{i}" in names:
            i += 1
        return f"{base}_{i}"

    def refresh(self):
        """Rebuild tree + combobox choices + grid size, then redraw."""
        sel = self.selected
        opened = self.__dict__.setdefault("_open_kinds", {})   # type folders stay open/closed
        if self.tree.exists("scene"):
            for k in self.tree.get_children("scene"):
                opened[k[2:]] = bool(self.tree.item(k, "open"))
        self.tree.delete(*self.tree.get_children())
        self.tree.insert("", "end", "scene", text="Scene (scene3d.csv)", open=True)
        kinds = {}
        for i, e in enumerate(self.entries):
            kinds.setdefault(e.kind, []).append(i)
        for kind in sorted(kinds):           # one folder per type, scene order inside
            label = (kind[:-2] if kind.endswith("3d") else kind) + "s"
            self.tree.insert("scene", "end", f"k:{kind}", text=f"{label} ({len(kinds[kind])})",
                             open=opened.get(kind, False))
            for i in kinds[kind]:
                e = self.entries[i]
                extra = ((" +twin" if e.twin else "") + (f" hollow {fmt(e.hollow[0])}" if e.hollow else "")
                         + (f" {e.csg[0]}:{e.csg[1]}" if e.csg else ""))
                self.tree.insert(f"k:{kind}", "end", f"s{i}", text=e.name, values=(e.kind + extra, e.group))
        self.cb_csg_target["values"] = [e.name for e in self.entries] + \
            ["@" + g for g in sorted({g for e in self.entries for g in gsegs(e)})]
        self._sync_groups()
        self.cb_group["values"] = sorted(self.groups)
        if self.script_objs:
            self.tree.insert("", "end", "script", text="Script run (not saved)", open=True)
            for i, (name, obj) in enumerate(self.script_objs):
                self.tree.insert("script", "end", f"r{i}", text=name, values=(type(obj).__name__,))
        self.cb_pivot["values"] = ["default", "center", "origin", "point"] + \
            [f"obj:{e.name}" for e in self.entries]
        self.cb_axis["values"] = ["custom"] + [e.name for e in self.entries
                                               if e.kind in ("line3d", "vector3d")]
        self.selected = None
        if sel and sel[0] == "s":
            for i, e in enumerate(self.entries):
                if e is sel[1]:
                    self.tree.selection_set(f"s{i}")
                    self.tree.see(f"s{i}")
                    self.selected = sel
        self.selected = self.selected or (sel if sel and sel[0] == "d" else None)
        self.tree_director()
        self.update_grid()
        self.redraw()

    def tree_director(self):
        """Camera director's keys, aims and lights as tree rows (while the director is open)."""
        if self.tree.exists("director"):
            self.tree.delete("director")
        d = self.director
        if d is None or not d.winfo_exists():
            if self.selected and self.selected[0] == "d":
                self.selected = None
            return
        self.tree.insert("", "end", "director", text="Camera director", open=True)
        for iid, label, kind in d.tree_items():
            self.tree.insert("director", "end", iid, text=label, values=(kind,))
        if self.selected and self.selected[0] == "d":
            if self.tree.exists(self.selected[1]):
                self.tree.selection_set(self.selected[1])
            else:
                self.selected = None

    def dir_item(self):
        """The selected director tree item (iid), or None."""
        if self.selected and self.selected[0] == "d" and self.director is not None:
            return self.selected[1]
        return None

    def sel_entry(self):
        if self.selected and self.selected[0] == "s":
            return self.selected[1]
        print("Select a scene object first (script objects: use 'Keep script objs').")
        return None

    def on_select(self, _event=None):
        self.preview_refresh()                       # (runs when idle) highlight it in the preview too
        iid = (self.tree.selection() or [""])[0]
        if iid.startswith("s") and iid != "scene" and iid != "script":
            e = self.entries[int(iid[1:])]
            self.selected = ("s", e)
            self.v_name.set(e.name)
            self.v_c1.set(e.c1)
            self.v_c2.set(e.c2)
            self._show_material(e)
            if e.group:                                 # outermost; pick an inner one to work on that
                self.v_group.set(gsegs(e)[0])
                self.cb_group["values"] = gsegs(e) + [g for g in sorted(self.groups) if g not in gsegs(e)]
            self._track_pick_order()
            self.v_twin.set(bool(e.twin))
            if e.twin:
                self.v_twin_pct.set(fmt(e.twin[0]))
                self.v_twin_axis.set(e.twin[1])
                self.v_twin_flip.set(e.twin[2])
            self.v_csg_op.set(e.csg[0] if e.csg else "none")
            self.v_csg_target.set(e.csg[1] if e.csg else "")
            self.v_hollow.set(bool(e.hollow))
            if e.hollow:
                self.v_hollow_t.set(num(e.hollow[0]))
                self.v_hollow_open.set(e.hollow[1])
            if e.obj is not None:
                c = self.group_center(self.group_entries(e))
                for v, val in zip(self.v_to, c):
                    v.set(fmt(val))
            self.lb_tf.delete(0, "end")
            for row in e.transforms:
                self.lb_tf.insert("end", ",".join(row))
            if e.obj is not None:
                print(f"{e.name}: {e.obj}")
            if self._props is not None:
                self._fill_props()
        elif iid.startswith("r") and iid[1:].isdigit():
            idx = int(iid[1:])
            self.selected = ("r", idx)
            name, obj = self.script_objs[idx]
            print(f"[script] {name}: {obj}")
        elif iid.startswith("d:") and self.director is not None:
            if self.selected == ("d", iid):
                return                                  # tree rebuilt and re-selected it
            self.selected = ("d", iid)
            self.director.select_item(iid)
            for v, val in zip(self.v_to, self.director.item_center(iid)):
                v.set(fmt(val))
            self.lb_tf.delete(0, "end")
            self.lb_tf.insert("end", "director item: Move / Center / Scale / Rotate / Undo work here")
            if iid[2:].startswith(("cam", "aim")):
                self.view_fill()                        # its eye / aim / fov into View / camera key
            print(f"{self.tree.item(iid, 'text')}: center ({', '.join(fmt(v) for v in self.director.item_center(iid))})")
        else:
            self.selected = None
        self.redraw()

    # -------------------------------------------------------------- editing
    def add_dialog(self):
        label = self.v_add.get()
        if label == "Lathe":                    # always a new one
            if self.lathe_tool is not None:
                self.lathe_tool.close()
            self.lathe_tool = LatheTool(self, None)
            return
        spec = ADD_SPECS[label]
        kind = {"Point": "point3d", "Line": "line3d", "Vector": "vector3d", "Plane": "plane3d",
                "Square": "square3d", "Cube": "cube3d", "Sphere": "sphere3d",
                "Circle": "circle3d", "Cylinder": "cylinder3d", "Cone": "cone3d",
                "Bend": "curvedcylinder3d", "CurvedTorus": "curvedtorus3d"}.get(label)   # solids: from add_nums
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Add {label}")
        dlg.transient(self.root)
        frm = ttk.Frame(dlg, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)
        v_name = tk.StringVar(value=self.unique_name(f"{label.lower()}1"))
        ttk.Label(frm, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v_name, width=16).grid(row=0, column=1, columnspan=3, sticky="we")
        fields = {}
        for r, (text, key, ftype, default) in enumerate(spec, 1):
            ttk.Label(frm, text=text).grid(row=r, column=0, sticky="w", pady=1)
            if ftype == "xyz":
                vs = [tk.StringVar(value=str(d)) for d in default]
                for i, v in enumerate(vs):
                    ttk.Entry(frm, textvariable=v, width=6).grid(row=r, column=1 + i)
                fields[key] = ("xyz", vs)
            elif ftype == "color":
                v = tk.StringVar(value=default)
                ttk.Entry(frm, textvariable=v, width=12).grid(row=r, column=1, columnspan=2, sticky="we")
                ttk.Button(frm, text="...", width=3, command=lambda v=v: self.pick(v, dlg)).grid(row=r, column=3)
                fields[key] = ("color", v)
            elif ftype == "bendsrc":       # existing bends to continue from
                names = ["(none)"] + [e.name for e in self.entries
                                      if CurvedCylinder3d and isinstance(e.obj, CurvedCylinder3d)]
                cur = self.selected[1].name if self.selected and self.selected[0] == "s" else ""
                v = tk.StringVar(value=cur if cur in names else "(none)")
                ttk.Combobox(frm, textvariable=v, values=names, width=14, state="readonly").grid(
                    row=r, column=1, columnspan=3, sticky="w")
                fields[key] = ("choice", v)
            elif isinstance(ftype, tuple):
                v = tk.StringVar(value=default)
                ttk.Combobox(frm, textvariable=v, values=ftype, width=max(6, max(map(len, ftype))),
                             state="readonly").grid(
                    row=r, column=1, sticky="w")
                fields[key] = ("choice", v)
            else:
                v = tk.StringVar(value=str(default))
                ttk.Entry(frm, textvariable=v, width=8).grid(row=r, column=1, sticky="w")
                fields[key] = ("num", v)

        def ok():
            try:
                vals = {}
                for key, (ftype, v) in fields.items():
                    if ftype == "xyz":
                        vals[key] = self._floats(v)
                    elif ftype == "num":
                        vals[key] = float(v.get()) if v.get().strip() else None
                    else:
                        vals[key] = v.get().strip()
                    if ftype == "color" and vals[key] and not self.valid_color(vals[key]):
                        raise ValueError(f"unknown color '{vals[key]}'")
                name = v_name.get().strip() or label.lower()
                if any(e.name == name for e in self.entries):
                    raise ValueError(f"name '{name}' already used")
                src = vals.get("src", "(none)")
                if label == "Bend" and src not in ("", "(none)"):
                    # Continue smoothly off the end of an existing bend; store the new bend's own geometry.
                    prev = next(o.obj for o in self.entries if o.name == src)
                    nxt = prev.make_next(math.radians(vals["a"]), math.radians(vals["tw"] or 0),
                                         bend_radius=vals["R"], tube_radius=vals["r"])
                    nums = entry_from_obj(name, nxt).nums
                elif label in solids3d.ADD_SPECS:
                    kind_now, nums = solids3d.add_nums(label, vals)
                else:
                    nums = add_nums(label, vals)
                e = Entry(kind or kind_now, name, vals.get("c1", ""), vals.get("c2", ""), nums)
                self.rebuild(e)
                if e.obj is None:
                    return
            except (ValueError, TypeError) as exc:
                print(f"Add {label}: {exc}")
                return
            self.entries.append(e)
            self.save()
            self.selected = ("s", e)
            self.refresh()
            print(f"Added {name}: {e.obj}")
            dlg.destroy()

        bar = ttk.Frame(frm)
        bar.grid(row=len(spec) + 1, column=0, columnspan=4, pady=(8, 0))
        ttk.Button(bar, text="Add", command=ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT)
        dlg.bind("<Return>", lambda _e: ok())

    # ------------------------------------------------------ properties editor
    def open_props(self):
        """One Properties window; it follows the tree selection while open."""
        if not (self.selected and self.selected[0] == "s"):
            return
        if self.selected[1].kind == "lathe3d":     # its properties are the profile: use the Lathe tool
            self.open_lathe()
            return
        if self._props is None:
            dlg = tk.Toplevel(self.root)
            proc = getattr(self, "_ti_proc", None)
            if proc is None or proc.poll() is not None:
                dlg.transient(self.root)       # not over the preview: a minimized viewer would hide it
            body = ttk.Frame(dlg, padding=8)
            body.pack(fill=tk.BOTH, expand=True)
            bar = ttk.Frame(dlg, padding=(8, 0, 8, 8))
            bar.pack(fill=tk.X)
            ttk.Button(bar, text="Apply", command=self._apply_props).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Reload", command=self._fill_props).pack(side=tk.LEFT)
            ttk.Button(bar, text="Close", command=self._close_props).pack(side=tk.RIGHT)
            dlg.bind("<Return>", lambda _e: self._apply_props())
            dlg.protocol("WM_DELETE_WINDOW", self._close_props)
            self._props = (dlg, body, {})
        self._fill_props()
        self._props[0].lift()

    def _close_props(self):
        if self._props is not None:
            self._props[0].destroy()
            self._props = None

    def _fill_props(self):
        """(Re)build the fields from the selected object's current geometry."""
        dlg, body, fields = self._props
        for w in body.winfo_children():
            w.destroy()
        fields.clear()
        e = self.selected[1] if self.selected and self.selected[0] == "s" else None
        if e is None or e.obj is None:
            dlg.title("Properties")
            ttk.Label(body, text="Select a scene object").grid(row=0, column=0)
            return
        dlg.title(f"Properties: {e.name}")
        self._props_entry = e
        ttk.Label(body, text=f"{e.name}  ({e.kind})").grid(row=0, column=0, columnspan=4, sticky="w")
        spec = prop_spec(e)
        for r, (text, key, ftype, val) in enumerate(spec, 1):
            if ftype == "bool":
                v = tk.BooleanVar(value=val)
                ttk.Checkbutton(body, text=text, variable=v).grid(row=r, column=0, columnspan=4, sticky="w")
                fields[key] = (ftype, v, val, val)
                continue
            ttk.Label(body, text=text).grid(row=r, column=0, sticky="w", pady=1)
            if ftype == "xyz":
                vs = [tk.StringVar(value=num(c)) for c in val]
                for i, v in enumerate(vs):
                    ttk.Entry(body, textvariable=v, width=9).grid(row=r, column=1 + i)
                fields[key] = (ftype, vs, [s.get() for s in vs], val)
            else:
                v = tk.StringVar(value=str(int(val)) if ftype == "int" else num(val))
                ttk.Entry(body, textvariable=v, width=9).grid(row=r, column=1, sticky="w")
                fields[key] = (ftype, v, v.get(), val)
        if e.transforms:
            ttk.Label(body, text=f"Apply bakes its {len(e.transforms)} transform(s) into the shape",
                      foreground="#888").grid(row=len(spec) + 1, column=0, columnspan=4, sticky="w")

    def _apply_props(self):
        if self._props is None:
            return
        e = getattr(self, "_props_entry", None)
        if e is None or e not in self.entries or e.obj is None:
            return
        vals, changed = {}, set()
        try:
            for key, (ftype, v, shown, exact) in self._props[2].items():
                if ftype == "bool":
                    vals[key] = v.get()
                elif ftype == "xyz":       # untouched boxes keep the exact (unrounded) value
                    texts = [s.get().strip() for s in v]
                    vals[key] = tuple(ex if t == sh else float(t) for t, sh, ex in zip(texts, shown, exact))
                    changed |= {key} if texts != shown else set()
                else:
                    t = v.get().strip()
                    vals[key] = exact if t == shown else (int(t) if ftype == "int" else float(t))
                    changed |= {key} if t != shown else set()
            nums = prop_nums(e, vals, changed)
            test = Entry(e.kind, e.name, e.c1, e.c2, nums)
            test.obj = build(test)
        except (ValueError, TypeError, np.linalg.LinAlgError) as exc:
            print(f"Properties {e.name}: {exc}")
            return
        moved = self._carry_chain(e, test.obj) if vals.get("carry") else []
        e.nums, e.transforms, e.obj = test.nums, [], test.obj
        if e.twin:                             # the first's flip is baked into nums now
            e.twin = e.twin[:2] + (False,)
            self.rebuild(e)
        self.save()
        self.refresh()
        self._fill_props()
        extra = f" (+ moved {', '.join(f.name for f in moved)})" if moved else ""
        print(f"{e.name} updated{extra}: {e.obj}")

    def _carry_chain(self, e, new_obj):
        """Bends that continue off the end of e: move them rigidly so they stay attached
        to new_obj's end. Returns the entries moved."""
        old = e.obj

        def end_frame(b):
            return (np.array(xyz(b.spine_point(1.0)), float),
                    np.column_stack([b.tangent(1.0), b.radial_dir(1.0), b.get_norm()]))

        def followers(b, seen):
            p, f = end_frame(b)
            out = []
            for o in self.entries:
                if o in seen or o.kind != "curvedcylinder3d" or o.obj is None:
                    continue
                if (np.linalg.norm(np.subtract(xyz(o.obj.get_spine_start()), p)) < 1e-6
                        and np.dot(o.obj.tangent(0.0), f[:, 0]) > 0.9999):
                    seen.add(o)
                    out += [o] + followers(o.obj, seen)
            return out

        chain = followers(old, {e})
        if not chain:
            return []
        p0, f0 = end_frame(old)
        p1, f1 = end_frame(new_obj)
        rot = f1 @ f0.T                        # old end frame -> new end frame
        for o in chain:
            c =p1 + rot @ (np.array(xyz(o.obj.get_bend_center())) - p0)
            s = p1 + rot @ (np.array(xyz(o.obj.get_spine_start())) - p0)
            nrm = rot @ np.array(o.obj.get_norm())
            o.nums = list(c) + list(s) + [o.obj.get_tube_radius(), math.degrees(o.obj.get_angle())] + list(nrm)
            o.transforms = []
            self.rebuild(o)
        return chain

    def rename(self):
        e = self.sel_entry()
        if e is None:
            return
        new = self.v_name.get().strip()
        if not new or any(o.name == new and o is not e for o in self.entries):
            print(f"Rename: '{new}' is empty or already used")
            return
        for o in self.entries:                 # csg links follow the new name
            if o.csg and o.csg[1] == e.name:
                o.csg = (o.csg[0], new) + tuple(o.csg[2:])
        e.name = new
        self.rebuild(e)
        self.save()
        self.refresh()

    def apply_twin(self):
        e = self.sel_entry()
        if e is None:
            return
        if not self.v_twin.get():
            e.twin = None
        elif e.kind == "plane3d":
            print("Twin: planes are endless, nothing to mirror")
            return
        else:
            try:
                lift = min(100.0, max(1.0, float(self.v_twin_pct.get())))
            except ValueError:
                print("Twin: lift % must be a number 1-100")
                return
            e.twin = (lift, self.v_twin_axis.get(), bool(self.v_twin_flip.get()))
        self.rebuild(e)
        self.save()
        self.refresh()
        print(f"{e.name}: " + (f"twin lifted {fmt(e.twin[0])}% along {e.twin[1]}"
                               + (", first flipped" if e.twin[2] else "") if e.twin else "twin removed"))

    def apply_csg(self):
        e = self.sel_entry()
        if e is None:
            return
        op, tgt = self.v_csg_op.get(), self.v_csg_target.get()
        g = self.group_level(e) if self.v_group_mode.get() else ""   # the whole group is the tool
        tools = self.group_entries(e) if g else [e]
        own = {o.name for o in tools} | ({"@" + g} if g else set())
        if op != "none" and (not tgt or tgt in own or not self.csg_target_ok(tgt)):
            print("CSG: pick another object (or @group) as the target")
            return
        for o in tools:
            o.csg = None if op == "none" else (op, tgt, g)
        self.save()
        self.refresh()
        who = f"group {g}" if g else e.name
        if op != "none":
            print(f"{who} {op}s {tgt}" + (" - shown as a dashed wire here, the render does the real cut"
                                          if op != "combine" else " - merged into one solid in the render"))
        else:
            print(f"{who}: CSG removed")

    def csg_target_ok(self, tgt):
        if tgt.startswith("@"):
            return any(tgt[1:] in gsegs(o) for o in self.entries)
        return any(o.name == tgt for o in self.entries)

    def is_cutter(self, e):
        """Cut / overlap tools draw as dashed wire only (the viewer can't carve faces)."""
        return bool(e.csg and e.csg[0] in ("cut", "overlap") and self.csg_target_ok(e.csg[1]))

    def apply_hollow(self):
        e = self.sel_entry()
        if e is None:
            return
        if not self.v_hollow.get():
            e.hollow = None
        else:
            try:
                t = float(self.v_hollow_t.get())
                if t <= 0:
                    raise ValueError
            except ValueError:
                print("Hollow: wall thickness must be a number > 0")
                return
            hollow = (t, self.v_hollow_open.get())
            try:
                for o in (e.obj, e.twin_obj):
                    if o is not None:
                        hollow_inner(o, *hollow)        # check it fits before keeping it
            except (ValueError, TypeError) as exc:
                print(f"Hollow: {exc}")
                return
            e.hollow = hollow
        self.save()
        self.refresh()
        self.redraw()
        print(f"{e.name}: " + (f"hollow, walls {num(e.hollow[0])}, open {e.hollow[1]}"
                               " - inner wall dashed here, the render cuts it out" if e.hollow else "solid again"))

    def apply_colors(self):
        e = self.sel_entry()
        if e is None:
            return
        c1, c2 = self.v_c1.get().strip(), self.v_c2.get().strip()
        for c in (c1, c2):
            if c and not self.valid_color(c):
                print(f"Unknown color '{c}'")
                return
        es = self.group_entries(e)             # whole group: recolor every member
        for o in es:
            o.c1, o.c2 = c1, c2
            self.rebuild(o)
        self._sync_groups()
        self.save()
        self.redraw()
        print(f"group {self.group_level(e)} ({len(es)} objects): colors {c1} {c2}" if len(es) > 1
              else f"{e.name}: {e.obj}")

    # ---- POV-Ray materials:  group -> {shown name: spec}  (spec format: pov_export.material)
    def _load_pov_lib(self):
        # worker thread: only hand the result over; Tk calls (after, widgets) stay on the main thread
        self._pov_lib_ready = pov_export.library()

    def _poll_pov_lib(self):
        lib = self.__dict__.pop("_pov_lib_ready", None)
        if lib is None:
            self.root.after(200, self._poll_pov_lib)
            return
        self.pov_lib = lib
        self._mat_groups()
        if self.selected and self.selected[0] == "s":
            self._show_material(self.selected[1])

    def _mat_choices(self):
        ch = {"Color": {"own color": ""},
              "Studio": {k: f"studio:{k}" for k in pov_export.STUDIO}}
        for grp, rows in self.pov_lib.items():
            ch[grp] = {f"{name} ({kind[:3]})": f"lib:{inc}:{kind}:{name}" for name, kind, inc in rows}
        imgs = sorted(f for f in os.listdir(POV_DIR) if os.path.splitext(f)[1].lower()
                      in pov_export.IMAGE_TYPES and not f.startswith("render")) if os.path.isdir(POV_DIR) else []
        ch["Image"] = {f: f"image:{f}" for f in imgs}
        return ch

    def _mat_groups(self):
        self.mat_choices = self._mat_choices()
        self.cb_mat_grp["values"] = list(self.mat_choices)
        self._mat_group_changed(keep=True)

    def _mat_group_changed(self, keep=False):
        names = list(self.mat_choices.get(self.v_mat_grp.get(), {}))
        self.cb_mat_name["values"] = names
        if not (keep and self.v_mat_name.get() in names):
            self.v_mat_name.set(names[0] if names else "")

    def _show_material(self, e):
        for grp, names in self.mat_choices.items():
            for shown, spec in names.items():
                if spec == e.mat:
                    self.v_mat_grp.set(grp)
                    self._mat_group_changed()
                    self.v_mat_name.set(shown)
                    self.v_mat_scale.set(fmt(e.mat_scale))
                    return
        self.v_mat_grp.set("Color")             # unknown spec (library not loaded yet): show own color
        self._mat_group_changed()
        self.v_mat_scale.set(fmt(e.mat_scale))

    def apply_material(self):
        e = self.sel_entry()
        if e is None:
            return
        try:
            scale = float(self.v_mat_scale.get())
        except ValueError:
            print(f"Tex scale '{self.v_mat_scale.get()}' is not a number")
            return
        mat = self.mat_choices.get(self.v_mat_grp.get(), {}).get(self.v_mat_name.get(), "")
        es = self.group_entries(e)
        for o in es:
            o.mat, o.mat_scale = mat, scale
        self.save()
        who = f"group {self.group_level(e)} ({len(es)} objects)" if len(es) > 1 else e.name
        print(f"{who}: material {mat or 'own color'}" + (f", scale {fmt(scale)}" if scale != 1 else ""))

    def pick_image(self):
        path = filedialog.askopenfilename(title="Image map", filetypes=[
            ("Images", " ".join("*" + x for x in pov_export.IMAGE_TYPES)), ("All files", "*.*")])
        if not path:
            return
        os.makedirs(POV_DIR, exist_ok=True)
        dest = os.path.join(POV_DIR, os.path.basename(path))
        if os.path.abspath(path) != os.path.abspath(dest):
            shutil.copy(path, dest)            # POV-Ray reads it from the render folder
        self._mat_groups()
        self.v_mat_grp.set("Image")
        self._mat_group_changed()
        self.v_mat_name.set(os.path.basename(path))
        self.apply_material()

    # --------------------------------------------------------------- groups
    def _sync_groups(self):
        """Rebuild the ObjGroup3d lists from the entries' group tags (objects get re-made on rebuild)."""
        self.groups = {}
        for e in self.entries:
            if e.obj is not None:
                for g in gsegs(e):                     # nested: one ObjGroup3d per level
                    self.groups.setdefault(g, class3d.ObjGroup3d(g)).addobj(e.obj)

    def group_level(self, e):
        """Which of e's groups 'whole group' works on: the one named in the Group box, else
        the outermost (select an object, pick its inner group in the box to work on that)."""
        segs = gsegs(e)
        lvl = self.v_group.get().strip()
        return lvl if lvl in segs else (segs[0] if segs else "")

    def group_entries(self, e):
        """e plus its group mates (e first) when group mode is on, else just e."""
        if not (e.group and self.v_group_mode.get()):
            return [e]
        g = self.group_level(e)
        return [e] + [o for o in self.entries if o is not e and g in gsegs(o) and o.obj is not None]

    def selection_sets(self):
        """Selected entries in pick order, each grown to its whole group (group mode), no repeats."""
        order = [self.entries[int(i[1:])] for i in getattr(self, "_pick_order", [])
                 if self.tree.exists(i) and i[1:].isdigit()]
        sets, seen = [], set()
        for e in order:
            if id(e) in seen:
                continue
            es = self.group_entries(e)
            seen |= {id(o) for o in es}
            sets.append(es)
        return sets

    def _track_pick_order(self):
        """Remember the order objects were clicked: Align moves the later ones to the first."""
        sel = [i for i in self.tree.selection() if i.startswith("s") and i[1:].isdigit()]
        old = [i for i in getattr(self, "_pick_order", []) if i in sel]
        self._pick_order = old + [i for i in sel if i not in old]

    @staticmethod
    def group_center(es):
        """Middle of the box around the members' centers (one object: its own center)."""
        cs = np.array([entry_center(o) for o in es if o.obj is not None], float)
        if len(cs) == 0:
            return (0.0, 0.0, 0.0)
        return tuple(float(v) for v in (cs.min(axis=0) + cs.max(axis=0)) / 2)

    def _selected_entries(self):
        return [self.entries[int(i[1:])] for i in self.tree.selection()
                if i.startswith("s") and i[1:].isdigit()]

    def tag_group(self):
        name = self.v_group.get().strip().replace(",", "_").replace("/", "_")
        es = [o for s in self._sets_of_selection() for o in s]
        if not name or not es:
            print("Tag: type a group name and select objects (Ctrl/Shift-click for several)")
            return
        for e in es:                       # already grouped: the new group goes around it (nested)
            if name not in gsegs(e):
                e.group = "/".join([name] + gsegs(e))
        self.save()
        self.refresh()
        print(f"Group {name}: {', '.join(e.name for e in self.entries if name in gsegs(e))}")
        print(self.groups[name])

    def _sets_of_selection(self):
        """Tree selection grown to whole groups when group mode is on."""
        self._track_pick_order()
        return self.selection_sets()

    def untag_group(self):
        """Take the selection out of its outermost group (or the one named in the Group box)."""
        es = [o for s in self._sets_of_selection() for o in s if o.group]
        for e in es:
            g = self.group_level(e)
            e.group = "/".join(s for s in gsegs(e) if s != g)
            print(f"{e.name}: removed from group {g}" + (f", still in {e.group}" if e.group else ""))
        if es:
            self.save()
            self.refresh()

    def _queue_tf(self, e, tf, animate=True):
        """Animate tf on entry e (and its group), then store it under each object and save.
        pivot "group" = the group's middle as it is when the job runs (after earlier queued ones)."""
        def job():
            es = [o for o in self.group_entries(e) if o.obj is not None]   # read when the job starts
            if not es:
                return
            t = dict(tf)
            if t.get("pivot") == "group":
                t["pivot"] = tuple(self.group_center(es))
            if len(es) > 1:
                if t.get("pivot") == "center" or t["op"] == "scale":   # one shared pivot keeps the group rigid
                    t["pivot"] = tuple(self.group_center(es))
                print(f"group {e.group} ({len(es)} objects).{tf_text(t)}")
            else:
                if es[0].twin_obj is not None and t.get("pivot") == "center":
                    t["pivot"] = tuple(entry_center(es[0]))       # turn the pair about its middle
                print(f"{e.name}.{tf_text(t)}")
            objs = [o.obj for o in es] + [o.twin_obj for o in es if o.twin_obj is not None]
            if animate:
                yield from self.anim_transform(objs, t)
            else:                                # already seen happen (Taichi preview drag): one step
                for o in objs:
                    run_tf(o, t, 1.0)
            for o in es:
                o.transforms.append(tf_to_row(t))
                self.rebuild(o)              # exact one-shot result, same as next load
            self._sync_groups()
            self.save()
            if self.selected and self.selected[1] is e:
                self.lb_tf.insert("end", ",".join(e.transforms[-1]))
                for v, val in zip(self.v_to, self.group_center(es)):
                    v.set(fmt(val))
            for o in es:
                print(f"{o.name} now: {o.obj}")
        self.enqueue(job())

    def move_by(self):
        it = self.dir_item()
        e = None if it else self.sel_entry()
        if e is None and it is None:
            return
        try:
            d = self._floats(self.v_mv)
        except ValueError:
            print("Move: enter three numbers")
            return
        if it:
            self.director.transform_item(it, lambda p: p + np.array(d))
            self._dir_done(it)
            return
        self._queue_tf(e, {"op": "move", "d": d})

    def _dir_done(self, it):
        """After a panel edit of a director item: refresh Center-to and report."""
        c = self.director.item_center(it)
        for v, val in zip(self.v_to, c):
            v.set(fmt(val))
        print(f"{self.tree.item(it, 'text')} now at ({', '.join(fmt(v) for v in c)})")

    def dir_look(self):
        """Look at it: swing the 3D view to center on the selection (any object or director item)."""
        it = self.dir_item()
        if it:
            c = self.director.item_center(it)
        else:
            e = self.sel_entry()
            if e is None or e.obj is None:
                return
            c = self.group_center(self.group_entries(e))
        self.target = tuple(float(v) for v in c)
        self.redraw()

    def dir_through(self):
        it = self.dir_item()
        if it is None:
            print("View through: select a Camera key in the tree (open the Director first)")
            return
        self.director.look_through(it)

    def dir_from_view(self):
        it = self.dir_item()
        if it is None:
            print("Camera = 3D view: select a Camera key in the tree (open the Director first)")
            return
        self.director.key_from_view(it)
        self._dir_done(it)

    # ------------------------------------------------------ align / replicate
    def align(self):
        """Move the 2nd, 3rd... picked objects (or groups) onto the first one picked."""
        sets = self._sets_of_selection()
        if len(sets) < 2:
            print("Align: click the object to align TO first, then Ctrl-click the one(s) to move")
            return
        axes = ["XYZ".index(c) for c in self.v_align_ax.get().upper() if c in "XYZ"]
        how = self.v_align_how.get()
        alo, ahi = bbox(sets[0])
        print(f"Align {self.v_align_ax.get()} {how} to {sets[0][0].name}")
        for s in sets[1:]:
            lo, hi = bbox(s)
            d = [0.0, 0.0, 0.0]
            for k in axes:
                if how == "low sides":
                    d[k] = alo[k] - lo[k]
                elif how == "high sides":
                    d[k] = ahi[k] - hi[k]
                elif how == "stack on" and k == axes[-1]:
                    d[k] = ahi[k] - lo[k]          # sits on top of the last axis named
                else:
                    d[k] = (alo[k] + ahi[k]) / 2 - (lo[k] + hi[k]) / 2
            d = tuple(float(v) for v in d)
            if how == "stack on":                  # the next one stacks on this one
                alo, ahi = lo + d, hi + d
            if any(abs(v) > 1e-9 for v in d):
                self._queue_tf(s[0], {"op": "move", "d": d})
            else:
                print(f"{s[0].name}: already aligned")

    @staticmethod
    def _fresh(base, taken):
        """base_2, base_3... (any _N already on the end is dropped first); claims it in taken."""
        b, k = re.sub(r"_\d+$", "", base), 2
        while f"{b}_{k}" in taken:
            k += 1
        taken.add(f"{b}_{k}")
        return f"{b}_{k}"

    def replicate(self):
        """Copy the selection (whole groups in group mode, CSG/twin/hollow and all) n times, step apart."""
        ids = {id(o) for s in self._sets_of_selection() for o in s}
        src = [e for e in self.entries if id(e) in ids]
        if not src:
            print("Replicate: select an object (whole group on to copy the group)")
            return
        try:
            n = max(1, min(500, int(float(self.v_rep_n.get()))))
            step = np.array(self._floats(self.v_rep_step), float)
        except ValueError:
            print("Replicate: copies and step need numbers")
            return
        # groups wholly inside the selection get new names per copy; outer ones are shared
        segs = list(dict.fromkeys(g for e in src for g in gsegs(e)))
        whole = [g for g in segs if all(id(o) in ids for o in self.entries if g in gsegs(o))]
        gtaken = {g for e in self.entries for g in gsegs(e)}
        ntaken = {e.name for e in self.entries}
        new = []
        for i in range(1, n + 1):
            smap = {g: self._fresh(g, gtaken) for g in whole}
            nmap = {e.name: self._fresh(e.name, ntaken) for e in src}
            for e in src:
                c = copy.copy(e)
                c.name = nmap[e.name]
                c.nums = list(e.nums)
                c.transforms = [list(r) for r in e.transforms] + \
                    [tf_to_row({"op": "move", "d": tuple(float(v) for v in step * i)})]
                c.group = "/".join(smap.get(g, g) for g in gsegs(e))
                if e.csg:
                    op, tgt, g = e.csg
                    tgt = "@" + smap.get(tgt[1:], tgt[1:]) if tgt.startswith("@") else nmap.get(tgt, tgt)
                    c.csg = (op, tgt, smap.get(g, g) if g else "")
                c.obj = c.twin_obj = None
                try:                               # the built source, moved: same as replaying every step
                    if e.obj is None:
                        raise ValueError
                    mv = {"op": "move", "d": tuple(float(v) for v in step * i)}
                    c.obj = copy.deepcopy(e.obj)
                    run_tf(c.obj, mv, 1.0)
                    if e.twin_obj is not None:
                        c.twin_obj = copy.deepcopy(e.twin_obj)
                        run_tf(c.twin_obj, mv, 1.0)
                except Exception:                  # noqa: BLE001
                    self.rebuild(c)
                new.append(c)
        self.entries += new
        outer = self.v_rep_group.get().strip().replace(",", "_").replace("/", "_")
        if outer:                                  # wrap originals + copies in one group
            for e in src + new:
                if outer not in gsegs(e):
                    e.group = "/".join([outer] + gsegs(e))
        self.save()
        self.refresh()
        print(f"Replicated {len(src)} object(s) x{n}, step ({', '.join(fmt(v) for v in step)})"
              + (f" - new groups {', '.join(sorted({g for c in new for g in gsegs(c)} - set(segs)))}"
                 if whole else "") + (f" - all in group {outer}" if outer else ""))

    # ------------------------------------------------- view / camera key panel
    def _show_view(self, eye, look, fov):
        for vs, p in ((self.v_eye, eye), (self.v_look, look)):
            for v, val in zip(vs, p):
                v.set(fmt(float(val)))
        self.v_fov.set(fmt(round(float(fov), 3)))

    def view_fill(self):
        """Boxes = where the 3D view is (or the selected director camera key)."""
        it = self.dir_item()
        if it and it[2:].startswith(("cam", "aim")):
            d = self.director
            i, ck, ak, fk = d.key_ref(int(it[5:]))
            s = d.shot["segments"][i]
            self._show_view(s[ck], s[ak], s[fk])
            return
        fwd, _l, _r = self._cam_axes()
        look = np.array(self.target, float)
        h = max(self.canvas.winfo_height(), 50)
        self._show_view(look - fwd * self.dist, look,
                        math.degrees(2 * math.atan((h / 2) / (self.scale * self.dist))))

    def _read_view(self):
        try:
            return (np.array(self._floats(self.v_eye), float), np.array(self._floats(self.v_look), float),
                    max(1.0, min(170.0, float(self.v_fov.get()))))
        except ValueError:
            print("View: Eye, Look at and FOV need numbers")
            return None

    def view_go(self):
        """Stand at Eye looking at Look at with that FOV."""
        v = self._read_view()
        if v is None:
            return
        eye, look, fov = v
        d = look - eye
        dist = float(np.linalg.norm(d))
        if dist < 1e-6:
            print("View: Eye and Look at are the same point")
            return
        self.target, self.dist = tuple(float(c) for c in look), dist
        self.yaw = math.atan2(d[0], d[1])
        self.pitch = max(-1.55, min(1.55, math.asin(max(-1.0, min(1.0, -d[2] / dist)))))
        h = max(self.canvas.winfo_height(), 50)
        self.scale = (h / 2) / math.tan(math.radians(fov) / 2) / dist
        self.redraw()
        print(f"View: eye ({', '.join(fmt(c) for c in eye)}) looking at ({', '.join(fmt(c) for c in look)})")

    def fly_to(self):
        """Jump the 3D view to the selection, framed, same viewing angle."""
        it = self.dir_item()
        if it:
            self.target = tuple(float(v) for v in self.director.item_center(it))
        else:
            e = self.sel_entry()
            if e is None or e.obj is None:
                return
            lo, hi = bbox(self.group_entries(e))
            radius = max(float(np.linalg.norm(hi - lo)) / 2, 1e-3)
            w, h = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
            self.target = tuple(float(v) for v in (lo + hi) / 2)
            self.scale = min(w, h) * 0.42 / radius
            self.dist = radius * 4
        self.redraw()
        if not it:                                 # director key: keep its own numbers in the boxes
            self.view_fill()
        print(f"Flew to ({', '.join(fmt(v) for v in self.target)})")

    def view_set_key(self):
        """Selected director camera key = Eye / Look at / FOV boxes."""
        it = self.dir_item()
        if not it or not it[2:].startswith(("cam", "aim")):
            print("Set camera key: open the Director (F8) and pick a Camera key in the tree")
            return
        v = self._read_view()
        if v is None:
            return
        eye, look, fov = v
        d = self.director
        j = int(it[5:])
        i, ck, ak, fk = d.key_ref(j)
        d._undo.append(copy.deepcopy(d.shot))
        d.set_point(i, ck, list(eye))
        d.set_point(i, ak, list(look))
        d.shot["segments"][i][fk] = fov
        d.set_point_scalar(i, fk)
        d.fill_move()
        d.changed()
        d.goto(d.key_frames()[j])
        print(f"Camera key {j + 1}: eye ({', '.join(fmt(c) for c in eye)}) "
              f"aim ({', '.join(fmt(c) for c in look)}) fov {fmt(fov)}")

    def _dir_rotate(self, it, tf):
        """Rotate a director item's points (same right-hand rule as the library's rotations)."""
        if tf["op"] == "vecrot":
            a, b = (np.array(q, float) for q in tf["axis"])
            k = b - a
        else:
            k = np.array(WORLD_AXIS.get(tf["op"], (0, 0, 1)), float)
            a = np.zeros(3)
        k = k / np.linalg.norm(k)
        piv = tf["pivot"]
        o = self.director.item_center(it) if piv == "center" else (a if piv is None else np.array(piv, float))
        t = math.radians(tf["deg"])
        ct, st = math.cos(t), math.sin(t)

        def turn(p):
            v = p - o
            return o + v * ct + np.cross(k, v) * st + k * float(k @ v) * (1 - ct)
        self.director.transform_item(it, turn)
        self._dir_done(it)

    def move_all(self):
        """Move every object except planes by the Move-by numbers (lift the scene off the floor)."""
        try:
            d = self._floats(self.v_mv)
        except ValueError:
            print("Move all: enter three numbers")
            return
        tf, n = {"op": "move", "d": d}, 0
        for e in self.entries:
            if e.obj is None or e.kind == "plane3d":
                continue
            e.transforms.append(tf_to_row(tf))
            self.rebuild(e)                  # prints if a kind can't move
            n += 1
        self.save()
        self.redraw()
        if self.selected:
            self.on_select()
        print(f"Moved {n} objects by {tuple(fmt(v) for v in d)}")

    def world_width(self):
        """Widest side of the box around every object except infinite planes."""
        es = [e for e in self.entries if e.obj is not None and e.kind != "plane3d"]
        if not es:
            return 0.0
        lo, hi = bbox(es)
        return float(np.max(hi - lo))

    @staticmethod
    def scale_shot(shot, f):
        """Every position in a camera_path shot x f (about the origin, so either axis order)."""
        import director3d
        for seg in shot.get("segments", []):
            for k in director3d.VEC_KEYS:
                if k in seg:
                    seg[k] = [float(v) * f for v in seg[k]]
        for lt in shot.get("lights", []):
            lt["position"] = [float(v) * f for v in lt["position"]]
        if "object" in shot and "position" in shot["object"]:
            shot["object"]["position"] = [float(v) * f for v in shot["object"]["position"]]

    def rescale_world(self):
        """Scale the whole scene about the origin so it is World width across: objects, planes,
        hollow walls, texture sizes, camera director shot and the view all together."""
        try:
            want = float(self.v_world.get())
        except ValueError:
            print("Rescale: World width needs a number")
            return
        now = self.world_width()
        if want <= 0 or now <= 0:
            print("Rescale: need a positive width and something in the scene")
            return
        f = want / now
        row = tf_to_row({"op": "scale", "f": f})          # no pivot = about the origin
        for e in self.entries:
            e.transforms.append(list(row))
            if e.hollow:
                e.hollow = (e.hollow[0] * f,) + tuple(e.hollow[1:])
            if e.mat and not e.mat.startswith("image:"):   # images stretch to fit; others are world-sized
                e.mat_scale *= f
            self.rebuild(e)
        self._sync_groups()
        d = self.director
        if d is not None and d.winfo_exists():
            d._undo.append(copy.deepcopy(d.shot))
            self.scale_shot(d.shot, f)
            d.fill_move()
            d.fill_light()
            d.changed()
        else:                                              # closed: fix the saved shot on disk
            path = os.path.join(POV_DIR, "director_shot.json")
            try:
                with open(path, encoding="utf-8") as fh:
                    shot = json.load(fh)
                self.scale_shot(shot, f)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(shot, fh, indent=2)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        self.target = tuple(float(v) * f for v in self.target)   # same picture, new numbers
        self.dist *= f
        self.scale /= f
        self.save()
        self.refresh()
        if self.selected:
            self.on_select()
        print(f"World rescaled x{fmt(f)}: {fmt(now)} -> {fmt(self.world_width())} wide "
              f"(undo: Rescale back to {fmt(now)})")

    def move_to(self):
        it = self.dir_item()
        e = None if it else self.sel_entry()
        if it is None and (e is None or e.obj is None):
            return
        try:
            target = self._floats(self.v_to)
        except ValueError:
            print("Center to: enter three numbers")
            return
        if it:
            d = np.array(target) - self.director.item_center(it)
            self.director.transform_item(it, lambda p: p + d)
            self._dir_done(it)
            return
        d = tuple(t - c for t, c in zip(target, self.group_center(self.group_entries(e))))
        self._queue_tf(e, {"op": "move", "d": d})

    def scale_by(self):
        it = self.dir_item()
        e = None if it else self.sel_entry()
        if it is None and (e is None or e.obj is None):
            return
        try:
            f = float(self.v_scale.get())
        except ValueError:
            print("Scale: enter a number")
            return
        if it:                                   # about its own center (a whole shot grows / shrinks)
            c = self.director.item_center(it)
            self.director.transform_item(it, lambda p: c + (p - c) * f)
            self._dir_done(it)
            return
        self._queue_tf(e, {"op": "scale", "f": f})

    def rotate(self):
        it = self.dir_item()
        e = None if it else self.sel_entry()
        if it is None and (e is None or e.obj is None):
            return
        try:
            deg = float(self.v_deg.get())
            choice = self.v_pivot.get()
            if choice == "default":
                pivot = None
            elif choice == "center":
                pivot = "center"
            elif choice == "origin":
                pivot = (0.0, 0.0, 0.0)
            elif choice.startswith("obj:"):
                other = next(o for o in self.entries if o.name == choice[4:])
                pivot = center_of(other.obj)
            else:
                pivot = self._floats(self.v_pxyz)
            tf = {"op": self.v_rot.get(), "deg": deg, "pivot": pivot}
            if tf["op"] == "vecrot":
                axis = self.v_axis.get()
                if axis == "custom":
                    a, b = self._floats(self.v_axa), self._floats(self.v_axb)
                else:
                    line = next(o for o in self.entries if o.name == axis).obj
                    a, b = xyz(line.get_start()), xyz(line.get_end())
                if np.allclose(a, b):
                    raise ValueError("axis start and end are the same point")
                tf["axis"] = (a, b)
        except (ValueError, StopIteration) as exc:
            print(f"Rotate: {exc or 'bad input'}")
            return
        if it:
            if tf["pivot"] is None and tf["op"] != "vecrot":
                tf["pivot"] = "center"           # a camera turns about its own eye by default
            self._dir_rotate(it, tf)
            return
        self._queue_tf(e, tf)

    def undo_tf(self):
        if self.dir_item():
            self.director.undo()
            if self.dir_item():                  # still there after the undo
                self._dir_done(self.dir_item())
            return
        e = self.sel_entry()
        if e is None or not e.transforms:
            return
        es = self.group_entries(e)
        if not all(o.transforms and o.transforms[-1] == e.transforms[-1] for o in es):
            es = [e]                         # last step wasn't a group move: undo just this one
        for o in es:
            row = o.transforms.pop()
            self.rebuild(o)
            print(f"{o.name}: removed {','.join(row)}")
        self._sync_groups()
        self.save()
        self.lb_tf.delete("end")
        self.redraw()

    def delete_selected(self):
        it = self.dir_item()
        if it:
            if it.startswith("d:light"):
                self.director.light_i = int(it[7:])
                self.director.delete_light()
                print("Deleted the light")
            else:
                print("Director items: delete moves in the Director window (Moves tab)")
            return
        # everything selected (whole groups in group mode; a type folder = all of that type)
        ids = {id(o) for s in self._sets_of_selection() for o in s}
        for f in self.tree.selection():
            if f.startswith("k:"):
                ids |= {id(self.entries[int(i[1:])]) for i in self.tree.get_children(f)}
        gone = [o for o in self.entries if id(o) in ids]
        if not gone:
            self.sel_entry()                          # prints the "select something" hint
            return
        names = {o.name for o in gone}
        self.entries = [o for o in self.entries if id(o) not in ids]
        for o in self.entries:
            if o.csg and o.csg[1] in names:
                print(f"{o.name}: CSG with {o.csg[1]} removed")
                o.csg = None
        self.selected = None
        self._pick_order = []
        self.save()
        self.refresh()
        print(f"Deleted {', '.join(o.name for o in gone)}" if len(gone) <= 6 else
              f"Deleted {len(gone)} objects ({', '.join(o.name for o in gone[:4])}, ...)")
        print("  (Ctrl+Z brings them back)")

    # ------------------------------------------------------- script running
    def ask_run_script(self):
        path = filedialog.askopenfilename(initialdir=HERE, title="Run a python script",
                                          filetypes=[("Python", "*.py"), ("All", "*.*")])
        if path:
            self.run_script(path)

    def run_script(self, path, replay=True):
        """Run path as __main__, capture prints, record transforms, harvest objects."""
        path = os.path.abspath(path)
        print(f"\n===== running {os.path.basename(path)} =====")
        target = os.path.normcase(path)
        captured = {}

        def prof(frame, event, _arg):
            if (event == "return" and frame.f_code.co_name == "main"
                    and os.path.normcase(os.path.abspath(frame.f_code.co_filename)) == target):
                captured.update(dict(frame.f_locals))

        rec = Recorder()
        rec.install()
        script_dir = os.path.dirname(path)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        g = {}
        try:
            sys.setprofile(prof)
            g = runpy.run_path(path, run_name="__main__")
        except SystemExit:
            pass
        except Exception:
            traceback.print_exc()
        finally:
            sys.setprofile(None)
            rec.uninstall()

        objs, seen = [], set()
        for src in (captured, g):
            for name, val in src.items():
                if not name.startswith("_") and isinstance(val, GEOM_TYPES) and id(val) not in seen:
                    seen.add(id(val))
                    objs.append((name, val))
        objs = self.drop_parts(objs)
        self.script_objs, self.events = objs, rec.events
        print(f"===== done: {len(objs)} objects, {len(rec.events)} transforms recorded =====")
        self.refresh()
        self.fit_view()
        if replay and self.events:
            self.v_show_scene.set(False)
            self.v_show_script.set(True)
            self.replay()

    @staticmethod
    def drop_parts(objs):
        """Hide objects that are building blocks (same instance) of another harvested object."""
        parts = {}
        for name, obj in objs:
            if isinstance(obj, Point3d):
                continue
            kids = []
            if isinstance(obj, Cube3d):
                kids += cube_faces(obj)
            if isinstance(obj, Square3d):
                kids += [obj]
            for sq in [k for k in kids if isinstance(k, Square3d)]:
                kids += [sq._line1, sq._line2, sq._line3, sq._line4]
            kids += points_of(obj)
            for k in kids:
                if k is not obj:
                    parts.setdefault(id(k), name)
        keep = [(n, o) for n, o in objs if id(o) not in parts]
        hidden = [f"{n} (in {parts[id(o)]})" for n, o in objs if id(o) in parts]
        if hidden:
            print("hidden building blocks: " + ", ".join(hidden))
        return keep

    def replay(self):
        if not self.events:
            print("Nothing to replay - run a script that rotates or moves something.")
            return
        self.enqueue(self._replay_job())

    def _replay_job(self):
        names = {id(o): n for n, o in self.script_objs}
        for ev in reversed(self.events):     # rewind everything to the script's start
            for p, c in ev.before:
                p.set_xyz(*c)
        print("----- replaying script transforms -----")
        for _ in range(8):
            yield
        for i, ev in enumerate(self.events, 1):
            name = names.get(id(ev.obj))
            label = name or f"<{type(ev.obj).__name__}>"
            print(f"> [{i}/{len(self.events)}] {label}.{tf_text(ev.tf)}")
            if name is not None:
                self.anim_target = ev.obj
                yield from self.anim_transform(ev.obj, ev.tf)
            for p, c in ev.after:            # land exactly where the script did
                p.set_xyz(*c)
            for _ in range(4 if name else 0):
                yield
        self.anim_target = None
        print("----- replay finished -----")

    def keep_script_objs(self):
        if not self.script_objs:
            print("No script objects to keep.")
            return
        for name, obj in self.script_objs:
            try:
                e = entry_from_obj(self.unique_name(name), obj)
            except Exception as exc:
                print(f"skip {name}: {exc}")
                continue
            self.rebuild(e)
            self.entries.append(e)
        print(f"Kept {len(self.script_objs)} script objects in {os.path.basename(SCENE_FILE)}")
        self.script_objs, self.events = [], []
        self.v_show_scene.set(True)
        self.save()
        self.refresh()

    # ------------------------------------------------------------ animation
    def enqueue(self, gen):
        self.jobs.append(gen)
        if not self.job_running:
            self.job_running = True
            self._tick()

    def _delay(self):
        try:
            return max(1, int(float(self.v_delay.get())))
        except ValueError:
            return 40

    def _tick(self):
        while self.jobs:
            try:
                next(self.jobs[0])
                self.redraw()
                self.root.after(self._delay(), self._tick)
                return
            except StopIteration:
                self.jobs.pop(0)
            except Exception:
                traceback.print_exc()
                self.jobs.pop(0)
        self.job_running = False
        self.anim_target = None
        self.update_grid()
        self.redraw()
        self.root.after(1200, self._clear_overlay)

    def _clear_overlay(self):
        if not self.job_running:
            self.overlay = []
            self.redraw()

    def anim_transform(self, obj, tf):
        """Generator: apply tf in small steps via the library, one frame per step."""
        try:
            step = max(0.5, float(self.v_step.get()))
        except ValueError:
            step = 5.0
        op = tf["op"]
        n = 12 if op in ("move", "scale") else max(1, math.ceil(abs(tf["deg"]) / step))
        objs = obj if isinstance(obj, list) else [obj]   # a group steps all members together
        lead = objs[0]
        pivot = pivot_point(lead, tf)
        start = center_of(lead)
        for _ in range(n):
            for o in objs:
                run_tf(o, tf, 1.0 / n)
            self.overlay = self.make_overlay(lead, tf, pivot, start)
            yield

    def make_overlay(self, obj, tf, pivot, start):
        items = []
        ctr = center_of(obj)
        op = tf["op"]
        if op == "move":
            items.append(("line", start, ctr, "#ff9f43", (4, 3), 1.5))
            items.append(("marker", start, "#ff9f43", "from"))
            return items
        if op == "scale":
            items.append(("marker", (0, 0, 0), "#ff9f43", f"scale x{fmt(tf['f'])}"))
            return items
        if op == "vecrot":
            a, b = tf["axis"]
            d = np.subtract(b, a)
            items.append(("line", a, b, "#e056fd", None, 3))
        else:
            d = WORLD_AXIS.get(op)
        if d is not None:
            d = np.array(d, float) / np.linalg.norm(d)
            L = self.grid_ext
            items.append(("line", tuple(np.add(pivot, -L * d)), tuple(np.add(pivot, L * d)),
                          "#e056fd", (6, 4), 1.2))
        if math.dist(pivot, ctr) > 1e-6:
            items.append(("line", pivot, ctr, "#ff9f43", None, 2))       # tether
        items.append(("marker", pivot, "#ff9f43",
                      "pivot (" + ", ".join(fmt(v) for v in pivot) + ")"))
        return items

    # --------------------------------------------------------------- camera
    def reset_camera(self):
        self.yaw, self.pitch = math.radians(-35), math.radians(25)
        self.scale, self.dist, self.target = 20.0, 60.0, (0.0, 0.0, 0.0)

    def open_director(self):
        import director3d
        if self.director is not None and self.director.winfo_exists():
            self.director.lift()
            return
        self.director = director3d.Director(self)

    def open_lathe(self):
        """Lathe tool: edits the selected lathe, or makes a new one."""
        cur = self.selected[1] if self.selected and self.selected[0] == "s" else None
        cur = cur if cur is not None and cur.kind == "lathe3d" and cur.obj is not None else None
        if self.lathe_tool is not None:
            if self.lathe_tool.entry is cur or cur is None:
                self.lathe_tool.top.lift()
                return
            self.lathe_tool.close()
        self.lathe_tool = LatheTool(self, cur)

    @staticmethod
    def make_entry(kind, name, c1, c2, nums):
        return Entry(kind, name, c1, c2, nums)

    def _drag_start(self, ev, mode):
        self.canvas.focus_set()              # so fly keys reach the canvas
        if mode == "orbit" and self.director is not None and self.director.grab_handle(ev.x, ev.y):
            mode = "handle"                  # dragging a director camera / aim / light handle
        self._drag = (mode, ev.x, ev.y)
        self._press, self._dragged = (ev.x, ev.y), False

    def _release1(self, ev):
        d = self._drag
        if d and d[0] == "handle" and self.director:
            self.director.release_handle()
        elif d and d[0] == "orbit" and not self._dragged:
            self._pick(ev)                   # a click, not an orbit: select what's under it

    def _pick(self, ev):
        """Select the tree row of the object under the cursor (Shift/Ctrl adds to the selection).
        Planes only win when nothing else is there."""
        c = self.canvas
        hit = plane = None
        for item in reversed(c.find_overlapping(ev.x - 3, ev.y - 3, ev.x + 3, ev.y + 3)):  # topmost first
            tags = c.gettags(item)
            iid = next((t[2:] for t in tags if t.startswith("o:")), None)
            if iid is None:
                continue
            if "plane" in tags:
                plane = plane or iid
                continue
            hit = iid
            break
        iid = hit or plane
        if iid is None or not self.tree.exists(iid):
            return
        if ev.state & 0x0005:                # Shift or Ctrl
            self.tree.selection_add(iid)
        else:
            self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)

    def _cam_axes(self):
        """World-space forward (view dir), level forward, and right vectors."""
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        return (np.array((sy * cp, cy * cp, -sp)), np.array((sy, cy, 0.0)),
                np.array((cy, -sy, 0.0)))

    def _fly(self, ev, mode, a, b, c=0):
        if ev.widget.winfo_class() in ("Entry", "TEntry", "Text", "TCombobox", "Listbox", "Spinbox", "TSpinbox"):
            return None                                # typing, not flying
        boost = 4 if ev.state & 0x0001 else 1          # Shift held
        fwd, level, right = self._cam_axes()
        if mode == "move":
            # Step ~40 px at the focus depth; view direction stays fixed.
            step = 40.0 / self.scale * boost
            d = right * a + level * b + np.array((0.0, 0.0, 1.0)) * c
            self.target = tuple(np.array(self.target) + d * step)
        else:
            # Turn the camera in place: keep the eye fixed, swing the focus point.
            eye = np.array(self.target) - fwd * self.dist
            ang = math.radians(3) * boost
            self.yaw += a * ang
            self.pitch = max(-1.55, min(1.55, self.pitch + b * ang))
            fwd, _l, _r = self._cam_axes()
            self.target = tuple(eye + fwd * self.dist)
        self.nav_redraw()
        return "break"

    def _drag_move(self, ev):
        if not self._drag:
            return
        mode, x0, y0 = self._drag
        dx, dy = ev.x - x0, ev.y - y0
        self._drag = (mode, ev.x, ev.y)
        px, py = getattr(self, "_press", (ev.x, ev.y))
        if abs(ev.x - px) + abs(ev.y - py) > 4:
            self._dragged = True
        if mode == "handle":
            self.director.drag_handle(dx, dy, ev.state & 0x0001)
            return
        if mode == "orbit":
            self.yaw -= dx * 0.01
            self.pitch = max(-1.55, min(1.55, self.pitch + dy * 0.01))
        else:
            cy, sy = math.cos(self.yaw), math.sin(self.yaw)
            cp, sp = math.cos(self.pitch), math.sin(self.pitch)
            right = np.array((cy, -sy, 0.0))
            up = np.array((sy * sp, cy * sp, cp))
            self.target = tuple(np.array(self.target) - right * dx / self.scale + up * dy / self.scale)
        self.nav_redraw()

    def _touch_scroll(self, ev):
        """Two-finger trackpad scroll (Tk 9): vertical swipe zooms."""
        try:
            _dx, dy = (float(v) for v in self.root.tk.splitlist(
                self.root.tk.call("tk::PreciseScrollDeltas", ev.delta)))
        except (tk.TclError, ValueError):
            return
        self.zoom(1.01 ** max(-20, min(20, -dy)), ev)

    def _wheel(self, ev):
        # Windows and Tk 9 send +-120 per notch; older Mac Tk sends small counts (+-1..+-10).
        steps = ev.delta / 120 if abs(ev.delta) >= 120 else max(-3, min(3, ev.delta * 0.5))
        self.zoom(1.1 ** steps, ev)

    def zoom(self, z, ev=None):
        """Move the camera toward/away from the target (lens stays the same, no stretching).
        Ctrl held = old lens zoom, kept between ~10 and ~120 degrees field of view."""
        if ev is not None and getattr(ev, "state", 0) & 0x0004:
            h = max(self.canvas.winfo_height(), 200) / 2
            lo, hi = h / math.tan(math.radians(60)), h / math.tan(math.radians(5))
            self.scale = min(max(self.scale * z, lo / self.dist), hi / self.dist)
        else:
            self.dist /= z
            self.scale *= z
        self.nav_redraw()

    def eye(self):
        """Where the camera sits (director camera when one is being drawn)."""
        if self.view:
            return self.view["eye"]
        fwd, _lv, _rt = self._cam_axes()
        return np.array(self.target, float) - fwd * self.dist

    def near(self):
        return self.view["near"] if self.view else 0.06 * self.dist

    def project(self, p):
        v = self.view
        if v:                                  # director camera: plain pinhole projection
            d = np.asarray(p, float) - v["eye"]
            depth = float(d @ v["fwd"])
            f = v["f"] / max(depth, v["near"])
            return self._w / 2 + float(d @ v["right"]) * f, self._h / 2 - float(d @ v["up"]) * f, depth, f
        x, y, z = p[0] - self.target[0], p[1] - self.target[1], p[2] - self.target[2]
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        x1 = x * cy - y * sy
        y1 = x * sy + y * cy
        depth = y1 * cp - z * sp
        up = y1 * sp + z * cp
        d = max(self.dist + depth, 0.05 * self.dist)
        f = self.scale * self.dist / d
        return self._w / 2 + x1 * f, self._h / 2 - up * f, depth, f

    def all_points(self):
        return [p for _name, pts in self.points_by_object() for p in pts]

    def points_by_object(self):
        out = []
        for _name, obj, _sel in self.visible_objects():
            pts = []
            out.append((_name, pts))
            try:
                pts += sample_points(obj)
            except Exception:
                pass
        return [(n, p) for n, p in out if p]

    def fit_view(self):
        self.canvas.update_idletasks()
        objs = self.points_by_object()
        if len(objs) > 2:
            # Ignore runaway objects (e.g. scaled x20 many times) so the rest stay visible.
            centers = np.array([np.mean(p, axis=0) for _n, p in objs])
            mid = np.median(centers, axis=0)
            reach = np.array([np.max(np.linalg.norm(np.array(p) - mid, axis=1)) for _n, p in objs])
            limit = max(np.median(reach), 1.0) * 50
            far = [n for (n, _p), d in zip(objs, reach) if d > limit]
            if far and len(far) < len(objs):
                print(f"Fit view ignored oversized/far objects: {', '.join(far)}")
                objs = [(n, p) for (n, p), d in zip(objs, reach) if d <= limit]
        pts = [q for _n, p in objs for q in p]
        w, h = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        if pts:
            arr = np.array(pts)
            lo, hi = arr.min(axis=0), arr.max(axis=0)
            self.target = tuple((lo + hi) / 2)
            radius = max(float(np.linalg.norm(hi - lo)) / 2, 1.0)
        else:
            self.target, radius = (0.0, 0.0, 0.0), 10.0
        self.scale = min(w, h) * 0.42 / radius
        self.dist = radius * 4
        self.update_grid()
        self.redraw()

    def update_grid(self):
        global _SP_MEMO
        _SP_MEMO = {}                          # world width + grid both walk every object: sample once
        try:
            self._update_grid()
        finally:
            _SP_MEMO = None

    def _update_grid(self):
        if hasattr(self, "l_world"):
            try:
                self.l_world.configure(text=f"now {fmt(round(self.world_width(), 3))}")
            except Exception:                  # noqa: BLE001 - label only
                pass
        pts = self.all_points()
        ext = max([abs(c) for p in pts for c in p] + [5.0]) * 1.1
        raw = ext / 10
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
        self.grid_step = step
        self.grid_ext = math.ceil(ext / step) * step

    # -------------------------------------------------------------- POV-Ray
    def pov_items(self):
        """What is on screen, as plain shape rows for pov_export (transforms applied)."""
        items = []
        owner = {id(e.obj): (e, False) for e in self.entries if e.obj is not None}
        owner.update({id(e.twin_obj): (e, True) for e in self.entries if e.twin_obj is not None})
        ghosts = {id(g) for _n, g in self.ghosts}
        for name, obj, _sel in self.visible_objects():
            if id(obj) in ghosts:                        # Lathe tool preview, not in the scene yet
                continue
            src, twin = owner.get(id(obj), (None, False))
            hole = id(obj) in self._holes
            if hole:
                src = self._holes[id(obj)][1]
            # _owner/_twin/_csg/_hole/_group: pov_export merges twins, cuts hollows out,
            # fuses tool/target groups and wraps csg tools around their target
            mat = {"mat": src.mat, "mat_scale": src.mat_scale, "_owner": src.name, "_twin": twin,
                   "_csg": src.csg, "_hole": hole, "_groups": gsegs(src)} if src else {}
            try:
                c1, c2 = (str(c) if c else "" for c in color_of(obj))
                if tube_bends(obj) is not None:
                    for i, bend in enumerate(tube_bends(obj)):
                        e = entry_from_obj(f"{name} bend {i + 1}", bend)
                        items.append({"name": e.name, "kind": e.kind, "c1": c1, "c2": c2, "nums": e.nums, **mat})
                    continue
                if getattr(obj, "_viewer_plane", False):     # carrier square of an infinite plane
                    q = [np.array(c) for c in square_corners(obj)]
                    nrm = np.cross(q[1] - q[0], q[3] - q[0])
                    items.append({"name": name, "kind": "plane3d", "c1": c1, "c2": c2,
                                  "nums": list(np.mean(q, axis=0)) + list(nrm)
                                  + [float(np.linalg.norm(q[1] - q[0]))], **mat})
                    continue
                e = entry_from_obj(name, obj)
                items.append({"name": name, "kind": e.kind, "c1": e.c1, "c2": e.c2, "nums": e.nums, **mat})
            except Exception as exc:                     # noqa: BLE001 - skip, keep exporting
                print(f"POV export: {name} skipped: {exc}")
        return items

    def pov_camera(self):
        """The viewer's own camera, so the render frames what you see."""
        fwd, _lv, _rt = self._cam_axes()
        w, h = max(self.canvas.winfo_width(), 2), max(self.canvas.winfo_height(), 2)
        return {"eye": np.array(self.target, float) - fwd * self.dist, "target": self.target,
                "angle": math.degrees(2 * math.atan(w / (2 * self.scale * self.dist))),
                "aspect": w / h}

    def pov_text(self):
        return pov_export.scene_pov(self.pov_items(), self.pov_camera(), self.rgb, background=BG)

    def save_pov(self):
        os.makedirs(POV_DIR, exist_ok=True)
        path = filedialog.asksaveasfilename(parent=self.root, initialdir=POV_DIR,
                                            initialfile=os.path.basename(POV_FILE),
                                            defaultextension=".pov", filetypes=[("POV-Ray scene", "*.pov")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.pov_text())
            print(f"Saved {path}")

    def open_pov_gui(self):
        os.makedirs(POV_DIR, exist_ok=True)
        with open(POV_FILE, "w", encoding="utf-8") as f:
            f.write(self.pov_text())
        try:
            pov_export.open_official_gui(POV_FILE)
            print(f"Opened {POV_FILE} in the POV-Ray GUI")
        except OSError as exc:
            print(f"Could not start POV-Ray GUI: {exc}")

    def render_pov(self):
        if getattr(self, "_pov_job", None):
            print("POV-Ray: a render is already running")
            return
        try:
            width = max(16, int(float(self.v_pov_w.get())))
        except ValueError:
            width = 640
        cam = self.pov_camera()
        height = max(16, int(round(width / cam["aspect"])))
        text = self.pov_text()
        quality = self.v_pov_q.get().lower()
        os.makedirs(POV_DIR, exist_ok=True)
        with open(POV_FILE, "w", encoding="utf-8") as f:      # always keep the last scene beside the render
            f.write(text)
        print(f"POV-Ray: rendering {width}x{height} ({quality})...")
        result = {}
        self._pov_job = threading.Thread(
            target=lambda: result.update(out=pov_export.render(text, width, height, POV_DIR, quality)),
            daemon=True)
        self._pov_job.start()

        def poll():
            if self._pov_job.is_alive():
                self.root.after(200, poll)
                return
            self._pov_job = None
            png, log = result.get("out", (None, "render thread failed"))
            if png is None:
                print("POV-Ray failed:\n" + log, file=sys.stderr)
                return
            final = os.path.join(POV_DIR, "render.png")
            os.replace(png, final)
            self.show_render(final)
            print(f"POV-Ray: done -> {final}")
        poll()

    def show_render(self, png):
        win = getattr(self, "_render_win", None)
        if win is None or not win.winfo_exists():
            win = tk.Toplevel(self.root)
            win.title("POV-Ray render")
            win.configure(bg="#111317")
            self._render_lbl = tk.Label(win, bg="#111317")
            self._render_lbl.pack(fill=tk.BOTH, expand=True)
            win.bind("<F9>", lambda _e: self.render_pov())
            self._render_win = win
        self._render_img = tk.PhotoImage(file=png)          # keep a reference or Tk drops it
        self._render_lbl.configure(image=self._render_img)
        win.lift()

    # ------------------------------------------------------ Taichi GPU preview
    def preview_mesh(self):
        """The scene as plain-colored triangles + lines for taichi_preview.py.
        CSG cutters and hollow inner walls are left out (the POV-Ray render does those)."""
        tv, tn, tc, lv, lc = [], [], [], [], []
        t_own, l_own, iids, index = [], [], [], {}  # which tree row each triangle / line belongs to
        planes = []                                 # per tree row: is it a plane (loses picks)
        pq, pq_own = [], []                         # plane areas (4 corners) for picking
        cur = [-1, False]                           # (index into iids or -1, selected)
        default = np.array(self.rgb(DEFAULT_LINE)) / 255

        def col(*cs):
            for c in cs:
                if c and self.rgb(c) is not None:
                    return np.array(self.rgb(c)) / 255
            return default

        def lit(c):                                 # selected objects show lighter
            return c * 0.55 + 0.45 if cur[1] else c

        def add(P, N, c):                           # P, N: (T, 3, 3)
            tv.append(P)
            tn.append(N)
            tc.append(np.broadcast_to(lit(c), P.shape))
            t_own.append(np.full(len(P), cur[0], np.int32))

        def flat(P, mid):
            """Face normals, turned away from the object's middle."""
            n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
            n[np.einsum("ij,ij->i", n, P.mean(axis=1) - mid) < 0] *= -1
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            return np.repeat(n[:, None], 3, axis=1)

        def quads(G):                               # (a, b, 3) grid -> two triangles per cell
            p00, p10, p11, p01 = G[:-1, :-1], G[1:, :-1], G[1:, 1:], G[:-1, 1:]
            return np.concatenate([np.stack([p00, p10, p11], -2).reshape(-1, 3, 3),
                                   np.stack([p00, p11, p01], -2).reshape(-1, 3, 3)])

        def fan(pts):
            pts = np.asarray(pts, float)
            return np.stack([np.repeat(pts[:1], len(pts) - 2, 0), pts[1:-1], pts[2:]], 1)

        def seg(a, b, c):
            lv.append((a, b))
            lc.append((lit(c), lit(c)))
            l_own.append(cur[0])

        def plane_lines(ctr, u, v, c):
            s = self.grid_step
            k = max(int(round(self.grid_ext / s)), 1)
            if cur[0] >= 0:                         # its whole area is clickable in the preview
                a, b = k * s * u, k * s * v
                pq.append((ctr - a - b, ctr + a - b, ctr + a + b, ctr - a + b))
                pq_own.append(cur[0])
            for i in range(-k, k + 1):
                seg(ctr + i * s * v - k * s * u, ctr + i * s * v + k * s * u, c)
                seg(ctr + i * s * u - k * s * v, ctr + i * s * u + k * s * v, c)

        for _name, obj, _sel in self.visible_objects():
            iid, cut = self._meta.get(id(obj), (None, False))
            if cut:
                continue                            # cutter / hollow inner wall
            if iid is not None and iid not in index:
                index[iid] = len(iids)
                iids.append(iid)
                planes.append(False)
            cur[:] = [index[iid] if iid is not None else -1, _sel]
            try:
                bc, fc = color_of(obj)
                if isinstance(obj, Sphere3d):
                    c, r = np.array(center_of(obj)), float(obj.get_radius())
                    th = np.linspace(0, math.pi, 13)[:, None]
                    ph = np.linspace(0, 2 * math.pi, 25)[None, :]
                    U = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph),
                                  np.cos(th) + 0 * ph], -1)
                    add(quads(c + r * U), quads(U), col(obj.get_color()))
                elif getattr(obj, "_viewer_plane", False) or is_lib_plane(obj):
                    if is_lib_plane(obj):
                        ctr = np.array(center_of(obj), float)
                        n = np.array(lib_plane_normal(obj), float)
                        n /= np.linalg.norm(n)
                        u = np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0))
                        u /= np.linalg.norm(u)
                        v = np.cross(n, u)
                    else:
                        q = [np.array(p, float) for p in square_corners(obj)]
                        ctr, u, v = sum(q) / 4, q[1] - q[0], q[3] - q[0]
                        u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
                    plane_lines(ctr, u, v, col(fc, bc) * 0.6)
                    if cur[0] >= 0:
                        planes[cur[0]] = True
                elif tube_bends(obj) is not None:
                    K = 16
                    for bend in tube_bends(obj):
                        c = np.array(xyz(bend.get_bend_center()), float)
                        n = np.array(bend.get_norm(), float)
                        R, r, ang = bend.get_bend_radius(), bend.get_tube_radius(), bend.get_angle()
                        M = max(4, int(math.ceil(48 * ang / (2 * math.pi))))
                        rad = np.array([bend.radial_dir(i / M) for i in range(M + 1)], float)[:, None]
                        f = np.linspace(0, 2 * math.pi, K + 1)[None, :, None]
                        Nq = np.cos(f) * rad + np.sin(f) * n
                        add(quads(c + R * rad + r * Nq), quads(Nq), col(fc, bc))
                elif isinstance(obj, Lathe3d):
                    G, N = obj.mesh()
                    G = np.asarray(G, float)
                    Nf = np.asarray(N, float).reshape(-1, 3)
                    Nf = Nf / (np.linalg.norm(Nf, axis=1, keepdims=True) + 1e-12)
                    add(quads(G), np.repeat(np.concatenate([Nf, Nf])[:, None], 3, 1), col(fc, bc))
                elif solids3d.is_solid(obj):
                    pts, faces, _smooth, _grid = solids3d.mesh(obj)
                    P = np.concatenate([fan(pts[list(fa)]) for fa in faces])
                    add(P, flat(P, pts.mean(axis=0)), col(fc, bc))
                elif is_round(obj):
                    ctr, n, r, h = round_geom(obj)
                    base = np.array(ring(ctr, n, r))
                    color = col(fc, bc)
                    if Cone3d and isinstance(obj, Cone3d):
                        apex = ctr + n * h
                        P = np.concatenate([np.stack([base[:-1], base[1:], np.repeat(apex[None], 48, 0)], 1),
                                            fan(base[:-1])])
                        add(P, flat(P, ctr + n * h / 3), color)
                    elif Cylinder3d and isinstance(obj, Cylinder3d):
                        top = base + n * h
                        P = np.concatenate([quads(np.stack([base, top])), fan(base[:-1]), fan(top[:-1])])
                        add(P, flat(P, ctr + n * h / 2), color)
                    else:                           # flat circle
                        P = fan(base[:-1])
                        add(P, np.broadcast_to(n, P.shape), color)
                elif isinstance(obj, (Cube3d, Square3d)):
                    cube = isinstance(obj, Cube3d)
                    mid = np.array(center_of(obj), float) if cube else None
                    for sq in (cube_faces(obj) if cube else (obj,)):
                        fill = fc or sq.get_fc()
                        q = np.array(square_corners(sq), float)
                        if fill and self.rgb(fill) is not None:
                            P = fan(q)
                            add(P, flat(P, mid if cube else q.mean(0) - np.cross(q[1] - q[0], q[3] - q[0])),
                                col(fill))
                        for a, b in square_edges(sq):
                            seg(a, b, col(bc or sq.get_bc()))
                elif isinstance(obj, Line3d):
                    seg(xyz(obj.get_start()), xyz(obj.get_end()), col(bc))
            except Exception as exc:                # noqa: BLE001 - leave that one out
                print(f"Taichi preview: {_name} skipped: {exc}")

        row = {id(e): i for i, e in enumerate(self.entries)}
        moves = []                                  # per tree row: what dragging it moves (a group label), -1 = can't
        pivots = []                                 # ... and the middle it turns / scales about
        by_group = {}                               # a 400-member group: work its middle out once, not 400 times
        for iid in iids:
            if iid.startswith("s"):
                es = self.group_entries(self.entries[int(iid[1:])])
                key = tuple(id(m) for m in es)
                if key not in by_group:
                    mates = [index.get(f"s{row[id(m)]}") for m in es]
                    by_group[key] = ([k for k in mates if k is not None], self.group_center(es))
                mates, mid = by_group[key]
                moves.append(min(mates + [index[iid]]))
                pivots.append(mid)
            else:
                moves.append(-1)                    # script objects come from the script
                pivots.append((0.0, 0.0, 0.0))
        cur[:] = [-1, False]                        # grid, axes, camera path: nobody's
        if self.v_grid.get():                     # the ground grid + axes, like the viewer
            minor, major = col("#262a31") * 1.6, col("#353a44") * 1.6
            E, s = self.grid_ext, self.grid_step
            for i in range(-int(round(E / s)), int(round(E / s)) + 1):
                c = major if i % 5 == 0 else minor
                seg((i * s, -E, 0), (i * s, E, 0), c)
                seg((-E, i * s, 0), (E, i * s, 0), c)
            for axis, c in ((0, "#ff6b6b"), (1, "#51cf66"), (2, "#5c9dff")):
                p = [0.0] * 3
                p[axis] = E
                seg((0, 0, 0), p, col(c))

        path = self.preview_path()
        for a, b in zip(path["path_cam"], path["path_cam"][1:]):        # the camera path, in orange
            seg(a, b, col("#ffa94d"))

        V = np.concatenate(tv).reshape(-1, 3) if tv else np.zeros((0, 3))
        L = np.array(lv, float).reshape(-1, 3) if lv else np.zeros((0, 3))
        allp = np.concatenate([V, L]) if len(V) + len(L) else np.zeros((1, 3))
        lo, hi = allp.min(0), allp.max(0)
        center = (lo + hi) / 2
        cam = self.pov_camera()
        h = max(self.canvas.winfo_height(), 2)
        # the tree, for the preview's Objects menu: folders and the rows in them
        tsel = set(self.tree.selection())
        tops = list(self.tree.get_children("scene")) if self.tree.exists("scene") else []
        tops += [k for k in ("script", "director") if self.tree.exists(k)]
        l_iid, l_name, l_fold = [], [], []
        for fi, k in enumerate(tops):
            for c in self.tree.get_children(k):
                l_iid.append(c)
                l_name.append(self.tree.item(c, "text"))
                l_fold.append(fi)
        menu = {"list_fids": np.array(tops, dtype=str),
                "list_folders": np.array([self.tree.item(k, "text") for k in tops], dtype=str),
                "list_iid": np.array(l_iid, dtype=str), "list_name": np.array(l_name, dtype=str),
                "list_fold": np.array(l_fold, np.int32),
                "list_sel": np.array([c in tsel for c in l_iid], bool),
                "obj_sel": np.array([i in tsel for i in iids] or [False], bool),
                "add_kinds": np.array(list(ADD_SPECS), dtype=str),
                "grid_on": bool(self.v_grid.get())}
        return {"verts": V.astype(np.float32),
                "normals": (np.concatenate(tn).reshape(-1, 3) if tn else V).astype(np.float32),
                "colors": (np.concatenate(tc).reshape(-1, 3) if tc else V).astype(np.float32),
                "lverts": L.astype(np.float32),
                "lcolors": (np.array(lc, float).reshape(-1, 3) if lc else L).astype(np.float32),
                "tri_obj": np.concatenate(t_own) if t_own else np.zeros(0, np.int32),
                "seg_obj": np.array(l_own, np.int32),
                "obj_iids": np.array(iids or [""], dtype="U16"),
                "obj_plane": np.array(planes or [False], bool),
                "obj_move": np.array(moves or [-1], np.int32),
                "obj_pivot": np.array(pivots or [(0.0, 0.0, 0.0)], float),
                "snap": self.grid_step / 10,
                "plane_quads": np.array(pq, float).reshape(-1, 4, 3),
                "plane_obj": np.array(pq_own, np.int32),
                "eye": np.asarray(cam["eye"], float), "target": np.asarray(cam["target"], float),
                "fov": math.degrees(2 * math.atan((h / 2) / (self.scale * self.dist))),
                "center": center, "radius": max(float(np.linalg.norm(hi - lo)) / 2, 1.0),
                "cam_id": getattr(self, "_ti_cam", 0), "play_id": getattr(self, "_ti_play", 0),
                "moves_done": getattr(self, "_ti_moves", 0),
                "start_play": bool(getattr(self, "_ti_start_play", False)), **path, **menu}

    def preview_path(self):
        """The Camera Director's frames (eye, look-at, up, vfov) for playing in the preview."""
        import director3d
        d = self.director
        try:
            frames = d.frames if d is not None and d.winfo_exists() else []
        except tk.TclError:
            frames = []
        roll = d.shot.get("roll", 0) if frames else 0
        cam = np.array([f["camera"] for f in frames], float).reshape(-1, 3)
        look = np.array([f["lookat"] for f in frames], float).reshape(-1, 3)
        up = np.array([director3d.basis(c, t, roll)[1] for c, t in zip(cam, look)], float).reshape(-1, 3)
        return {"path_cam": cam, "path_look": look, "path_up": up,
                "path_fov": np.array([f["vfov"] for f in frames], float),
                "path_fps": float(d.shot.get("fps", 24)) if frames else 24.0}

    def preview_refresh(self):
        """Send the scene again if the preview window is open (after an edit)."""
        proc = getattr(self, "_ti_proc", None)
        if proc is not None and proc.poll() is None and not getattr(self, "_ti_queued", False):
            self._ti_queued = True

            def go():
                self._ti_queued = False
                self.write_preview()
            self.root.after_idle(go)

    def write_preview(self):
        path = os.path.join(POV_DIR, "_preview.npz")
        tmp = os.path.join(POV_DIR, "_preview_tmp.npz")
        os.makedirs(POV_DIR, exist_ok=True)
        np.savez(tmp, **self.preview_mesh())
        for _ in range(10):                         # the preview may be reading it right now
            try:
                os.replace(tmp, path)
                return path
            except PermissionError:
                self.root.after(30)
        print("Taichi preview: could not update the mesh file")
        return path

    def _taichi_python(self):
        """A Python that has Taichi (checked once)."""
        if getattr(self, "_ti_py", None):
            return self._ti_py
        cands = [[os.path.expanduser(os.environ["TAICHI_PYTHON"])]] if os.environ.get("TAICHI_PYTHON") else []
        cands += [[sys.executable]]
        if sys.platform == "win32":
            cands += [["py", "-3.12"], ["py", "-3.11"], ["py", "-3.10"]]
        else:
            cands += [["python3.12"], ["python3.11"], ["python3.10"], ["python3"]]
        for c in cands:
            try:
                r = subprocess.run(c + ["-c", "import taichi"], capture_output=True, text=True, timeout=60,
                                   **self._no_window())
                if r.returncode == 0:
                    self._ti_py = c
                    return c
                why = (r.stderr or r.stdout).strip().splitlines()[-1:] or [f"exit {r.returncode}"]
            except (OSError, subprocess.TimeoutExpired) as exc:
                why = [str(exc)]
            print(f"Taichi preview: {' '.join(c)} -> {why[0]}")
        return None

    @staticmethod
    def _no_window():
        return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}

    def open_preview(self, play=False, resume=False):
        """Open the Taichi GPU window: at the viewer's current camera, or (play) running
        the Camera Director's path, or (resume) where it was before it closed."""
        if play:
            self._ti_play = getattr(self, "_ti_play", 0) + 1
        elif not resume:
            self._ti_cam = getattr(self, "_ti_cam", 0) + 1
        self._ti_start_play = play                  # a fresh window: start playing right away?
        path = self.write_preview()
        self._ti_start_play = False
        proc = getattr(self, "_ti_proc", None)
        if proc is not None and proc.poll() is None:
            print("Taichi preview: " + ("playing the camera path" if play else "updated (camera reset to this view)"))
            return
        py = self._taichi_python()
        if py is None:
            print("Taichi preview: no Python with taichi found - pip install taichi (Python 3.10-3.12), "
                  "then set TAICHI_PYTHON to that python if it is in a venv")
            return
        log = open(os.path.join(POV_DIR, "_preview.log"), "w", encoding="utf-8")
        self._ti_proc = proc = subprocess.Popen(
            py + ["-u", os.path.join(HERE, "taichi_preview.py"), path] + (["--resume"] if resume else []),
            stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8", errors="replace",
            **self._no_window())
        self._ti_picks = picks = queue.SimpleQueue()
        self._ti_started, self._ti_done = time.time(), False

        def read():                                 # thread: PICK / XF / KEY / CMD lines -> queue, the rest -> log
            for line in proc.stdout:
                if line.startswith(("PICK ", "XF ", "KEY ", "CMD ")):
                    picks.put(line.split())
                else:
                    log.write(line)
                    log.flush()
            log.close()
        self._ti_reader = threading.Thread(target=read, daemon=True)
        self._ti_reader.start()
        self.root.after(50, self._preview_picks)
        self.redraw()                               # (the 3D view pauses while it's open)
        print(f"Taichi preview: starting (log: {log.name})")

    def _preview_moved(self):
        """Job after a preview drag's move: tell the preview it's done (it stops drawing its own offset)."""
        self._ti_moves = getattr(self, "_ti_moves", 0) + 1
        self.preview_refresh()
        return
        yield                                       # (a generator, for enqueue)

    def _preview_picks(self):
        """Do what was done in the preview window: PICK <iid> set|add selects it in the tree;
        XF <iid> move dx dy dz | xrot/yrot/zrot deg | scale f transforms it (and its group)
        about the group's middle, like the panel buttons."""
        picks = self._ti_picks
        try:
            while not picks.empty():
                kind, iid, *rest = picks.get() + ["set"]
                if kind == "KEY":                # undo / redo / delete pressed in the preview:
                    fn = {"undo": lambda: self._undo_redo(None, "undo_stack", "redo_stack", "Undo", True),
                          "redo": lambda: self._undo_redo(None, "redo_stack", "undo_stack", "Redo", True),
                          "delete": self.delete_selected}.get(iid)
                    if fn is not None:           # queued, so moves sent before it land first
                        self.enqueue(self._call_job(fn))
                    continue
                if kind == "CMD":                # a button in the preview's menu
                    self.enqueue(self._call_job(lambda c=iid, a=rest[:-1]: self._preview_cmd(c, a)))
                    continue
                if kind == "XF":                 # every XF gets its ticket done, even a bad one,
                    try:                         # or the preview keeps drawing it "on its way"
                        e = self.entries[int(iid[1:])] if self.tree.exists(iid) and iid[1:].isdigit() else None
                        op, vals = rest[0], [float(v) for v in rest[1:-1]]   # (last is the "set" pad)
                        tf = None if e is None else (
                            {"op": "move", "d": tuple(vals[:3])} if op == "move" else
                            {"op": "scale", "f": vals[0], "pivot": "group"} if op == "scale" else
                            {"op": op, "deg": vals[0], "pivot": "group"} if op in ("xrot", "yrot", "zrot") else None)
                    except (ValueError, IndexError):
                        tf = None
                    if tf is not None:
                        self._queue_tf(e, tf, animate=False)
                    self.enqueue(self._preview_moved())
                    continue
                if not self.tree.exists(iid):
                    continue
                how = rest[0]
                if how == "add":
                    self.tree.selection_add(iid)
                else:
                    self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
        except Exception:
            traceback.print_exc()
        finally:
            proc = getattr(self, "_ti_proc", None)
            if proc is not None and picks is self._ti_picks:
                if proc.poll() is None:
                    self.root.after(50, self._preview_picks)
                elif not self._ti_done:
                    self._ti_done = True
                    self._ti_reader.join(1.0)
                    self._preview_picks()        # what it sent just before it closed
                    if not self._preview_crashed(proc.returncode):
                        self.redraw()            # closed for good: the 3D view draws again

    def _preview_crashed(self, rc):
        """Taichi 1.7's ImGui aborts the window ("Mismatching io.KeyCtrl ... vs io.KeyMods") when it
        misses a Ctrl / Shift / Alt press or release (switching windows with one held). Not our code,
        so reopen it where it was. Closing the window normally exits 0 and stays closed.
        True = reopening."""
        if rc == 0:
            return False
        if time.time() - self._ti_started < 10:
            print(f"Taichi preview closed (exit {rc}) right after starting - not reopening; see pov/_preview.log")
            return False
        print(f"Taichi preview crashed (exit {rc}, Taichi's own key-state bug) - reopening where you were")
        self._ti_reopen_at = time.time()
        self.root.after(300, lambda: self.open_preview(resume=True))
        return True

    def _preview_cmd(self, cmd, args):
        """A button in the preview's menu. Things that need typing open a Tk box in front."""
        before = set(self.root.winfo_children())
        target = None
        if cmd == "add" and args and args[0].isdigit() and int(args[0]) < len(ADD_SPECS):
            self.v_add.set(list(ADD_SPECS)[int(args[0])])
            self.add_dialog()
        elif cmd == "grid":
            self.v_grid.set(bool(args) and args[0] == "1")
            self.redraw()
            self.preview_refresh()
        elif cmd == "tag":
            self._ask("Group", [("Group name", self.v_group)], self.tag_group)
        elif cmd == "replicate":
            self._ask("Replicate", [("Copies", self.v_rep_n), ("Step X", self.v_rep_step[0]),
                                    ("Step Y", self.v_rep_step[1]), ("Step Z", self.v_rep_step[2]),
                                    ("Into group (optional)", self.v_rep_group)], self.replicate)
        elif cmd == "move_by":
            self._ask("Move by", [("X  Y  Z", self.v_mv)], self.move_by)
        elif cmd == "move_to":
            self._ask("Center to", [("X  Y  Z", self.v_to)], self.move_to)
        elif cmd == "scale":
            self._ask("Scale", [("Scale x  (group: its center)", self.v_scale)], self.scale_by)
        elif cmd == "rotate":
            self._ask("Rotate", [("Rotate", self.v_rot, ROT_TYPES), ("Degrees", self.v_deg),
                                 ("Pivot", self.v_pivot, self.cb_pivot["values"]),
                                 ("  point  (pivot = point)", self.v_pxyz),
                                 ("Axis  (vecrot)", self.v_axis, self.cb_axis["values"]),
                                 ("  from", self.v_axa), ("  to", self.v_axb)], self.rotate)
        elif cmd == "viewer":
            target = self.root
        else:
            fn = {"props": self.open_props, "lathe": self.open_lathe, "director": self.open_director,
                  "render": self.render_pov, "select_all": self.select_all,
                  "select_none": self.select_none, "untag": self.untag_group}.get(cmd)
            if fn is None:
                print(f"Taichi preview: unknown menu command {cmd}")
                return
            fn()
            target = {"props": (self._props or [None])[0], "director": self.director,
                      "lathe": self.lathe_tool}.get(cmd)
        for w in self.root.winfo_children():
            if isinstance(w, tk.Toplevel) and w not in before:
                self._to_front(w)
        if isinstance(target, tk.Misc):
            self._to_front(target)

    @staticmethod
    def _to_front(w):
        """Over the preview window (it has the focus, so just asking Windows isn't enough)."""
        try:
            if not w.winfo_exists():
                return
            w.deiconify()
            w.lift()
            w.attributes("-topmost", True)
            w.focus_force()
            w.after(400, lambda: w.winfo_exists() and w.attributes("-topmost", False))
        except tk.TclError:
            pass

    def _ask(self, title, fields, then):
        """Small box to type values in (for the preview's menu): OK puts them in the panel's
        boxes, then runs then() - same as filling the panel and pressing its button.
        A field is (label, var), (label, var, choices) for a drop-down, or (label, [x, y, z vars])."""
        top = tk.Toplevel(self.root)
        top.title(title)
        top.resizable(False, False)
        boxes = []
        for r, (label, var, *choices) in enumerate(fields):
            ttk.Label(top, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            row = ttk.Frame(top)
            row.grid(row=r, column=1, padx=6, pady=2, sticky="we")
            for one in (var if isinstance(var, (list, tuple)) else [var]):
                v = tk.StringVar(value=one.get())
                if choices:
                    ent = ttk.Combobox(row, textvariable=v, values=list(choices[0]), width=16)
                else:
                    ent = ttk.Entry(row, textvariable=v, width=14 if one is var else 6)
                ent.pack(side=tk.LEFT, padx=1)
                boxes.append((one, v, ent))

        def ok(_e=None):
            for var, v, _ent in boxes:
                var.set(v.get())
            top.destroy()
            self.enqueue(self._call_job(then))
        bf = ttk.Frame(top)
        bf.grid(row=len(fields), column=0, columnspan=2, pady=4)
        ttk.Button(bf, text="OK", command=ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=4)
        top.bind("<Return>", ok)
        top.bind("<Escape>", lambda _e: top.destroy())
        boxes[0][2].focus_set()
        boxes[0][2].select_range(0, "end")
        self._to_front(top)
        return top

    # -------------------------------------------------------------- drawing
    def rgb(self, color):
        if color not in self._rgb_cache:
            try:
                self._rgb_cache[color] = tuple(v / 257 for v in self.root.winfo_rgb(color))
            except tk.TclError:
                self._rgb_cache[color] = None
        return self._rgb_cache[color]

    def blend(self, color, alpha):
        c, b = self.rgb(color), self.rgb(BG)
        if c is None:
            return None
        return "#%02x%02x%02x" % tuple(int(cc * alpha + bb * (1 - alpha)) for cc, bb in zip(c, b))

    def safe(self, color, default):
        return color if color and self.rgb(color) is not None else default

    def visible_objects(self):
        out = []
        self._meta = meta = {}              # id(obj) -> (tree iid, drawn as cutter wire)
        self._holes = holes = {}            # id(inner copy) -> (inner copy, hollow entry)
        if self.v_show_scene.get():
            cur = self.selected[1] if self.selected and self.selected[0] == "s" else None
            mates = {id(o) for o in self.group_entries(cur)} if cur is not None else set()
            for i, e in enumerate(self.entries):
                if e.obj is not None:
                    sel = id(e) in mates
                    cut = self.is_cutter(e)
                    for o in (e.obj, e.twin_obj):
                        if o is not None:
                            out.append((e.name, o, sel))
                            meta[id(o)] = (f"s{i}", cut)
                            if e.hollow:
                                try:
                                    inner = hollow_inner(o, *e.hollow)
                                except (ValueError, TypeError):
                                    continue
                                out.append((e.name, inner, sel))
                                meta[id(inner)] = (f"s{i}", True)       # inner wall: dashed
                                holes[id(inner)] = (inner, e)
        if self.v_show_script.get():
            for i, (name, obj) in enumerate(self.script_objs):
                sel = (self.selected == ("r", i)) or obj is self.anim_target
                out.append((name, obj, sel))
                meta[id(obj)] = (f"r{i}", False)
        out += [(name, obj, True) for name, obj in self.ghosts]
        return out

    def draw_through(self, canvas, view, grid=True):
        """Draw the real scene on another canvas through a director camera.
        view: {"eye", "right", "up", "fwd" (unit np vectors), "f" (focal px), "near"}."""
        saved = self.canvas, self.view
        self.canvas, self.view = canvas, view
        try:
            self._paint(grid, extras=False)
        finally:
            self.canvas, self.view = saved
            self._w, self._h = self.canvas.winfo_width(), self.canvas.winfo_height()

    def redraw(self):
        if self.tk_paused():
            c = self.canvas
            c.delete("all")
            c.create_text(c.winfo_width() // 2, c.winfo_height() // 2, fill="#5c6370", font=("Segoe UI", 11),
                          text="3D view paused while the Taichi preview is open\n"
                               "(tick \"Draw here too\" in the POV-Ray row to draw it here as well)",
                          justify=tk.CENTER)
            return
        self._paint(self.v_grid.get(), extras=True)

    def tk_paused(self):
        """A big scene takes this canvas ~30 s to draw (90k items); with the Taichi window open it's
        the same picture twice, and every edit froze the viewer. So skip it unless asked."""
        proc = getattr(self, "_ti_proc", None)
        v = getattr(self, "v_tk_draw", None)
        open_ = proc is not None and (proc.poll() is None or time.time() - getattr(self, "_ti_reopen_at", 0) < 15)
        return open_ and not (v is not None and v.get())

    def nav_redraw(self):
        """Redraw for camera moves.  A full redraw of a big scene takes over a second; drawing on
        every key-repeat queued them up for minutes.  Now moves pile into one light redraw, and a
        full-detail redraw follows once input stops."""
        self._moving = True
        if not getattr(self, "_nav_pending", False):
            self._nav_pending = True
            self.root.after_idle(self._nav_paint)
        if getattr(self, "_settle_id", None):
            self.root.after_cancel(self._settle_id)
        self._settle_id = self.root.after(400, self._settle)

    def _nav_paint(self):
        self._nav_pending = False
        self.redraw()

    def _settle(self):
        self._settle_id = None
        self._moving = False
        self.redraw()

    def _paint(self, grid, extras):
        c = self.canvas
        c.delete("all")
        self._w, self._h = c.winfo_width(), c.winfo_height()
        if grid:
            self.draw_grid()
        fills, lines, dots = [], [], []
        owner = {}                            # id(drawn tuple) -> canvas tags (click picks the object)
        P = self.project
        for name, obj, sel in self.visible_objects():
            n0, l0, d0 = len(fills), len(lines), len(dots)
            try:
                self.collect(obj, sel, fills, lines, dots)
            except Exception as exc:          # e.g. a half-built object from a script
                c.create_text(10, 10, anchor="nw", fill="#ff7b72", text=f"{name}: {exc}")
            iid, cut = self._meta.get(id(obj), (None, False))
            if cut:                           # csg cut/overlap tool: dashed wire only
                del fills[n0:]
                lines[l0:] = [ln[:5] + ((4, 3),) for ln in lines[l0:]]
            if iid:
                plane = getattr(obj, "_viewer_plane", False) or is_lib_plane(obj)
                tags = ("o:" + iid,) + (("plane",) if plane else ())
                for t in fills[n0:] + lines[l0:] + dots[d0:]:
                    owner[id(t)] = tags
        for item in sorted(fills, key=lambda t: -t[0]):
            coords, fill = item[1], item[2]
            tags = owner.get(id(item), ())
            if len(coords) == 4:              # sphere disc: x0,y0,x1,y1
                c.create_oval(*coords, fill=fill, outline="", tags=tags)
            else:                             # 4th field: stipple for see-through planes
                c.create_polygon(*coords, fill=fill, outline="",
                                 stipple=item[3] if len(item) > 3 else "", tags=tags)
        moving = getattr(self, "_moving", False) and extras
        for ln in sorted(lines, key=lambda t: -t[0]):
            depth, coords, color, width, arrow, dash = ln
            if moving and width == 1 and arrow is None:     # thin detail lines wait until you stop
                continue
            c.create_line(*coords, fill=color, width=width, arrow=arrow, dash=dash,
                          arrowshape=(12, 14, 5), capstyle=tk.ROUND, tags=owner.get(id(ln), ()))
        labelled = set()
        near = self.near()
        for dot in dots if extras else ():     # director preview: objects only
            p, color, sel = dot
            if self.cam_d(p) < near:
                continue
            sx, sy, _d, _f = P(p)
            r = 4 if sel else 3
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=color, outline="#000",
                          tags=owner.get(id(dot), ()))
            key = tuple(round(v, 2) for v in p)
            if self.v_coords.get() and not moving and key not in labelled:
                labelled.add(key)
                c.create_text(sx + 6, sy - 7, anchor="w", font=("Segoe UI", 7),
                              fill="#e8e8e8" if sel else "#8f98a6",
                              text="(" + ", ".join(fmt(v) for v in p) + ")")
        if not extras:
            return
        if self.director is not None:
            self.director.draw_in_viewer(c)
        for item in self.overlay:
            if item[0] == "line":
                _, a, b, color, dash, width = item
                (ax, ay, _, _), (bx, by, _, _) = P(a), P(b)
                c.create_line(ax, ay, bx, by, fill=color, dash=dash, width=width)
            else:
                _, p, color, text = item
                sx, sy, _, _ = P(p)
                c.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, outline=color, width=2)
                c.create_text(sx + 8, sy + 9, anchor="w", fill=color, text=text, font=("Segoe UI", 8))
        c.create_text(8, self._h - 8, anchor="sw", fill="#5c6370", font=("Segoe UI", 8),
                      text="left-drag orbit  |  right-drag pan  |  wheel zoom  |  "
                           "WASD move  Q/E down/up  arrows look  (Shift = faster, click view first)")

    def collect(self, obj, sel, fills, lines, dots):
        P = self.project
        width = 3.2 if sel else 1.6
        bc, fc = color_of(obj)

        def seg(a, b, color, arrow=None, w=None):
            s = self.seg2d(a, b)
            if s:
                lines.append((s[0], s[1], color, w or width, arrow, None))

        def face(corners, fill):
            if not fill:
                return
            pg = self.poly2d(corners)
            if pg:
                fills.append((pg[0], pg[1], fill))

        if isinstance(obj, Sphere3d):
            ctr, r = center_of(obj), float(obj.get_radius())
            color = self.safe(obj.get_color(), DEFAULT_LINE)
            sx, sy, depth, f = P(ctr)
            if self.cam_d(ctr) < self.near() + r:       # camera inside / touching: skip the disc
                return
            fills.append((depth, (sx - r * f, sy - r * f, sx + r * f, sy + r * f),
                          self.blend(color, FILL_ALPHA)))
            ring_col = self.blend(color, 0.55)
            for e1, e2 in ((0, 1), (0, 2), (1, 2)):
                coords, dsum = [], 0.0
                for k in range(37):
                    t = 2 * math.pi * k / 36
                    q = list(ctr)
                    q[e1] += r * math.cos(t)
                    q[e2] += r * math.sin(t)
                    px, py, pd, _ = P(q)
                    coords += [px, py]
                    dsum += pd
                lines.append((dsum / 37, coords, ring_col, 1, None, None))
            lines.append((depth - r, (sx - r * f, sy - r * f, sx + r * f, sy + r * f, sx - r * f, sy - r * f),
                          color, width, None, None))
            lines[-1] = (depth - r, self._circle(sx, sy, r * f), color, width, None, None)
            dots.append((ctr, color, sel))
            return
        if getattr(obj, "_viewer_plane", False) or is_lib_plane(obj):
            self.collect_plane(obj, sel, fills, lines, dots)
            return
        if tube_bends(obj) is not None:
            self.collect_tube(obj, sel, fills, lines, dots)
            return
        if isinstance(obj, Lathe3d):
            self.collect_lathe(obj, sel, fills, lines, dots)
            return
        if solids3d.is_solid(obj):             # before is_round: TruncatedCone3d is a Cylinder3d
            self.collect_solid(obj, sel, fills, lines, dots)
            return
        if is_round(obj):
            ctr, n, r, h = round_geom(obj)
            bcol = self.safe(bc, DEFAULT_LINE)
            fcol = self.blend(fc, FILL_ALPHA) if self.rgb(fc or "") else None
            dim = self.blend(bcol, 0.45)
            base = ring(ctr, n, r)
            eye = self.eye()
            shade = fc if self.rgb(fc or "") else None
            # Camera inside a cylinder (a tunnel): show the inside walls instead of the outside.
            rel = eye - ctr
            along = float(rel @ n)
            inside = (Cylinder3d and isinstance(obj, Cylinder3d) and not (Cone3d and isinstance(obj, Cone3d))
                      and min(0, h) <= along <= max(0, h) and np.linalg.norm(rel - n * along) < r)
            flip = -1.0 if inside else 1.0

            def lit(corners, out_n, cap=False):
                """Shade like the bent tubes; False (nothing drawn) when facing away from the camera."""
                to_eye = eye - sum(corners) / len(corners)
                facing = flip * float(np.dot(out_n, to_eye)) / (
                    np.linalg.norm(out_n) * np.linalg.norm(to_eye) + 1e-12)
                if facing <= 0:
                    return False
                if shade:
                    face(corners, self.blend(shade, 0.45 if cap else 0.15 + 0.55 * min(facing * 1.2, 1.0)))
                return True

            def sides(vis, tip):
                """Silhouette where seen meets unseen, plus a few dim lines on the seen side."""
                for i in range(len(vis)):
                    if vis[i - 1] != vis[i]:
                        seg(tuple(base[i]), tuple(tip(i)), bcol)
                    elif vis[i] and i % 6 == 0:
                        seg(base[i], tip(i), dim, w=1)

            if Cone3d and isinstance(obj, Cone3d):
                apex = ctr + n * h
                bot = lit(base[:-1], -n * np.sign(h or 1), cap=True)
                vis = []
                for a, b in zip(base[:-1], base[1:]):
                    nf = np.cross(b - a, apex - a)
                    if np.dot(nf, (a + b) / 2 - ctr) < 0:
                        nf = -nf
                    vis.append(lit([a, b, apex], nf))
                for i, (a, b) in enumerate(zip(base, base[1:])):
                    if bot or vis[i]:
                        seg(tuple(a), tuple(b), bcol)
                sides(vis, lambda i: apex)
                dots.append((tuple(apex), bcol, sel))
            elif Cylinder3d and isinstance(obj, Cylinder3d):
                top = [q + n * h for q in base]
                up = n * np.sign(h or 1)
                top_vis = lit(top[:-1], up, cap=True)
                bot_vis = lit(base[:-1], -up, cap=True)
                vis = [lit([base[i], base[i + 1], top[i + 1], top[i]], (base[i] + base[i + 1]) / 2 - ctr)
                       for i in range(len(base) - 1)]
                for i in range(len(vis)):
                    if bot_vis or vis[i]:
                        seg(tuple(base[i]), tuple(base[i + 1]), bcol)
                    if top_vis or vis[i]:
                        seg(tuple(top[i]), tuple(top[i + 1]), bcol)
                sides(vis, lambda i: top[i])
                dots.append((tuple(ctr + n * h), bcol, sel))
            else:                           # flat circle: short normal arrow shows which way it faces
                face(base[:-1], fcol)
                for a, b in zip(base, base[1:]):
                    seg(tuple(a), tuple(b), bcol)
                seg(ctr, ctr + n * r * 0.6, dim, tk.LAST, w=1)
            dots.append((tuple(ctr), bcol, sel))
            return
        if isinstance(obj, (Cube3d, Square3d)):
            faces =cube_faces(obj) if isinstance(obj, Cube3d) else (obj,)
            for sq in faces:
                fill = fc or sq.get_fc()
                face(square_corners(sq), self.blend(fill, FILL_ALPHA) if self.rgb(fill or "") else None)
                for a, b in square_edges(sq):
                    seg(a, b, self.safe(bc or sq.get_bc(), DEFAULT_LINE))
            for p in points_of(obj):
                dots.append((xyz(p), self.safe(bc, DEFAULT_POINT), sel))
            return
        if isinstance(obj, Line3d):
            a, b = xyz(obj.get_start()), xyz(obj.get_end())
            color = self.safe(bc, DEFAULT_LINE)
            seg(a, b, color, tk.LAST if isinstance(obj, Vector3d) else None)
            dots.append((a, color, sel))
            dots.append((b, color, sel))
            return
        if isinstance(obj, Point3d):
            dots.append((xyz(obj), self.safe(bc, DEFAULT_POINT), sel))

    # ------------------------------------------------------ bent tube drawing
    def collect_tube(self, obj, sel, fills, lines, dots):
        """Shaded tube surface for a CurvedCylinder3d or every bend of a CurvedTorus3d.
        Faces turned away from the camera are skipped; the outline is where seen meets unseen."""
        P = self.project
        bc, fc = color_of(obj)
        bcol = self.safe(bc, DEFAULT_LINE)
        base = fc if self.rgb(fc or "") else bcol
        dim = self.blend(bcol, 0.35)
        width = 3.2 if sel else 1.6
        eye = self.eye()
        bends = tube_bends(obj)
        single = len(bends) == 1
        coarse = getattr(self, "_moving", False) and not self.view
        K = 8 if coarse else 16                         # facets around the tube

        def line(a, b, color, w):
            s = self.seg2d(a, b)
            if s:
                lines.append((s[0], s[1], color, w, None, None))

        def spine_dist(bend):
            pts = [np.array(xyz(bend.spine_point(i / 24)), float) for i in range(25)]
            best = math.inf
            for a, b in zip(pts, pts[1:]):
                ab = b - a
                t = min(1.0, max(0.0, float((eye - a) @ ab) / (float(ab @ ab) + 1e-12)))
                best = min(best, float(np.linalg.norm(eye - (a + t * ab))))
            return best

        # Camera inside the tube (flying through a tunnel): show the inside walls.
        flip = -1.0 if any(spine_dist(b) < b.get_tube_radius() for b in bends) else 1.0

        for bend in bends:
            c = np.array(xyz(bend.get_bend_center()), float)
            n = np.array(bend.get_norm(), float)
            R, r, ang = bend.get_bend_radius(), bend.get_tube_radius(), bend.get_angle()
            M = max(4, int(math.ceil((24 if coarse else 48) * ang / (2 * math.pi))))   # steps along the bend
            rad = [np.array(bend.radial_dir(i / M), float) for i in range(M + 1)]
            phis = [2 * math.pi * j / K for j in range(K + 1)]
            nrm = [[math.cos(f) * rd + math.sin(f) * n for f in phis] for rd in rad]
            grid = [[c + R * rd + r * q for q in row] for rd, row in zip(rad, nrm)]
            vis = [[False] * K for _ in range(M)]
            for i in range(M):
                for j in range(K):
                    quad = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
                    mid = sum(quad) / 4
                    to_eye = eye - mid
                    facing = flip * float(np.dot(nrm[i][j] + nrm[i + 1][j + 1], to_eye)) / (
                        2 * np.linalg.norm(to_eye) + 1e-12)
                    if facing <= 0:
                        continue
                    vis[i][j] = True
                    pg = self.poly2d(quad)
                    if pg:
                        fills.append((pg[0], pg[1], self.blend(base, 0.15 + 0.55 * min(facing * 1.2, 1.0))))
            ring_every = max(1, M // 4)
            for i in range(M + 1):
                for j in range(K):
                    a_vis = vis[i - 1][j] if i > 0 else False
                    b_vis = vis[i][j] if i < M else False
                    if (i == 0 or i == M) and single and (a_vis or b_vis):
                        line(grid[i][j], grid[i][j + 1], bcol, width)        # open end ring
                    elif i % ring_every == 0 and (a_vis or b_vis):
                        line(grid[i][j], grid[i][j + 1], dim, 1)
            for i in range(M):
                for j in range(K):
                    left, right = vis[i][j - 1], vis[i][j]
                    if left != right:
                        line(grid[i][j], grid[i + 1][j], bcol, width)          # silhouette
                    elif left and j % 4 == 0:
                        line(grid[i][j], grid[i + 1][j], dim, 1)
            if single:
                for i, t in ((0, 0.0), (M, 1.0)):                      # flat end caps
                    to_eye = eye - np.array(xyz(bend.spine_point(t)))
                    out = -np.array(bend.tangent(0.0)) if i == 0 else np.array(bend.tangent(1.0))
                    pg = self.poly2d(grid[i][:-1])
                    if flip * float(np.dot(out, to_eye)) > 0 and pg:
                        fills.append((pg[0], pg[1], self.blend(base, 0.45)))
                dots.append((xyz(bend.get_spine_start()), bcol, sel))
                dots.append((xyz(bend.get_spine_end()), bcol, sel))
        dots.append((xyz(obj.get_center()), bcol, sel))

    # ------------------------------------------------------- lathe drawing
    def collect_lathe(self, obj, sel, fills, lines, dots):
        """Shaded quads of a Lathe3d.  A profile can be open, so the far side shows through
        darker (inside walls); outlines are where the outside turns away from the camera."""
        bc, fc = color_of(obj)
        bcol = self.safe(bc, DEFAULT_LINE)
        base = fc if self.rgb(fc or "") else bcol
        dim = self.blend(bcol, 0.35)
        width = 3.2 if sel else 1.6
        G, N = obj.mesh()
        S, J = N.shape[0], N.shape[1]
        to_eye = self.eye() - (G[:-1, :-1] + G[1:, 1:]) / 2
        facing = np.einsum("ijk,ijk->ij", N, to_eye) / (np.linalg.norm(to_eye, axis=2) + 1e-12)
        vis = facing > 0
        for i in range(S):
            for j in range(J):
                pg = self.poly2d([G[i, j], G[i + 1, j], G[i + 1, j + 1], G[i, j + 1]])
                if pg:
                    f = float(facing[i, j])
                    shade = 0.15 + 0.55 * min(f * 1.2, 1.0) if f > 0 else 0.07 + 0.2 * min(-f * 1.2, 1.0)
                    fills.append((pg[0], pg[1], self.blend(base, shade)))

        def line(a, b, color, w):
            s = self.seg2d(a, b)
            if s:
                lines.append((s[0], s[1], color, w, None, None))

        full = obj.get_sweep() >= 360 - 1e-6
        mstep = max(1, J // 8)
        for i in range(S):                               # meridians (along the profile)
            for j in range(J if full else J + 1):        # full turn: column J is column 0
                if not full and j in (0, J):
                    line(G[i, j], G[i + 1, j], bcol, width)          # cut edge of a partial sweep
                    continue
                left, right = vis[i, j - 1], vis[i, j % J]
                if left != right:
                    line(G[i, j], G[i + 1, j], bcol, width)          # silhouette
                elif left and j % mstep == 0:
                    line(G[i, j], G[i + 1, j], dim, 1)
        rstep = 8 if obj.is_curved() and len(obj.get_profile()) >= 3 else 1
        prof = obj.samples()
        for i in range(S + 1):                           # rings (around the axis)
            for j in range(J):
                below, above = (vis[i - 1, j] if i > 0 else None), (vis[i, j] if i < S else None)
                if below is None or above is None:
                    if prof[i][0] > 1e-9:
                        line(G[i, j], G[i, j + 1], bcol, width)      # open rim
                elif below != above:
                    line(G[i, j], G[i, j + 1], bcol, width)
                elif below and i % rstep == 0:
                    line(G[i, j], G[i, j + 1], dim, 1)
        b, t = xyz(obj.get_base()), xyz(obj.get_tip())
        if sel:
            s = self.seg2d(b, t)
            if s:
                lines.append((s[0], s[1], "#e06c75", 1, tk.LAST, (6, 4)))
        dots.append((b, bcol, sel))
        dots.append((center_of(obj), bcol, sel))

    def collect_solid(self, obj, sel, fills, lines, dots):
        """Shaded front faces of a solids3d shape; hard edges where a flat face shows,
        outlines where a curved surface turns away, plus a few dim grid lines."""
        bc, fc = color_of(obj)
        bcol = self.safe(bc, DEFAULT_LINE)
        base = fc if self.rgb(fc or "") else bcol
        dim = self.blend(bcol, 0.35)
        width = 3.2 if sel else 1.6
        faces, edges = solids3d.draw_pieces(obj, self.eye())
        for corners, f in faces:
            pg = self.poly2d(list(corners))
            if pg:
                fills.append((pg[0], pg[1], self.blend(base, 0.15 + 0.55 * min(f * 1.2, 1.0))))
        for a, b, strong in edges:
            s = self.seg2d(a, b)
            if s:
                lines.append((s[0], s[1], bcol if strong else dim, width if strong else 1, None, None))
        dots.append((center_of(obj), bcol, sel))

    # ------------------------------------------------- infinite plane drawing
    def cam_d(self, p):
        """Distance in front of the camera (same math as project())."""
        if self.view:
            return float((np.asarray(p, float) - self.view["eye"]) @ self.view["fwd"])
        x, y, z = p[0] - self.target[0], p[1] - self.target[1], p[2] - self.target[2]
        y1 = x * math.sin(self.yaw) + y * math.cos(self.yaw)
        return self.dist + y1 * math.cos(self.pitch) - z * math.sin(self.pitch)

    def clip_near(self, pts):
        """Clip a 3D polygon to the part in front of the camera."""
        near = self.near()
        d = [self.cam_d(p) for p in pts]
        out = []
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            if d[i] >= near:
                out.append(pts[i])
            if (d[i] >= near) != (d[j] >= near):
                out.append(pts[i] + (near - d[i]) / (d[j] - d[i]) * (pts[j] - pts[i]))
        return out

    def clip_seg(self, a, b):
        near = self.near()
        a, b = np.asarray(a, float), np.asarray(b, float)
        da, db = self.cam_d(a), self.cam_d(b)
        if da < near and db < near:
            return None
        if da < near:
            a = a + (near - da) / (db - da) * (b - a)
        elif db < near:
            b = b + (near - db) / (da - db) * (a - b)
        return a, b

    def poly2d(self, corners):
        """(depth, flat screen coords) of a 3D polygon cut at the near plane, or None if all behind."""
        near = self.near()
        if any(self.cam_d(q) < near for q in corners):
            corners = self.clip_near([np.asarray(q, float) for q in corners])
            if len(corners) < 3:
                return None
            proj = [self.project(q) for q in corners]
            scr = self.clip_screen([q[:2] for q in proj], m=2000)
            if len(scr) < 3:
                return None
            return sum(q[2] for q in proj) / len(proj), [v for q in scr for v in q]
        proj = [self.project(q) for q in corners]
        if self.off_screen([q[0] for q in proj], [q[1] for q in proj]):
            return None
        return sum(q[2] for q in proj) / len(proj), [v for q in proj for v in q[:2]]

    def off_screen(self, xs, ys, m=20):
        """True when a shape lies wholly past one canvas edge (no point making a Tk item)."""
        return (max(xs) < -m or min(xs) > self._w + m or max(ys) < -m or min(ys) > self._h + m)

    def seg2d(self, a, b):
        """(depth, x0, y0, x1, y1) of a 3D segment cut at the near plane, or None."""
        cut = self.clip_seg(a, b)
        if cut is None:
            return None
        pa, pb = self.project(cut[0]), self.project(cut[1])
        if self.off_screen((pa[0], pb[0]), (pa[1], pb[1])):
            return None
        return (pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1])

    def clip_screen(self, pts, m=40):
        """Clip a 2D polygon to the canvas (+margin) so huge coords never reach Tk."""
        edges = ((0, -m, 1), (0, self._w + m, -1), (1, -m, 1), (1, self._h + m, -1))
        for axis, lim, sgn in edges:
            src, pts = pts, []
            for i in range(len(src)):
                a, b = src[i], src[(i + 1) % len(src)]
                ina, inb = (a[axis] - lim) * sgn >= 0, (b[axis] - lim) * sgn >= 0
                if ina:
                    pts.append(a)
                if ina != inb:
                    t = (lim - a[axis]) / (b[axis] - a[axis])
                    pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            if not pts:
                return []
        return pts

    def collect_plane(self, obj, sel, fills, lines, dots):
        P = self.project
        if is_lib_plane(obj):               # your Plane3d: through vec1's start, facing get_norm()
            ctr = np.array(center_of(obj), float)
            n = np.array(lib_plane_normal(obj), float)
            if np.linalg.norm(n) == 0:
                raise ValueError("plane normal is zero")
            n /= np.linalg.norm(n)
            u = np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0))
            u /= np.linalg.norm(u)
            v = np.cross(n, u)
        else:                               # viewer plane: carrier square's corners
            c = [np.array(q, float) for q in square_corners(obj)]
            ctr = sum(c) / 4
            u, v = c[1] - c[0], c[3] - c[0]
            u /= np.linalg.norm(u)
            v /= np.linalg.norm(v)
            n = np.cross(u, v)
            n /= np.linalg.norm(n)
        bc, fc = color_of(obj)
        color = self.safe(fc or bc, "#5c9dff")
        # fill: a quad far bigger than the scene, clipped to the camera and screen
        L = 1000 * max(self.dist, self.grid_ext, 1.0)
        quad = [ctr + su * L * u + sv * L * v for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        poly = self.clip_near(quad)
        if len(poly) >= 3:
            scr = self.clip_screen([P(q)[:2] for q in poly])
            if len(scr) >= 3:
                fills.append((math.inf, [k for q in scr for k in q], color,
                              "gray50" if sel else "gray25"))
        # grid on the plane so tilt reads clearly
        s = self.grid_step
        k = max(int(round(self.grid_ext / s)), 1)
        for i in range(-k, k + 1):
            col = self.blend(color, 0.8 if sel else 0.6) if i % 5 == 0 else self.blend(color, 0.35)
            for a, b in ((ctr + i * s * v - k * s * u, ctr + i * s * v + k * s * u),
                         (ctr + i * s * u - k * s * v, ctr + i * s * u + k * s * v)):
                cut = self.clip_seg(a, b)
                if cut:
                    pa, pb = P(cut[0]), P(cut[1])
                    lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), col, 1, None, None))
        # normal arrow + center point
        tip = self.clip_seg(ctr, ctr + n * s * 2)
        if tip:
            pa, pb = P(tip[0]), P(tip[1])
            lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]),
                          color, 3.2 if sel else 2, tk.LAST, None))
        dots.append((tuple(ctr), color, sel))

    @staticmethod
    def _circle(cx, cy, r, n=48):
        out = []
        for k in range(n + 1):
            t = 2 * math.pi * k / n
            out += [cx + r * math.cos(t), cy + r * math.sin(t)]
        return out

    def draw_grid(self):
        c, P = self.canvas, self.project
        E, s = self.grid_ext, self.grid_step
        n = int(round(E / s))
        near = self.near()
        for i in range(-n, n + 1):
            col = "#353a44" if i % 5 == 0 else "#262a31"
            for a, b in (((i * s, -E, 0), (i * s, E, 0)), ((-E, i * s, 0), (E, i * s, 0))):
                sg = self.seg2d(a, b)
                if sg:
                    c.create_line(*sg[1], fill=col)
        for axis, color, dim, label in ((0, "#ff6b6b", "#6b2f2f", "X"), (1, "#51cf66", "#2a5c33", "Y"),
                                        (2, "#5c9dff", "#2c4670", "Z")):
            neg, pos = [0.0] * 3, [0.0] * 3
            neg[axis], pos[axis] = -E, E
            sn, sp = self.seg2d(neg, (0, 0, 0)), self.seg2d((0, 0, 0), pos)
            if sn:
                c.create_line(*sn[1], fill=dim, width=1.5)
            if sp:
                c.create_line(*sp[1], fill=color, width=2, arrow=tk.LAST)
                if self.cam_d(pos) >= near:
                    c.create_text(sp[1][2] + 10, sp[1][3], text=label, fill=color, font=("Segoe UI", 10, "bold"))
            for i in range(-n, n + 1):
                if i and i % 5 == 0:
                    t = [0.0] * 3
                    t[axis] = i * s
                    if self.cam_d(t) < near:
                        continue
                    tx, ty, _, _ = P(t)
                    c.create_text(tx, ty + 8, text=fmt(i * s), fill=dim, font=("Segoe UI", 7))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
