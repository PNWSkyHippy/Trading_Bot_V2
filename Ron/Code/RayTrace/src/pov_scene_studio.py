"""POV-Ray Scene Studio & Visual Builder for tkray_tracer.

Mimics the POV-Ray 3.7 Windows GUI front-end and scene editor:
- Load, edit, and save .pov and .inc scene files
- Visual Scene Explorer / Parser: Inspect cameras, lights, primitives, textures, and finishes
- Element Palette & Inserter: Pick and insert objects (spheres, boxes, cylinders, tunnels),
  materials (cosmic, glass, chrome, metal, brick, image_maps), and lighting rigs
- Fast Live Ray-Traced Preview: One-click render at configurable draft/production resolutions
- Spatial Top-Down Radar / Wireframe View: Visualizes camera, lights, and object placements
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

# Determine POV-Ray runner command (WSL or Windows native)
IS_WINDOWS = os.name == "nt"


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
) -> Optional[Image.Image]:
    """Renders a fast draft preview frame of the scene using POV-Ray."""
    working_dir = working_dir or Path(__file__).resolve().parent
    with tempfile.NamedTemporaryFile("w", suffix=".pov", delete=False, dir=str(working_dir), encoding="utf-8") as tf:
        tf.write(scene_text)
        temp_pov_path = Path(tf.name)

    temp_png_path = temp_pov_path.with_suffix(".png")

    try:
        if IS_WINDOWS:
            wsl_pov = _windows_to_wsl_path(temp_pov_path)
            wsl_png = _windows_to_wsl_path(temp_png_path)
            wsl_work = _windows_to_wsl_path(working_dir)
            cmd = [
                "wsl",
                "--cd", wsl_work,
                "povray",
                f"+I{temp_pov_path.name}",
                f"+W{width}",
                f"+H{height}",
                f"+O{temp_png_path.name}",
                "+Q5",      # Fast draft quality
                "-D",       # Disable interactive display window
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

        proc = subprocess.run(cmd, cwd=str(working_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if temp_png_path.exists() and temp_png_path.stat().st_size > 0:
            img = Image.open(temp_png_path).convert("RGB")
            return img
    except Exception as exc:
        print(f"POV-Ray preview error: {exc}")
    finally:
        # Clean up temporary files
        try:
            if temp_pov_path.exists():
                temp_pov_path.unlink()
            if temp_png_path.exists():
                temp_png_path.unlink()
        except Exception:
            pass

    return None


# ==============================================================================
# SCENE PARSER & ELEMENT MODELS
# ==============================================================================

@dataclass
class SceneElement:
    kind: str           # "camera", "light_source", "sphere", "box", "cylinder", "plane", "texture", "union"
    name: str
    line_start: int
    raw_text: str
    params: Dict[str, Any] = field(default_factory=dict)


class PovSceneParser:
    """Extracts cameras, lights, objects, and textures from POV-Ray source code."""

    @staticmethod
    def parse(source: str) -> List[SceneElement]:
        elements: List[SceneElement] = []
        lines = source.splitlines()

        # Regular expressions for primary blocks
        block_patterns = [
            ("camera", r"\bcamera\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("light_source", r"\blight_source\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("sphere", r"\bsphere\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("box", r"\bbox\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("cylinder", r"\bcylinder\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("plane", r"\bplane\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("torus", r"\btorus\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("disc", r"\bdisc\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
            ("texture", r"\btexture\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"),
        ]

        for kind, pat in block_patterns:
            for match in re.finditer(pat, source, re.DOTALL | re.IGNORECASE):
                raw = match.group(0)
                body = match.group(1)
                start_line = source[: match.start()].count("\n") + 1

                name = f"{kind.capitalize()} @ L{start_line}"
                params: Dict[str, Any] = {}

                # Extract vectors <x, y, z>
                vecs = re.findall(r"<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", body)
                if vecs:
                    params["vectors"] = [[float(v[0]), float(v[1]), float(v[2])] for v in vecs]

                # Extract color
                col = re.search(r"color\s+rgb\s*<\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*>", body, re.IGNORECASE)
                if col:
                    params["color"] = [float(col.group(1)), float(col.group(2)), float(col.group(3))]

                # Extract radius / numbers
                nums = re.findall(r"\b([-0-9.]+)\b", body)
                if nums:
                    params["numbers"] = [float(n) for n in nums if n.replace(".", "", 1).replace("-", "", 1).isdigit()][:4]

                # Image map file if present
                img_map = re.search(r'image_map\s*\{\s*(?:jpeg|png|tga|sys)\s*["\']([^"\']+)["\']', body, re.IGNORECASE)
                if img_map:
                    params["image_map"] = img_map.group(1)
                    name = f"Texture ({os.path.basename(img_map.group(1))})"

                elements.append(
                    SceneElement(
                        kind=kind,
                        name=name,
                        line_start=start_line,
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
    """POV-Ray Scene Editor, Material/Object Builder, and Quick Previewer."""

    def __init__(
        self,
        parent: tk.Tk,
        initial_scene_path: Optional[Path] = None,
        on_scene_applied: Optional[Callable[[Path], None]] = None,
    ):
        super().__init__(parent)
        self.title("🏰 POV-Ray 3.7 Scene Studio & Visual Builder")
        self.geometry("1420x900")
        self.minsize(1100, 720)
        self.configure(bg="#181a20")

        self.current_scene_path: Optional[Path] = initial_scene_path
        self.on_scene_applied = on_scene_applied
        self.parsed_elements: List[SceneElement] = []
        self._preview_photo: Optional[ImageTk.PhotoImage] = None
        self.is_rendering_preview: bool = False

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
        # 1. Top Ribbon Menu / Controls
        ribbon = tk.Frame(self, bg="#232733", height=42)
        ribbon.pack(side=tk.TOP, fill=tk.X)

        rbtn = {
            "bg": "#32384a", "fg": "#f1f5f9", "activebackground": "#434b63",
            "activeforeground": "#ffffff", "relief": tk.FLAT, "padx": 10, "pady": 4, "font": ("Segoe UI", 9)
        }

        tk.Button(ribbon, text="📄 New Scene", command=self.new_scene_template, **rbtn).pack(side=tk.LEFT, padx=4, pady=5)
        tk.Button(ribbon, text="📂 Open .pov", command=self.on_open_file, **rbtn).pack(side=tk.LEFT, padx=4, pady=5)
        tk.Button(ribbon, text="💾 Save .pov", command=self.on_save_file, **rbtn).pack(side=tk.LEFT, padx=4, pady=5)
        tk.Button(ribbon, text="💾 Save As...", command=self.on_save_as_file, **rbtn).pack(side=tk.LEFT, padx=4, pady=5)
        tk.Button(ribbon, text="🚀 Official GUI", command=self.on_spawn_official_gui, **rbtn).pack(side=tk.LEFT, padx=4, pady=5)

        tk.Label(ribbon, text="|", bg="#232733", fg="#475569").pack(side=tk.LEFT, padx=8)

        # Quick Render Preview Trigger Button (Prominent)
        render_btn = tk.Button(
            ribbon, text="⚡ RENDER PREVIEW [F9]",
            command=self.on_render_preview,
            bg="#059669", fg="#ffffff", activebackground="#047857",
            relief=tk.FLAT, padx=14, pady=4, font=("Segoe UI", 9, "bold")
        )
        render_btn.pack(side=tk.LEFT, padx=4, pady=5)

        tk.Label(ribbon, text="Resolution:", bg="#232733", fg="#94a3b8", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(12, 4))
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
            ribbon, text="Untitled.pov", bg="#232733", fg="#38bdf8", font=("Segoe UI", 10, "bold")
        )
        self.scene_title_label.pack(side=tk.RIGHT, padx=15)

        # 2. Main Paned Workspace
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#13151b", sashrelief=tk.RAISED, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # Left Panel: Scene Explorer & Insert Palette Notebook
        left_panel = tk.Frame(main_paned, bg="#1a1d26", width=380)
        main_paned.add(left_panel, minsize=320)
        self._build_left_panel(left_panel)

        # Middle Panel: POV-Ray Code Editor
        center_panel = tk.Frame(main_paned, bg="#13151b")
        main_paned.add(center_panel, minsize=420)
        self._build_code_editor(center_panel)

        # Right Panel: Live Preview & 2D Spatial Radar
        right_panel = tk.Frame(main_paned, bg="#1a1d26", width=460)
        main_paned.add(right_panel, minsize=380)
        self._build_preview_panel(right_panel)

        # 3. Bottom Status Bar
        self.status_bar = tk.Label(
            self, text="Ready. Press F9 to render quick preview.", bg="#0f1117", fg="#94a3b8",
            anchor="w", padx=10, pady=3, font=("Segoe UI", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_left_panel(self, parent: tk.Frame):
        """Constructs Scene Explorer tree and Insert Palettes (Objects, Textures, Cameras)."""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 1: Scene Explorer (Hierarchy)
        explorer_tab = tk.Frame(notebook, bg="#1a1d26")
        notebook.add(explorer_tab, text="🔍 Scene Explorer")

        tk.Label(explorer_tab, text="PARSED SCENE ELEMENTS:", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))

        tree_frame = tk.Frame(explorer_tab, bg="#1a1d26")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.scene_tree = ttk.Treeview(tree_frame, columns=("kind", "line"), show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.scene_tree.yview)
        self.scene_tree.configure(yscrollcommand=tree_scroll.set)
        self.scene_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.scene_tree.bind("<<TreeviewSelect>>", self.on_tree_element_selected)
        self.scene_tree.bind("<Double-1>", self.on_tree_element_double_click)

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

    def _build_objects_palette(self, parent: tk.Frame):
        tk.Label(parent, text="CLICK TO INSERT PRIMITIVE:", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        pbtn = {"bg": "#2a2f3f", "fg": "#f8fafc", "relief": tk.FLAT, "anchor": "w", "padx": 10, "pady": 4}

        primitives = [
            ("🔮 Sphere", self._snippet_sphere),
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
        tk.Label(parent, text="PICK & INSERT MATERIAL / TEXTURE:", bg="#1a1d26", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        pbtn = {"bg": "#2a2f3f", "fg": "#f8fafc", "relief": tk.FLAT, "anchor": "w", "padx": 10, "pady": 4}

        textures = [
            ("🌌 Astral Nebula Image Map", self._snippet_astral_map),
            ("🪞 Perfect Chrome / Mirror", self._snippet_chrome),
            ("💎 Optical Glass (IOR 1.5)", self._snippet_glass),
            ("🔘 Brushed Metal / Steel", self._snippet_brushed_metal),
            ("🟡 Emissive Luminaire Neon Glow", self._snippet_emissive_light),
            ("🏁 Checkerboard Pattern", self._snippet_checkerboard),
            ("🖼 Custom Image File Texture...", self.on_pick_custom_image_map),
        ]
        for label, fn in textures:
            tk.Button(parent, text=label, command=lambda f=fn: self.insert_code_snippet(f()), **pbtn).pack(fill=tk.X, padx=8, pady=3)

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

    def _build_preview_panel(self, parent: tk.Frame):
        """Live Preview Canvas and 2D Spatial Overview."""
        p_header = tk.Frame(parent, bg="#1a1d26", height=28)
        p_header.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(p_header, text="RAY-TRACED PREVIEW", bg="#1a1d26", fg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.render_time_label = tk.Label(p_header, text="Time: ---", bg="#1a1d26", fg="#38bdf8", font=("Consolas", 9))
        self.render_time_label.pack(side=tk.RIGHT)

        # Preview Canvas
        self.preview_canvas = tk.Canvas(parent, bg="#0b0d11", highlightthickness=1, highlightbackground="#2d3345")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        self.preview_canvas.create_text(200, 150, text="Press F9 to render quick preview.", fill="#475569", font=("Segoe UI", 10))

        # Bottom 2D Spatial Radar / Top-Down View
        radar_header = tk.Frame(parent, bg="#1a1d26", height=24)
        radar_header.pack(fill=tk.X, padx=8, pady=(4, 2))
        tk.Label(radar_header, text="📍 2D TOP-DOWN SCENE RADAR", bg="#1a1d26", fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)

        self.radar_canvas = tk.Canvas(parent, bg="#090a0f", height=160, highlightthickness=1, highlightbackground="#2d3345")
        self.radar_canvas.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.draw_spatial_radar()

    def _bind_shortcuts(self):
        self.bind("<F9>", lambda e: self.on_render_preview())
        self.bind("<Control-s>", lambda e: self.on_save_file())
        self.bind("<Control-o>", lambda e: self.on_open_file())

    # --------------------------------------------------------------------------
    # SCENE PARSING & EXPLORER TREE
    # --------------------------------------------------------------------------
    def parse_and_populate_tree(self):
        source = self.code_text.get("1.0", tk.END)
        self.parsed_elements = PovSceneParser.parse(source)

        self.scene_tree.delete(*self.scene_tree.get_children())

        cats = {
            "camera": self.scene_tree.insert("", "end", text="📷 Cameras", open=True),
            "light_source": self.scene_tree.insert("", "end", text="💡 Lights", open=True),
            "objects": self.scene_tree.insert("", "end", text="🔷 Objects & Geometry", open=True),
            "textures": self.scene_tree.insert("", "end", text="🎨 Textures & Materials", open=True),
        }

        for elem in self.parsed_elements:
            if elem.kind == "camera":
                parent = cats["camera"]
            elif elem.kind == "light_source":
                parent = cats["light_source"]
            elif elem.kind == "texture":
                parent = cats["textures"]
            else:
                parent = cats["objects"]

            self.scene_tree.insert(parent, "end", text=elem.name, values=(elem.kind, elem.line_start))

        self.draw_spatial_radar()

    def on_tree_element_selected(self, event):
        sel = self.scene_tree.selection()
        if not sel:
            return
        vals = self.scene_tree.item(sel[0], "values")
        if vals and len(vals) >= 2:
            line_no = int(vals[1])
            self.code_text.see(f"{line_no}.0")
            self.code_text.tag_remove("highlight", "1.0", tk.END)
            self.code_text.tag_add("highlight", f"{line_no}.0", f"{line_no + 1}.0")
            self.code_text.tag_config("highlight", background="#2a3f68")

    def on_tree_element_double_click(self, event):
        self.on_tree_element_selected(event)

    def _on_code_modified(self):
        # Debounced re-parse
        if hasattr(self, "_reparse_timer") and self._reparse_timer:
            self.after_cancel(self._reparse_timer)
        self._reparse_timer = self.after(1500, self.parse_and_populate_tree)

    # --------------------------------------------------------------------------
    # 2D SPATIAL RADAR
    # --------------------------------------------------------------------------
    def draw_spatial_radar(self):
        """Draws top-down (X-Z plane) positions of cameras, lights, and objects."""
        c = self.radar_canvas
        c.delete("all")
        w = c.winfo_width() or 400
        h = c.winfo_height() or 160

        cx, cy = w // 2, h // 2

        # Draw grid axes
        c.create_line(0, cy, w, cy, fill="#1e2433")
        c.create_line(cx, 0, cx, h, fill="#1e2433")
        c.create_text(cx + 8, cy - 8, text="+Z forward", fill="#334155", font=("Segoe UI", 7))
        c.create_text(w - 25, cy - 8, text="+X", fill="#334155", font=("Segoe UI", 7))

        scale = 3.5  # pixels per scene unit

        for elem in self.parsed_elements:
            vecs = elem.params.get("vectors", [])
            if not vecs:
                continue

            # Position on X-Z plane
            pos = vecs[0]
            px = cx + int(pos[0] * scale)
            pz = cy - int(pos[2] * scale)  # -Z goes upwards on radar

            if elem.kind == "camera":
                c.create_polygon(px, pz - 7, px - 6, pz + 6, px + 6, pz + 6, fill="#38bdf8", outline="#ffffff")
                c.create_text(px + 8, pz, text="Cam", fill="#38bdf8", font=("Segoe UI", 7, "bold"))
                if len(vecs) > 1:
                    look = vecs[1]
                    lx = cx + int(look[0] * scale)
                    lz = cy - int(look[2] * scale)
                    c.create_line(px, pz, lx, lz, fill="#38bdf8", dash=(2, 2))

            elif elem.kind == "light_source":
                c.create_oval(px - 4, pz - 4, px + 4, pz + 4, fill="#facc15", outline="#ffffff")
                c.create_text(px + 6, pz, text="Light", fill="#facc15", font=("Segoe UI", 7))

            else:
                c.create_rectangle(px - 3, pz - 3, px + 3, pz + 3, fill="#a855f7", outline="")

    # --------------------------------------------------------------------------
    # FAST RAY-TRACED PREVIEW
    # --------------------------------------------------------------------------
    def on_render_preview(self):
        if self.is_rendering_preview:
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
        self.render_time_label.config(text="Rendering...")

        t_start = time.time()

        def worker():
            img = run_povray_preview(
                source, width=pw, height=ph,
                working_dir=self.current_scene_path.parent if self.current_scene_path else None
            )
            elapsed = time.time() - t_start

            def on_done():
                self.is_rendering_preview = False
                if img is not None:
                    self.display_preview_image(img)
                    self.render_time_label.config(text=f"Render: {elapsed:.2f}s ({pw}x{ph})")
                    self.status_bar.config(text=f"Preview completed in {elapsed:.2f} seconds.")
                else:
                    self.render_time_label.config(text="Render Failed")
                    self.status_bar.config(text="POV-Ray render failed. Check scene syntax.")

            self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def display_preview_image(self, img: Image.Image):
        cw = self.preview_canvas.winfo_width() or 380
        ch = self.preview_canvas.winfo_height() or 280

        # Scale image keeping aspect ratio
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
    # FILE OPERATIONS
    # --------------------------------------------------------------------------
    def load_scene_file(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", text)
            self.current_scene_path = path
            self.scene_title_label.config(text=path.name)
            self.status_bar.config(text=f"Loaded: {path}")
            self.parse_and_populate_tree()
            self.on_render_preview()
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not read scene file:\n{exc}")

    def on_open_file(self):
        chosen = filedialog.askopenfilename(
            title="Open POV-Ray Scene",
            filetypes=[("POV-Ray Scenes", "*.pov;*.inc"), ("All Files", "*.*")]
        )
        if chosen:
            self.load_scene_file(Path(chosen).resolve())

    def on_save_file(self):
        if self.current_scene_path:
            try:
                self.current_scene_path.write_text(self.code_text.get("1.0", tk.END), encoding="utf-8")
                self.status_bar.config(text=f"Saved: {self.current_scene_path.name}")
                messagebox.showinfo("Saved", f"Scene saved to {self.current_scene_path.name}")
            except Exception as exc:
                messagebox.showerror("Save Error", str(exc))
        else:
            self.on_save_as_file()

    def on_save_as_file(self):
        chosen = filedialog.asksaveasfilename(
            title="Save POV-Ray Scene As",
            defaultextension=".pov",
            filetypes=[("POV-Ray Scene", "*.pov"), ("All Files", "*.*")]
        )
        if chosen:
            self.current_scene_path = Path(chosen).resolve()
            self.on_save_file()
            self.scene_title_label.config(text=self.current_scene_path.name)

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
        """Saves active text and sets as current scene in main tkray_tracer."""
        if not self.current_scene_path:
            self.on_save_as_file()
        else:
            self.on_save_file()

        if self.current_scene_path and self.on_scene_applied:
            self.on_scene_applied(self.current_scene_path)
            messagebox.showinfo(
                "Scene Applied",
                f"Scene '{self.current_scene_path.name}' is now active in tkray_tracer for rendering!"
            )

    def new_scene_template(self):
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
            '// Light Source\n'
            'light_source {\n'
            '    <5.0, 10.0, -5.0>\n'
            '    color rgb <1.0, 0.98, 0.95>\n'
            '}\n\n'
            '// Checkered Floor Plane\n'
            'plane {\n'
            '    y, 0\n'
            '    pigment { checker color rgb <0.1, 0.1, 0.15> color rgb <0.8, 0.8, 0.85> scale 1.0 }\n'
            '    finish { diffuse 0.8 ambient 0.1 }\n'
            '}\n\n'
            '// Primary Subject Sphere\n'
            'sphere {\n'
            '    <0, 1.0, 0>, 1.0\n'
            '    pigment { color rgb <0.9, 0.2, 0.2> }\n'
            '    finish { diffuse 0.7 specular 0.4 roughness 0.05 reflection 0.2 }\n'
            '}\n'
        )
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", template)
        self.current_scene_path = None
        self.scene_title_label.config(text="Untitled.pov")
        self.parse_and_populate_tree()

    def insert_code_snippet(self, snippet: str):
        self.code_text.insert(tk.INSERT, "\n" + snippet + "\n")
        self.parse_and_populate_tree()
        self.on_render_preview()

    # --------------------------------------------------------------------------
    # SNIPPET TEMPLATES (OBJECTS, TEXTURES, CAMERAS, LIGHTS)
    # --------------------------------------------------------------------------
    def _snippet_sphere(self) -> str:
        return (
            "sphere {\n"
            "    <0.0, 1.0, 0.0>, 1.0\n"
            "    pigment { color rgb <0.2, 0.6, 0.9> }\n"
            "    finish { ambient 0.1 diffuse 0.8 specular 0.5 roughness 0.03 }\n"
            "}"
        )

    def _snippet_box(self) -> str:
        return (
            "box {\n"
            "    <-1.0, 0.0, -1.0>, <1.0, 2.0, 1.0>\n"
            "    pigment { color rgb <0.85, 0.55, 0.2> }\n"
            "    finish { ambient 0.1 diffuse 0.85 specular 0.2 }\n"
            "}"
        )

    def _snippet_cylinder(self) -> str:
        return (
            "cylinder {\n"
            "    <0.0, 0.0, 0.0>, <0.0, 3.0, 0.0>, 0.8\n"
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
        return (
            "torus {\n"
            "    1.5, 0.4\n"
            "    rotate <45, 0, 0>\n"
            "    translate <0, 1.5, 0>\n"
            "    pigment { color rgb <0.95, 0.8, 0.2> }\n"
            "    finish { ambient 0.1 diffuse 0.8 specular 0.8 roughness 0.02 }\n"
            "}"
        )

    def _snippet_cone(self) -> str:
        return (
            "cone {\n"
            "    <0, 0, 0>, 1.2, <0, 2.5, 0>, 0.0\n"
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

    def _snippet_brushed_metal(self) -> str:
        return (
            "texture {\n"
            "    pigment { color rgb <0.75, 0.78, 0.82> }\n"
            "    finish { ambient 0.1 diffuse 0.6 reflection 0.35 roughness 0.08 metallic 0.7 }\n"
            "}"
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

    def _snippet_astral_map(self) -> str:
        return (
            "texture {\n"
            "    pigment {\n"
            "        image_map { jpeg \"astral_drift.jpg\" map_type 2 interpolate 2 }\n"
            "        scale <-1, 50, 1>\n"
            "    }\n"
            "    finish { ambient 0.2 diffuse 0.8 }\n"
            "}"
        )

    def on_pick_custom_image_map(self):
        chosen = filedialog.askopenfilename(
            title="Select Texture Image File",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tga"), ("All Files", "*.*")]
        )
        if chosen:
            fname = os.path.basename(chosen)
            snippet = (
                "texture {\n"
                f"    pigment {{\n"
                f'        image_map {{ jpeg "{fname}" map_type 2 interpolate 2 }}\n'
                f"        scale <-1, 100, 1>\n"
                f"    }}\n"
                f"    finish {{ ambient 0.15 diffuse 0.85 specular 0.2 }}\n"
                "}"
            )
            self.insert_code_snippet(snippet)

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
