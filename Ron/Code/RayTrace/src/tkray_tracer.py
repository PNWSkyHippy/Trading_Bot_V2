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

import os
import re
import sys
import subprocess
import time
from pathlib import Path
from typing import Any, cast
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageEnhance, ImageFilter, ImageTk

# This file is in Code/RayTrace/src, while quick_tk is in Code/quick_tk.
# Adding Code to sys.path lets this script work when launched directly rather
# than only when launched as part of a larger Python package.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quick_tk import QuickApp, ToolView
from quick_tk.core.forms import FormPanel

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

import time
"""
scene1 = [
    {
        "filename": "scene1.image1.ppm",
        "book": "2",
        "chapter": "6",
        "light1": "2,7,3,0.8",
        "light2": "-3,4,1,0.2",
        "camera": "26,3,16",
        "lookat": "0,2,0",
        "vfov": "28",
    },
    {
        "filename": "scene1.image2.ppm",
        "book": "2",
        "chapter": "6",
        "light1": "2,7,3,0.8",
        "light2": "-3,4,1,0.2",
        "camera": "22,3,12",
        "lookat": "0,2,0",
        "vfov": "26",
    },
    {
        "filename": "scene1.image3.ppm",
        "book": "2",
        "chapter": "6",
        "light1": "2,7,3,0.8",
        "light2": "-3,4,1,0.2",
        "camera": "16,4,7",
        "lookat": "0,2,0",
        "vfov": "24",
    },
    {
        "filename": "scene1.image4.ppm",
        "book": "2",
        "chapter": "6",
        "light1": "2,7,3,0.8",
        "light2": "-3,4,1,0.2",
        "camera": "9,6,2",
        "lookat": "0,2,0",
        "vfov": "22",
    },
    {
        "filename": "scene1.image5.ppm",
        "book": "2",
        "chapter": "6",
        "light1": "2,7,3,0.8",
        "light2": "-3,4,1,0.2",
        "camera": "3,9,-3",
        "lookat": "0,1.5,0",
        "vfov": "25",
    },
    {
        "filename": "scene1.image6.ppm",
        "book": "2",
        "chapter": "6",
        "light1": "2,7,3,0.8",
        "light2": "-3,4,1,0.2",
        "camera": "-4,12,-7",
        "lookat": "0,0.5,0",
        "vfov": "30",
    },
]
"""
def lerp(a, b, t):
    """Return a value t of the way from a to b."""
    return a + (b - a) * t


def lerp_point(start, end, t):
    """Interpolate an (x, y, z) point."""
    return tuple(lerp(a, b, t) for a, b in zip(start, end))


def point_text(point):
    """Turn (x, y, z) into the C++ command format: x,y,z."""
    return ",".join(f"{value:.3f}" for value in point)


def make_scene1(keyframes, common_settings):
    """
    Create the scene1 list that your existing render button already uses.

    keyframes:
        A list of important camera poses.  Frame numbers can be any distance
        apart; all missing frames are generated automatically.
    """
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


# These remain the same for every frame in this particular shot.
common_scene1_settings = {
    "book": "2",
    "chapter": "6",
    "light1": "2,7,3,0.8",
    "light2": "-3,4,1,0.2",
}


