"""pov_export.py - turn a viewer3d scene into POV-Ray source and render it.

The viewer is Z-up and right-handed; POV-Ray is Y-up and left-handed.  Swapping
y and z converts one into the other (no mirroring), so every point and direction
goes out as <x, z, y>.

Input items are plain data (no class3d objects), one dict per shape:
    {"name", "kind", "c1", "c2", "nums", "texture" (optional POV text)}
where kind/nums follow the scene3d.csv object rows (current geometry, transforms
already applied).
"""
import math
import os
import re
import subprocess
import tempfile

import numpy as np

PVENGINE = r"C:\Program Files\POV-Ray\v3.7\bin\pvengine64.exe"
LINE_RADIUS = 0.03          # lines / vectors become thin cylinders
POINT_RADIUS = 0.08


# ----------------------------------------------------------------------------
# small writers
# ----------------------------------------------------------------------------
def _n(v):
    """Format a number with up to 5 decimals and no trailing zeros."""
    s = f"{float(v):.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def vec(p):
    """Viewer (x, y, z) -> POV <x, z, y>."""
    return f"<{_n(p[0])}, {_n(p[2])}, {_n(p[1])}>"


def unit(v):
    """Return v scaled to length 1 (unchanged if it is zero)."""
    v = np.array(v, float)
    L = np.linalg.norm(v)
    return v / L if L > 1e-12 else v


def rgb_text(color, rgb_of):
    """'<r, g, b>' (0..1) for a Tk color name / #hex, or None."""
    c = rgb_of(color) if color else None
    return None if c is None else "<%s, %s, %s>" % tuple(_n(x / 255.0) for x in c)


def indent(text, pad="    "):
    """Indent every non-blank line of `text` by `pad`."""
    return "\n".join(pad + ln if ln.strip() else ln for ln in text.splitlines())


# ----------------------------------------------------------------------------
# materials
#   spec  ""                         the object's own fill / line color
#         "studio:<Name>"            a preset below ({rgb} = object color, {s} = scale)
#         "lib:<file.inc>:<kind>:<Name>"   a #declare from POV-Ray's include library
#         "image:<file>"             image wrapped around the object (file in POV_DIR)
# Each one is the inside of a  material { }  block.
# ----------------------------------------------------------------------------
STUDIO = {
    "Plastic": "texture { pigment { color rgb {rgb} }\n"
               "    finish { ambient 0.1 diffuse 0.7 specular 0.6 roughness 0.02 reflection 0.1 } }",
    "Matte": "texture { pigment { color rgb {rgb} } finish { ambient 0.1 diffuse 0.85 } }",
    "Glow": "texture { pigment { color rgb {rgb} } finish { ambient 2.5 diffuse 0 } }",
    "Chrome": "texture { pigment { color rgb <0.95, 0.95, 0.98> }\n"
              "    finish { ambient 0.05 diffuse 0.1 reflection 0.92 metallic 0.8 specular 1 roughness 0.005 } }",
    "Tinted metal": "texture { pigment { color rgb {rgb} }\n"
                    "    finish { ambient 0.1 diffuse 0.45 reflection 0.6 metallic 0.9 specular 0.8 roughness 0.02 } }",
    "Gold": "texture { pigment { color rgb <1, 0.84, 0> }\n"
            "    finish { ambient 0.1 diffuse 0.5 reflection 0.75 metallic 0.8 specular 0.85 roughness 0.02 } }",
    "Brushed metal": "texture { pigment { color rgb <0.75, 0.78, 0.82> }\n"
                     "    finish { ambient 0.1 diffuse 0.6 reflection 0.35 roughness 0.08 metallic 0.7 } }",
    "Glass": "texture { pigment { color rgbf <0.98, 0.98, 1, 0.9> }\n"
             "    finish { ambient 0.05 diffuse 0.1 reflection 0.15 specular 0.9 roughness 0.01 } }\n"
             "interior { ior 1.5 }",
    "Tinted glass": "texture { pigment { color rgb {rgb} filter 0.85 }\n"
                    "    finish { ambient 0.05 diffuse 0.1 reflection 0.15 specular 0.9 roughness 0.01 } }\n"
                    "interior { ior 1.5 }",
    "Emerald": "texture { pigment { color rgbf <0.2, 0.85, 0.4, 0.8> }\n"
               "    finish { ambient 0.08 diffuse 0.2 reflection 0.25 specular 0.9 roughness 0.01 } }\n"
               "interior { ior 1.58 }",
    "Checker": "texture { pigment { checker color rgb {rgb} color rgb <0.9, 0.9, 0.9> scale {s} }\n"
               "    finish { ambient 0.1 diffuse 0.85 } }",
    "Tiles": "texture { pigment { brick color rgb <0.85, 0.85, 0.82> color rgb {rgb}\n"
             "    brick_size <1, 1, 1> mortar 0.06 scale {s} } finish { ambient 0.1 diffuse 0.8 specular 0.2 } }",
    "Prism glass": "texture { pigment { color rgbf <0.98, 0.98, 1, 0.95> }\n"
                   "    finish { ambient 0 diffuse 0.05 reflection 0.1 specular 0.9 roughness 0.005 } }\n"
                   "interior { ior 1.6 dispersion 1.15 dispersion_samples 24 }",
    # Strong dispersion for a CAST rainbow (caustic on floor/wall).  Needs photons ON (F6),
    # a non-parallel-faced shape (a 3-sided prism3d, not a box), and a bright narrow spot.
    "Prism rainbow": "texture { pigment { color rgbf <0.98, 0.98, 1, 0.97> }\n"
                     "    finish { ambient 0 diffuse 0.02 reflection 0.06 specular 0.7 roughness 0.004 } }\n"
                     "interior { ior 1.52 dispersion 1.45 dispersion_samples 36 }",
    # Volumes.  The object becomes a see-through container (hollow) filled with media.
    # {fade} thins it out toward the object's edge, {inv} = 1 / object size so a big
    # cloud is not brighter than a small one.
    "Nebula": "texture { pigment { color rgbt 1 } }\n"
              "interior { media {\n"
              "    emission {rgb} * 2.5 * {inv}\n"
              "    method 3 intervals 1 samples 8\n"
              "    density { {fade} color_map { [0 rgb 0] [0.45 rgb 0.25] [1 rgb 1] } }\n"
              "    density { granite turbulence 0.5 scale 0.8 * {s}\n"
              "        color_map { [0 rgb 0] [0.35 rgb 0.15] [0.7 rgb 1] [1 rgb 2] } }\n"
              "} }",
    "Dust cloud": "texture { pigment { color rgbt 1 } }\n"
                  "interior { media {\n"
                  "    scattering { 1, {rgb} * 0.45 * {inv} extinction 0.5 }\n"
                  "    method 3 intervals 1 samples 10\n"
                  "    density { {fade} color_map { [0 rgb 0] [0.45 rgb 0.25] [1 rgb 1] } }\n"
                  "    density { bozo turbulence 0.7 octaves 5 scale 0.5 * {s}\n"
                  "        color_map { [0 rgb 0] [0.4 rgb 0.2] [1 rgb 1.6] } }\n"
                  "} }",
    "Smoke": "texture { pigment { color rgbt 1 } }\n"
             "interior { media {\n"
             "    absorption <0.6, 0.6, 0.62> * 2 * {inv}\n"
             "    scattering { 1, <0.5, 0.5, 0.52> * {inv} }\n"
             "    method 3 intervals 1 samples 10\n"
             "    density { {fade} color_map { [0 rgb 0] [0.45 rgb 0.25] [1 rgb 1] } }\n"
             "    density { wrinkles turbulence 0.6 scale 0.4 * {s}\n"
             "        color_map { [0 rgb 0] [0.5 rgb 0.3] [1 rgb 1.4] } }\n"
             "} }",
    # A real light in the object's color; the object itself is drawn glowing (looks_like).
    "Star light": "texture { pigment { color rgb {rgb} } finish { ambient 1.5 diffuse 0 emission 1 } }",
}
VOLUMES = ("studio:Nebula", "studio:Dust cloud", "studio:Smoke")
OVAL = "spherical scale <1, 0.5, 1> translate <0, 0.5, 0>"   # soft egg inside a unit cylinder
STRETCHED = VOLUMES + ("studio:Star light",)     # these fit the object, like an image map
LIB_FINISH = "finish { ambient 0.1 diffuse 0.75 specular 0.2 }"
IMAGE_TYPES = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".tga": "tga",
               ".bmp": "sys", ".tif": "tiff", ".tiff": "tiff", ".ppm": "ppm", ".exr": "exr", ".hdr": "hdr"}

