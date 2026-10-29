"""Help system for the 3D viewer.

One window (HelpWindow) with an index on the left and, on the right, a drawn
diagram over an explanation.  F1 / ? / H in the viewer open it on the topic that
fits what is selected (context help); the index is the master menu for the whole
program.  Diagrams are painted with plain Tk canvas primitives so they work the
same whether the window is opened from the Tk viewer or popped from the Taichi
preview (GGUI can't draw images, so it asks the viewer to open this instead).
"""
import tkinter as tk
from tkinter import ttk

CANVAS_W, CANVAS_H = 500, 300
BG = "#fbfbfd"
INK = "#222"
MUTE = "#777"
BLUE = "#2b6cb0"
FILL = "#cfe3ff"
GREEN = "#2f855a"
GFILL = "#c6f6d5"
ORANGE = "#c05621"
OFILL = "#feebc8"
RED = "#c53030"

# --------------------------------------------------------------- draw helpers
def _arrow(c, x1, y1, x2, y2, color=INK, width=2, dash=None):
    c.create_line(x1, y1, x2, y2, arrow="last", fill=color, width=width,
                  dash=dash, capstyle="round")

def _line(c, x1, y1, x2, y2, color=INK, width=2, dash=None):
    c.create_line(x1, y1, x2, y2, fill=color, width=width, dash=dash, capstyle="round")

def _box(c, x, y, w, h, fill=FILL, outline=BLUE, width=2, dash=None):
    c.create_rectangle(x, y, x + w, y + h, fill=fill, outline=outline, width=width, dash=dash)

def _oval(c, x, y, w, h, fill=FILL, outline=BLUE, width=2):
    c.create_oval(x, y, x + w, y + h, fill=fill, outline=outline, width=width)

def _poly(c, pts, fill=FILL, outline=BLUE, width=2):
    c.create_polygon(pts, fill=fill, outline=outline, width=width)

def _txt(c, x, y, s, color=INK, size=9, anchor="center", bold=False):
    f = ("Segoe UI", size, "bold") if bold else ("Segoe UI", size)
    c.create_text(x, y, text=s, fill=color, font=f, anchor=anchor)

def _cube(c, x, y, s, fill=FILL, top="#eaf2ff", side="#aecbf0", outline=BLUE):
    """A small isometric-ish cube with its front-bottom-left corner near (x,y)."""
    d = s * 0.4
    # front
    _box(c, x, y, s, s, fill=fill, outline=outline)
    # top
    _poly(c, [x, y, x + d, y - d, x + s + d, y - d, x + s, y], fill=top, outline=outline)
    # right
    _poly(c, [x + s, y, x + s + d, y - d, x + s + d, y + s - d, x + s, y + s],
          fill=side, outline=outline)

# --------------------------------------------------------------- diagrams
def _d_overview(c):
    _txt(c, CANVAS_W / 2, 18, "The window has three parts", bold=True, size=11)
    _box(c, 30, 45, 250, 210, fill="#eef4ff")
    _txt(c, 155, 60, "3D view  —  orbit, pan, zoom", color=BLUE)
    _cube(c, 120, 150, 60)
    _box(c, 300, 45, 170, 95, fill="#f0fff4")
    _txt(c, 385, 58, "Object tree", color=GREEN, bold=True)
    for i, t in enumerate(("floor  (plane)", "wall1  (cube)", "lamp   (sphere)")):
        _txt(c, 315, 78 + i * 18, t, color=INK, size=8, anchor="w")
    _box(c, 300, 155, 170, 100, fill="#fffaf0")
    _txt(c, 385, 168, "Side panel", color=ORANGE, bold=True)
    for i, t in enumerate(("Add / Transform", "Group / Twin / CSG", "Colors / Layers")):
        _txt(c, 315, 188 + i * 18, t, color=INK, size=8, anchor="w")

def _d_navigate(c):
    _cube(c, 180, 160, 90)
    _arrow(c, 150, 120, 110, 95, color=BLUE)
    _arrow(c, 330, 120, 370, 95, color=BLUE)
    _txt(c, 240, 70, "drag Left = orbit", color=BLUE, bold=True)
    _txt(c, 240, 235, "drag Right = pan        wheel = zoom", color=INK)
    _txt(c, 240, 262, "W A S D fly,  R / F up-down,  Shift = faster", color=MUTE)

def _d_tree(c):
    _txt(c, CANVAS_W / 2, 18, "Click a row to select.  Shift / Ctrl pick more.", size=10)
    items = [(0, "floor"), (0, "house  (group)"), (1, "wall1"), (1, "wall2"),
             (1, "roof"), (0, "lamp")]
    for i, (depth, name) in enumerate(items):
        y = 55 + i * 34
        x = 60 + depth * 28
        sel = name == "wall1"
        _box(c, x, y, 300 - depth * 28, 26, fill="#dcecff" if sel else "#fff",
             outline=BLUE if sel else "#ccc", width=2 if sel else 1)
        _txt(c, x + 12, y + 13, name, anchor="w", bold=sel)
    _txt(c, 250, 245, "selected row is highlighted here and in the 3D view", color=MUTE)
    _txt(c, 250, 268, "Delete removes,  Ctrl+Z undo,  double-click = Properties", color=MUTE)

def _d_add(c):
    _txt(c, CANVAS_W / 2, 18, "Add menu:  pick a kind, type two points, OK", size=10)
    _cube(c, 55, 110, 46)
    _oval(c, 150, 70, 60, 60, fill=GFILL, outline=GREEN)
    _poly(c, [270, 120, 300, 60, 330, 120], fill=OFILL, outline=ORANGE)
    _oval(c, 380, 85, 70, 36, fill="#fed7e2", outline=RED)
    _line(c, 55, 190, 130, 165, color=INK)
    _txt(c, 92, 205, "Line / Vector", size=8)
    _txt(c, 78, 150, "Cube", size=8)
    _txt(c, 180, 140, "Sphere", size=8)
    _txt(c, 300, 135, "Cone", size=8)
    _txt(c, 415, 130, "Cylinder", size=8)
    _txt(c, 250, 250, "Solids, curved tubes and the Lathe tool are all in the Add menu", color=MUTE)