# These are the only camera poses you direct by hand.
# Python generates every frame between them.
scene1_keyframes192f = [
    {
        "frame": 1,
        "camera": (46, 3, 32),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 16,
        "camera": (40, 3, 28),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 32,
        "camera": (32, 6, 16),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 48,
        "camera": (16, 12, 8),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
    {
        "frame": 64,
        "camera": (9, 6, 2),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 80,
        "camera": (4,12,-7),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 96,
        "camera": (9, 18, -14),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 112,
        "camera": (15, 24, -12),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
       {
            "frame": 128,
            "camera": (15, 24, -12),
            "lookat": (0.1, 0.6, 0),
            "vfov": 32,
        },
   {
        "frame": 144,
        "camera": (15, 24, -12),
        "lookat": (.2, 0.7, 0),
        "vfov": 34,
    },
      {
            "frame": 160,
            "camera": (15, 24, -12),
            "lookat": (0.3, 0.8, 0),
            "vfov": 36,
        },
      {
            "frame": 1176,
            "camera": (15, 24, -12),
            "lookat": (0.4, 0.9, 0),
            "vfov": 38,
        },
  {
        "frame": 192,
        "camera": (15, 24, -12),
        "lookat": (0.5, 1.0, 0),
        "vfov": 40,
    },
]

scene1_keyframes112f = [
    {
        "frame": 1,
        "camera": (46, 3, 32),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 16,
        "camera": (40, 3, 28),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 32,
        "camera": (32, 6, 16),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 48,
        "camera": (16, 12, 8),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
    {
        "frame": 64,
        "camera": (9, 6, 2),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 80,
        "camera": (4,12,-7),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 96,
        "camera": (9, 18, -14),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 112,
        "camera": (15, 24, -12),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
    
]

scene1_keyframes48f = [
    {
        "frame": 1,
        "camera": (26, 3, 16),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 16,
        "camera": (22, 3, 12),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 32,
        "camera": (9, 6, 2),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 48,
        "camera": (-4, 12, -7),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
]
scene1_keyframes24f = [
    {
        "frame": 1,
        "camera": (26, 3, 16),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 8,
        "camera": (22, 3, 12),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 16,
        "camera": (9, 6, 2),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 24,
        "camera": (-4, 12, -7),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
]


# This is the same scene1 list your existing six-frame render code expects.
scene1 = make_scene1(scene1_keyframes192f, common_scene1_settings)

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
    Attaches rectangle selection to an existing canvas.
    Returns normalized (x0, y0, x1, y1) to a callback function on release.
    """
    def __init__(self, canvas, callback):
        """Initialize class varaibles

        Args:
            canvas (_type_): _description_
            callback (function): _description_
        """        
        self.canvas = canvas      # Main window drawing cntainer
        self.callback = callback  # The function to run when mouse is released
        self.start_x = None    # For renderer
        self.start_y = None
        self.rect_id = None

        # Bind to the existing canvas passed into the class
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

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
#        self.debug_win = None
        self.filepath = ""  #H for output file
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
        self.blur = False               # Has blue been applied
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
        self.sequence_paths = []
        self.sequence_index = 0
        self.sequence_playing = False
        self.sequence_after_id = None
        self.sequence_photo = None
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
        self.form.add_button("Cancel / Stop Render ⏹", callback=self.on_stop_render, variant="outline")
        self.form.add_button("Load Image Sequence 📂", callback=self.on_load_image_sequence, variant="surface")
        self.form.add_button("Export Sequence as GIF 🎞", callback=self.on_export_sequence_gif, variant="surface")
 #       self.form.add_button("Save Rendered Image 💾", callback=self.on_save_image, variant="surface")

        # 2. Right Canvas: Live Drawing Image Surface
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
        file_menu.add_command(label="Save Rendered Image 💾 <Ctrl-s>", command=self.on_save_image)
        self.bind_all("<Control-s>", self.on_save_image)
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
        tools_menu.add_command(label="Zoom In <Shift-+>", command=self.zoom_in_window)
        self.bind_all("<Shift-KeyPress-plus>", self.zoom_in_window)
        tools_menu.add_command(label="Zoom Out <Shift-->", command=self.zoom_out_window)
        self.bind_all("<Shift-KeyPress-minus>", self.zoom_out_window)
        tools_menu.add_command(label="Crop Window <Ctrl-b>", command=self.crop_window)
        self.bind_all("<Control-b>", self.crop_window)
        tm3 = tools_menu.add_command(label=f"Undu ({len(self.image_stack)}) <Ctrl-z>", command=self.stack_pop)
        self.bind_all("<Control-z>", self.stack_pop)
        
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
            photo = ImageTk.PhotoImage(preview_img)
            self.live_photo = photo
            self.img_label.config(image=self.live_photo, text="")
        else:
            self.img_label.config(image="", text="Select Book & Scene, then click Start Render")

    def stack_pop(self,event=None):
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
        if self.current_transformed_image is not None:
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
        self.stack_add(img2, "Select Zoom")
        results =  self.setup_zoom_image_workspace(self.live_photo)

              
    def crop_window(self, event=None):
#       self.update_live_preview()
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
        self.stack_add(img2, "Cropped")
        results =  self.setup_image_workspace(self.live_photo)

 
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

    def on_file_selected(self, filepath: str):
        """Called if a file is loaded."""
        if filepath and os.path.exists(filepath):
            try:
                self.edit_base_image = None
                self.source_image = Image.open(filepath)
                self.orig_image_width, self.orig_image_height = self.source_image.size
                self.current_width, self.current_height = self.source_image.size
                self.update_live_preview()
            except Exception as e:
                self.set_status(f"Error loading image: {e}")
        self.filepath = filepath

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
        
    def on_click_render2(self, argumen=None):
        if self.is_rendering:
            messagebox.showinfo("Rendering", "A render is already in progress. Stop it first if you want to start a new one.")
            return

        self._scene_render_values = self.form.get_values()
        self._scene_render_queue = iter(scene1)
        self._start_next_scene_render()

    def _start_next_scene_render(self):
        """Start one movie frame; the completion callback starts the next."""
        try:
            scene = next(self._scene_render_queue)
        except StopIteration:
            self.set_status("✨ All scene frames finished.")
            return

        render_args = [
            "-o", scene["filename"],
            "-b", scene["book"],
            "-c", scene["chapter"],
            "--light", scene["light1"],
            "--light", scene["light2"],
            "--camera", scene["camera"],
            "--look-at", scene["lookat"],
            "--vfov", scene["vfov"],
            "-r", "600,600",
            "-p",
        ]

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

        # Reset PhotoImage
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")
        WIN_EXEC_PATH = "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src"
        MAC_EXEC_PATH = "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src"
        # Determine unified binary

        binary_name = "inoneweekend"

        if IS_WINDOWS:
            # On Windows, run the Linux binary through WSL
            wsl_binary = f"{WIN_EXEC_PATH}/{binary_name}"
            cmd = ["wsl", wsl_binary, *render_args]
        else:
            # On Mac / POSIX, run the compiled binary directly
            mac_binary = f"{MAC_EXEC_PATH}/{binary_name}"
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
        self.sequence_images = loaded_images
        self.sequence_paths = loaded_paths
        self.sequence_index = 0
        self.sequence_scrubber.configure(to=len(loaded_images) - 1)
        self.sequence_frame_var.set(0)
        self.show_sequence_frame(0)

        if failures:
            messagebox.showwarning(
                "Some Frames Were Skipped",
                "The usable frames were loaded, but these files could not be read:\n\n" + "\n".join(failures),
            )

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
        img = self.current_transformed_image
        if img is None and self.rendered_pixels:
            img = self.buffer_to_img(self.rendered_pixels)
        if img is None and self.source_image is not None:
            img = self.source_image

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
        if state is not None:
            self._begin_control_edit("blur")
            self.blur = bool(state)
        self.update_live_preview()

    def contour_auto_calc(self, state=None):
        if state is not None:
            self._begin_control_edit("contour")
            self.contour = bool(state)
        self.update_live_preview()

    def smooth_auto_calc(self, state=None):
        if state is not None:
            self._begin_control_edit("smooth")
            self.smooth = bool(state)
        self.update_live_preview()

    def sharpen_auto_calc(self, state=None):
        if state is not None:
            self._begin_control_edit("sharpen")
            self.sharpen = bool(state)
        self.update_live_preview()

    def scaled_auto_calc(self, _=None):
        self._begin_control_edit("scale")
        values = self.form.get_values()
        self.scale_fac = min(10.0, max(0.1, float(values.get("scalefac", 1.0))))
        self.is_scaled = True
        self.is_resized = False
        self.update_live_preview()
    
    def zoon_auto_calc(self,_=None):
        pass
 
    def resizedw_auto_calc(self, _, control_name: str | None = "resize"):
        if control_name:
            self._begin_control_edit(control_name)
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
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()

    def resizedh_auto_calc(self, _, control_name: str | None = "resize"):
        if control_name:
            self._begin_control_edit(control_name)
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
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()

    def aspratio_auto_calc(self, _=None):
        self._begin_control_edit("aspect ratio")
        values = self.form.get_values()
        self.aspratio = values.get("aspratio", "None/None")
        if self.aspratio != "None/None":
            self.resizedw_auto_calc(None, control_name=None)
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
        self._begin_control_edit("rotation")
        self.rotation = float(finval)
        self.update_live_preview()

    def on_contrast_change(self, val):
        self._schedule_adjustment("contrast_timer_id", float(val), self.finalize_cont_stack)

    def finalize_cont_stack(self, val):
        self.contrast_timer_id = None
        if abs(float(val) - self.contrast) < 1e-9:
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
        self._begin_control_edit("color")
        self.color = float(val)
        self.update_live_preview()

    def on_brightness_change(self, val):
        self._schedule_adjustment("brightness_timer_id", float(val), self.finalize_brightness_stack)

    def finalize_brightness_stack(self, val):
        self.brightness_timer_id = None
        if abs(float(val) - self.brightness) < 1e-9:
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
        self._begin_control_edit("sharpness")
        self.sharpness = float(val)
        self.update_live_preview()

    def on_scale_change(self, val):
        self._schedule_adjustment("scale_timer_id", float(val), self.finalize_scale_stack)

    def finalize_scale_stack(self, val):
        self.scale_timer_id = None
        if abs(float(val) - self.scale_fac) < 1e-9:
            return
        self._begin_control_edit("scale")
        self.scale_fac = float(val)
        self.is_scaled = True
        self.update_live_preview()

    def setup_zoom_image_workspace(self, image, target_frame=None):
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
       
            img = self.current_transformed_image or self.source_image
            if img is None or x0 < 0 or y0 < 0:
                return
            box = (x0, y0, x1, y1)
            width = img.width
            height = img.height
            img_swap = img.crop(box)
            self._commit_discrete_image(img_swap.resize((width, height), Image.Resampling.LANCZOS))
            
        # 4. Inject the selection tool seamlessly
        CanvasSelector(overlay_canvas, callback=handle_selection)

    def setup_image_workspace(self, image, target_frame=None):
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
       
            img = self.current_transformed_image or self.source_image
            if img is None or x0 < 0 or y0 < 0:
                return
            box = (x0, y0, x1, y1)
            self._commit_discrete_image(img.crop(box))
            
        # 4. Inject the selection tool seamlessly
        CanvasSelector(overlay_canvas, callback=handle_selection)

if __name__ == "__main__":
    app = QuickApp(title="Progressive Ray-Tracer Studio", size=(1050, 960))
    app.set_single_tool(LiveRayTraceViewer)
    app.run()

