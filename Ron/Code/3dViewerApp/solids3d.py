"""Viewer support for the class3d solids added 2026-10-15: prisms (3..20 sides),
truncated prisms, pyramids, truncated cones, ellipsoids, the four polyhedra,
spherical caps and hemispheres.

Everything kind-specific lives here so viewer3d.py only needs small hooks:
  kind_of / build / to_nums      CSV row <-> live library object
  colors                         (border, fill) the viewer draws with
  mesh                           points + faces for drawing (all are convex)
  ADD_SPECS / add_nums           the Add dialog
  prop_spec / prop_nums          the Properties editor
  pov_shape                      POV-Ray text pieces for pov_export

CSV numbers per kind (all points are world x,y,z):
  prism3d            base center, base corner, top center, sides
  truncatedprism3d   base center, base corner, top center, sides, top scale
  pyramid3d          base center, base corner, apex, sides
  truncatedcone3d    base center, base edge point, top center, top scale
  ellipsoid3d        center, x tip, y tip, z tip
  octahedron3d .. rhombicdodecahedron3d   center, edge length, x axis dir, y axis dir
  sphericalcap3d     sphere center, pole, cap height
  hemisphere3d       sphere center, pole
"""
import math

import numpy as np

import class3d
from class3d import Point3d

_g = lambda n: getattr(class3d, n, None)   # noqa: E731 - library may not have every class
Prism3d, TruncatedPrism3d, Pyramid3d = _g("Prism3d"), _g("TruncatedPrism3d"), _g("Pyramid3d")
TruncatedCone3d, Ellipsoid3d = _g("TruncatedCone3d"), _g("Ellipsoid3d")
SphericalCap3d, Hemisphere3d = _g("SphericalCap3d"), _g("Hemisphere3d")
POLY = {"octahedron3d": _g("Octahedron3d"), "dodecahedron3d": _g("Dodecahedron3d"),
        "icosahedron3d": _g("Icosahedron3d"), "rhombicdodecahedron3d": _g("RhombicDodecahedron3d")}
POLY = {k: c for k, c in POLY.items() if c}

# Most specific class first (Pyramid is a TruncatedPrism is a Prism, Hemisphere is a cap).
_ORDER = [("pyramid3d", Pyramid3d), ("truncatedprism3d", TruncatedPrism3d), ("prism3d", Prism3d),
          ("truncatedcone3d", TruncatedCone3d), ("ellipsoid3d", Ellipsoid3d),
          ("hemisphere3d", Hemisphere3d), ("sphericalcap3d", SphericalCap3d)] + list(POLY.items())
_ORDER = [(k, c) for k, c in _ORDER if c]
KINDS = tuple(k for k, _c in _ORDER)
TYPES = tuple(c for _k, c in _ORDER)
ONE_COLOR = tuple(c for c in (Ellipsoid3d, SphericalCap3d) if c)   # library keeps a single color


def xyz(p):
    return np.array([float(c) for c in p.get_xyz()])


def kind_of(obj):
    for k, cls in _ORDER:
        if isinstance(obj, cls):
            return k
    return None


def is_solid(obj):
    return bool(TYPES) and isinstance(obj, TYPES)


def colors(obj):
    """(border, fill).  Ellipsoid / cap keep one color in the library (the fill here);
    the viewer's border color rides along as _viewer_bc."""
    if isinstance(obj, ONE_COLOR):
        return getattr(obj, "_viewer_bc", None), obj.get_color()
    return obj.get_bc(), obj.get_fc()


def _unit(v, what="vector"):
    v = np.array(v, float)
    if np.linalg.norm(v) < 1e-12:
        raise ValueError(f"{what} cannot be zero")
    return v / np.linalg.norm(v)


def _perp_dir(old, n):
    d = np.array(old, float) - np.dot(old, n) * n
    if np.linalg.norm(d) < 1e-9:
        d = np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0))
    return d / np.linalg.norm(d)


# ----------------------------------------------------------------------------
# polyhedra are saved as center + edge + turn; the turn is found by fitting the
# current corners onto a fresh unturned copy (Kabsch)
# ----------------------------------------------------------------------------
def _canon(cls, edge):
    fresh = cls(Point3d(0, 0, 0), edge)
    return np.array([xyz(v) for v in fresh._verts])