# Where POV-Ray's own include library lives (WSL install first, then Windows).
LIB_DIRS = [r"\\wsl.localhost\Ubuntu\usr\local\share\povray-3.8\include",
            r"\\wsl.localhost\Ubuntu\usr\local\share\povray-3.7\include",
            r"\\wsl.localhost\Ubuntu\usr\share\povray-3.7\include",
            os.path.expanduser(r"~\Documents\POV-Ray\v3.7\include"),
            "/usr/share/povray-3.7/include", "/usr/local/share/povray-3.7/include",   # Linux
            "/opt/homebrew/share/povray-3.7/include"]                                  # Mac (brew)
LIB_FILES = ("textures.inc", "metals.inc", "golds.inc", "stones1.inc", "stones2.inc", "woods.inc", "skies.inc")
_GROUPS = (("Glass", ("glass", "bottle", "water")),
           ("Metal", ("chrome", "brass", "gold", "bronze", "copper", "silver", "alumin", "penny", "rust",
                      "iron", "metal", "tinny")),
           ("Wood", ("wood", "pine", "rosewood", "sandalwood", "oak", "dmf", "emb")),
           ("Stone", ("marble", "agate", "granit", "jade", "alabaster", "stone", "grnt", "crack")),
           ("Sky", ("sky", "cloud", "apocalypse", "starfield")))
_LIBRARY = None


def library():
    """{group: [(name, kind, include file)]} read from POV-Ray's include files (cached)."""
    global _LIBRARY
    if _LIBRARY is not None:
        return _LIBRARY
    pat = re.compile(r"^\s*#declare\s+([A-Za-z_]\w*)\s*=\s*(?://[^\n]*\n|\s)*(texture|pigment|material)\b",
                     re.M)
    lib = {g: [] for g, _w in _GROUPS}
    lib["Other"] = []
    folder = next((d for d in LIB_DIRS if os.path.exists(os.path.join(d, "textures.inc"))), None)
    for fname in LIB_FILES if folder else ():
        try:
            with open(os.path.join(folder, fname), encoding="latin-1") as f:
                text = f.read()
        except OSError:
            continue
        for name, kind in pat.findall(text):
            if fname == "textures.inc" and kind == "texture" and "glass" in name.lower():
                continue                    # the M_ glass materials carry the interior (refraction)
            low = name.lower()
            grp = ("Metal" if fname in ("metals.inc", "golds.inc") else
                   "Stone" if fname.startswith("stones") else
                   "Wood" if fname == "woods.inc" else
                   "Sky" if fname == "skies.inc" else
                   next((g for g, words in _GROUPS if any(w in low for w in words)), "Other"))
            inc = "stones.inc" if fname.startswith("stones") else fname
            lib[grp].append((name, kind, inc))
    _LIBRARY = {g: v for g, v in lib.items() if v}
    return _LIBRARY


def material(item, rgb_of):
    """(inside of a POV material block, #include it needs or None) for an item."""
    spec, s = item.get("mat") or "", float(item.get("mat_scale") or 1.0)
    rgb = (rgb_text(item.get("c2"), rgb_of) or rgb_text(item.get("c1"), rgb_of)
           or "<0.78, 0.8, 0.83>")
    if spec.startswith("studio:") and spec[7:] in STUDIO:
        return (STUDIO[spec[7:]].replace("{rgb}", rgb).replace("{s}", _n(s))
                .replace("{inv}", _n(1.0 / max(item.get("_size", 1.0), 1e-6)))
                .replace("{fade}", item.get("_fade", "spherical"))), None
    if spec.startswith("lib:") and spec.count(":") == 3:
        _l, inc, kind, name = spec.split(":", 3)
        sc = f" scale {_n(s)}" if s != 1 else ""
        if kind == "material":
            return f"{name}{sc}", inc
        if kind == "pigment":
            return f"texture {{ pigment {{ {name}{sc} }} {LIB_FINISH} }}", inc
        return f"texture {{ {name}{sc} }}", inc
    if spec.startswith("image:"):
        fname = spec[6:]
        kind = IMAGE_TYPES.get(os.path.splitext(fname)[1].lower(), "png")
        return (f'texture {{ pigment {{ image_map {{ {kind} "{fname}" map_type {item.get("_map", 0)}'
                f' interpolate 2 }} {item.get("_img", "")}}}\n    finish {{ ambient 0.12 diffuse 0.85 specular 0.2 }} }}'), None
    return ("texture { pigment { color rgb %s }\n"
            "    finish { ambient 0.1 diffuse 0.75 specular 0.3 roughness 0.03 } }" % rgb), None