def _d_transforms(c):
    _txt(c, CANVAS_W / 2, 16, "Move / Center / Scale / Rotate the selection", size=10)
    _cube(c, 55, 110, 46)
    _arrow(c, 115, 95, 185, 95, color=GREEN, width=3)
    _cube(c, 190, 110, 46, fill=GFILL, outline=GREEN, top="#e6ffed", side="#9ae6b4")
    _txt(c, 150, 78, "Move X Y Z", color=GREEN, size=8)
    _cube(c, 300, 120, 32)
    _arrow(c, 345, 100, 375, 100, color=ORANGE, width=3)
    _cube(c, 380, 108, 56, fill=OFILL, outline=ORANGE, top="#fffaf0", side="#fbd38d")
    _txt(c, 360, 170, "Scale x2", color=ORANGE, size=8)
    c.create_arc(60, 210, 140, 275, start=200, extent=140, style="arc", outline=BLUE, width=3)
    _arrow(c, 128, 215, 138, 228, color=BLUE)
    _txt(c, 210, 245, "Rotate by degrees   (Undo transform steps back one)", color=INK, size=9, anchor="w")

def _d_pivot(c):
    _txt(c, CANVAS_W / 2, 16, "Rotate about a pivot point, or about an axis line", size=10)
    # pivot point
    cx, cy = 130, 150
    c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=RED, outline=RED)
    _txt(c, cx, cy + 16, "pivot", color=RED, size=8)
    for a in (0, 1, 2, 3):
        import math
        ang = math.radians(a * 30)
        x = cx + 70 * math.cos(ang)
        y = cy - 70 * math.sin(ang)
        _box(c, x - 10, y - 10, 20, 20, fill=FILL if a else "#fff",
             outline=BLUE, width=2 if a == 0 else 1)
    c.create_arc(cx - 70, cy - 70, cx + 70, cy + 70, start=0, extent=90,
                 style="arc", outline=BLUE, width=2, dash=(3, 2))
    # axis line
    _line(c, 320, 90, 440, 220, color=GREEN, width=3)
    _txt(c, 385, 230, "axis (vecrot)", color=GREEN, size=8)
    _box(c, 350, 120, 26, 26, fill=GFILL, outline=GREEN)
    c.create_arc(338, 108, 388, 158, start=20, extent=200, style="arc", outline=GREEN, width=2, dash=(3, 2))
    _txt(c, 250, 275, "Pivot = center / point / an object;  axis spins around any line", color=MUTE)

def _d_replicate(c):
    _txt(c, CANVAS_W / 2, 16, "Replicate:  N copies, each stepped and (optionally) smaller", size=9)
    x = 40
    s = 60
    for i in range(5):
        _cube(c, x, 160, s, fill=FILL if i == 0 else "#e6eefc")
        if i < 4:
            _arrow(c, x + s + 2, 150, x + s + 18, 150, color=MUTE, width=2)
        x += s + 20
        s *= 0.82
    _txt(c, 250, 250, "step X moves each copy over;  size x0.8 shrinks each one", color=INK)
    _txt(c, 250, 274, "put them in a group to move the whole run at once", color=MUTE)

def _d_ring(c):
    import math
    _txt(c, CANVAS_W / 2, 16, "Ring copy:  copies spread around a circle", size=10)
    cx, cy, r = 250, 165, 95
    c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#ccc", width=1, dash=(3, 3))
    for i in range(8):
        ang = math.radians(i * 45)
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        _box(c, x - 12, y - 12, 24, 24, fill=FILL, outline=BLUE)
    c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=RED, outline=RED)
    _txt(c, 250, 282, "from/to degrees set the spread;  add step for a spiral", color=MUTE)

def _d_groups(c):
    _txt(c, CANVAS_W / 2, 16, "Group:  tag objects so they move/scale together", size=10)
    _box(c, 55, 55, 240, 190, fill="", outline=GREEN, width=2, dash=(6, 4))
    _txt(c, 175, 70, "house", color=GREEN, bold=True)
    _cube(c, 80, 150, 50)
    _cube(c, 150, 150, 50, fill="#e6eefc")
    _poly(c, [80, 130, 155, 95, 230, 130], fill=OFILL, outline=ORANGE)
    _txt(c, 390, 120, "tag -> group name", size=9)
    _txt(c, 390, 145, "untag to remove", size=9, color=MUTE)
    _txt(c, 390, 170, "groups can nest", size=9, color=MUTE)

def _d_twin(c):
    _txt(c, CANVAS_W / 2, 16, "Twin:  a mirrored copy lifted off the first", size=10)
    _poly(c, [150, 180, 250, 180, 200, 110], fill=FILL, outline=BLUE)
    _poly(c, [150, 182, 250, 182, 200, 252], fill=GFILL, outline=GREEN)
    _line(c, 120, 181, 300, 181, color=MUTE, dash=(4, 3))
    _txt(c, 330, 150, "lift 100% = tip to tip", size=8, anchor="w")
    _txt(c, 330, 172, "lift 50% = half overlap", size=8, anchor="w")
    _txt(c, 330, 200, "axis X/Y/Z, flip option", size=8, anchor="w")

