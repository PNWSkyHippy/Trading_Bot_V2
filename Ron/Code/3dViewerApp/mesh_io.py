"""mesh_io.py - turn viewer objects into triangle meshes and write STL / OBJ.

Why this is cheap: every object already becomes triangles (or a POV primitive) to
render, so printing is the same triangles in a different text format - no trimesh,
no numpy-stl, numpy only.

Axes: the viewer is Z-up and so are STL / OBJ and every slicer (Cura, Prusa, Bambu),
so there is NO axis swap here (unlike pov_export, which flips to POV's Y-up).  All
triangles come out in world coordinates with the object's transforms already baked
into its live object / nums.

Units: STL and OBJ are unitless; a slicer reads 1.0 as 1.0 mm.  Pass scale= to turn
viewer units into millimetres before writing (e.g. scale=10 makes a 1-unit cube 10 mm).

The real work is object_triangles(); write_stl / write_obj are thin.  Both are plain
functions so a future headless / MCP caller can build a printable file with no GUI.
"""

import math
import os
import struct
import numpy as np

import solids3d

SEG = 48                      # facets around a round thing on export (finer than the live view)

# kinds that are NOT a printable solid (zero thickness or infinite) - reported, not written
NON_SOLID = {"point3d", "line3d", "vector3d", "plane3d", "square3d", "circle3d"}


# ----------------------------------------------------------------------------
# small geometry helpers
# ----------------------------------------------------------------------------
def _unit(x):
    x = np.asarray(x, float)
    n = np.linalg.norm(x)
    return x / n if n > 1e-12 else x


def _perp(n):
    """Any unit vector perpendicular to n."""
    n = _unit(n)
    a = (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0)
    return _unit(np.cross(n, a))


def _fan(face):
    """Polygon vertex-index list -> triangle-index triples (simple fan)."""
    return [(face[0], face[i], face[i + 1]) for i in range(1, len(face) - 1)]


def _frustum(c, n, h, r1, r2, seg, cap_bottom=True, cap_top=True):
    """A cylinder / cone / truncated cone as a solid: base ring of radius r1 at centre c,
    top ring of radius r2 at c + n*h, wound so normals face outward.  Returns (verts, tris)."""
    n = _unit(n)
    u = _perp(n)
    w = np.cross(n, u)
    top = c + n * h
    ang = [2 * math.pi * j / seg for j in range(seg)]
    base = [c + r1 * (math.cos(a) * u + math.sin(a) * w) for a in ang]
    tip = [top + r2 * (math.cos(a) * u + math.sin(a) * w) for a in ang]
    verts = base + tip
    tris = []
    for j in range(seg):
        k = (j + 1) % seg
        b0, b1, t0, t1 = j, k, seg + j, seg + k
        if r2 > 1e-9:
            tris += [(b0, b1, t1), (b0, t1, t0)]          # quad side
        else:
            tris += [(b0, b1, seg + j)]                    # all tips coincide (cone apex)
    if r2 <= 1e-9:                                         # single apex vertex, dedup
        verts = base + [top]
        apex = seg
        tris = [(j, (j + 1) % seg, apex) for j in range(seg)]
    if cap_bottom:
        cb = len(verts); verts = verts + [c]
        tris += [((j + 1) % seg, j, cb) for j in range(seg)]      # faces down/out
    if cap_top and r2 > 1e-9:
        ct = len(verts); verts = verts + [top]
        tris += [(seg + j, seg + (j + 1) % seg, ct) for j in range(seg)]
    return [np.asarray(p, float) for p in verts], tris