def mat_rows(m):
    """matrix <...> from 4 world vectors: images of local x, y, z, then the origin."""
    return "matrix <" + ", ".join(vec(x)[1:-1] for x in m) + ">"


def block(head, body, item, rgb_of, frame=None, includes=None):
    """One POV object.  frame = (x, y, z, origin) world vectors the local primitive is
    mapped by.  An image map goes inside the frame so it stretches to fit the object;
    any other material rides along with the object's position and turn, unstretched."""
    spec = item.get("mat") or ""
    if frame is not None:                       # world size of the local unit shape
        item = {**item, "_size": item.get("_size") or float(np.mean([np.linalg.norm(a) for a in frame[:3]]))}
    inner, inc = material(item, rgb_of)
    if inc and includes is not None:
        includes.add(inc)
    if spec == "studio:Star light":
        rgb = rgb_text(item.get("c2"), rgb_of) or rgb_text(item.get("c1"), rgb_of) or "<1, 1, 1>"
        shape = indent(f"{head} {{\n{indent(body)}\n    material {{\n{indent(inner, ' ' * 8)}\n    }}\n}}")
        where = ("    " + mat_rows(frame)) if frame is not None else ""
        return (f"// {item.get('name', '')}\nlight_source {{\n    <0, 0, 0>, color {rgb} * 1.6\n"
                f"    looks_like {{\n{indent(shape)}\n    }}\n{where}\n}}\n")
    out = [f"// {item.get('name', '')}", f"{head} {{", indent(body)]
    if head == "mesh":                          # gives a closed mesh an inside, so CSG can cut it
        out.append("    inside_vector <0.31, 0.59, 0.74>")
    if spec in VOLUMES:
        out.append("    hollow")
    if frame is not None and (spec.startswith("image:") or spec in STRETCHED):
        out += [indent(f"material {{\n{indent(inner)}\n}}"), "    " + mat_rows(frame)]
    elif frame is not None:
        rigid = [unit(a) for a in frame[:3]] + [frame[3]]
        out += ["    " + mat_rows(frame),
                indent(f"material {{\n{indent(inner)}\n    {mat_rows(rigid)}\n}}")]
    else:
        out.append(indent(f"material {{\n{indent(inner)}\n}}"))
    return "\n".join(out) + "\n}\n"


def perp(n):
    """A unit vector at right angles to unit vector n."""
    return unit(np.cross(n, (1.0, 0, 0) if abs(n[0]) < 0.9 else (0, 1.0, 0)))


# ----------------------------------------------------------------------------
# one shape -> POV text.  Solids are built in local space and placed with a matrix;
# local POV y is the object's axis.  Frames are chosen so nothing gets mirrored
# (the y/z swap is itself a mirror, so the world frame must be left-handed).
# ----------------------------------------------------------------------------
def bend_pov(c, start, r, angle_deg, normal):
    """A clipped torus for one bend (CurvedCylinder3d).  Sweep goes from the spine
    start toward cross(normal, start-dir), same as class3d's _frame()."""
    c = np.array(c, float)
    e1 = unit(np.array(start, float) - c)
    n = unit(normal)
    e2 = np.cross(n, e1)
    R = float(np.linalg.norm(np.array(start, float) - c))
    th = math.radians(angle_deg)
    body = f"torus {{ 1, {_n(r / R)} }}"           # unit ring scaled by the frame (map_type 5 wants R = 1)
    e1, n, e2 = e1 * R, n * R, e2 * R
    if th < 2 * math.pi - 1e-6:
        # Keep 0 <= angle <= th, measured from local x toward local z.
        # A plane keeps the side opposite its normal.
        h1 = "plane { <0, 0, -1>, 0 }"
        h2 = f"plane {{ <{_n(-math.sin(th))}, 0, {_n(math.cos(th))}>, 0 }}"
        wedge = (f"intersection {{ {h1} {h2} }}" if th <= math.pi
                 else f"union {{ {h1} {h2} }}")
        return "intersection", f"{body}\n{wedge}", (e1, n, e2, c)
    return "object", body, (e1, n, e2, c)