def _d_csg(c):
    _txt(c, CANVAS_W / 2, 16, "CSG:  combine two solids", size=10)
    labels = ("Union", "Difference", "Intersect")
    for i, lab in enumerate(labels):
        ox = 40 + i * 155
        cy = 130
        if lab == "Union":
            _oval(c, ox, cy - 30, 70, 70, fill=FILL, outline=BLUE)
            _oval(c, ox + 40, cy - 30, 70, 70, fill=FILL, outline=BLUE)
        elif lab == "Difference":
            _oval(c, ox, cy - 30, 70, 70, fill=FILL, outline=BLUE)
            _oval(c, ox + 40, cy - 30, 70, 70, fill="#fff", outline="#bbb")
        else:
            _oval(c, ox, cy - 30, 70, 70, fill="#fff", outline="#bbb")
            _oval(c, ox + 40, cy - 30, 70, 70, fill="#fff", outline="#bbb")
            c.create_oval(ox + 40, cy - 30, ox + 70, cy + 40, fill=FILL, outline=BLUE)
        _txt(c, ox + 55, cy + 70, lab, bold=True, size=9)
    _txt(c, 250, 250, "click the FIRST object, then CSG, then pick the target by name", color=MUTE)
    _txt(c, 250, 272, "@name targets a whole group", color=MUTE)

def _d_hollow(c):
    _txt(c, CANVAS_W / 2, 16, "Hollow:  shell out a solid, set wall thickness", size=10)
    _box(c, 150, 70, 200, 170, fill="#e6eefc", outline=BLUE)
    _box(c, 170, 90, 160, 130, fill=BG, outline=BLUE, dash=(4, 3))
    _arrow(c, 150, 60, 170, 60, color=RED)
    _arrow(c, 170, 60, 150, 60, color=RED)
    _txt(c, 160, 48, "wall", color=RED, size=8)
    _txt(c, 250, 155, "cavity", color=MUTE)
    _txt(c, 250, 262, "open end:  none / top / both  (like a pipe or a cup)", color=MUTE)

def _d_align(c):
    _txt(c, CANVAS_W / 2, 16, "Align:  snap objects to the first one clicked", size=10)
    _line(c, 90, 150, 410, 150, color=RED, dash=(5, 3))
    _box(c, 90, 120, 50, 50, fill=GFILL, outline=GREEN)
    _txt(c, 115, 185, "first (stays)", color=GREEN, size=8)
    for x in (200, 300, 370):
        _box(c, x, 100 + (x % 60), 40, 40, fill="#e6eefc", outline=BLUE, dash=(3, 2))
        _arrow(c, x + 20, 100 + (x % 60) + 40, x + 20, 148, color=BLUE, width=1)
        _box(c, x, 128, 40, 40, fill=FILL, outline=BLUE)
    _txt(c, 250, 250, "pick axes (X/Y/Z) and how:  min / center / max edge", color=MUTE)

def _d_colors(c):
    _txt(c, CANVAS_W / 2, 16, "Colors:  line color and fill color", size=10)
    _cube(c, 150, 170, 110, fill="#ffd6d6", top="#ffecec", side="#ffb3b3", outline=RED)
    _txt(c, 205, 230, "line = outline", color=RED, size=9)
    _txt(c, 205, 100, "fill = faces", color=INK, size=9)
    _box(c, 360, 90, 40, 40, fill="#ffd6d6", outline=RED, width=3)
    _box(c, 360, 150, 40, 40, fill="#ffd6d6", outline="#888")
    _txt(c, 410, 110, "line", anchor="w", size=8)
    _txt(c, 410, 170, "fill", anchor="w", size=8)

def _d_material(c):
    _txt(c, CANVAS_W / 2, 16, "Material:  a POV-Ray look, optional image texture", size=9)
    _box(c, 120, 70, 150, 150, fill="#d7c2a0", outline=ORANGE)
    for i in range(1, 5):
        _line(c, 120 + i * 30, 70, 120 + i * 30, 220, color="#b89b74", width=1)
        _line(c, 120, 70 + i * 30, 270, 70 + i * 30, color="#b89b74", width=1)
    _txt(c, 195, 240, "tex scale sets the tile size", color=MUTE, size=9)
    _txt(c, 340, 110, "pick Group ->", size=9, anchor="w")
    _txt(c, 340, 135, "pick Material", size=9, anchor="w")
    _txt(c, 340, 170, "or load your", size=9, anchor="w", color=MUTE)
    _txt(c, 340, 190, "own image file", size=9, anchor="w", color=MUTE)

def _d_layers(c):
    _txt(c, CANVAS_W / 2, 16, "Layers:  tag objects, then show or hide a whole layer", size=9)
    sheets = [("Default", "#cfe3ff", True), ("Walls", "#c6f6d5", True),
              ("Wiring", "#feebc8", False), ("Notes", "#fed7e2", True)]
    for i, (name, col, shown) in enumerate(sheets):
        y = 70 + i * 42
        x = 120 - i * 10
        _poly(c, [x, y, x + 180, y, x + 150, y + 30, x - 30, y + 30],
              fill=col if shown else "#eee", outline=BLUE if shown else "#bbb")
        _txt(c, x + 75, y + 15, name + ("" if shown else "   (hidden)"),
             color=INK if shown else MUTE, size=9)
    _txt(c, 250, 262, "unticking a layer hides it in the 3D view, preview and render", color=MUTE)

def _d_snapshots(c):
    _txt(c, CANVAS_W / 2, 16, "Snapshots:  save the current camera to come back to", size=9)
    _oval(c, 60, 120, 44, 44, fill="#333", outline="#000")
    _poly(c, [100, 130, 130, 120, 130, 165, 100, 155], fill="#555", outline="#000")
    _txt(c, 82, 180, "camera", size=8, color=MUTE)
    for i in range(3):
        x = 200 + i * 90
        _box(c, x, 110, 70, 55, fill="#eef4ff")
        _cube(c, x + 18, 150, 28)
        _txt(c, x + 35, 178, f"view {i + 1}", size=8)
    _txt(c, 250, 250, "click a saved snapshot to fly the camera back to it", color=MUTE)

def _d_director(c):
    import math
    _txt(c, CANVAS_W / 2, 16, "Director (F8):  camera keys along a path for a flythrough", size=9)
    pts = [(70, 220), (160, 140), (260, 200), (360, 110), (440, 160)]
    for i in range(len(pts) - 1):
        _line(c, *pts[i], *pts[i + 1], color=BLUE, width=2, dash=(5, 3))
    for i, (x, y) in enumerate(pts):
        _poly(c, [x, y, x + 22, y - 7, x + 22, y + 7], fill=OFILL, outline=ORANGE)
        _txt(c, x + 6, y - 16, f"cam{i + 1}", size=8, color=ORANGE)
    _txt(c, 250, 262, "set eye / aim / fov per key;  Play flies through them in order", color=MUTE)

