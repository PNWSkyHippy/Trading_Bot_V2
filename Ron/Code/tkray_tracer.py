import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageEnhance, ImageFilter, ImageTk
from quick_tk import QuickApp, ToolView
from quick_tk.core.forms import FormPanel

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
import tkinter as tk

class CanvasSelector:
    """
    Attaches rectangle selection to an existing canvas.
    Returns normalized (x0, y0, x1, y1) to a callback function on release.
    """
    def __init__(self, canvas, callback):
        self.canvas = canvas
        self.callback = callback  # The function to run when mouse is released
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # Bind to the existing canvas passed into the class
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, 
            outline="cyan", width=2, tags="selector"
        )

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        # 1. Normalize corners
        x0, x1 = sorted([self.start_x, end_x])
        y0, y1 = sorted([self.start_y, end_y])

        # 2. Clean up the drawing box right away if desired
        self.canvas.delete(self.rect_id)
        
        # 3. Send coordinates back to your main project logic
        if (x1 - x0) > 2 and (y1 - y0) > 2:  # Avoid accidental tiny clicks
            self.callback(int(x0), int(y0), int(x1), int(y1))
        else:
            self.callback(-1, -1, -1, -1)


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

BOOK_BINARIES = {
    "Book 1: In One Weekend": {
        "mac_dir": "/Users/ronh/Ron/Code/RayTrace/src/InOneWeekend",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src/InOneWeekend",
        "binary": "inoneweekend",
        "has_scenes": False,
        "default_res": (672, 378),
    },
    "Book 2: The Next Week": {
        "mac_dir": "/Users/ronh/Ron/Code/RayTrace/src/TheNextWeek",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src/TheNextWeek",
        "binary": "thenextweek",
        "has_scenes": True,
        "default_res": (600, 600),
    },
    "Book 3: The Rest of Your Life": {
        "mac_dir": "/Users/ronh/Ron/Code/RayTrace/src/TheRestOfYourLife",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src/TheRestOfYourLife",
        "binary": "therest",
        "has_scenes": False,
        "default_res": (600, 600),
    },
}


