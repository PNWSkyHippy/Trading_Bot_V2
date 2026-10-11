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
import csv
import math
import os
import runpy
import sys
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

Plane3d = getattr(class3d, "Plane3d", None)
Circle3d = getattr(class3d, "Circle3d", None)
Cylinder3d = getattr(class3d, "Cylinder3d", None)
Cone3d = getattr(class3d, "Cone3d", None)
ROUND_TYPES = tuple(c for c in (Circle3d, Cylinder3d, Cone3d) if c)   # Circle3d family


def is_lib_plane(obj):
    return Plane3d is not None and isinstance(obj, Plane3d)


def is_round(obj):
    return bool(ROUND_TYPES) and isinstance(obj, ROUND_TYPES)

SCENE_FILE = os.path.join(HERE, "scene3d.csv")
DEFAULT_SCRIPT = os.path.join(HERE, "test3d_lib.py")

# Rotation types are read from the library, so a new  ___rot  method shows up here.
ROT_TYPES = sorted((n for n in dir(_Geometry3d)
                    if n.endswith("rot") and callable(getattr(_Geometry3d, n))),
                   key=lambda n: (n == "vecrot", n))
KINDS = ("point3d", "line3d", "vector3d", "plane3d", "square3d", "cube3d", "sphere3d",
         "circle3d", "cylinder3d", "cone3d")
ALIASES = {"rotatex": "xrot", "rotatey": "yrot", "rotatez": "zrot",
           "rotatevec": "vecrot", "rotate": "vecrot", "translate": "move"}
GEOM_TYPES = (Point3d, Line3d, Square3d, Cube3d, Sphere3d) + ((Plane3d,) if Plane3d else ()) + ROUND_TYPES
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
    if is_lib_plane(obj):
        return None, obj.get_color()
    if isinstance(obj, (Cube3d, Square3d)) or is_round(obj):
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
        return {"op": "scale", "f": float(row[1])}
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
        return ["scale", num(tf["f"])]
    if op == "vecrot":
        a, b = tf["axis"]
        return ["vecrot", num(tf["deg"])] + [num(v) for v in a + b] + _pivot_fields(tf["pivot"])
    return [op, num(tf["deg"])] + _pivot_fields(tf["pivot"])


def tf_text(tf):
    op = tf["op"]
    if op == "move":
        return "move(" + ", ".join(fmt(v) for v in tf["d"]) + ")"
    if op == "scale":
        return f"scale({fmt(tf['f'])})"
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
        self.obj = None

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
        return cls(*args, bc=c1, fc=c2)
    raise ValueError(f"unknown kind {e.kind}")