def _poly_frame(obj):
    c = xyz(obj.get_center())
    W = np.array([xyz(v) for v in obj._verts]) - c
    V = _canon(type(obj), obj.get_length())
    U, _S, Vt = np.linalg.svd(V.T @ W)
    d = np.sign(np.linalg.det(Vt.T @ U.T)) or 1.0
    R = Vt.T @ np.diag([1, 1, d]) @ U.T          # W ~ V @ R.T
    return c, R[:, 0], R[:, 1]


# ----------------------------------------------------------------------------
# CSV <-> object
# ----------------------------------------------------------------------------
def build(kind, n, c1, c2, name):
    n = [float(v) for v in n]
    P = lambda i: Point3d(*n[i:i + 3])                     # noqa: E731
    d = lambda i, j: np.subtract(n[j:j + 3], n[i:i + 3])   # noqa: E731
    if kind in ("prism3d", "truncatedprism3d", "pyramid3d"):
        h = float(np.linalg.norm(d(0, 6)))
        if h <= 0:
            raise ValueError("height must be > 0")
        sides = int(round(n[9]))
        if kind == "prism3d":
            return Prism3d(P(0), P(3), sides, h, bc=c1, fc=c2, name=name, normal=d(0, 6))
        if kind == "pyramid3d":
            return Pyramid3d(P(0), P(3), h, sides, bc=c1, fc=c2, name=name, normal=d(0, 6))
        return TruncatedPrism3d(P(0), P(3), sides, h, n[10], bc=c1, fc=c2, name=name, normal=d(0, 6))
    if kind == "truncatedcone3d":
        h = float(np.linalg.norm(d(0, 6)))
        return TruncatedCone3d(P(0), P(3), h, n[9], bc=c1, fc=c2, name=name, normal=d(0, 6))
    if kind == "ellipsoid3d":
        obj = Ellipsoid3d(P(0), 1, 1, 1, color=c2 or c1, name=name)
        for tip, i in ((obj._tip_x, 3), (obj._tip_y, 6), (obj._tip_z, 9)):
            tip.set_xyz(*n[i:i + 3])
        obj._viewer_bc = c1
        return obj
    if kind in ("sphericalcap3d", "hemisphere3d"):
        r = float(np.linalg.norm(d(0, 3)))
        if kind == "hemisphere3d":
            obj = Hemisphere3d(P(0), r, d(0, 3), color=c2 or c1, name=name)
        else:
            obj = SphericalCap3d(P(0), r, n[6], d(0, 3), color=c2 or c1, name=name)
        obj._viewer_bc = c1
        return obj
    if kind in POLY:
        c = np.array(n[0:3])
        obj = POLY[kind](Point3d(*c), n[3], bc=c1, fc=c2, name=name)
        ax = _unit(n[4:7], "x axis")
        ay = _perp_dir(n[7:10], ax)
        R = np.column_stack([ax, ay, np.cross(ax, ay)])
        for v in obj._verts:
            v.set_xyz(*(c + R @ (xyz(v) - c)))
        return obj
    raise ValueError(f"unknown kind {kind}")


def to_nums(obj):
    k = kind_of(obj)
    if k in ("prism3d", "truncatedprism3d", "pyramid3d"):
        nums = (list(xyz(obj._center_point)) + list(xyz(obj._edge)) + list(xyz(obj._top))
                + [obj.get_num_faces()])
        return nums + ([obj.get_top_scale()] if k == "truncatedprism3d" else [])
    if k == "truncatedcone3d":
        return (list(xyz(obj._cent)) + list(xyz(obj._rad_edge)) + list(xyz(obj._top))
                + [obj.get_top_scale()])
    if k == "ellipsoid3d":
        return [v for p in obj._points() for v in xyz(p)]
    if k == "sphericalcap3d":
        return list(xyz(obj._cent)) + list(xyz(obj._pole)) + [obj.get_height()]
    if k == "hemisphere3d":
        return list(xyz(obj._cent)) + list(xyz(obj._pole))
    if k in POLY:
        c, ax, ay = _poly_frame(obj)
        return list(c) + [obj.get_length()] + list(ax) + list(ay)
    raise TypeError(type(obj).__name__)


# ----------------------------------------------------------------------------
# drawing mesh: (points Nx3, faces [index tuples], smooth flags, dim grid edges)
# ----------------------------------------------------------------------------
def _grid(rings, seg):
    """Faces of a lat/long band grid: ring i point j = i*seg + j."""
    faces = []
    for i in range(len(rings) - 1):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    return faces