def _d_pov(c):
    _txt(c, CANVAS_W / 2, 16, "POV-Ray render (F9):  the photo-quality picture", size=10)
    _box(c, 60, 60, 170, 150, fill="#eef4ff")
    _txt(c, 145, 50, "Draft (fast)", color=BLUE, size=9)
    _cube(c, 110, 160, 50, top="#eaf2ff", side="#aecbf0")
    _box(c, 280, 60, 170, 150, fill="#2b2b35")
    _txt(c, 365, 50, "Final (slow, lit)", color=INK, size=9)
    _cube(c, 330, 160, 50, fill="#8fb3e0", top="#cfe3ff", side="#5a7fb0", outline="#1a3a60")
    _txt(c, 250, 232, "toggle Draft/Final, set width in px, then Render now", color=MUTE)
    _txt(c, 250, 258, "Save .pov writes the scene file;  Open POV GUI launches POV-Ray", color=MUTE)

def _d_taichi(c):
    _txt(c, CANVAS_W / 2, 16, "Taichi preview (F10):  a fast GPU window you can drag in", size=9)
    _box(c, 60, 55, 250, 200, fill="#1a1a22", outline="#444")
    _cube(c, 150, 170, 60, fill="#8fb3e0", top="#cfe3ff", side="#5a7fb0", outline="#1a3a60")
    _arrow(c, 180, 150, 230, 120, color="#f6e05e")
    _txt(c, 250, 110, "drag to move", color="#f6e05e", size=8)
    _box(c, 330, 55, 140, 200, fill="#fffaf0", outline=ORANGE)
    _txt(c, 400, 68, "menu", color=ORANGE, bold=True, size=9)
    for i, t in enumerate(("Add", "Transform", "Group", "Layers", "Help")):
        _txt(c, 345, 95 + i * 26, "- " + t, anchor="w", size=8)
    _txt(c, 250, 275, "same actions as the main window;  orbit/pan/fly here too", color=MUTE)

def _d_scripts(c):
    _txt(c, CANVAS_W / 2, 16, "Scripts:  run a .py file that builds objects", size=10)
    _box(c, 70, 90, 110, 120, fill="#fff", outline="#888")
    _txt(c, 125, 78, "build.py", size=9, color=MUTE)
    for i in range(4):
        _line(c, 85, 110 + i * 22, 165, 110 + i * 22, color="#bbb", width=1)
    _arrow(c, 190, 150, 270, 150, color=GREEN, width=3)
    _cube(c, 300, 150, 44, fill=GFILL, outline=GREEN, top="#e6ffed", side="#9ae6b4")
    _cube(c, 370, 150, 44, fill=GFILL, outline=GREEN, top="#e6ffed", side="#9ae6b4")
    _txt(c, 250, 230, "Replay re-runs it;  Keep script objects turns them into real entries", color=MUTE)

# --------------------------------------------------------------- topics
TOPICS = {}

def _topic(tid, title, body, draw=None):
    TOPICS[tid] = {"title": title, "body": body.strip("\n"), "draw": draw}

_topic("overview", "Welcome / Overview", """
A sandbox for building 3-D scenes out of simple parts and rendering them.

- The 3D view (left) shows the scene; drag to look around.
- The object tree (top right) lists everything; click to select.
- The side panel (right) is where you add objects and change them.

Build a scene, then render it with POV-Ray (F9) for a lit picture, or open the
Taichi preview (F10) for a fast GPU view you can spin and drag things in.

Press F1 any time for help on whatever you have selected.  Everything in the
program is listed on the left of this window.
""", _d_overview)

_topic("navigate", "Moving the camera", """
- Drag with the LEFT button to orbit around the scene.
- Drag with the RIGHT button to pan (slide) the view.
- Mouse wheel zooms in and out.
- Fly with the keyboard: W/S forward-back, A/D left-right, R/F up-down,
  arrow keys turn.  Hold Shift to move faster.

The camera you set here is what the POV-Ray render and the Taichi preview use.
""", _d_navigate)

_topic("tree", "The object tree & selecting", """
Every object in the scene is a row in the tree.

- Click a row to select it; it lights up here and in the 3D view.
- Shift-click or Ctrl-click to select several at once.
- Delete removes the selection; Ctrl+Z undoes, Ctrl+Y redoes.
- Double-click opens the Properties editor for that object.
- Ctrl+A selects all, Esc selects none.

Groups show as a parent row with their members nested underneath.
""", _d_tree)

_topic("add", "Adding objects", """
Pick a kind from the Add box, type the two defining points (center and an edge
point, usually), and press OK.

Available kinds include points, lines and vectors; flat shapes (square, circle,
plane); solids (cube, sphere, cylinder, cone, prism, pyramid, ellipsoid,
polyhedron and more); curved tubes and bends; and the Lathe tool for spinning a
profile into a solid.

New objects land at the coordinates you type, so you can place them exactly.
""", _d_add)

_topic("transforms", "Move, Center, Scale, Rotate", """
With something selected:

- Move by:  shift it by X Y Z.
- Center to:  put its center at an exact X Y Z.
- Scale:  multiply its size (a group scales about its own center).
- Rotate:  turn it by a number of degrees (see Pivot & axis).
- Undo transform:  step back one transform without undoing anything else.

Transforms stack up and are listed for the object, so you can see its history.
""", _d_transforms)

_topic("pivot", "Pivot & axis (for Rotate)", """
Rotate needs to know what to turn around.

- Pivot = center:  spins in place about its own middle.
- Pivot = point:  spins about an exact X Y Z you type.
- Pivot = an object:  spins about that object's center.
- Axis (vecrot):  spins about any line, from one point to another - useful for
  tilting something at an angle.

Ring copy uses the same pivot and axis choices to spread copies around.
""", _d_pivot)