def entry_from_obj(name, obj):
    """Snapshot a live library object as a scene entry (current geometry)."""
    c1, c2 = (str(c) if c else "" for c in color_of(obj))
    if is_lib_plane(obj):
        return Entry("plane3d", name, c2, c2, list(center_of(obj)) + list(lib_plane_normal(obj)) + [10.0])
    if is_round(obj):                  # center, edge point (vec1's end), height
        kind = ("cone3d" if Cone3d and isinstance(obj, Cone3d) else
                "cylinder3d" if Cylinder3d and isinstance(obj, Cylinder3d) else "circle3d")
        nums = list(xyz(obj.get_center())) + list(xyz(obj.get_vec1().get_end()))
        return Entry(kind, name, c1, c2, nums + ([obj.get_height()] if kind != "circle3d" else []))
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
                "# Transform rows follow their object (degrees):\n"
                "#   xrot|yrot|zrot,deg,pivot   vecrot,deg,ax,ay,az,bx,by,bz,pivot   move,dx,dy,dz   scale,f\n"
                "#   pivot = default | center | origin | point,x,y,z\n")
        w = csv.writer(f)
        for e in entries:
            w.writerow(e.row())
            for t in e.transforms:
                w.writerow(t)


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
        self.reset_camera()
        self.grid_step, self.grid_ext = 1.0, 10.0
        self._build_ui()
        sys.stdout = PaneWriter(self.out)
        sys.stderr = PaneWriter(self.out, "err")
        root.report_callback_exception = lambda *exc: traceback.print_exception(*exc)
        self.load_or_bootstrap()
        root.after(100, self.fit_view)

    # ------------------------------------------------------------- UI layout
    def _build_ui(self):
        outer = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        outer.pack(fill=tk.BOTH, expand=True)
        top = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        outer.add(top, weight=4)

        self.canvas = tk.Canvas(top, bg=BG, highlightthickness=0, width=950, height=640)
        top.add(self.canvas, weight=4)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", lambda e: self._drag_start(e, "orbit"))
        self.canvas.bind("<ButtonPress-3>", lambda e: self._drag_start(e, "pan"))
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<B3-Motion>", self._drag_move)
        self.canvas.bind("<MouseWheel>", self._wheel)

        panel = ttk.Frame(top, padding=6)
        top.add(panel, weight=1)
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
        ttk.Combobox(r1, textvariable=self.v_add, values=list(ADD_SPECS), width=9,
                     state="readonly").pack(side=tk.LEFT, padx=3)
        ttk.Button(r1, text="Add...", command=self.add_dialog).pack(side=tk.LEFT)

        r2 = ttk.Frame(p)
        r2.pack(fill=tk.X, pady=2)
        ttk.Button(r2, text="Run script...", command=self.ask_run_script).pack(side=tk.LEFT)
        ttk.Button(r2, text="Replay", command=self.replay).pack(side=tk.LEFT, padx=3)
        ttk.Button(r2, text="Keep script objs", command=self.keep_script_objs).pack(side=tk.LEFT)

        r3 = ttk.Frame(p)
        r3.pack(fill=tk.X, pady=2)
        ttk.Button(r3, text="Fit view", command=self.fit_view).pack(side=tk.LEFT)
        ttk.Button(r3, text="Reset view", command=lambda: (self.reset_camera(), self.fit_view())
                   ).pack(side=tk.LEFT, padx=3)
        ttk.Label(r3, text="Step deg").pack(side=tk.LEFT, padx=(8, 2))
        self.v_step = tk.StringVar(value="5")
        ttk.Spinbox(r3, from_=1, to=90, textvariable=self.v_step, width=4).pack(side=tk.LEFT)
        ttk.Label(r3, text="ms").pack(side=tk.LEFT, padx=(6, 2))
        self.v_delay = tk.StringVar(value="40")
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

        tf = ttk.Frame(p)
        tf.pack(fill=tk.BOTH, expand=True, pady=4)
        self.tree = ttk.Treeview(tf, columns=("kind",), height=11, selectmode="browse")
        self.tree.heading("#0", text="Object")
        self.tree.heading("kind", text="Type")
        self.tree.column("#0", width=170)
        self.tree.column("kind", width=90)
        sb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())

        ef = ttk.LabelFrame(p, text="Selected object", padding=4)
        ef.pack(fill=tk.X)
        self.edit_frame = ef
        g = 0
        self.v_name = tk.StringVar()
        ttk.Label(ef, text="Name").grid(row=g, column=0, sticky="w")
        ttk.Entry(ef, textvariable=self.v_name, width=14).grid(row=g, column=1, columnspan=2, sticky="we")
        ttk.Button(ef, text="Rename", command=self.rename).grid(row=g, column=3, sticky="we")
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
        ttk.Separator(ef).grid(row=g, column=0, columnspan=4, sticky="we", pady=3)
        g += 1
        self.v_mv = self._xyz_row(ef, g, "Move by", ("0", "0", "0"))
        ttk.Button(ef, text="Move", command=self.move_by).grid(row=g, column=4, sticky="we")
        g += 1
        self.v_to = self._xyz_row(ef, g, "Center to", ("0", "0", "0"))
        ttk.Button(ef, text="Go", command=self.move_to).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Label(ef, text="Scale x").grid(row=g, column=0, sticky="w")
        self.v_scale = tk.StringVar(value="2")
        ttk.Entry(ef, textvariable=self.v_scale, width=6).grid(row=g, column=1, sticky="we")
        ttk.Label(ef, text="(about origin)").grid(row=g, column=2, columnspan=2, sticky="w")
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

    def pick(self, var):
        res = colorchooser.askcolor(color=var.get() or None, parent=self.root)
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
        try:
            save_scene(SCENE_FILE, self.entries)
        except OSError as exc:
            print(f"Could not save {SCENE_FILE}: {exc}")

    def rebuild(self, e):
        """Recreate e.obj from its CSV row, then replay its transforms instantly."""
        try:
            obj = build(e)
        except Exception as exc:
            print(f"{e.name}: cannot build {e.kind}: {exc}")
            e.obj = None
            return
        for row in e.transforms:
            try:
                run_tf(obj, parse_row(row), 1.0)
            except Exception as exc:
                print(f"{e.name}: transform {','.join(row)} failed: {exc}")
        e.obj = obj

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
        self.tree.delete(*self.tree.get_children())
        self.tree.insert("", "end", "scene", text="Scene (scene3d.csv)", open=True)
        for i, e in enumerate(self.entries):
            self.tree.insert("scene", "end", f"s{i}", text=e.name, values=(e.kind,))
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
                    self.selected = sel
        self.update_grid()
        self.redraw()

    def sel_entry(self):
        if self.selected and self.selected[0] == "s":
            return self.selected[1]
        print("Select a scene object first (script objects: use 'Keep script objs').")
        return None

    def on_select(self, _event=None):
        iid = (self.tree.selection() or [""])[0]
        if iid.startswith("s") and iid != "scene" and iid != "script":
            e = self.entries[int(iid[1:])]
            self.selected = ("s", e)
            self.v_name.set(e.name)
            self.v_c1.set(e.c1)
            self.v_c2.set(e.c2)
            if e.obj is not None:
                c = center_of(e.obj)
                for v, val in zip(self.v_to, c):
                    v.set(fmt(val))
            self.lb_tf.delete(0, "end")
            for row in e.transforms:
                self.lb_tf.insert("end", ",".join(row))
            if e.obj is not None:
                print(f"{e.name}: {e.obj}")
        elif iid.startswith("r") and iid[1:].isdigit():
            idx = int(iid[1:])
            self.selected = ("r", idx)
            name, obj = self.script_objs[idx]
            print(f"[script] {name}: {obj}")
        else:
            self.selected = None
        self.redraw()

    # -------------------------------------------------------------- editing
    def add_dialog(self):
        label = self.v_add.get()
        spec = ADD_SPECS[label]
        kind = {"Point": "point3d", "Line": "line3d", "Vector": "vector3d", "Plane": "plane3d",
                "Square": "square3d", "Cube": "cube3d", "Sphere": "sphere3d",
                "Circle": "circle3d", "Cylinder": "cylinder3d", "Cone": "cone3d"}[label]
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
                ttk.Button(frm, text="...", width=3, command=lambda v=v: self.pick(v)).grid(row=r, column=3)
                fields[key] = ("color", v)
            elif isinstance(ftype, tuple):
                v = tk.StringVar(value=default)
                ttk.Combobox(frm, textvariable=v, values=ftype, width=6, state="readonly").grid(
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
                e = Entry(kind, name, vals.get("c1", ""), vals.get("c2", ""), add_nums(label, vals))
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

    def rename(self):
        e = self.sel_entry()
        if e is None:
            return
        new = self.v_name.get().strip()
        if not new or any(o.name == new and o is not e for o in self.entries):
            print(f"Rename: '{new}' is empty or already used")
            return
        e.name = new
        self.rebuild(e)
        self.save()
        self.refresh()

    def apply_colors(self):
        e = self.sel_entry()
        if e is None:
            return
        c1, c2 = self.v_c1.get().strip(), self.v_c2.get().strip()
        for c in (c1, c2):
            if c and not self.valid_color(c):
                print(f"Unknown color '{c}'")
                return
        e.c1, e.c2 = c1, c2
        self.rebuild(e)
        self.save()
        self.redraw()
        print(f"{e.name}: {e.obj}")

    def _queue_tf(self, e, tf):
        """Animate tf on entry e, then store it under the object and save."""
        def job():
            obj = e.obj                      # read when the job starts (queued jobs)
            if obj is None:
                return
            print(f"{e.name}.{tf_text(tf)}")
            yield from self.anim_transform(obj, tf)
            e.transforms.append(tf_to_row(tf))
            self.rebuild(e)                  # exact one-shot result, same as next load
            self.save()
            if self.selected and self.selected[1] is e:
                self.lb_tf.insert("end", ",".join(e.transforms[-1]))
                for v, val in zip(self.v_to, center_of(e.obj)):
                    v.set(fmt(val))
            print(f"{e.name} now: {e.obj}")
        self.enqueue(job())

    def move_by(self):
        e = self.sel_entry()
        if e is None:
            return
        try:
            d = self._floats(self.v_mv)
        except ValueError:
            print("Move: enter three numbers")
            return
        self._queue_tf(e, {"op": "move", "d": d})

    def move_to(self):
        e = self.sel_entry()
        if e is None or e.obj is None:
            return
        try:
            target = self._floats(self.v_to)
        except ValueError:
            print("Center to: enter three numbers")
            return
        d = tuple(t - c for t, c in zip(target, center_of(e.obj)))
        self._queue_tf(e, {"op": "move", "d": d})

    def scale_by(self):
        e = self.sel_entry()
        if e is None or e.obj is None:
            return
        try:
            f = float(self.v_scale.get())
        except ValueError:
            print("Scale: enter a number")
            return
        self._queue_tf(e, {"op": "scale", "f": f})

    def rotate(self):
        e = self.sel_entry()
        if e is None or e.obj is None:
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
        self._queue_tf(e, tf)

    def undo_tf(self):
        e = self.sel_entry()
        if e is None or not e.transforms:
            return
        row = e.transforms.pop()
        self.rebuild(e)
        self.save()
        self.lb_tf.delete("end")
        print(f"{e.name}: removed {','.join(row)}")
        self.redraw()

    def delete_selected(self):
        e = self.sel_entry()
        if e is None:
            return
        self.entries = [o for o in self.entries if o is not e]
        self.selected = None
        self.save()
        self.refresh()
        print(f"Deleted {e.name}")

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
        pivot = pivot_point(obj, tf)
        start = center_of(obj)
        for _ in range(n):
            run_tf(obj, tf, 1.0 / n)
            self.overlay = self.make_overlay(obj, tf, pivot, start)
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

    def _drag_start(self, ev, mode):
        self._drag = (mode, ev.x, ev.y)

    def _drag_move(self, ev):
        if not self._drag:
            return
        mode, x0, y0 = self._drag
        dx, dy = ev.x - x0, ev.y - y0
        self._drag = (mode, ev.x, ev.y)
        if mode == "orbit":
            self.yaw -= dx * 0.01
            self.pitch = max(-1.55, min(1.55, self.pitch + dy * 0.01))
        else:
            cy, sy = math.cos(self.yaw), math.sin(self.yaw)
            cp, sp = math.cos(self.pitch), math.sin(self.pitch)
            right = np.array((cy, -sy, 0.0))
            up = np.array((sy * sp, cy * sp, cp))
            self.target = tuple(np.array(self.target) - right * dx / self.scale + up * dy / self.scale)
        self.redraw()

    def _wheel(self, ev):
        self.scale *= 1.1 ** (ev.delta / 120)
        self.redraw()

    def project(self, p):
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
        pts = []
        for _name, obj, _sel in self.visible_objects():
            try:
                if isinstance(obj, Sphere3d):
                    c, r = center_of(obj), obj.get_radius()
                    pts += [tuple(np.add(c, s * r * np.eye(3)[i])) for i in range(3) for s in (-1, 1)]
                elif is_round(obj):
                    ctr, n, r, h = round_geom(obj)
                    pts += [tuple(q) for q in ring(ctr, n, r, 8)]
                    if h:
                        pts.append(tuple(ctr + n * h))
                else:
                    pts += [xyz(p) for p in points_of(obj)]
            except Exception:
                pass
        return pts

    def fit_view(self):
        self.canvas.update_idletasks()
        pts = self.all_points()
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
        pts = self.all_points()
        ext = max([abs(c) for p in pts for c in p] + [5.0]) * 1.1
        raw = ext / 10
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
        self.grid_step = step
        self.grid_ext = math.ceil(ext / step) * step

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
        if self.v_show_scene.get():
            for e in self.entries:
                if e.obj is not None:
                    sel = self.selected is not None and self.selected[0] == "s" and self.selected[1] is e
                    out.append((e.name, e.obj, sel))
        if self.v_show_script.get():
            for i, (name, obj) in enumerate(self.script_objs):
                sel = (self.selected == ("r", i)) or obj is self.anim_target
                out.append((name, obj, sel))
        return out

    def redraw(self):
        c = self.canvas
        c.delete("all")
        self._w, self._h = c.winfo_width(), c.winfo_height()
        if self.v_grid.get():
            self.draw_grid()
        fills, lines, dots = [], [], []
        P = self.project
        for name, obj, sel in self.visible_objects():
            try:
                self.collect(obj, sel, fills, lines, dots)
            except Exception as exc:          # e.g. a half-built object from a script
                c.create_text(10, 10, anchor="nw", fill="#ff7b72", text=f"{name}: {exc}")
        for item in sorted(fills, key=lambda t: -t[0]):
            coords, fill = item[1], item[2]
            if len(coords) == 4:              # sphere disc: x0,y0,x1,y1
                c.create_oval(*coords, fill=fill, outline="")
            else:                             # 4th field: stipple for see-through planes
                c.create_polygon(*coords, fill=fill, outline="",
                                 stipple=item[3] if len(item) > 3 else "")
        for depth, coords, color, width, arrow, dash in sorted(lines, key=lambda t: -t[0]):
            c.create_line(*coords, fill=color, width=width, arrow=arrow, dash=dash,
                          arrowshape=(12, 14, 5), capstyle=tk.ROUND)
        labelled = set()
        for p, color, sel in dots:
            sx, sy, _d, _f = P(p)
            r = 4 if sel else 3
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=color, outline="#000")
            key = tuple(round(v, 2) for v in p)
            if self.v_coords.get() and key not in labelled:
                labelled.add(key)
                c.create_text(sx + 6, sy - 7, anchor="w", font=("Segoe UI", 7),
                              fill="#e8e8e8" if sel else "#8f98a6",
                              text="(" + ", ".join(fmt(v) for v in p) + ")")
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
                      text="left-drag orbit  |  right-drag pan  |  wheel zoom")

    def collect(self, obj, sel, fills, lines, dots):
        P = self.project
        width = 3.2 if sel else 1.6
        bc, fc = color_of(obj)

        def seg(a, b, color, arrow=None):
            pa, pb = P(a), P(b)
            lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), color, width, arrow, None))

        def face(corners, fill):
            if not fill:
                return
            proj = [P(q) for q in corners]
            fills.append((sum(q[2] for q in proj) / len(proj),
                          [v for q in proj for v in q[:2]], fill))

        if isinstance(obj, Sphere3d):
            ctr, r = center_of(obj), float(obj.get_radius())
            color = self.safe(obj.get_color(), DEFAULT_LINE)
            sx, sy, depth, f = P(ctr)
            fills.append((depth, (sx - r * f, sy - r * f, sx + r * f, sy + r * f),
                          self.blend(color, FILL_ALPHA)))
            ring = self.blend(color, 0.55)
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
                lines.append((dsum / 37, coords, ring, 1, None, None))
            lines.append((depth - r, (sx - r * f, sy - r * f, sx + r * f, sy + r * f, sx - r * f, sy - r * f),
                          color, width, None, None))
            lines[-1] = (depth - r, self._circle(sx, sy, r * f), color, width, None, None)
            dots.append((ctr, color, sel))
            return
        if getattr(obj, "_viewer_plane", False) or is_lib_plane(obj):
            self.collect_plane(obj, sel, fills, lines, dots)
            return
        if is_round(obj):
            ctr, n, r, h = round_geom(obj)
            bcol = self.safe(bc, DEFAULT_LINE)
            fcol = self.blend(fc, FILL_ALPHA) if self.rgb(fc or "") else None
            dim = self.blend(bcol, 0.45)
            base = ring(ctr, n, r)
            face(base[:-1], fcol)
            for a, b in zip(base, base[1:]):
                seg(tuple(a), tuple(b), bcol)
            if Cone3d and isinstance(obj, Cone3d):
                apex = ctr + n * h
                for a, b in zip(base[:-1], base[1:]):
                    face([a, b, apex], fcol)
                for a in base[:-1:6]:
                    pa, pb = P(a), P(apex)
                    lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), dim, 1, None, None))
                dots.append((tuple(apex), bcol, sel))
            elif Cylinder3d and isinstance(obj, Cylinder3d):
                top = [q + n * h for q in base]
                face(top[:-1], fcol)
                for i in range(len(base) - 1):
                    face([base[i], base[i + 1], top[i + 1], top[i]], fcol)
                    seg(tuple(top[i]), tuple(top[i + 1]), bcol)
                for a, b in zip(base[:-1:6], top[:-1:6]):
                    pa, pb = P(a), P(b)
                    lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), dim, 1, None, None))
                dots.append((tuple(ctr + n * h), bcol, sel))
            else:                           # flat circle: short normal arrow shows which way it faces
                pa, pb = P(ctr), P(ctr + n * r * 0.6)
                lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), dim, 1, tk.LAST, None))
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

    # ------------------------------------------------- infinite plane drawing
    def cam_d(self, p):
        """Distance in front of the camera (same math as project())."""
        x, y, z = p[0] - self.target[0], p[1] - self.target[1], p[2] - self.target[2]
        y1 = x * math.sin(self.yaw) + y * math.cos(self.yaw)
        return self.dist + y1 * math.cos(self.pitch) - z * math.sin(self.pitch)

    def clip_near(self, pts):
        """Clip a 3D polygon to the part in front of the camera."""
        near = 0.06 * self.dist
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
        near = 0.06 * self.dist
        da, db = self.cam_d(a), self.cam_d(b)
        if da < near and db < near:
            return None
        if da < near:
            a = a + (near - da) / (db - da) * (b - a)
        elif db < near:
            b = b + (near - db) / (da - db) * (a - b)
        return a, b

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
        for i in range(-n, n + 1):
            col = "#353a44" if i % 5 == 0 else "#262a31"
            for a, b in (((i * s, -E, 0), (i * s, E, 0)), ((-E, i * s, 0), (E, i * s, 0))):
                (ax, ay, _, _), (bx, by, _, _) = P(a), P(b)
                c.create_line(ax, ay, bx, by, fill=col)
        for axis, color, dim, label in ((0, "#ff6b6b", "#6b2f2f", "X"), (1, "#51cf66", "#2a5c33", "Y"),
                                        (2, "#5c9dff", "#2c4670", "Z")):
            neg, pos = [0.0] * 3, [0.0] * 3
            neg[axis], pos[axis] = -E, E
            o = P((0, 0, 0))
            pn, pp = P(neg), P(pos)
            c.create_line(pn[0], pn[1], o[0], o[1], fill=dim, width=1.5)
            c.create_line(o[0], o[1], pp[0], pp[1], fill=color, width=2, arrow=tk.LAST)
            c.create_text(pp[0] + 10, pp[1], text=label, fill=color, font=("Segoe UI", 10, "bold"))
            for i in range(-n, n + 1):
                if i and i % 5 == 0:
                    t = [0.0] * 3
                    t[axis] = i * s
                    tx, ty, _, _ = P(t)
                    c.create_text(tx, ty + 8, text=fmt(i * s), fill=dim, font=("Segoe UI", 7))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
