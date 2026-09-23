"""A small Tk camera director: edit plain data, preview it, save it for rendering.

The canvases are inexpensive wireframes, not a second ray tracer. Grid dragging
changes two coordinates; the XYZ entries also let you set the hidden coordinate.
"""

import copy
import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

import camera_path as cp


class CameraPathEditor(tk.Toplevel):
    def __init__(self, parent, include_path, on_use, shot=None, template_path=None):
        super().__init__(parent)
        self.title("Camera Director — paths, lights and wireframe preview")
        self.geometry("1250x820")
        self.minsize(950, 700)
        self.include_path = Path(include_path)
        self.on_use = on_use
        self.template_path = Path(template_path) if template_path else None
        self.shot = copy.deepcopy(shot or cp.default_shot())
        # A saved None means this shot generates its own scene. Do not reopen
        # that generated file as a background and add its lights a second time.
        if "pov_template" in self.shot:
            saved_template = self.shot["pov_template"]
            self.template_path = Path(saved_template) if saved_template else None
        self.move_index = 0
        self.light_index = 0 if self.shot["lights"] else None
        self.frames = cp.sample_shot(self.shot)
        self.frame_index = 0
        self.timer = None
        self.dragging = False
        self.scale = 20.0
        self.center = [0.0, 0.0, 0.0]
        self.vars = {}
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        controls = ttk.Notebook(self)
        controls.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        moves = ttk.Frame(controls, padding=8)
        objects = ttk.Frame(controls, padding=8)
        files = ttk.Frame(controls, padding=8)
        controls.add(moves, text="Camera moves")
        controls.add(objects, text="Object / lights")
        controls.add(files, text="Save / load")
        self._entry(moves, "name", "Shot name", self.shot["name"])
        self.move_list = tk.Listbox(moves, height=6, exportselection=False)
        self.move_list.pack(fill="x", pady=5)
        self.move_list.bind("<<ListboxSelect>>", self.select_move)
        buttons = ttk.Frame(moves)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Add move", command=self.add_move).pack(side="left")
        ttk.Button(buttons, text="Delete move", command=self.delete_move).pack(side="left")
        self._entry(moves, "kind", "Move type", "Arc", ["Line", "Arc"])
        for key, label in [
            ("a", "Start A (X,Y,Z)"), ("b", "Arc through B (X,Y,Z)"),
            ("c", "End (C for arc; B for line)"),
            ("target_a", "Aim at start (X,Y,Z)"), ("target_c", "Aim at end (X,Y,Z)"),
            ("steps", "Frame steps to end"), ("fov_a", "Start vertical FOV"),
            ("fov_c", "End vertical FOV"),
        ]:
            self._entry(moves, key, label, "")
        ttk.Button(moves, text="Apply move / rebuild preview", command=self.apply).pack(fill="x", pady=5)
        ttk.Button(moves, text="Aim this move at object", command=self.aim_at_object).pack(fill="x")
        ttk.Label(moves, text="Line uses Start → End. Arc passes through B halfway.\n"
                  "One initial frame + each move's steps. Shared endpoints appear once.\n"
                  "Changing an endpoint also joins its neighboring move.",
                  wraplength=345).pack(fill="x", pady=8)

        self._entry(objects, "object_kind", "Reference object", "Sphere", ["Sphere", "Box"])
        self._entry(objects, "object_position", "Object X,Y,Z", "")
        self._entry(objects, "object_size", "Radius / box half-size", "1")
        self._entry(objects, "object_color", "Object color", "#75baff")
        ttk.Button(objects, text="Pick object color", command=lambda: self.pick_color("object_color")).pack(fill="x")
        self._entry(objects, "ground_y", "Reference ground Y", str(self.shot.get("ground_y", 0)))
        self._entry(objects, "roll", "POV camera roll (degrees, all moves)", str(self.shot.get("roll", 0)))
        ttk.Label(objects, text="Preview only. Camera below this height is marked red.", wraplength=345).pack(fill="x", pady=4)
        ttk.Separator(objects).pack(fill="x", pady=12)
        ttk.Label(objects, text="Light sources").pack(anchor="w")
        self.light_list = tk.Listbox(objects, height=5, exportselection=False)
        self.light_list.pack(fill="x", pady=5)
        self.light_list.bind("<<ListboxSelect>>", self.select_light)
        light_buttons = ttk.Frame(objects)
        light_buttons.pack(fill="x")
        ttk.Button(light_buttons, text="Add light", command=self.add_light).pack(side="left")
        ttk.Button(light_buttons, text="Delete light", command=self.delete_light).pack(side="left")
        self._entry(objects, "light_position", "Light X,Y,Z", "")
        self._entry(objects, "light_color", "Light color", "#ffffff")
        self._entry(objects, "light_brightness", "Brightness (0 = off)", "1")
        ttk.Button(objects, text="Pick light color", command=lambda: self.pick_color("light_color")).pack(fill="x")
        ttk.Button(objects, text="Apply object / light", command=self.apply).pack(fill="x", pady=8)
        ttk.Label(objects, text="Full colored lighting and the reference object export to POV-Ray.\n"
                  "The book renderer keeps its book objects and supports only two white lights (0–1).",
                  wraplength=345).pack(fill="x", pady=8)

        self.preset_var = tk.StringVar()
        ttk.Label(files, text="Shots saved in rayincludes.py").pack(anchor="w")
        self.preset_box = ttk.Combobox(files, textvariable=self.preset_var, state="readonly")
        self.preset_box.pack(fill="x", pady=6)
        self.use_existing = tk.BooleanVar(value=bool(self.template_path))
        self.include_object = tk.BooleanVar(value=self.shot.get("include_object", False))
        ttk.Checkbutton(files, text="Use an existing POV scene", variable=self.use_existing).pack(anchor="w")
        self.template_label = ttk.Label(files, text=str(self.template_path or "No background scene selected"), wraplength=345)
        self.template_label.pack(fill="x", pady=4)
        ttk.Button(files, text="Choose existing POV scene…", command=self.choose_template).pack(fill="x")
        ttk.Button(files, text="Start path at scene's camera / aim", command=self.import_camera).pack(fill="x", pady=3)
        ttk.Checkbutton(files, text="Also render reference object in existing scene", variable=self.include_object).pack(anchor="w", pady=5)
        for label, command in [
            ("Load selected saved shot", self.load_preset),
            ("Save shot to rayincludes.py", self.save_preset),
            ("Open project JSON…", self.open_project),
            ("Save project JSON…", self.save_project),
            ("Export POV scene + frame list…", self.export_scene),
            ("Use this path with book renderer", lambda: self.use_path(False)),
            ("Use complete scene with POV-Ray", lambda: self.use_path(True)),
        ]:
            ttk.Button(files, text=label, command=command).pack(fill="x", pady=4)
        ttk.Label(files, text="Save keeps editable shot data in a marked section of rayincludes.py.\n"
                  "Existing scenes are preserved; a .director.bak file keeps the previous version.\n\n"
                  "Use prepares the main window. Start its Homemade strip or POV-Ray strip when ready.\n"
                  "Director paths use these exact frame steps, not the main Movie Frames override.\n\n"
                  "Wireframe shows the reference object, lights and grid only; it does not parse book scenes or arbitrary POV files.",
                  wraplength=345).pack(fill="x", pady=12)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)
        toolbar = ttk.Frame(right)
        toolbar.grid(row=0, column=0, sticky="ew")
        self.plane = tk.StringVar(value="Top XZ")
        plane_box = ttk.Combobox(toolbar, textvariable=self.plane,
                                values=["Top XZ", "Front XY", "Side ZY"], state="readonly", width=12)
        plane_box.pack(side="left")
        plane_box.bind("<<ComboboxSelected>>", lambda event: self.draw())
        self.place = tk.StringVar(value="Start A")
        ttk.Combobox(toolbar, textvariable=self.place, state="readonly", width=15,
                     values=["Start A", "Through B", "End", "Aim start", "Aim end", "Object", "Light"]).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Fit", command=self.fit).pack(side="left")
        ttk.Label(toolbar, text="Click to place / drag a marker. Wheel = zoom.").pack(side="left", padx=6)
        self.map_canvas = tk.Canvas(right, background="#141b27", highlightthickness=0)
        self.map_canvas.grid(row=1, column=0, sticky="nsew", pady=6)
        self.map_canvas.bind("<Button-1>", self.press)
        self.map_canvas.bind("<B1-Motion>", self.drag)
        self.map_canvas.bind("<ButtonRelease-1>", lambda event: setattr(self, "dragging", False))
        self.map_canvas.bind("<MouseWheel>", self.zoom)
        self.map_canvas.bind("<Configure>", lambda event: self.draw())
        ttk.Label(right, text="Through the camera — wireframe (same aim and vertical FOV as export)").grid(row=2, column=0, sticky="w")
        self.camera_canvas = tk.Canvas(right, background="#0c111b", highlightthickness=0)
        self.camera_canvas.grid(row=3, column=0, sticky="nsew", pady=6)
        self.camera_canvas.bind("<Configure>", lambda event: self.draw())
        playback = ttk.Frame(right)
        playback.grid(row=4, column=0, sticky="ew")
        ttk.Button(playback, text="Play", command=self.play).pack(side="left")
        ttk.Button(playback, text="Stop", command=self.stop).pack(side="left")
        self.fps = tk.StringVar(value=str(self.shot["fps"]))
        ttk.Label(playback, text="FPS").pack(side="left", padx=(8, 3))
        ttk.Spinbox(playback, from_=1, to=120, textvariable=self.fps, width=5).pack(side="left")
        self.frame_var = tk.DoubleVar(value=0)
        self.scrub = ttk.Scale(playback, from_=0, to=len(self.frames)-1,
                               variable=self.frame_var, command=self.on_scrub)
        self.scrub.pack(side="left", fill="x", expand=True, padx=8)
        self.frame_label = ttk.Label(playback)
        self.frame_label.pack(side="left")
        self.status = tk.StringVar(value="Choose a marker and click a grid. Change views to edit the third coordinate.")
        ttk.Label(self, textvariable=self.status, wraplength=1150).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh_lists()
        self.load_fields()
        self.refresh_presets()
        self.after_idle(self.fit)

    def _entry(self, parent, name, label, value, choices=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=25).pack(side="left")
        var = self.vars[name] = tk.StringVar(value=value)
        widget = (ttk.Combobox(row, textvariable=var, values=choices, state="readonly", width=18)
                  if choices else ttk.Entry(row, textvariable=var, width=20))
        widget.pack(side="left", fill="x", expand=True)
        widget.bind("<Return>", lambda event: self.apply())

    def refresh_lists(self):
        self.move_list.delete(0, "end")
        for i, move in enumerate(self.shot["segments"]):
            self.move_list.insert("end", f"{i+1}. {move['kind']} — {move['steps']} steps")
        self.move_list.selection_set(self.move_index)
        self.light_list.delete(0, "end")
        for i, light in enumerate(self.shot["lights"]):
            self.light_list.insert("end", f"{i+1}. {light['color']} — {light['brightness']:g}")
        if self.light_index is not None:
            self.light_list.selection_set(self.light_index)

    def load_fields(self):
        self.vars["ground_y"].set(str(self.shot.get("ground_y", 0)))
        self.vars["roll"].set(str(self.shot.get("roll", 0)))
        move = self.shot["segments"][self.move_index]
        for key, value in move.items():
            self.vars[key].set(cp.point_text(value) if isinstance(value, (tuple, list)) else str(value))
        for key, value in self.shot["object"].items():
            self.vars["object_"+key].set(cp.point_text(value) if isinstance(value, (tuple, list)) else str(value))
        light = self.shot["lights"][self.light_index] if self.light_index is not None else {
            "position": [0, 5, 0], "color": "#ffffff", "brightness": 1}
        for key, value in light.items():
            self.vars["light_"+key].set(cp.point_text(value) if isinstance(value, (tuple, list)) else str(value))

    def collect(self):
        """Parse into a copy first, so a half-typed value cannot corrupt a shot."""
        shot = copy.deepcopy(self.shot)
        def point(key):
            result = [float(x.strip()) for x in self.vars[key].get().split(",")]
            cp.check_vector(result, key)
            return result
        move = shot["segments"][self.move_index]
        for key in ("a", "b", "c", "target_a", "target_c"):
            move[key] = point(key)
        for key in ("fov_a", "fov_c"):
            move[key] = float(self.vars[key].get())
        move["steps"] = int(self.vars["steps"].get())
        move["kind"] = self.vars["kind"].get()
        # Joined endpoints share their pose. This avoids a teleport between moves.
        if self.move_index:
            previous = shot["segments"][self.move_index-1]
            previous.update(c=move["a"][:], target_c=move["target_a"][:], fov_c=move["fov_a"])
        if self.move_index+1 < len(shot["segments"]):
            following = shot["segments"][self.move_index+1]
            following.update(a=move["c"][:], target_a=move["target_c"][:], fov_a=move["fov_c"])
        shot["name"] = self.vars["name"].get().strip()
        shot["pov_template"] = str(self.template_path) if self.use_existing.get() and self.template_path else None
        shot["include_object"] = self.include_object.get()
        shot["fps"] = int(self.fps.get())
        shot["ground_y"] = float(self.vars["ground_y"].get())
        shot["roll"] = float(self.vars["roll"].get())
        shot["object"] = {"kind": self.vars["object_kind"].get(), "position": point("object_position"),
                          "size": float(self.vars["object_size"].get()), "color": self.vars["object_color"].get()}
        if self.light_index is not None:
            shot["lights"][self.light_index] = {"position": point("light_position"),
                "color": self.vars["light_color"].get(), "brightness": float(self.vars["light_brightness"].get())}
        return shot

    def apply(self):
        self.stop()
        try:
            shot = self.collect()
            frames = cp.sample_shot(shot)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self.status.set(f"Check settings: {exc}")
            return False
        self.shot, self.frames = shot, frames
        self.frame_index = min(self.frame_index, len(frames)-1)
        self.scrub.configure(to=len(frames)-1)
        self.refresh_lists()
        self.draw()
        self.status.set(f"{len(frames)} frames · {len(frames)/shot['fps']:.2f} seconds at {shot['fps']} FPS. Settings applied.")
        below = [i+1 for i, pose in enumerate(frames) if pose["camera"][1] < shot.get("ground_y", 0)]
        if below:
            self.status.set(f"{len(frames)} frames. Camera is below reference ground Y={shot['ground_y']:g} in {len(below)} frames (first: {below[0]}). Red path shows those sections.")
        return True

    def select_move(self, event=None):
        selected = self.move_list.curselection()
        if selected and selected[0] != self.move_index:
            index = selected[0]
            if self.apply():
                self.move_index = index
                self.refresh_lists()
                self.load_fields()
                self.draw()

    def select_light(self, event=None):
        selected = self.light_list.curselection()
        if selected and selected[0] != self.light_index:
            index = selected[0]
            if self.apply():
                self.light_index = index
                self.refresh_lists()
                self.load_fields()
                self.draw()

    def add_move(self):
        if not self.apply():
            return
        last = self.shot["segments"][-1]
        a = list(last["c"])
        c = list(cp.add(a, (5, 0, 0)))
        self.shot["segments"].append({"kind": "Line", "a": a, "b": list(cp.mix(a, c, .5)), "c": c,
            "target_a": last["target_c"][:], "target_c": last["target_c"][:],
            "steps": 24, "fov_a": last["fov_c"], "fov_c": last["fov_c"]})
        self.move_index = len(self.shot["segments"])-1
        self.load_fields()
        self.apply()

    def delete_move(self):
        if len(self.shot["segments"]) == 1:
            self.status.set("Keep at least one camera move.")
            return
        if not self.apply():
            return
        del self.shot["segments"][self.move_index]
        self.move_index = min(self.move_index, len(self.shot["segments"])-1)
        for previous, following in zip(self.shot["segments"], self.shot["segments"][1:]):
            following.update(a=previous["c"][:], target_a=previous["target_c"][:], fov_a=previous["fov_c"])
        self.load_fields()
        self.apply()

    def add_light(self):
        if self.apply():
            self.shot["lights"].append({"position": [0, 6, -4], "color": "#ffffff", "brightness": 1})
            self.light_index = len(self.shot["lights"])-1
            self.load_fields()
            self.apply()

    def delete_light(self):
        if self.light_index is not None and self.apply():
            del self.shot["lights"][self.light_index]
            self.light_index = 0 if self.shot["lights"] else None
            self.load_fields()
            self.apply()

    def pick_color(self, key):
        chosen = colorchooser.askcolor(self.vars[key].get(), parent=self)[1]
        if chosen:
            self.vars[key].set(chosen)
            self.apply()

    def aim_at_object(self):
        self.vars["target_a"].set(self.vars["object_position"].get())
        self.vars["target_c"].set(self.vars["object_position"].get())
        self.apply()

    def axes(self):
        return {"Top XZ": (0, 2), "Front XY": (0, 1), "Side ZY": (2, 1)}[self.plane.get()]

    def map_point(self, point):
        i, j = self.axes()
        return (self.map_canvas.winfo_width()/2 + (point[i]-self.center[i])*self.scale,
                self.map_canvas.winfo_height()/2 - (point[j]-self.center[j])*self.scale)

    def handles(self):
        move = self.shot["segments"][self.move_index]
        handles = {"Start A": move["a"], "End": move["c"], "Aim start": move["target_a"],
                   "Aim end": move["target_c"], "Object": self.shot["object"]["position"]}
        if move["kind"] == "Arc":
            handles["Through B"] = move["b"]
        if self.light_index is not None:
            handles["Light"] = self.shot["lights"][self.light_index]["position"]
        return handles

    def press(self, event):
        if not self.apply():
            return
        for name, position in self.handles().items():
            x, y = self.map_point(position)
            if (x-event.x)**2+(y-event.y)**2 < 100:
                self.place.set(name)
                break
        self.dragging = True
        self.drag(event)

    def drag(self, event):
        if not self.dragging or self.place.get() not in self.handles():
            return
        value = list(self.handles()[self.place.get()])
        i, j = self.axes()
        value[i] = self.center[i] + (event.x-self.map_canvas.winfo_width()/2)/self.scale
        value[j] = self.center[j] - (event.y-self.map_canvas.winfo_height()/2)/self.scale
        key = {"Start A": "a", "Through B": "b", "End": "c", "Aim start": "target_a",
               "Aim end": "target_c", "Object": "object_position", "Light": "light_position"}[self.place.get()]
        self.vars[key].set(cp.point_text(value))
        self.apply()

    def zoom(self, event):
        self.scale = min(1000, max(.01, self.scale*(1.15 if event.delta > 0 else 1/1.15)))
        self.draw()

    def fit(self):
        points = [pose["camera"] for pose in self.frames] + list(self.handles().values())
        lower = [min(p[i] for p in points)-2 for i in range(3)]
        upper = [max(p[i] for p in points)+2 for i in range(3)]
        self.center = list(cp.mix(lower, upper, .5))
        i, j = self.axes()
        self.scale = min(max(100, self.map_canvas.winfo_width())/(upper[i]-lower[i]),
                         max(100, self.map_canvas.winfo_height())/(upper[j]-lower[j]))*.85
        self.draw()

    def wire_edges(self):
        """A reference object, light markers, and origin axes in world coordinates."""
        obj = self.shot["object"]
        center, size, color = obj["position"], obj["size"], obj["color"]
        edges = []
        if obj["kind"] == "Sphere":
            for a, b in [(0, 1), (0, 2), (1, 2)]:
                ring = []
                for k in range(33):
                    point = list(center)
                    point[a] += size*math.cos(k*math.tau/32)
                    point[b] += size*math.sin(k*math.tau/32)
                    ring.append(point)
                edges += [(p, q, color) for p, q in zip(ring, ring[1:])]
        else:
            corners = [cp.add(center, (x*size, y*size, z*size)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
            for k in range(8):
                for bit in (1, 2, 4):
                    if k < (k ^ bit):
                        edges.append((corners[k], corners[k ^ bit], color))
        for light in self.shot["lights"]:
            for axis in range(3):
                delta = [0, 0, 0]
                delta[axis] = size*.15
                edges.append((cp.sub(light["position"], delta), cp.add(light["position"], delta), light["color"]))
        for axis, color in enumerate(["#e97474", "#78d693", "#7ba9f4"]):
            end = [0, 0, 0]
            end[axis] = max(2, size*2)
            edges.append(((0, 0, 0), end, color))
        # This grid is only an orientation aid, not exported scene geometry.
        extent = max(10, size*5, abs(center[0])+size*2, abs(center[2])+size*2)
        ground = self.shot.get("ground_y", 0)
        for k in range(-5, 6):
            value = k*extent/5
            edges.append(((-extent, ground, value), (extent, ground, value), "#28364b"))
            edges.append(((value, ground, -extent), (value, ground, extent), "#28364b"))
        return edges

    def draw(self):
        if not hasattr(self, "camera_canvas") or not self.frames:
            return
        canvas = self.map_canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        i, j = self.axes()
        spacing = 10**math.ceil(math.log10(max(1e-6, 30/self.scale)))
        for axis, extent in [(i, w), (j, h)]:
            lo = self.center[axis]-extent/(2*self.scale)
            hi = self.center[axis]+extent/(2*self.scale)
            for k in range(math.floor(lo/spacing), math.ceil(hi/spacing)+1):
                p = list(self.center)
                p[axis] = k*spacing
                x, y = self.map_point(p)
                coords = (x, 0, x, h) if axis == i else (0, y, w, y)
                canvas.create_line(*coords, fill="#38465a" if k == 0 else "#253043")
                canvas.create_text(x+3 if axis == i else 3, 12 if axis == i else y-3,
                                   text=f"{k*spacing:g}", anchor="w", fill="#7f91a8")
        for p, q, color in self.wire_edges():
            canvas.create_line(*self.map_point(p), *self.map_point(q), fill=color)
        points = [self.map_point(frame["camera"]) for frame in self.frames]
        if len(points) > 1:
            canvas.create_line(*[n for point in points for n in point], fill="#6fbdff", width=2)
            for k in range(1, len(points)):
                if min(self.frames[k-1]["camera"][1], self.frames[k]["camera"][1]) < self.shot.get("ground_y", 0):
                    canvas.create_line(*points[k-1], *points[k], fill="#ff6262", width=3)
        for name, position in self.handles().items():
            x, y = self.map_point(position)
            color = "#ffd26f" if name == self.place.get() else "#edf3ff"
            canvas.create_oval(x-4, y-4, x+4, y+4, fill=color)
            canvas.create_text(x+8, y+8, text=name, anchor="nw", fill=color)
        pose = self.frames[self.frame_index]
        x, y = self.map_point(pose["camera"])
        tx, ty = self.map_point(pose["lookat"])
        canvas.create_line(x, y, tx, ty, fill="#ff9e6e", arrow="last", dash=(4, 3))
        canvas.create_rectangle(x-5, y-5, x+5, y+5, outline="#ff9e6e", width=2)
        canvas.create_text(w-8, h-8, text=f"{'XYZ'[i]} horizontal / {'XYZ'[j]} vertical · grid {spacing:g}", anchor="se", fill="#c5d0e0")
        self.draw_camera(pose)
        self.frame_label.configure(text=f"{self.frame_index+1} / {len(self.frames)}")

    def draw_camera(self, pose):
        canvas = self.camera_canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        right, up, forward = cp.camera_basis(pose["camera"], pose["lookat"], self.shot.get("roll", 0))
        focal = h/(2*math.tan(math.radians(pose["vfov"])/2))
        def local(point):
            offset = cp.sub(point, pose["camera"])
            return (cp.dot(offset, right), cp.dot(offset, up), cp.dot(offset, forward))
        def project(point):
            return (w/2+point[0]*focal/point[2], h/2-point[1]*focal/point[2])
        for a, b, color in self.wire_edges():
            a, b = local(a), local(b)
            near = .01
            if a[2] < near and b[2] < near:
                continue
            # Clip segments crossing the camera, instead of drawing behind it.
            if a[2] < near:
                a = cp.mix(a, b, (near-a[2])/(b[2]-a[2]))
            elif b[2] < near:
                b = cp.mix(b, a, (near-b[2])/(a[2]-b[2]))
            canvas.create_line(*project(a), *project(b), fill=color, width=2)
        canvas.create_line(w/2-5, h/2, w/2+5, h/2, fill="#61748c")
        canvas.create_line(w/2, h/2-5, w/2, h/2+5, fill="#61748c")
        canvas.create_text(8, h-8, text=f"Camera {cp.point_text(pose['camera'])}  |  aim {cp.point_text(pose['lookat'])}  |  FOV {pose['vfov']:.1f}°", anchor="sw", fill="#c5d0e0")

    def on_scrub(self, value):
        self.frame_index = max(0, min(len(self.frames)-1, round(float(value))))
        self.draw()

    def play(self):
        if self.apply():
            if self.frame_index == len(self.frames)-1:
                self.frame_index = 0
            self.tick()

    def tick(self):
        self.timer = None
        self.frame_var.set(self.frame_index)
        self.draw()
        if self.frame_index < len(self.frames)-1:
            self.frame_index += 1
            self.timer = self.after(round(1000/self.shot["fps"]), self.tick)

    def stop(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None

    def close(self):
        self.stop()
        self.destroy()

    def refresh_presets(self):
        try:
            self.preset_box.configure(values=list(cp.load_presets(self.include_path)))
        except (OSError, ValueError, SyntaxError) as exc:
            self.status.set(f"Could not read saved shots: {exc}")

    def replace_shot(self, shot):
        frames = cp.sample_shot(shot)
        self.stop()
        self.shot, self.frames = copy.deepcopy(shot), frames
        self.move_index = self.frame_index = 0
        self.light_index = 0 if shot["lights"] else None
        self.vars["name"].set(shot["name"])
        self.template_path = Path(shot["pov_template"]) if shot.get("pov_template") else None
        self.use_existing.set(bool(self.template_path))
        self.include_object.set(shot.get("include_object", False))
        self.template_label.configure(text=str(self.template_path or "No background scene selected"))
        self.fps.set(str(shot["fps"]))
        self.load_fields()
        self.apply()
        self.fit()

    def load_preset(self):
        try:
            self.replace_shot(cp.load_presets(self.include_path)[self.preset_var.get()])
        except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
            messagebox.showerror("Load shot", str(exc), parent=self)

    def save_preset(self):
        if not self.apply():
            return
        try:
            presets = cp.load_presets(self.include_path)
            if self.shot["name"] in presets and not messagebox.askyesno(
                "Replace saved shot?", f"Replace the saved shot '{self.shot['name']}'?", parent=self):
                return
            cp.save_preset(self.include_path, self.shot)
            self.refresh_presets()
            self.preset_var.set(self.shot["name"])
            self.status.set(f"Saved to {self.include_path}. Previous include saved as .director.bak.")
        except (OSError, ValueError, SyntaxError) as exc:
            messagebox.showerror("Save shot", str(exc), parent=self)

    def open_project(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Camera project", "*.json")])
        if path:
            try:
                self.replace_shot(cp.load_project(path))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                messagebox.showerror("Open project", str(exc), parent=self)

    def save_project(self):
        if not self.apply():
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Camera project", "*.json")])
        if path:
            try:
                cp.save_project(path, self.shot)
                self.status.set(f"Project saved: {path}")
            except OSError as exc:
                messagebox.showerror("Save project", str(exc), parent=self)

    def export_scene(self):
        if not self.apply():
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".pov", filetypes=[("POV-Ray scene", "*.pov")])
        if path:
            try:
                path = Path(path)
                frames_path = path.with_suffix(".frames.json")
                project_path = path.with_suffix(".project.json")
                ini_path = path.with_suffix(".ini")
                existing = [p for p in (frames_path, project_path, ini_path) if p.exists()]
                if existing and not messagebox.askyesno("Replace export companions?", "\n".join(str(p) for p in existing), parent=self):
                    return
                if self.use_existing.get():
                    if self.template_path is None:
                        raise ValueError("Choose an existing POV scene first.")
                    if path.resolve() == self.template_path.resolve():
                        raise ValueError("Export to a new file to preserve your original POV scene.")
                    # Relative include/texture paths remain valid beside the source.
                    if path.parent.resolve() != self.template_path.parent.resolve():
                        raise ValueError("Export beside the original POV file so relative includes and textures still resolve.")
                    text = cp.pov_animation_text(self.shot, self.template_path.read_text(encoding="utf-8"), self.include_object.get())
                else:
                    text = cp.pov_animation_text(self.shot)
                path.write_text(text, encoding="utf-8")
                frames_path.write_text(json.dumps(cp.renderer_frames(self.shot), indent=2)+"\n", encoding="utf-8")
                cp.save_project(project_path, self.shot)
                ini_path.write_text(
                    f'Input_File_Name="{path.name}"\nOutput_File_Name="{path.stem}_frame.png"\n'
                    f"Initial_Frame=1\nFinal_Frame={len(self.frames)}\nInitial_Clock=0\nFinal_Clock=1\n"
                    "Width=600\nHeight=600\nDisplay=Off\nOutput_File_Type=N\n", encoding="utf-8")
                self.status.set(f"Exported {path.name}, {ini_path.name}, frames and editable project. Run POV-Ray with the INI in this folder.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Export scene", str(exc), parent=self)

    def use_path(self, complete_scene):
        if self.apply():
            try:
                template = self.template_path if complete_scene and self.use_existing.get() else None
                if complete_scene and self.use_existing.get() and template is None:
                    raise ValueError("Choose an existing POV scene first.")
                self.on_use(copy.deepcopy(self.shot), complete_scene, template, self.include_object.get())
                self.status.set("Prepared the main window. Start its POV-Ray strip." if complete_scene else
                                "Prepared the main window. Start its Homemade strip; book objects / white lights apply.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Use camera path", str(exc), parent=self)

    def choose_template(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("POV-Ray scene", "*.pov")])
        if path:
            self.template_path = Path(path)
            self.use_existing.set(True)
            self.template_label.configure(text=str(self.template_path))

    def import_camera(self):
        """Move the whole path into the existing scene's coordinate neighborhood."""
        if not self.apply():
            return
        try:
            if self.template_path is None:
                raise ValueError("Choose an existing POV scene first.")
            pose = cp.read_pov_camera(self.template_path.read_text(encoding="utf-8"))
            shot = copy.deepcopy(self.shot)
            first = shot["segments"][0]
            offset = cp.sub(pose["location"], first["a"])
            target_offset = cp.sub(pose["look_at"], first["target_a"])
            for segment in shot["segments"]:
                for key in ("a", "b", "c"):
                    segment[key] = list(cp.add(segment[key], offset))
                for key in ("target_a", "target_c"):
                    segment[key] = list(cp.add(segment[key], target_offset))
            shot["object"]["position"] = pose["look_at"][:]
            for light in shot["lights"]:
                light["position"] = list(cp.add(light["position"], target_offset))
            self.replace_shot(shot)
            self.status.set("Path moved to the scene camera. Reference object marks its look_at point. Check reference ground Y for this scene; FOV is unchanged.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Import scene camera", str(exc), parent=self)