_topic("replicate", "Replicate (rows & grids)", """
Make N copies of the selection, each one stepped over from the last:

- Copies:  how many.
- Step X / Y / Z:  how far each copy moves from the one before.
- Size each copy x:  0.8 makes every copy 80% of the previous (a taper); 1 keeps
  them the same.
- Into group:  optionally drop them all into a named group.

Repeat with different step axes to build grids and stacks.
""", _d_replicate)

_topic("ring", "Ring copy (circular arrays)", """
Spread copies around a circle instead of a line:

- Copies and From/To degrees set how many and how far around they go.
- Pivot / point / axis say what they circle around (same as Rotate).
- Step each copy turns it into a spiral.
- Size each copy shrinks each one for a cone of copies.

Great for columns around a room, teeth on a gear, petals on a flower.
""", _d_ring)

_topic("groups", "Groups & tagging", """
A group is just a name shared by several objects so you can treat them as one.

- Select objects and Tag them with a group name.
- Moving, scaling or rotating a grouped object moves the whole group.
- Untag takes an object back out of its group.
- Groups can nest:  a group can be a member of a bigger group.

The tree shows a group as a parent row with its members underneath.
""", _d_groups)

_topic("twin", "Twin (mirror copy)", """
Twin adds a mirrored copy of the object, lifted off the original along an axis.

- Lift %:  100 puts them tip to tip; 50 overlaps them halfway.
- Axis:  which way the twin is lifted (X, Y or Z).
- Flip first:  mirror the original too, for a symmetric pair.

Good for making symmetric shapes - wings, arches, reflected halves.
""", _d_twin)

_topic("csg", "CSG (combine solids)", """
Constructive solid geometry fuses or cuts one solid with another.

- Union:  the two become one.
- Difference:  the target is carved out of the first (holes, slots).
- Intersect:  keep only the overlap.

Click the FIRST object, open CSG, choose the operation, then pick the target by
name.  Use @name as the target to combine with a whole group at once.

The cut is real geometry: the preview shows the carved target (the tool stays as a
dashed wire), and the STL/OBJ export and the render carry it too.  A cut that sits
completely inside a solid makes a sealed void - let the tool poke out through a face
to open it.  Needs the manifold3d package (pip install manifold3d).
""", _d_csg)

_topic("hollow", "Hollow (shell out a solid)", """
Turn a solid into a shell with walls of a set thickness.

- Wall thickness:  how thick the remaining shell is.
- Open end:  none (a closed box), top (a cup), or both (a pipe or tube).

Combine with CSG and Twin to build enclosures, cups, pipes and casings.
""", _d_hollow)

_topic("align", "Align", """
Line objects up against the first one you clicked (which stays put).

- Axes:  which directions to align (X, Y and/or Z).
- How:  match their min edge, their centers, or their max edge.

Select the anchor object first, then the others, then Align.
""", _d_align)

_topic("colors", "Colors", """
Each object has two colors:

- Line color:  its outline/wireframe in the 3D view.
- Fill color:  its faces.

Type a color name or pick one with the "..." button.  Colors carry through to
the POV-Ray render unless a Material overrides them.
""", _d_colors)

_topic("material", "Materials & textures", """
A material gives an object a POV-Ray look - metal, glass, wood, stone and so on.

- Pick a Group, then a Material within it.
- Tex scale sets how big an image texture tiles across the surface.
- Image file...  uses your own picture as the texture.

Materials show in the render (F9); the 3D view stays a simple shaded preview.
""", _d_material)

_topic("layers", "Layers", """
Layers let you tag objects into named sheets and show or hide them in bulk.

- Set layer:  put the selected objects on a layer (blank = the Default layer).
- The show/hide checkboxes turn a whole layer on or off at once.
- Hiding a layer hides it everywhere - the 3D view, the Taichi preview and the
  POV-Ray render all honour it.

Use layers to park work-in-progress, separate rooms, or hide clutter while you
work on one part.
""", _d_layers)

_topic("snapshots", "Snapshots", """
Save the current camera position as a snapshot so you can return to it later.

- Menu bar: View > Save current view...  names the camera you have now.
- View > Go to saved view > (name)  flies the camera back to it.
- View > Delete saved view removes one.
- In the Taichi preview: Camera section > "Save this view as a snapshot..." and
  "Go to a saved view..." (after going to one, press R to jump there).

Snapshots are stored with the scene (<scene>.views.json), so your favourite
angles come back next time you open it.  (Not the same as "Render snapshot from
here (C)", which makes a POV-Ray picture from the current view.)
""", _d_snapshots)

_topic("director", "Director (camera paths)", """
The Director (F8) builds a flythrough from a series of camera keys.

- Each key stores an eye position, an aim point and a field of view.
- The keys join into a path; Play flies the camera through them in order.
- Select a key to edit its eye / aim / fov in the View panel.
- Lights tab: the shot carries its own lamps (drag them in the preview).
  Each one can now be a plain point light, a Spotlight cone (aims at the
  camera target, with cone radius / softness / tightness), a Shadowless
  fill, and/or have a Fade distance.  These are separate from the F5 scene
  lights - F5 lights a still of the main scene, the Director's own lights
  light the movie.  No shot lights = the viewer's auto key + moving fill.

Use it for walkthroughs and turntable animations of your scene.
""", _d_director)

