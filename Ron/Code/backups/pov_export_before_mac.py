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
    s = f"{float(v):.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def vec(p):
    """Viewer (x, y, z) -> POV <x, z, y>."""
    return f"<{_n(p[0])}, {_n(p[2])}, {_n(p[1])}>"


def unit(v):
    v = np.array(v, float)
    L = np.linalg.norm(v)
    return v / L if L > 1e-12 else v


def rgb_text(color, rgb_of):
    """'<r, g, b>' (0..1) for a Tk color name / #hex, or None."""
    c = rgb_of(color) if color else None
    return None if c is None else "<%s, %s, %s>" % tuple(_n(x / 255.0) for x in c)


def indent(text, pad="    "):
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
            os.path.expanduser(r"~\Documents\POV-Ray\v3.7\include")]
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
                f' interpolate 2 }} }}\n    finish {{ ambient 0.12 diffuse 0.85 specular 0.2 }} }}'), None
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
    k, v = item["kind"], [float(x) for x in item["nums"]]
    p = lambda i: np.array(v[i:i + 3])                      # noqa: E731

    def put(head, body, frame=None, **kw):
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


def scene_pov(items, cam, rgb_of, background="#1b1d22", lights=None, extra=""):
    bg = rgb_of(background) or (27, 29, 34)
    out = ["// Generated by viewer3d.py - edit the scene in the viewer, not here.",
           "#version 3.7;",
           '#include "colors.inc"',
           '#include "textures.inc"',
           "global_settings { assumed_gamma 1.0 }",
           "background { color rgb <%s, %s, %s> }" % tuple(_n(x / 255.0) for x in bg),
           "", camera_pov(cam), lights if lights is not None else default_lights(cam)]
    includes = set()
    shapes = [shape_pov(it, rgb_of, includes) for it in items]
    out[4:4] =[f'#include "{inc}"' for inc in sorted(includes - {"textures.inc", "colors.inc"})]
    out += shapes
    if extra.strip():
        out += ["// ---- extra POV code", extra.strip(), ""]
    return "\n".join(out)


# ----------------------------------------------------------------------------
# running POV-Ray
# ----------------------------------------------------------------------------
def wsl_path(path):
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
    subprocess.Popen([PVENGINE] + ([pov_path] if pov_path else []))
