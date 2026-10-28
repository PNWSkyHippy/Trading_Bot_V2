"""boolmesh.py - real mesh booleans (combine / cut / overlap / hollow / twin) for the viewer.

Pure numpy + manifold3d, no Tk and no viewer imports, so the previews, the STL/OBJ export
and the headless command layer all share one answer.  The rules mirror pov_export.combine:
a body is its parts (object + twin) unioned, minus its hollow inner copies; a group that is
a csg target (@name) or tool fuses into one body; then each csg tool wraps its target:
combine = union, cut = target minus tool, overlap = intersection.  A target already
wrapped is wrapped again (chains).

Input is plain oriented triangles, so geometry never goes stale: the caller tessellates
the live objects.  Anything that isn't a watertight solid is reported in `failed` and left
for the caller to draw / export as it was.
"""
import numpy as np

try:
    import manifold3d as _m
except ImportError:                      # pragma: no cover - optional dependency
    _m = None


class BoolError(Exception):
    pass


def available():
    return _m is not None


def _array(facets):
    """(T, 3, 3) from [(a, b, c, n), ...] or an array already in that shape."""
    if isinstance(facets, np.ndarray):
        return facets.reshape(-1, 3, 3)
    return np.array([[f[0], f[1], f[2]] for f in facets], float).reshape(-1, 3, 3)


def to_manifold(facets):
    """Weld a triangle soup by position and build a watertight Manifold from it."""
    if _m is None:
        raise BoolError("manifold3d is not installed (pip install manifold3d)")
    P = _array(facets)
    if not len(P):
        raise BoolError("no faces")
    flat = P.reshape(-1, 3)
    _u, first, inv = np.unique(np.round(flat * 1e6).astype(np.int64), axis=0,
                               return_index=True, return_inverse=True)
    verts, tris = flat[first], inv.reshape(-1, 3)
    tris = tris[(tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])]
    if not len(tris):
        raise BoolError("only degenerate faces")
    vol = np.einsum("ij,ij->", verts[tris[:, 0]], np.cross(verts[tris[:, 1]], verts[tris[:, 2]])) / 6.0
    if vol < 0:                          # inside out: wound the wrong way round
        tris = tris[:, ::-1]
    man = _m.Manifold(_m.Mesh(vert_properties=verts.astype(np.float32),
                              tri_verts=np.ascontiguousarray(tris).astype(np.uint32)))
    if man.status() != _m.Error.NoError or man.is_empty():
        raise BoolError("not a closed watertight solid")
    return man


def to_facets(man):
    """[(a, b, c, normal), ...] numpy float triangles out of a Manifold."""
    mesh = man.to_mesh()
    V = np.asarray(mesh.vert_properties, float)[:, :3]
    T = np.asarray(mesh.tri_verts, np.intp)
    out = []
    for i, j, k in T:
        a, b, c = V[i], V[j], V[k]
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln < 1e-14:
            continue
        out.append((a, b, c, n / ln))
    return out


def _union(ms):
    return ms[0] if len(ms) == 1 else _m.Manifold.batch_boolean(ms, _m.OpType.Add)


def solve(items):
    """items: [{"name", "parts": [facets...], "holes": [facets...], "csg": (op, target, group)
    or None, "groups": [group path, outermost first]}].

    Returns (results, failed).  results: [{"host": name, "members": [names merged in],
    "facets": [...]}], one per finished solid.  failed: {name: reason} for items whose parts
    weren't watertight - those are left out of every result."""
    failed, body, its = {}, {}, {}
    for it in items:
        try:
            m = _union([to_manifold(p) for p in it["parts"]])
            if it["holes"]:
                m = m - _union([to_manifold(h) for h in it["holes"]])
            body[it["name"]] = m
            its[it["name"]] = it
        except BoolError as exc:
            failed[it["name"]] = str(exc)
    csg_of = lambda it: tuple(it["csg"] or ()) + (None, None, "")[len(it["csg"] or ()):]  # noqa: E731
    fused = {str(csg_of(it)[1])[1:] for it in its.values() if str(csg_of(it)[1]).startswith("@")}
    fused |= {str(csg_of(it)[2]) for it in its.values() if csg_of(it)[2]}
    key_of, order, members = {}, [], {}
    for n, it in its.items():            # innermost fused group on the path wins
        g = next((g for g in reversed(it.get("groups") or []) if g in fused), None)
        k = "@" + g if g else n
        key_of[n] = k
        if k not in members:
            order.append(k)
            members[k] = []
        members[k].append(n)
    mesh, merged, first_k = {}, {}, {}
    for k in order:
        mesh[k] = _union([body[n] for n in members[k]])
        merged[k] = list(members[k])
        first_k[k] = next((its[n] for n in members[k] if its[n]["csg"]), its[members[k][0]])
    host, lost = {k: k for k in order}, set()
    ops = {"combine": lambda a, b: a + b, "cut": lambda a, b: a - b,
           "overlap": lambda a, b: a ^ b}
    for k in order:
        op, tgt, _g = csg_of(first_k[k])
        tgt = tgt if str(tgt).startswith("@") else key_of.get(tgt)
        if op not in ops or tgt not in host:
            if op in ("cut", "overlap"):
                lost.add(k)              # a tool whose target isn't a solid: not a part of its own
            continue
        h = tgt
        while host[h] != h:              # target already went into another csg
            h = host[h]
        if h == k:
            continue                     # a loop - leave it
        mesh[h] = ops[op](mesh[h], mesh[k])
        merged[h] += merged[k]
        mesh[k], host[k] = None, h
    results = []
    for k in order:
        if mesh[k] is not None and k not in lost:
            results.append({"host": members[k][0], "members": merged[k],
                            "facets": [] if mesh[k].is_empty() else to_facets(mesh[k])})
    return results, failed