_topic("pov", "POV-Ray render", """
POV-Ray makes the final lit, shaded picture (F9).

- Draft is quick and flat; Final is slower but properly lit.
- Width (px) sets the picture size.
- Render now builds it; Save .pov writes the scene file; Open POV GUI launches
  POV-Ray itself.

Set your camera in the 3D view (or with the Director) first - that's the shot.
(In the Taichi preview, press C to render from exactly where you're standing.)

Where renders go:
- Every render is saved in the pov/ folder beside the app, with a unique
  timestamped name: render_YYYYMMDD-HHMMSS.png - so nothing is ever overwritten.
- render.png is always refreshed to the most recent one, for convenience.
- The render window's title bar shows the file name; the toolbar on it has
  "Open folder" (reveals the file on disk) and "Save as…" (write it anywhere
  under a name you choose).  The console also prints the full path each time.

For how the scene is lit, see Lights (F5) and Lighting / global illumination (F6).
""", _d_pov)

_topic("lighting", "Lighting / global illumination (F6)", """
The Lighting panel (F6, or the "Lighting" button on the POV row) controls the
two extra passes POV-Ray can run for a richer, more realistic picture:

- Radiosity: soft indirect "bounce" light.  Surfaces pick up colour from their
  neighbours and shadows fill in gently, the way a real room looks.  Quality
  low / medium / high trades speed for smoothness.
- Photons: real caustics - the focused pools and sparkle that light makes
  shining through glass, gems or off metal.  Count sets how many are shot
  (more = cleaner caustics, slower).  Only glass / gem / metal materials catch
  them; shadowless fill lights don't shoot them.
- Max trace level: how many times a ray may bounce through glass and mirrors.
  Raise it when deep glass or many reflections look black or cut off.
- Fog / atmosphere: haze in the air.  "Ground" is a low mist layer that hugs
  the floor and thins with height (set Mist height); "distance" is a uniform
  haze that fades far objects out.  Distance sets the thickness - smaller is
  thicker.  Turbulence breaks a flat mist into drifting wisps, and Colour tints
  it.  Fog shows in the render only, not the fast live preview.

These passes add render time.  Turn them on for the final beauty render; leave
them off for quick Draft previews.  The same controls are in the Taichi menu
under "Lighting / global illumination" (fog on/off, type and distance there;
height, turbulence and colour live in the full F6 panel).

Fog is baked into Director movies too, so a whole fly-through can sit in mist.
""", None)

_topic("prism", "Prism beam - cast a rainbow", """
Scene menu -> "Prism beam (cast rainbow)" (also in the Taichi menu's Add
section) drops a complete little rainbow rig in one click:

- a triangular glass prism (three sides - that's what splits white light into
  a spectrum; a box has parallel faces that recombine it, so no rainbow),
- a bright, narrow white spotlight aimed through it,
- a plain floor for the rainbow to land on (only if the scene has none yet),
- and it switches photons on (200k, max trace 8) so the caustic actually casts.

Render it with F9.  The rainbow lands on the floor on the far side of the prism
from the light - red through blue, with a bright refracted spot beside it.

Tips:
- Dim or delete the other lamps (F5) for a bolder, cleaner rainbow against dark.
- The prism, floor and "prism beam" lamp are ordinary objects - move, aim or
  recolour them like anything else.  Aim the beam squarely at a flat face.
- The effect lives in the "Prism rainbow" material (strong dispersion) plus
  photons; it only shows in the F9 render, not the fast live preview.
""", None)

_topic("export", "Export STL / OBJ - print your objects", """
File menu -> "Export mesh (STL/OBJ)..." (also in the Taichi menu's Scene file
section) turns your objects into a triangle mesh and writes a file any slicer
(Cura, PrusaSlicer, Bambu) can open.

The dialog asks three things:

- Scope: just the Selected objects, or the Whole scene.
- Format: STL (binary) - smallest, the usual choice; STL (ASCII) - text you
  can read; or OBJ - keeps each object as its own named group.
- Scale (units -> mm): how many millimetres one viewer unit becomes in the
  slicer.  A 2-unit cube at scale 10 prints as a 20 mm cube.  The console
  prints the final bounding-box size in mm so you can sanity-check it.

What exports: every solid - cube, sphere, cylinder, cone, the prisms /
pyramids / polyhedra, truncated cones and caps, lathe surfaces, and curved
tubes (torus / curved cylinder).  All current transforms are baked in, so what
you see is what prints.  Flat helpers with no volume - points, lines, vectors,
bare planes, squares and circles - have nothing to print, so they are listed as
"skipped" and left out.

Print notes:
- The solids come out watertight (manifold), which is what a slicer needs.
- No axis flip: the viewer and every slicer are both Z-up, so up stays up.
- CSG (cut / union) objects export as they render.  Very thin walls may need a
  larger scale to survive slicing.
""", None)

_topic("import", "Import a mesh - bring in STL / OBJ", """
File menu -> "Import mesh (STL/OBJ)..." (also in the Taichi menu's Scene file
section) reads a 3D model off disk and drops it into the scene as one object.
Point it at any STL (binary or text) or Wavefront OBJ - the kind of file a
slicer, Thingiverse download or another 3D app gives you.

What happens:

- The file is copied into the app's meshes/ folder and the scene row just
  remembers its name, so the model travels with the scene and the original on
  disk is never touched.
- It becomes an ordinary "mesh3d" object.  Move, rotate, scale, group, layer,
  twin, cut/union (CSG) and re-export it exactly like a cube or a lathe shape -
  all the same controls apply.
- No axis flip: the viewer and every slicer are Z-up, so a model keeps its
  orientation coming in and going back out.

Notes:
- The mesh is welded on load (duplicate corners merged, collapsed facets
  dropped) so it stays watertight for printing and CSG.
- Geometry stays as it was authored - the import does not re-tessellate or
  smooth it.  A heavy model (hundreds of thousands of triangles) draws as a
  bounding box in the Tk viewport to stay responsive; the Taichi preview and
  the POV render show every triangle.
- Scale on import is 1:1 (one file unit = one viewer unit).  If a model comes in
  tiny or huge, select it and scale it once in the scene.
""", None)