def shape_pov(item, rgb_of, includes=None):
    """Return the POV-Ray text for one scene item; rgb_of turns a color name into (r, g, b)."""
    k, v = item["kind"], [float(x) for x in item["nums"]]
    p = lambda i: np.array(v[i:i + 3])                      # noqa: E731

    def put(head, body, frame=None, **kw):
        """Wrap a shape's head and body in a POV block using this item's settings."""
        return block(head, body, {**item, **kw}, rgb_of, frame, includes)

    if k == "sphere3d":                 # map_type 1 = spherical, poles on the viewer's Z
        r = v[3]
        X, Y, Z = np.eye(3)
        return put("sphere", "<0, 0, 0>, 1", (X * r, Z * r, Y * r, p(0)), c2="", _map=1)
    if k == "point3d":
        return put("sphere", f"{vec(p(0))}, {POINT_RADIUS}")
    if k in ("line3d", "vector3d"):
        a, b = p(0), p(3)
        if np.linalg.norm(b - a) < 1e-9:
            return ""
        if k == "line3d":
            return put("cylinder", f"{vec(a)}, {vec(b)}, {LINE_RADIUS}")
        head = b - unit(b - a) * min(0.25, np.linalg.norm(b - a) / 3)
        return put("union", f"cylinder {{ {vec(a)}, {vec(head)}, {LINE_RADIUS} }}\n"
                            f"cone {{ {vec(head)}, {LINE_RADIUS * 3}, {vec(b)}, 0 }}")
    if k == "square3d":
        q = [p(i) for i in range(0, 12, 3)]
        return put("polygon", "5, " + ", ".join(vec(x) for x in q + q[:1]))
    if k == "plane3d":
        n = unit(p(3))
        if (item.get("mat") or "").startswith("image:"):
            # image laid flat on the plane, one copy per plane size (x tex scale), centered, tiled
            S = v[6] if len(v) > 6 and v[6] > 0 else 10.0
            u = perp(n)
            s = float(item.get("mat_scale") or 1.0)
            return put("plane", "<0, 1, 0>, 0", (u * S, n, np.cross(n, u) * S, p(0)),
                       _img=f"translate <-0.5, -0.5, 0> rotate x*90 scale {_n(s)} ")
        return put("plane", f"{vec(n)}, {_n(np.dot(n, p(0)))}")
    if k == "cube3d":
        q = [p(i) for i in range(0, 24, 3)]
        base, top = q[:4], q[4:]
        u, w, h = base[1] - base[0], base[3] - base[0], top[0] - base[0]
        if all(np.allclose(top[i], base[i] + h, atol=1e-6) for i in range(4)) \
                and np.allclose(base[2], base[0] + u + w, atol=1e-6):
            if np.dot(np.cross(u, h), w) > 0:      # wrong hand: swap the two base edges
                u, w = w, u
            return put("box", "<0, 0, 0>, <1, 1, 1>", (u, h, w, base[0]),
                       _fade="boxed scale 0.5 translate <0.5, 0.5, 0.5>")
        faces = [base, top] + [[base[i], base[(i + 1) % 4], top[(i + 1) % 4], top[i]] for i in range(4)]
        return put("union", "\n".join("polygon { 5, " + ", ".join(vec(x) for x in f + f[:1]) + " }"
                                      for f in faces))
    if k in ("circle3d", "cylinder3d", "cone3d"):
        c = p(0)
        r = float(np.linalg.norm(p(3) - c))
        kn = 6 if k == "circle3d" else 7
        n = unit(v[kn:kn + 3]) if len(v) >= kn + 3 else np.array((0.0, 0.0, 1.0))
        h = 0.0 if k == "circle3d" else v[6]
        u = perp(n)
        w = np.cross(n, u)
        if abs(h) < 1e-9:
            return put("disc", "<0, 0, 0>, y, 1", (u * r, n, w * r, c))
        frame = (u * r, n * h, w * r, c)
        if k == "cylinder3d":           # map_type 2 = cylindrical, wraps the side once
            return put("cylinder", "<0, 0, 0>, <0, 1, 0>, 1", frame, _map=2, _fade=OVAL)
        return put("cone", "<0, 0, 0>, 1, <0, 1, 0>, 0", frame, _map=2, _fade=OVAL)
    if k == "curvedcylinder3d":
        head, body, frame = bend_pov(p(0), p(3), v[6], v[7], v[8:11] if len(v) >= 11 else (0, 0, 1))
        return put(head, body, frame, _map=5, _size=v[6], _fade="planar scale 1e6")   # no edge fade on a tube
    if k == "lathe3d":                  # smooth full turn = POV lathe, else a triangle mesh
        import lathe3d
        head, body, frame = lathe3d.pov_shape(v, vec, _n)
        return put(head, body, frame) if frame is not None else put(head, body)
    if k == "mesh3d":                   # imported STL/OBJ -> POV mesh2 (triangles carried in _mesh)
        mesh = item.get("_mesh")
        if not mesh or len(mesh[1]) == 0:
            return f"//{item.get('name', '')}: mesh3d has no geometry\n"
        verts, tris = mesh
        vv = ",\n        ".join(vec(x) for x in verts)
        ff = ",\n        ".join(f"<{int(a)}, {int(b)}, {int(c)}>" for a, b, c in tris)
        body = (f"vertex_vectors {{\n        {len(verts)},\n        {vv}\n    }}\n"
                f"    face_indices {{\n        {len(tris)},\n        {ff}\n    }}\n"
                f"    inside_vector <0.31, 0.59, 0.74>")
        return put("mesh2", body)
    import solids3d
    if k in solids3d.KINDS:             # prisms/polyhedra = mesh, cone/ellipsoid/cap = true shapes
        head, body, frame, kw = solids3d.pov_shape(k, v, vec, _n)
        return put(head, body, frame, **kw)
    return f"//{item.get('name', '')}: {k} not exported\n"


# ----------------------------------------------------------------------------
# whole scene
# ----------------------------------------------------------------------------
def camera_pov(cam):
    """cam: {"eye", "target", "angle" (horizontal deg), "aspect" (w/h)} + optional "sky" (camera up, rolls it)."""
    sky = vec(cam["sky"]) if cam.get("sky") is not None else "y"
    return ("camera {\n    perspective\n"
            f"    location {vec(cam['eye'])}\n"
            f"    right x*{_n(cam['aspect'])}\n    up y\n    sky {sky}\n"
            f"    angle {_n(cam['angle'])}\n"
            f"    look_at {vec(cam['target'])}\n}}\n")


def default_lights(cam):
    """Key light up behind the camera's shoulder plus a soft shadowless fill at the eye."""
    eye, tgt = np.array(cam["eye"], float), np.array(cam["target"], float)
    d = eye - tgt
    span = max(np.linalg.norm(d), 1.0)
    side = unit(np.cross(d, (0.0, 0.0, 1.0))) if np.linalg.norm(np.cross(d, (0, 0, 1))) > 1e-6 \
        else np.array((1.0, 0.0, 0.0))
    key = tgt + d + side * span * 0.6 + np.array((0.0, 0.0, span * 0.8))
    return (f"light_source {{ {vec(key)}, color rgb <1, 0.97, 0.92> }}\n"
            f"light_source {{ {vec(eye)}, color rgb <0.45, 0.48, 0.55> shadowless }}\n")


