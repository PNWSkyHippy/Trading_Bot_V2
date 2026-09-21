"""Tkinter front end for the unified C++ ray-tracing renderer.

PROGRAM MAP
===========
This file has three main responsibilities:

1. Collect render settings and start the one C++ executable.
2. Read the renderer's scanline output and update the preview progressively.
3. Apply Pillow edits while keeping a useful, human-sized Undo history.

The normal path for an image edit is:

        UI control -> callback -> edit state variable -> update_live_preview()

The callback changes the state variable, and update_live_preview() rebuilds
the displayed image from the original image plus the current state variables.
The code does not repeatedly edit the already-edited image, which prevents
the same effect from being accidentally applied on top of itself.

UNDO MODEL
==========
The editor history deliberately groups repeated changes to one control. For
example, dragging Rotation through twenty intermediate values is one edit,
not twenty Undo entries.

        pending_snapshot = state before the first change to the active control
        pending_control  = name of the control currently being changed
        image_stack      = completed Undo snapshots

While the same control is used, its pending snapshot is kept and the live
value is allowed to change. When another control or a discrete action starts,
the pending snapshot is moved to image_stack. Undo commits a pending edit
first, then restores the newest completed snapshot. If no snapshot exists,
Undo only displays the empty-stack message and changes nothing.

ADDING A NEW IMAGE EDIT: MAINTENANCE CHECKLIST
===============================================
Suppose the new edit is called "invert". A complete edit normally needs these
pieces, in this order:

1. Add the state variable in build_ui():

             self.invert = False

2. Add a UI entry in setup_menus() or a control in build_ui():

             self.invert_var = view_menu.add_toggle(
                     "Invert", default=False, on_toggle=self.invert_auto_calc
             )

     The control must call a callback. Merely adding a menu label does not
     connect the menu to image processing or Undo.

3. Add the callback. It starts or continues the named Undo session, changes
     the state variable, and rebuilds the preview:

             def invert_auto_calc(self, state=None):
                     if state is not None:
                             self._begin_control_edit("invert")
                             self.invert = bool(state)
                     self.update_live_preview()

4. Add the actual Pillow operation in update_live_preview(), near the other
     image filters. The operation must use the local image named img:

             if self.invert:
                     img = ImageOps.invert(img)

     Add the required import at the top, for example:

             from PIL import ImageOps

5. Add the state variable to _snapshot_editor_state():

             "invert": self.invert,

6. Restore it in _restore_editor_state():

             self.invert = snapshot.get("invert", self.invert)

     Without both snapshot entries, the image may look correct while Undo and
     redo-like state restoration silently lose the new setting.

7. If the edit uses a slider, add a timer id in build_ui(), a public
     on_invert_change() callback, and a finalize_invert_stack() callback. Copy
     the existing rotation/contrast pattern. The finalize method should call
     _begin_control_edit("invert") before changing the value, then call
     update_live_preview(). Do not call stack_add() for every slider movement.

8. If the edit changes more than one related value, give it one control name
     so the related callbacks share one pending Undo session. For automatic
     helper callbacks, pass control_name=None when they are internal work for
     the already-active control. This is how aspect ratio avoids creating a
     second Undo entry for its automatic resize.

9. If the edit is a discrete action such as Crop or Zoom, call stack_add()
     once before changing the image. Do not also call _begin_control_edit() for
     the same action.

10. Validate the new edit in three ways:

        - Toggle or move it repeatedly and confirm the preview changes.
        - Change another control, press Undo, and confirm the whole edit reverses.
        - Press Undo repeatedly after the stack is empty and confirm the image
            stays unchanged and the zero-Undo message repeats safely.

CHANGE LOG / NOTES
==================
Current file architecture:

- main.cc is the unified C++ renderer; this file launches it with -b, -c,
    and -r width,height, then reads LINE scanlines from stdout.
- The C++ headers remain under the local TheNextWeek directory.
- Windows launches the Linux binary through WSL. POSIX systems launch the
    native binary from the configured mac_dir.
- PROJECT_ROOT adds Code/ to sys.path so the sibling quick_tk package can be
    imported when this file is run directly.
- The Tkinter casts around PhotoImage.put and Canvas._w are for dynamic
    Tk APIs that Pylance's public type stubs do not describe.
- The Undo queue was changed to coalesce repeated edits from one control and
    to leave the image untouched when the completed stack is empty.

When extending this file, keep the same mental order: state, UI, callback,
preview operation, snapshot, restore, then focused validation.
"""
import sys
quick_tk_dir = r"C:\Users\Linda\Trading_Bot_V2\Ron\Code"
if quick_tk_dir not in sys.path:
    sys.path.insert(0, quick_tk_dir)
from quick_tk import QuickApp, ToolView, FormPanel
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, cast
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageTk
import rayincludes as ri
# This file is in Code/RayTrace/src, while quick_tk is in Code/quick_tk.
# Adding Code to sys.path lets this script work when launched directly rather
# than only when launched as part of a larger Python package.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAYTRACE_SRC_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