def mesh(obj, seg=36):
    k = kind_of(obj)
    if k in ("prism3d", "truncatedprism3d", "pyramid3d") or k in POLY:
        pts = np.array([xyz(p) for p in obj.get_points()])
        faces = [tuple(f) for f in obj.get_faces()]
        return pts, faces, [False] * len(faces), set()
    if k == "truncatedcone3d":
        c, top = xyz(obj._cent), xyz(obj._top)
        r1, r2 = obj.get_radius(), obj.get_top_radius()
        n = _unit(top - c)
        u = _perp_dir(xyz(obj._rad_edge) - c, n)
        w = np.cross(n, u)
        ang = [2 * math.pi * j / seg for j in range(seg)]
        ring = lambda o, r: [o + r * (math.cos(a) * u + math.sin(a) * w) for a in ang]  # noqa: E731
        pts = ring(c, r1) + ring(top, max(r2, 1e-9))
        faces = _grid([0, 1], seg)
        smooth = [True] * len(faces)
        faces.append(tuple(range(seg)))
        smooth.append(False)
        if r2 > 1e-9:
            faces.append(tuple(range(seg, 2 * seg)))
            smooth.append(False)
        step = max(1, seg // 8)
        grid = {(j, j + seg) for j in range(0, seg, step)}
        return np.array(pts), faces, smooth, grid
    if k == "ellipsoid3d":
        c = xyz(obj.get_center())
        ax, ay, az = obj.get_axes()
        rx, ry, rz = obj.get_radii()
        lats = [-math.pi / 2 + math.pi * i / 16 for i in range(1, 16)]
        pts = [c + math.cos(la) * (ax * rx * math.cos(lo) + ay * ry * math.sin(lo)) + az * rz * math.sin(la)
               for la in lats for lo in (2 * math.pi * j / seg for j in range(seg))]
        south, north = len(pts), len(pts) + 1
        pts += [c - az * rz, c + az * rz]
        faces = _grid(lats, seg)
        last = (len(lats) - 1) * seg
        faces += [((j + 1) % seg, j, south) for j in range(seg)]
        faces += [(last + j, last + (j + 1) % seg, north) for j in range(seg)]
        return np.array(pts), faces, [True] * len(faces), _dim_edges(len(lats), seg, 4, 6)
    if k in ("sphericalcap3d", "hemisphere3d"):
        c, n, r = xyz(obj.get_center()), obj.get_norm(), obj.get_radius()
        u = _perp_dir((1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0), n)
        w = np.cross(n, u)
        top = math.acos(max(-1.0, min(1.0, (r - obj.get_height()) / r)))   # pole -> rim angle
        rings = 12
        angs = [top * (1 - i / rings) for i in range(rings)]                # rim first
        pts = [c + r * (n * math.cos(a) + math.sin(a) * (u * math.cos(lo) + w * math.sin(lo)))
               for a in angs for lo in (2 * math.pi * j / seg for j in range(seg))]
        pole = len(pts)
        pts.append(c + n * r)
        faces = _grid(angs, seg)
        last = (rings - 1) * seg
        faces += [(last + j, last + (j + 1) % seg, pole) for j in range(seg)]
        smooth = [True] * len(faces)
        faces.append(tuple(range(seg)))                                    # flat cut
        smooth.append(False)
        return np.array(pts), faces, smooth, _dim_edges(rings, seg, 4, 6)
    raise TypeError(type(obj).__name__)


def _dim_edges(nrings, seg, every_ring, every_seg):
    """Thin grid lines on a smooth lat/long surface."""
    out = set()
    for i in range(nrings):
        for j in range(seg):
            a = i * seg + j
            if i % every_ring == 0:
                out.add(tuple(sorted((a, i * seg + (j + 1) % seg))))
            if j % every_seg == 0 and i + 1 < nrings:
                out.add(tuple(sorted((a, a + seg))))
    return out


def draw_pieces(obj, eye):
    """Back faces culled; returns ([(corners, facing)], [(a, b, strong)]) for the viewer."""
    pts, faces, smooth, grid = mesh(obj)
    mid = pts.mean(axis=0)
    faces_out, vis, edges = [], [], {}
    for fi, f in enumerate(faces):
        q = pts[list(f)]
        nrm = np.zeros(3)
        for i in range(len(q)):                        # Newell; flipped outward (all convex)
            nrm += np.cross(q[i], q[(i + 1) % len(q)])
        fc = q.mean(axis=0)
        if np.dot(nrm, fc - mid) < 0:
            nrm = -nrm
        L = np.linalg.norm(nrm)
        to_eye = eye - fc
        facing = float(np.dot(nrm, to_eye) / (L * np.linalg.norm(to_eye) + 1e-12)) if L > 0 else 0.0
        vis.append(facing > 0)
        if facing > 0:
            faces_out.append((q, facing))
        for i in range(len(f)):
            edges.setdefault(tuple(sorted((f[i], f[(i + 1) % len(f)]))), []).append(fi)
    lines = []
    for e, fs in edges.items():
        shown = [vis[i] for i in fs]
        if not any(shown):
            continue
        sharp = len(fs) != 2 or not (smooth[fs[0]] and smooth[fs[1]])
        if sharp or not all(shown):
            lines.append((pts[e[0]], pts[e[1]], True))
        elif e in grid:
            lines.append((pts[e[0]], pts[e[1]], False))
    return faces_out, lines


# ----------------------------------------------------------------------------
# Add dialog
# ----------------------------------------------------------------------------
POLY_NAMES = {"Octahedron": "octahedron3d", "Dodecahedron": "dodecahedron3d",
              "Icosahedron": "icosahedron3d", "RhombicDodecahedron": "rhombicdodecahedron3d"}
POLY_NAMES = {k: v for k, v in POLY_NAMES.items() if v in POLY}

ADD_SPECS = {}
_C = lambda fill: [("Border", "c1", "color", "white"), ("Fill", "c2", "color", fill)]   # noqa: E731
if Prism3d:
    ADD_SPECS["Prism"] = [("Base center", "p", "xyz", (0, 0, 0)), ("Base corner", "e", "xyz", (3, 0, 0)),
                          ("Axis direction", "n", "xyz", (0, 0, 1)), ("Height", "h", "num", 5),
                          ("Sides (3..20)", "s", "num", 6)] + _C("teal")
if TruncatedPrism3d:
    ADD_SPECS["TruncPrism"] = ADD_SPECS["Prism"][:5] + [("Top scale (0 = point, 1 = prism)", "t", "num", 0.5)] + _C("slateblue")
if Pyramid3d:
    ADD_SPECS["Pyramid"] = ADD_SPECS["Prism"][:4] + [("Sides (3..20)", "s", "num", 4)] + _C("goldenrod")
if TruncatedCone3d:
    ADD_SPECS["TruncCone"] = [("Base center", "p", "xyz", (0, 0, 0)), ("Base edge point", "e", "xyz", (3, 0, 0)),
                              ("Axis direction", "n", "xyz", (0, 0, 1)), ("Height", "h", "num", 5),
                              ("Top scale (0 = cone, 1 = cylinder)", "t", "num", 0.5)] + _C("coral")
if Ellipsoid3d:
    ADD_SPECS["Ellipsoid"] = [("Center", "p", "xyz", (0, 0, 0)), ("Radii x, y, z", "r", "xyz", (4, 2.5, 1.5))] + _C("mediumseagreen")
if POLY_NAMES:
    ADD_SPECS["Polyhedron"] = [("Type", "k", tuple(POLY_NAMES), next(iter(POLY_NAMES))),
                               ("Center", "p", "xyz", (0, 0, 0)), ("Edge length", "a", "num", 3)] + _C("plum")
if SphericalCap3d:
    ADD_SPECS["SphereCap"] = [("Sphere center", "p", "xyz", (0, 0, 0)), ("Dome direction", "n", "xyz", (0, 0, 1)),
                              ("Sphere radius", "r", "num", 4), ("Cap height (0..2 x radius)", "h", "num", 2)] + _C("skyblue")
if Hemisphere3d:
    ADD_SPECS["Hemisphere"] = ADD_SPECS["SphereCap"][:3] + _C("lightsalmon") if SphericalCap3d else []


def _base(v):
    """(center, corner, top center) from base center, a corner/edge point, axis dir and height."""
    c = np.array(v["p"], float)
    n = _unit(v["n"], "Axis direction")
    if not v["h"] or v["h"] <= 0:
        raise ValueError("Height must be > 0")
    e = np.array(v["e"], float) - c
    r = np.linalg.norm(e - np.dot(e, n) * n)
    if r < 1e-9:
        raise ValueError("Base corner / edge point must be off the axis")
    return list(c), list(c + _perp_dir(e, n) * r), list(c + n * v["h"])


def add_nums(label, v):
    """(kind, CSV numbers) for an Add-dialog label."""
    if label in ("Prism", "TruncPrism", "Pyramid"):
        s = int(round(v["s"] or 0))
        if not 3 <= s <= 20:
            raise ValueError("Sides must be 3..20")
        c, e, t = _base(v)
        if label == "TruncPrism":
            if v["t"] is None or v["t"] < 0:
                raise ValueError("Top scale must be >= 0")
            return "truncatedprism3d", c + e + t + [s, v["t"]]
        return ("prism3d" if label == "Prism" else "pyramid3d"), c + e + t + [s]
    if label == "TruncCone":
        if v["t"] is None or v["t"] < 0:
            raise ValueError("Top scale must be >= 0")
        c, e, t = _base(v)
        return "truncatedcone3d", c + e + t + [v["t"]]
    if label == "Ellipsoid":
        if min(v["r"]) <= 0:
            raise ValueError("Radii must be > 0")
        c = list(v["p"])
        return "ellipsoid3d", c + [c[i] + (v["r"][0] if i == 0 else 0) for i in range(3)] \
            + [c[i] + (v["r"][1] if i == 1 else 0) for i in range(3)] \
            + [c[i] + (v["r"][2] if i == 2 else 0) for i in range(3)]
    if label == "Polyhedron":
        if not v["a"] or v["a"] <= 0:
            raise ValueError("Edge length must be > 0")
        return POLY_NAMES[v["k"]], list(v["p"]) + [v["a"], 1, 0, 0, 0, 1, 0]
    if label in ("SphereCap", "Hemisphere"):
        if not v["r"] or v["r"] <= 0:
            raise ValueError("Radius must be > 0")
        pole = list(np.array(v["p"], float) + _unit(v["n"], "Dome direction") * v["r"])
        if label == "Hemisphere":
            return "hemisphere3d", list(v["p"]) + pole
        if not v["h"] or not 0 < v["h"] <= 2 * v["r"]:
            raise ValueError("Cap height must be above 0 and at most 2 x radius")
        return "sphericalcap3d", list(v["p"]) + pole + [v["h"]]
    raise ValueError(label)


# ----------------------------------------------------------------------------
# Properties editor
# ----------------------------------------------------------------------------
def prop_spec(o, k):
    if k in ("prism3d", "truncatedprism3d", "pyramid3d"):
        out = [("Base center", "p", "xyz", tuple(xyz(o._center_point))), ("Radius (center to corner)", "r", "num", o.get_radius()),
               ("Height", "h", "num", o.get_height()), ("Sides (3..20)", "s", "int", o.get_num_faces()),
               ("Axis direction", "n", "xyz", tuple(float(x) for x in o.get_norm()))]
        return out + ([("Top scale", "t", "num", o.get_top_scale())] if k == "truncatedprism3d" else [])
    if k == "truncatedcone3d":
        n = _unit(xyz(o._top) - xyz(o._cent))
        return [("Base center", "p", "xyz", tuple(xyz(o._cent))), ("Base radius", "r", "num", o.get_radius()),
                ("Height", "h", "num", o.get_height()), ("Top scale", "t", "num", o.get_top_scale()),
                ("Axis direction", "n", "xyz", tuple(n))]
    if k == "ellipsoid3d":
        rx, ry, rz = o.get_radii()
        return [("Center", "p", "xyz", tuple(xyz(o.get_center()))),
                ("Radius along its x", "rx", "num", rx), ("Radius along its y", "ry", "num", ry),
                ("Radius along its z", "rz", "num", rz)]
    if k in POLY:
        return [("Center", "p", "xyz", tuple(xyz(o.get_center()))), ("Edge length", "a", "num", o.get_length())]
    if k in ("sphericalcap3d", "hemisphere3d"):
        return ([("Sphere center", "p", "xyz", tuple(xyz(o.get_center()))), ("Sphere radius", "r", "num", o.get_radius())]
                + ([("Cap height", "h", "num", o.get_height())] if k == "sphericalcap3d" else [])
                + [("Dome direction", "n", "xyz", tuple(float(x) for x in o.get_norm()))])
    return []


def prop_nums(o, k, v):
    if k in ("prism3d", "truncatedprism3d", "pyramid3d", "truncatedcone3d"):
        if v["r"] <= 0 or v["h"] <= 0:
            raise ValueError("Radius and height must be > 0")
        n = _unit(v["n"], "Axis direction")
        c = np.array(v["p"], float)
        old_c, old_e = (o._cent, o._rad_edge) if k == "truncatedcone3d" else (o._center_point, o._edge)
        e = c + _perp_dir(xyz(old_e) - xyz(old_c), n) * v["r"]
        nums = list(c) + list(e) + list(c + n * v["h"])
        if k == "truncatedcone3d":
            if v["t"] < 0:
                raise ValueError("Top scale must be >= 0")
            return nums + [v["t"]]
        if not 3 <= int(v["s"]) <= 20:
            raise ValueError("Sides must be 3..20")
        if k == "truncatedprism3d" and v["t"] < 0:
            raise ValueError("Top scale must be >= 0")
        return nums + [int(v["s"])] + ([v["t"]] if k == "truncatedprism3d" else [])
    if k == "ellipsoid3d":
        if min(v["rx"], v["ry"], v["rz"]) <= 0:
            raise ValueError("Radii must be > 0")
        c = np.array(v["p"], float)
        return list(c) + [x for a, r in zip(o.get_axes(), (v["rx"], v["ry"], v["rz"])) for x in c + a * r]
    if k in POLY:
        if v["a"] <= 0:
            raise ValueError("Edge length must be > 0")
        _c, ax, ay = _poly_frame(o)
        return list(v["p"]) + [v["a"]] + list(ax) + list(ay)
    if k in ("sphericalcap3d", "hemisphere3d"):
        if v["r"] <= 0:
            raise ValueError("Radius must be > 0")
        pole = list(np.array(v["p"], float) + _unit(v["n"], "Dome direction") * v["r"])
        if k == "hemisphere3d":
            return list(v["p"]) + pole
        if not 0 < v["h"] <= 2 * v["r"]:
            raise ValueError("Cap height must be above 0 and at most 2 x radius")
        return list(v["p"]) + pole + [v["h"]]
    raise ValueError(f"no editable properties for {k}")


# ----------------------------------------------------------------------------
# POV-Ray: (head, body, frame or None, extra block keywords)
# frame = local x, y, z, origin in world; local y is the object's axis
# ----------------------------------------------------------------------------
def pov_shape(kind, v, vec, _n):
    P = lambda i: np.array(v[i:i + 3], float)   # noqa: E731
    if kind == "truncatedcone3d":
        c, e, top = P(0), P(3), P(6)
        h = float(np.linalg.norm(top - c))
        n = _unit(top - c)
        u = _perp_dir(e - c, n)
        r = float(np.linalg.norm(e - c))
        return "cone", f"<0, 0, 0>, 1, <0, 1, 0>, {_n(v[9])}", (u * r, n * h, np.cross(n, u) * r, c), {"_map": 2}
    if kind == "ellipsoid3d":
        c = P(0)
        ax, ay, az = P(3) - c, P(6) - c, P(9) - c
        if np.dot(np.cross(ax, ay), az) < 0:                 # keep the frame from mirroring
            ay = -ay
        return "sphere", "<0, 0, 0>, 1", (ax, az, ay, c), {"_map": 1}
    if kind in ("sphericalcap3d", "hemisphere3d"):
        c, pole = P(0), P(3)
        r = float(np.linalg.norm(pole - c))
        n = _unit(pole - c)
        hf = 1.0 if kind == "hemisphere3d" else v[6] / r
        u = _perp_dir((1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0), n)
        body = f"sphere {{ <0, 0, 0>, 1 }}\nplane {{ <0, -1, 0>, {_n(hf - 1)} }}"
        return "intersection", body, (u * r, n * r, np.cross(n, u) * r, c), {"_map": 1}
    # flat-faced solids: a triangle mesh from the rebuilt object
    obj = build(kind, v, None, None, "")
    pts = [xyz(p) for p in obj.get_points()]
    tris = []
    for f in obj.get_faces():
        for i in range(1, len(f) - 1):
            tris.append(f"triangle {{ {vec(pts[f[0]])}, {vec(pts[f[i]])}, {vec(pts[f[i + 1]])} }}")
    return "mesh", "\n".join(tris), None, {}
