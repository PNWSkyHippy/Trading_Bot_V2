"""mcp3d_server.py - headless MCP server for the 3D viewer (stdio).

One in-memory scene per server process, built with the same verbs as commands3d and the
turtle3d LOGO language.  It never draws anything: it returns text results and writes
files (STL / OBJ / scene CSV) whose paths it reports back.  Relative paths land in
./mcp_work/out next to this file.

Run:  python mcp3d_server.py            (stdio; point your MCP client at this command)
Needs: pip install mcp  (1.x or 2.x; plus numpy, manifold3d as for the viewer)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:                                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP  # noqa: E402
except ImportError:                     # mcp 2.x renamed it
    from mcp.server.mcpserver import MCPServer as FastMCP  # noqa: E402

import boolmesh  # noqa: E402
import turtle3d  # noqa: E402
import viewer3d as V  # noqa: E402
from commands3d import CmdError, Session  # noqa: E402

WORK = os.path.join(HERE, "mcp_work")
OUT = os.path.join(WORK, "out")
os.makedirs(OUT, exist_ok=True)

mcp = FastMCP("viewer3d")
sess = Session(mesh_dir=os.path.join(WORK, "meshes"))


def _path(p):
    return p if os.path.isabs(p) else os.path.join(OUT, p)


@mcp.tool()
def run_commands(text: str) -> str:
    """Run viewer verbs, one per line ('#' comments).  Verbs: new | add <shape> <nums> [at x,y,z]
    [color c1 [c2]] [name n] | import <file> | move <name> dx,dy,dz | rotate <name> <deg> on <x|y|z>
    [about center|origin|x,y,z] | scale <name> <f> | color <name> <c> | rename | delete | list |
    save <f.csv> | open <f.csv> | export <f.stl|.obj> [scale s] | turtle <f.logo>.
    Shapes: cube s | box dx dy dz | sphere r | cylinder r h | cone r h | prism sides r h | pyramid sides r h.
    Returns one result line per command; a failing line doesn't stop the rest."""
    return str(sess.run(text))


@mcp.tool()
def run_turtle(source: str) -> str:
    """Run a 3D LOGO program and add its meshes to the scene (grouped by part instance).
    Language: fd bk rt lt up down roll goto home pu pd pensize color joints detail; stamps cube box
    sphere cylinder cone; beginfill/endfill/fillthick; push/pop; repeat if for make; to..end;
    part..endpart with place <name> args [as inst] [mirror l|f|u] [scale s]; group..endgroup.
    Remember 'goto 5 -3 0' is three arguments (write 5-3 to subtract)."""
    try:
        return turtle3d.run(source, sess)
    except turtle3d.TurtleError as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def list_objects() -> str:
    """List scene objects with kind, group and bounding box."""
    if not sess.entries:
        return "scene is empty"
    rows = []
    for e in sess.entries:
        try:
            lo, hi = e.obj._bbox()
            box = f"x[{lo[0]:.2f},{hi[0]:.2f}] y[{lo[1]:.2f},{hi[1]:.2f}] z[{lo[2]:.2f},{hi[2]:.2f}]"
        except Exception:                                      # noqa: BLE001 - not every kind has one
            box = "no bbox"
        rows.append(f"{e.name}  [{e.kind}]  group={e.group or '-'}  color={e.c1 or '-'}  {box}")
    return "\n".join(rows)


@mcp.tool()
def measure(a: str, b: str = "") -> str:
    """Size of object `a`, or the distance between objects `a` and `b`."""
    try:
        return sess.measure(a, b or None)
    except CmdError as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def save_scene(path: str) -> str:
    """Save the scene as a viewer CSV (open it in the viewer).  Relative paths go to mcp_work/out."""
    p = _path(path)
    return sess.save(p)


@mcp.tool()
def open_scene(path: str) -> str:
    """Load a viewer scene CSV, replacing the current scene."""
    try:
        return sess.open(_path(path))
    except CmdError as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def export_mesh(path: str, scale: float = 1.0, only: str = "") -> str:
    """Write the scene as STL (binary) or OBJ by extension.  `scale` = viewer units to mm.
    `only` = comma separated object names.  Returns the absolute path written."""
    p = _path(path)
    try:
        msg = sess.export(p, scale, [n for n in only.split(",") if n] or None)
    except CmdError as exc:
        return f"ERROR: {exc}"
    return f"{msg}\n{os.path.abspath(p)}"


@mcp.tool()
def validate() -> str:
    """Printability check: is each object a closed watertight solid?  Lists problems."""
    if not sess.entries:
        return "scene is empty"
    for e in sess.entries:
        if e.obj is None:
            sess._rebuild(e)
    groups, skipped = V.scene_groups(sess.entries, 1.0)
    bad, ok = [], 0
    for name, facets in groups:
        try:
            man = boolmesh.to_manifold(facets)
            ok += 1
            vol = man.volume()
            if vol <= 0:
                bad.append(f"{name}: zero volume")
        except boolmesh.BoolError as exc:
            bad.append(f"{name}: {exc}")
    msg = f"{ok} closed solid(s)"
    if skipped:
        msg += f"; {len(skipped)} not printable (points/lines/planes)"
    return msg + ("\nPROBLEMS:\n" + "\n".join(bad) if bad else "\nall good")


if __name__ == "__main__":
    mcp.run()
