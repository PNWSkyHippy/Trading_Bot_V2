"""commands3d.py - headless command layer for the 3D viewer (Project 2 seed).

A GUI-free way to BUILD a scene from a sequence of plain-text draw commands and
read / write it as scene CSV or printable STL/OBJ.  It reuses the viewer's own
build / transform / save / collect code - all module-level in viewer3d, no Tk -
so a CLI or an MCP server can produce the exact same geometry the interactive
viewer does, without ever opening a window.

    from commands3d import Session
    sess = Session()
    sess.run('''
        add cylinder 6 40 at 0,0,0 color silver      # rocket body
        add cone 6 14 at 0,0,40 color red            # nose
        add box 2 8 10 at 7,0,4 color red name fin    # a fin
        rotate fin 45 on z
        export rocket.stl scale 2
    ''')

Verbs (one per line; '#' starts a comment):
    new
    add <shape> <nums...> [at x,y,z] [color c1 [c2]] [name <n>]
        shapes: cube <size> | box <dx> <dy> <dz> | sphere <r> |
                cylinder <r> <h> | cone <r> <h> |
                prism <sides> <r> <h> | pyramid <sides> <r> <h>
    import <file> [name <n>] [scale <s>]
    move <name> [by] <dx,dy,dz>
    rotate <name> <deg> on <x|y|z> [about center|origin|x,y,z]
    scale <name> <factor> [about center|origin|x,y,z]
    color <name> <c1> [c2]
    rename <old> <new>
    delete <name>
    list
    save <file.csv>
    open <file.csv>
    export <file.stl|.obj> [scale <s>] [only <name>[,<name>...]]

Shapes are centred on `at` (default origin); cylinders/cones/prisms/pyramids
stand up the +Z axis.  rotate/scale default to the object's own centre.
"""
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import viewer3d as V      # noqa: E402  module-level build/run_tf/parse_row/save_scene/load_scene
import solids3d           # noqa: E402
import mesh_io            # noqa: E402

num = V.num
Entry = V.Entry
_ADD_KW = ("at", "color", "name")


class CmdError(Exception):
    """A command that could not be carried out (reported per line, not fatal to a batch)."""


# ---- token / argument parsing ----------------------------------------------

def _tokens(line):
    """Split on whitespace but keep "double quoted" runs (for paths with spaces),
    leaving backslashes untouched so Windows paths survive."""
    return [a or b for a, b in re.findall(r'"([^"]*)"|(\S+)', line)]


def _isnum(tok):
    try:
        float(tok)
        return True
    except ValueError:
        return False


def _xyz(tok):
    parts = tok.split(",")
    if len(parts) != 3:
        raise CmdError(f"expected x,y,z but got '{tok}'")
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        raise CmdError(f"bad coordinate '{tok}'")


def _pivot(tok):
    """A rotate/scale pivot token -> 'center' | 'origin' | (x,y,z)."""
    low = tok.lower()
    return low if low in ("center", "origin") else _xyz(tok)


# ---- shape number builders (match viewer3d.build's expected nums) -----------

def _cube_nums(size, c):
    s = size / 2.0
    cx, cy, cz = c
    base = [(cx - s, cy - s, cz - s), (cx + s, cy - s, cz - s),
            (cx + s, cy + s, cz - s), (cx - s, cy + s, cz - s)]
    top = [(x, y, cz + s) for (x, y, _z) in base]
    return [v for p in base + top for v in p]


def _box_nums(dx, dy, dz, c):
    hx, hy, hz = dx / 2.0, dy / 2.0, dz / 2.0
    cx, cy, cz = c
    base = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz)]
    top = [(x, y, cz + hz) for (x, y, _z) in base]
    return [v for p in base + top for v in p]


def _round_nums(r, h, c):
    """cylinder / cone: base centre, a base-edge point, height, +Z axis."""
    cx, cy, cz = c
    return [cx, cy, cz, cx + r, cy, cz, h, 0.0, 0.0, 1.0]


def _center_xyz(obj):
    """Best-effort world centre of a built object, for a baked scale pivot."""
    try:
        return tuple(float(v) for v in obj.get_center().get_xyz())
    except Exception:
        return (0.0, 0.0, 0.0)


# ---- the session ------------------------------------------------------------

