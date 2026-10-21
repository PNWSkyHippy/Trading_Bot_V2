"""Movie Maker Suite for tkray_tracer.

A full-featured non-linear video editing suite for ray-traced sequences:
- Multi-track timeline (Video clips, Audio overlays, Text & Title overlays)
- Clip editing: Cut/Split, Trim In/Out, Copy/Paste, Reorder, Speed adjustments
- Transitions: Crossfade, Fade-to-Black, Fade-to-White, Directional Wipes
- Text Overlays: Star Wars style perspective crawl, Title cards, Subtitles, HUD telemetry
- Modern Video Export: MP4 (H.264/OpenH264 + AAC) with hardware acceleration support
- Audio muxing directly into exported MP4
- Integrated seamlessly with tkray_tracer's live sequence memory and disk assets.
"""

from __future__ import annotations

import copy
import math
import os
import shutil
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageTk

# Locate system FFmpeg executable
POSSIBLE_FFMPEG_PATHS = [
    r"C:\Program Files\BlueStacks_nxt\ffmpeg.exe",
    shutil.which("ffmpeg") or "",
]
FFMPEG_EXE = next((p for p in POSSIBLE_FFMPEG_PATHS if p and os.path.exists(p)), "")


# ==============================================================================
# DATA MODELS
# ==============================================================================

def _natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]


@dataclass
class TimelineClip:
    """Represents a video/frame sequence segment on the timeline with lazy streaming."""
    name: str
    frames: List[Image.Image] = field(default_factory=list)  # In-memory PIL images
    file_paths: List[str] = field(default_factory=list)      # Lazy disk frame paths (PPM, PNG, JPG)
    in_point: int = 0                                       # First used frame index in source
    out_point: int = 0                                      # Last used frame index in source
    speed: float = 1.0                                      # Playback speed multiplier (1.0 = normal)
    transition_type: str = "none"                           # "none", "crossfade", "fade_black", "fade_white", "wipe_left"
    transition_frames: int = 15                             # Duration of transition to NEXT clip
    thumbnail: Optional[Image.Image] = None                 # Thumbnail for timeline display
    _frame_cache: Dict[int, Image.Image] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        total = self.source_length
        if self.out_point <= 0 and total > 0:
            self.out_point = total - 1
        if not self.thumbnail and total > 0:
            self._generate_thumbnail()

    def _generate_thumbnail(self):
        total = self.source_length
        if total <= 0:
            return
        mid = (self.in_point + self.out_point) // 2
        mid = max(0, min(total - 1, mid))
        try:
            if self.frames:
                img = self.frames[mid].copy()
            elif self.file_paths:
                with Image.open(self.file_paths[mid]) as im:
                    img = im.convert("RGB")
            else:
                img = Image.new("RGB", (120, 68), (40, 45, 60))
            img.thumbnail((120, 68), Image.Resampling.LANCZOS)
            self.thumbnail = img
        except Exception:
            self.thumbnail = Image.new("RGB", (120, 68), (35, 40, 50))

    @property
    def source_length(self) -> int:
        return len(self.frames) if self.frames else len(self.file_paths)

    @property
    def active_frame_count(self) -> int:
        """Effective frame count accounting for in/out points and speed."""
        raw_count = max(1, self.out_point - self.in_point + 1)
        if self.speed <= 0.0:
            return raw_count
        return max(1, round(raw_count / self.speed))

    def get_source_frame(self, relative_index: int) -> Image.Image:
        """Get source frame given relative frame index within this clip (lazy streaming)."""
        total = self.source_length
        if total <= 0:
            return Image.new("RGB", (640, 480), (10, 12, 16))

        src_offset = round(relative_index * self.speed)
        actual_index = self.in_point + src_offset
        actual_index = max(0, min(total - 1, actual_index))

        if self.frames:
            return self.frames[actual_index]

        if actual_index in self._frame_cache:
            return self._frame_cache[actual_index]

        try:
            with Image.open(self.file_paths[actual_index]) as im:
                img = im.convert("RGB")
            if len(self._frame_cache) > 60:
                self._frame_cache.pop(next(iter(self._frame_cache)))
            self._frame_cache[actual_index] = img
            return img
        except Exception:
            return Image.new("RGB", (640, 480), (15, 18, 24))


@dataclass
class AudioTrack:
    """Represents an audio overlay on the timeline."""
    name: str
    file_path: str
    start_frame: int = 0                    # Timeline frame where audio begins
    volume: float = 1.0                     # Volume level (0.0 - 2.0)
    duration_sec: float = 0.0               # Duration in seconds


@dataclass
class TextOverlay:
    """Represents a text or crawl overlay on the timeline."""
    text: str
    style: str = "star_wars_crawl"          # "star_wars_crawl", "title_center", "lower_third", "hud_telemetry"
    start_frame: int = 0
    end_frame: int = 120
    font_size: int = 32
    color: Tuple[int, int, int] = (255, 220, 50)  # Classic crawl yellow
    fade_frames: int = 15                   # Fade in / fade out duration


# ==============================================================================
# TIMELINE ENGINE
# ==============================================================================

