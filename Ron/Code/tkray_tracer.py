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
       
        self.form = self.add_form("Ray-Tracer Settings", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        
        self.setup_menus()

        # Filters
#        self.form.add_checkbox("blur", "Blur", default=False, on_change=self.blur_auto_calc)
#        self.form.add_checkbox("contour", "Contour", default=False, on_change=self.contour_auto_calc)
#        self.form.add_checkbox("smooth", "Smooth", default=False, on_change=self.smooth_auto_calc)
#        self.form.add_checkbox("sharpen", "Sharpen", default=False, on_change=self.sharpen_auto_calc)

        # Transforms & Sliders (all with two-way synced spinboxes)
#        self.form.add_slider("rotation", "Rotate (°)", min_val=0, max_val=360, step=1, default=0, on_change=self.update_live_preview)
#        self.form.add_slider("contrast", "Contrast", min_val=0.1, max_val=4.0, step=0.1, default=1.0, on_change=self.update_live_preview)
#        self.form.add_slider("color", "Color", min_val=0.1, max_val=1.0, step=0.1, default=1.0, on_change=self.update_live_preview)
#        self.form.add_slider("brightness", "Brightness", min_val=0.1, max_val=1.0, step=0.1, default=1.0, on_change=self.update_live_preview)
#        self.form.add_slider("sharpness", "Sharpness", min_val=0.1, max_val=2.0, step=0.1, default=1.0, on_change=self.update_live_preview)
#        self.form.add_slider("scalefac", "Scale Factor", min_val=0.1, max_val=10.0, step=0.1, default=1.0, on_change=self.scaled_auto_calc)
        self.form.add_dropdown("aspratio", "Aspect Ratio", ["16/9", "16/10", "21/9", "4/3", "5/4", "None/None"], default="None/None", on_change=self.aspratio_auto_calc)
        
        spin_w = self.form.add_number("width", "Width (px)", min_val=100, max_val=8192, default=600, step=16)
        spin_w.bind("<Return>", self.resizedw_auto_calc)
        spin_h = self.form.add_number("height", "Height (px)", min_val=100, max_val=8192, default=600, step=16)
        spin_h.bind("<Return>", self.resizedh_auto_calc)

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
        right_box = self.add_container(parent=self)
        right_box.grid(row=0, column=1, sticky="nsew")

        self.canvas_frame = ttk.Frame(right_box, style="Card.TFrame", padding=6)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")

        self.img_label = tk.Label(self.canvas_frame, bg="#11111b", text="Select Book & Scene, then click Start Render")
        self.img_label.pack(expand=True)

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_command("Save Rendered Image 💾", self.on_save_image, shortcut="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_item("Exit Application", self.app.root.quit, shortcut="Alt+F4")

        # 3. VIEW MENU (With Toggle Checkboxes and Radio Groups)
        view_menu = self.menu("View")
        self.blur_var = view_menu.add_toggle("Blur", default=False, on_toggle=self.blur_auto_calc)
        self.contour_var = view_menu.add_toggle("Contour", default=False, on_toggle=self.contour_auto_calc)
        self.smooth_var = view_menu.add_toggle("Smooth", default=False, on_toggle=self.smooth_auto_calc)
        self.sharpen_var = view_menu.add_toggle("Sharpen", default=False, on_toggle=self.sharpen_auto_calc)

        tools_menu = self.menu("Tools")
        tools_menu.add_command("Image Adjustments 🎨", self.open_adjustments_window, shortcut="Ctrl+A")


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

        # 1. Start from clean RAM copy
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
            print(f"Preview display error: {e}")

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

    def on_save_image(self, values: dict = None):
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
        self.update_live_preview()

    def contour_auto_calc(self, state=None):
        if state is not None:
            self.contour = bool(state)
        self.update_live_preview()

    def smooth_auto_calc(self, state=None):
        if state is not None:
            self.smooth = bool(state)
        self.update_live_preview()

    def sharpen_auto_calc(self, state=None):
        if state is not None:
            self.sharpen = bool(state)
        self.update_live_preview()

    def scaled_auto_calc(self, _=None):
        values = self.form.get_values()
        self.scale_fac = min(10.0, max(0.1, float(values.get("scalefac", 1.0))))
        self.is_scaled = True
        self.is_resized = False
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
        self.update_live_preview()

    def aspratio_auto_calc(self, _=None):
        values = self.form.get_values()
        self.aspratio = values.get("aspratio", "None/None")
        if self.aspratio != "None/None":
            self.resizedw_auto_calc()
        else:
            self.update_live_preview()

    def on_rotation_change(self, val):
        self.rotation = float(val)
        self.update_live_preview()

    def on_contrast_change(self, val):
        self.contrast = float(val)
        self.update_live_preview()

    def on_color_change(self, val):
        self.color = float(val)
        self.update_live_preview()

    def on_brightness_change(self, val):
        self.brightness = float(val)
        self.update_live_preview()

    def on_sharpness_change(self, val):
        self.sharpness = float(val)
        self.update_live_preview()

    def on_scale_change(self, val):
        self.scale_fac = float(val)
        self.is_scaled = True
        self.update_live_preview()

    def open_adjustments_window(self):
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

if __name__ == "__main__":
    app = QuickApp(title="Progressive Ray-Tracer Studio", size=(1050, 960))
    app.set_single_tool(LiveRayTraceViewer)
    app.run()