def _read_pov_ppm(stream):
    """Read a binary PPM pipe, returning dimensions and an iterator of RGB rows."""
    def token():
        value = bytearray()
        while True:
            char = stream.read(1)
            if not char:
                if value:
                    return bytes(value)
                raise RuntimeError("POV-Ray ended before completing its PPM image.")
            if char == b"#":
                stream.readline()
                if value:
                    return bytes(value)
            elif char in b" \t\r\n\v\f":
                if value:
                    # Consume only the header separator, never binary pixels.
                    return bytes(value)
            else:
                value.extend(char)

    magic = token()
    if magic not in (b"P3", b"P6"):
        raise RuntimeError(f"Expected a POV-Ray P3 or P6 image stream, received {magic!r}.")
    width, height, maximum = (int(token()) for _ in range(3))
    if width <= 0 or height <= 0 or not 1 <= maximum <= 65535:
        raise RuntimeError(f"Invalid PPM header: {width}x{height}, maximum {maximum}.")

    def rows():
        sample_bytes = 1 if maximum < 256 else 2
        for row in range(height):
            if magic == b"P6":
                needed = width * 3 * sample_bytes
                data = bytearray()
                while len(data) < needed:
                    chunk = stream.read(needed - len(data))
                    if not chunk:
                        raise RuntimeError(f"POV-Ray P6 stream ended partway through row {row + 1}/{height}.")
                    data.extend(chunk)
                channels = (list(data) if sample_bytes == 1 else
                            [int.from_bytes(data[i:i + 2], "big") for i in range(0, len(data), 2)])
            else:
                channels = [int(token()) for _ in range(width * 3)]
            if any(channel < 0 or channel > maximum for channel in channels):
                raise RuntimeError(f"Invalid PPM pixel value in row {row + 1}.")
            if maximum != 255:
                channels = [(channel * 255 + maximum // 2) // maximum for channel in channels]
            yield [tuple(channels[i:i + 3]) for i in range(0, len(channels), 3)]

    return width, height, rows()

import time

def lerp(a, b, t):
    """Return a value t of the way from a to b."""
    return a + (b - a) * t


def lerp_point(start, end, t):
    """Interpolate an (x, y, z) point."""
    return tuple(lerp(a, b, t) for a, b in zip(start, end))


def point_text(point):
    """Turn (x, y, z) into the C++ command format: x,y,z."""
    return ",".join(f"{value:.3f}" for value in point)


def make_scene1(keyframes, common_settings, total_frames=None):
    """
    Create the scene1 list that your existing render button already uses.

    keyframes:
        A list of important camera poses.  Frame numbers can be any distance
        apart; all missing frames are generated automatically.
    """
    keyframes = [dict(keyframe) for keyframe in keyframes]
    if len(keyframes) < 2:
        raise ValueError("A camera path needs at least two keyframes.")

    # The frame values in the include file are timing markers: they describe
    # where the director wants each key pose to occur relative to the others.
    # Rescale those markers to any requested total frame count.
    if total_frames is not None:
        total_frames = int(total_frames)
        if total_frames < len(keyframes):
            raise ValueError(
                f"Movie Frames must be at least {len(keyframes)} for this {len(keyframes)}-keyframe path."
            )
        first_marker = keyframes[0]["frame"]
        last_marker = keyframes[-1]["frame"]
        marker_span = last_marker - first_marker
        if marker_span <= 0:
            raise ValueError("Camera-path keyframe markers must increase from first to last.")

        previous_frame = 0
        for index, keyframe in enumerate(keyframes):
            if index == 0:
                scaled_frame = 1
            elif index == len(keyframes) - 1:
                scaled_frame = total_frames
            else:
                progress = (keyframe["frame"] - first_marker) / marker_span
                scaled_frame = 1 + round(progress * (total_frames - 1))
                # Leave one frame for every remaining keyframe.
                scaled_frame = max(previous_frame + 1, scaled_frame)
                scaled_frame = min(scaled_frame, total_frames - (len(keyframes) - 1 - index))
            keyframe["frame"] = scaled_frame
            previous_frame = scaled_frame

    frames = []

    for keyframe_index in range(len(keyframes) - 1):
        start = keyframes[keyframe_index]
        end = keyframes[keyframe_index + 1]

        start_frame = start["frame"]
        end_frame = end["frame"]
        frame_count = end_frame - start_frame

        if frame_count <= 0:
            raise ValueError("Each keyframe frame number must be larger than the one before it.")

        # First segment includes its start frame. Later segments do not,
        # because that keyframe was already added as the previous segment's end.
        first_frame = start_frame if keyframe_index == 0 else start_frame + 1

        for frame_number in range(first_frame, end_frame + 1):
            t = (frame_number - start_frame) / frame_count

            camera = lerp_point(start["camera"], end["camera"], t)
            lookat = lerp_point(start["lookat"], end["lookat"], t)
            vfov = lerp(start["vfov"], end["vfov"], t)

            frames.append({
                **common_settings,
                "filename": f"scene_data/scene1.image{frame_number:03d}.ppm",
                "camera": point_text(camera),
                "lookat": point_text(lookat),
                "vfov": f"{vfov:.2f}",
            })

    return frames



# The include file is the editable camera-path skeleton.  This module-level
# default preserves compatibility; the render buttons regenerate it using the
# Movie Frames field immediately before each movie render.
scene1 = make_scene1(ri.scene1_keyframes, ri.common_scene1_settings)

class RayTraceTimer:
    def __init__(self, total_pixels=None):
        if total_pixels is not None:
            self.total_pixels = total_pixels
        # Start the clock
        self.start_time = time.perf_counter()
        self.last_report_time = self.start_time

    def report_progress(self, current_pixel=0, interval_seconds=10):
        """Pollable progress reporter. Prints updates only after a set time interval."""
        current_time = time.perf_counter()
        
        # Only print updates every X seconds to avoid slowing down the render loop
        if current_time - self.last_report_time >= interval_seconds:
            elapsed = current_time - self.start_time
            self.last_report_time = current_time
            return(f"Elapsed: {elapsed / 60:.1f}m")

    def print_final(self):
        """Call this immediately after the loop finishes."""
        end_time = time.perf_counter()
        total_duration = end_time - self.start_time
        return (f"\n--- Render Complete ---\nTotal Time: {total_duration / 60:.2f} minutes ({total_duration:.2f} seconds)")

class CanvasSelector:
    """
    Attach a rectangle or point-by-point freehand selector to a canvas.

    ``selection_mode="box"`` returns normalized ``x0, y0, x1, y1`` values.
    ``selection_mode="freehand"`` returns a list of closed-loop ``(x, y)``
    points. In freehand mode, click to place each point and click near the
    first point to close the loop. Escape cancels and returns an empty list.
    """
    def __init__(self, canvas, callback, selection_mode="box"):
        """Initialize class varaibles

        Args:
            canvas (_type_): _description_
            callback (function): _description_
        """        
        self.canvas = canvas      # Main window drawing cntainer
        self.callback = callback  # The function to run when mouse is released
        if selection_mode not in {"box", "freehand"}:
            raise ValueError("selection_mode must be 'box' or 'freehand'")
        self.selection_mode = selection_mode
        self.start_x = None    # For renderer
        self.start_y = None
        self.rect_id = None
        self.points = []
        self.rubber_line_id = None
        self.close_distance = 10

        # Bind to the existing canvas passed into the class
        if self.selection_mode == "box":
            self.canvas.bind("<ButtonPress-1>", self.on_press)
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_release)
        else:
            self.canvas.bind("<Button-1>", self.on_freehand_click)
            self.canvas.bind("<Motion>", self.on_freehand_motion)
            self.canvas.bind("<Escape>", self.on_cancel)
            self.canvas.focus_set()

    def _canvas_point(self, event):
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def on_press(self, event):
        """_summary_ Triggered on mouse clicks in canvas
        Happpends anytime mouse clicked in canvas and track retake if
        one is dragged out to be used or not used

        Args:
            event (_type_): _description_
        """        
        self.start_x = self.canvas.canvasx(event.x)   #record location of click
        self.start_y = self.canvas.canvasy(event.y)
        self.rect_id = self.canvas.create_rectangle(  #record dragged rectangle
            self.start_x, self.start_y, self.start_x, self.start_y, 
            outline="cyan", width=2, tags="selector"
        )

    def on_drag(self, event):
        """_summary_ nouse depressed and drgged

        Args:
            event (_type_): _description_
        """        
        # Track the end point of the dragged rectangle
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
        
    def on_release(self, event):
        """_summary_ Mouse released ending defining a rectangle selection

        Args:
            event (_type_): _description_
        """        
        end_x = self.canvas.canvasx(event.x) # Record end coords
        end_y = self.canvas.canvasy(event.y)
        
        # Verify there wa a valid start ing x,y
        if self.start_x is None or self.start_y is None:
            return

        # 1. Normalize corners (Im case dragged down to up oor right to left
        x0, x1 = sorted([self.start_x, end_x])
        y0, y1 = sorted([self.start_y, end_y])

        # 2. Clean up the drawing box right away if desired
        self.canvas.delete(self.rect_id)
        
        # 3. Send coordinates back to your main project logic
        if (x1 - x0) > 2 and (y1 - y0) > 2:  # Avoid accidental tiny clicks
            self.callback(int(x0), int(y0), int(x1), int(y1))
        else:
            self.callback(-1, -1, -1, -1)

    def on_freehand_click(self, event):
        """Place one lasso point, or close the loop near its first point."""
        x, y = self._canvas_point(event)

        if len(self.points) >= 3:
            first_x, first_y = self.points[0]
            distance = ((x - first_x) ** 2 + (y - first_y) ** 2) ** 0.5
            if distance <= self.close_distance:
                last_x, last_y = self.points[-1]
                self.canvas.create_line(
                    last_x, last_y, first_x, first_y,
                    fill="cyan", width=2, tags="selector",
                )
                if self.rubber_line_id is not None:
                    self.canvas.delete(self.rubber_line_id)
                    self.rubber_line_id = None
                closed_points = [
                    (int(point_x), int(point_y))
                    for point_x, point_y in self.points
                ]
                self.callback(closed_points)
                return

        if self.points:
            last_x, last_y = self.points[-1]
            self.canvas.create_line(
                last_x, last_y, x, y,
                fill="cyan", width=2, tags="selector",
            )

        self.points.append((x, y))
        self.canvas.create_oval(
            x - 3, y - 3, x + 3, y + 3,
            fill="cyan", outline="cyan", tags="selector",
        )

        if self.rubber_line_id is not None:
            self.canvas.delete(self.rubber_line_id)
        self.rubber_line_id = self.canvas.create_line(
            x, y, x, y,
            fill="cyan", width=2, dash=(4, 3), tags="selector",
        )

    def on_freehand_motion(self, event):
        """Rubber-band from the most recently placed point to the mouse."""
        if not self.points or self.rubber_line_id is None:
            return
        x, y = self._canvas_point(event)
        last_x, last_y = self.points[-1]
        self.canvas.coords(self.rubber_line_id, last_x, last_y, x, y)

    def on_cancel(self, _event=None):
        """Cancel a freehand selection without changing the image."""
        self.canvas.delete("selector")
        self.points = []
        self.rubber_line_id = None
        self.callback([])

# List of premade scenes to render
# credit https://github.com/RayTracing
SCENES_BOOK2 = [
    ("1", "1: Bouncing Spheres"),
    ("2", "2: Checkered Spheres"),
    ("3", "3: Earth Globe (Texture Map)"),
    ("4", "4: Perlin Noise Spheres"),
    ("5", "5: Planar Quads"),
    ("6", "6: Simple Light Box"),
    ("7", "7: Cornell Box"),
    ("8", "8: Cornell Box with Smoke"),
    ("9", "9: Final Complex Scene"),
]

# As this is a front end to a c++ ray tracing engine
#  we define the parameters needed for calling the tracer
#  with proper arguments  
BOOK_BINARIES = {
    "Book 1: In One Weekend": {
        "mac_dir": "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "binary": "inoneweekend",
        "has_scenes": False,
        "default_res": (672, 378),
        "book_id": 1,
    },
    "Book 2: The Next Week": {
        "mac_dir": "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "binary": "inoneweekend",
        "has_scenes": True,
        "default_res": (600, 600),
        "book_id": 2,
    },
    "Book 3: The Rest of Your Life": {
        "mac_dir": "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "binary": "inoneweekend",
        "has_scenes": False,
        "default_res": (600, 600),
        "book_id": 3,
    },
}

BOOK_SCENE_CHOICES = {
    "Book 1: In One Weekend": ["1: Default Book 1 Scene"],
    "Book 2: The Next Week": [label for _, label in SCENES_BOOK2],
    "Book 3: The Rest of Your Life": ["1: Default Book 3 Scene"],
}


class LiveRayTraceViewer(ToolView):
    """_summary_ The main class  program loop
    This program is a python front end to display the results
    of ray traced images, to alow post raytracing, image processing
    I.E. resizing, aspect ratio adjusts, color balance, etc.
    
    It wil also house a UI scene editor to create povray style scenes to send to
    the ra trace engine as well as the ability to read in and use povray files

    Alo proposed eventually ability to create video clips of ray traced frames 
    from animated gifs to short mp4s
    Args:
        ToolView (_type_): _description_
    """    
    title = "Live Progressive Ray-Tracer Studio"

    def build_ui(self):
        """_summary_ Build out the contents of the  Gui
        """        
        # 1. Left Controls Panel
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.debug_win: tk.Toplevel | None = None
        self.debug_console = None
        self.filepath = ""  #H for output file
        self._ignore_infile_change = False
        self.rendered_pixels = {}  # memory buffer of image being ray traced 
        self.current_width = 600      # to hold current image dimensions
        self.current_height = 600
        self.orig_image_width = 600     # Track orig un-modded dimensions
        self.orig_image_height = 600
        self.image_width = 600          # TBD
        self.image_height = 600
        self.is_rendering = False       # Is rendering in progress
        self.current_proc = None        # Tracks rendering process
        self.is_scaled = False          # Has image been scaled
        self.is_resized = False         # Has height/width been edited
        self.aspratio = "None/None"     # Has ap ration been edited
        self.blur = False               # Has blur been applied
        self.contour = False            # Think te next few are obvious
        self.smooth = False
        self.sharpen = False
        self.rotation = 0.0
        self.contrast = 1.0
        self.color = 1.0
        self.brightness = 1.0
        self.sharpness = 1.0
        self.scale_fac = 1.0
        self.source_image = None   #holds current pre edited image
        self.edit_base_image = None  # committed Crop/Zoom base
        self.current_transformed_image = None #holds edit progression of image
        self.live_photo = None   # Holds TKinter canvas ready copy of image
        self.sequence_images = []
        self.sequence_original_images = []
        self.sequence_paths = []
        self.sequence_index = 0
        self.sequence_playing = False
        self.sequence_after_id = None
        self.sequence_photo = None
        self.sequence_multi_edit_confirmed = False
        self.sequence_edit_in_progress = False
        self.sequence_edit_history = []
        self.sequence_undo_history = []
        self.sequence_generation = 0
        self.pov_scene_path = None
        self.sequence_fps_var = tk.IntVar(value=8)
        self.sequence_frame_var = tk.IntVar(value=0)
        self.image_stack = []    # Holds list  of Undue states
        self.stack_desc = []     # Holds matching list of triggering event
        self.stack_cnt = 0       # Same as len(image_stack)
        # A control edit has two phases:
        #   pending_snapshot = the state before the first change
        #   current object fields = the user's live, changing values
        # We keep the snapshot pending until another control/action starts.
        self.pending_control = None
        self.pending_snapshot = None
        self.form = self.add_form("Ray-Tracer Settings", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.last_rotation_value = self.rotation
        self.rotation_timer_id = None
        self.contrast_timer_id = None
        self.color_timer_id = None
        self.brightness_timer_id = None
        self.sharpness_timer_id = None
        self.scale_timer_id = None
        self.setup_menus()

        
        self.form.add_dropdown("aspratio", "Aspect Ratio", ["16/9", "16/10", "21/9", "4/3", "5/4", "None/None"], default="None/None", on_change=self.aspratio_auto_calc)
        
        spin_w = self.form.add_number("width", "Width (px)", min_val=100, max_val=8192, default=600, step=16)
        spin_w.bind("<Return>", self.resizedw_auto_calc)
        spin_w.bind("<FocusOut>", self.resizedw_auto_calc)
        spin_h = self.form.add_number("height", "Height (px)", min_val=100, max_val=8192, default=600, step=16)
        spin_h.bind("<Return>", self.resizedh_auto_calc)
        spin_h.bind("<FocusOut>", self.resizedh_auto_calc)
        self.form.add_number(
            "movie_frames", "Movie Frames", min_val=2, max_val=2000,
            default=48, step=1,
        )
#        self.stats.set_metrics({
#            "Active Feed": ("Not Selected", "info"),
#             "Input File": ("None", "warning"),
#            "Status": ("Ready", "success")
#        })
 # 2. Large Console Panel occupying the main window space
 #       self.console = self.add_console("Workspace Log & Output Stream", parent=self)
 #       self.console.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
 #       self.console.write_heading("CLEAN MAIN WINDOW")
 #       self.console.write_line("All parameter inputs, dropdowns, and file pickers have been moved to the menu.", "dim")
 #       self.console.write_line("Click 'Configuration' -> 'Open Input & File Dialog...' in the menu bar to set up parameters.\n", "primary")

        # Book Selection
        self.form.add_dropdown(
            "book",
            "Ray Tracing Book",
            options=list(BOOK_BINARIES.keys()),
            default="Book 2: The Next Week",
            on_change=self._on_book_changed,
        )

        # Scene Selection (Book 1 and 3 have a single default render, Book 2 has the 9 scene presets)
        self.scene_combo = self.form.add_dropdown(
            "scene",
            "Scene",
            options=BOOK_SCENE_CHOICES["Book 2: The Next Week"],
            default=BOOK_SCENE_CHOICES["Book 2: The Next Week"][0],
        )

        # Action Buttons
        self.form.add_button("Start Progressive Render ▶", callback=self.on_start_render, variant="primary")
        self.form.add_button("Start Homemade Render ▶", callback=self.on_click_render2, variant="primary")
      
        self.form.add_button("Render POV Still ▶", callback=self.on_click_povray_still, variant="primary")
        self.form.add_button("Render POV Camera Strip ▶", callback=self.on_click_povray_strip, variant="primary")
        self.form.add_button("Cancel / Stop Render ⏹", callback=self.on_stop_render, variant="outline")
        self.prog_bar = self.form.addCTkProgressBar("scan_progress", "Scan Progress", default=0.0)
        # 2. Right Canvas: Live Drawing Image Surface self.form.set_values({"infile": filepath}
        self.right_box = self.add_container(parent=self)
        self.right_box.grid(row=0, column=1, sticky="nsew")
        self.right_box.columnconfigure(0, weight=1)
        self.right_box.rowconfigure(0, weight=1)

        self.canvas_frame = ttk.Frame(self.right_box, style="Card.TFrame", padding=6)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")

        self.img_label = tk.Label(self.canvas_frame, bg="#11111b", text="Select Book & Scene, then click Start Render")
        self.img_label.pack(expand=True)

        # Playback strip for rendered image sequences.  It deliberately lives
        # outside the renderer so the same player can later feed GIF or MP4 export.
        sequence_bar = ttk.Frame(self.right_box, padding=(6, 4))
        sequence_bar.grid(row=1, column=0, sticky="ew")
        sequence_bar.columnconfigure(2, weight=1)

        ttk.Button(sequence_bar, text="▶ Play", command=self.on_play_sequence).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(sequence_bar, text="■ Stop", command=self.on_stop_sequence).grid(row=0, column=1, padx=(0, 10))

        self.sequence_scrubber = ttk.Scale(
            sequence_bar,
            from_=0,
            to=0,
            orient="horizontal",
            variable=self.sequence_frame_var,
            command=self.on_sequence_scrub,
        )
        self.sequence_scrubber.grid(row=0, column=2, sticky="ew", padx=(0, 10))

        ttk.Label(sequence_bar, text="FPS").grid(row=0, column=3, padx=(0, 3))
        self.sequence_fps_spin = ttk.Spinbox(
            sequence_bar,
            from_=1,
            to=60,
            width=4,
            textvariable=self.sequence_fps_var,
        )
        self.sequence_fps_spin.grid(row=0, column=4, padx=(0, 8))
        self.sequence_info_label = ttk.Label(sequence_bar, text="No sequence loaded")
        self.sequence_info_label.grid(row=0, column=5, sticky="e")

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
               # Top-level Menu: Configuration
        file_menu = self.menu("Configuration")
        file_menu.add_item(
            "Open Input & File Dialog... (Modal)",
            self.open_modal_inputs,
            shortcut="Ctrl+P"
        )
        file_menu.add_item(
            "Image settings",
            self.open_floating_window,
            shortcut="Ctrl+Shift+P"
        )
        file_menu.add_separator()
        file_menu.add_item("Exit", self.app.root.quit, shortcut="Alt+F4")
        file_menu.add_item(
            "Iamge Opering/Closing features",
            self.open_floating_window,
            shortcut="Ctrl+Shift+P"
        )
        file_menu.add_separator()
        file_menu.add_item("Exit Application <Alt-F4>", command=self.app.root.quit)
        self.bind_all("<Alt-F4>", lambda _event: self.app.root.quit())
        self.bind_all("<Control-p>", lambda _event: self.app.root.quit())
        # 3. VIEW MENU (With Toggle Checkboxes and Radio Groups)
        view_menu = self.menu("View")
        self.blur_var = view_menu.add_toggle("Blur", default=False, on_toggle=self.blur_auto_calc)
        self.contour_var = view_menu.add_toggle("Contour", default=False, on_toggle=self.contour_auto_calc)
        self.smooth_var = view_menu.add_toggle("Smooth", default=False, on_toggle=self.smooth_auto_calc)
        self.sharpen_var = view_menu.add_toggle("Sharpen", default=False, on_toggle=self.sharpen_auto_calc)
        view_menu.add_separator()
        self.debug_var = view_menu.add_toggle("Debug", default=False, on_toggle=self.open_debug_window)
        self.bind_all("<Control-d>", self.open_debug_window)
        tools_menu = self.menu("Edit")
        tools_menu.add_command(label="Image Adjustments 🎨 <Ctrl-a>", command=self.open_adjustments_window)
        self.bind_all("<Control-a>", self.open_adjustments_window)
        tools_menu.add_command(label="Zoom to Selection", command=self.zoom_select_window)
        tools_menu.add_command(label="Zoom In < [ >", command=self.zoom_in_window)
        self.bind_all("<KeyPress-bracketleft>", self.zoom_in_window)
        tools_menu.add_command(label="Zoom Out < ] >", command=self.zoom_out_window)   
        self.bind_all("<KeyPress-bracketright>", self.zoom_out_window)
        tools_menu.add_command(label="Bokeh effect <Ctrl-e>", command=self.bokeh_window)
        self.bind_all("<Control-e>", self.bokeh_window)
        tools_menu.add_command(label="Crop Window <Ctrl-b>", command=self.crop_window)
        self.bind_all("<Control-b>", self.crop_window)
        tm3 = tools_menu.add_command(label=f"Undu ({len(self.image_stack)}) <Ctrl-z>", command=self.stack_pop)
        self.bind_all("<Control-z>", self.stack_pop)
#        self.bind_all("<Shift-KeyPress-plus>", self.zoom_in_window)
  
    # =========================================================================
    # OPTION 1: MODAL POPUP DIALOG (self.prompt_form)
    # Recommended for straightforward configuration steps
    # =========================================================================
    def open_modal_inputs(self):
        pass
        # Opens popup dialog centered over the main window
        """        results = self.prompt_form(
            title="Configure Sources & File Pickers",
            form_builder_fn=build_inputs,
            size=(480, 420),
            ok_text="Apply & Ingest",
            cancel_text="Cancel"
        )
        if results:
            self.on_apply_inputs(results)
        """
    # =========================================================================
    # OPTION 2: PERSISTENT FLOATING WINDOW (tk.Toplevel)
    # Use if you want the window to stay open while working on the main screen
    # =========================================================================
    def open_floating_window(self):
        popup = tk.Toplevel(self)
        popup.title("Floating Configuration Palette")
        popup.geometry("480x440")
        popup.configure(bg=self.theme.get("bg", "#181825"))

        container = ttk.Frame(popup, style="Surface.TFrame", padding=14)
        container.pack(fill="both", expand=True)

        form = FormPanel(container, theme=self.theme)
        form.pack(fill="both", expand=True)


        form.add_button("Save Rendered Image 💾 <Ctrl-s>", callback=self.on_save_image, variant="primary")
        self.bind_all("<Control-s>", self.on_save_image)
        form.add_button("Export Sequence as GIF 🎞", callback=self.on_export_sequence_gif, variant="surface")
        form.add_button("Load Image Sequence 📂", callback=self.on_load_image_sequence, variant="surface")
        form.add_button("Load POV-Ray Scene 📂", callback=self.on_load_pov_scene, variant="surface")
        form.add_button("Save Edited Sequence 📂", callback=self.on_save_edited_sequence, variant="surface")

        form.add_file_picker("infile", "Pre Rendered Image to edit", default="", mode="open",on_change=self.on_file_selected)          

        # Action Buttons inside the popup
        def _on_submit():
            vals = form.get_values()
            self.on_apply_inputs(vals)
            popup.destroy()

        form.add_button("Execute with Selected Files", callback=_on_submit, variant="primary")

  
    def run_progressbarr(self, *args):
        """Smoothly animates the CTkProgressBar on a background thread without freezing GUI."""
        def _worker():
            for p in range(0, 101, 5):
                self.prog_bar.set(p / 100.0)
                time.sleep(0.04)
            return True

        def _on_done(res):
            self.on_run()
            self.set_status("Scan complete: 100% processed!")

        self.run_async(_worker, on_done=_on_done, status_msg="Running simulation scan...")

    def restore_def_ctrls(self):
        self.pending_control = None
        self.pending_snapshot = None
        self.last_rotation_value = self.rotation
        self.rotation_timer_id = None
        self.contrast_timer_id = None
        self.color_timer_id = None
        self.brightness_timer_id = None
        self.sharpness_timer_id = None
        self.scale_timer_id = None
        self.is_scaled = False          # Has image been scaled
        self.is_resized = False         # Has height/width been edited
        self.aspratio = "None/None"     # Has ap ration been edited
        self.blur = False               # Has blur been applied
        self.contour = False            # Think te next few are obvious
        self.smooth = False
        self.sharpen = False
        self.rotation = 0.0
        self.contrast = 1.0
        self.color = 1.0
        self.brightness = 1.0
        self.sharpness = 1.0
        self.scale_fac = 1.0
        self.debug_win: tk.Toplevel | None = None
        self.debug_console = None
        self.scan_progress = 0.45

    def close_debug_window(self):
        if self.debug_win is not None:
            self.debug_win.destroy()

        self.debug_win = None
        self.debug_console = None
        self.debug_var.set(False)
        
    def open_debug_window(self, state=None):
        win = self.debug_win

        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_force()
            if state == False:
                self.close_debug_window()
            return


        win = tk.Toplevel(self.app.root)
        win.title("Debug Data")
        win.geometry("520x520")
        self.debug_win = win
        win.protocol("WM_DELETE_WINDOW", self.close_debug_window)
        # This is a text console, not a form/input panel.
        self.debug_console = self.add_console(
            "Ray Tracer Debug Data",
            parent=cast(tk.Widget, win),
        )
        self.debug_console.pack(fill="both", expand=True, padx=8, pady=8)

        # Avoid holding references to widgets after the user closes the window.
        win.protocol("WM_DELETE_WINDOW", self.close_debug_window)
    

 
    def open_adjustments_window(self, event=None):
        # If the window is already open, just bring it to the front
        if getattr(self, "adjustments_win", None) and self.adjustments_win.winfo_exists():
            self.adjustments_win.lift()
            self.adjustments_win.focus_force()
            return

        # 1. Create a floating Toplevel window
        win = tk.Toplevel(self.app.root)
        win.title("Image Adjustments")
        win.geometry("360x520")
        self.adjustments_win = win

        # 2. Put a FormPanel inside the floating window
        adj_form = self.add_form("Live Adjustments", parent=cast(tk.Widget, win))
        adj_form.pack(fill="both", expand=True, padx=8, pady=8)
        self.adjustments_form = adj_form

        # 3. Add your sliders (callbacks only fire after the user finishes dragging or leaves the widget)
        adj_form.add_slider(
            "rotation", "Rotate (°)", min_val=0, max_val=360, step=1,
            default=self.rotation, on_change=self.on_rotation_change
        )

        adj_form.add_slider(
            "contrast", "Contrast", min_val=0.1, max_val=4.0, step=0.1,
            default=self.contrast, on_change=self.on_contrast_change
        )

        adj_form.add_slider(
            "color", "Color", min_val=0.1, max_val=1.0, step=0.1,
            default=self.color, on_change=self.on_color_change
        )

        adj_form.add_slider(
            "brightness", "Brightness", min_val=0.1, max_val=1.0, step=0.1,
            default=self.brightness, on_change=self.on_brightness_change
        )
        adj_form.add_slider(
            "sharpness", "Sharpness", min_val=0.1, max_val=2.0, step=0.1,
            default=self.sharpness, on_change=self.on_sharpness_change
        )
        adj_form.add_slider(
            "scalefac", "Scale Factor", min_val=0.1, max_val=10.0, step=0.1,
            default=self.scale_fac, on_change=self.on_scale_change
        )

  
 
    def _snapshot_editor_state(self, reason="Generic"):
        snapshot = {
            "reason": reason,
            "form_values": self.form.get_values().copy() if hasattr(self, "form") else {},
            "source_image": self.source_image.copy() if self.source_image is not None else None,
            "edit_base_image": self.edit_base_image.copy() if self.edit_base_image is not None else None,
            "current_transformed_image": self.current_transformed_image.copy() if self.current_transformed_image is not None else None,
            "rendered_pixels": {k: list(v) for k, v in (self.rendered_pixels or {}).items()},
            "current_width": self.current_width,
            "current_height": self.current_height,
            "orig_image_width": self.orig_image_width,
            "orig_image_height": self.orig_image_height,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "is_rendering": self.is_rendering,
            "is_scaled": self.is_scaled,
            "is_resized": self.is_resized,
            "aspratio": self.aspratio,
            "blur": self.blur,
            "contour": self.contour,
            "smooth": self.smooth,
            "sharpen": self.sharpen,
            "rotation": self.rotation,
            "contrast": self.contrast,
            "color": self.color,
            "brightness": self.brightness,
            "sharpness": self.sharpness,
            "scale_fac": self.scale_fac,
            "filepath": getattr(self, "filepath", ""),
        }
        return snapshot

    def _restore_editor_state(self, snapshot):
        if not snapshot:
            return

        self.source_image = snapshot.get("source_image")
        self.edit_base_image = snapshot.get("edit_base_image")
        self.current_transformed_image = snapshot.get("current_transformed_image")

        manual_image = snapshot.get("manual_image")
        if manual_image is not None:
            self.current_transformed_image = manual_image.copy() if hasattr(manual_image, "copy") else manual_image

        self.rendered_pixels = snapshot.get("rendered_pixels", {})
        self.current_width = snapshot.get("current_width", self.current_width)
        self.current_height = snapshot.get("current_height", self.current_height)
        self.orig_image_width = snapshot.get("orig_image_width", self.orig_image_width)
        self.orig_image_height = snapshot.get("orig_image_height", self.orig_image_height)
        self.image_width = snapshot.get("image_width", self.image_width)
        self.image_height = snapshot.get("image_height", self.image_height)
        self.is_rendering = snapshot.get("is_rendering", False)
        self.is_scaled = snapshot.get("is_scaled", False)
        self.is_resized = snapshot.get("is_resized", False)
        self.aspratio = snapshot.get("aspratio", self.aspratio)
        self.blur = snapshot.get("blur", self.blur)
        self.contour = snapshot.get("contour", self.contour)
        self.smooth = snapshot.get("smooth", self.smooth)
        self.sharpen = snapshot.get("sharpen", self.sharpen)
        self.rotation = snapshot.get("rotation", self.rotation)
        self.contrast = snapshot.get("contrast", self.contrast)
        self.color = snapshot.get("color", self.color)
        self.brightness = snapshot.get("brightness", self.brightness)
        self.sharpness = snapshot.get("sharpness", self.sharpness)
        self.scale_fac = snapshot.get("scale_fac", self.scale_fac)
        self.filepath = snapshot.get("filepath", getattr(self, "filepath", ""))
 
        form_values = snapshot.get("form_values", {})
        if form_values:
            self.form.set_values(form_values)

        self.blur_var.set(self.blur)
        self.contour_var.set(self.contour)
        self.smooth_var.set(self.smooth)
        self.sharpen_var.set(self.sharpen)

        adjustments_form = getattr(self, "adjustments_form", None)
        if adjustments_form is not None:
            try:
                if adjustments_form.winfo_exists():
                    adjustments_form.set_values({
                        "rotation": self.rotation,
                        "contrast": self.contrast,
                        "color": self.color,
                        "brightness": self.brightness,
                        "sharpness": self.sharpness,
                        "scalefac": self.scale_fac,
                    })
            except tk.TclError:
                self.adjustments_form = None


        preview_img = self.current_transformed_image or self.source_image or (self.buffer_to_img(self.rendered_pixels) if self.rendered_pixels else None)
        if preview_img is not None:
            photo = ImageTk.PhotoImage(preview_img)  # type: ignore[arg-type]
            self.live_photo = photo
            self.img_label.config(image=self.live_photo, text="")
        else:
            self.img_label.config(image="", text="Select Book & Scene, then click Start Render")

    def clear_stack(self):
        self.stack_cnt = 0
        self.image_stack.clear()
        self.stack_desc.clear()
        self.pending_control = None
        self.pending_snapshot = None
        
    def stack_pop(self,event=None):
        if self.sequence_images:
            if self.sequence_edit_in_progress:
                messagebox.showinfo("Undo", "Please let the current sequence edit finish first.")
                return
            if not self.sequence_undo_history:
                messagebox.showinfo("Undo", "There are (0) sequence Undos remaining.")
                return

            self.sequence_edit_history = self.sequence_undo_history.pop()
            history = list(self.sequence_edit_history)
            generation = self.sequence_generation
            visible_index = self.sequence_index
            visible_image = self._apply_sequence_history(
                self.sequence_original_images[visible_index], history
            )
            self.sequence_images[visible_index] = visible_image
            self.show_sequence_frame(visible_index)
            self.sequence_edit_in_progress = True
            originals = list(self.sequence_original_images)

            def worker():
                edited = [
                    self._apply_sequence_history(original, history)
                    for original in originals
                ]
                self.after(0, lambda: self._finish_sequence_edit(edited, generation, "Undo"))

            threading.Thread(target=worker, name="sequence-image-undo", daemon=True).start()
            return

        # Undo must include the edit currently being adjusted, even if the
        # user presses Undo before touching another control.
        if self.pending_snapshot is not None:
            self._commit_pending_edit()

        if not self.image_stack:
            self.stack_cnt = 0
            messagebox.showinfo("Undo", "There are (0) Undos remaining.")
            return

        snapshot = self.image_stack.pop()
        tmpdesc = self.stack_desc.pop()
        self.stack_cnt = len(self.image_stack)
        self._restore_editor_state(snapshot)
        return snapshot, tmpdesc

    def _commit_pending_edit(self):
        """Move the current control's one snapshot into the Undo stack.

        The snapshot represents the state *before* the control was changed.
        That is what makes Undo return to the state the user started from,
        regardless of how many intermediate slider values were tried.
        """
        if self.pending_snapshot is None:
            return
        self.image_stack.append(self.pending_snapshot)
        self.stack_desc.append(self.pending_control or "edit")
        self.stack_cnt += 1
        self.pending_control = None
        self.pending_snapshot = None

    def _begin_control_edit(self, control_name):
        """Start or continue an edit session for one named control.

        Re-entering the same control keeps the existing pending snapshot.
        Entering a different control first commits the previous session, so
        each logical control edit becomes exactly one Undo item.
        """
        if self.pending_control == control_name:
            return
        self._commit_pending_edit()
        self.pending_control = control_name
        self.pending_snapshot = self._snapshot_editor_state(control_name)
    
    def stack_add(self, img=None, reason="Generic"):
        # Crop, zoom, and similar actions call stack_add directly. They are
        # discrete actions, so commit any open slider session before recording
        # the new action's starting state.
        self._commit_pending_edit()
        snapshot = self._snapshot_editor_state(reason)
        if img is not None and not isinstance(img, dict):
            snapshot["manual_image"] = img.copy() if hasattr(img, "copy") else img
        self.image_stack.append(snapshot)
        self.stack_desc.append(reason)
        self.stack_cnt += 1

    def get_cur_img(self):
        if self.sequence_images:
            img = self.sequence_images[self.sequence_index]
        elif self.current_transformed_image is not None:
            img = self.current_transformed_image
        elif self.source_image is not None:
            img = self.source_image.copy()
        elif self.rendered_pixels:
            img = self.buffer_to_img(self.rendered_pixels)
        else:
            return None
        return img.copy()

    def _commit_discrete_image(self, image):
        """Make a Crop/Zoom result the next stable editing base."""
        if image is None:
            return

        self.edit_base_image = image.copy()
        self.current_transformed_image = image.copy()
        self.rotation = 0.0
        self.contrast = self.color = self.brightness = self.sharpness = 1.0
        self.scale_fac = 1.0
        self.blur = self.contour = self.smooth = self.sharpen = False
        self.is_scaled = self.is_resized = False
        self.aspratio = "None/None"
        self.image_width, self.image_height = image.size
        self.form.set_values({"width": self.image_width, "height": self.image_height, "aspratio": self.aspratio})
        self.blur_var.set(False)
        self.contour_var.set(False)
        self.smooth_var.set(False)
        self.sharpen_var.set(False)

        adjustments_form = getattr(self, "adjustments_form", None)
        if adjustments_form is not None:
            try:
                if adjustments_form.winfo_exists():
                    adjustments_form.set_values({
                        "rotation": self.rotation, "contrast": self.contrast,
                        "color": self.color, "brightness": self.brightness,
                        "sharpness": self.sharpness, "scalefac": self.scale_fac,
                    })
            except tk.TclError:
                self.adjustments_form = None
        self.update_live_preview()
    def zoom_in_window(self, event=None):
        img = self.get_cur_img()
        if img is None:
            return

        if self.sequence_images:
            self._submit_sequence_edit(
                f"zoom-in-{len(self.sequence_edit_history)}",
                "Zoom In",
                lambda frame: frame.resize(
                    (max(1, int(frame.width * 1.10)), max(1, int(frame.height * 1.10))),
                    Image.Resampling.LANCZOS,
                ),
            )
            return

        self.stack_add(img.copy(), "Zoom In")

        current = img.copy()
        new_size = (max(1, int(current.width * 1.10)),
                    max(1, int(current.height * 1.10)))

        zoomed = current.resize(new_size, Image.Resampling.LANCZOS)
        self._commit_discrete_image(zoomed)
        
    def zoom_out_window(self, event=None):
        img = self.get_cur_img()
        if img is None:
            return

        if self.sequence_images:
            self._submit_sequence_edit(
                f"zoom-out-{len(self.sequence_edit_history)}",
                "Zoom Out",
                lambda frame: frame.resize(
                    (max(1, int(frame.width * 0.90)), max(1, int(frame.height * 0.90))),
                    Image.Resampling.LANCZOS,
                ),
            )
            return

        self.stack_add(img.copy(), "Zoom Out")

        current = img.copy()
        new_size = (max(1, int(current.width * 0.90)),
                   max(1, int(current.height * 0.90)))

        zoomed = current.resize(new_size, Image.Resampling.LANCZOS)
        self._commit_discrete_image(zoomed)

    def zoom_select_window(self, event=None):
#       self.update_live_preview()
        img = self.get_cur_img()
        if img is None:
            return
        photo = ImageTk.PhotoImage(img)
        self.live_photo = photo
        self.img_label.config(image=self.live_photo, text="")
        img2 = self.get_cur_img()
        if not self.sequence_images:
            self.stack_add(img2, "Select Zoom")
        self.setup_zoom_image_workspace(self.live_photo,working_image=img)

    def bokeh_window(self, event=None):
         # 1. Start from clean RAM copy
        img = self.get_cur_img()
        if img is None:
            return

        photo = ImageTk.PhotoImage(img)
        self.live_photo = photo
        self.img_label.config(image=self.live_photo, text="")

        if not self.sequence_images:
            self.stack_add(img, "Bokehed")

        self.setup_bokeh_image_workspace(
        self.live_photo,
            working_image=img,
        )

    
    
    def crop_window(self, event=None):
         # 1. Start from clean RAM copy
        img = self.get_cur_img()
        if self.debug_console is not None:
            self.debug_console.write_line(f"In crop_window:\n" 
                                f"img = self.get_cur_img() returned: {img}")
        if img is None:
            return
        photo = ImageTk.PhotoImage(img)
        self.live_photo = photo
        self.img_label.config(image=self.live_photo, text="")
        img2 = self.get_cur_img()
        if not self.sequence_images:
            self.stack_add(img2, "Cropped")
        self.setup_image_workspace(self.live_photo,working_image=img)

 
    def _on_book_changed(self, selected_book: str):
        config = BOOK_BINARIES.get(selected_book, {})
        choices = BOOK_SCENE_CHOICES.get(selected_book, ["1: Default Scene"])
        self.scene_combo['values'] = choices
        self.scene_combo.set(choices[0])
        has_scenes = config.get("has_scenes", False)
        if has_scenes:
            self.scene_combo.config(state="readonly")
        else:
            self.scene_combo.config(state="readonly")

    def _clear_loaded_sequence(self):
        self.on_stop_sequence()
        self.sequence_generation += 1
        self.sequence_images = []
        self.sequence_original_images = []
        self.sequence_paths = []
        self.sequence_index = 0
        self.sequence_multi_edit_confirmed = False
        self.sequence_edit_in_progress = False
        self.sequence_edit_history = []
        self.sequence_undo_history = []
        self.sequence_frame_var.set(0)
        self.sequence_scrubber.configure(to=0)
        self.sequence_info_label.config(text="No sequence loaded")

    def _reset_editor_controls_for_new_source(self, width, height):
        """Reset edits when a static image or sequence becomes the new document."""
        self.pending_control = None
        self.pending_snapshot = None
        self.rotation = 0.0
        self.contrast = 1.0
        self.color = 1.0
        self.brightness = 1.0
        self.sharpness = 1.0
        self.scale_fac = 1.0
        self.blur = False
        self.contour = False
        self.smooth = False
        self.sharpen = False
        self.is_scaled = False
        self.is_resized = False
        self.aspratio = "None/None"
        self.current_width = width
        self.current_height = height
        self.orig_image_width = width
        self.orig_image_height = height
        self.image_width = width
        self.image_height = height

        self.form.set_values({
            "width": width,
            "height": height,
            "aspratio": self.aspratio,
        })
        self.blur_var.set(False)
        self.contour_var.set(False)
        self.smooth_var.set(False)
        self.sharpen_var.set(False)

        adjustments_form = getattr(self, "adjustments_form", None)
        if adjustments_form is not None:
            try:
                if adjustments_form.winfo_exists():
                    adjustments_form.set_values({
                        "rotation": self.rotation,
                        "contrast": self.contrast,
                        "color": self.color,
                        "brightness": self.brightness,
                        "sharpness": self.sharpness,
                        "scalefac": self.scale_fac,
                    })
            except tk.TclError:
                self.adjustments_form = None

    def _set_static_file_field(self, filepath):
        """Change the picker text without treating it as a new user selection."""
        self._ignore_infile_change = True
        try:
            self.form.set_values({"infile": filepath})
        finally:
            self._ignore_infile_change = False

    def on_file_selected(self, filepath: str):
        """Load one static image as a new editable document."""
        if self._ignore_infile_change:
            return
        if not filepath:
            return
        if (
            filepath == self.filepath
            and self.source_image is not None
            and not self.sequence_images
        ):
            return
        if self.is_rendering:
            messagebox.showinfo(
                "Rendering",
                "Stop the active render before loading a static image.",
            )
            self._set_static_file_field(self.filepath)
            return

        try:
            with Image.open(filepath) as image:
                loaded_image = image.copy()
        except Exception as exc:
            messagebox.showerror("Load Image", f"Could not open the selected image:\n{exc}")
            self.set_status(f"Error loading image: {exc}")
            self._set_static_file_field(self.filepath)
            return

        self._clear_loaded_sequence()
        self.clear_stack()
        self.rendered_pixels = {}
        self.source_image = loaded_image
        self.edit_base_image = None
        self.current_transformed_image = None
        self.filepath = filepath
        self._reset_editor_controls_for_new_source(*loaded_image.size)
        self.update_live_preview()
        self.set_status(f"Loaded static image: {os.path.basename(filepath)}")

    def update_live_preview(self, _=None):
        """Transforms the in-memory buffer and updates the preview."""
        if not self.rendered_pixels and self.source_image is None and self.current_transformed_image is None:
            return

        values = self.form.get_values()
        self.image_width = int(values.get("width", self.current_width))
        self.image_height = int(values.get("height", self.current_height))
        # 1. Start from the current working image so discrete edits like crop
        # and zoom become the new base for follow-up adjustments without
        # reapplying transforms to the original render.
        # Always rebuild a live adjustment from the unedited source/render
        # pixels. current_transformed_image is preview output only; using it
        # as input causes every active effect to compound on every callback.
        # Start from the currently edited image so the next transformation
        # works on the result of every previous transformation.
        if self.edit_base_image is not None:
            img = self.edit_base_image.copy()
        elif self.source_image is not None:
            img = self.source_image.copy()
        elif self.rendered_pixels:
            img = self.buffer_to_img(self.rendered_pixels)
        else:
            return
 
        # 2. Apply In-Memory Transformations
        if self.blur:
            img = img.filter(ImageFilter.BLUR)
        if self.smooth:
            img = img.filter(ImageFilter.SMOOTH)
        if self.contour:
            img = img.filter(ImageFilter.CONTOUR)
        if self.sharpen:
            img = img.filter(ImageFilter.SHARPEN)
        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)

        # Contrast
        if self.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast)
        # Color
        if self.color != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(self.color)
        # Brightness
        if self.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness)
        # Sharpness
        if self.sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(self.sharpness)

        # Scaling / Resize
        if self.is_scaled and self.scale_fac != 1.0:
            new_w = max(1, int(img.width * self.scale_fac))
            new_h = max(1, int(img.height * self.scale_fac))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        elif self.is_resized and (self.image_width != img.width or self.image_height != img.height):
            img = img.resize((self.image_width, self.image_height), Image.Resampling.LANCZOS)

        # 3. Store current transformed buffer & push to preview!
        self.current_transformed_image = img
        try:
            photo = ImageTk.PhotoImage(img)
            self.live_photo = photo
            self.img_label.config(image=self.live_photo, text="")
        except Exception as e:
            messagebox.showerror("Preview display error", str(e))

    def on_start_render(self, values: dict):
        if self.is_rendering:
            messagebox.showinfo("Rendering", "A render is already in progress. Stop it first if you want to start a new one.")
            return
        self._clear_loaded_sequence()
        self.clear_stack()
        book_name = values.get("book", "Book 2: The Next Week")
        scene_str = values.get("scene", SCENES_BOOK2[0][1])
        width = int(values.get("width", 600))
        height = int(values.get("height", 600))

        self.current_width = width
        self.current_height = height
        self.orig_image_width = width
        self.orig_image_height = height
        self.image_width = width
        self.image_height = height
        self.rendered_pixels = {}
        self.edit_base_image = None
        self.current_transformed_image = None
        self.source_image = None
        self.filepath = ""
        self._set_static_file_field("")

        # Reset PhotoImage
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")

        # Determine unified binary
        book_info = BOOK_BINARIES.get(book_name, BOOK_BINARIES["Book 2: The Next Week"])
        binary_name = book_info["binary"]
        book_id = int(book_info.get("book_id", 2))

        if IS_WINDOWS:
            # On Windows, run the Linux binary through WSL
            wsl_binary = f"{book_info['wsl_dir']}/{binary_name}"
            cmd = [
                "wsl",
                wsl_binary,
                "-b", str(book_id),
                # Pass both dimensions. If only width is passed, the C++
                # camera derives its own aspect-ratio height, which may not
                # match the PhotoImage allocated by this GUI.
                "-r", f"{width},{height}",
            ]
        else:
            # On Mac / POSIX, run the compiled binary directly
            mac_binary = f"{book_info['mac_dir']}/{binary_name}"
            if not os.path.exists(mac_binary):
                messagebox.showerror(
                    "Binary Not Found",
                    f"Executable not found:\n{mac_binary}\nPlease compile it first.",
                )
                return
            cmd = [
                mac_binary,
                "-b", str(book_id),
                # Keep native Mac output the same size as the GUI buffer.
                "-r", f"{width},{height}",
            ]

        if book_info.get("has_scenes", False):
            scene_num = scene_str.split(":")[0].strip()
            cmd.extend(["-c", scene_num])

        cmd.extend(["-p"])

        self.is_rendering = True
        self.start_time = time.time()
        
        raytimer = RayTraceTimer()

        def _render_stream():
            """Read one renderer scanline at a time on the worker thread.

            The C++ program writes a P3 header followed by lines in the form
            ``LINE row red green blue ...``. Tk widgets must only be changed
            on the main thread, so each parsed row is scheduled with
            ``root.after`` instead of being drawn here.
            """
            lines_drawn = 0
         
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                self.current_proc = proc
                if proc.stdout is None:
                    raise RuntimeError("Renderer did not provide stdout")
                stdout = proc.stdout

                # Skip header lines if P3 is sent
                first_line = stdout.readline()
                if "P3" in first_line:
                    stdout.readline()  # dimensions
                    stdout.readline()  # max val

                for line in stdout:
                    if not self.is_rendering:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    tokens = line.split()
                    if not tokens:
                        continue

                    if tokens[0] == "LINE" and len(tokens) > 2 and tokens[1].isdigit():
                        target_row = int(tokens[1])
                        pixel_tokens = tokens[2:]
                    else:
                        target_row = lines_drawn
                        pixel_tokens = tokens

                    nums = [int(t) for t in pixel_tokens if t.isdigit()]
                    if len(nums) >= 3:
                        hex_colors = []
                        row_rgb = []
                        for k in range(0, len(nums), 3):
                            if k + 2 < len(nums):
                                r, g, b = nums[k], nums[k + 1], nums[k + 2]
                                hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                                row_rgb.append((r, g, b))

                        self.rendered_pixels[target_row] = row_rgb
                        row_hex_string = "{" + " ".join(hex_colors) + "}"

                        r_idx = target_row
                        self.app.root.after(0, lambda r=r_idx, data=row_hex_string: self._draw_row(r, data, width, height))
                        lines_drawn += 1
                        if self.debug_console is not None:
                            msg = raytimer.report_progress(interval_seconds=10)
                            if msg:
                                self.debug_console.write_line(msg)
                proc.wait()
            except Exception as e:
                self.app.root.after(0, lambda err=e: self.set_status(f"Error: {err}"))
            finally:
                self.is_rendering = False
                self.current_proc = None
                elapsed = time.time() - self.start_time
                self.app.root.after(0, lambda el=elapsed, ld=lines_drawn, h=height: self.set_status(f"✨ Render Finished in {el:.2f}s ({ld}/{h} scanlines)"))
                if self.is_rendering == False and self.debug_console is not None:
                    self.debug_console.write(f'{raytimer.print_final()}')
        platform_label = "WSL" if IS_WINDOWS else "Native Mac"
        self.run_async(_render_stream, status_msg=f"Rendering {book_name} ({width}x{height}) via OpenMP ({platform_label})...")

    def on_load_pov_scene(self, event=None):
        chosen_path = filedialog.askopenfilename(
            title="Select POV-Ray Scene",
            filetypes=[("POV-Ray Scene", "*.pov"), ("All Files", "*.*")],
        )
        if not chosen_path:
            return False

        self.pov_scene_path = Path(chosen_path).resolve()
        self.set_status(f"POV-Ray scene loaded: {self.pov_scene_path.name}")
        if self.debug_console is not None:
            self.debug_console.write(f"Loaded POV-Ray scene: {self.pov_scene_path}\n")
        return True

    def _require_pov_scene(self):
        scene_path = self.pov_scene_path
        if scene_path is not None and scene_path.is_file():
            return scene_path
        if self.on_load_pov_scene():
            return self.pov_scene_path
        return None

    def _start_pov_render(self, frames, output_suffix):
        if self.is_rendering:
            messagebox.showinfo("Rendering", "A render is already in progress. Stop it first if you want to start a new one.")
            return
        
        self. run_progressbarr()
        scene_path = self._require_pov_scene()
        if scene_path is None:
            return

        self.clear_stack()
        self._scene_render_values = self.form.get_values()
        output_dir = None
        if frames is not None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            folder_name = f"{scene_path.stem}_{output_suffix}_{timestamp}"
            output_dir = scene_path.parent / "pov_frames" / folder_name
            suffix = 2
            while output_dir.exists():
                output_dir = scene_path.parent / "pov_frames" / f"{folder_name}_{suffix}"
                suffix += 1
            output_dir.mkdir(parents=True)
        self._pov_output_dir = output_dir
        self._pov_render_queue = iter(self._build_pov_render_queue([
            {
                "template_path": scene_path,
                "frames": frames,
                "output_prefix": f"{scene_path.stem}_{output_suffix}",
                "output_dir": output_dir,
            },
        ]))
        self._start_next_povray_scene_render()

    def _requested_scene1_frames(self):
        """Build this render's frame list from the shared keyframe skeleton."""
        values = self.form.get_values()
        try:
            total_frames = int(values.get("movie_frames", 48))
            return make_scene1(
                ri.scene1_keyframes,
                ri.common_scene1_settings,
                total_frames=total_frames,
            )
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Movie Frames", f"Could not generate the camera path:\n{exc}")
            return None

    def on_click_povray_still(self, argument=None):
        self._start_pov_render(frames=None, output_suffix="still")

    def on_click_povray_strip(self, argument=None):
        frames = self._requested_scene1_frames()
        if frames is not None:
            self._start_pov_render(frames=frames, output_suffix="strip")

    # Compatibility for any existing binding that still references this name.
    def on_click_povray(self, argument=None):
        self.on_click_povray_still(argument)
        
    def on_click_render2(self, argument=None):
        if self.is_rendering:
            messagebox.showinfo("Rendering", "A render is already in progress. Stop it first if you want to start a new one.")
            return

        self.clear_stack()
        self._scene_render_values = self.form.get_values()
        book_name = self._scene_render_values.get("book", "Book 2: The Next Week")
        scene_str = self._scene_render_values.get("scene", SCENES_BOOK2[0][1])
        book_info = BOOK_BINARIES.get(book_name, BOOK_BINARIES["Book 2: The Next Week"])
        scene_num = scene_str.split(":")[0].strip()
        frames = self._requested_scene1_frames()
        if frames is None:
            return

        book_id = str(book_info.get("book_id", 2))
        scene_id = scene_num if book_info.get("has_scenes", False) else "default"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        folder_name = f"book{book_id}_scene{scene_id}_{timestamp}"
        output_dir = RAYTRACE_SRC_DIR / "scene_data" / folder_name
        suffix = 2
        while output_dir.exists():
            output_dir = RAYTRACE_SRC_DIR / "scene_data" / f"{folder_name}_{suffix}"
            suffix += 1
        output_dir.mkdir(parents=True)
        self._homemade_output_dir = output_dir

        # The camera path supplies the changing camera values. The selected
        # Book and Scene supply the actual subject rendered in every frame.
        for frame_number, frame in enumerate(frames, start=1):
            frame["filename"] = (
                Path("scene_data") / output_dir.name / f"frame_{frame_number:04d}.ppm"
            ).as_posix()
            frame["book"] = book_id
            frame["chapter"] = scene_num

        self._scene_render_queue = iter(frames)
        self._start_next_scene_render()

    def _start_next_povray_scene_render(self):
        self.run_progressbarr()
        try:
            render_job = next(self._pov_render_queue)
        except StopIteration:
            output_dir = getattr(self, "_pov_output_dir", None)
            if output_dir is None:
                self.set_status("✨ POV-Ray still finished.")
            else:
                self.set_status(f"✨ All POV-Ray frames finished: {output_dir}")
            return
        except Exception as exc:
            messagebox.showerror("POV-Ray Setup Error", str(exc))
            self.set_status(f"POV-Ray setup error: {exc}")
            return

        try:
            template_path = render_job["template_path"]
            frame = render_job["frame"]
            if frame is None:
                pov_input_path = template_path
            else:
                pov_input_path = template_path.with_name("__active_frame.pov")
                self._write_pov_camera_frame(template_path, pov_input_path, frame)
        except Exception as exc:
            messagebox.showerror("POV-Ray Template Error", str(exc))
            self.set_status(f"POV-Ray template error: {exc}")
            return

        render_args = [
            f"+I{pov_input_path.name}",
            "+FP",
            "Compression=0",
            "-o-",
        ]
        if self.debug_console is not None:
            self.debug_console.write(f"Starting frame: {' '.join(render_args)}\n\n")

        self.on_start_render_povray(
            self._scene_render_values,
            render_args,
            output_path=render_job["output_path"],
            frame_label=render_job["label"],
            working_dir=template_path.parent,
            on_complete=self._start_next_povray_scene_render,
        )

    def _build_pov_render_queue(self, jobs):
        """Expand one still job or one camera-path job into renderable frames."""
        for job in jobs:
            template_path = Path(job["template_path"])
            if not template_path.is_file():
                raise FileNotFoundError(f"POV-Ray scene file was not found: {template_path}")

            output_dir = job.get("output_dir") or template_path.parent / "pov_frames"
            prefix = job.get("output_prefix", template_path.stem)
            frames = job.get("frames")
            if frames is None:
                yield {
                    "template_path": template_path,
                    "frame": None,
                    # A one-off still is kept in the live preview and can be
                    # saved through Save Image. Do not create a movie folder.
                    "output_path": None,
                    "label": template_path.name,
                }
                continue

            for index, frame in enumerate(frames, start=1):
                yield {
                    "template_path": template_path,
                    "frame": frame,
                    "output_path": output_dir / f"{prefix}_{index:04d}.ppm",
                    "label": f"{template_path.name} frame {index}/{len(frames)}",
                }

    @staticmethod
    def _pov_vector(value):
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
        else:
            parts = [str(part) for part in value]
        if len(parts) != 3:
            raise ValueError(f"POV-Ray camera vectors need three values, got {value!r}")
        return "<" + ", ".join(parts) + ">"

    @staticmethod
    def _windows_path_to_wsl(path):
        resolved_path = Path(path).resolve()
        drive = resolved_path.drive.rstrip(":").lower()
        if not drive:
            raise ValueError(f"Cannot convert {resolved_path} to a WSL path.")
        return "/mnt/" + drive + resolved_path.as_posix()[2:]

    def _write_pov_camera_frame(self, template_path, output_path, frame):
        """Copy a normal POV scene and replace only its first camera block."""
        scene_text = template_path.read_text(encoding="utf-8")
        camera_match = re.search(r"\bcamera\s*\{", scene_text, flags=re.IGNORECASE)
        if camera_match is None:
            raise ValueError(f"No camera {{ ... }} block was found in {template_path.name}.")

        open_brace = scene_text.find("{", camera_match.start())
        depth = 0
        close_brace = None
        for index in range(open_brace, len(scene_text)):
            if scene_text[index] == "{":
                depth += 1
            elif scene_text[index] == "}":
                depth -= 1
                if depth == 0:
                    close_brace = index
                    break
        if close_brace is None:
            raise ValueError(f"The first camera block in {template_path.name} has no closing brace.")

        camera_block = scene_text[camera_match.start():close_brace + 1]
        camera_vector = self._pov_vector(frame["camera"])
        lookat_vector = self._pov_vector(frame["lookat"])
        vfov = str(frame.get("vfov", 45))

        camera_block, locations = re.subn(
            r"(\blocation\s*)<[^>]*>",
            lambda match: match.group(1) + camera_vector,
            camera_block,
            count=1,
            flags=re.IGNORECASE,
        )
        camera_block, lookats = re.subn(
            r"(\blook_at\s*)<[^>]*>",
            lambda match: match.group(1) + lookat_vector,
            camera_block,
            count=1,
            flags=re.IGNORECASE,
        )
        if not locations or not lookats:
            raise ValueError(
                f"{template_path.name} must have location <x,y,z> and look_at <x,y,z> in its first camera block."
            )

        camera_block, angles = re.subn(
            r"(\bangle\s+)[^\s}]+",
            lambda match: match.group(1) + vfov,
            camera_block,
            count=1,
            flags=re.IGNORECASE,
        )
        if not angles:
            camera_block = camera_block[:-1] + f"\n  angle {vfov}\n}}"

        output_path.write_text(
            scene_text[:camera_match.start()] + camera_block + scene_text[close_brace + 1:],
            encoding="utf-8",
        )
        
    def _start_next_scene_render(self):
        """Start one movie frame; the completion callback starts the next."""
        try:
            scene = next(self._scene_render_queue)
        except StopIteration:
            output_dir = getattr(self, "_homemade_output_dir", None)
            if output_dir is None:
                self.set_status("✨ All scene frames finished.")
            else:
                self.set_status(f"✨ All scene frames finished: {output_dir}")
            return

        width = int(self._scene_render_values.get("width", 600))
        height = int(self._scene_render_values.get("height", 600))
        book_name = self._scene_render_values.get("book", "Book 2: The Next Week")
        book_info = BOOK_BINARIES.get(book_name, BOOK_BINARIES["Book 2: The Next Week"])

        render_args = [
            "-o", scene["filename"],
            "-b", scene["book"],
            "--light", scene["light1"],
            "--light", scene["light2"],
            "--camera", scene["camera"],
            "--look-at", scene["lookat"],
            "--vfov", scene["vfov"],
            "-r", f"{width},{height}",
        ]
        if book_info.get("has_scenes", False):
            render_args.extend(["-c", scene["chapter"]])
        render_args.append("-p")

        if self.debug_console is not None:
            self.debug_console.write(f"Starting frame: {' '.join(render_args)}\n\n")

        self.on_start_render2(
            self._scene_render_values,
            render_args,
            on_complete=self._start_next_scene_render,
        )

    def on_start_render2(self, values: dict, render_args: list[str], on_complete=None):
        if self.is_rendering:
            messagebox.showinfo("Rendering", "A render is already in progress. Stop it first if you want to start a new one.")
            return
        self._clear_loaded_sequence()

        width = int(values.get("width", 600))
        height = int(values.get("height", 600))