def _sphere(c, r, seg):
    """Lat/long sphere, Z-up poles (matches the viewer's sphere map)."""
    c = np.asarray(c, float)
    rings = max(6, seg // 2)
    lats = [-math.pi / 2 + math.pi * i / rings for i in range(1, rings)]     # exclude poles
    verts, tris = [], []
    for la in lats:
        for j in range(seg):
            lo = 2 * math.pi * j / seg
            verts.append(c + r * np.array([math.cos(la) * math.cos(lo),
                                           math.cos(la) * math.sin(lo),
                                           math.sin(la)]))
    south = len(verts); verts.append(c + np.array([0, 0, -r]))
    north = len(verts); verts.append(c + np.array([0, 0, r]))
    for i in range(len(lats) - 1):
        for j in range(seg):
            k = (j + 1) % seg
            a, b = i * seg + j, i * seg + k
            cc, d = (i + 1) * seg + j, (i + 1) * seg + k
            tris += [(a, b, d), (a, d, cc)]
    for j in range(seg):                                   # end caps
        k = (j + 1) % seg
        tris.append((k, j, south))
        last = (len(lats) - 1) * seg
        tris.append((last + j, last + k, north))
    return verts, tris


def _bend_tris(bend, seg):
    """One CurvedCylinder3d piece as a solid rod: sweep a radius-r ring along the spine arc."""
    c = np.array(bend.get_bend_center(), float) if not hasattr(bend.get_bend_center(), "get_xyz") \
        else np.array(bend.get_bend_center().get_xyz(), float)
    n = _unit(np.array(bend.get_norm(), float))
    R, r, ang = bend.get_bend_radius(), bend.get_tube_radius(), bend.get_angle()
    M = max(4, int(math.ceil(seg * ang / (2 * math.pi))))          # steps along the bend
    rad = [_unit(np.array(bend.radial_dir(i / M), float)) for i in range(M + 1)]
    phis = [2 * math.pi * j / seg for j in range(seg)]
    grid = [[c + R * rd + r * (math.cos(f) * rd + math.sin(f) * n) for f in phis] for rd in rad]
    verts, tris = [], []
    base = {}
    def vid(i, j):
        key = (i, j)
        if key not in base:
            base[key] = len(verts); verts.append(grid[i][j])
        return base[key]
    for i in range(M):
        for j in range(seg):
            k = (j + 1) % seg
            a, b = vid(i, j), vid(i, k)
            cc, d = vid(i + 1, j), vid(i + 1, k)
            tris += [(a, b, d), (a, d, cc)]                 # wound outward (radial)
    # cap the two open ends so the rod is a closed solid
    for i, flip in ((0, True), (M, False)):
        ctr = len(verts); verts.append(c + R * rad[i])
        for j in range(seg):
            k = (j + 1) % seg
            a, b = vid(i, j), vid(i, k)
            tris.append((b, a, ctr) if flip else (a, b, ctr))
    return verts, tris


# ----------------------------------------------------------------------------
# object -> triangles
# ----------------------------------------------------------------------------
def object_triangles(kind, nums, obj, seg=SEG):
    """World-space triangles for one object.

    Returns (verts, tris, trust_winding) on success, or (None, reason, None) when the
    kind is not a printable solid.  trust_winding True means the tessellation is already
    wound outward (tube / lathe); False lets the caller orient normals by centroid.
    """
    v = [float(x) for x in nums]
    def p(i): return np.array(v[i:i + 3], float)

    if kind in NON_SOLID:
        return None, f"{kind} is not a solid (no printable volume)", None

    if kind == "mesh3d":                                    # an imported STL/OBJ mesh
        if obj is None or not hasattr(obj, "triangles"):
            return None, "mesh3d has no geometry", None
        return obj.triangles()

    if kind == "cube3d":
        q = [p(i) for i in range(0, 24, 3)]                 # 8 corners: base 4, top 4
        base, top = list(range(4)), list(range(4, 8))
        faces = [base, top,
                 [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        tris = [t for f in faces for t in _fan(f)]
        return q, tris, False

    if kind == "sphere3d":
        verts, tris = _sphere(p(0), v[3], seg)
        return verts, tris, True

    if kind in ("cylinder3d", "cone3d"):
        c = p(0)
        r = float(np.linalg.norm(p(3) - c))
        n = _unit(v[7:10]) if len(v) >= 10 else np.array([0.0, 0, 1])
        h = v[6]
        r2 = r if kind == "cylinder3d" else 0.0
        verts, tris = _frustum(c, n, h, r, r2, seg)
        return verts, tris, True

    if kind in ("curvedcylinder3d", "curvedtorus3d"):
        bends = obj.get_bends() if hasattr(obj, "get_bends") else [obj]
        verts, tris = [], []
        for bend in bends:
            bv, bt = _bend_tris(bend, max(8, seg // 3))
            off = len(verts)
            verts += bv
            tris += [(a + off, b + off, c + off) for a, b, c in bt]
        return verts, tris, True

    if kind == "lathe3d":
        G, _N = obj.mesh()                                  # (samples, seg+1, 3)
        S, C, _ = G.shape
        verts = [G[i, j] for i in range(S) for j in range(C)]
        def idx(i, j): return i * C + j
        tris = []
        for i in range(S - 1):
            for j in range(C - 1):
                a, b = idx(i, j), idx(i, j + 1)
                cc, d = idx(i + 1, j), idx(i + 1, j + 1)
                tris += [(a, b, d), (a, d, cc)]
        return verts, tris, True

    if kind in solids3d.KINDS:                              # prisms / polyhedra / ellipsoid / cap / cone
        pts, faces, _smooth, _grid = solids3d.mesh(obj, seg)
        verts = [np.asarray(x, float) for x in pts]
        tris = [t for f in faces for t in _fan(list(f))]
        return verts, tris, False

    return None, f"{kind}: no mesh exporter", None


def _facet_normal(a, b, c):
    nrm = np.cross(np.asarray(b) - np.asarray(a), np.asarray(c) - np.asarray(a))
    ln = np.linalg.norm(nrm)
    return nrm / ln if ln > 1e-12 else np.array([0.0, 0, 1])


def _orient(verts, tris, trust_winding):
    """Yield (a, b, c, normal) world triangles with outward normals.
    When winding isn't trusted, flip any facet whose normal points toward the centroid."""
    verts = [np.asarray(x, float) for x in verts]
    centroid = np.mean(verts, axis=0) if verts else np.zeros(3)
    out = []
    for i, j, k in tris:
        a, b, c = verts[i], verts[j], verts[k]
        nrm = _facet_normal(a, b, c)
        if np.linalg.norm(b - a) < 1e-12 or np.linalg.norm(np.cross(b - a, c - a)) < 1e-14:
            continue                                        # degenerate / zero-area
        if not trust_winding:
            mid = (a + b + c) / 3.0
            if float(np.dot(nrm, mid - centroid)) < 0:
                b, c = c, b
                nrm = -nrm
        out.append((a, b, c, nrm))
    return out


# ----------------------------------------------------------------------------
# scene -> triangles  (one list of oriented world triangles, grouped by object)
# ----------------------------------------------------------------------------
def collect(entries, scale=1.0, seg=SEG):
    """entries: objects with .kind, .nums, .obj, .name.
    Returns (groups, skipped) where groups = [(name, [(a,b,c,n), ...]), ...] scaled to mm,
    skipped = [(name, reason), ...]."""
    groups, skipped = [], []
    for e in entries:
        obj = getattr(e, "obj", None)
        if obj is None:
            skipped.append((e.name, "not built"))
            continue
        try:
            verts, tris, trust = object_triangles(e.kind, e.nums, obj, seg)
        except Exception as exc:                            # noqa: BLE001 - report, don't abort the file
            skipped.append((e.name, f"{type(exc).__name__}: {exc}"))
            continue
        if verts is None:
            skipped.append((e.name, tris))                  # tris holds the reason here
            continue
        facets = _orient(verts, tris, trust)
        if scale != 1.0:
            facets = [(a * scale, b * scale, c * scale, n) for a, b, c, n in facets]
        if facets:
            groups.append((e.name, facets))
        else:
            skipped.append((e.name, "no faces"))
    return groups, skipped


def bbox(groups):
    """(min xyz, max xyz) over every triangle, or None when empty."""
    pts = [v for _n, fac in groups for (a, b, c, _nn) in fac for v in (a, b, c)]
    if not pts:
        return None
    arr = np.asarray(pts)
    return arr.min(axis=0), arr.max(axis=0)


# ----------------------------------------------------------------------------
# writers
# ----------------------------------------------------------------------------
def write_stl(path, groups, binary=True, name="viewer_scene"):
    """Write every group's triangles as ONE solid (slicers treat an STL as one body)."""
    facets = [f for _n, fac in groups for f in fac]
    if binary:
        with open(path, "wb") as fh:
            fh.write(b"\0" * 80)                            # 80-byte header
            fh.write(struct.pack("<I", len(facets)))
            for a, b, c, nrm in facets:
                fh.write(struct.pack("<12fH",
                                     *nrm, *a, *b, *c, 0))
    else:
        with open(path, "w") as fh:
            fh.write(f"solid {name}\n")
            for a, b, c, nrm in facets:
                fh.write(f"  facet normal {nrm[0]:.6e} {nrm[1]:.6e} {nrm[2]:.6e}\n")
                fh.write("    outer loop\n")
                for vx in (a, b, c):
                    fh.write(f"      vertex {vx[0]:.6e} {vx[1]:.6e} {vx[2]:.6e}\n")
                fh.write("    endloop\n  endfacet\n")
            fh.write(f"endsolid {name}\n")
    return len(facets)


def write_obj(path, groups):
    """OBJ with one group ('o <name>') per object, shared 1-based vertex list."""
    lines, vi = [], 1
    nfac = 0
    with open(path, "w") as fh:
        fh.write("# exported by viewer3d / mesh_io\n")
        for name, fac in groups:
            fh.write(f"o {name}\n")
            start = vi
            for a, b, c, _n in fac:                         # write each triangle's 3 verts
                for vx in (a, b, c):
                    fh.write(f"v {vx[0]:.6f} {vx[1]:.6f} {vx[2]:.6f}\n")
                    vi += 1
            for t in range(len(fac)):
                base = start + t * 3
                fh.write(f"f {base} {base + 1} {base + 2}\n")
                nfac += 1
    return nfac


# ----------------------------------------------------------------------------
# readers  (STL / OBJ file -> welded verts + triangle indices)   [Phase 2 import]
# ----------------------------------------------------------------------------
def _weld(raw_tris, places=5):
    """raw_tris: list of (a, b, c) float triples -> (verts Nx3, tris list of int-triples),
    duplicate vertices merged so the mesh shares corners (smaller, nicer to draw)."""
    verts, tris, seen = [], [], {}
    def vid(p):
        key = (round(p[0], places), round(p[1], places), round(p[2], places))
        i = seen.get(key)
        if i is None:
            i = seen[key] = len(verts)
            verts.append([float(p[0]), float(p[1]), float(p[2])])
        return i
    for a, b, c in raw_tris:
        ia, ib, ic = vid(a), vid(b), vid(c)
        if ia != ib and ib != ic and ia != ic:          # drop collapsed facets
            tris.append((ia, ib, ic))
    return np.asarray(verts, float) if verts else np.zeros((0, 3)), tris


def read_stl(path):
    """STL (binary or ASCII) -> (verts Nx3 float, tris list of int-triples).  Winding kept."""
    with open(path, "rb") as fh:
        head = fh.read(84)
        if len(head) >= 84:
            n = struct.unpack("<I", head[80:84])[0]
            if os.path.getsize(path) == 84 + n * 50:     # exact size => real binary STL
                raw = []
                for _ in range(n):
                    d = fh.read(50)
                    if len(d) < 50:
                        break
                    f = struct.unpack("<12fH", d)
                    raw.append((f[3:6], f[6:9], f[9:12]))
                return _weld(raw)
    # ASCII fallback
    with open(path, "r", errors="replace") as fh:
        verts3, raw = [], []
        for line in fh:
            s = line.split()
            if len(s) == 4 and s[0] == "vertex":
                verts3.append((float(s[1]), float(s[2]), float(s[3])))
                if len(verts3) == 3:
                    raw.append(tuple(verts3)); verts3 = []
    if not raw:
        raise ValueError("no triangles found (not a valid STL)")
    return _weld(raw)


def read_obj(path):
    """OBJ -> (verts Nx3 float, tris list of int-triples).  v/f only; n-gons fan-triangulated,
    1-based and negative (relative) indices handled; vt/vn/o/g/usemtl ignored."""
    verts, raw = [], []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            s = line.split()
            if not s:
                continue
            if s[0] == "v" and len(s) >= 4:
                verts.append((float(s[1]), float(s[2]), float(s[3])))
            elif s[0] == "f" and len(s) >= 4:
                idx = []
                for tok in s[1:]:
                    t = tok.split("/")[0]
                    if not t:
                        continue
                    j = int(t)
                    idx.append(j - 1 if j > 0 else len(verts) + j)   # 1-based or relative
                for i in range(1, len(idx) - 1):                     # fan triangulate
                    a, b, c = idx[0], idx[i], idx[i + 1]
                    if 0 <= a < len(verts) and 0 <= b < len(verts) and 0 <= c < len(verts):
                        raw.append((verts[a], verts[b], verts[c]))
    if not raw:
        raise ValueError("no faces found (not a valid OBJ)")
    return _weld(raw)


def read_mesh(path):
    """Read an STL or OBJ by extension -> (verts, tris)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".obj":
        return read_obj(path)
    if ext in (".stl", ""):
        return read_stl(path)
    raise ValueError(f"unsupported mesh type '{ext}' (use .stl or .obj)")


# base meshes read from disk, keyed by (path, mtime, size) so an edited file reloads
_MESH_CACHE = {}


def load_base(path):
    """(verts, tris) for a sidecar file, cached; returns copies safe to transform."""
    try:
        st = os.stat(path)
        key = (os.path.abspath(path), st.st_mtime, st.st_size)
    except OSError as exc:
        raise ValueError(f"mesh file not found: {path} ({exc})")
    hit = _MESH_CACHE.get(key)
    if hit is None:
        if len(_MESH_CACHE) > 64:
            _MESH_CACHE.clear()
        hit = _MESH_CACHE[key] = read_mesh(path)
    v, t = hit
    return v.copy(), list(t)


# ----------------------------------------------------------------------------
# Mesh3d - an imported triangle mesh that rides the viewer's transform/draw rails
# ----------------------------------------------------------------------------
class _Pt:
    """Minimal Point3d stand-in: get_center() returns one so _rotation_pivot('center') works."""
    __slots__ = ("_x", "_y", "_z")

    def __init__(self, x, y, z):
        self._x, self._y, self._z = float(x), float(y), float(z)

    def get_xyz(self):
        return (self._x, self._y, self._z)

    def get_x(self):
        return self._x

    def get_y(self):
        return self._y

    def get_z(self):
        return self._z


class Mesh3d:
    """A welded triangle mesh in world coordinates.  Implements the class3d transform
    protocol (move / scale / xrot / yrot / zrot / vecrot) with the same sign and pivot
    conventions, so run_tf / scale_obj / sample_points drive it like any library object.

    verts: Nx3 numpy float (mutated in place by transforms).  tris: list of int-triples.
    """

    def __init__(self, verts, tris, name="mesh", bc=None, fc=None, src=""):
        self.verts = np.asarray(verts, float).reshape(-1, 3).copy()
        self.tris = list(tris)
        self.name = name
        self.bc = bc
        self.fc = fc
        self.src = src                       # sidecar basename this mesh was read from

    # -- geometry queries -------------------------------------------------
    def _bbox(self):
        if not len(self.verts):
            return np.zeros(3), np.zeros(3)
        return self.verts.min(axis=0), self.verts.max(axis=0)

    def _center_xyz(self):
        lo, hi = self._bbox()
        return (lo + hi) / 2.0

    def get_center(self):
        return _Pt(*self._center_xyz())

    def get_bc(self):
        return self.bc

    def get_fc(self):
        return self.fc

    def corners(self):
        """The 8 bounding-box corners (cheap stand-in for 'all points')."""
        lo, hi = self._bbox()
        return [np.array([x, y, z], float)
                for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]

    def triangles(self):
        """(verts copy, tris, trust_winding=True) - ready for mesh_io.collect / export."""
        return [v.copy() for v in self.verts], list(self.tris), True

    # -- pivot resolution (mirrors class3d._rotation_pivot for our accepted forms) --
    def _pivot(self, pivot, default):
        if pivot is None:
            return np.asarray(default, float)
        if isinstance(pivot, str):
            if pivot != "center":
                raise ValueError('The only named pivot is "center".')
            return self._center_xyz()
        if hasattr(pivot, "get_xyz"):
            return np.asarray(pivot.get_xyz(), float)
        return np.asarray(pivot, float)

    # -- transforms (in place; return self) -------------------------------
    def move(self, dx, dy, dz):
        self.verts += np.array([dx, dy, dz], float)
        return self

    def scale(self, factor):                 # about the world origin, like class3d
        self.verts *= float(factor)
        return self

    def xrot(self, angle_rad, pivot=None):
        px, py, pz = self._pivot(pivot, (0, 0, 0))
        y, z = self.verts[:, 1] - py, self.verts[:, 2] - pz
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        self.verts[:, 1] = py + y * c - z * s
        self.verts[:, 2] = pz + y * s + z * c
        return self

    def yrot(self, angle_rad, pivot=None):
        px, py, pz = self._pivot(pivot, (0, 0, 0))
        x, z = self.verts[:, 0] - px, self.verts[:, 2] - pz
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        self.verts[:, 0] = px + x * c + z * s
        self.verts[:, 2] = pz - x * s + z * c
        return self

    def zrot(self, angle_rad, pivot=None):
        px, py, pz = self._pivot(pivot, (0, 0, 0))
        x, y = self.verts[:, 0] - px, self.verts[:, 1] - py
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        self.verts[:, 0] = px + x * c - y * s
        self.verts[:, 1] = py + x * s + y * c
        return self

    def vecrot(self, vecaxis, angle_rad, pivot=None):
        start = np.asarray(vecaxis.get_start().get_xyz(), float)
        axis = np.asarray(vecaxis.get_end().get_xyz(), float) - start
        norm = np.linalg.norm(axis)
        if norm == 0:
            raise ValueError("Rotation axis cannot be a zero vector.")
        k = axis / norm
        origin = self._pivot(pivot, start)
        v = self.verts - origin
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        kxv = np.cross(np.broadcast_to(k, v.shape), v)
        kv = v @ k
        self.verts = (v * c + kxv * s + np.outer(kv, k) * (1 - c)) + origin
        return self