# ----------------------------------------------------------------------------
# per-light model (Phase 2) - structured lights the viewer can edit.
#   A spec is a dict; missing keys fall back to DEFAULT_LIGHT.  color is rgb
#   floats 0..1, scaled by intensity.  area = soft shadows, spot = cone,
#   fade = distance falloff, shadowless = a pure fill that casts no shadow.
# ----------------------------------------------------------------------------
DEFAULT_LIGHT = {
    "pos": [5.0, 5.0, 5.0],
    "color": [1.0, 0.97, 0.92],     # rgb 0..1
    "intensity": 1.0,
    "shadowless": False,
    "fade": None,                   # None=off, else distance (float)
    "fade_power": 2,
    "area": None,                   # None=off, else {"size": float, "samples": int}
    "spot": None,                   # None=off, else {"radius","falloff","tightness"}
    "point_at": None,               # spot aim in viewer coords; None -> camera target
    "name": "light",
}


def _light(spec):
    """Return a light spec with the defaults filled in."""
    return {**DEFAULT_LIGHT, **(spec or {})}


def light_block(spec, cam=None):
    """One light_source {} block from a spec (multi-line when it has extras)."""
    s = _light(spec)
    r, g, b = s.get("color") or [1.0, 1.0, 1.0]
    i = float(s.get("intensity", 1.0))
    lines = ["light_source {",
             f"    {vec(s['pos'])}, color rgb <{_n(r * i)}, {_n(g * i)}, {_n(b * i)}>"]
    area = s.get("area")
    if area:
        size = float(area.get("size", 2.0))
        n = max(2, int(area.get("samples", 5)))
        lines.append(f"    area_light <{_n(size)}, 0, 0>, <0, 0, {_n(size)}>, {n}, {n}")
        lines.append("    adaptive 1")
        lines.append("    jitter")
    spot = s.get("spot")
    if spot:
        pa = s.get("point_at")
        pa = pa if pa is not None else (cam["target"] if cam else [0.0, 0.0, 0.0])
        lines.append(f"    spotlight radius {_n(spot.get('radius', 30))} "
                     f"falloff {_n(spot.get('falloff', 45))} "
                     f"tightness {_n(spot.get('tightness', 10))}")
        lines.append(f"    point_at {vec(pa)}")
    if s.get("fade") is not None:
        lines.append(f"    fade_distance {_n(s['fade'])} fade_power {_n(s.get('fade_power', 2))}")
    if s.get("shadowless"):
        lines.append("    shadowless")
    lines.append("}")
    return "\n".join(lines)


def tag_light_photons(block):
    """Let a shadow-casting light shoot photons; a shadowless fill stays quiet."""
    if "shadowless" in block or "photons" in block:
        return block
    b = block.rstrip()
    if not b.endswith("}"):
        return block
    return b[:-1].rstrip() + "\n    photons { reflection on refraction on }\n}"


def lights_pov(specs, cam=None, photons=False):
    """Render a list of light specs to POV text."""
    blocks = [light_block(s, cam) for s in (specs or [])]
    if photons:
        blocks = [tag_light_photons(b) for b in blocks]
    return "\n".join(blocks) + "\n"


def default_light_specs(cam):
    """The default key + shadowless fill as editable specs (matches default_lights)."""
    eye, tgt = np.array(cam["eye"], float), np.array(cam["target"], float)
    d = eye - tgt
    span = max(np.linalg.norm(d), 1.0)
    cz = np.cross(d, (0.0, 0.0, 1.0))
    side = unit(cz) if np.linalg.norm(cz) > 1e-6 else np.array((1.0, 0.0, 0.0))
    key = tgt + d + side * span * 0.6 + np.array((0.0, 0.0, span * 0.8))
    return [
        {"pos": [float(x) for x in key], "color": [1.0, 0.97, 0.92],
         "intensity": 1.0, "name": "key"},
        {"pos": [float(x) for x in eye], "color": [0.45, 0.48, 0.55],
         "intensity": 1.0, "shadowless": True, "name": "fill"},
    ]


CSG_POV = {"combine": "merge", "cut": "difference", "overlap": "intersection"}


def wrap(op, parts, name):
    """Return the parts combined under a CSG operator (union, difference ...) with a comment name."""
    return f"// {name}\n{op} {{\n" + "".join(indent(s.rstrip("\n")) + "\n" for s in parts) + "}\n"


def combine(shapes, items):
    """Shapes of one viewer object (twin pair, tube bends) become one, minus its hollow
    inner copies (_hole); a group that is a csg target (@name) or tool (_csg[2]) fuses into
    one solid; then each csg tool (_csg = (op, target name or @group)) wraps its target:
    merge / difference / intersection.  A target already wrapped is wrapped again (chains)."""
    owners, solid, holes, first = [], {}, {}, {}
    for s, it in zip(shapes, items):
        o = it.get("_owner") or f"#{len(owners)}"
        if o not in solid:
            owners.append(o)
            solid[o], holes[o], first[o] = [], [], it
        (holes if it.get("_hole") else solid)[o].append(s)
    body = {}
    for o in owners:
        p = solid[o]
        if not p:
            continue
        t = p[0] if len(p) == 1 else wrap(
            "merge" if any(i.get("_twin") for i in items if i.get("_owner") == o) else "union", p, o)
        body[o] = wrap("difference", [t] + holes[o], f"{o} hollow") if holes[o] else t
    csg_of = lambda it: tuple(it.get("_csg") or ()) + (None, None, False)[len(it.get("_csg") or ()):]  # noqa: E731
    fused = {str(csg_of(first[o])[1])[1:] for o in body if str(csg_of(first[o])[1]).startswith("@")}
    fused |= {str(csg_of(first[o])[2]) for o in body if csg_of(first[o])[2]}
    key_of, order, members = {}, [], {}
    for o in body:                             # _groups = group path, outermost first: innermost fused wins
        g = next((g for g in reversed(first[o].get("_groups") or []) if g in fused), None)
        k = "@" + g if g else o
        key_of[o] = k
        if k not in members:
            order.append(k)
            members[k] = []
        members[k].append(o)
    text, first_k = {}, {}
    for k in order:
        ms = members[k]
        text[k] = body[ms[0]] if len(ms) == 1 else wrap("merge", [body[o] for o in ms], f"group {k[1:]}")
        first_k[k] = next((first[o] for o in ms if first[o].get("_csg")), first[ms[0]])
    host = {k: k for k in order}
    for k in order:
        op, tgt, _grp = csg_of(first_k[k])
        tgt = tgt if str(tgt).startswith("@") else key_of.get(tgt)
        if op not in CSG_POV or tgt not in host:
            continue
        h = tgt
        while host[h] != h:                    # target already went into another csg
            h = host[h]
        if h == k:
            continue                           # a loop - leave it
        text[h] = wrap(CSG_POV[op], [text[h], text[k]], f"{h} {op} {k}")
        text[k], host[k] = None, h
    return [text[k] for k in order if text[k]]