#RON HERE
        self.current_width = width
        self.current_height = height
        self.orig_image_width = width
        self.orig_image_height = height
        self.image_width = width
        self.image_height = height
        self.rendered_pixels = {}
        self.edit_base_image = None
        self.current_transformed_image = None
        self.source_image = None
        self.filepath = ""
        self._set_static_file_field("")

        # Reset PhotoImage
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")
        book_name = values.get("book", "Book 2: The Next Week")
        book_info = BOOK_BINARIES.get(book_name, BOOK_BINARIES["Book 2: The Next Week"])
        binary_name = book_info["binary"]

        if IS_WINDOWS:
            # On Windows, run the Linux binary through WSL
            wsl_binary = f"{book_info['wsl_dir']}/{binary_name}"
            cmd = ["wsl", wsl_binary, *render_args]
        else:
            # On Mac / POSIX, run the compiled binary directly
            mac_binary = f"{book_info['mac_dir']}/{binary_name}"
            if not os.path.exists(mac_binary):
                messagebox.showerror(
                    "Binary Not Found",
                    f"Executable not found:\n{mac_binary}\nPlease compile it first.",
                )
                return
            cmd = [mac_binary, *render_args]

        if self.debug_console is not None:
            self.debug_console.write(f'In on_render 2, cmd={cmd}')
   #     cmd.extend(["-p"])

        self.is_rendering = True
        self.start_time = time.time()
        
        raytimer = RayTraceTimer()

        def _render_stream():
            """Read one renderer scanline at a time on the worker thread.

            The C++ program writes a P3 header followed by lines in the form
            ``LINE row red green blue ...``. Tk widgets must only be changed
            on the main thread, so each parsed row is scheduled with
            ``root.after`` instead of being drawn here.
            """
            lines_drawn = 0
            completed = False
            render_error = None
         
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    cwd=RAYTRACE_SRC_DIR,
                )
                self.current_proc = proc
                if proc.stdout is None:
                    raise RuntimeError("Renderer did not provide stdout")
                stdout = proc.stdout

                # Skip header lines if P3 is sent
                first_line = stdout.readline()
                if "P3" in first_line:
                    stdout.readline()  # dimensions
                    stdout.readline()  # max val

                for line in stdout:
                    if not self.is_rendering:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    tokens = line.split()
                    if not tokens:
                        continue

                    if tokens[0] == "LINE" and len(tokens) > 2 and tokens[1].isdigit():
                        target_row = int(tokens[1])
                        pixel_tokens = tokens[2:]
                    else:
                        target_row = lines_drawn
                        pixel_tokens = tokens

                    nums = [int(t) for t in pixel_tokens if t.isdigit()]
                    if len(nums) >= 3:
                        hex_colors = []
                        row_rgb = []
                        for k in range(0, len(nums), 3):
                            if k + 2 < len(nums):
                                r, g, b = nums[k], nums[k + 1], nums[k + 2]
                                hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                                row_rgb.append((r, g, b))

                        self.rendered_pixels[target_row] = row_rgb
                        row_hex_string = "{" + " ".join(hex_colors) + "}"

                        r_idx = target_row
                        self.app.root.after(0, lambda r=r_idx, data=row_hex_string: self._draw_row(r, data, width, height))
                        lines_drawn += 1
                        if self.debug_console is not None:
                            msg = raytimer.report_progress(interval_seconds=10)
                            if msg:
                                self.debug_console.write_line(msg)
                return_code = proc.wait()
                if return_code != 0:
                    stderr_text = proc.stderr.read() if proc.stderr is not None else ""
                    raise RuntimeError(
                        f"Renderer exited with code {return_code}: {stderr_text.strip()}"
                    )
                completed = self.is_rendering
            except Exception as e:
                render_error = e
            finally:
                elapsed = time.time() - self.start_time
                if self.debug_console is not None:
                    self.debug_console.write(f'{raytimer.print_final()}')

                def finish_render():
                    self.is_rendering = False
                    self.current_proc = None
                    if render_error is not None:
                        self.set_status(f"Render error: {render_error}")
                    elif not completed:
                        self.set_status("⏹ Render stopped by user.")
                    elif on_complete is not None:
                        on_complete()
                    else:
                        self.set_status(f"✨ Render Finished in {elapsed:.2f}s ({lines_drawn}/{height} scanlines)")

                self.app.root.after(0, finish_render)
        platform_label = "WSL" if IS_WINDOWS else "Native Mac"
        self.run_async(_render_stream, status_msg=f"Rendering an image ({width}x{height}) via OpenMP ({platform_label})...")


    def on_start_render_povray(
        self,
        values: dict,
        render_args: list[str],
        output_path: Path | None = None,
        frame_label: str = "POV-Ray scene",
        working_dir: Path | None = None,
        on_complete=None,
    ):
        if self.is_rendering:
            messagebox.showinfo("Rendering", "A render is already in progress. Stop it first if you want to start a new one.")
            return
        self._clear_loaded_sequence()

        width = 600
        height = 600

        self.current_width = width
        self.current_height = height
        self.orig_image_width = width
        self.orig_image_height = height
        self.image_width = width
        self.image_height = height
        self.rendered_pixels = {}
        self.edit_base_image = None
        self.current_transformed_image = None
        self.source_image = None
        self.filepath = ""
        self._set_static_file_field("")

        # Reset PhotoImage
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")
        binary_name = "povray"
        working_dir = Path(working_dir or Path(__file__).resolve().parent).resolve()
        popen_cwd = None

        if IS_WINDOWS:
            # POV-Ray is on the WSL PATH. --cd makes relative #include files,
            # the selected scene, and __active_frame.pov resolve together.
            cmd = ["wsl", "--cd", self._windows_path_to_wsl(working_dir), binary_name, *render_args]
        else:
            # Native POV-Ray is expected to be on the Mac/POSIX PATH.
            cmd = [binary_name, *render_args]
            popen_cwd = str(working_dir)

        if self.debug_console is not None:
            self.debug_console.write(f'In on_render povray, cmd={cmd}')
   #     cmd.extend(["-p"])

        self.is_rendering = True
        self.start_time = time.time()
        
        raytimer = RayTraceTimer()

        def _render_stream():
            """Read ASCII or binary POV-Ray pixels and schedule Tk preview rows."""

            lines_drawn = 0
            completed = False
            render_error = None
            proc = None
         
            try:
                stats_path = working_dir / "render_stats.txt"
                with open(stats_path, "w", encoding="utf-8", errors="replace") as stats_file:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=stats_file,
                        text=False,
                        cwd=popen_cwd,
                    )
                    self.current_proc = proc
                    if proc.stdout is None:
                        raise RuntimeError("POV-Ray did not provide stdout")
                    stdout = proc.stdout

                    width, height, rows = _read_pov_ppm(stdout)

                    # Replace the temporary preview with the actual dimensions.
                    self.current_width = width
                    self.current_height = height
                    self.orig_image_width = width
                    self.orig_image_height = height
                    self.image_width = width
                    self.image_height = height
                    self.app.root.after(0, lambda w=width, h=height: self._prepare_pov_preview(w, h))

                    completed_rows = []
                    for row_rgb in rows:
                        if not self.is_rendering:
                            break
                        self.rendered_pixels[lines_drawn] = row_rgb
                        completed_rows.append(row_rgb)
                        row_hex_string = "{" + " ".join(
                            f"#{r:02x}{g:02x}{b:02x}" for r, g, b in row_rgb
                        ) + "}"
                        self.app.root.after(
                            0,
                            lambda r=lines_drawn, data=row_hex_string, w=width, h=height:
                                self._draw_row(r, data, w, h),
                        )
                        lines_drawn += 1
                        if self.debug_console is not None:
                            msg = raytimer.report_progress(interval_seconds=10)
                            if msg:
                                self.debug_console.write_line(msg)

                    if not self.is_rendering and proc.poll() is None:
                        proc.kill()
                    return_code = proc.wait()
                if lines_drawn != height:
                    raise RuntimeError(
                        f"POV-Ray PPM stream contained {lines_drawn} rows; expected {height}. See {stats_path} for details."
                    )
                if return_code != 0:
                    raise RuntimeError(
                        f"POV-Ray exited with code {return_code}. See {stats_path} for details."
                    )
                if output_path is not None:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    completed_image = Image.new("RGB", (width, height))
                    completed_image.putdata([pixel for row in completed_rows for pixel in row])
                    completed_image.save(output_path)
                completed = self.is_rendering
            except Exception as e:
                render_error = RuntimeError(f"{e} See {working_dir / 'render_stats.txt'} for POV-Ray details.")
            finally:
                if proc is not None:
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait()
                    if proc.stdout is not None:
                        proc.stdout.close()
                elapsed = time.time() - self.start_time
                if self.debug_console is not None:
                    self.debug_console.write(f'{raytimer.print_final()}')

                def finish_render():
                    self.is_rendering = False
                    self.current_proc = None
                    if render_error is not None:
                        self.set_status(f"Render error: {render_error}")
                    elif not completed:
                        self.set_status("⏹ Render stopped by user.")
                    elif on_complete is not None:
                        self.set_status(f"✨ Finished {frame_label}; starting next POV-Ray frame...")
                        on_complete()
                    else:
                        self.set_status(f"✨ Render Finished in {elapsed:.2f}s ({lines_drawn}/{height} scanlines)")

                self.app.root.after(0, finish_render)
        platform_label = "WSL" if IS_WINDOWS else "Native Mac"
        self.run_async(_render_stream, status_msg=f"Rendering an image ({width}x{height}) via OpenMP ({platform_label})...")
       
    def _prepare_pov_preview(self, width, height):
        """Create the Tk image after the POV-Ray PPM header reveals its size."""
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")

       
    def _draw_row(self, row_idx, row_hex_string, width, height):
        try:
            if self.live_photo is None:
                return
            # PhotoImage.put exists at runtime, but Tkinter's type stubs do
            # not expose it consistently. The cast documents that this is a
            # deliberate use of Tk's dynamic API, not an optional image bug.
            photo = cast(Any, self.live_photo)
            photo.put(row_hex_string, to=(0, row_idx, width, row_idx + 1))
            drawn_count = len(self.rendered_pixels)
            pct = (drawn_count / height) * 100
            elapsed = time.time() - self.start_time
            self.set_status(f"⚡ Live Rendering: {pct:.1f}% ({drawn_count}/{height} rows) - {elapsed:.1f}s")
        except Exception:
            pass

    def on_stop_render(self, values: dict | None = None):
        if self.is_rendering and self.current_proc:
            self.is_rendering = False
            try:
                self.current_proc.terminate()
            except Exception:
                pass
            self.set_status("⏹ Render stopped by user.")

    @staticmethod
    def _natural_path_key(path):
        """Sort image1, image2 ... image10 in their visual frame order."""
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", os.path.basename(path))
        ]

    def on_load_image_sequence(self, event=None):
        if self.is_rendering:
            messagebox.showinfo(
                "Rendering",
                "Stop the active render before loading an image sequence.",
            )
            return

        paths = filedialog.askopenfilenames(
            title="Select Rendered Frames",
            filetypes=[
                ("Image Files", "*.ppm;*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff"),
                ("All Files", "*.*"),
            ],
        )
        if not paths:
            return

        loaded_images = []
        loaded_paths = []
        failures = []
        for path in sorted(paths, key=self._natural_path_key):
            try:
                with Image.open(path) as image:
                    loaded_images.append(image.convert("RGB").copy())
                    loaded_paths.append(path)
            except Exception as exc:
                failures.append(f"{os.path.basename(path)}: {exc}")

        if not loaded_images:
            messagebox.showerror("Load Image Sequence", "None of the selected files could be opened.")
            return

        self.on_stop_sequence()
        # A newly loaded frame sequence is a new document, so old image undo
        # snapshots must never be allowed to modify one of its frames.
        self.clear_stack()
        self.sequence_generation += 1
        self.sequence_multi_edit_confirmed = False
        self.sequence_edit_in_progress = False
        self.sequence_edit_history = []
        self.sequence_undo_history = []
        self.sequence_original_images = [image.copy() for image in loaded_images]
        self.sequence_images = loaded_images
        self.sequence_paths = loaded_paths
        self.sequence_index = 0
        self.rendered_pixels = {}
        self.source_image = None
        self.edit_base_image = None
        self.current_transformed_image = None
        self.filepath = ""
        self._set_static_file_field("")
        self._reset_editor_controls_for_new_source(*loaded_images[0].size)
        self.sequence_scrubber.configure(to=len(loaded_images) - 1)
        self.sequence_frame_var.set(0)
        self.show_sequence_frame(0)

        if failures:
            messagebox.showwarning(
                "Some Frames Were Skipped",
                "The usable frames were loaded, but these files could not be read:\n\n" + "\n".join(failures),
            )

    def _confirm_sequence_multi_edit(self):
        """Ask once before allowing edits to affect the loaded sequence."""
        if not self.sequence_images:
            return False
        if self.sequence_multi_edit_confirmed:
            return True

        confirmed = messagebox.askyesno(
            "Edit Entire Sequence",
            "Apply this edit to every image in the loaded sequence?\n\n"
            "The edited frames will stay in memory until you save them.",
            parent=self.winfo_toplevel(),
        )
        if confirmed:
            self.sequence_multi_edit_confirmed = True
        return confirmed

    @staticmethod
    def _apply_sequence_history(image, history):
        result = image.copy()
        for edit in history:
            result = edit["transform"](result)
        return result

    def _submit_sequence_edit(self, key, description, transform, replace=False, remove=False):
        """Apply one captured edit recipe to the visible frame and then the rest."""
        if not self.sequence_images:
            return False
        if self.sequence_edit_in_progress:
            messagebox.showinfo(
                "Sequence Edit In Progress",
                "Please let the current sequence edit finish before starting another.",
                parent=self.winfo_toplevel(),
            )
            return False
        if not self._confirm_sequence_multi_edit():
            return False

        previous_history = list(self.sequence_edit_history)
        new_history = list(previous_history)
        existing_index = next((i for i, edit in enumerate(new_history) if edit["key"] == key), None)

        if remove:
            if existing_index is not None:
                new_history.pop(existing_index)
        else:
            edit = {"key": key, "description": description, "transform": transform}
            if replace and existing_index is not None:
                new_history[existing_index] = edit
            else:
                new_history.append(edit)

        if new_history == previous_history:
            return True

        self.sequence_undo_history.append(previous_history)
        self.sequence_edit_history = new_history
        self.sequence_edit_in_progress = True
        self.on_stop_sequence()
        generation = self.sequence_generation
        visible_index = self.sequence_index

        visible_image = self._apply_sequence_history(
            self.sequence_original_images[visible_index], new_history
        )
        self.sequence_images[visible_index] = visible_image
        self.show_sequence_frame(visible_index)
        self.sequence_info_label.config(
            text=f"Editing sequence… 1/{len(self.sequence_images)}"
        )

        originals = list(self.sequence_original_images)

        def worker():
            edited = [None] * len(originals)
            edited[visible_index] = visible_image
            try:
                for index, original in enumerate(originals):
                    if index == visible_index:
                        continue
                    edited[index] = self._apply_sequence_history(original, new_history)
            except Exception as exc:
                self.after(0, lambda error=exc: self._finish_sequence_edit_error(error, generation))
                return
            self.after(0, lambda: self._finish_sequence_edit(edited, generation, description))

        threading.Thread(target=worker, name="sequence-image-edit", daemon=True).start()
        return True

    def _finish_sequence_edit(self, edited_images, generation, description):
        if generation != self.sequence_generation:
            return
        self.sequence_images = edited_images
        self.sequence_edit_in_progress = False
        self.show_sequence_frame(self.sequence_index)
        self.set_status(f"Applied {description} to {len(edited_images)} sequence frames in memory.")

    def _finish_sequence_edit_error(self, error, generation):
        if generation != self.sequence_generation:
            return
        self.sequence_edit_in_progress = False
        if self.sequence_undo_history:
            self.sequence_edit_history = self.sequence_undo_history.pop()
        self.sequence_images[self.sequence_index] = self._apply_sequence_history(
            self.sequence_original_images[self.sequence_index], self.sequence_edit_history
        )
        messagebox.showerror(
            "Sequence Edit Error",
            f"The sequence edit could not be completed:\n{error}",
            parent=self.winfo_toplevel(),
        )
        self.show_sequence_frame(self.sequence_index)

    def on_save_edited_sequence(self, event=None):
        if not self.sequence_images:
            messagebox.showinfo("Save Edited Sequence", "Load an image sequence first.")
            return
        if self.sequence_edit_in_progress:
            messagebox.showinfo(
                "Save Edited Sequence",
                "Please wait for the current sequence edit to finish.",
            )
            return

        output_dir = filedialog.askdirectory(title="Select Folder for Edited Sequence")
        if not output_dir:
            return

        failures = []
        for index, image in enumerate(self.sequence_images):
            original_name = os.path.basename(self.sequence_paths[index])
            output_path = os.path.join(output_dir, original_name)
            try:
                image.save(output_path)
            except Exception as exc:
                failures.append(f"{original_name}: {exc}")

        saved_count = len(self.sequence_images) - len(failures)
        if failures:
            messagebox.showwarning(
                "Sequence Save Completed with Errors",
                f"Saved {saved_count}/{len(self.sequence_images)} frames.\n\n" + "\n".join(failures),
            )
        else:
            messagebox.showinfo(
                "Edited Sequence Saved",
                f"Saved {saved_count} edited frames to:\n{output_dir}",
            )
        self.set_status(f"Saved {saved_count} edited sequence frames.")

    def show_sequence_frame(self, frame_index):
        if not self.sequence_images:
            return

        frame_index = max(0, min(int(frame_index), len(self.sequence_images) - 1))
        self.sequence_index = frame_index
        image = self.sequence_images[frame_index]
        self.sequence_photo = ImageTk.PhotoImage(image)
        self.live_photo = self.sequence_photo
        self.img_label.config(image=self.sequence_photo, text="")
        self.sequence_frame_var.set(frame_index)
        self.sequence_info_label.config(
            text=f"Frame {frame_index + 1}/{len(self.sequence_images)}  {image.width}x{image.height}"
        )

    def on_sequence_scrub(self, value):
        if self.sequence_images:
            self.show_sequence_frame(round(float(value)))

    def _sequence_fps(self):
        try:
            return max(1, min(60, int(self.sequence_fps_var.get())))
        except (ValueError, tk.TclError):
            self.sequence_fps_var.set(8)
            return 8

    def on_play_sequence(self):
        if not self.sequence_images:
            messagebox.showinfo("Image Sequence", "Load rendered frames first.")
            return
        if self.sequence_playing:
            return

        self.sequence_playing = True
        self._play_sequence_tick()

    def _play_sequence_tick(self):
        if not self.sequence_playing or not self.sequence_images:
            return

        self.show_sequence_frame(self.sequence_index)
        self.sequence_index = (self.sequence_index + 1) % len(self.sequence_images)
        interval_ms = round(1000 / self._sequence_fps())
        self.sequence_after_id = self.after(interval_ms, self._play_sequence_tick)

    def on_stop_sequence(self):
        self.sequence_playing = False
        if self.sequence_after_id is not None:
            try:
                self.after_cancel(self.sequence_after_id)
            except tk.TclError:
                pass
            self.sequence_after_id = None

    def on_export_sequence_gif(self, event=None):
        if not self.sequence_images:
            messagebox.showinfo("Export GIF", "Load rendered frames first.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Animated GIF",
            defaultextension=".gif",
            filetypes=[("Animated GIF", "*.gif")],
        )
        if not output_path:
            return

        base_size = self.sequence_images[0].size
        frames = [
            image if image.size == base_size else image.resize(base_size, Image.Resampling.LANCZOS)
            for image in self.sequence_images
        ]
        duration_ms = round(1000 / self._sequence_fps())
        try:
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=duration_ms,
                loop=0,
                disposal=2,
            )
            self.set_status(f"🎞 Saved {len(frames)}-frame GIF: {os.path.basename(output_path)}")
            messagebox.showinfo("GIF Saved", f"Saved {len(frames)} frames at {self._sequence_fps()} fps:\n{output_path}")
        except Exception as exc:
            messagebox.showerror("GIF Export Error", f"Could not save GIF:\n{exc}")

    def on_save_image(self,  event=None):
        img = self.get_cur_img()

        if img is None:
            messagebox.showwarning("Save Image", "No rendered image data to save yet!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Rendered Image",
            defaultextension=".png",
            filetypes=[
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg;*.jpeg"),
                ("PPM Files", "*.ppm"),
                ("BMP Files", "*.bmp"),
                ("GIF Files", "*.gif"),
                ("TGA Files", "*.tga"),
                ("TIFF Files", "*.tif;*.tiff"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            img.save(file_path)
            messagebox.showinfo("Image Saved", f"Successfully saved image to:\n{file_path}")
            self.set_status(f"💾 Saved to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image: {e}")

    def buffer_to_img(self, rendered_pixels):
        img = Image.new("RGB", (self.current_width, self.current_height), color=(0, 0, 0))
        for y, row_pixels in rendered_pixels.items():
            if 0 <= y < self.current_height:
                for x, rgb in enumerate(row_pixels):
                    if 0 <= x < self.current_width:
                        img.putpixel((x, y), rgb)
        return img

    def blur_auto_calc(self, state=None):
        if state is not None and self.sequence_images:
            enabled = bool(state)
            accepted = self._submit_sequence_edit(
                "filter-blur",
                "Blur" if enabled else "Remove Blur",
                lambda image: image.filter(ImageFilter.BLUR),
                replace=True,
                remove=not enabled,
            )
            if accepted:
                self.blur = enabled
            else:
                self.blur_var.set(self.blur)
            return
        if state is not None:
            self._begin_control_edit("blur")
            self.blur = bool(state)
        self.update_live_preview()

    def contour_auto_calc(self, state=None):
        if state is not None and self.sequence_images:
            enabled = bool(state)
            accepted = self._submit_sequence_edit(
                "filter-contour", "Contour" if enabled else "Remove Contour",
                lambda image: image.filter(ImageFilter.CONTOUR), replace=True, remove=not enabled,
            )
            if accepted:
                self.contour = enabled
            else:
                self.contour_var.set(self.contour)
            return
        if state is not None:
            self._begin_control_edit("contour")
            self.contour = bool(state)
        self.update_live_preview()

    def smooth_auto_calc(self, state=None):
        if state is not None and self.sequence_images:
            enabled = bool(state)
            accepted = self._submit_sequence_edit(
                "filter-smooth", "Smooth" if enabled else "Remove Smooth",
                lambda image: image.filter(ImageFilter.SMOOTH), replace=True, remove=not enabled,
            )
            if accepted:
                self.smooth = enabled
            else:
                self.smooth_var.set(self.smooth)
            return
        if state is not None:
            self._begin_control_edit("smooth")
            self.smooth = bool(state)
        self.update_live_preview()

    def sharpen_auto_calc(self, state=None):
        if state is not None and self.sequence_images:
            enabled = bool(state)
            accepted = self._submit_sequence_edit(
                "filter-sharpen", "Sharpen" if enabled else "Remove Sharpen",
                lambda image: image.filter(ImageFilter.SHARPEN), replace=True, remove=not enabled,
            )
            if accepted:
                self.sharpen = enabled
            else:
                self.sharpen_var.set(self.sharpen)
            return
        if state is not None:
            self._begin_control_edit("sharpen")
            self.sharpen = bool(state)
        self.update_live_preview()

    def scaled_auto_calc(self, _=None):
        values = self.form.get_values()
        new_scale = min(10.0, max(0.1, float(values.get("scalefac", 1.0))))
        if self.sequence_images:
            if self._submit_sequence_edit(
                "adjust-scale", "Scale",
                lambda image, amount=new_scale: image.resize(
                    (max(1, int(image.width * amount)), max(1, int(image.height * amount))),
                    Image.Resampling.LANCZOS,
                ),
                replace=True,
                remove=abs(new_scale - 1.0) < 1e-9,
            ):
                self.scale_fac = new_scale
                self.is_scaled = abs(new_scale - 1.0) >= 1e-9
            return
        self._begin_control_edit("scale")
        self.scale_fac = new_scale
        self.is_scaled = True
        self.is_resized = False
        self.update_live_preview()
    
    def zoon_auto_calc(self,_=None):
        pass
 
    def resizedw_auto_calc(self, _, control_name: str | None = "resize"):
        values = self.form.get_values()
        self.image_width = int(values.get("width", self.orig_image_width))
        if "/" in self.aspratio:
            aspa, aspb = self.aspratio.split("/")
            if aspa != "None" and aspb != "None":
                try:
                    aspa = float(aspa)
                    aspb = float(aspb)
                    if aspa > 0:
                        self.image_height = max(1, int(self.image_width / (aspa / aspb)))
                        self.form.set_value("height", self.image_height)
                except Exception:
                    pass
        if self.sequence_images:
            target_size = (max(1, self.image_width), max(1, self.image_height))
            self._submit_sequence_edit(
                "adjust-resize", "Resize",
                lambda image, size=target_size: image.resize(size, Image.Resampling.LANCZOS),
                replace=True,
            )
            return
        if control_name:
            self._begin_control_edit(control_name)
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()

    def resizedh_auto_calc(self, _, control_name: str | None = "resize"):
        values = self.form.get_values()
        self.image_height = int(values.get("height", self.orig_image_height))
        if "/" in self.aspratio:
            aspa, aspb = self.aspratio.split("/")
            if aspa != "None" and aspb != "None":
                try:
                    aspa = float(aspa)
                    aspb = float(aspb)
                    if aspa > 0:
                        self.image_width = max(1, int(self.image_height * (aspa / aspb)))
                        self.form.set_value("width", self.image_width)
                except Exception:
                    pass
        if self.sequence_images:
            target_size = (max(1, self.image_width), max(1, self.image_height))
            self._submit_sequence_edit(
                "adjust-resize", "Resize",
                lambda image, size=target_size: image.resize(size, Image.Resampling.LANCZOS),
                replace=True,
            )
            return
        if control_name:
            self._begin_control_edit(control_name)
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()

    def aspratio_auto_calc(self, _=None):
        if not self.sequence_images:
            self._begin_control_edit("aspect ratio")
        values = self.form.get_values()
        self.aspratio = values.get("aspratio", "None/None")
        if self.aspratio != "None/None":
            self.resizedw_auto_calc(None, control_name=None)
        elif self.sequence_images:
            return
        else:
            self.update_live_preview()

    def _schedule_adjustment(self, timer_name: str, value: float, callback, delay_ms: int = 180):
        existing = getattr(self, timer_name, None)
        if existing is not None:
            try:
                self.after_cancel(existing)
            except Exception:
                pass
        setattr(self, timer_name, self.after(delay_ms, lambda: callback(value)))

    def on_rotation_change(self, val):
        self._schedule_adjustment("rotation_timer_id", float(val), self.finalize_rot_stack)

    def finalize_rot_stack(self, finval):
        self.rotation_timer_id = None
        if abs(float(finval) - self.rotation) < 1e-9:
            return
        if self.sequence_images:
            value = float(finval)
            if self._submit_sequence_edit(
                "adjust-rotation", "Rotation",
                lambda image, angle=value: image.rotate(angle, expand=True), replace=True,
                remove=abs(value) < 1e-9,
            ):
                self.rotation = value
            return
        self._begin_control_edit("rotation")
        self.rotation = float(finval)
        self.update_live_preview()

    def on_contrast_change(self, val):
        self._schedule_adjustment("contrast_timer_id", float(val), self.finalize_cont_stack)

    def finalize_cont_stack(self, val):
        self.contrast_timer_id = None
        if abs(float(val) - self.contrast) < 1e-9:
            return
        if self.sequence_images:
            value = float(val)
            if self._submit_sequence_edit(
                "adjust-contrast", "Contrast",
                lambda image, amount=value: ImageEnhance.Contrast(image).enhance(amount), replace=True,
                remove=abs(value - 1.0) < 1e-9,
            ):
                self.contrast = value
            return
        self._begin_control_edit("contrast")
        self.contrast = float(val)
        self.update_live_preview()

    def on_color_change(self, val):
        self._schedule_adjustment("color_timer_id", float(val), self.finalize_color_stack)

    def finalize_color_stack(self, val):
        self.color_timer_id = None
        if abs(float(val) - self.color) < 1e-9:
            return
        if self.sequence_images:
            value = float(val)
            if self._submit_sequence_edit(
                "adjust-color", "Color",
                lambda image, amount=value: ImageEnhance.Color(image).enhance(amount), replace=True,
                remove=abs(value - 1.0) < 1e-9,
            ):
                self.color = value
            return
        self._begin_control_edit("color")
        self.color = float(val)
        self.update_live_preview()

    def on_brightness_change(self, val):
        self._schedule_adjustment("brightness_timer_id", float(val), self.finalize_brightness_stack)

    def finalize_brightness_stack(self, val):
        self.brightness_timer_id = None
        if abs(float(val) - self.brightness) < 1e-9:
            return
        if self.sequence_images:
            value = float(val)
            if self._submit_sequence_edit(
                "adjust-brightness", "Brightness",
                lambda image, amount=value: ImageEnhance.Brightness(image).enhance(amount), replace=True,
                remove=abs(value - 1.0) < 1e-9,
            ):
                self.brightness = value
            return
        self._begin_control_edit("brightness")
        self.brightness = float(val)
        self.update_live_preview()

    def on_sharpness_change(self, val):
        self._schedule_adjustment("sharpness_timer_id", float(val), self.finalize_sharpness_stack)

    def finalize_sharpness_stack(self, val):
        self.sharpness_timer_id = None
        if abs(float(val) - self.sharpness) < 1e-9:
            return
        if self.sequence_images:
            value = float(val)
            if self._submit_sequence_edit(
                "adjust-sharpness", "Sharpness",
                lambda image, amount=value: ImageEnhance.Sharpness(image).enhance(amount), replace=True,
                remove=abs(value - 1.0) < 1e-9,
            ):
                self.sharpness = value
            return
        self._begin_control_edit("sharpness")
        self.sharpness = float(val)
        self.update_live_preview()

    def on_scale_change(self, val):
        self._schedule_adjustment("scale_timer_id", float(val), self.finalize_scale_stack)

    def finalize_scale_stack(self, val):
        self.scale_timer_id = None
        if abs(float(val) - self.scale_fac) < 1e-9:
            return
        if self.sequence_images:
            value = float(val)
            if self._submit_sequence_edit(
                "adjust-scale", "Scale",
                lambda image, amount=value: image.resize(
                    (max(1, int(image.width * amount)), max(1, int(image.height * amount))),
                    Image.Resampling.LANCZOS,
                ),
                replace=True,
                remove=abs(value - 1.0) < 1e-9,
            ):
                self.scale_fac = value
            return
        self._begin_control_edit("scale")
        self.scale_fac = float(val)
        self.is_scaled = True
        self.update_live_preview()

    def setup_zoom_image_workspace(self, image, working_image,target_frame=None):
        display_frame = target_frame if target_frame is not None else self.canvas_frame

        self.live_photo = image 

        overlay_canvas = tk.Canvas(
            display_frame, 
            width=image.width(), 
            height=image.height(), 
            highlightthickness=0
        )
    
        # FIX CENTERING: Position the anchor point right in the middle (relx=0.5, rely=0.5)
        # and set anchor="center" so it sits exactly on top of the original centered view.
        overlay_canvas.place(
            in_=display_frame, 
            relx=0.5, rely=0.5, 
            width=image.width(), 
            height=image.height(), 
            anchor="center"
        )
    
        overlay_canvas.create_image(0, 0, anchor="nw", image=self.live_photo)

        # Tk stores the native window identifier in _w. It is available at
        # runtime but intentionally absent from the public Canvas type stub.
        canvas_widget = cast(Any, overlay_canvas)
        self.tk.call('raise', canvas_widget._w)

        # 3. Main project handler (This is where your crop/zoom/buffer logic goes)
        def handle_selection(x0, y0, x1, y1):
            overlay_canvas.destroy()
       
            img =  working_image.copy()
            if img is None or x0 < 0 or y0 < 0:
                return
            box = (x0, y0, x1, y1)
            width = img.width
            height = img.height
            if self.sequence_images:
                self._submit_sequence_edit(
                    f"select-zoom-{len(self.sequence_edit_history)}",
                    "Select Zoom",
                    lambda frame, selected_box=box: frame.crop(selected_box).resize(
                        frame.size, Image.Resampling.LANCZOS
                    ),
                )
                return
            img_swap = img.crop(box)
            self._commit_discrete_image(img_swap.resize((width, height), Image.Resampling.LANCZOS))
            
        # 4. Inject the selection tool seamlessly
        CanvasSelector(overlay_canvas, callback=handle_selection)

    def setup_bokeh_image_workspace( self,image,working_image,target_frame=None):
        display_frame = target_frame if target_frame is not None else self.canvas_frame

        self.live_photo = image 

        overlay_canvas = tk.Canvas(
            display_frame, 
            width=image.width(), 
            height=image.height(), 
            highlightthickness=0
        )
    
        # FIX CENTERING: Position the anchor point right in the middle (relx=0.5, rely=0.5)
        # and set anchor="center" so it sits exactly on top of the original centered view.
        overlay_canvas.place(
            in_=display_frame, 
            relx=0.5, rely=0.5, 
            width=image.width(), 
            height=image.height(), 
            anchor="center"
        )
    
        overlay_canvas.create_image(0, 0, anchor="nw", image=self.live_photo)

        # Tk stores the native window identifier in _w. It is available at
        # runtime but intentionally absent from the public Canvas type stub.
        canvas_widget = cast(Any, overlay_canvas)
        self.tk.call('raise', canvas_widget._w)

        # 3. Main project handler (This is where your crop/zoom/buffer logic goes)
        def handle_selection(points):
            if len(points) < 3:
                overlay_canvas.destroy()
                return

            blur_amt = simpledialog.askfloat(
               "Bokeh Blur",
                "Enter a blur amount between 0 and 1: (Suggsted range .2-.3)",
                parent=self.winfo_toplevel(),
                initialvalue=0.25,
                minvalue=0.0,
                maxvalue=1.0,
            )     
            if self.debug_console is not None:
                self.debug_console.write(f'Input received for blur amount was: {blur_amt}')
            if blur_amt is None:
                overlay_canvas.destroy()
                return
            
            overlay_canvas.destroy()
       
            if blur_amt is None:
                return
            img = working_image.copy()

            if img is None:
                return
            blur_radius = blur_amt * 20.0

            def apply_bokeh(frame, selected_points=tuple(points), radius=blur_radius):
                mask = Image.new("L", frame.size, 0)
                mask.save("Makedimage.png")
                ImageDraw.Draw(mask).polygon(selected_points, fill=255)
                mask.save("PostMaskedImage.png")
                blurred = frame.filter(ImageFilter.GaussianBlur(radius=radius))
                blurred.save("blurred-image.png")
                return Image.composite(frame, blurred, mask)

            if self.sequence_images:
                self._submit_sequence_edit(
                    f"bokeh-{len(self.sequence_edit_history)}",
                    "Bokeh",
                    apply_bokeh,
                )
                return

            self._commit_discrete_image(apply_bokeh(img))
        
        # 4. Inject the selection tool seamlessly
        CanvasSelector(
            overlay_canvas,
            callback=handle_selection,
            selection_mode="freehand",
        )

    def setup_image_workspace(self, image, working_image,target_frame=None):
        display_frame = target_frame if target_frame is not None else self.canvas_frame

        self.live_photo = image 

        overlay_canvas = tk.Canvas(
            display_frame, 
            width=image.width(), 
            height=image.height(), 
            highlightthickness=0
        )
    
        # FIX CENTERING: Position the anchor point right in the middle (relx=0.5, rely=0.5)
        # and set anchor="center" so it sits exactly on top of the original centered view.
        overlay_canvas.place(
            in_=display_frame, 
            relx=0.5, rely=0.5, 
            width=image.width(), 
            height=image.height(), 
            anchor="center"
        )
    
        overlay_canvas.create_image(0, 0, anchor="nw", image=self.live_photo)

        # Tk stores the native window identifier in _w. It is available at
        # runtime but intentionally absent from the public Canvas type stub.
        canvas_widget = cast(Any, overlay_canvas)
        self.tk.call('raise', canvas_widget._w)

        # 3. Main project handler (This is where your crop/zoom/buffer logic goes)
        def handle_selection(x0, y0, x1, y1):
            overlay_canvas.destroy()
            img = working_image.copy()
            if img is None or x0 < 0 or y0 < 0:
                return
            box = (x0, y0, x1, y1)
            if self.sequence_images:
                self._submit_sequence_edit(
                    f"crop-{len(self.sequence_edit_history)}",
                    "Crop",
                    lambda frame, selected_box=box: frame.crop(selected_box),
                )
                return
            self._commit_discrete_image(img.crop(box))
            
        # 4. Inject the selection tool seamlessly
        CanvasSelector(overlay_canvas, callback=handle_selection)

if __name__ == "__main__":
    app = QuickApp(title="Progressive Ray-Tracer Studio", size=(1050, 960))
    app.set_single_tool(LiveRayTraceViewer)
    app.run()
