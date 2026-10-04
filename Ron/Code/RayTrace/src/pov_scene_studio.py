"""POV-Ray Scene Studio & Visual Builder for tkray_tracer.

Mimics the POV-Ray 3.7 Windows GUI front-end and scene editor:
- Load, edit, and save .pov and .inc scene files directly in Ron\\Code\\RayTrace\\src
- Visual Scene Explorer / Parser: Inspect cameras, lights, primitives, textures, and finishes
- Interactive Object Inspector: Move (X, Y, Z), resize, and color selected objects with live radar update
- Smart Object Placement: Automatically offsets newly added objects so they don't spawn on top of each other
- Detailed Error Feedback: Displays exact POV-Ray parser errors & line numbers instead of failing silently
- Fast Live Ray-Traced Preview: One-click render at configurable draft/production resolutions
- Spatial Top-Down Radar / Wireframe View: Visualizes camera, lights, and object placements
- Reset to Working Default Scene: Instant 1-click recovery from corrupted/broken scenes
- Seamless integration with tkray_tracer to set active scene for movie generation.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageTk

IS_WINDOWS = os.name == "nt"
LOCAL_SRC_DIR = Path(r"C:\Users\Linda\Trading_Bot_V2\Ron\Code\RayTrace\src").resolve()


def _windows_to_wsl_path(path: Path | str) -> str:
    p = Path(path).resolve()
    drive = p.drive.rstrip(":").lower()
    parts = list(p.parts[1:])
    return "/mnt/" + drive + "/" + "/".join(parts)


def run_povray_preview(
    scene_text: str,
    width: int = 320,
    height: int = 240,
    working_dir: Optional[Path] = None,
) -> Tuple[Optional[Image.Image], str]:
    """Renders a fast draft preview frame of the scene using POV-Ray.

    Returns:
        (image_or_none, error_message_or_log)
    """
    # Always use a reliable local directory for temp rendering so WSL can resolve it
    render_dir = LOCAL_SRC_DIR if LOCAL_SRC_DIR.exists() else Path(tempfile.gettempdir())

    with tempfile.NamedTemporaryFile("w", suffix=".pov", delete=False, dir=str(render_dir), encoding="utf-8") as tf:
        tf.write(scene_text)
        temp_pov_path = Path(tf.name)

    temp_png_path = temp_pov_path.with_suffix(".png")
    err_output = ""

    try:
        if IS_WINDOWS:
            wsl_work = _windows_to_wsl_path(render_dir)
            cmd = [
                "wsl",
                "--cd", wsl_work,
                "povray",
                f"+I{temp_pov_path.name}",
                f"+W{width}",
                f"+H{height}",
                f"+O{temp_png_path.name}",
                "+Q5",      # Fast draft quality
                "-D",       # Disable interactive X11 display
            ]
        else:
            cmd = [
                "povray",
                f"+I{temp_pov_path}",
                f"+W{width}",
                f"+H{height}",
                f"+O{temp_png_path}",
                "+Q5",
                "-D",
            ]

        proc = subprocess.run(
            cmd, cwd=str(render_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25
        )
        stdout_txt = proc.stdout.decode("utf-8", errors="replace")
        stderr_txt = proc.stderr.decode("utf-8", errors="replace")
        full_log = (stderr_txt + "\n" + stdout_txt).strip()

        if temp_png_path.exists() and temp_png_path.stat().st_size > 0:
            img = Image.open(temp_png_path).convert("RGB")
            return img, "Success"
        else:
            # Extract actionable POV-Ray error messages
            error_lines = []
            for line in full_log.splitlines():
                if any(k in line.lower() for k in ["error", "parse", "fatal", "expected", "undeclared"]):
                    error_lines.append(line.strip())
            err_output = "\n".join(error_lines) if error_lines else full_log[-500:]
            return None, err_output or "Unknown POV-Ray render failure."

    except Exception as exc:
        return None, f"Execution error: {exc}"
    finally:
        try:
            if temp_pov_path.exists():
                temp_pov_path.unlink()
            if temp_png_path.exists():
                temp_png_path.unlink()
        except Exception:
            pass


# ==============================================================================
# SCENE PARSER & ELEMENT MODELS
# ==============================================================================

@dataclass
class SceneElement:
    kind: str           # "camera", "light_source", "sphere", "box", "cylinder", "plane", "texture", etc.
    name: str
    line_start: int
    char_start: int
    char_end: int
    raw_text: str
    params: Dict[str, Any] = field(default_factory=dict)


class PovSceneParser:
    """Extracts cameras, lights, objects, and textures from POV-Ray source code."""

    @staticmethod
    def parse(source: str) -> List[SceneElement]:
        elements: List[SceneElement] = []

        block_patterns = [
            ("camera", r"\bcamera\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("light_source", r"\blight_source\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("sphere", r"\bsphere\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("box", r"\bbox\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("cylinder", r"\bcylinder\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("plane", r"\bplane\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("torus", r"\btorus\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("cone", r"\bcone\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("disc", r"\bdisc\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
        ]

        for kind, pat in block_patterns:
            for match in re.finditer(pat, source, re.DOTALL | re.IGNORECASE):
                raw = match.group(0)
                body = match.group(1)
                start_char = match.start()
                end_char = match.end()
                start_line = source[:start_char].count("\n") + 1

                name = f"{kind.capitalize()} (L{start_line})"
                params: Dict[str, Any] = {}

                if kind == "camera":
                    loc_m = re.search(r"location\s*<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", body, re.IGNORECASE)
                    params["location"] = [float(loc_m.group(1)), float(loc_m.group(2)), float(loc_m.group(3))] if loc_m else [0.0, 1.5, -4.0]

                    look_m = re.search(r"look_at\s*<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", body, re.IGNORECASE)
                    params["look_at"] = [float(look_m.group(1)), float(look_m.group(2)), float(look_m.group(3))] if look_m else [0.0, 1.0, 0.0]

                    ang_m = re.search(r"angle\s+([-0-9.]+)", body, re.IGNORECASE)
                    params["angle"] = float(ang_m.group(1)) if ang_m else 65.0
                    params["vectors"] = [params["location"], params["look_at"]]

                elif kind == "plane":
                    dist = 0.0
                    p_axis = re.search(r"plane\s*\{\s*[xyzXYZ]\s*,\s*([-0-9.]+)", raw, re.IGNORECASE)
                    if p_axis:
                        dist = float(p_axis.group(1))
                    else:
                        p_vec = re.search(r"plane\s*\{\s*<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>\s*,\s*([-0-9.]+)", raw, re.IGNORECASE)
                        if p_vec:
                            dist = float(p_vec.group(1))

                    tx, ty, tz = 0.0, dist, 0.0
                    tr_m = re.search(r"translate\s*<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", body, re.IGNORECASE)
                    if tr_m:
                        tx = float(tr_m.group(1))
                        tz = float(tr_m.group(3))

                    params["distance"] = dist
                    params["vectors"] = [[tx, ty, tz]]

                elif kind == "light_source":
                    ls_m = re.search(r"light_source\s*\{\s*<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", raw, re.IGNORECASE)
                    params["vectors"] = [[float(ls_m.group(1)), float(ls_m.group(2)), float(ls_m.group(3))]] if ls_m else [[0.0, 5.0, -5.0]]

                elif kind in ("sphere", "torus", "disc", "cylinder", "cone", "box"):
                    tr_m = re.search(r"translate\s*<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", raw, re.IGNORECASE)
                    if tr_m:
                        params["vectors"] = [[float(tr_m.group(1)), float(tr_m.group(2)), float(tr_m.group(3))]]
                    else:
                        vec_matches = []
                        for vm in re.finditer(r"<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", body):
                            prefix = body[:vm.start()].rstrip()
                            if not prefix.endswith(("rgb", "color", "rgbf", "rgbt", "rotate", "scale")):
                                vec_matches.append([float(vm.group(1)), float(vm.group(2)), float(vm.group(3))])
                        params["vectors"] = vec_matches if vec_matches else [[0.0, 0.0, 0.0]]

                    rad = 1.0
                    if kind == "sphere":
                        r_m = re.search(r"sphere\s*\{\s*<[^>]+>\s*,\s*([-0-9.]+)", raw, re.IGNORECASE)
                        if r_m: rad = float(r_m.group(1))
                    elif kind == "cylinder":
                        r_m = re.search(r"cylinder\s*\{[^<]*<[^>]+>[^<]*<[^>]+>\s*,\s*([-0-9.]+)", raw, re.IGNORECASE)
                        if r_m: rad = float(r_m.group(1))
                    elif kind == "cone":
                        r_m = re.search(r"cone\s*\{[^<]*<[^>]+>\s*,\s*([-0-9.]+)", raw, re.IGNORECASE)
                        if r_m: rad = float(r_m.group(1))
                    elif kind == "torus":
                        r_m = re.search(r"torus\s*\{\s*([-0-9.]+)", raw, re.IGNORECASE)
                        if r_m: rad = float(r_m.group(1))
                    params["radius"] = rad

                elements.append(
                    SceneElement(
                        kind=kind,
                        name=name,
                        line_start=start_line,
                        char_start=start_char,
                        char_end=end_char,
                        raw_text=raw,
                        params=params,
                    )
                )

        elements.sort(key=lambda e: e.line_start)
        return elements


# ==============================================================================
# POV-RAY SCENE STUDIO GUI
# ==============================================================================

class POVSceneStudio(tk.Toplevel):
    """POV-Ray Scene Editor, Material/Object Builder, Inspector, and Quick Previewer."""

    def __init__(
        self,
        parent: tk.Tk,
        initial_scene_path: Optional[Path] = None,
        on_scene_applied: Optional[Callable[[Path], None]] = None,
    ):
        super().__init__(parent)
        self.title("🏰 POV-Ray 3.7 Scene Studio & Visual Builder")
        self.geometry("1460x920")
        self.minsize(1120, 740)
        self.configure(bg="#181a20")

        self.current_scene_path: Optional[Path] = initial_scene_path
        self.on_scene_applied = on_scene_applied
        self.parsed_elements: List[SceneElement] = []
        self.selected_element: Optional[SceneElement] = None
        self.selected_element_idx: Optional[int] = None
        self._preview_photo: Optional[ImageTk.PhotoImage] = None
        self.is_rendering_preview: bool = False
        self._render_timer: Any = None
        self._render_pending: bool = False
        self.object_insert_count: int = 0

        self._build_ui()
        self._bind_shortcuts()

        if self.current_scene_path and self.current_scene_path.is_file():
            self.load_scene_file(self.current_scene_path)
        else:
            self.new_scene_template()

    # --------------------------------------------------------------------------
    # UI CONSTRUCTION
    # --------------------------------------------------------------------------
    def _build_ui(self):
        # 1. Top Ribbon Menu
        ribbon = tk.Frame(self, bg="#232733", height=42)
        ribbon.pack(side=tk.TOP, fill=tk.X)

        rbtn = {
            "bg": "#32384a", "fg": "#f1f5f9", "activebackground": "#434b63",
            "activeforeground": "#ffffff", "relief": tk.FLAT, "padx": 10, "pady": 4, "font": ("Segoe UI", 9)
        }

        tk.Button(ribbon, text="📄 New Scene", command=self.new_scene_template, **rbtn).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="↺ Reset Default", command=self.reset_working_default, bg="#7f1d1d", fg="#fecaca", relief=tk.FLAT, padx=8, pady=4, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="📂 Open .pov", command=self.on_open_file, **rbtn).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="↺ Revert File", command=self.on_revert_file, bg="#7c2d12", fg="#fed7aa", relief=tk.FLAT, padx=8, pady=4, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="↶ Undo", command=self.on_undo_code, **rbtn).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="💾 Save .pov", command=self.on_save_file, **rbtn).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="💾 Save As...", command=self.on_save_as_file, **rbtn).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(ribbon, text="🚀 Official GUI", command=self.on_spawn_official_gui, **rbtn).pack(side=tk.LEFT, padx=3, pady=5)

        tk.Label(ribbon, text="|", bg="#232733", fg="#475569").pack(side=tk.LEFT, padx=6)

        # Quick Render Preview Trigger Button
        render_btn = tk.Button(
            ribbon, text="⚡ RENDER PREVIEW [F9]",
            command=self.on_render_preview,
            bg="#059669", fg="#ffffff", activebackground="#047857",
            relief=tk.FLAT, padx=14, pady=4, font=("Segoe UI", 9, "bold")
        )
        render_btn.pack(side=tk.LEFT, padx=4, pady=5)

        tk.Label(ribbon, text="Resolution:", bg="#232733", fg="#94a3b8", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(10, 3))
        self.preview_res_var = tk.StringVar(value="320x240 (Instant)")
        res_cb = ttk.Combobox(
            ribbon, textvariable=self.preview_res_var,
            values=["320x240 (Instant)", "480x360", "640x480", "800x600", "1280x720 (HD)"],
            state="readonly", width=16
        )
        res_cb.pack(side=tk.LEFT, padx=2)

        # Apply to Main Tracer button
        apply_btn = tk.Button(
            ribbon, text="🚀 Send to Main Tracer",
            command=self.on_apply_to_main,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8",
            relief=tk.FLAT, padx=12, pady=4, font=("Segoe UI", 9, "bold")
        )
        apply_btn.pack(side=tk.RIGHT, padx=10, pady=5)

        self.scene_title_label = tk.Label(
            ribbon, text="Untitled.pov", bg="#232733", fg="#38bdf8", font=("Segoe UI", 9, "bold")
        )
        self.scene_title_label.pack(side=tk.RIGHT, padx=10)

        # 2. Main Paned Workspace
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#13151b", sashrelief=tk.RAISED, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # Left Panel: Scene Explorer + Object Inspector + Palettes
        left_panel = tk.Frame(main_paned, bg="#1a1d26", width=420)
        main_paned.add(left_panel, minsize=350)
        self._build_left_panel(left_panel)

        # Middle Panel: POV-Ray Code Editor
        center_panel = tk.Frame(main_paned, bg="#13151b")
        main_paned.add(center_panel, minsize=380)
        self._build_code_editor(center_panel)

        # Right Panel: Live Preview & Error Diagnostics & Spatial Radar
        right_panel = tk.Frame(main_paned, bg="#1a1d26", width=480)
        main_paned.add(right_panel, minsize=400)
        self._build_preview_panel(right_panel)

        # 3. Bottom Status Bar
        self.status_bar = tk.Label(
            self, text=f"Ready. Working Folder: {LOCAL_SRC_DIR}", bg="#0f1117", fg="#94a3b8",
            anchor="w", padx=10, pady=3, font=("Segoe UI", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_left_panel(self, parent: tk.Frame):
        """Constructs Scene Explorer, Interactive Object Inspector, and Insert Palettes."""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 1: Scene Explorer & Inspector
        explorer_tab = tk.Frame(notebook, bg="#1a1d26")
        notebook.add(explorer_tab, text="🔍 Scene & Transform")

        tk.Label(explorer_tab, text="SCENE OBJECTS & ELEMENTS:", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

        # Scene Treeview
        tree_frame = tk.Frame(explorer_tab, bg="#1a1d26", height=180)
        tree_frame.pack(fill=tk.X, padx=6, pady=2)

        self.scene_tree = ttk.Treeview(tree_frame, columns=("kind", "line"), show="tree", selectmode="browse", height=8)
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.scene_tree.yview)
        self.scene_tree.configure(yscrollcommand=tree_scroll.set)
        self.scene_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.scene_tree.bind("<<TreeviewSelect>>", self.on_tree_element_selected)

        # Interactive Object Inspector Panel
        inspector_frame = tk.LabelFrame(
            explorer_tab, text="🎯 Interactive Object Inspector (Move & Size)",
            bg="#202431", fg="#38bdf8", font=("Segoe UI", 9, "bold"), padx=8, pady=6
        )
        inspector_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 4))
        self._build_object_inspector(inspector_frame)

        # Tab 2: Insert Objects Palette
        objects_tab = tk.Frame(notebook, bg="#1a1d26")
        notebook.add(objects_tab, text="📦 Insert Objects")
        self._build_objects_palette(objects_tab)

        # Tab 3: Textures & Materials Palette
        textures_tab = tk.Frame(notebook, bg="#1a1d26")
        notebook.add(textures_tab, text="🎨 Textures")
        self._build_textures_palette(textures_tab)

        # Tab 4: Cameras & Rigs
        cameras_tab = tk.Frame(notebook, bg="#1a1d26")
        notebook.add(cameras_tab, text="📷 Cameras & Lights")
        self._build_cameras_palette(cameras_tab)

    def _build_object_inspector(self, parent: tk.Widget):
        """Constructs live sliders and spinboxes to move and size selected objects."""
        self.insp_name_var = tk.StringVar(value="Select an element above")
        tk.Label(parent, textvariable=self.insp_name_var, bg="#202431", fg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        lbl_s = {"bg": "#202431", "fg": "#cbd5e1", "font": ("Consolas", 9, "bold")}
        btn_nudge_s = {"bg": "#2e3447", "fg": "#f1f5f9", "relief": tk.FLAT, "padx": 5, "pady": 1, "font": ("Consolas", 8)}

        def _on_spin_enter(event):
            self.apply_inspector_transform()
            return "break"

        # 1. Primary Position Frame (Camera Location, Light Pos, Floor Elevation, Object Center)
        self.pos_frame = tk.Frame(parent, bg="#202431")
        self.pos_frame.pack(fill=tk.X, pady=2)

        self.pos_frame_lbl = tk.Label(self.pos_frame, text="POSITION (X, Y, Z):", **lbl_s)
        self.pos_frame_lbl.pack(anchor="w", pady=(0, 2))

        pos_grid = tk.Frame(self.pos_frame, bg="#202431")
        pos_grid.pack(fill=tk.X)

        # X Position
        tk.Label(pos_grid, text="X:", **lbl_s).grid(row=0, column=0, sticky="w", pady=2)
        self.pos_x_var = tk.DoubleVar(value=0.0)
        tk.Button(pos_grid, text="-1", command=lambda: self._nudge_pos("x", -1.0), **btn_nudge_s).grid(row=0, column=1, padx=2)
        self.spin_x = tk.Spinbox(pos_grid, from_=-500.0, to=500.0, increment=0.5, textvariable=self.pos_x_var, width=7, command=self.apply_inspector_transform)
        self.spin_x.grid(row=0, column=2, padx=2)
        self.spin_x.bind("<Return>", _on_spin_enter)
        self.spin_x.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(pos_grid, text="+1", command=lambda: self._nudge_pos("x", 1.0), **btn_nudge_s).grid(row=0, column=3, padx=2)

        # Y Position
        tk.Label(pos_grid, text="Y:", **lbl_s).grid(row=1, column=0, sticky="w", pady=2)
        self.pos_y_var = tk.DoubleVar(value=1.0)
        tk.Button(pos_grid, text="-1", command=lambda: self._nudge_pos("y", -1.0), **btn_nudge_s).grid(row=1, column=1, padx=2)
        self.spin_y = tk.Spinbox(pos_grid, from_=-500.0, to=500.0, increment=0.5, textvariable=self.pos_y_var, width=7, command=self.apply_inspector_transform)
        self.spin_y.grid(row=1, column=2, padx=2)
        self.spin_y.bind("<Return>", _on_spin_enter)
        self.spin_y.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(pos_grid, text="+1", command=lambda: self._nudge_pos("y", 1.0), **btn_nudge_s).grid(row=1, column=3, padx=2)

        # Z Position
        tk.Label(pos_grid, text="Z:", **lbl_s).grid(row=2, column=0, sticky="w", pady=2)
        self.pos_z_var = tk.DoubleVar(value=0.0)
        tk.Button(pos_grid, text="-1", command=lambda: self._nudge_pos("z", -1.0), **btn_nudge_s).grid(row=2, column=1, padx=2)
        self.spin_z = tk.Spinbox(pos_grid, from_=-500.0, to=500.0, increment=0.5, textvariable=self.pos_z_var, width=7, command=self.apply_inspector_transform)
        self.spin_z.grid(row=2, column=2, padx=2)
        self.spin_z.bind("<Return>", _on_spin_enter)
        self.spin_z.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(pos_grid, text="+1", command=lambda: self._nudge_pos("z", 1.0), **btn_nudge_s).grid(row=2, column=3, padx=2)

        # 2. Camera Controls Frame (Look-At Target & Angle FOV)
        self.cam_frame = tk.Frame(parent, bg="#202431")

        tk.Label(self.cam_frame, text="🎯 CAMERA AIM / LOOK-AT TARGET:", **lbl_s).pack(anchor="w", pady=(4, 2))
        look_grid = tk.Frame(self.cam_frame, bg="#202431")
        look_grid.pack(fill=tk.X)

        # Look-At X
        tk.Label(look_grid, text="Aim X:", **lbl_s).grid(row=0, column=0, sticky="w", pady=2)
        self.look_x_var = tk.DoubleVar(value=0.0)
        tk.Button(look_grid, text="-1", command=lambda: self._nudge_look("x", -1.0), **btn_nudge_s).grid(row=0, column=1, padx=2)
        self.spin_lx = tk.Spinbox(look_grid, from_=-500.0, to=500.0, increment=0.5, textvariable=self.look_x_var, width=7, command=self.apply_inspector_transform)
        self.spin_lx.grid(row=0, column=2, padx=2)
        self.spin_lx.bind("<Return>", _on_spin_enter)
        self.spin_lx.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(look_grid, text="+1", command=lambda: self._nudge_look("x", 1.0), **btn_nudge_s).grid(row=0, column=3, padx=2)

        # Look-At Y
        tk.Label(look_grid, text="Aim Y:", **lbl_s).grid(row=1, column=0, sticky="w", pady=2)
        self.look_y_var = tk.DoubleVar(value=1.0)
        tk.Button(look_grid, text="-1", command=lambda: self._nudge_look("y", -1.0), **btn_nudge_s).grid(row=1, column=1, padx=2)
        self.spin_ly = tk.Spinbox(look_grid, from_=-500.0, to=500.0, increment=0.5, textvariable=self.look_y_var, width=7, command=self.apply_inspector_transform)
        self.spin_ly.grid(row=1, column=2, padx=2)
        self.spin_ly.bind("<Return>", _on_spin_enter)
        self.spin_ly.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(look_grid, text="+1", command=lambda: self._nudge_look("y", 1.0), **btn_nudge_s).grid(row=1, column=3, padx=2)

        # Look-At Z
        tk.Label(look_grid, text="Aim Z:", **lbl_s).grid(row=2, column=0, sticky="w", pady=2)
        self.look_z_var = tk.DoubleVar(value=0.0)
        tk.Button(look_grid, text="-1", command=lambda: self._nudge_look("z", -1.0), **btn_nudge_s).grid(row=2, column=1, padx=2)
        self.spin_lz = tk.Spinbox(look_grid, from_=-500.0, to=500.0, increment=0.5, textvariable=self.look_z_var, width=7, command=self.apply_inspector_transform)
        self.spin_lz.grid(row=2, column=2, padx=2)
        self.spin_lz.bind("<Return>", _on_spin_enter)
        self.spin_lz.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(look_grid, text="+1", command=lambda: self._nudge_look("z", 1.0), **btn_nudge_s).grid(row=2, column=3, padx=2)

        # Camera Field of View (Angle)
        ang_grid = tk.Frame(self.cam_frame, bg="#202431")
        ang_grid.pack(fill=tk.X, pady=(4, 2))
        tk.Label(ang_grid, text="FOV Angle°:", **lbl_s).grid(row=0, column=0, sticky="w")
        self.cam_angle_var = tk.DoubleVar(value=65.0)
        tk.Button(ang_grid, text="-5", command=lambda: self._nudge_angle(-5.0), **btn_nudge_s).grid(row=0, column=1, padx=2)
        self.spin_ang = tk.Spinbox(ang_grid, from_=10.0, to=160.0, increment=5.0, textvariable=self.cam_angle_var, width=7, command=self.apply_inspector_transform)
        self.spin_ang.grid(row=0, column=2, padx=2)
        self.spin_ang.bind("<Return>", _on_spin_enter)
        self.spin_ang.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(ang_grid, text="+5", command=lambda: self._nudge_angle(5.0), **btn_nudge_s).grid(row=0, column=3, padx=2)

        # 3. Radius / Size Frame
        self.radius_frame = tk.Frame(parent, bg="#202431")
        self.radius_frame.pack(fill=tk.X, pady=2)

        r_grid = tk.Frame(self.radius_frame, bg="#202431")
        r_grid.pack(fill=tk.X)
        tk.Label(r_grid, text="Radius / Size:", **lbl_s).grid(row=0, column=0, sticky="w", pady=2)
        self.radius_var = tk.DoubleVar(value=1.0)
        tk.Button(r_grid, text="-0.2", command=lambda: self._nudge_radius(-0.2), **btn_nudge_s).grid(row=0, column=1, padx=2)
        self.spin_r = tk.Spinbox(r_grid, from_=0.05, to=200.0, increment=0.2, textvariable=self.radius_var, width=7, command=self.apply_inspector_transform)
        self.spin_r.grid(row=0, column=2, padx=2)
        self.spin_r.bind("<Return>", _on_spin_enter)
        self.spin_r.bind("<FocusOut>", lambda e: self.apply_inspector_transform())
        tk.Button(r_grid, text="+0.2", command=lambda: self._nudge_radius(0.2), **btn_nudge_s).grid(row=0, column=3, padx=2)

        # 4. Action Buttons Bar
        self.btn_bar = tk.Frame(parent, bg="#202431")
        self.btn_bar.pack(fill=tk.X, pady=(8, 2))

        self.color_btn = tk.Button(
            self.btn_bar, text="🎨 Pick Color", command=self.on_pick_element_color,
            bg="#3b4256", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, font=("Segoe UI", 8)
        )
        self.color_btn.pack(side=tk.LEFT, padx=2)

        self.mat_menu_btn = tk.Menubutton(
            self.btn_bar, text="✨ Material ▾",
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief=tk.FLAT, padx=8, pady=3, font=("Segoe UI", 8, "bold")
        )
        self.mat_menu = tk.Menu(self.mat_menu_btn, tearoff=0, bg="#1e222d", fg="#f1f5f9", activebackground="#2563eb")
        self._populate_materials_menu(self.mat_menu)
        self.mat_menu_btn["menu"] = self.mat_menu
        self.mat_menu_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(
            self.btn_bar, text="Apply Position & Render ⚡", command=self.apply_inspector_transform,
            bg="#2563eb", fg="#ffffff", relief=tk.FLAT, padx=10, pady=3, font=("Segoe UI", 8, "bold")
        ).pack(side=tk.RIGHT, padx=2)

    def _populate_materials_menu(self, menu: tk.Menu):
        menu.add_command(label="🪞 Perfect Chrome / Mirror", command=lambda: self.apply_material_to_element(self._snippet_chrome(), "Chrome"))
        menu.add_command(label="💎 Optical Glass (IOR 1.5)", command=lambda: self.apply_material_to_element(self._snippet_glass(), "Glass"))
        menu.add_command(label="👑 Polished Gold", command=lambda: self.apply_material_to_element(self._snippet_gold(), "Gold"))
        menu.add_command(label="🔘 Brushed Metal / Steel", command=lambda: self.apply_material_to_element(self._snippet_brushed_metal(), "Brushed Steel"))
        menu.add_command(label="🔴 Glossy Red Plastic", command=lambda: self.apply_material_to_element(self._snippet_red_plastic(), "Red Plastic"))
        menu.add_command(label="🟢 Emerald Gemstone", command=lambda: self.apply_material_to_element(self._snippet_emerald(), "Emerald"))
        menu.add_command(label="🟡 Neon Emissive Glow", command=lambda: self.apply_material_to_element(self._snippet_emissive_light(), "Neon Glow"))
        menu.add_command(label="🏁 Checkerboard Pattern", command=lambda: self.apply_material_to_element(self._snippet_checkerboard(), "Checkerboard"))
        menu.add_command(label="🌍 Earth Globe Map", command=lambda: self.apply_material_to_element(self._snippet_earth_map(), "Earth Globe"))
        menu.add_command(label="🌌 Astral Cosmic Map", command=lambda: self.apply_material_to_element(self._snippet_astral_map(), "Astral Map"))
        menu.add_separator()
        menu.add_command(label="🖼 Custom Image File Texture...", command=self.on_pick_custom_image_map)

    def _sync_spin_entry(self, spin: tk.Spinbox, val: float):
        if spin is not None:
            spin.delete(0, tk.END)
            spin.insert(0, str(round(val, 2)))

    def _read_spin_val(self, spin: tk.Spinbox, var: tk.DoubleVar) -> float:
        try:
            val_str = spin.get().strip()
            v = float(val_str)
            var.set(v)
            return v
        except Exception:
            return var.get()

    def _nudge_pos(self, axis: str, delta: float):
        spin_map = {"x": (self.spin_x, self.pos_x_var), "y": (self.spin_y, self.pos_y_var), "z": (self.spin_z, self.pos_z_var)}
        spin, var = spin_map[axis]
        curr = self._read_spin_val(spin, var)
        new_val = round(curr + delta, 2)
        var.set(new_val)
        spin.delete(0, tk.END)
        spin.insert(0, str(new_val))
        self.apply_inspector_transform()

    def _nudge_look(self, axis: str, delta: float):
        spin_map = {"x": (self.spin_lx, self.look_x_var), "y": (self.spin_ly, self.look_y_var), "z": (self.spin_lz, self.look_z_var)}
        spin, var = spin_map[axis]
        curr = self._read_spin_val(spin, var)
        new_val = round(curr + delta, 2)
        var.set(new_val)
        spin.delete(0, tk.END)
        spin.insert(0, str(new_val))
        self.apply_inspector_transform()

    def _nudge_angle(self, delta: float):
        curr = self._read_spin_val(self.spin_ang, self.cam_angle_var)
        new_val = max(10.0, min(160.0, round(curr + delta, 1)))
        self.cam_angle_var.set(new_val)
        self.spin_ang.delete(0, tk.END)
        self.spin_ang.insert(0, str(new_val))
        self.apply_inspector_transform()

    def _nudge_radius(self, delta: float):
        curr = self._read_spin_val(self.spin_r, self.radius_var)
        new_val = max(0.1, round(curr + delta, 2))
        self.radius_var.set(new_val)
        self.spin_r.delete(0, tk.END)
        self.spin_r.insert(0, str(new_val))
        self.apply_inspector_transform()

    def _schedule_preview_render(self, delay_ms: int = 300):
        """Debounces preview rendering so rapid typing/nudges don't spam or queue up stale jobs."""
        if hasattr(self, "_render_timer") and self._render_timer:
            try:
                self.after_cancel(self._render_timer)
            except Exception:
                pass
        self._render_timer = self.after(delay_ms, self.on_render_preview)

    def apply_inspector_transform(self):
        """Updates the selected element's coordinates directly in the code text."""
        if not self.selected_element or self.selected_element_idx is None:
            return

        elem = self.selected_element
        source = self.code_text.get("1.0", tk.END)

        nx = self._read_spin_val(self.spin_x, self.pos_x_var)
        ny = self._read_spin_val(self.spin_y, self.pos_y_var)
        nz = self._read_spin_val(self.spin_z, self.pos_z_var)
        nr = self._read_spin_val(self.spin_r, self.radius_var)
        lx = self._read_spin_val(self.spin_lx, self.look_x_var)
        ly = self._read_spin_val(self.spin_ly, self.look_y_var)
        lz = self._read_spin_val(self.spin_lz, self.look_z_var)
        ang = self._read_spin_val(self.spin_ang, self.cam_angle_var)

        old_block = elem.raw_text
        new_block = old_block

        if elem.kind == "camera":
            # 1. Update location <x, y, z>
            loc_pat = r"(location\s*)<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>"
            if re.search(loc_pat, new_block, re.IGNORECASE):
                new_block = re.sub(loc_pat, rf"\g<1><{nx:.2f}, {ny:.2f}, {nz:.2f}>", new_block, flags=re.IGNORECASE)
            else:
                new_block = re.sub(r"(camera\s*\{)", rf"\g<1>\n    location <{nx:.2f}, {ny:.2f}, {nz:.2f}>", new_block, flags=re.IGNORECASE)

            # 2. Update look_at <x, y, z>
            look_pat = r"(look_at\s*)<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>"
            if re.search(look_pat, new_block, re.IGNORECASE):
                new_block = re.sub(look_pat, rf"\g<1><{lx:.2f}, {ly:.2f}, {lz:.2f}>", new_block, flags=re.IGNORECASE)
            else:
                new_block = re.sub(r"(camera\s*\{)", rf"\g<1>\n    look_at <{lx:.2f}, {ly:.2f}, {lz:.2f}>", new_block, flags=re.IGNORECASE)

            # 3. Update angle
            ang_pat = r"(angle\s+)([-0-9.]+)"
            if re.search(ang_pat, new_block, re.IGNORECASE):
                new_block = re.sub(ang_pat, rf"\g<1>{ang:.1f}", new_block, flags=re.IGNORECASE)

        elif elem.kind == "light_source":
            # Update only position vector right after light_source {
            ls_pat = r"(light_source\s*\{\s*)<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>"
            new_block = re.sub(ls_pat, rf"\g<1><{nx:.2f}, {ny:.2f}, {nz:.2f}>", new_block, flags=re.IGNORECASE)

        elif elem.kind == "plane":
            # Update plane Y elevation
            pl_dist_pat = r"(plane\s*\{\s*(?:<[^>]+>|[xyzXYZ])\s*,\s*)([-0-9.]+)"
            if re.search(pl_dist_pat, new_block, re.IGNORECASE):
                new_block = re.sub(pl_dist_pat, rf"\g<1>{ny:.2f}", new_block, flags=re.IGNORECASE)

            # Update or insert translate for X and Z shift
            tr_pat = r"(translate\s*)<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>"
            if re.search(tr_pat, new_block, re.IGNORECASE):
                new_block = re.sub(tr_pat, rf"\g<1><{nx:.2f}, 0.00, {nz:.2f}>", new_block, flags=re.IGNORECASE)
            elif abs(nx) > 0.001 or abs(nz) > 0.001:
                last_brace = new_block.rfind("}")
                if last_brace != -1:
                    new_block = new_block[:last_brace] + f"    translate <{nx:.2f}, 0.00, {nz:.2f}>\n" + new_block[last_brace:]

        elif elem.kind == "sphere":
            # Update center vector
            sph_pos_pat = r"(sphere\s*\{\s*)<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>"
            new_block = re.sub(sph_pos_pat, rf"\g<1><{nx:.2f}, {ny:.2f}, {nz:.2f}>", new_block, flags=re.IGNORECASE)
            # Update radius
            sph_r_pat = r"(sphere\s*\{\s*<[^>]+>\s*,\s*)([-0-9.]+)"
            new_block = re.sub(sph_r_pat, rf"\g<1>{nr:.2f}", new_block, flags=re.IGNORECASE)

        elif elem.kind in ("cylinder", "cone", "box", "torus", "disc"):
            tr_pat = r"(translate\s*)<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+\s*>"
            if re.search(tr_pat, new_block, re.IGNORECASE):
                new_block = re.sub(tr_pat, rf"\g<1><{nx:.2f}, {ny:.2f}, {nz:.2f}>", new_block, flags=re.IGNORECASE)
            else:
                # No translate statement: move BOTH geometry vectors synchronously to prevent tilting/stretching!
                vec_matches = []
                for m in re.finditer(r"<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", new_block):
                    prefix = new_block[:m.start()].rstrip()
                    if not prefix.endswith(("rgb", "color", "rgbf", "rgbt", "rotate", "scale")):
                        vec_matches.append(m)

                if len(vec_matches) >= 2:
                    m1, m2 = vec_matches[0], vec_matches[1]
                    x1, y1, z1 = float(m1.group(1)), float(m1.group(2)), float(m1.group(3))
                    x2, y2, z2 = float(m2.group(1)), float(m2.group(2)), float(m2.group(3))
                    hx, hy, hz = x2 - x1, y2 - y1, z2 - z1

                    new_v1_str = f"<{nx:.2f}, {ny:.2f}, {nz:.2f}>"
                    new_v2_str = f"<{nx + hx:.2f}, {ny + hy:.2f}, {nz + hz:.2f}>"

                    new_block = new_block[:m2.start()] + new_v2_str + new_block[m2.end():]
                    new_block = new_block[:m1.start()] + new_v1_str + new_block[m1.end():]
                elif elem.kind == "torus":
                    last_brace = new_block.rfind("}")
                    if last_brace != -1:
                        new_block = new_block[:last_brace] + f"    translate <{nx:.2f}, {ny:.2f}, {nz:.2f}>\n" + new_block[last_brace:]

            # Radius / size scaling
            if elem.kind == "cylinder":
                cyl_r_pat = r"(cylinder\s*\{[^<]*<[^>]+>[^<]*<[^>]+>\s*,\s*)([-0-9.]+)"
                if re.search(cyl_r_pat, new_block, re.IGNORECASE):
                    new_block = re.sub(cyl_r_pat, rf"\g<1>{nr:.2f}", new_block, flags=re.IGNORECASE)
            elif elem.kind == "cone":
                cone_r_pat = r"(cone\s*\{[^<]*<[^>]+>\s*,\s*)([-0-9.]+)"
                if re.search(cone_r_pat, new_block, re.IGNORECASE):
                    new_block = re.sub(cone_r_pat, rf"\g<1>{nr:.2f}", new_block, flags=re.IGNORECASE)
            elif elem.kind == "torus":
                torus_r_pat = r"(torus\s*\{\s*)([-0-9.]+)"
                if re.search(torus_r_pat, new_block, re.IGNORECASE):
                    new_block = re.sub(torus_r_pat, rf"\g<1>{nr:.2f}", new_block, flags=re.IGNORECASE)

        # Locate and replace old_block in source code text
        pos = source.find(old_block)
        if pos == -1:
            old_norm = " ".join(old_block.split())
            for elem_candidate in PovSceneParser.parse(source):
                if elem_candidate.kind == elem.kind and " ".join(elem_candidate.raw_text.split()) == old_norm:
                    pos = elem_candidate.char_start
                    old_block = elem_candidate.raw_text
                    break

        if pos != -1:
            updated_source = source[:pos] + new_block + source[pos + len(old_block):]
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", updated_source)

            # Update element in memory immediately
            elem.raw_text = new_block
            if elem.kind == "camera":
                elem.params["location"] = [nx, ny, nz]
                elem.params["look_at"] = [lx, ly, lz]
                elem.params["angle"] = ang
                elem.params["vectors"] = [[nx, ny, nz], [lx, ly, lz]]
            elif elem.kind == "plane":
                elem.params["vectors"] = [[nx, ny, nz]]
            elif "vectors" in elem.params and elem.params["vectors"]:
                elem.params["vectors"][0] = [nx, ny, nz]
            if "radius" in elem.params:
                elem.params["radius"] = nr

            saved_idx = self.selected_element_idx
            self.parse_and_populate_tree(preserve_index=saved_idx)
            self.draw_spatial_radar()
            self._schedule_preview_render(delay_ms=300)

    def on_pick_element_color(self):
        if not self.selected_element or self.selected_element_idx is None:
            messagebox.showinfo("Pick Color", "Select an object first.")
            return
        chosen = colorchooser.askcolor(title="Pick Object Color")
        if chosen and chosen[0]:
            r, g, b = [round(c / 255.0, 3) for c in chosen[0]]
            source = self.code_text.get("1.0", tk.END)
            old_block = self.selected_element.raw_text

            col_match = re.search(r"color\s+rgb[ft]?\s*<\s*[-0-9.]+\s*,\s*[-0-9.]+\s*,\s*[-0-9.]+(?:\s*,\s*[-0-9.]+)?\s*>", old_block, re.IGNORECASE)
            new_col_str = f"color rgb <{r}, {g}, {b}>"
            if col_match:
                new_block = old_block[:col_match.start()] + new_col_str + old_block[col_match.end():]
            else:
                # Add pigment block if missing
                insert_pt = old_block.rfind("}")
                if insert_pt != -1:
                    new_block = old_block[:insert_pt] + f"    pigment {{ {new_col_str} }}\n" + old_block[insert_pt:]
                else:
                    new_block = old_block

            pos = source.find(old_block)
            if pos != -1:
                updated_source = source[:pos] + new_block + source[pos + len(old_block):]
                self.code_text.delete("1.0", tk.END)
                self.code_text.insert("1.0", updated_source)
                self.selected_element.raw_text = new_block
                saved_idx = self.selected_element_idx
                self.parse_and_populate_tree(preserve_index=saved_idx)
                self.draw_spatial_radar()
                self._schedule_preview_render(delay_ms=50)

    def _remove_keywords_with_braces(self, text: str, keywords: List[str]) -> str:
        """Finds keywords (like 'texture', 'pigment', 'finish', 'interior')
        and cleanly cuts out their entire '{ ... }' block using exact brace counting.
        """
        for kw in keywords:
            pos = 0
            while True:
                pattern = rf"\b{kw}\s*\{{"
                m = re.search(pattern, text[pos:], re.IGNORECASE)
                if not m:
                    break
                kw_start = pos + m.start()
                brace_start = pos + m.end() - 1  # index of '{'

                depth = 1
                idx = brace_start + 1
                while idx < len(text) and depth > 0:
                    if text[idx] == '{':
                        depth += 1
                    elif text[idx] == '}':
                        depth -= 1
                    idx += 1

                if depth == 0:
                    text = text[:kw_start] + text[idx:]
                    pos = kw_start
                else:
                    pos = brace_start + 1
        return text

    def apply_material_to_element(self, mat_snippet: str, mat_name: str = "Material"):
        """Applies a texture/material block directly into the selected scene element."""
        # 1. If cursor in code editor is sitting inside a specific element, target that element!
        cursor_idx = self.get_element_at_cursor()
        if cursor_idx is not None and cursor_idx != self.selected_element_idx:
            self.scene_tree.selection_set(str(cursor_idx))
            self.on_tree_element_selected()

        # 2. If still nothing selected, try to auto-select the first 3D shape
        if not self.selected_element or self.selected_element_idx is None:
            shapes = [e for e in self.parsed_elements if e.kind not in ("camera", "light_source")]
            if shapes:
                first_idx = self.parsed_elements.index(shapes[0])
                self.scene_tree.selection_set(str(first_idx))
                self.on_tree_element_selected()
            else:
                # No 3D objects exist: insert as a clean #declare block
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', mat_name).strip('_')
                declare_snippet = f"\n// Declared Material Preset\n#declare Mat_{clean_name} = {mat_snippet.strip()};\n"
                self.code_text.insert("1.0", declare_snippet)
                self.parse_and_populate_tree()
                self.status_bar.config(text=f"Declared #declare Mat_{clean_name} at top of file (No 3D object in scene).")
                self._schedule_preview_render(delay_ms=50)
                return

        elem = self.selected_element
        if elem.kind in ("camera", "light_source"):
            messagebox.showwarning(
                "Cannot Apply Texture",
                f"'{elem.name}' is a {elem.kind}.\nCameras and lights cannot have surface textures in POV-Ray.\n\nPlease select a 3D object (Sphere, Plane, Box, etc.) from the Scene Tree first."
            )
            return

        source = self.code_text.get("1.0", tk.END)
        old_block = elem.raw_text

        # Strip any existing material keywords (texture, pigment, finish, interior) from old_block
        stripped_block = self._remove_keywords_with_braces(
            old_block, ["texture", "pigment", "finish", "interior"]
        )

        # Locate the closing brace of the object
        last_brace = stripped_block.rfind("}")
        if last_brace == -1:
            return

        # Format and indent the new material snippet (4 spaces indentation)
        indented_mat = "\n".join("    " + line.strip() if line.strip() else "" for line in mat_snippet.strip().splitlines())
        new_block = f"{stripped_block[:last_brace].rstrip()}\n{indented_mat}\n}}"

        pos = source.find(old_block)
        if pos == -1:
            old_norm = " ".join(old_block.split())
            for elem_candidate in PovSceneParser.parse(source):
                if elem_candidate.kind == elem.kind and " ".join(elem_candidate.raw_text.split()) == old_norm:
                    pos = elem_candidate.char_start
                    old_block = elem_candidate.raw_text
                    break

        if pos != -1:
            updated_source = source[:pos] + new_block + source[pos + len(old_block):]
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", updated_source)
            self.selected_element.raw_text = new_block

            saved_idx = self.selected_element_idx
            self.parse_and_populate_tree(preserve_index=saved_idx)
            self.draw_spatial_radar()
            self.status_bar.config(text=f"Applied '{mat_name}' material to {elem.name} ✨")
            self._schedule_preview_render(delay_ms=50)
        else:
            self.status_bar.config(text="Could not locate object block in source code.")

    def on_declare_material_global(self):
        """Allows declaring a material as a reusable global #declare at top of file."""
        dialog = tk.Toplevel(self)
        dialog.title("Declare Global Material")
        dialog.geometry("380x300")
        dialog.configure(bg="#1a1d26")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Select Material to Declare:", bg="#1a1d26", fg="#f1f5f9", font=("Segoe UI", 10, "bold")).pack(padx=12, pady=(12, 6), anchor="w")

        presets = [
            ("Chrome", self._snippet_chrome),
            ("OpticalGlass", self._snippet_glass),
            ("Gold", self._snippet_gold),
            ("BrushedSteel", self._snippet_brushed_metal),
            ("RedPlastic", self._snippet_red_plastic),
            ("Emerald", self._snippet_emerald),
            ("NeonGlow", self._snippet_emissive_light),
            ("Checkerboard", self._snippet_checkerboard),
            ("EarthGlobe", self._snippet_earth_map),
            ("AstralCosmic", self._snippet_astral_map),
        ]

        preset_var = tk.StringVar(value="Chrome")
        cb = ttk.Combobox(dialog, textvariable=preset_var, values=[p[0] for p in presets], state="readonly", width=25)
        cb.pack(padx=12, pady=6, fill=tk.X)

        tk.Label(dialog, text="Declaration Identifier Name:", bg="#1a1d26", fg="#94a3b8", font=("Segoe UI", 9)).pack(padx=12, pady=(8, 2), anchor="w")
        name_var = tk.StringVar(value="Material_Chrome")
        name_entry = tk.Entry(dialog, textvariable=name_var, bg="#0d0f14", fg="#38bdf8", insertbackground="#38bdf8", font=("Consolas", 10))
        name_entry.pack(padx=12, pady=2, fill=tk.X)

        def _on_cb_change(e):
            name_var.set(f"Material_{preset_var.get()}")
        cb.bind("<<ComboboxSelected>>", _on_cb_change)

        def _do_insert():
            ident = re.sub(r'[^a-zA-Z0-9_]', '_', name_var.get().strip()).strip('_')
            chosen_name = preset_var.get()
            fn = next((p[1] for p in presets if p[0] == chosen_name), self._snippet_chrome)
            mat_body = fn()
            decl_block = f"\n// Reusable Material Definition\n#declare {ident} = {mat_body.strip()};\n"

            source = self.code_text.get("1.0", tk.END)
            inc_match = re.search(r'#include\s+["<][^">]+[">]', source)
            if inc_match:
                insert_idx = source.find("\n", inc_match.end())
                if insert_idx != -1:
                    updated = source[:insert_idx+1] + decl_block + source[insert_idx+1:]
                else:
                    updated = source + decl_block
            else:
                updated = decl_block + source

            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", updated)
            self.parse_and_populate_tree()
            self.status_bar.config(text=f"Declared reusable '#declare {ident}' in scene.")
            self._schedule_preview_render(delay_ms=50)
            dialog.destroy()

        btn_box = tk.Frame(dialog, bg="#1a1d26")
        btn_box.pack(fill=tk.X, padx=12, pady=16)
        tk.Button(btn_box, text="Cancel", command=dialog.destroy, bg="#334155", fg="#cbd5e1", relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_box, text="Declare Material ⚡", command=_do_insert, bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=12, pady=4, font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=4)

    def _build_objects_palette(self, parent: tk.Frame):
        tk.Label(parent, text="CLICK TO INSERT (Auto-Offset Position):", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        pbtn = {"bg": "#2a2f3f", "fg": "#f8fafc", "relief": tk.FLAT, "anchor": "w", "padx": 10, "pady": 4}

        primitives = [
            ("🔮 Sphere (Auto-Offset)", self._snippet_sphere),
            ("📦 Bounding Box", self._snippet_box),
            ("🥫 Cylinder / Tube", self._snippet_cylinder),
            ("📐 Infinite Floor Plane", self._snippet_plane),
            ("🍩 Torus Ring", self._snippet_torus),
            ("🔺 Cone", self._snippet_cone),
            ("🕳 5-Section Textured Tunnel", self._snippet_tunnel),
        ]
        for label, fn in primitives:
            tk.Button(parent, text=label, command=lambda f=fn: self.insert_code_snippet(f()), **pbtn).pack(fill=tk.X, padx=8, pady=3)

    def _build_textures_palette(self, parent: tk.Frame):
        tgt_frame = tk.Frame(parent, bg="#13151b", padx=8, pady=6)
        tgt_frame.pack(fill=tk.X, padx=6, pady=(6, 4))

        tk.Label(tgt_frame, text="TARGET OBJECT TO APPLY TO:", bg="#13151b", fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.tex_target_lbl = tk.Label(tgt_frame, text="Select an object in Scene Tree", bg="#13151b", fg="#38bdf8", font=("Segoe UI", 9, "bold"))
        self.tex_target_lbl.pack(anchor="w", pady=(2, 0))

        tk.Label(parent, text="CLICK ANY MATERIAL TO APPLY TO OBJECT:", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
        pbtn = {"bg": "#2a2f3f", "fg": "#f8fafc", "relief": tk.FLAT, "anchor": "w", "padx": 10, "pady": 4}

        materials = [
            ("🪞 Perfect Chrome / Mirror", self._snippet_chrome, "Chrome"),
            ("💎 Optical Glass (IOR 1.5)", self._snippet_glass, "Optical Glass"),
            ("👑 Polished Gold", self._snippet_gold, "Gold"),
            ("🔘 Brushed Metal / Steel", self._snippet_brushed_metal, "Brushed Steel"),
            ("🔴 Glossy Red Plastic", self._snippet_red_plastic, "Red Plastic"),
            ("🟢 Emerald Gemstone", self._snippet_emerald, "Emerald"),
            ("🟡 Emissive Luminaire Neon Glow", self._snippet_emissive_light, "Neon Glow"),
            ("🏁 Checkerboard Pattern", self._snippet_checkerboard, "Checkerboard"),
            ("🌍 Realistic Earth Globe Map", self._snippet_earth_map, "Earth Globe"),
            ("🌌 Astral Cosmic Image Map", self._snippet_astral_map, "Astral Map"),
            ("🖼 Custom Image File Texture...", self.on_pick_custom_image_map, "Custom Image"),
        ]
        for label, fn, name in materials:
            if fn == self.on_pick_custom_image_map:
                cmd = self.on_pick_custom_image_map
            else:
                cmd = lambda f=fn, n=name: self.apply_material_to_element(f(), n)
            tk.Button(parent, text=label, command=cmd, **pbtn).pack(fill=tk.X, padx=8, pady=2)

        decl_frame = tk.Frame(parent, bg="#13151b", padx=8, pady=6)
        decl_frame.pack(fill=tk.X, padx=6, pady=(10, 4))
        tk.Label(decl_frame, text="GLOBAL MATERIAL LIBRARY:", bg="#13151b", fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(decl_frame, text="Declares reusable #declare at top of scene file.", bg="#13151b", fg="#64748b", font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 4))

        tk.Button(
            decl_frame, text="➕ Declare Material at Top (#declare)",
            command=self.on_declare_material_global,
            bg="#334155", fg="#f1f5f9", relief=tk.FLAT, padx=8, pady=3, font=("Segoe UI", 8, "bold")
        ).pack(fill=tk.X)

    def _build_cameras_palette(self, parent: tk.Frame):
        tk.Label(parent, text="CAMERA & LIGHTING PRESETS:", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        pbtn = {"bg": "#2a2f3f", "fg": "#f8fafc", "relief": tk.FLAT, "anchor": "w", "padx": 10, "pady": 4}

        presets = [
            ("📷 Tunnel Center Look-Through", self._snippet_tunnel_camera),
            ("📷 Walking Human Eye-Level (1.7m)", self._snippet_walking_camera),
            ("📷 3/4 Isometric Perspective", self._snippet_isometric_camera),
            ("💡 3-Point Studio Lighting (Key, Fill, Rim)", self._snippet_3point_lights),
            ("💡 Overhead Spaced Tunnel Lights", self._snippet_overhead_tunnel_lights),
        ]
        for label, fn in presets:
            tk.Button(parent, text=label, command=lambda f=fn: self.insert_code_snippet(f()), **pbtn).pack(fill=tk.X, padx=8, pady=3)

    def _build_code_editor(self, parent: tk.Frame):
        """Constructs the code editor area with line numbers and parse refresh."""
        header = tk.Frame(parent, bg="#13151b", height=28)
        header.pack(fill=tk.X, padx=6, pady=(6, 2))
        tk.Label(header, text="POV-RAY SCENE SOURCE CODE", bg="#13151b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Button(
            header, text="🔄 Reparse Scene Tree", command=self.parse_and_populate_tree,
            bg="#2a2e3d", fg="#cbd5e1", relief=tk.FLAT, padx=6, pady=1, font=("Segoe UI", 8)
        ).pack(side=tk.RIGHT)

        text_frame = tk.Frame(parent, bg="#13151b")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.code_text = tk.Text(
            text_frame, bg="#0d0f14", fg="#e2e8f0", insertbackground="#38bdf8",
            selectbackground="#2563eb", selectforeground="#ffffff",
            wrap=tk.NONE, font=("Consolas", 10), undo=True, maxundo=50
        )
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.code_text.yview)
        scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.code_text.xview)
        self.code_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.code_text.bind("<KeyRelease>", lambda e: self._on_code_modified())
        self.code_text.bind("<ButtonRelease-1>", lambda e: self._on_code_cursor_moved())

    def _build_preview_panel(self, parent: tk.Frame):
        """Live Preview Canvas, Error Diagnostics Banner, and 2D Spatial Overview."""
        p_header = tk.Frame(parent, bg="#1a1d26", height=28)
        p_header.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(p_header, text="RAY-TRACED PREVIEW", bg="#1a1d26", fg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.render_time_label = tk.Label(p_header, text="Ready", bg="#1a1d26", fg="#38bdf8", font=("Consolas", 9, "bold"))
        self.render_time_label.pack(side=tk.RIGHT)

        # Preview Canvas
        self.preview_canvas = tk.Canvas(parent, bg="#0b0d11", highlightthickness=1, highlightbackground="#2d3345")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
        self.preview_canvas.create_text(200, 150, text="Press F9 to render quick preview.", fill="#475569", font=("Segoe UI", 10))

        # POV-Ray Error / Diagnostics Banner (Expands on error, collapses on success)
        self.error_frame = tk.Frame(parent, bg="#3b1212", padx=6, pady=4)
        self.error_label = tk.Label(
            self.error_frame, text="", bg="#3b1212", fg="#fca5a5",
            justify=tk.LEFT, anchor="w", font=("Consolas", 8), wraplength=420
        )
        self.error_label.pack(fill=tk.X)

        # Bottom 2D Spatial Radar / Top-Down View
        radar_header = tk.Frame(parent, bg="#1a1d26", height=24)
        radar_header.pack(fill=tk.X, padx=8, pady=(4, 2))
        tk.Label(radar_header, text="📍 2D TOP-DOWN SCENE RADAR", bg="#1a1d26", fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)

        self.radar_canvas = tk.Canvas(parent, bg="#090a0f", height=150, highlightthickness=1, highlightbackground="#2d3345")
        self.radar_canvas.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.draw_spatial_radar()

    def _bind_shortcuts(self):
        self.bind("<F9>", lambda e: self.on_render_preview())
        self.bind("<Control-s>", lambda e: self.on_save_file())
        self.bind("<Control-o>", lambda e: self.on_open_file())
        self.bind("<Control-z>", lambda e: self.on_undo_code())

    # --------------------------------------------------------------------------
    # SCENE PARSING & EXPLORER TREE
    # --------------------------------------------------------------------------
    def parse_and_populate_tree(self, preserve_index: Optional[int] = None):
        source = self.code_text.get("1.0", tk.END)
        self.parsed_elements = PovSceneParser.parse(source)

        self.scene_tree.delete(*self.scene_tree.get_children())

        for idx, elem in enumerate(self.parsed_elements):
            icon = {
                "camera": "📷",
                "light_source": "💡",
                "plane": "📐",
                "sphere": "🔮",
                "torus": "🍩",
                "cylinder": "🥫",
                "cone": "🔺",
                "box": "📦",
            }.get(elem.kind, "🔷")
            display_text = f"{icon} {elem.name}"
            self.scene_tree.insert("", "end", iid=str(idx), text=display_text, values=(elem.kind, elem.line_start))

        # Restore active selection so continuous transforms NEVER lose focus or state
        target_idx = preserve_index if preserve_index is not None else self.selected_element_idx
        if target_idx is not None and 0 <= target_idx < len(self.parsed_elements):
            target_iid = str(target_idx)
            if self.scene_tree.exists(target_iid):
                self.scene_tree.selection_set(target_iid)
                self.scene_tree.focus(target_iid)
                self.selected_element_idx = target_idx
                self.selected_element = self.parsed_elements[target_idx]
                self.insp_name_var.set(f"Selected: {self.selected_element.name}")
        elif self.parsed_elements:
            default_idx = 0
            for i, el in enumerate(self.parsed_elements):
                if el.kind not in ("camera", "light_source"):
                    default_idx = i
                    break
            self.scene_tree.selection_set(str(default_idx))
            self.on_tree_element_selected()

        self.draw_spatial_radar()

    def on_tree_element_selected(self, event=None, scroll_code: bool = True):
        sel = self.scene_tree.selection()
        if not sel:
            return

        idx_str = sel[0]
        if not idx_str.isdigit() or int(idx_str) >= len(self.parsed_elements):
            return

        idx = int(idx_str)
        self.selected_element_idx = idx
        elem = self.parsed_elements[idx]
        self.selected_element = elem
        self.insp_name_var.set(f"Selected: {elem.name}")

        # Configure dynamic UI sections
        if elem.kind == "camera":
            self.pos_frame_lbl.config(text="📷 CAMERA LOCATION:")
            self.cam_frame.pack(fill=tk.X, pady=(4, 2), before=self.btn_bar)
            self.radius_frame.pack_forget()
            self.color_btn.pack_forget()
            if hasattr(self, "mat_menu_btn"):
                self.mat_menu_btn.pack_forget()

            loc = elem.params.get("location", [0.0, 1.5, -4.0])
            self.pos_x_var.set(round(loc[0], 2))
            self.pos_y_var.set(round(loc[1], 2))
            self.pos_z_var.set(round(loc[2], 2))
            self._sync_spin_entry(self.spin_x, loc[0])
            self._sync_spin_entry(self.spin_y, loc[1])
            self._sync_spin_entry(self.spin_z, loc[2])

            look = elem.params.get("look_at", [0.0, 1.0, 0.0])
            self.look_x_var.set(round(look[0], 2))
            self.look_y_var.set(round(look[1], 2))
            self.look_z_var.set(round(look[2], 2))
            self._sync_spin_entry(self.spin_lx, look[0])
            self._sync_spin_entry(self.spin_ly, look[1])
            self._sync_spin_entry(self.spin_lz, look[2])

            ang = elem.params.get("angle", 65.0)
            self.cam_angle_var.set(round(ang, 1))
            self._sync_spin_entry(self.spin_ang, ang)

        elif elem.kind == "plane":
            self.pos_frame_lbl.config(text="📐 FLOOR ELEVATION (Y) & TILE SHIFT (X, Z):")
            self.cam_frame.pack_forget()
            self.radius_frame.pack_forget()
            self.color_btn.pack(side=tk.LEFT, padx=2)
            if hasattr(self, "mat_menu_btn"):
                self.mat_menu_btn.pack(side=tk.LEFT, padx=2)

            vecs = elem.params.get("vectors", [[0.0, 0.0, 0.0]])
            pos = vecs[0]
            self.pos_x_var.set(round(pos[0], 2))
            self.pos_y_var.set(round(pos[1], 2))
            self.pos_z_var.set(round(pos[2], 2))
            self._sync_spin_entry(self.spin_x, pos[0])
            self._sync_spin_entry(self.spin_y, pos[1])
            self._sync_spin_entry(self.spin_z, pos[2])

        elif elem.kind == "light_source":
            self.pos_frame_lbl.config(text="💡 LIGHT POSITION:")
            self.cam_frame.pack_forget()
            self.radius_frame.pack_forget()
            self.color_btn.pack(side=tk.LEFT, padx=2)
            if hasattr(self, "mat_menu_btn"):
                self.mat_menu_btn.pack_forget()

            vecs = elem.params.get("vectors", [[0.0, 5.0, -5.0]])
            pos = vecs[0]
            self.pos_x_var.set(round(pos[0], 2))
            self.pos_y_var.set(round(pos[1], 2))
            self.pos_z_var.set(round(pos[2], 2))
            self._sync_spin_entry(self.spin_x, pos[0])
            self._sync_spin_entry(self.spin_y, pos[1])
            self._sync_spin_entry(self.spin_z, pos[2])

        else: # sphere, box, cylinder, torus, etc.
            self.pos_frame_lbl.config(text="🔷 OBJECT POSITION:")
            self.cam_frame.pack_forget()
            self.radius_frame.pack(fill=tk.X, pady=(2, 2), before=self.btn_bar)
            self.color_btn.pack(side=tk.LEFT, padx=2)
            if hasattr(self, "mat_menu_btn"):
                self.mat_menu_btn.pack(side=tk.LEFT, padx=2)

            vecs = elem.params.get("vectors", [[0.0, 0.0, 0.0]])
            pos = vecs[0]
            self.pos_x_var.set(round(pos[0], 2))
            self.pos_y_var.set(round(pos[1], 2))
            self.pos_z_var.set(round(pos[2], 2))
            self._sync_spin_entry(self.spin_x, pos[0])
            self._sync_spin_entry(self.spin_y, pos[1])
            self._sync_spin_entry(self.spin_z, pos[2])

            rad = elem.params.get("radius", 1.0)
            self.radius_var.set(round(rad, 2))
            self._sync_spin_entry(self.spin_r, rad)

        if hasattr(self, "tex_target_lbl"):
            self.tex_target_lbl.config(text=f"Selected: {elem.name} ({elem.kind})")

        # Highlight lines in code
        if scroll_code:
            self.code_text.see(f"{elem.line_start}.0")
            self.code_text.mark_set(tk.INSERT, f"{elem.line_start}.0")
        end_line = elem.line_start + elem.raw_text.count("\n") + 1
        self.code_text.tag_remove("highlight", "1.0", tk.END)
        self.code_text.tag_add("highlight", f"{elem.line_start}.0", f"{end_line}.0")
        self.code_text.tag_config("highlight", background="#2a3f68")

    def _on_code_modified(self):
        if hasattr(self, "_reparse_timer") and self._reparse_timer:
            self.after_cancel(self._reparse_timer)
        self._reparse_timer = self.after(1000, lambda: self.parse_and_populate_tree(preserve_index=self.selected_element_idx))

    def get_element_at_cursor(self) -> Optional[int]:
        """Finds the index of the parsed scene element enclosing the text cursor position."""
        try:
            cursor_pos = self.code_text.index(tk.INSERT)
            char_idx = len(self.code_text.get("1.0", cursor_pos))
            best_idx = None
            best_span = float("inf")
            for idx, elem in enumerate(self.parsed_elements):
                if elem.char_start <= char_idx <= elem.char_end:
                    span = elem.char_end - elem.char_start
                    if span < best_span:
                        best_span = span
                        best_idx = idx
            if best_idx is not None:
                return best_idx

            cursor_line = int(cursor_pos.split(".")[0])
            for idx, elem in enumerate(self.parsed_elements):
                line_count = elem.raw_text.count("\n")
                if elem.line_start <= cursor_line <= elem.line_start + line_count:
                    return idx
            return None
        except Exception:
            return None

    def _on_code_cursor_moved(self):
        """When text cursor moves, automatically select enclosing element in tree and inspector."""
        elem_idx = self.get_element_at_cursor()
        if elem_idx is not None and elem_idx != self.selected_element_idx:
            self.scene_tree.selection_set(str(elem_idx))
            self.on_tree_element_selected(scroll_code=False)

    def on_undo_code(self):
        """Reverts the last text edit action in the code editor."""
        try:
            self.code_text.edit_undo()
            self._on_code_modified()
            self.status_bar.config(text="Undo last edit.")
        except tk.TclError:
            self.status_bar.config(text="Nothing to undo.")

    def on_revert_file(self):
        """Discards unsaved edits and reloads the current scene from disk."""
        if not self.current_scene_path or not self.current_scene_path.is_file():
            if messagebox.askyesno("Reset Scene", "No saved file on disk.\nReset to working default template?"):
                self.reset_working_default()
            return

        if messagebox.askyesno(
            "Revert Unsaved Changes",
            f"Discard all unsaved edits and reload '{self.current_scene_path.name}' from disk?"
        ):
            self.load_scene_file(self.current_scene_path)
            self.status_bar.config(text=f"Reverted to disk file: {self.current_scene_path.name}")

    # --------------------------------------------------------------------------
    # 2D SPATIAL RADAR
    # --------------------------------------------------------------------------
    def draw_spatial_radar(self):
        """Draws top-down (X-Z plane) positions of cameras, lights, and objects."""
        c = self.radar_canvas
        c.delete("all")
        w = c.winfo_width() or 400
        h = c.winfo_height() or 150

        cx, cy = w // 2, h // 2

        # Axes
        c.create_line(0, cy, w, cy, fill="#1e2433")
        c.create_line(cx, 0, cx, h, fill="#1e2433")
        c.create_text(cx + 8, cy - 8, text="+Z (Forward)", fill="#475569", font=("Segoe UI", 7))
        c.create_text(w - 25, cy - 8, text="+X", fill="#475569", font=("Segoe UI", 7))

        scale = 3.5  # pixels per scene unit

        for elem in self.parsed_elements:
            vecs = elem.params.get("vectors", [])
            if not vecs:
                continue

            pos = vecs[0]
            px = cx + int(pos[0] * scale)
            pz = cy - int(pos[2] * scale)

            is_sel = (self.selected_element == elem)
            outline_col = "#ffffff" if is_sel else ""

            if elem.kind == "camera":
                c.create_polygon(px, pz - 8, px - 6, pz + 6, px + 6, pz + 6, fill="#38bdf8", outline=outline_col or "#ffffff")
                c.create_text(px + 8, pz, text="Cam", fill="#38bdf8", font=("Segoe UI", 7, "bold"))
                if len(vecs) > 1:
                    look = vecs[1]
                    lx = cx + int(look[0] * scale)
                    lz = cy - int(look[2] * scale)
                    c.create_line(px, pz, lx, lz, fill="#38bdf8", dash=(2, 2))

            elif elem.kind == "light_source":
                c.create_oval(px - 5, pz - 5, px + 5, pz + 5, fill="#facc15", outline=outline_col or "#ffffff")
                c.create_text(px + 7, pz, text="Light", fill="#facc15", font=("Segoe UI", 7))

            else:
                rad_px = max(4, int(elem.params.get("radius", 1.0) * scale))
                c.create_oval(px - rad_px, pz - rad_px, px + rad_px, pz + rad_px, fill="#a855f7", outline=outline_col)
                label_txt = elem.name.split()[0]
                c.create_text(px, pz, text=label_txt[:3], fill="#ffffff", font=("Segoe UI", 6))

    # --------------------------------------------------------------------------
    # FAST RAY-TRACED PREVIEW
    # --------------------------------------------------------------------------
    def on_render_preview(self):
        if self.is_rendering_preview:
            self._render_pending = True
            return

        source = self.code_text.get("1.0", tk.END).strip()
        if not source:
            messagebox.showwarning("Empty Scene", "Scene code is empty.")
            return

        res_str = self.preview_res_var.get().split()[0]
        try:
            pw, ph = map(int, res_str.split("x"))
        except Exception:
            pw, ph = 320, 240

        self.is_rendering_preview = True
        self.status_bar.config(text=f"Rendering {pw}x{ph} preview with POV-Ray...")
        self.render_time_label.config(text="Rendering...", fg="#facc15")

        t_start = time.time()

        def worker():
            img, err_msg = run_povray_preview(
                source, width=pw, height=ph,
                working_dir=LOCAL_SRC_DIR
            )
            elapsed = time.time() - t_start

            def on_done():
                self.is_rendering_preview = False
                if img is not None:
                    self.display_preview_image(img)
                    self.render_time_label.config(text=f"Render: {elapsed:.2f}s ({pw}x{ph})", fg="#38bdf8")
                    self.status_bar.config(text=f"Preview completed in {elapsed:.2f}s.")
                    self.error_frame.pack_forget()
                else:
                    self.render_time_label.config(text="Render Failed ⚠️", fg="#ef4444")
                    self.status_bar.config(text="POV-Ray render failed. See error banner below.")
                    self.error_label.config(text=f"POV-Ray Error:\n{err_msg}")
                    self.error_frame.pack(fill=tk.X, padx=8, pady=4)

                # If another render was queued during execution, fire it now
                if getattr(self, "_render_pending", False):
                    self._render_pending = False
                    self.after(50, self.on_render_preview)

            self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def display_preview_image(self, img: Image.Image):
        cw = self.preview_canvas.winfo_width() or 380
        ch = self.preview_canvas.winfo_height() or 280

        scale = min(cw / img.width, ch / img.height)
        dw = max(1, int(img.width * scale))
        dh = max(1, int(img.height * scale))

        disp = img.resize((dw, dh), Image.Resampling.BILINEAR)
        self._preview_photo = ImageTk.PhotoImage(disp)

        self.preview_canvas.delete("all")
        cx = (cw - dw) // 2
        cy = (ch - dh) // 2
        self.preview_canvas.create_image(cx, cy, anchor="nw", image=self._preview_photo)

    # --------------------------------------------------------------------------
    # FILE OPERATIONS (LOCAL SRC DIRECTORY PRIORITY)
    # --------------------------------------------------------------------------
    def load_scene_file(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", text)
            self.current_scene_path = path
            self.scene_title_label.config(text=f"{path.name} ({path.parent.name})")
            self.status_bar.config(text=f"Loaded: {path}")
            self.parse_and_populate_tree()
            self.on_render_preview()
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not read scene file:\n{exc}")

    def on_open_file(self):
        init_dir = str(self.current_scene_path.parent) if (self.current_scene_path and self.current_scene_path.parent.exists()) else str(LOCAL_SRC_DIR)
        chosen = filedialog.askopenfilename(
            initialdir=init_dir,
            title="Open POV-Ray Scene",
            filetypes=[("POV-Ray Scenes", "*.pov;*.inc"), ("All Files", "*.*")]
        )
        if chosen:
            self.load_scene_file(Path(chosen).resolve())

    def on_save_file(self):
        if self.current_scene_path:
            try:
                self.current_scene_path.write_text(self.code_text.get("1.0", tk.END), encoding="utf-8")
                self.status_bar.config(text=f"Saved: {self.current_scene_path}")
                messagebox.showinfo("Saved", f"Scene saved to:\n{self.current_scene_path}")
            except Exception as exc:
                messagebox.showerror("Save Error", str(exc))
        else:
            self.on_save_as_file()

    def on_save_as_file(self):
        init_dir = str(LOCAL_SRC_DIR)
        chosen = filedialog.asksaveasfilename(
            initialdir=init_dir,
            title="Save POV-Ray Scene As",
            defaultextension=".pov",
            filetypes=[("POV-Ray Scene", "*.pov"), ("All Files", "*.*")]
        )
        if chosen:
            self.current_scene_path = Path(chosen).resolve()
            self.on_save_file()
            self.scene_title_label.config(text=f"{self.current_scene_path.name} ({self.current_scene_path.parent.name})")

    def on_spawn_official_gui(self):
        """Spawns the official POV-Ray 3.7 Windows GUI Editor (pvengine64.exe)."""
        pvengine_path = r"C:\Program Files\POV-Ray\v3.7\bin\pvengine64.exe"
        cmd = [pvengine_path]
        if self.current_scene_path and self.current_scene_path.is_file():
            cmd.append(str(self.current_scene_path))
        try:
            subprocess.Popen(cmd)
            self.status_bar.config(text="Launched official POV-Ray 3.7 Windows GUI Editor.")
        except Exception as exc:
            messagebox.showerror("POV-Ray Launch Error", f"Could not launch POV-Ray GUI:\n{exc}")

    def on_apply_to_main(self):
        """Sends active editor text to main tkray_tracer for rendering WITHOUT overwriting the original .pov file on disk."""
        target_dir = self.current_scene_path.parent if (self.current_scene_path and self.current_scene_path.parent.exists()) else LOCAL_SRC_DIR
        active_draft = target_dir / "__active_frame.pov"
        try:
            active_draft.write_text(self.code_text.get("1.0", tk.END), encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Export Error", f"Could not write active draft frame:\n{exc}")
            return

        if self.on_scene_applied:
            self.on_scene_applied(active_draft)
            orig_name = self.current_scene_path.name if self.current_scene_path else "Unsaved Scene"
            messagebox.showinfo(
                "Scene Sent to Main Tracer",
                f"Active scene sent to tkray_tracer as live render frame:\n{active_draft.name}\n\n"
                f"Note: Your source file '{orig_name}' remains untouched on disk until you explicitly click [Save .pov]!"
            )
            self.status_bar.config(text=f"Sent active frame to Main Tracer ({active_draft.name}). Source file untouched.")

    def new_scene_template(self):
        self.reset_working_default()

    def reset_working_default(self):
        """Resets the editor to a guaranteed working POV-Ray scene and immediately renders preview."""
        template = (
            '#version 3.7;\n'
            'global_settings { assumed_gamma 1.0 }\n'
            '#include "colors.inc"\n\n'
            '// Camera\n'
            'camera {\n'
            '    location <0.0, 1.5, -4.0>\n'
            '    look_at  <0.0, 1.0,  0.0>\n'
            '    angle 65.0\n'
            '}\n\n'
            '// Key Light Source\n'
            'light_source {\n'
            '    <5.0, 10.0, -5.0>\n'
            '    color rgb <1.0, 0.98, 0.95>\n'
            '}\n\n'
            '// Checkered Floor Plane\n'
            'plane {\n'
            '    y, 0\n'
            '    pigment { checker color rgb <0.12, 0.12, 0.18> color rgb <0.82, 0.82, 0.88> scale 1.0 }\n'
            '    finish { diffuse 0.8 ambient 0.1 }\n'
            '}\n\n'
            '// Primary Subject Sphere\n'
            'sphere {\n'
            '    <0.0, 1.0, 0.0>, 1.0\n'
            '    pigment { color rgb <0.9, 0.2, 0.2> }\n'
            '    finish { diffuse 0.7 specular 0.4 roughness 0.05 reflection 0.2 }\n'
            '}\n'
        )
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", template)
        self.current_scene_path = LOCAL_SRC_DIR / "default_scene.pov"
        self.scene_title_label.config(text=f"default_scene.pov ({LOCAL_SRC_DIR.name})")
        self.object_insert_count = 0
        self.error_frame.pack_forget()
        self.parse_and_populate_tree()
        self.on_render_preview()

    def insert_code_snippet(self, snippet: str):
        self.code_text.insert(tk.INSERT, "\n" + snippet + "\n")
        self.parse_and_populate_tree()
        self.on_render_preview()

    # --------------------------------------------------------------------------
    # SNIPPET TEMPLATES (WITH SMART AUTO-OFFSET FOR MULTIPLE OBJECTS)
    # --------------------------------------------------------------------------
    def _snippet_sphere(self) -> str:
        self.object_insert_count += 1
        # Offset X: 0, 2.5, -2.5, 5.0, -5.0
        offset_x = (self.object_insert_count // 2) * 2.5 * (1 if self.object_insert_count % 2 != 0 else -1)
        colors = [
            "<0.2, 0.6, 0.9>",   # Azure
            "<0.9, 0.3, 0.2>",   # Ruby
            "<0.2, 0.85, 0.4>",  # Emerald
            "<0.95, 0.8, 0.2>",  # Gold
            "<0.8, 0.3, 0.9>",   # Purple
        ]
        col = colors[self.object_insert_count % len(colors)]
        return (
            f"// Sphere #{self.object_insert_count + 1}\n"
            "sphere {\n"
            f"    <{offset_x:.2f}, 1.0, 0.0>, 1.0\n"
            f"    pigment {{ color rgb {col} }}\n"
            "    finish { ambient 0.1 diffuse 0.8 specular 0.5 roughness 0.03 }\n"
            "}"
        )

    def _snippet_box(self) -> str:
        self.object_insert_count += 1
        offset_x = (self.object_insert_count // 2) * 2.8 * (1 if self.object_insert_count % 2 != 0 else -1)
        return (
            f"// Box #{self.object_insert_count + 1}\n"
            "box {\n"
            "    <-1.0, 0.0, -1.0>, <1.0, 2.0, 1.0>\n"
            f"    translate <{offset_x:.2f}, 0.0, 0.0>\n"
            "    pigment { color rgb <0.85, 0.55, 0.2> }\n"
            "    finish { ambient 0.1 diffuse 0.85 specular 0.2 }\n"
            "}"
        )

    def _snippet_cylinder(self) -> str:
        self.object_insert_count += 1
        offset_x = (self.object_insert_count // 2) * 2.5 * (1 if self.object_insert_count % 2 != 0 else -1)
        return (
            f"// Cylinder #{self.object_insert_count + 1}\n"
            "cylinder {\n"
            "    <0.0, 0.0, 0.0>, <0.0, 2.5, 0.0>, 0.8\n"
            f"    translate <{offset_x:.2f}, 0.0, 0.0>\n"
            "    pigment { color rgb <0.3, 0.8, 0.4> }\n"
            "    finish { ambient 0.1 diffuse 0.8 specular 0.3 }\n"
            "}"
        )

    def _snippet_plane(self) -> str:
        return (
            "plane {\n"
            "    y, 0\n"
            "    pigment { checker color rgb <0.15, 0.15, 0.18> color rgb <0.75, 0.75, 0.8> scale 1.5 }\n"
            "    finish { ambient 0.1 diffuse 0.8 reflection 0.1 }\n"
            "}"
        )

    def _snippet_torus(self) -> str:
        self.object_insert_count += 1
        offset_x = (self.object_insert_count // 2) * 3.0 * (1 if self.object_insert_count % 2 != 0 else -1)
        return (
            f"// Torus #{self.object_insert_count + 1}\n"
            "torus {\n"
            "    1.5, 0.4\n"
            "    rotate <45, 0, 0>\n"
            f"    translate <{offset_x:.2f}, 1.5, 0>\n"
            "    pigment { color rgb <0.95, 0.8, 0.2> }\n"
            "    finish { ambient 0.1 diffuse 0.8 specular 0.8 roughness 0.02 }\n"
            "}"
        )

    def _snippet_cone(self) -> str:
        self.object_insert_count += 1
        offset_x = (self.object_insert_count // 2) * 2.5 * (1 if self.object_insert_count % 2 != 0 else -1)
        return (
            f"// Cone #{self.object_insert_count + 1}\n"
            "cone {\n"
            "    <0.0, 0.0, 0.0>, 1.2, <0.0, 2.5, 0.0>, 0.0\n"
            f"    translate <{offset_x:.2f}, 0.0, 0.0>\n"
            "    pigment { color rgb <0.9, 0.3, 0.3> }\n"
            "    finish { ambient 0.1 diffuse 0.8 }\n"
            "}"
        )

    def _snippet_tunnel(self) -> str:
        return (
            "// Continuous 100-Yard Textured Tunnel Section\n"
            "cylinder {\n"
            "    <0, 0, 0>, <0, 100, 0>, 3.5\n"
            "    open hollow\n"
            "    texture {\n"
            "        pigment {\n"
            "            image_map { jpeg \"section1.jpg\" map_type 2 interpolate 2 }\n"
            "            scale <-1, 100, 1>\n"
            "            rotate <0, 90, 0>\n"
            "        }\n"
            "        finish { ambient 0.15 diffuse 0.85 specular 0.2 }\n"
            "    }\n"
            "    rotate <90, 0, 0>\n"
            "    translate <0, 0, 0>\n"
            "}"
        )

    def _snippet_chrome(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgb <0.95, 0.95, 0.98> }\n"
            "    finish {\n"
            "        ambient 0.05 diffuse 0.1\n"
            "        reflection 0.92 metallic 0.8\n"
            "        specular 1.0 roughness 0.005\n"
            "    }\n"
            "}"
        )

    def _snippet_glass(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgbf <0.98, 0.98, 1.0, 0.9> }\n"
            "    finish { ambient 0.05 diffuse 0.1 reflection 0.15 specular 0.9 roughness 0.01 }\n"
            "}\n"
            "interior { ior 1.5 }"
        )

    def _snippet_gold(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgb <1.0, 0.84, 0.0> }\n"
            "    finish { ambient 0.1 diffuse 0.5 reflection 0.75 metallic 0.8 specular 0.85 roughness 0.02 }\n"
            "}"
        )

    def _snippet_brushed_metal(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgb <0.75, 0.78, 0.82> }\n"
            "    finish { ambient 0.1 diffuse 0.6 reflection 0.35 roughness 0.08 metallic 0.7 }\n"
            "}"
        )

    def _snippet_red_plastic(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgb <0.9, 0.15, 0.15> }\n"
            "    finish { ambient 0.1 diffuse 0.7 specular 0.6 roughness 0.02 reflection 0.15 }\n"
            "}"
        )

    def _snippet_emerald(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgbf <0.2, 0.85, 0.4, 0.8> }\n"
            "    finish { ambient 0.08 diffuse 0.2 reflection 0.25 specular 0.9 roughness 0.01 }\n"
            "}\n"
            "interior { ior 1.58 }"
        )

    def _snippet_emissive_light(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgb <0.3, 0.8, 1.0> }\n"
            "    finish { ambient 2.5 diffuse 0.0 }\n"
            "}"
        )

    def _snippet_checkerboard(self) -> str:
        return (
            "texture {\n"
            "    pigment { checker color rgb <0.1, 0.1, 0.1> color rgb <0.9, 0.9, 0.9> scale 1.0 }\n"
            "    finish { ambient 0.1 diffuse 0.85 }\n"
            "}"
        )

    def _snippet_earth_map(self) -> str:
        return (
            "texture {\n"
            "    pigment {\n"
            '        image_map { jpeg "earthmap.jpg" map_type 1 interpolate 2 }\n'
            "    }\n"
            "    finish { ambient 0.1 diffuse 0.85 specular 0.2 roughness 0.05 }\n"
            "}"
        )

    def _snippet_astral_map(self) -> str:
        return (
            "texture {\n"
            "    pigment {\n"
            '        image_map { jpeg "section1.jpg" map_type 2 interpolate 2 }\n'
            "        scale <-1, 50, 1>\n"
            "    }\n"
            "    finish { ambient 0.25 diffuse 0.75 specular 0.2 }\n"
            "}"
        )

    def on_pick_custom_image_map(self):
        chosen = filedialog.askopenfilename(
            initialdir=str(LOCAL_SRC_DIR),
            title="Select Texture Image File",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tga"), ("All Files", "*.*")]
        )
        if chosen:
            src_path = Path(chosen)
            dest_path = LOCAL_SRC_DIR / src_path.name
            if not dest_path.exists() and src_path.is_file():
                try:
                    import shutil
                    shutil.copy2(src_path, dest_path)
                except Exception:
                    pass
            fname = src_path.name
            ext = src_path.suffix.lower()
            img_format = "png" if ext == ".png" else "jpeg"
            snippet = (
                "texture {\n"
                f"    pigment {{\n"
                f'        image_map {{ {img_format} "{fname}" map_type 1 interpolate 2 }}\n'
                f"        scale 1.0\n"
                f"    }}\n"
                f"    finish {{ ambient 0.15 diffuse 0.85 specular 0.2 }}\n"
                "}"
            )
            self.apply_material_to_element(snippet, mat_name=f"Image ({fname})")

    def _snippet_tunnel_camera(self) -> str:
        return (
            "camera {\n"
            "    perspective\n"
            "    location <0.0, 0.0, 0.0>\n"
            "    look_at  <0.0, 0.0, 100.0>\n"
            "    angle 65.0\n"
            "}"
        )

    def _snippet_walking_camera(self) -> str:
        return (
            "camera {\n"
            "    perspective\n"
            "    location <0.0, 1.7, -5.0>\n"
            "    look_at  <0.0, 1.5,  0.0>\n"
            "    angle 60.0\n"
            "}"
        )

    def _snippet_isometric_camera(self) -> str:
        return (
            "camera {\n"
            "    perspective\n"
            "    location <6.0, 8.0, -8.0>\n"
            "    look_at  <0.0, 1.0,  0.0>\n"
            "    angle 45.0\n"
            "}"
        )

    def _snippet_3point_lights(self) -> str:
        return (
            "// Key Light (Warm, Primary)\n"
            "light_source { <6.0, 8.0, -6.0>, color rgb <1.0, 0.95, 0.88> * 1.2 }\n"
            "// Fill Light (Cool, Soft)\n"
            "light_source { <-6.0, 4.0, -4.0>, color rgb <0.7, 0.8, 1.0> * 0.5 shadowless }\n"
            "// Rim Light (Backlight)\n"
            "light_source { <0.0, 6.0, 8.0>, color rgb <1.0, 1.0, 1.0> * 0.8 }\n"
        )

    def _snippet_overhead_tunnel_lights(self) -> str:
        return (
            "#for (ZPos, 10.0, 90.0, 15.0)\n"
            "    light_source {\n"
            "        <0.0, 3.2, ZPos>, color rgb <1.0, 0.98, 0.92> * 1.1\n"
            "        fade_distance 15.0 fade_power 2 shadowless\n"
            "    }\n"
            "    cylinder { <0, 3.2, ZPos-0.5>, <0, 3.2, ZPos+0.5>, 0.08 pigment { color rgb <1, 1, 1> } finish { ambient 1.5 } no_shadow }\n"
            "#end\n"
        )