class LiveRayTraceViewer(ToolView):
    title = "Live Progressive Ray-Tracer Studio"

    def build_ui(self):
        # 1. Left Controls Panel
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.filepath = ""
        self.rendered_pixels = {}  # row_idx -> list of (r,g,b)
        self.current_width = 600
        self.current_height = 600
        self.orig_image_width = 600
        self.orig_image_height = 600
        self.image_width = 600
        self.image_height = 600
        self.is_rendering = False
        self.current_proc = None
        self.is_scaled = False
        self.is_resized = False
        self.aspratio = "None/None"
        self.blur = False
        self.contour = False    
        self.smooth = False
        self.sharpen = False
        self.rotation = 0.0
        self.contrast = 1.0
        self.color = 1.0
        self.brightness = 1.0
        self.sharpness = 1.0
        self.scale_fac = 1.0
        self.source_image = None
        self.current_transformed_image = None
        self.live_photo = None   
        self.image_stack = []    
        self.stack_desc = []
        self.stack_cnt = 0
        self.form = self.add_form("Ray-Tracer Settings", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.last_rotation_value = self.rotation
        self.rotation_timer_id = None
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

        # Scene Selection (for Book 2)
        self.scene_combo = self.form.add_dropdown(
            "scene",
            "Scene (Book 2)",
            options=[label for _, label in SCENES_BOOK2],
            default=SCENES_BOOK2[0][1],
        )

        # Action Buttons
        self.form.add_button("Start Progressive Render ▶", callback=self.on_start_render, variant="primary")
        self.form.add_button("Cancel / Stop Render ⏹", callback=self.on_stop_render, variant="outline")
 #       self.form.add_button("Save Rendered Image 💾", callback=self.on_save_image, variant="surface")

        # 2. Right Canvas: Live Drawing Image Surface
        self.right_box = self.add_container(parent=self)
        self.right_box.grid(row=0, column=1, sticky="nsew")

        self.canvas_frame = ttk.Frame(self.right_box, style="Card.TFrame", padding=6)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")

        self.img_label = tk.Label(self.canvas_frame, bg="#11111b", text="Select Book & Scene, then click Start Render")
        self.img_label.pack(expand=True)

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_command(label="Save Rendered Image 💾 <Ctrl-s>", command=self.on_save_image)
        self.bind_all("<Control-s>", self.on_save_image)
        file_menu.add_separator()
        file_menu.add_item("Exit Application <Alt-F4>", command=self.app.root.quit)
        self.bind_all("<Alt-F4>", self.app.root.quit)
        self.bind_all("<Control-p>", self.app.root.quit)
        # 3. VIEW MENU (With Toggle Checkboxes and Radio Groups)
        view_menu = self.menu("View")
        self.blur_var = view_menu.add_toggle("Blur", default=False, on_toggle=self.blur_auto_calc)
        self.contour_var = view_menu.add_toggle("Contour", default=False, on_toggle=self.contour_auto_calc)
        self.smooth_var = view_menu.add_toggle("Smooth", default=False, on_toggle=self.smooth_auto_calc)
        self.sharpen_var = view_menu.add_toggle("Sharpen", default=False, on_toggle=self.sharpen_auto_calc)

        tools_menu = self.menu("Edit")
        tools_menu.add_command(label="Image Adjustments 🎨 <Ctrl-a>", command=self.open_adjustments_window)
        self.bind_all("<Control-a>", self.open_adjustments_window)
        tools_menu.add_command(label="Crop Image <Ctrl-b>", command=self.crop_window)
        self.bind_all("<Control-b>", self.crop_window)
        tm3 = tools_menu.add_command(label=f"Undu ({len(self.image_stack)}) <Ctrl-z>", command=self.stack_pop)
        self.bind_all("<Control-z>", self.stack_pop)
        
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
        adj_form = self.add_form("Live Adjustments", parent=win)
        adj_form.pack(fill="both", expand=True, padx=8, pady=8)

        # 3. Add your sliders (hooked straight to your update callbacks)
        adj_form.add_slider(
            "rotation", "Rotate (°)", min_val=0, max_val=360, step=1,
            default=self.rotation
        )
        adj_r.bind("<Return>", self.on_rotation_change)
        adj_r.bind("<FocusOut>", self.on_rotation_change)
   
        adj_form.add_slider(
            "contrast", "Contrast", min_val=0.1, max_val=4.0, step=0.1,
            default=self.contrast
        )
 #       adj_s.bind("<Return>", self.on_contrast_change)
 #       adj_s.bind("<FocusOut>", self.on_contrast_change)
               
        adj_form.add_slider(
            "color", "Color", min_val=0.1, max_val=1.0, step=0.1,
            default=self.color
        )
 #       adj_c.bind("<Return>", self.on_color_change)
 #       adj_c.bind("<FocusOut>", self.on_color_change)
        
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

    def apply_ui_zoom(self, x0, y0, x1, y1):
        # 1. Store your current full-sized image in your history stack
        img2 = self.get_cur_img()
        self.stack_add(img2, "Zoom")
 #       self.zoom_history_stack.append(self.current_full_image)
        img = img2.copy()
        # 2. Slice out the region using Pillow
        cropped_slice = img.crop((x0, y0, x1, y1))
    
        # 3. GET DYNAMIC VALUES: Ask Tkinter for the exact width and height 
        # that your layout engine has assigned to the frame right now
        panel_width = self.canvas_frame.winfo_width()
        panel_height = self.canvas_frame.winfo_height()
    
        # 4. Resize the crop to perfectly fill the frame's relative space
        zoomed_view = cropped_slice.resize((panel_width, panel_height))
    
        # 5. Display the zoomed image on your label
        photo = ImageTk.PhotoImage(zoomed_view)
        self.live_photo = photo  # Prevent garbage collection
        self.img_label.config(image=self.live_photo)

 
    def stack_pop(self,event=None):
        if self.stack_cnt:
            tmpimg = self.image_stack.pop()
            tmpdesc = self.stack_desc.pop()
            self.stack_cnt -= 1
            messagebox.showinfo("Undu", f"removing ({tmpdesc}), there are now  ({self.stack_cnt}) Undus left.")
            photo = ImageTk.PhotoImage(tmpimg)
            self.live_photo = photo
            self.img_label.config(image=self.live_photo, text="")
            self.source_image = tmpimg
        else:
            messagebox.showinfo("Undu", f"There are ({self.stack_cnt}) Undus left.")
            return
        return(tmpimg, tmpdesc)
    
    def stack_add(self, img, reason="Generic"):
        self.image_stack.append(img)
        self.stack_desc.append(reason)
        self.stack_cnt += 1

    def get_cur_img(self):
        if self.current_transformed_image is not None:
            img = self.current_transformed_image
        elif self.source_image is not None:
            img = self.source_image.copy()
        elif self.rendered_pixels:
            img = self.buffer_to_img(self.rendered_pixels)
        return(img.copy())
                
    def crop_window(self, event=None):
        self.update_live_preview()
         # 1. Start from clean RAM copy
        if self.source_image is not None:
            img = self.source_image.copy()
        elif self.rendered_pixels:
            img = self.buffer_to_img(self.rendered_pixels)
        else:
            messagebox.showinfo("Error n file buffer tp crop~")
            return
        photo = ImageTk.PhotoImage(img)
        self.live_photo = photo
        self.img_label.config(image=self.live_photo, text="")
        img2 = self.get_cur_img()
        self.stack_add(img2, "Cropped")
        results =  self.setup_image_workspace(self.live_photo)
        sys.stdoutUT.write(f'setup_image_workspace returned: {results}')
 
    def _on_book_changed(self, selected_book: str):
        config = BOOK_BINARIES.get(selected_book, {})
        has_scenes = config.get("has_scenes", False)
        if has_scenes:
            self.scene_combo.config(state="readonly")
        else:
            self.scene_combo.config(state="disabled")

    def on_file_selected(self, filepath: str):
        """Called if a file is loaded."""
        if filepath and os.path.exists(filepath):
            try:
                self.source_image = Image.open(filepath)
                self.orig_image_width, self.orig_image_height = self.source_image.size
                self.current_width, self.current_height = self.source_image.size
                self.update_live_preview()
            except Exception as e:
                self.set_status(f"Error loading image: {e}")
        self.filepath = filepath

    def update_live_preview(self, _=None):
        """Transforms the in-memory buffer and updates the preview."""
        if not self.rendered_pixels and self.source_image is None:
            return

        values = self.form.get_values()
        self.image_width = int(values.get("width", self.current_width))
        self.image_height = int(values.get("height", self.current_height))
#        breakpoint()
        # 1. Start from clean RAM copy
        try:
            if self.current_transformed_image is not None:
                img - self.current_transformed_image
        except:
            messagebox.showinfo(f"Eror opening {self.current_transformed_image}")
        if self.source_image is not None:
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
            messsagebox.showinfo(f"Preview display error: {e}")

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
        self.current_transformed_image = None
        self.source_image = None

        # Reset PhotoImage
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")

        # Determine Binary
        book_info = BOOK_BINARIES.get(book_name, BOOK_BINARIES["Book 2: The Next Week"])
        binary_name = book_info["binary"]

        if IS_WINDOWS:
            # On Windows, run the Linux binary through WSL
            wsl_binary = f"{book_info['wsl_dir']}/{binary_name}"
            cmd = [
                "wsl",
                wsl_binary,
                "-r", f"{width},{height}",
                "-p",
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
                "-r", f"{width},{height}",
                "-p",
            ]

        if book_info.get("has_scenes", False):
            scene_num = scene_str.split(":")[0].strip()
            cmd.extend(["-c", scene_num])

        self.is_rendering = True
        self.start_time = time.time()

        def _render_stream():
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

                # Skip header lines if P3 is sent
                first_line = proc.stdout.readline()
                if "P3" in first_line:
                    proc.stdout.readline()  # dimensions
                    proc.stdout.readline()  # max val

                for line in proc.stdout:
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
                proc.wait()
            except Exception as e:
                self.app.root.after(0, lambda err=e: self.set_status(f"Error: {err}"))
            finally:
                self.is_rendering = False
                self.current_proc = None
                elapsed = time.time() - self.start_time
                self.app.root.after(0, lambda el=elapsed, ld=lines_drawn, h=height: self.set_status(f"✨ Render Finished in {el:.2f}s ({ld}/{h} scanlines)"))

        platform_label = "WSL" if IS_WINDOWS else "Native Mac"
        self.run_async(_render_stream, status_msg=f"Rendering {book_name} ({width}x{height}) via OpenMP ({platform_label})...")

    def _draw_row(self, row_idx, row_hex_string, width, height):
        try:
            self.live_photo.put(row_hex_string, to=(0, row_idx, width, row_idx + 1))
            drawn_count = len(self.rendered_pixels)
            pct = (drawn_count / height) * 100
            elapsed = time.time() - self.start_time
            self.set_status(f"⚡ Live Rendering: {pct:.1f}% ({drawn_count}/{height} rows) - {elapsed:.1f}s")
        except Exception:
            pass

    def on_stop_render(self, values: dict = None):
        if self.is_rendering and self.current_proc:
            self.is_rendering = False
            try:
                self.current_proc.terminate()
            except Exception:
                pass
            self.set_status("⏹ Render stopped by user.")

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
            self.blur = bool(state)
            img = self.get_cur_img()
            self.stack_add(img, "blur")
        self.update_live_preview()

    def contour_auto_calc(self, state=None):
        if state is not None:
            self.contour = bool(state)
            img = self.get_cur_img()
            self.stack_add(img, "contour")
        self.update_live_preview()

    def smooth_auto_calc(self, state=None):
        if state is not None:
            self.smooth = bool(state)
            img = self.get_cur_img()
            self.stack_add(img, "smooth")
        self.update_live_preview()

    def sharpen_auto_calc(self, state=None):
        if state is not None:
            self.sharpen = bool(state)
            img = self.get_cur_img()
            self.stack_add(img, "sharpen")
        self.update_live_preview()

    def scaled_auto_calc(self, _=None):
        values = self.form.get_values()
        self.scale_fac = min(10.0, max(0.1, float(values.get("scalefac", 1.0))))
        self.is_scaled = True
        self.is_resized = False
        img = self.get_cur_img()
        self.stack_add(img, "scaled")
        self.update_live_preview()

    def resizedw_auto_calc(self, _=None):
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
        img = self.get_cur_img()
        self.stack_add(img, "resized")
        self.update_live_preview()

    def resizedh_auto_calc(self, _=None):
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
        img = self.get_cur_img()
        self.stack_add(img, "resized")
        self.update_live_preview()

    def aspratio_auto_calc(self, _=None):
        values = self.form.get_values()
        self.aspratio = values.get("aspratio", "None/None")
        if self.aspratio != "None/None":
            self.resizedw_auto_calc()
        else:
            self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "asp ratio")

    def on_rotation_change(self, val):
        if self.rotation_timer_id is not None:
            self.afer_cancel(self.roation_timer_id)
        self.rotaion_timer_id = self.after(300, lambda: self.finalize_rot_stack(val))
  
    def finalize_rot_stack(self, finval):
        self.rotation_timer_id == None
        if float(finval) == self.rotation:
            return
        self.rotation = float(finval)
        self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "rotation")
        
    def on_contrast_change(self, val):
        if self.contrast_timer_id is not None:
            self.afer_cancel(self.contrast_timer_id)
        self.contrast_timer_id = self.after(300, lambda: self.finalize_cont_stack(val))
        
    def finalize_cont_stack(self, val):
        if self.contrast_timer_id is not None:
            self.afer_cancel(self.contrast_timer_id)
        self.contrast_timer_id = self.after(300, lambda: self.finalize_cont_stack(val))
             
        self.contrast_color_id == None
        if float(val) == self.contrast:
            return    
        self.contrast = float(val)
        self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "contrast")
                 
    def on_color_change(self, val):
        if self.contrast_timer_id is not None:
            self.afer_cancel(self.contrast_timer_id)
        self.contrast_timer_id = self.after(300, lambda: self.finalize_cont_stack(val))
        
        
        self.color = float(val)
        self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "color")
        
    def on_brightness_change(self, val):
        self.brightness = float(val)
        self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "brightness")
        
    def on_sharpness_change(self, val):
        self.sharpness = float(val)
        self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "sharness")
        
    def on_scale_change(self, val):
        self.scale_fac = float(val)
        self.is_scaled = True
        self.update_live_preview()
        img = self.get_cur_img()
        self.stack_add(img, "scaled")

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

        self.tk.call('raise', overlay_canvas._w)

        # 3. Main project handler (This is where your crop/zoom/buffer logic goes)
        def handle_selection(x0, y0, x1, y1):
            overlay_canvas.destroy()
       
            if not self.current_transformed_image:
                img = self.source_image
            else:
                img = self.current_transformed_image
            box = (x0, y0, x1, y1)
            img = img.crop(box)
            self.source_image = img
            self.current_transformed_image = img
            self.form.set_value("width", img.width)
            self.form.set_value("height", img.height) 
         
            self.update_live_preview()
            
            # TODO: Add your logic here
            # - For Zoom: Push current state to a list/stack buffer, then crop & resize image
            # - For Copy: Grab image bounding box slice to clipboard

        # 4. Inject the selection tool seamlessly
        CanvasSelector(overlay_canvas, callback=handle_selection)

if __name__ == "__main__":
    app = QuickApp(title="Progressive Ray-Tracer Studio", size=(1050, 960))
    app.set_single_tool(LiveRayTraceViewer)
    app.run()