# ----------------------------------------------------------------------------
# render / lighting settings  ->  the global_settings block + photon tags.
#   radiosity = soft indirect "bounce" light (colour bleed, filled shadows)
#   photons   = real caustics focused through glass / gems / metal
# A viewer passes scene_pov(..., render={...}); missing keys fall back here.
# ----------------------------------------------------------------------------
RADIOSITY = {
    "low":    "count 35 error_bound 0.6 nearest_count 5 recursion_limit 1 "
              "pretrace_start 0.08 pretrace_end 0.04",
    "medium": "count 100 error_bound 0.4 nearest_count 6 recursion_limit 2 "
              "pretrace_start 0.08 pretrace_end 0.02",
    "high":   "count 200 error_bound 0.25 nearest_count 10 recursion_limit 3 "
              "pretrace_start 0.08 pretrace_end 0.005",
}
DEFAULT_RENDER = {
    "radiosity": False, "radiosity_quality": "medium",
    "photons": False, "photons_count": 20000,
    "max_trace": 5, "ambient_light": None,
    # fog / atmosphere (Phase 3): "ground" = low mist layer, "distance" = uniform haze
    "fog": False, "fog_type": "ground", "fog_color": "#aeb4bf",
    "fog_distance": 18.0, "fog_height": 3.0, "fog_turbulence": 0.15,
    # sky (everything above the floor that no object blocks): "off", a SKY_PRESETS name,
    # or "image" (equirectangular panorama named in sky_image, kept in the pov folder)
    "sky": "off", "sky_top": "#2a5fb0", "sky_horizon": "#bcd6f0",
    "sky_image": "", "sky_rotate": 0.0,
}
SKY_PRESETS = ("gradient", "clouds", "sunset", "stars")


def _render(render):
    """Return the render settings with the defaults filled in."""
    return {**DEFAULT_RENDER, **(render or {})}


def global_settings_pov(render=None):
    """Return the POV global_settings block (gamma, trace level, radiosity, photons)."""
    r = _render(render)
    lines = ["    assumed_gamma 1.0", f"    max_trace_level {max(1, int(r['max_trace']))}"]
    if r.get("ambient_light"):
        lines.append(f"    ambient_light {r['ambient_light']}")
    if r.get("photons"):
        lines.append(f"    photons {{ count {max(1000, int(r['photons_count']))} "
                     "autostop 0 jitter 0.35 }")
    if r.get("radiosity"):
        q = RADIOSITY.get(r.get("radiosity_quality"), RADIOSITY["medium"])
        lines.append("    radiosity {\n        brightness 1\n        " + q + "\n    }")
    return "global_settings {\n" + "\n".join(lines) + "\n}"


def fog_pov(render, rgb_of):
    """Atmospheric fog (Phase 3).  'distance' = uniform haze that swallows far objects;
    'ground' = a low-lying mist layer that thins with altitude (y is up).  Smaller distance
    means thicker fog.  turbulence > 0 breaks a flat mist into drifting wisps.  Returns "" when
    fog is off.  POV-only: it shows in the render, not the fast GL / Tk preview."""
    r = _render(render)
    if not r.get("fog"):
        return ""
    col = rgb_of(r.get("fog_color") or "#aeb4bf") or (174, 180, 191)
    c = tuple(_n(x / 255.0) for x in col)
    dist = max(0.1, float(r.get("fog_distance", 18.0)))
    turb = max(0.0, float(r.get("fog_turbulence", 0.0)))
    lines = ["fog {"]
    if r.get("fog_type") == "ground":
        alt = max(0.01, float(r.get("fog_height", 3.0)))
        lines += ["    fog_type 2", "    fog_offset 0",
                  f"    fog_alt {_n(alt)}", "    up <0, 1, 0>"]
    else:
        lines += ["    fog_type 1"]
    lines += [f"    distance {_n(dist)}", "    color rgb <%s, %s, %s>" % c]
    if turb > 0:
        lines.append(f"    turbulence {_n(turb)}")
    lines.append("}")
    return "\n".join(lines)


def sky_pov(render, rgb_of):
    """A sky_sphere: a pigment wrapped on an infinite sphere that shows wherever a ray leaves the
    scene without hitting anything, so the floor and every object always draw in front of it.
    Returns (pov text, include file or None); ("", None) when the sky is off.  POV-only.
    (POV-Ray's own skies.inc fails to parse on this install, so presets are built here.)"""
    r = _render(render)
    mode = str(r.get("sky") or "off")
    if mode == "off":
        return "", None
    rot = float(r.get("sky_rotate") or 0.0)
    spin = f"\n    rotate <0, {_n(rot)}, 0>" if rot else ""

    def col(key, default):
        """Return a POV rgb color for settings key `key`, falling back to `default`."""
        c = rgb_of(r.get(key) or default) or rgb_of(default)
        return "rgb <%s, %s, %s>" % tuple(_n(x / 255.0) for x in c)
    top, hor = col("sky_top", "#2a5fb0"), col("sky_horizon", "#bcd6f0")
    # y runs -1..1 over the sphere; scale 2 / translate -1 maps that to 0..1 (horizon at 0.5)
    grad = "gradient y scale 2 translate -1"
    inc = None
    if mode == "gradient":
        layers = [f"pigment {{ {grad} color_map {{ [0 {hor}] [0.5 {hor}] [1 {top}] }} }}"]
    elif mode == "clouds":
        layers = [f"pigment {{ {grad} color_map {{ [0 {hor}] [0.5 {hor}] [1 {top}] }} }}",
                  "pigment { bozo turbulence 0.65 octaves 6 omega 0.7 lambda 2\n"
                  "        color_map { [0.0 rgbt <1, 1, 1, 1>] [0.45 rgbt <1, 1, 1, 1>]\n"
                  "                    [0.7 rgbt <1, 1, 1, 0.15>] [1.0 rgbt <0.85, 0.87, 0.92, 0>] }\n"
                  "        scale <0.25, 0.1, 0.25> }"]
    elif mode == "sunset":
        layers = [f"pigment {{ {grad} color_map {{ [0 rgb <0.95, 0.55, 0.25>] [0.5 rgb <0.98, 0.62, 0.3>]\n"
                  "        [0.56 rgb <0.85, 0.4, 0.4>] [0.68 rgb <0.45, 0.25, 0.5>]\n"
                  "        [1 rgb <0.05, 0.07, 0.22>] } }"]
    elif mode == "stars":
        layers = ["pigment { color rgb <0.01, 0.012, 0.03> }",
                  "pigment { granite scale 0.012\n"
                  "        color_map { [0 rgbt <1, 1, 1, 1>] [0.82 rgbt <1, 1, 1, 1>] [0.95 rgbt <1, 1, 1, 0.4>]\n"
                  "                    [1 rgbt <1, 1, 1, 0>] } }"]
    elif mode == "image":
        fname = os.path.basename(str(r.get("sky_image") or ""))
        if not fname:
            return "", None
        kind = IMAGE_TYPES.get(os.path.splitext(fname)[1].lower(), "png")
        layers = [f'pigment {{ image_map {{ {kind} "{fname}" map_type 1 interpolate 2 }} }}']
    else:
        return "", None
    body = "\n".join("    " + ly for ly in layers)
    return "sky_sphere {\n" + body + spin + "\n}", inc