_topic("slice", "Slice plane - section view and cut", """
Taichi menu -> Slice plane (section view / cut an object).  Tick it and a
translucent plane appears through the selected object (the plane re-centres on
whatever you select, so switching objects moves it there).

- Arrows on the plane slide it; grab a coloured ring (the line itself) to turn it.
  The X/Y/Z position and "turn about" sliders do the same numerically, and the
  three buttons snap it flat (cuts across Z) or facing X or Y.
- The white arrow points to the half that goes.  "Cut away the other side" flips it.
- By default only the SELECTED object is clipped in the preview; tick "Cut
  everything in the preview" to see the whole scene in section.
- "Leave the cut OPEN" shows the hollow inside instead of a flat cap.
- "Add this plane, set up another cut" stacks planes (a wedge, a slot, a corner);
  "Drop the last added plane" undoes the last one.

Nothing is changed until you press "CUT the selected object here".  That bakes
every staged plane into the object, which becomes a closed mesh (name, colours,
group and layer stay).  Ctrl+Z undoes it.  Each cut result is a real solid, so it
exports to STL and takes part in CSG like anything else.

Notes:
- The object must be a closed solid (cube, sphere, cylinder, imported mesh ...).
  Planes, lines and open shapes can't be cut.
- Needs the manifold3d package in the viewer's Python.  On the Mac the viewer runs
  on python3.15 (has it) and launches Taichi from the venv via TAICHI_PYTHON.
- If the plane misses the object, or takes all of it, nothing changes and the
  console says so.
""", None)

_topic("quickcut", "Quick cut / Quick keep - scissors", """
Taichi menu, under the Slice plane controls.  Use another solid as a pair of
scissors - no plane needed.

1. Move the cutter so it overlaps the thing to cut (a cylinder through a block,
   a sphere biting a corner ...).
2. Select the CUTTER (the scissors).
3. Press one of:
   - QUICK CUT: every other solid it overlaps has the overlap removed and is
     baked to a mesh.  The scissors vanish ("poof").
   - QUICK KEEP: every other solid it overlaps is trimmed down to ONLY the part
     inside the scissors (an intersection).

One undo step (Ctrl+Z) restores everything.  A solid the scissors swallow whole
is deleted by Quick cut.  Things that aren't closed solids (planes, lines) are
skipped.  Holes drilled this way keep their name, colours, group and layer, and
export to STL as real geometry.

Tip: for a persistent, editable version instead of a one-way bake, give the cutter a
CSG cut in the object's CSG settings.
""", None)

_topic("turtle", "Turtle - 3D LOGO programs", """
File menu -> "Run turtle script (.logo)...", or the command  turtle file.logo
A turtle walks in 3D and builds objects from a short text program.  Samples are
in the turtle_lib folder (mickey.logo, shapes.logo, gen_example.py).

  fd bk rt lt up down roll   move and turn (degrees; starts facing +X, up = +Z)
  pu pd  pensize r  color c  pen up/down, tube radius, colour
  cube box sphere cylinder cone      stamp a solid at the turtle
  beginfill ... endfill (fillthick t)   fill the path as a flat polygon / slab
  push pop        save / restore the turtle (position, heading, pen, colour)
  repeat n [..]  if e [..] else [..]  for i a b [..]  make x e  to name :a .. end
  part name :a .. endpart     a reusable assembly in its own local frame
  place name args as inst [mirror l|f|u] [scale s]
  group name .. endgroup   use file   (library: turtle_lib/file.logo)

Build an arm ONCE, then  place arm 12 as arm_l  and  place arm 12 as arm_r mirror l
for the other side.  Parts nest: arm and head inside torso.  Each placed part
becomes a group in the object tree (mickey/torso/head/ear_l) and each group/colour
becomes a mesh object, so colours, materials, move/rotate/scale, POV-Ray and STL
export all work on it normally.

A Python program can write the .logo text (fractals, equations, loops) - see
turtle_lib/gen_example.py.  Negative arguments: "goto 5 -3 0" is three numbers;
write 5-3 or 5 - 3 to subtract.  A part must be defined before it is placed.
""", None)

_topic("lights", "Lights - lamps in the scene (F5)", """
The Lights panel (F5, or the "Lights" button on the POV row) is where you add,
remove and shape the individual lamps.  Out of the box the scene uses an
automatic pair - a main "key" light and a soft "fill"; touch any control and
you take over that list (Reset default puts the pair back).

Per light you can set:

- Position (type X Y Z, or "At camera" to drop it where you're looking),
  Colour, and Brightness.
- Shadowless: a pure fill that adds light but casts no shadow.
- Soft shadows (area light): the lamp becomes a glowing panel, so shadows get
  a soft edge instead of a hard one.  Size = how big the panel is (softer when
  bigger); Samples = quality of the soft edge.
- Spotlight: a cone aimed at the camera target.  Hot radius is the full-bright
  centre, Falloff the outer dim edge (both in degrees), Tightness the sharpness.
- Distance fade: the lamp dims the further a surface is, past the set distance.

Quick toggles for every light are also in the Taichi menu under "Lights".
""", None)

_topic("taichi", "Taichi GPU preview", """
The Taichi preview (F10) is a fast GPU window, handy for big scenes.

- Orbit, pan and fly just like the main view.
- Click an object to select it; drag to move it; the menu has rotate/scale/snap.
- The collapsible menu has the same actions as the main window - Add, Transform,
  Group, Layers, Scripts, POV and Help.

Render a still from exactly where you're standing:
- Fly/orbit to the spot and angle you want, then press C (or the "Render snapshot
  from here" button at the top of the menu).  POV-Ray frames the render on the
  preview's live eye, aim and FOV - not the Camera Director's camera.
- It works mid-playback too: press C while the Director's path is playing and it
  freezes the path at that frame and renders that still.  (Plain Play/Stop is P.)

It runs as its own window and stays in step with the main scene.
""", _d_taichi)

_topic("scripts", "Scripts", """
Run a Python script that builds objects in the scene.

- Run script:  pick a .py file and run it.
- Replay:  run the same script again after you've edited it.
- Keep script objects:  turn the script's output into real, saved entries you can
  edit by hand.

Scripts are the way to build anything repetitive or math-driven.
""", _d_scripts)