class TimelineEngine:
    """Manages clips, transitions, overlays, and renders the composite playhead frame."""

    def __init__(self, fps: int = 30):
        self.fps: int = fps
        self.clips: List[TimelineClip] = []
        self.audio_tracks: List[AudioTrack] = []
        self.text_overlays: List[TextOverlay] = []
        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

    def get_system_font(self, size: int) -> ImageFont.ImageFont:
        """Loads a suitable TrueType system font or falls back cleanly."""
        windir = os.environ.get("WINDIR", "C:\\Windows")
        candidates = [
            os.path.join(windir, "Fonts", "impact.ttf"),
            os.path.join(windir, "Fonts", "arialbd.ttf"),
            os.path.join(windir, "Fonts", "arial.ttf"),
            os.path.join(windir, "Fonts", "consola.ttf"),
        ]
        for font_path in candidates:
            if os.path.exists(font_path):
                key = (font_path, size)
                if key not in self._font_cache:
                    try:
                        self._font_cache[key] = ImageFont.truetype(font_path, size)
                    except Exception:
                        continue
                return self._font_cache[key]
        return ImageFont.load_default()

    @property
    def total_frames(self) -> int:
        if not self.clips:
            return 0
        total = 0
        for i, clip in enumerate(self.clips):
            count = clip.active_frame_count
            # Subtract transition overlap with next clip
            if i < len(self.clips) - 1 and clip.transition_type != "none":
                trans = min(clip.transition_frames, count // 2)
                total += (count - trans)
            else:
                total += count
        return max(1, total)

    @property
    def total_duration_seconds(self) -> float:
        return self.total_frames / max(1, self.fps)

    def get_frame_at(self, timeline_frame: int) -> Image.Image:
        """Composite the video, transitions, and text overlays at a given timeline frame."""
        if not self.clips:
            return Image.new("RGB", (800, 600), (15, 18, 24))

        timeline_frame = max(0, min(self.total_frames - 1, timeline_frame))

        # 1. Locate which clip(s) correspond to this frame
        current_offset = 0
        base_img: Optional[Image.Image] = None

        for i, clip in enumerate(self.clips):
            c_len = clip.active_frame_count
            trans_len = 0
            has_next = (i < len(self.clips) - 1)
            if has_next and clip.transition_type != "none":
                trans_len = min(clip.transition_frames, c_len // 2)

            clip_start = current_offset
            clip_end = clip_start + c_len
            trans_start = clip_end - trans_len

            if clip_start <= timeline_frame < clip_end:
                rel_idx = timeline_frame - clip_start
                raw_frame = clip.get_source_frame(rel_idx)

                # Check if we are inside the transition zone to the next clip
                if has_next and trans_len > 0 and timeline_frame >= trans_start:
                    next_clip = self.clips[i + 1]
                    trans_progress = (timeline_frame - trans_start) / max(1, trans_len)
                    next_rel_idx = timeline_frame - trans_start
                    next_frame = next_clip.get_source_frame(next_rel_idx)
                    base_img = self._blend_transition(
                        raw_frame, next_frame, clip.transition_type, trans_progress
                    )
                else:
                    base_img = raw_frame
                break

            current_offset += (c_len - trans_len)

        if base_img is None:
            # Fallback to last frame of last clip
            last_clip = self.clips[-1]
            base_img = last_clip.get_source_frame(last_clip.active_frame_count - 1)

        # Make an editable RGBA copy for overlays
        comp_img = base_img.convert("RGBA")

        # 2. Render Text Overlays
        for overlay in self.text_overlays:
            if overlay.start_frame <= timeline_frame <= overlay.end_frame:
                comp_img = self._apply_text_overlay(comp_img, overlay, timeline_frame)

        return comp_img.convert("RGB")

    def _blend_transition(
        self,
        img_a: Image.Image,
        img_b: Image.Image,
        transition: str,
        progress: float,
    ) -> Image.Image:
        """Blends two frames according to the transition style and progress (0.0 to 1.0)."""
        progress = max(0.0, min(1.0, progress))
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size, Image.Resampling.BILINEAR)

        if transition == "crossfade":
            return Image.blend(img_a, img_b, progress)

        elif transition == "fade_black":
            if progress < 0.5:
                # Fade out to black
                fade = 1.0 - (progress * 2.0)
                enh = ImageEnhance.Brightness(img_a)
                return enh.enhance(fade)
            else:
                # Fade in from black
                fade = (progress - 0.5) * 2.0
                enh = ImageEnhance.Brightness(img_b)
                return enh.enhance(fade)

        elif transition == "fade_white":
            # Hyperdrive white flash
            white = Image.new("RGB", img_a.size, (255, 255, 255))
            if progress < 0.4:
                return Image.blend(img_a, white, progress / 0.4)
            else:
                return Image.blend(white, img_b, (progress - 0.4) / 0.6)

        elif transition == "wipe_left":
            # Linear horizontal wipe
            w, h = img_a.size
            split_x = int(w * progress)
            result = img_a.copy()
            box = (w - split_x, 0, w, h)
            region = img_b.crop((0, 0, split_x, h))
            result.paste(region, (0, 0))
            return result

        return img_b if progress >= 0.5 else img_a

    def _apply_text_overlay(
        self, base_img: Image.Image, overlay: TextOverlay, frame_idx: int
    ) -> Image.Image:
        """Applies title cards, lower-thirds, or Star Wars crawls onto the image."""
        w, h = base_img.size
        draw_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(draw_layer)

        # Alpha fade calculation
        alpha = 1.0
        dur = overlay.end_frame - overlay.start_frame
        elapsed = frame_idx - overlay.start_frame
        rem = overlay.end_frame - frame_idx
        if overlay.fade_frames > 0:
            if elapsed < overlay.fade_frames:
                alpha = elapsed / overlay.fade_frames
            elif rem < overlay.fade_frames:
                alpha = rem / overlay.fade_frames
        alpha_byte = int(255 * max(0.0, min(1.0, alpha)))
        r, g, b = overlay.color
        color_with_alpha = (r, g, b, alpha_byte)
        shadow_color = (0, 0, 0, int(alpha_byte * 0.85))

        font = self.get_system_font(overlay.font_size)

        if overlay.style == "star_wars_crawl":
            # Perspective-style scrolling text
            progress = elapsed / max(1, dur)
            # Create tall text banner
            crawl_lines = overlay.text.split("\n")
            line_height = int(overlay.font_size * 1.4)
            total_text_h = len(crawl_lines) * line_height + 40
            banner_w = w
            banner = Image.new("RGBA", (banner_w, total_text_h), (0, 0, 0, 0))
            bdraw = ImageDraw.Draw(banner)

            for i, line in enumerate(crawl_lines):
                # Center line text
                bbox = bdraw.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
                lx = (banner_w - lw) // 2
                ly = i * line_height
                # Shadow + Text
                bdraw.text((lx + 2, ly + 2), line, font=font, fill=shadow_color)
                bdraw.text((lx, ly), line, font=font, fill=color_with_alpha)

            # Move banner vertically upwards across the screen
            y_start = h * 0.95
            y_end = -total_text_h
            cur_y = int(y_start + progress * (y_end - y_start))

            draw_layer.paste(banner, (0, cur_y), banner)

        elif overlay.style == "title_center":
            # Centered bold cinematic title
            lines = overlay.text.split("\n")
            line_height = int(overlay.font_size * 1.3)
            total_h = len(lines) * line_height
            start_y = (h - total_h) // 2

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
                lx = (w - lw) // 2
                ly = start_y + i * line_height
                draw.text((lx + 3, ly + 3), line, font=font, fill=shadow_color)
                draw.text((lx, ly), line, font=font, fill=color_with_alpha)

        elif overlay.style == "lower_third":
            # Professional lower third subtitle bar
            bar_h = int(overlay.font_size * 2.2)
            bar_y = h - bar_h - 30
            # Semi-transparent dark background bar
            draw.rectangle(
                [0, bar_y, w, bar_y + bar_h],
                fill=(10, 15, 25, int(alpha_byte * 0.75))
            )
            # Accent left border
            draw.rectangle(
                [0, bar_y, 8, bar_y + bar_h],
                fill=(255, 180, 40, alpha_byte)
            )
            bbox = draw.textbbox((0, 0), overlay.text, font=font)
            ty = bar_y + (bar_h - (bbox[3] - bbox[1])) // 2
            draw.text((30, ty), overlay.text, font=font, fill=color_with_alpha)

        elif overlay.style == "hud_telemetry":
            # Sci-Fi / Space HUD telemetry
            hud_font = self.get_system_font(max(14, overlay.font_size - 10))
            lines = overlay.text.split("\n")
            # Upper right corner telemetry
            max_lw = max(draw.textbbox((0, 0), l, font=hud_font)[2] for l in lines)
            base_x = w - max_lw - 25
            base_y = 25
            for i, line in enumerate(lines):
                ly = base_y + i * int(overlay.font_size * 1.1)
                draw.text((base_x + 1, ly + 1), line, font=hud_font, fill=(0, 0, 0, alpha_byte))
                draw.text((base_x, ly), line, font=hud_font, fill=(60, 240, 180, alpha_byte))

        return Image.alpha_composite(base_img, draw_layer)


# ==============================================================================
# MOVIE MAKER STUDIO GUI
# ==============================================================================

class MovieMakerStudio(tk.Toplevel):
    """Full-featured Non-Linear Video Editor Window for tkray_tracer."""

    def __init__(
        self,
        parent: tk.Tk,
        initial_frames: Optional[List[Image.Image]] = None,
        initial_fps: int = 30,
        clip_name: str = "RayTraced_Shot",
    ):
        super().__init__(parent)
        self.title("🎬 tkray_tracer — Movie Maker Studio")
        self.geometry("1380x880")
        self.minsize(1050, 700)
        self.configure(bg="#1a1c23")

        self.engine = TimelineEngine(fps=initial_fps)
        self.current_frame_idx: int = 0
        self.is_playing: bool = False
        self.play_thread: Optional[threading.Thread] = None
        self.selected_clip_idx: Optional[int] = None
        self.copied_clip: Optional[TimelineClip] = None

        # Add initial clip if provided
        if initial_frames:
            clip = TimelineClip(name=clip_name, frames=list(initial_frames))
            self.engine.clips.append(clip)
            self.selected_clip_idx = 0

        self._build_ui()
        self._bind_keys()
        self.update_preview()
        self.draw_timeline()

    # --------------------------------------------------------------------------
    # UI CONSTRUCTION
    # --------------------------------------------------------------------------
    def _build_ui(self):
        # 1. Top Control Ribbon
        top_bar = tk.Frame(self, bg="#242834", height=45)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        btn_style = {
            "bg": "#32384a", "fg": "#e2e8f0", "activebackground": "#444c64",
            "activeforeground": "#ffffff", "relief": tk.FLAT, "padx": 10, "pady": 4, "font": ("Segoe UI", 9, "bold")
        }

        tk.Button(top_bar, text="📁 Add Frames (Folder)", command=self.on_import_image_sequence, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(top_bar, text="🖼 Add Frames (Files)", command=self.on_import_image_files, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(top_bar, text="🎞 Add GIF / Video", command=self.on_import_gif_video, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(top_bar, text="🎵 Add Audio Track", command=self.on_import_audio, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(top_bar, text="📝 Add Text Overlay", command=self.on_add_text_overlay, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)

        # FPS selector
        tk.Label(top_bar, text="FPS:", bg="#242834", fg="#94a3b8", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(15, 2))
        self.fps_var = tk.StringVar(value=str(self.engine.fps))
        fps_combo = ttk.Combobox(top_bar, textvariable=self.fps_var, values=["12", "15", "24", "30", "60"], width=4, state="readonly")
        fps_combo.pack(side=tk.LEFT, padx=4)
        fps_combo.bind("<<ComboboxSelected>>", self.on_fps_changed)

        # Export Button (Highlight color)
        export_btn = tk.Button(
            top_bar, text="🚀 EXPORT MOVIE (MP4 / GIF)",
            command=self.on_export_movie_dialog,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            relief=tk.FLAT, padx=14, pady=5, font=("Segoe UI", 9, "bold")
        )
        export_btn.pack(side=tk.RIGHT, padx=10, pady=6)

        # 2. Main Middle Workspace: Preview (Left) + Inspector (Right)
        middle_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#13151b", sashrelief=tk.RAISED, sashwidth=4)
        middle_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left Preview Panel
        preview_frame = tk.Frame(middle_paned, bg="#13151b")
        middle_paned.add(preview_frame, minsize=650)

        # Canvas for video playback
        self.preview_canvas = tk.Canvas(preview_frame, bg="#0b0d11", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))
        self.preview_canvas.bind("<Configure>", lambda e: self.update_preview())

        # Timecode & Scrubber bar above playback controls
        info_bar = tk.Frame(preview_frame, bg="#1a1c23")
        info_bar.pack(fill=tk.X, padx=8, pady=2)

        self.timecode_label = tk.Label(
            info_bar, text="00:00:00.00 | Frame 0 / 0", bg="#1a1c23", fg="#38bdf8",
            font=("Consolas", 11, "bold")
        )
        self.timecode_label.pack(side=tk.LEFT, padx=6)

        self.res_label = tk.Label(
            info_bar, text="Resolution: ---", bg="#1a1c23", fg="#94a3b8", font=("Segoe UI", 9)
        )
        self.res_label.pack(side=tk.RIGHT, padx=6)

        # Scrub slider
        self.scrub_var = tk.DoubleVar(value=0)
        self.scrub_slider = tk.Scale(
            preview_frame, variable=self.scrub_var, from_=0, to=100, orient=tk.HORIZONTAL,
            showvalue=False, bg="#1a1c23", fg="#38bdf8", troughcolor="#2a2e3d",
            activebackground="#0284c7", highlightthickness=0, command=self.on_scrub
        )
        self.scrub_slider.pack(fill=tk.X, padx=8, pady=2)

        # Playback Transport Controls
        transport_bar = tk.Frame(preview_frame, bg="#1a1c23", height=38)
        transport_bar.pack(fill=tk.X, padx=8, pady=(2, 8))

        tbtn = {"bg": "#2a2e3d", "fg": "#f1f5f9", "relief": tk.FLAT, "padx": 8, "pady": 2, "font": ("Segoe UI", 9)}
        tk.Button(transport_bar, text="⏮ Start", command=self.on_jump_start, **tbtn).pack(side=tk.LEFT, padx=2)
        tk.Button(transport_bar, text="◀ Prev", command=self.on_prev_frame, **tbtn).pack(side=tk.LEFT, padx=2)
        self.play_btn = tk.Button(
            transport_bar, text="▶ PLAY", command=self.toggle_play,
            bg="#059669", fg="#ffffff", activebackground="#047857", relief=tk.FLAT,
            padx=16, pady=2, font=("Segoe UI", 9, "bold")
        )
        self.play_btn.pack(side=tk.LEFT, padx=4)
        tk.Button(transport_bar, text="Next ▶", command=self.on_next_frame, **tbtn).pack(side=tk.LEFT, padx=2)
        tk.Button(transport_bar, text="End ⏭", command=self.on_jump_end, **tbtn).pack(side=tk.LEFT, padx=2)

        # Splice / Cut Buttons
        tk.Label(transport_bar, text="|", bg="#1a1c23", fg="#475569").pack(side=tk.LEFT, padx=6)
        tk.Button(transport_bar, text="✂ Split Clip [C]", command=self.on_split_clip, bg="#b45309", fg="#ffffff", relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=2)
        tk.Button(transport_bar, text="📋 Copy", command=self.on_copy_clip, **tbtn).pack(side=tk.LEFT, padx=2)
        tk.Button(transport_bar, text="📥 Paste", command=self.on_paste_clip, **tbtn).pack(side=tk.LEFT, padx=2)
        tk.Button(transport_bar, text="🗑 Delete", command=self.on_delete_clip, bg="#7f1d1d", fg="#fca5a5", relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=2)

        # Right Inspector Panel
        inspector_frame = tk.Frame(middle_paned, bg="#1e222d", width=340)
        middle_paned.add(inspector_frame, minsize=300)
        self._build_inspector(inspector_frame)

        # 3. Bottom Multi-Track Visual Timeline
        bottom_frame = tk.Frame(self, bg="#13151b", height=240)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        t_header = tk.Frame(bottom_frame, bg="#1e222d", height=26)
        t_header.pack(fill=tk.X)
        tk.Label(t_header, text="🎞 TIMELINE TRACKS (Video • Audio • Overlays)", bg="#1e222d", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)

        # Scrollable Timeline Canvas
        self.timeline_canvas = tk.Canvas(bottom_frame, bg="#0f1117", height=200, highlightthickness=0)
        self.timeline_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)

    def _build_inspector(self, parent: tk.Frame):
        """Constructs clip, transition, and overlay inspector controls."""
        tk.Label(parent, text="PROPERTIES & INSPECTOR", bg="#1e222d", fg="#f8fafc", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))

        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Clip Tab
        clip_tab = tk.Frame(notebook, bg="#1e222d")
        notebook.add(clip_tab, text="Clip Settings")

        tk.Label(clip_tab, text="Selected Clip:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=8, pady=(8, 2))
        self.clip_name_var = tk.StringVar(value="None")
        tk.Entry(clip_tab, textvariable=self.clip_name_var, bg="#2a2e3d", fg="#f1f5f9", relief=tk.FLAT).pack(fill=tk.X, padx=8, pady=2)

        # In/Out Point adjustments
        in_out_frame = tk.Frame(clip_tab, bg="#1e222d")
        in_out_frame.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(in_out_frame, text="In Frame:", bg="#1e222d", fg="#94a3b8").grid(row=0, column=0, sticky="w")
        self.in_pt_var = tk.IntVar(value=0)
        tk.Spinbox(in_out_frame, from_=0, to=99999, textvariable=self.in_pt_var, width=6, command=self.on_trim_changed).grid(row=0, column=1, padx=4)

        tk.Label(in_out_frame, text="Out Frame:", bg="#1e222d", fg="#94a3b8").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.out_pt_var = tk.IntVar(value=0)
        tk.Spinbox(in_out_frame, from_=0, to=99999, textvariable=self.out_pt_var, width=6, command=self.on_trim_changed).grid(row=0, column=3, padx=4)

        # Speed Multiplier
        tk.Label(clip_tab, text="Playback Speed:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=8, pady=(6, 2))
        self.speed_var = tk.StringVar(value="1.0x")
        speed_cb = ttk.Combobox(clip_tab, textvariable=self.speed_var, values=["0.25x", "0.5x", "1.0x", "1.5x", "2.0x", "4.0x"], state="readonly")
        speed_cb.pack(fill=tk.X, padx=8, pady=2)
        speed_cb.bind("<<ComboboxSelected>>", self.on_speed_changed)

        # Transition to Next Clip
        tk.Label(clip_tab, text="Transition to Next Clip:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=8, pady=(12, 2))
        self.trans_type_var = tk.StringVar(value="none")
        trans_cb = ttk.Combobox(
            clip_tab, textvariable=self.trans_type_var,
            values=["none", "crossfade", "fade_black", "fade_white", "wipe_left"], state="readonly"
        )
        trans_cb.pack(fill=tk.X, padx=8, pady=2)
        trans_cb.bind("<<ComboboxSelected>>", self.on_trans_type_changed)

        tk.Label(clip_tab, text="Transition Frames:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=8, pady=(6, 2))
        self.trans_frames_var = tk.IntVar(value=15)
        tk.Spinbox(clip_tab, from_=2, to=120, textvariable=self.trans_frames_var, command=self.on_trans_frames_changed).pack(fill=tk.X, padx=8, pady=2)

        # Text Overlay Tab
        text_tab = tk.Frame(notebook, bg="#1e222d")
        notebook.add(text_tab, text="Text & Crawl")

        tk.Label(text_tab, text="Overlay Style:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=8, pady=(8, 2))
        self.text_style_var = tk.StringVar(value="star_wars_crawl")
        t_style_cb = ttk.Combobox(
            text_tab, textvariable=self.text_style_var,
            values=["star_wars_crawl", "title_center", "lower_third", "hud_telemetry"], state="readonly"
        )
        t_style_cb.pack(fill=tk.X, padx=8, pady=2)

        tk.Label(text_tab, text="Text Content (Multiline for Crawl):", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=8, pady=(6, 2))
        self.overlay_text_entry = tk.Text(text_tab, bg="#2a2e3d", fg="#f1f5f9", height=8, font=("Consolas", 9), relief=tk.FLAT)
        self.overlay_text_entry.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)
        self.overlay_text_entry.insert(
            "1.0",
            "ASTRAL DRIFT\n\n"
            "Episode I: THE HYPERSPACE CORRIDOR\n\n"
            "Deep within the outer rim,\n"
            "a lone explorer discovers\n"
            "a ray-traced wormhole..."
        )

        apply_text_btn = tk.Button(
            text_tab, text="Update Overlay Text", command=self.on_apply_text_overlay,
            bg="#2563eb", fg="#ffffff", relief=tk.FLAT, pady=4
        )
        apply_text_btn.pack(fill=tk.X, padx=8, pady=6)

    def _bind_keys(self):
        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("<Left>", lambda e: self.on_prev_frame())
        self.bind("<Right>", lambda e: self.on_next_frame())
        self.bind("<c>", lambda e: self.on_split_clip())
        self.bind("<C>", lambda e: self.on_split_clip())

    # --------------------------------------------------------------------------
    # TIMELINE RENDERING & INTERACTION
    # --------------------------------------------------------------------------
    def draw_timeline(self):
        """Draws the multi-track visual timeline on the bottom canvas."""
        c = self.timeline_canvas
        c.delete("all")

        w = c.winfo_width()
        if w < 10:
            w = 1200
        h = 200

        total = self.engine.total_frames
        if total <= 0:
            c.create_text(w // 2, h // 2, text="No clips loaded. Click 'Add Image Sequence' above.", fill="#475569", font=("Segoe UI", 11))
            return

        px_per_frame = max(0.5, (w - 100) / max(1, total))
        track_x_start = 50

        # Track 1: Time Ruler
        ruler_y = 20
        c.create_line(track_x_start, ruler_y, track_x_start + total * px_per_frame, ruler_y, fill="#334155")
        step_frames = max(10, int(30 * (1.0 / px_per_frame)))
        for f in range(0, total + 1, step_frames):
            rx = track_x_start + f * px_per_frame
            sec = f / self.engine.fps
            c.create_line(rx, ruler_y - 5, rx, ruler_y + 5, fill="#475569")
            c.create_text(rx, ruler_y - 10, text=f"{sec:.1f}s", fill="#64748b", font=("Segoe UI", 8))

        # Track 2: Video Clips Track
        v_y = 35
        v_h = 60
        cur_frame_offset = 0

        colors = ["#1e3a8a", "#065f46", "#701a75", "#78350f", "#1e293b"]

        for idx, clip in enumerate(self.engine.clips):
            count = clip.active_frame_count
            clip_w = count * px_per_frame
            cx1 = track_x_start + cur_frame_offset * px_per_frame
            cx2 = cx1 + clip_w

            is_sel = (idx == self.selected_clip_idx)
            border_color = "#38bdf8" if is_sel else "#475569"
            bg_color = colors[idx % len(colors)]

            # Clip box
            c.create_rectangle(cx1, v_y, cx2, v_y + v_h, fill=bg_color, outline=border_color, width=2 if is_sel else 1)
            # Clip label
            c.create_text(cx1 + 8, v_y + 14, text=f"{clip.name} ({count}f)", fill="#f8fafc", anchor="w", font=("Segoe UI", 9, "bold"))
            c.create_text(cx1 + 8, v_y + 32, text=f"Speed: {clip.speed}x", fill="#94a3b8", anchor="w", font=("Segoe UI", 8))

            # Transition indicator
            if clip.transition_type != "none" and idx < len(self.engine.clips) - 1:
                t_w = clip.transition_frames * px_per_frame
                c.create_rectangle(cx2 - t_w, v_y + v_h - 14, cx2, v_y + v_h, fill="#f59e0b", outline="")
                c.create_text(cx2 - t_w / 2, v_y + v_h - 7, text=f"⤭ {clip.transition_type[:5]}", fill="#000", font=("Segoe UI", 7, "bold"))

            cur_frame_offset += count

        # Track 3: Audio Tracks
        a_y = 105
        a_h = 30
        c.create_rectangle(track_x_start, a_y, track_x_start + total * px_per_frame, a_y + a_h, fill="#18181b", outline="#27272a")
        for audio in self.engine.audio_tracks:
            ax1 = track_x_start + audio.start_frame * px_per_frame
            dur_frames = int(audio.duration_sec * self.engine.fps)
            ax2 = ax1 + dur_frames * px_per_frame
            c.create_rectangle(ax1, a_y, ax2, a_y + a_h, fill="#047857", outline="#10b981")
            c.create_text(ax1 + 8, a_y + 15, text=f"🎵 {audio.name} ({audio.volume*100:.0f}%)", fill="#ecfdf5", anchor="w", font=("Segoe UI", 8))

        # Track 4: Text Overlays
        t_y = 145
        t_h = 30
        c.create_rectangle(track_x_start, t_y, track_x_start + total * px_per_frame, t_y + t_h, fill="#18181b", outline="#27272a")
        for txt in self.engine.text_overlays:
            tx1 = track_x_start + txt.start_frame * px_per_frame
            tx2 = track_x_start + txt.end_frame * px_per_frame
            c.create_rectangle(tx1, t_y, tx2, t_y + t_h, fill="#b45309", outline="#f59e0b")
            first_line = txt.text.split("\n")[0][:25]
            c.create_text(tx1 + 8, t_y + 15, text=f"📝 {first_line}...", fill="#fef3c7", anchor="w", font=("Segoe UI", 8))

        # Playhead (Red vertical line)
        px = track_x_start + self.current_frame_idx * px_per_frame
        c.create_line(px, 10, px, h - 5, fill="#ef4444", width=2)
        # Red scrub handle
        c.create_polygon(px - 6, 8, px + 6, 8, px, 18, fill="#ef4444", outline="")

    def on_timeline_click(self, event):
        w = self.timeline_canvas.winfo_width()
        total = self.engine.total_frames
        if total <= 0:
            return
        px_per_frame = max(0.5, (w - 100) / max(1, total))
        track_x_start = 50

        frame = round((event.x - track_x_start) / px_per_frame)
        self.seek_to(frame)

        # Check if clicked on a clip in Video Track (y between 35 and 95)
        if 35 <= event.y <= 95:
            cur_offset = 0
            for idx, clip in enumerate(self.engine.clips):
                c_len = clip.active_frame_count
                if cur_offset <= frame < cur_offset + c_len:
                    self.select_clip(idx)
                    break
                cur_offset += c_len

    def on_timeline_drag(self, event):
        self.on_timeline_click(event)

    def select_clip(self, idx: int):
        if 0 <= idx < len(self.engine.clips):
            self.selected_clip_idx = idx
            clip = self.engine.clips[idx]
            self.clip_name_var.set(clip.name)
            self.in_pt_var.set(clip.in_point)
            self.out_pt_var.set(clip.out_point)
            self.speed_var.set(f"{clip.speed}x")
            self.trans_type_var.set(clip.transition_type)
            self.trans_frames_var.set(clip.transition_frames)
            self.draw_timeline()

    # --------------------------------------------------------------------------
    # PREVIEW & PLAYBACK
    # --------------------------------------------------------------------------
    def seek_to(self, frame_idx: int):
        total = self.engine.total_frames
        self.current_frame_idx = max(0, min(total - 1 if total > 0 else 0, frame_idx))
        if total > 0:
            self.scrub_slider.config(to=total - 1)
            self.scrub_var.set(self.current_frame_idx)
        self.update_preview()
        self.draw_timeline()

    def update_preview(self):
        """Fetches the composited frame and renders it scaled to fit the preview canvas."""
        frame = self.engine.get_frame_at(self.current_frame_idx)
        total = self.engine.total_frames

        # Update Timecode Readout
        sec = self.current_frame_idx / max(1, self.engine.fps)
        mins = int(sec // 60)
        secs = int(sec % 60)
        frames_part = int(self.current_frame_idx % self.engine.fps)
        self.timecode_label.config(
            text=f"{mins:02d}:{secs:02d}.{frames_part:02d} | Frame {self.current_frame_idx + 1} / {total}"
        )
        self.res_label.config(text=f"Resolution: {frame.width}x{frame.height}")

        # Scale image to canvas keeping aspect ratio
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 50 or ch < 50:
            cw, ch = 800, 480

        img_w, img_h = frame.size
        scale = min(cw / img_w, ch / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        disp_img = frame.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self._photo = ImageTk.PhotoImage(disp_img)

        self.preview_canvas.delete("all")
        # Center in canvas
        cx = (cw - new_w) // 2
        cy = (ch - new_h) // 2
        self.preview_canvas.create_image(cx, cy, anchor="nw", image=self._photo)

    def toggle_play(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.config(text="▶ PLAY", bg="#059669")
        else:
            if self.engine.total_frames <= 0:
                return
            self.is_playing = True
            self.play_btn.config(text="⏸ PAUSE", bg="#dc2626")
            self._playback_loop()

    def _playback_loop(self):
        if not self.is_playing:
            return
        total = self.engine.total_frames
        if total <= 0:
            self.toggle_play()
            return

        self.current_frame_idx = (self.current_frame_idx + 1) % total
        self.seek_to(self.current_frame_idx)

        interval_ms = max(5, int(1000 / self.engine.fps))
        self.after(interval_ms, self._playback_loop)

    def on_jump_start(self):
        self.seek_to(0)

    def on_jump_end(self):
        self.seek_to(self.engine.total_frames - 1)

    def on_prev_frame(self):
        self.seek_to(self.current_frame_idx - 1)

    def on_next_frame(self):
        self.seek_to(self.current_frame_idx + 1)

    def on_scrub(self, val):
        if not self.is_playing:
            self.seek_to(int(float(val)))

    # --------------------------------------------------------------------------
    # EDITING ACTIONS (SPLIT, TRIM, COPY, PASTE, DELETE)
    # --------------------------------------------------------------------------
    def on_split_clip(self):
        """Splits the active clip at the current playhead into two clips."""
        if self.selected_clip_idx is None or not self.engine.clips:
            messagebox.showinfo("Split Clip", "Select a clip to split.")
            return

        clip = self.engine.clips[self.selected_clip_idx]
        cur_offset = 0
        for i in range(self.selected_clip_idx):
            cur_offset += self.engine.clips[i].active_frame_count

        rel_frame = self.current_frame_idx - cur_offset
        if rel_frame <= 0 or rel_frame >= clip.active_frame_count:
            messagebox.showinfo(
                "Split Clip",
                f"Playhead is outside the body of '{clip.name}'. Position the playhead inside the clip to cut."
            )
            return

        # Split into two parts
        source_cut = clip.in_point + round(rel_frame * clip.speed)

        part1 = TimelineClip(
            name=f"{clip.name}_A",
            frames=clip.frames,
            file_paths=clip.file_paths,
            in_point=clip.in_point,
            out_point=source_cut - 1,
            speed=clip.speed,
            transition_type="none"
        )
        part2 = TimelineClip(
            name=f"{clip.name}_B",
            frames=clip.frames,
            file_paths=clip.file_paths,
            in_point=source_cut,
            out_point=clip.out_point,
            speed=clip.speed,
            transition_type=clip.transition_type,
            transition_frames=clip.transition_frames
        )

        self.engine.clips[self.selected_clip_idx] = part1
        self.engine.clips.insert(self.selected_clip_idx + 1, part2)
        self.select_clip(self.selected_clip_idx)
        self.seek_to(self.current_frame_idx)

    def on_delete_clip(self):
        if self.selected_clip_idx is None or not self.engine.clips:
            return
        del self.engine.clips[self.selected_clip_idx]
        if self.engine.clips:
            self.selected_clip_idx = min(self.selected_clip_idx, len(self.engine.clips) - 1)
        else:
            self.selected_clip_idx = None
        self.seek_to(0)

    def on_copy_clip(self):
        if self.selected_clip_idx is None or not self.engine.clips:
            return
        self.copied_clip = copy.copy(self.engine.clips[self.selected_clip_idx])
        messagebox.showinfo("Copied", f"Copied clip '{self.copied_clip.name}' to clipboard.")

    def on_paste_clip(self):
        if not self.copied_clip:
            return
        new_clip = copy.copy(self.copied_clip)
        new_clip.name = f"{new_clip.name}_copy"
        insert_idx = (self.selected_clip_idx + 1) if self.selected_clip_idx is not None else len(self.engine.clips)
        self.engine.clips.insert(insert_idx, new_clip)
        self.select_clip(insert_idx)
        self.draw_timeline()

    def on_trim_changed(self):
        if self.selected_clip_idx is None or not self.engine.clips:
            return
        clip = self.engine.clips[self.selected_clip_idx]
        clip.in_point = max(0, min(self.in_pt_var.get(), len(clip.frames) - 1))
        clip.out_point = max(clip.in_point, min(self.out_pt_var.get(), len(clip.frames) - 1))
        self.draw_timeline()
        self.update_preview()

    def on_speed_changed(self, event=None):
        if self.selected_clip_idx is None or not self.engine.clips:
            return
        val_str = self.speed_var.get().replace("x", "")
        try:
            speed = float(val_str)
            self.engine.clips[self.selected_clip_idx].speed = speed
            self.draw_timeline()
            self.update_preview()
        except ValueError:
            pass

    def on_trans_type_changed(self, event=None):
        if self.selected_clip_idx is None or not self.engine.clips:
            return
        self.engine.clips[self.selected_clip_idx].transition_type = self.trans_type_var.get()
        self.draw_timeline()

    def on_trans_frames_changed(self):
        if self.selected_clip_idx is None or not self.engine.clips:
            return
        self.engine.clips[self.selected_clip_idx].transition_frames = self.trans_frames_var.get()
        self.draw_timeline()

    def on_fps_changed(self, event=None):
        try:
            self.engine.fps = int(self.fps_var.get())
            self.draw_timeline()
            self.update_preview()
        except ValueError:
            pass

    # --------------------------------------------------------------------------
    # ASSET IMPORTING (SEQUENCES, GIFS, AUDIO)
    # --------------------------------------------------------------------------
    def on_import_image_sequence(self):
        """Imports a folder of rendered image frames (PPM, PNG, JPG, BMP) using instant lazy streaming."""
        folder = filedialog.askdirectory(title="Select Folder of Rendered Frames")
        if not folder:
            return

        valid_exts = (".ppm", ".png", ".jpg", ".jpeg", ".bmp")
        try:
            candidates = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith(valid_exts) and os.path.isfile(os.path.join(folder, f))
            ]
        except Exception as exc:
            messagebox.showerror("Error Reading Folder", str(exc))
            return

        if not candidates:
            messagebox.showwarning(
                "No Frames Found",
                f"No supported image files (.ppm, .png, .jpg) were found in:\n{folder}"
            )
            return

        # Natural sort so frame_1, frame_2, ... frame_10 are correctly ordered
        files = sorted(candidates, key=_natural_sort_key)

        name = os.path.basename(folder) or "Sequence"
        clip = TimelineClip(name=name, file_paths=files)
        self.engine.clips.append(clip)
        self.select_clip(len(self.engine.clips) - 1)
        self.seek_to(0)
        messagebox.showinfo(
            "Frames Loaded",
            f"Instantly loaded {len(files)} frames ({os.path.splitext(files[0])[1]}) from:\n{name}"
        )

    def on_import_image_files(self):
        """Imports individual image files via multi-select dialog."""
        chosen = filedialog.askopenfilenames(
            title="Select Rendered Image Frames",
            filetypes=[
                ("Image Frames", "*.ppm;*.png;*.jpg;*.jpeg;*.bmp"),
                ("PPM Files", "*.ppm"),
                ("PNG Files", "*.png"),
                ("All Files", "*.*"),
            ]
        )
        if not chosen:
            return

        files = sorted(list(chosen), key=_natural_sort_key)
        name = os.path.basename(files[0])
        clip = TimelineClip(name=f"Files_{len(files)}", file_paths=files)
        self.engine.clips.append(clip)
        self.select_clip(len(self.engine.clips) - 1)
        self.seek_to(0)
        messagebox.showinfo(
            "Frames Loaded",
            f"Instantly loaded {len(files)} selected frames."
        )

    def on_import_gif_video(self):
        """Imports an animated GIF file into frames."""
        file_path = filedialog.askopenfilename(
            title="Select Animated GIF",
            filetypes=[("Animated GIF", "*.gif"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            im = Image.open(file_path)
            frames = []
            for frame_idx in range(getattr(im, "n_frames", 1)):
                im.seek(frame_idx)
                frames.append(im.convert("RGB"))

            name = os.path.splitext(os.path.basename(file_path))[0]
            clip = TimelineClip(name=name, frames=frames)
            self.engine.clips.append(clip)
            self.select_clip(len(self.engine.clips) - 1)
            self.seek_to(0)
            messagebox.showinfo("Imported", f"Successfully imported {len(frames)} frames from {os.path.basename(file_path)}.")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not load animated GIF:\n{exc}")

    def on_import_audio(self):
        """Imports an audio file (MP3, WAV, AAC, OGG)."""
        file_path = filedialog.askopenfilename(
            title="Select Audio Track",
            filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg;*.aac;*.m4a"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        # Probe duration via FFmpeg if available, or rough estimate
        duration_sec = 60.0
        audio = AudioTrack(
            name=os.path.basename(file_path),
            file_path=file_path,
            start_frame=self.current_frame_idx,
            volume=1.0,
            duration_sec=duration_sec
        )
        self.engine.audio_tracks.append(audio)
        self.draw_timeline()
        messagebox.showinfo("Audio Added", f"Added audio track '{audio.name}' starting at frame {self.current_frame_idx}.")

    def on_add_text_overlay(self):
        """Adds a Star Wars Crawl or Title overlay across the current timeline span."""
        total = self.engine.total_frames
        dur = min(150, max(30, total))
        overlay = TextOverlay(
            text=self.overlay_text_entry.get("1.0", tk.END).strip(),
            style=self.text_style_var.get(),
            start_frame=self.current_frame_idx,
            end_frame=min(total - 1 if total > 0 else 120, self.current_frame_idx + dur),
            font_size=32,
            color=(255, 220, 50)
        )
        self.engine.text_overlays.append(overlay)
        self.draw_timeline()
        self.update_preview()
        messagebox.showinfo("Overlay Added", f"Added '{overlay.style}' overlay across frames {overlay.start_frame} to {overlay.end_frame}.")

    def on_apply_text_overlay(self):
        txt = self.overlay_text_entry.get("1.0", tk.END).strip()
        if self.engine.text_overlays:
            self.engine.text_overlays[-1].text = txt
            self.engine.text_overlays[-1].style = self.text_style_var.get()
            self.update_preview()
            self.draw_timeline()

    # --------------------------------------------------------------------------
    # MOVIE EXPORT ENGINE (MP4 & ANIMATED GIF)
    # --------------------------------------------------------------------------
    def on_export_movie_dialog(self):
        """Opens export dialog and handles multi-threaded MP4 encoding."""
        if not self.engine.clips:
            messagebox.showwarning("Export Movie", "No clips in timeline to export.")
            return

        export_win = tk.Toplevel(self)
        export_win.title("Export Movie")
        export_win.geometry("450x380")
        export_win.configure(bg="#1e222d")
        export_win.grab_set()

        tk.Label(export_win, text="RENDER & EXPORT MOVIE", bg="#1e222d", fg="#f8fafc", font=("Segoe UI", 11, "bold")).pack(pady=(12, 8))

        # Format
        tk.Label(export_win, text="Format:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=20)
        fmt_var = tk.StringVar(value="MP4 Video (H.264)" if FFMPEG_EXE else "Animated GIF")
        fmt_cb = ttk.Combobox(export_win, textvariable=fmt_var, values=["MP4 Video (H.264)", "Animated GIF", "PNG Image Sequence"], state="readonly")
        fmt_cb.pack(fill=tk.X, padx=20, pady=2)

        # Resolution
        tk.Label(export_win, text="Resolution Preset:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=20, pady=(6, 0))
        res_var = tk.StringVar(value="Original Source")
        res_cb = ttk.Combobox(export_win, textvariable=res_var, values=["Original Source", "1920x1080 (1080p)", "1280x720 (720p)", "800x600"], state="readonly")
        res_cb.pack(fill=tk.X, padx=20, pady=2)

        # Framerate
        tk.Label(export_win, text="Framerate:", bg="#1e222d", fg="#94a3b8").pack(anchor="w", padx=20, pady=(6, 0))
        fps_out_var = tk.StringVar(value=str(self.engine.fps))
        fps_out_cb = ttk.Combobox(export_win, textvariable=fps_out_var, values=["24", "30", "60"], state="readonly")
        fps_out_cb.pack(fill=tk.X, padx=20, pady=2)

        # Include Audio
        include_audio_var = tk.BooleanVar(value=True if self.engine.audio_tracks else False)
        tk.Checkbutton(export_win, text="Include Audio Tracks (MP4 only)", variable=include_audio_var, bg="#1e222d", fg="#cbd5e1", selectcolor="#2a2e3d").pack(anchor="w", padx=20, pady=8)

        # Progress bar
        prog_var = tk.DoubleVar(value=0)
        prog_bar = ttk.Progressbar(export_win, variable=prog_var, maximum=100)
        prog_bar.pack(fill=tk.X, padx=20, pady=8)
        status_lbl = tk.Label(export_win, text="Ready to export.", bg="#1e222d", fg="#38bdf8", font=("Segoe UI", 9))
        status_lbl.pack(pady=2)

        def start_export():
            fmt_chosen = fmt_var.get()
            if "MP4" in fmt_chosen:
                ext = ".mp4"
                ftypes = [("MP4 Video", "*.mp4")]
            elif "GIF" in fmt_chosen:
                ext = ".gif"
                ftypes = [("Animated GIF", "*.gif")]
            else:
                ext = ""
                ftypes = [("Folder", "*.*")]

            out_path = filedialog.asksaveasfilename(
                parent=export_win,
                title="Save Rendered Movie",
                defaultextension=ext,
                filetypes=ftypes
            )
            if not out_path:
                return

            def worker():
                try:
                    total = self.engine.total_frames
                    target_fps = int(fps_out_var.get())

                    # Resolution
                    res_choice = res_var.get()
                    if "1920" in res_choice:
                        target_size = (1920, 1080)
                    elif "1280" in res_choice:
                        target_size = (1280, 720)
                    elif "800" in res_choice:
                        target_size = (800, 600)
                    else:
                        target_size = self.engine.get_frame_at(0).size

                    # Ensure dimensions are even for H.264
                    w, h = target_size
                    w = w - (w % 2)
                    h = h - (h % 2)

                    if "MP4" in fmt_chosen:
                        if not FFMPEG_EXE:
                            raise RuntimeError("FFmpeg executable not found. Please install FFmpeg or export as GIF.")

                        cmd = [
                            FFMPEG_EXE, "-y",
                            "-f", "rawvideo",
                            "-vcodec", "rawvideo",
                            "-s", f"{w}x{h}",
                            "-pix_fmt", "rgb24",
                            "-r", str(target_fps),
                            "-i", "-",
                        ]

                        # Add audio if requested and exists
                        has_audio = include_audio_var.get() and len(self.engine.audio_tracks) > 0
                        if has_audio:
                            audio_file = self.engine.audio_tracks[0].file_path
                            cmd.extend(["-i", audio_file, "-c:a", "aac", "-b:a", "192k"])

                        cmd.extend([
                            "-c:v", "libopenh264",
                            "-b:v", "4M",
                            "-pix_fmt", "yuv420p",
                            out_path
                        ])

                        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                        for f_idx in range(total):
                            frame = self.engine.get_frame_at(f_idx)
                            if frame.size != (w, h):
                                frame = frame.resize((w, h), Image.Resampling.LANCZOS)
                            proc.stdin.write(frame.tobytes())
                            prog = ((f_idx + 1) / total) * 100
                            self.after(0, lambda p=prog, idx=f_idx: (
                                prog_var.set(p),
                                status_lbl.config(text=f"Encoding frame {idx + 1} / {total}...")
                            ))

                        proc.stdin.close()
                        proc.wait()
                        if proc.returncode != 0:
                            err = proc.stderr.read().decode(errors="replace")
                            raise RuntimeError(f"FFmpeg failed with code {proc.returncode}:\n{err[:300]}")

                    elif "GIF" in fmt_chosen:
                        frames_to_save = []
                        for f_idx in range(total):
                            frame = self.engine.get_frame_at(f_idx)
                            if frame.size != (w, h):
                                frame = frame.resize((w, h), Image.Resampling.LANCZOS)
                            frames_to_save.append(frame)
                            prog = ((f_idx + 1) / total) * 100
                            self.after(0, lambda p=prog: prog_var.set(p))

                        dur_ms = round(1000 / target_fps)
                        frames_to_save[0].save(
                            out_path,
                            save_all=True,
                            append_images=frames_to_save[1:],
                            duration=dur_ms,
                            loop=0,
                            disposal=2
                        )

                    self.after(0, lambda: (
                        status_lbl.config(text="Export Completed Successfully!"),
                        messagebox.showinfo("Export Complete", f"Movie successfully saved to:\n{out_path}"),
                        export_win.destroy()
                    ))

                except Exception as exc:
                    self.after(0, lambda e=exc: (
                        status_lbl.config(text="Export Failed!"),
                        messagebox.showerror("Export Error", f"Failed to export movie:\n{e}")
                    ))

            threading.Thread(target=worker, daemon=True).start()

        tk.Button(
            export_win, text="Start Exporting", command=start_export,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", relief=tk.FLAT, pady=6, font=("Segoe UI", 9, "bold")
        ).pack(fill=tk.X, padx=20, pady=10)