def _reflective(text):
    """True if an object's material reflects or refracts (so photons should focus through it)."""
    low = text.lower()
    if "media {" in low:                            # a volume container, not a caustic surface
        return False
    return ("ior " in low) or ("reflection" in low) or ("metallic" in low) or ("interior {" in low)


def tag_object_photons(text):
    """Add a photons{} tag as the last modifier of a top-level object so it casts/receives
    caustics.  It must follow the shape's geometry, so it goes just before the closing brace.
    light_source blocks are told to shoot photons; reflective/refractive solids to catch them."""
    body = text.rstrip()
    if not body.endswith("}"):
        return text
    head = next((ln.strip() for ln in body.split("\n") if ln.rstrip().endswith("{")), "")
    if head.startswith("light_source"):
        tag = "    photons { refraction on reflection on }"
    elif _reflective(body):
        tag = "    photons { target on reflection on refraction on }"
    else:
        return text
    trailing = text[len(body):]                      # keep the original trailing newline(s)
    return body[:-1].rstrip() + "\n" + tag + "\n}" + trailing


def add_light_photons(lights_text):
    """Let each shadow-casting light shoot photons (fill lights marked shadowless stay quiet)."""
    out = []
    for ln in lights_text.split("\n"):
        s = ln.rstrip()
        if "light_source {" in s and "shadowless" not in s and "photons" not in s and s.endswith("}"):
            s = s[:-1].rstrip() + " photons { reflection on refraction on } }"
        out.append(s)
    return "\n".join(out)


def scene_pov(items, cam, rgb_of, background="#1b1d22", lights=None, extra="",
              render=None, light_specs=None):
    """Return the whole POV-Ray scene text: camera, background, lights, objects and render settings."""
    bg = rgb_of(background) or (27, 29, 34)
    r = _render(render)
    if light_specs is not None:                     # structured per-light model (Phase 2)
        lt = lights_pov(light_specs, cam, photons=r.get("photons", False))
    else:                                           # legacy text lights / auto default
        lt = lights if lights is not None else default_lights(cam)
        if r.get("photons"):
            lt = add_light_photons(lt)
    out = ["// Generated by viewer3d.py - edit the scene in the viewer, not here.",
           "#version 3.7;",
           '#include "colors.inc"',
           '#include "textures.inc"',
           global_settings_pov(r),
           "background { color rgb <%s, %s, %s> }" % tuple(_n(x / 255.0) for x in bg),
           *([fog_pov(r, rgb_of)] if r.get("fog") else []),
           "", camera_pov(cam), lt]
    includes = set()
    sky_text, sky_inc = sky_pov(r, rgb_of)
    if sky_text:
        out.insert(out.index(""), sky_text)
        if sky_inc:
            includes.add(sky_inc)
    shapes = combine([shape_pov(it, rgb_of, includes) for it in items], items)
    if r.get("photons"):
        shapes = [tag_object_photons(s) for s in shapes]
    out[4:4] =[f'#include "{inc}"' for inc in sorted(includes - {"textures.inc", "colors.inc"})]
    out += shapes
    if extra.strip():
        out += ["// ---- extra POV code", extra.strip(), ""]
    return "\n".join(out)


# ----------------------------------------------------------------------------
# running POV-Ray
# ----------------------------------------------------------------------------
def wsl_path(path):
    """Convert a Windows path to its WSL /mnt/... form."""
    path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(path)
    return "/mnt/" + drive.rstrip(":").lower() + rest.replace("\\", "/")