_topic("keys", "Keyboard shortcuts", """
F1   / ?         this help (on whatever is selected)
F5   / Ctrl+L    Lights (lamps: soft shadows, spots, fade)
F6   / Ctrl+G    Lighting / global illumination (radiosity, photons, fog)
F7   / Ctrl+T    Lathe tool
F8   / Ctrl+D    Director (camera paths)
F9   / Ctrl+R    POV-Ray render
F10  / Ctrl+P    Taichi GPU preview

macOS reserves the F-row for the system, so use the Ctrl+ combos there
(or just click the buttons in the menu panel).

Every action also lives in the menu bar at the top of the window
(File / Edit / Scene / Object / Arrange / Camera / Tools / Render / Help) -
the surest way to reach anything on a Mac.  The fuller menus are split
into sub-sections so you don't have to scan one long list:
  Object  -> Textures / material,  Grouping,  Combine (CSG)
  Arrange -> Transform,  Copies
  Camera  -> View,  Director

Delete        remove the selection
Ctrl+Z / Y    undo / redo
Ctrl+A        select all
Esc           select none
double-click  Properties editor

In the 3D view:  left-drag orbit, right-drag pan, wheel zoom,
W A S D / R F fly, arrows turn, Shift to go faster.
In the Taichi preview:  C renders a POV-Ray still from exactly the view you're
in (freezes the Director path first if it's playing); P plays/stops that path.
""", None)

_topic("files", "Scene files & saving", """
The scene saves itself (autosave) after every change, and undo/redo work on
that same file - so you never lose edits.

You always work IN one file at a time, shown in the tree header: "Scene (name.csv)".

File menu:
  New scene        start a blank scene in a fresh timestamped file
                   (scene3d_YYYYMMDD-HHMMSS.csv) - your current file is left alone
  Open scene...    open a .csv and work in it from now on
  Save scene as... save to a name you pick AND switch to working in it

Because Save-as and Open switch the active file, autosave and undo follow the
file you chose - editing one scene can no longer overwrite another.

A first run with no saved scene starts in its own timestamped file instead of a
single shared default, so separate scenes (a chandelier, a tunnel, ...) stay
separate.  The app reopens whatever scene you last worked in.
""", None)

# index: (section label, [topic ids])
GROUPS = [
    ("Getting started", ["overview", "navigate", "tree", "keys", "files"]),
    ("Building", ["add", "scripts"]),
    ("Changing objects", ["transforms", "pivot", "replicate", "ring", "align"]),
    ("Combining", ["groups", "twin", "csg", "hollow"]),
    ("Looks", ["colors", "material", "layers"]),
    ("Camera & output", ["snapshots", "director", "pov", "lights", "lighting", "prism", "import", "export", "taichi"]),
]

# which topic to open for a selected object of a given kind (context help)
def kind_topic(kind):
    """The best starting topic for a selected object.  Everything per-object is
    one click away in the index, so we land them on the general editing page."""
    if not kind:
        return "overview"
    if kind in ("point3d", "line3d", "vector3d", "plane3d", "square3d", "circle3d"):
        return "add"
    return "transforms"

# --------------------------------------------------------------- window
class HelpWindow:
    def __init__(self, master, topic=None):
        self.top = tk.Toplevel(master)
        self.top.title("3D Viewer - Help")
        self.top.geometry("820x560")
        self.top.minsize(680, 460)
        pane = ttk.Panedwindow(self.top, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(pane, padding=(4, 4))
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.column("#0", width=210)
        pane.add(left, weight=0)

        right = ttk.Frame(pane, padding=(6, 6))
        _txt_title = ttk.Label(right, text="", font=("Segoe UI", 13, "bold"))
        _txt_title.pack(anchor="w")
        self.title_lbl = _txt_title
        self.canvas = tk.Canvas(right, width=CANVAS_W, height=CANVAS_H, bg=BG,
                                highlightthickness=1, highlightbackground="#ddd")
        self.canvas.pack(pady=(6, 6))
        tf = ttk.Frame(right)
        tf.pack(fill=tk.BOTH, expand=True)
        self.text = tk.Text(tf, wrap="word", font=("Segoe UI", 10), relief="flat",
                            bg=BG, padx=8, pady=6, height=8)
        sb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        pane.add(right, weight=1)

        self._iid = {}                 # topic id -> tree row id
        for label, ids in GROUPS:
            parent = self.tree.insert("", "end", text=label, open=True)
            for tid in ids:
                row = self.tree.insert(parent, "end", text="   " + TOPICS[tid]["title"])
                self._iid[row] = tid
        self.tree.bind("<<TreeviewSelect>>", self._on_pick)
        self.top.bind("<Escape>", lambda _e: self.top.destroy())
        self.top.bind("<F1>", lambda _e: None)
        self.show(topic or "overview")

    def _on_pick(self, _e=None):
        row = (self.tree.selection() or [""])[0]
        tid = self._iid.get(row)
        if tid:
            self._render(tid)

    def show(self, tid):
        """Select tid in the index and render it."""
        if tid not in TOPICS:
            tid = "overview"
        for row, t in self._iid.items():
            if t == tid:
                self.tree.selection_set(row)
                self.tree.see(row)
                break
        self._render(tid)

    def _render(self, tid):
        t = TOPICS[tid]
        self.current = tid
        self.title_lbl.config(text=t["title"])
        self.canvas.delete("all")
        if t["draw"]:
            try:
                t["draw"](self.canvas)
            except Exception as ex:          # a diagram must never break the page
                _txt(self.canvas, CANVAS_W / 2, CANVAS_H / 2, f"(diagram error: {ex})", color=MUTE)
        else:
            _txt(self.canvas, CANVAS_W / 2, CANVAS_H / 2,
                 "see the text below", color=MUTE, size=11)
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", t["body"])
        self.text.config(state="disabled")

    def lift_to(self, topic=None):
        if topic:
            self.show(topic)
        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()
