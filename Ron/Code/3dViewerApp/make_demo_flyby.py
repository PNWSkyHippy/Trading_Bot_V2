"""Builds demo_flyby.csv (+ demo_flyby.director.json): a spinning globe at the end of a road, a car driving
up the road towards it, and a camera that closes in on the globe while circling clockwise.

    python make_demo_flyby.py          then open demo_flyby.csv in the viewer and press the Director's play.
"""
import math
import os
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from commands3d import Session   # noqa: E402

SCIFI = "--scifi" in sys.argv     # cloud-free: a round deck instead of the big field, so the panorama's floor dome shows round it
SCENE = os.path.join(HERE, "demo_scifi.csv" if SCIFI else "demo_flyby.csv")
SPH = (0.0, 14.0, 5.0)           # globe centre; radius 5, sitting on the ground
R = 5.0
SECONDS, FPS = 10, 30
CAR_Y0, CAR_Y1 = -80.0, -12.0

lines = ["new"]
add = lines.append

# ground (so cloud shadows have somewhere to land) + road + dashes + roadside posts (the posts and dashes are what makes the motion read)
if SCIFI:
    add("add cylinder 90 0.2 at 0,-40,-0.1 color #20283a name ground")
else:
    add("add box 900 900 0.2 at 0,0,-0.1 color #5d8a45 name ground")
add("add box 9 150 0.1 at 0,-60,0.05 color #3a3d44 name road")
for i in range(14):
    add(f"add box 0.3 4 0.12 at 0,{-125 + i * 10},0.12 color #f2f2f2 name dash{i}")
for i in range(10):
    for sx in (-8, 8):
        add(f"add box 0.5 0.5 {3 + (i % 3)} at {sx},{-120 + i * 14},{(3 + i % 3) / 2} color #8a6a3c name post{i}{'L' if sx < 0 else 'R'}")

# globe + 'continents' (small blocks pinned to its surface so the spin is visible)
add(f"add sphere {R} at {SPH[0]},{SPH[1]},{SPH[2]} color #2f6fd6 name globe")
marks = [(30, 20, "#38b24a"), (130, -10, "#38b24a"), (230, 35, "#e0b030"), (300, -30, "#e0e0e0"),
         (80, 60, "#e0e0e0"), (190, -55, "#c04030")]
for k, (lon, lat, col) in enumerate(marks):
    lo, la = math.radians(lon), math.radians(lat)
    x = SPH[0] + (R + 0.15) * math.cos(la) * math.cos(lo)
    y = SPH[1] + (R + 0.15) * math.cos(la) * math.sin(lo)
    z = SPH[2] + (R + 0.15) * math.sin(la)
    add(f"add box 1.6 1.6 1.6 at {x:.3f},{y:.3f},{z:.3f} color {col} name land{k}")

# car: body, cabin, four wheels (axles along x), nose towards +y
add(f"add box 3 7 1.2 at 0,{CAR_Y0},1.1 color #d62f2f name car_body")
add(f"add box 2.6 3.4 1 at 0,{CAR_Y0 - 0.4},2.2 color #9fc4e8 name car_cabin")
for n, (wx, wy) in {"fl": (-1.6, 2.2), "fr": (1.6, 2.2), "bl": (-1.6, -2.2), "br": (1.6, -2.2)}.items():
    add(f"add cylinder 0.7 0.5 at {wx},{CAR_Y0 + wy},0.7 color #1a1a1a name wheel_{n}")
    add(f"rotate wheel_{n} 90 on y")

import re   # noqa: E402

colors = {}                                       # '#' starts a comment in a command line: set colours afterwards
for i, ln in enumerate(lines):
    m = re.search(r" color (#[0-9a-fA-F]{6}) name (\S+)", ln)
    if m:
        colors[m.group(2)] = m.group(1)
        lines[i] = ln.replace(f" color {m.group(1)}", "")
sess = Session()
report = sess.run("\n".join(lines))
for nm, col in colors.items():
    sess.color(nm, col, col)                          # fill too: boxes with no fill are only wire edges in the previews
open(os.path.join(os.environ["TEMP"], "demo_report.txt"), "w").write(str(report))
sess.run(f"save {SCENE}")