def render(pov_text, width, height, work_dir, quality="draft", timeout=300):
    """Render pov_text with POV-Ray (WSL on Windows).  Returns (png path or None, log).
    The .pov is written into work_dir so image maps / includes beside it are found."""
    os.makedirs(work_dir, exist_ok=True)
    fd, pov_path = tempfile.mkstemp(suffix=".pov", prefix="_render_", dir=work_dir)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(pov_text)
    png_path = pov_path[:-4] + ".png"
    qual = ["+Q5", "-A"] if quality == "draft" else ["+Q9", "+A0.2", "+AM2", "+R3"]
    args = [f"+I{os.path.basename(pov_path)}", f"+O{os.path.basename(png_path)}",
            f"+W{int(width)}", f"+H{int(height)}", *qual, "-D"]
    cmd = (["wsl", "--cd", wsl_path(work_dir), "povray"] + args) if os.name == "nt" \
        else ["povray"] + args
    try:
        proc = subprocess.run(cmd, cwd=work_dir, capture_output=True, timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log = (proc.stderr.decode("utf-8", "replace") + proc.stdout.decode("utf-8", "replace")).strip()
    except Exception as exc:                     # noqa: BLE001 - report anything to the caller
        log = f"could not run POV-Ray: {exc}"
    finally:
        try:
            os.remove(pov_path)
        except OSError:
            pass
    if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
        return png_path, log
    errs = [ln for ln in log.splitlines()
            if any(k in ln.lower() for k in ("error", "parse", "fatal", "expected", "undeclared"))]
    return None, "\n".join(errs) or log[-800:] or "POV-Ray produced no image."


def open_official_gui(pov_path=None):
    """Open the official POV-Ray program, optionally on `pov_path`."""
    subprocess.Popen([PVENGINE] + ([pov_path] if pov_path else []))


# ----------------------------------------------------------------------------
# cloud layers (Director): drifting noise planes at a set altitude.  Each layer casts a soft
# filtered shadow on the ground (the plane is invisible to the camera, "no_image"), and can also
# be drawn as a visible haze sheet to fly through.  clouds = {"sun": {...}, "layers": [...]}, all in
# the viewer's Z-up units (x east, y north, z up); compass headings are degrees clockwise from north.
#   layer: {"name", "alt", "heading", "speed", "coverage" 0-1, "soft" 0.02-0.5, "density" 0-1,
#           "size" (blob size, scene units), "visible" bool, "color", "seed"}
#   sun:   {"az", "el", "color", "brightness"}  - a parallel light, so shadows fall true
# Presets are in feet / ft-per-second and get scaled by clouds["ft"] (scene units per foot).
# ----------------------------------------------------------------------------
CLOUD_PRESETS = {
    "Morning fog (800 ft)":     dict(alt=800,   speed=2,  coverage=0.85, soft=0.45, density=0.55, size=2500, visible=True,  color="#e8ecf0"),
    "Stratus (6,000 ft)":       dict(alt=6000,  speed=25, coverage=0.55, soft=0.25, density=0.70, size=5000, visible=True,  color="#f2f4f7"),
    "Altocumulus (12,000 ft)":  dict(alt=12000, speed=40, coverage=0.45, soft=0.20, density=0.60, size=4000, visible=False, color="#f6f7f9"),
    "Thunderstorm (22,000 ft)": dict(alt=22000, speed=30, coverage=0.30, soft=0.12, density=0.92, size=9000, visible=False, color="#8c929c"),
    "Inversion cap (9,000 ft)": dict(alt=9000,  speed=6,  coverage=1.00, soft=0.50, density=0.50, size=12000, visible=True, color="#cfd3d9"),
}


def default_clouds():
    """Return a new cloud setup: units, sun and no layers."""
    return {"ft": 0.3048, "sun": {"az": 135.0, "el": 55.0, "color": "#fff4e0", "brightness": 1.1}, "layers": []}


def cloud_layer_from_preset(name, ft=0.3048, heading=270.0):
    """Return a cloud layer built from a named preset, scaled by `ft` and flying toward `heading`."""
    p = CLOUD_PRESETS[name]
    return {"name": name.split(" (")[0], "alt": p["alt"] * ft, "heading": heading, "speed": p["speed"] * ft,
            "coverage": p["coverage"], "soft": p["soft"], "density": p["density"], "size": p["size"] * ft,
            "visible": p["visible"], "color": p["color"], "seed": 0}


def _hex3(c, default):
    """Turn a '#rrggbb' color (or `default` if invalid) into three 0..1 number strings."""
    c = str(c or default).lstrip("#")
    if len(c) != 6:
        c = default.lstrip("#")
    return tuple(_n(int(c[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def sun_pov(sun):
    """A parallel 'sun' light (viewer Z-up az/el -> POV Y-up)."""
    az, el = math.radians(float(sun.get("az", 135.0))), math.radians(float(sun.get("el", 55.0)))
    x, y, z = math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)
    k = max(0.0, float(sun.get("brightness", 1.1)))
    r, g, b = (float(v) * k for v in (int(str(sun.get("color") or "#fff4e0").lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)))
    return (f"light_source {{ <{_n(x * 1e5)}, {_n(z * 1e5)}, {_n(y * 1e5)}>, color rgb <{_n(r)}, {_n(g)}, {_n(b)}> "
            "parallel point_at <0, 0, 0> }\n")


def cloud_pov(clouds, t):
    """POV text for every cloud layer at shot time t (seconds): the layers drift with t."""
    out = []
    for i, ly in enumerate(clouds.get("layers", [])):
        alt = float(ly.get("alt", 100.0))
        size = max(0.01, float(ly.get("size", 50.0)))
        cov = min(1.0, max(0.0, float(ly.get("coverage", 0.5))))
        soft = min(0.5, max(0.02, float(ly.get("soft", 0.25))))
        den = min(1.0, max(0.0, float(ly.get("density", 0.7))))
        h = math.radians(float(ly.get("heading", 270.0)))
        sp = float(ly.get("speed", 0.0)) * float(t)
        seed = float(ly.get("seed", 0)) + i
        th = 0.08 + (1.0 - cov) * 0.67               # bozo clusters round 0.5: map coverage onto that
        top = min(0.999, th + soft)
        tx, tz = math.sin(h) * sp + seed * 37.1, math.cos(h) * sp + seed * 91.7

        def pig(rgb, opacity):
            """Return the POV cloud pigment for a color and an opacity."""
            return (f"pigment {{ bozo turbulence 0.55 octaves 5 omega 0.5 lambda 2.2\n"
                    f"        color_map {{ [0 rgbt <{rgb}, 1>] [{_n(th)} rgbt <{rgb}, 1>] [{_n(top)} rgbt <{rgb}, {_n(1 - opacity)}>] "
                    f"[1 rgbt <{rgb}, {_n(1 - opacity)}>] }}\n"
                    f"        scale {_n(size)} translate <{_n(tx)}, {_n(i * 13.7)}, {_n(tz)}> }}")
        nm = str(ly.get("name") or f"layer{i}")
        out.append(f"// cloud layer: {nm}\nplane {{ y, {_n(alt)}\n    {pig('1, 1, 1', den)}\n"
                   "    finish { ambient 0 diffuse 0 }\n    no_image no_reflection\n}")
        if ly.get("visible"):
            col = ", ".join(_hex3(ly.get("color"), "#f2f4f7"))
            out.append(f"plane {{ y, {_n(alt)}\n    {pig(col, min(1.0, den * 0.9))}\n"
                       "    finish { ambient 0.75 diffuse 0.35 }\n    no_shadow\n}")
    return "\n".join(out) + ("\n" if out else "")
