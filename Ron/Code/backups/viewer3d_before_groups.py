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
import shutil
import sys
import threading
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
         "circle3d", "cylinder3d", "cone3d", "curvedcylinder3d", "curvedtorus3d")
ALIASES = {"rotatex": "xrot", "rotatey": "yrot", "rotatez": "zrot",
           "rotatevec": "vecrot", "rotate": "vecrot", "translate": "move"}
GEOM_TYPES = (Point3d, Line3d, Square3d, Cube3d, Sphere3d) + ((Plane3d,) if Plane3d else ()) + ROUND_TYPES + TUBE_TYPES
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
    if isinstance(obj, (Cube3d, Square3d) + TUBE_TYPES) or is_round(obj):
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
        self.mat, self.mat_scale = "", 1.0   # POV-Ray material spec (see pov_export.material)
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
                "# Transform rows follow their object (degrees):\n"
                "#   xrot|yrot|zrot,deg,pivot   vecrot,deg,ax,ay,az,bx,by,bz,pivot   move,dx,dy,dz   scale,f\n"
                "#   pivot = default | center | origin | point,x,y,z\n"
                "# pov,<material>,<texture scale> after an object row sets its POV-Ray material\n")
        w = csv.writer(f)
        for e in entries:
            w.writerow(e.row())
            if e.mat:
                w.writerow(["pov", e.mat, num(e.mat_scale)])
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
        try:                           # Tk 9: two-finger trackpad scroll arrives as its own event
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
        ttk.Combobox(r1, textvariable=self.v_add, values=list(ADD_SPECS), width=11,
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
        self.root.bind("<F9>", lambda _e: self.render_pov())

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
        self.tree.bind("<Double-Button-1>", lambda _e: self.open_props())
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())

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
        g += 1
        ttk.Separator(ef).grid(row=g, column=0, columnspan=4, sticky="we", pady=3)
        g += 1
        self.v_mv = self._xyz_row(ef, g, "Move by", ("0", "0", "0"))
        ttk.Button(ef, text="Move", command=self.move_by).grid(row=g, column=4, sticky="we")
        g += 1
        ttk.Button(ef, text="Move all by these (not planes)", command=self.move_all).grid(
            row=g, column=1, columnspan=4, sticky="we")
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
            self._show_material(e)
            if e.obj is not None:
                c = center_of(e.obj)
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
        else:
            self.selected = None
        self.redraw()

    # -------------------------------------------------------------- editing
    def add_dialog(self):
        label = self.v_add.get()
        spec = ADD_SPECS[label]
        kind = {"Point": "point3d", "Line": "line3d", "Vector": "vector3d", "Plane": "plane3d",
                "Square": "square3d", "Cube": "cube3d", "Sphere": "sphere3d",
                "Circle": "circle3d", "Cylinder": "cylinder3d", "Cone": "cone3d",
                "Bend": "curvedcylinder3d", "CurvedTorus": "curvedtorus3d"}[label]
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
                src = vals.get("src", "(none)")
                if label == "Bend" and src not in ("", "(none)"):
                    # Continue smoothly off the end of an existing bend; store the new bend's own geometry.
                    prev = next(o.obj for o in self.entries if o.name == src)
                    nxt = prev.make_next(math.radians(vals["a"]), math.radians(vals["tw"] or 0),
                                         bend_radius=vals["R"], tube_radius=vals["r"])
                    nums = entry_from_obj(name, nxt).nums
                else:
                    nums = add_nums(label, vals)
                e = Entry(kind, name, vals.get("c1", ""), vals.get("c2", ""), nums)
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
        if self._props is None:
            dlg = tk.Toplevel(self.root)
            dlg.transient(self.root)
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

    # ---- POV-Ray materials:  group -> {shown name: spec}  (spec format: pov_export.material)
    def _load_pov_lib(self):
        lib = pov_export.library()
        def done():
            self.pov_lib = lib
            self._mat_groups()
            if self.selected and self.selected[0] == "s":
                self._show_material(self.selected[1])
        self.root.after(0, done)

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
        e.mat = self.mat_choices.get(self.v_mat_grp.get(), {}).get(self.v_mat_name.get(), "")
        e.mat_scale = scale
        self.save()
        print(f"{e.name}: material {e.mat or 'own color'}" + (f", scale {fmt(scale)}" if scale != 1 else ""))

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
        self.canvas.focus_set()              # so fly keys reach the canvas
        self._drag = (mode, ev.x, ev.y)

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
        self.redraw()
        return "break"

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

    def _touch_scroll(self, ev):
        """Two-finger trackpad scroll (Tk 9): vertical swipe zooms."""
        try:
            _dx, dy = (float(v) for v in self.root.tk.splitlist(
                self.root.tk.call("tk::PreciseScrollDeltas", ev.delta)))
        except (tk.TclError, ValueError):
            return
        self.scale *= 1.01 ** max(-20, min(20, -dy))
        self.redraw()

    def _wheel(self, ev):
        # Windows and Tk 9 send +-120 per notch; older Mac Tk sends small counts (+-1..+-10).
        steps = ev.delta / 120 if abs(ev.delta) >= 120 else max(-3, min(3, ev.delta * 0.5))
        self.scale *= 1.1 ** steps
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
        return [p for _name, pts in self.points_by_object() for p in pts]

    def points_by_object(self):
        out = []
        for _name, obj, _sel in self.visible_objects():
            pts = []
            out.append((_name, pts))
            try:
                if isinstance(obj, Sphere3d):
                    c, r = center_of(obj), obj.get_radius()
                    pts += [tuple(np.add(c, s * r * np.eye(3)[i])) for i in range(3) for s in (-1, 1)]
                elif tube_bends(obj) is not None:
                    for b in tube_bends(obj):
                        pts += [xyz(b.surface_point(t / 4, f * math.pi / 2)) for t in range(5) for f in range(4)]
                elif is_round(obj):
                    ctr, n, r, h = round_geom(obj)
                    pts += [tuple(q) for q in ring(ctr, n, r, 8)]
                    if h:
                        pts.append(tuple(ctr + n * h))
                else:
                    pts += [xyz(p) for p in points_of(obj)]
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
        owner = {id(e.obj): e for e in self.entries if e.obj is not None}
        for name, obj, _sel in self.visible_objects():
            src = owner.get(id(obj))
            mat = {"mat": src.mat, "mat_scale": src.mat_scale} if src else {}
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
                                  "nums": list(np.mean(q, axis=0)) + list(nrm) + [10.0], **mat})
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
                      text="left-drag orbit  |  right-drag pan  |  wheel zoom  |  "
                           "WASD move  Q/E down/up  arrows look  (Shift = faster, click view first)")

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
        if is_round(obj):
            ctr, n, r, h = round_geom(obj)
            bcol = self.safe(bc, DEFAULT_LINE)
            fcol = self.blend(fc, FILL_ALPHA) if self.rgb(fc or "") else None
            dim = self.blend(bcol, 0.45)
            base = ring(ctr, n, r)
            fwd, _lv, _rt = self._cam_axes()
            eye = np.array(self.target, float) - fwd * self.dist
            shade = fc if self.rgb(fc or "") else None

            def lit(corners, out_n, cap=False):
                """Shade like the bent tubes; False (nothing drawn) when facing away from the camera."""
                to_eye = eye - sum(corners) / len(corners)
                facing = float(np.dot(out_n, to_eye)) / (
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
                        pa, pb = P(base[i]), P(tip(i))
                        lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), dim, 1, None, None))

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
        fwd, _lv, _rt = self._cam_axes()
        eye = np.array(self.target, float) - fwd * self.dist
        bends = tube_bends(obj)
        single = len(bends) == 1
        K = 16                                          # facets around the tube

        def line(a, b, color, w):
            pa, pb = P(a), P(b)
            lines.append(((pa[2] + pb[2]) / 2, (pa[0], pa[1], pb[0], pb[1]), color, w, None, None))

        for bend in bends:
            c = np.array(xyz(bend.get_bend_center()), float)
            n = np.array(bend.get_norm(), float)
            R, r, ang = bend.get_bend_radius(), bend.get_tube_radius(), bend.get_angle()
            M = max(4, int(math.ceil(48 * ang / (2 * math.pi))))     # steps along the bend
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
                    facing = float(np.dot(nrm[i][j] + nrm[i + 1][j + 1], to_eye)) / (
                        2 * np.linalg.norm(to_eye) + 1e-12)
                    if facing <= 0:
                        continue
                    vis[i][j] = True
                    proj = [P(q) for q in quad]
                    fills.append((sum(q[2] for q in proj) / 4, [v for q in proj for v in q[:2]],
                                  self.blend(base, 0.15 + 0.55 * min(facing * 1.2, 1.0))))
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
                    cap = [P(q) for q in grid[i][:-1]]
                    to_eye = eye - np.array(xyz(bend.spine_point(t)))
                    out = -np.array(bend.tangent(0.0)) if i == 0 else np.array(bend.tangent(1.0))
                    if float(np.dot(out, to_eye)) > 0:
                        fills.append((sum(q[2] for q in cap) / K, [v for q in cap for v in q[:2]],
                                      self.blend(base, 0.45)))
                dots.append((xyz(bend.get_spine_start()), bcol, sel))
                dots.append((xyz(bend.get_spine_end()), bcol, sel))
        dots.append((xyz(obj.get_center()), bcol, sel))

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