class Session:
    """An in-memory scene the commands build.  Pure data + viewer3d's builders."""

    def __init__(self, mesh_dir=None):
        self.entries = []
        self.mesh_dir = mesh_dir or V.MESH_DIR
        V.MESH_DIR = self.mesh_dir      # build() resolves mesh3d sidecars against this

    # -- helpers
    def _unique(self, base):
        names = {e.name for e in self.entries}
        if base not in names:
            return base
        i = 2
        while f"{base}_{i}" in names:
            i += 1
        return f"{base}_{i}"

    def _find(self, name):
        for e in self.entries:
            if e.name == name:
                return e
        raise CmdError(f"no object named '{name}'")

    def _rebuild(self, e):
        """build + replay transforms (the GUI App.rebuild without the GUI / twins)."""
        obj = V.build(e)                                  # raises on bad geometry
        for row in e.transforms:
            V.run_tf(obj, V.parse_row(row), 1.0)
        e.obj = obj
        return obj

    # -- verbs
    def new(self):
        self.entries = []
        return "scene cleared"

    def add(self, shape, nums, at=(0, 0, 0), color=("", ""), name=None):
        shape = shape.lower()
        c1, c2 = (list(color) + ["", ""])[:2]

        def need(n):
            if len(nums) < n:
                raise CmdError(f"'{shape}' needs {n} number(s), got {len(nums)}")

        if shape == "cube":
            need(1); kind, n = "cube3d", _cube_nums(nums[0], at)
        elif shape == "box":
            need(3); kind, n = "cube3d", _box_nums(nums[0], nums[1], nums[2], at)
        elif shape == "sphere":
            need(1); kind, n = "sphere3d", [at[0], at[1], at[2], nums[0]]
        elif shape in ("cylinder", "cone"):
            need(2)
            kind = "cylinder3d" if shape == "cylinder" else "cone3d"
            n = _round_nums(nums[0], nums[1], at)
        elif shape in ("prism", "pyramid"):
            need(3)
            label = "Prism" if shape == "prism" else "Pyramid"
            kind, n = solids3d.add_nums(label, {
                "p": list(at), "e": [at[0] + nums[1], at[1], at[2]],
                "n": [0, 0, 1], "h": nums[2], "s": int(round(nums[0]))})
        else:
            raise CmdError(f"unknown shape '{shape}'")

        e = Entry(kind, self._unique(name or shape), c1, c2, n)
        self._rebuild(e)
        self.entries.append(e)
        return f"added {e.kind} '{e.name}'"

    def import_mesh(self, path, name=None, scale=1.0):
        if not os.path.isfile(path):
            raise CmdError(f"no such file: {path}")
        mesh_io.read_mesh(path)                            # validate before copying
        os.makedirs(self.mesh_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(path))[0] or "mesh"
        ext = os.path.splitext(path)[1].lower() or ".stl"
        dest = f"{base}_{time.strftime('%Y%m%d-%H%M%S')}{ext}"
        shutil.copyfile(path, os.path.join(self.mesh_dir, dest))
        e = Entry("mesh3d", self._unique(name or base), "white", "teal", [])
        e.mesh_src = dest
        if scale and abs(scale - 1.0) > 1e-12:
            e.transforms.append(["scale", num(scale)])
        self._rebuild(e)
        self.entries.append(e)
        return f"imported '{e.name}' ({len(e.obj.tris)} tris) from {os.path.basename(path)}"

    def move(self, name, d):
        e = self._find(name)
        e.transforms.append(["move", num(d[0]), num(d[1]), num(d[2])])
        self._rebuild(e)
        return f"moved '{name}' by {d[0]},{d[1]},{d[2]}"

    def rotate(self, name, deg, axis, pivot="center"):
        op = {"x": "xrot", "y": "yrot", "z": "zrot"}.get(axis.lower())
        if not op:
            raise CmdError(f"axis must be x, y or z (got '{axis}')")
        piv = None if pivot == "origin" else pivot        # 'origin' -> library default (origin)
        row = [op, num(deg)] + (V._pivot_fields(piv) if piv else [])
        e = self._find(name)
        e.transforms.append(row)
        self._rebuild(e)
        return f"rotated '{name}' {deg} deg on {axis.lower()}"

    def scale(self, name, factor, pivot="center"):
        e = self._find(name)
        if pivot == "center":                              # bake current centre as a fixed point
            piv = _center_xyz(e.obj) if e.obj is not None else (0.0, 0.0, 0.0)
        elif pivot == "origin":
            piv = None
        else:
            piv = pivot
        row = ["scale", num(factor)] + (V._pivot_fields(piv) if piv else [])
        e.transforms.append(row)
        self._rebuild(e)
        return f"scaled '{name}' by {factor}"

    def color(self, name, c1, c2=""):
        e = self._find(name)
        e.c1, e.c2 = c1 or "", c2 or ""
        self._rebuild(e)
        return f"recoloured '{name}'"

    def rename(self, old, new):
        e = self._find(old)
        if any(x.name == new for x in self.entries if x is not e):
            raise CmdError(f"name '{new}' already in use")
        e.name = new
        return f"renamed '{old}' -> '{new}'"

    def delete(self, name):
        e = self._find(name)
        self.entries.remove(e)
        return f"deleted '{name}'"

    def list(self):
        if not self.entries:
            return "scene is empty"
        out = []
        for e in self.entries:
            tf = f" +{len(e.transforms)}tf" if e.transforms else ""
            out.append(f"  {e.name}  [{e.kind}]{tf}")
        return f"{len(self.entries)} object(s):\n" + "\n".join(out)

    def save(self, path):
        V.save_scene(path, self.entries)
        return f"saved {len(self.entries)} object(s) -> {path}"

    def open(self, path):
        if not os.path.isfile(path):
            raise CmdError(f"no such file: {path}")
        self.entries = V.load_scene(path)
        failed = []
        for e in self.entries:
            try:
                self._rebuild(e)
            except Exception as exc:                       # noqa: BLE001 - report, keep going
                failed.append(f"{e.name} ({exc})")
        msg = f"opened {len(self.entries)} object(s) from {path}"
        return msg + (f"; could not build: {', '.join(failed)}" if failed else "")

    def export(self, path, scale=1.0, only=None):
        entries = self.entries
        if only:
            want = set(only)
            entries = [e for e in self.entries if e.name in want]
            missing = want - {e.name for e in entries}
            if missing:
                raise CmdError(f"no such object(s): {', '.join(sorted(missing))}")
        for e in entries:
            if e.obj is None:
                self._rebuild(e)
        groups, skipped = mesh_io.collect(entries, scale=scale)
        if not groups:
            raise CmdError("nothing printable to export (only points/lines/planes, or empty)")
        ext = os.path.splitext(path)[1].lower()
        if ext == ".obj":
            n = mesh_io.write_obj(path, groups)
        else:
            n = mesh_io.write_stl(path, groups, binary=(ext != ".stla"),
                                  name=os.path.splitext(os.path.basename(path))[0])
        skip = f"; skipped {len(skipped)}" if skipped else ""
        return f"exported {n} facet(s) -> {path}{skip}"

    # -- dispatch
    def _dispatch(self, tok):
        verb = tok[0].lower()
        rest = tok[1:]

        def need(n, what):
            if len(rest) < n:
                raise CmdError(f"{verb} needs {what}")

        if verb == "new":
            return self.new()
        if verb == "add":
            return self._p_add(rest)
        if verb == "import":
            return self._p_import(rest)
        if verb == "move":
            need(2, "a name and dx,dy,dz")
            j = 2 if rest[1].lower() == "by" else 1
            need(j + 1, "dx,dy,dz")
            return self.move(rest[0], _xyz(rest[j]))
        if verb == "rotate":
            return self._p_rotate(rest)
        if verb == "scale":
            need(2, "a name and a factor")
            piv = "center"
            if len(rest) > 2 and rest[2].lower() == "about":
                need(4, "a pivot after 'about'")
                piv = _pivot(rest[3])
            return self.scale(rest[0], float(rest[1]), piv)
        if verb == "color":
            need(2, "a name and a colour")
            return self.color(rest[0], rest[1], rest[2] if len(rest) > 2 else "")
        if verb == "rename":
            need(2, "an old and a new name")
            return self.rename(rest[0], rest[1])
        if verb == "delete":
            need(1, "a name")
            return self.delete(rest[0])
        if verb == "list":
            return self.list()
        if verb == "save":
            need(1, "a file path")
            return self.save(rest[0])
        if verb == "open":
            need(1, "a file path")
            return self.open(rest[0])
        if verb == "export":
            return self._p_export(rest)
        raise CmdError(f"unknown command '{verb}'")

    def _p_add(self, rest):
        if not rest:
            raise CmdError("add needs a shape")
        shape = rest[0]
        i = 1
        nums = []
        while i < len(rest) and _isnum(rest[i]):
            nums.append(float(rest[i]))
            i += 1
        at, color, name = (0, 0, 0), ("", ""), None
        while i < len(rest):
            k = rest[i].lower()
            if k == "at":
                at = _xyz(rest[i + 1]); i += 2
            elif k == "color":
                c1 = rest[i + 1]; i += 2
                if i < len(rest) and rest[i].lower() not in _ADD_KW:
                    color = (c1, rest[i]); i += 1
                else:
                    color = (c1, "")
            elif k == "name":
                name = rest[i + 1]; i += 2
            else:
                raise CmdError(f"unexpected '{rest[i]}' in add")
        return self.add(shape, nums, at, color, name)

    def _p_import(self, rest):
        if not rest:
            raise CmdError("import needs a file path")
        path = rest[0]
        name, scale, i = None, 1.0, 1
        while i < len(rest):
            k = rest[i].lower()
            if k == "name":
                name = rest[i + 1]; i += 2
            elif k == "scale":
                scale = float(rest[i + 1]); i += 2
            else:
                raise CmdError(f"unexpected '{rest[i]}' in import")
        return self.import_mesh(path, name, scale)

    def _p_rotate(self, rest):
        if len(rest) < 2:
            raise CmdError("rotate needs a name and an angle")
        name = rest[0]
        deg = float(rest[1])
        i = 2
        if i < len(rest) and rest[i].lower() == "on":
            i += 1
        if i >= len(rest):
            raise CmdError("rotate needs an axis (on x|y|z)")
        axis = rest[i]; i += 1
        pivot = "center"
        if i < len(rest) and rest[i].lower() == "about":
            pivot = _pivot(rest[i + 1])
        return self.rotate(name, deg, axis, pivot)

    def _p_export(self, rest):
        if not rest:
            raise CmdError("export needs a file path")
        path = rest[0]
        scale, only, i = 1.0, None, 1
        while i < len(rest):
            k = rest[i].lower()
            if k == "scale":
                scale = float(rest[i + 1]); i += 2
            elif k == "only":
                only = [s for s in rest[i + 1].split(",") if s]; i += 2
            else:
                raise CmdError(f"unexpected '{rest[i]}' in export")
        return self.export(path, scale, only)

    # -- batch runner
    def run(self, text):
        """Run a block of commands.  Never raises: each line's outcome is collected."""
        results = []
        for raw in text.splitlines():
            line = re.split(r"(?:^|\s)#", raw, 1)[0].strip()
            if not line:
                continue
            try:
                results.append(CmdResult(line, True, self._dispatch(_tokens(line))))
            except Exception as exc:                        # noqa: BLE001 - per-line report
                results.append(CmdResult(line, False, f"{type(exc).__name__}: {exc}"))
        return CmdReport(results)


class CmdResult:
    __slots__ = ("line", "ok", "msg")

    def __init__(self, line, ok, msg):
        self.line, self.ok, self.msg = line, ok, msg


class CmdReport:
    def __init__(self, results):
        self.results = results

    @property
    def errors(self):
        return sum(1 for r in self.results if not r.ok)

    @property
    def ok(self):
        return self.errors == 0

    def __str__(self):
        lines = []
        for r in self.results:
            lines.append(f"{'ok ' if r.ok else 'ERR'} | {r.line}")
            if not r.ok or (r.msg and "\n" in r.msg):
                lines.append(f"      -> {r.msg}")
        tail = "all ok" if self.ok else f"{self.errors} error(s)"
        return "\n".join(lines + [f"[{tail}]"])


def main(argv=None):
    """CLI: commands3d.py <script.cmds> [more.cmds ...]   (or '-' / no args = stdin)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv == ["-"]:
        text = sys.stdin.read()
    else:
        text = "\n".join(open(a, encoding="utf-8").read() for a in argv)
    sess = Session()
    report = sess.run(text)
    print(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