# ---- the shot ---------------------------------------------------------------
import viewer3d      # noqa: E402
import director3d as d   # noqa: E402

root = tk.Tk()
app = viewer3d.App(root)
app.entries = viewer3d.load_scene(SCENE)           # not open_scene_file: that would switch the user's active scene
for e in app.entries:
    app.rebuild(e)
if not any(e.name == "globe" for e in app.entries):
    raise SystemExit("scene did not load into the viewer")

d.Director.autosave = lambda self: None            # leave the user's last shot alone
dr = d.Director(app)


def on_circle(r, deg, z):
    a = math.radians(deg)
    return [SPH[0] + r * math.cos(a), SPH[1] + r * math.sin(a), z]


tgt = list(SPH)
# camera: clockwise from above = decreasing angle; starts off to the south-west, ends close in
legs = [(268, 228, 120, 64, 10, 10), (228, 130, 64, 22, 10, 6)]
segs = []
for a0, a1, r0, r1, z0, z1 in legs:
    am, rm, zm = (a0 + a1) / 2, (r0 + r1) / 2, (z0 + z1) / 2
    start = segs[-1]["c"] if segs else on_circle(r0, a0, z0)      # each move starts exactly where the last ended
    segs.append({"kind": "Arc", "a": list(start), "b": on_circle(rm, am, zm), "c": on_circle(r1, a1, z1),
                 "target_a": tgt, "target_c": tgt, "steps": SECONDS * FPS // 2 - 1, "fov_a": 50 if not segs else 42, "fov_c": 42})
shot = {"name": "demo_flyby", "segments": segs,
        "object": {"kind": "Sphere", "position": tgt, "size": 1, "color": "#75baff"}, "lights": [], "fps": FPS, "ground_y": 0, "roll": 0}

spin = d.blank_key(0.0)
spin_end = {**d.blank_key(SECONDS), "rot": [0.0, 0.0, 360.0]}          # + z = counter-clockwise from above
drive = {**d.blank_key(SECONDS), "move": [0.0, CAR_Y1 - CAR_Y0, 0.0]}
tracks, pivots = {}, {}
tracks["globe"] = [spin, spin_end]
for k in range(len(marks)):
    tracks[f"land{k}"] = [d.blank_key(0.0), dict(spin_end)]
    pivots[f"land{k}"] = "globe"
for n in ("car_body", "car_cabin", "wheel_fl", "wheel_fr", "wheel_bl", "wheel_br"):
    key = dict(drive)
    if n.startswith("wheel"):                                               # rolling: circumference 2*pi*0.7
        key["rot"] = [-math.degrees((CAR_Y1 - CAR_Y0) / 0.7), 0.0, 0.0]
    tracks[n] = [d.blank_key(0.0), key]
shot["tracks"], shot["pivots"] = tracks, pivots
import pov_export   # noqa: E402
clouds = pov_export.default_clouds()
clouds["sun"].update(az=120.0, el=38.0)
clouds["layers"] = [   # demo scale: scene units are metres, so these are low "toy" layers over the road
    {"name": "Stratus", "alt": 60, "heading": 270, "speed": 7, "coverage": 0.55, "soft": 0.25, "density": 0.75,
     "size": 40, "visible": True, "color": "#f2f4f7", "seed": 1},
    {"name": "High cloud", "alt": 120, "heading": 0, "speed": 11, "coverage": 0.45, "soft": 0.2, "density": 0.6,
     "size": 70, "visible": False, "color": "#f6f7f9", "seed": 2}]
if SCIFI:
    clouds["layers"] = []                       # no clouds, so no moving shadows
    clouds["sun"].update(az=200.0, el=65.0, color="#cfe6ff", brightness=0.9)
shot["clouds"] = clouds

dr.shot = shot
dr.resample()
SIDE = os.path.splitext(SCENE)[0] + ".director.json"
dr.save_scene_sidecar(SIDE)
open(os.path.join(os.environ["TEMP"], "demo_out.txt"), "w").write(f"frames {len(dr.frames)}")
print("frames", len(dr.frames), "sidecar", SIDE)
root.destroy()
