import os
import subprocess
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageEnhance
from quick_tk import QuickApp, ToolView


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
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src/InOneWeekend",
        "binary": "inoneweekend",
        "has_scenes": False,
        "default_res": (672, 378),
    },
    "Book 2: The Next Week": {
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src/TheNextWeek",
        "binary": "thenextweek",
        "has_scenes": True,
        "default_res": (600, 600),
    },
    "Book 3: The Rest of Your Life": {
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src/TheRestOfYourLife",
        "binary": "therest",
        "has_scenes": False,
        "default_res": (600, 600),
    },
}


class LiveRayTraceViewer(ToolView):
    title = "Live Progressive Ray-Tracer Studio"

    def build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.rendered_pixels = {}  # row_idx -> list of (r,g,b)
        self.current_width = 600
        self.current_height = 600
        self.is_rendering = False
        self.current_proc = None

        # 1. Left Controls Panel
        self.form = self.add_form("Ray-Tracer Settings", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

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
        self.form.add_dropdown("format", "Output Format", ["bmp", "jpg", "ppm", "gif", "pcx","tga","ico","png","tif"], default="ppm", on_change=self.update_live_preview)
        # Resolution controls
        self.form.add_output_file_picker(
            name="outfile",
            label="Output File",
            default_filename="ray_traced.ppm",
            default_extension=".ppm",
            on_change=self.update_live_preview,
            filetypes=[("Ppm Files", "*.ppm"), ("Jpg Files", "*.jpg"), 
                    ("Bmp Files", "*.bmp"), ("Gif Files", "*.gif"),
                    ("Pcx Files", "*.pcx"), ("Tga Files", "*.tga"),
                    ("Png Files", "*.png"), ("Tif Files", "*.tif"),
                    ("All Files", "*.*")]
        )       

        self.form.add_slider("rotation", "Rotate (°)", min_val=0, max_val=360, step=1, default=0, on_change=self.update_live_preview)
        self.form.add_slider("contrast", "Contrast", min_val=0.1, max_val=4.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("color", "Color", min_val=0.1, max_val=1.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("brightness", "Brightness", min_val=0.1, max_val=1.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("sharpness", "Sharpness", min_val=0.1, max_val=2.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("scalefac", "Scale Factor", min_val=0.1, max_val=10.0, step=0.1, default=1.0, on_change=self.scaled_auto_calc)
        self.form.add_slider("width", "Width (px)", min_val=100, max_val=1920, default=600, step=16)
        self.form.add_slider("height", "Height (px)", min_val=100, max_val=1080, default=600, step=16)

        # Action Buttons
        self.form.add_button("Start Progressive Render ▶", callback=self.on_start_render, variant="primary")
        self.form.add_button("Cancel / Stop Render ⏹", callback=self.on_stop_render, variant="outline")
        self.form.add_button("Save Rendered Image 💾", callback=self.on_save_image, variant="surface")
        self.form.add_button("Convert Image", callback=self.on_view_clicked, variant="primary")

        # 2. Right Canvas: Live Drawing Image Surface
        right_box = self.add_container(parent=self)
        right_box.grid(row=0, column=1, sticky="nsew")

        self.canvas_frame = ttk.Frame(right_box, style="Card.TFrame", padding=6)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")

        self.img_label = tk.Label(self.canvas_frame, bg="#11111b", text="Select Book & Scene, then click Start Render")
        self.img_label.pack(expand=True)

    def _on_book_changed(self, selected_book: str):
        config = BOOK_BINARIES.get(selected_book, {})
        has_scenes = config.get("has_scenes", False)
        if has_scenes:
            self.scene_combo.config(state="readonly")
        else:
            self.scene_combo.config(state="disabled")

        w, h = config.get("default_res", (600, 600))
#        self.form.set_value("width", w)
#        self.form.set_value("height", h)
        
    def on_file_selected(self, filepath: str):
        """Called the instant the user chooses a file."""
        if filepath and os.path.exists(filepath):
            try:
                self.source_image = Image.open(filepath)
                self.update_live_preview()
            except Exception as e:
                self.preview.clear()
        self.filepath = filepath
        
    def update_live_preview(self, _=None):
        """Transforms the in-memory buffer and updates the preview in 0.1ms."""
        if self.source_image is None:
            self.preview.clear()
            return
        values = self.form.get_values()
        self.rotation = float(values.get("rotation", 0))
        self.contrast = float(values.get("contrast", 1.0))
        self.color = float(values.get("color", 1.0))
        self.brightness = float(values.get("brightness", 1.0))
        self.sharpness = float(values.get("sharpness", 1.0))
        self.scale_fac = float(values.get("scalefac", 60))
        self.image_width = int(values.get("width", 600))
        self.image_height = int(values.get("height", 600))
        # 1. Start from clean RAM copy
        img = self.source_image.copy()
        # 2. Apply In-Memory Transformations:
        # Rotation
        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)
        # Contrast
        if self.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast)
        if self.color != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(self.color)  
        if self.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness)
        if self.sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(self.sharpness)            
        # Scaling / Resize
        if self.is_scaled and self.scale_fac != 1.0:
            new_w = max(1, int(img.width * self.scale_fac))
            new_h = max(1, int(img.height * self.scale_fac))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        elif self.is_resized and (self.image_width != img.width or self.image_height != img.height):    
             img = img.resize((self.image_width, self.image_height))
        # 3. Store current transformed buffer & push to preview!
        self.current_transformed_image = img
        self.preview.set_image(img, info_text=f"{img.width}x{img.height} px | In-Memory")


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
        self.rendered_pixels = {}

        # Reset PhotoImage
        self.live_photo = tk.PhotoImage(width=width, height=height)
        self.img_label.config(image=self.live_photo, text="")

        # Determine Binary
        book_info = BOOK_BINARIES.get(book_name, BOOK_BINARIES["Book 2: The Next Week"])
        wsl_binary = f"{book_info['wsl_dir']}/{book_info['binary']}"

        cmd = [
            "wsl",
            wsl_binary,
            "-r", f"{width},{height}",
            "-p"
        ]

        if book_info.get("has_scenes", False):
            # Extract scene index (e.g. "1: Bouncing Spheres" -> "1")
            scene_num = scene_str.split(":")[0].strip()
            cmd.extend(["-c", scene_num])

        self.is_rendering = True
        self.start_time = time.time()

        def _render_stream():
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

                lines_drawn = 0
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
                self.set_status(f"Error: {e}")
            finally:
                self.is_rendering = False
                self.current_proc = None
                elapsed = time.time() - self.start_time
                self.set_status(f"✨ Render Finished in {elapsed:.2f}s ({lines_drawn}/{height} scanlines)")

        self.run_async(_render_stream, status_msg=f"Rendering {book_name} ({width}x{height}) via OpenMP WSL...")

    def _draw_row(self, row_idx, row_hex_string, width, height):
        try:
            self.live_photo.put(row_hex_string, to=(0, row_idx, width, row_idx + 1))
            drawn_count = len(self.rendered_pixels)
            pct = (drawn_count / height) * 100
            elapsed = time.time() - self.start_time
            self.set_status(f"⚡ Live Rendering: {pct:.1f}% ({drawn_count}/{height} rows) - {elapsed:.1f}s")
            return(elapsed)
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
        if not self.rendered_pixels:
            messagebox.showwarning("Save Image", "No rendered image data to save yet!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Rendered Image",
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg"),
                ("BMP Image", "*.bmp"),
                ("TIFF Image", "*.tif"),
                ("PPM Image", "*.ppm"),
                ("All Files", "*.*"),
            ]
        )
        if not file_path:
            return

        try:
            img = Image.new("RGB", (self.current_width, self.current_height), color=(0, 0, 0))
            for y, row_pixels in self.rendered_pixels.items():
                if 0 <= y < self.current_height:
                    for x, rgb in enumerate(row_pixels):
                        if 0 <= x < self.current_width:
                            img.putpixel((x, y), rgb)

            img.save(file_path)
            messagebox.showinfo("Image Saved", f"Successfully saved image to:\n{file_path}")
            self.set_status(f"💾 Saved to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image: {e}")

    def scaled_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.scale_fac = float(values.get("scalefac", 1.0))
        self.is_scaled = True
        self.is_resized = False
        self.update_live_preview()
        
    def on_view_clicked(self, values: dict):
        self.update_live_preview()
        self.make_image(values)
       
       
    def make_image(self, values: dict):
        # values["outfile"] contains the full, verified output Path!
        if not self.filepath:
            return
        if values.get("outfile","image_converted.ppm"):
            self.outfile = values.get("outfile","image_converted.ppm")
        else:
            self.outfile = "image_converted.ppm"
        try:
            f, e = self.outfile.split(".")
            self.outfile = f + "." + self.format
        except:
            self.outfile = self.outfile + "." + self.format
        try:
            with Image.open(self.filepath) as img: 
                values = self.form.get_values()
                self.rotation = float(values.get("rotation", 0))
                self.contrast = float(values.get("contrast", 1.0))
                self.color = float(values.get("color", 1.0))
                self.brightness = float(values.get("brightness", 1.0))
                self.sharpness = float(values.get("sharpness", 1.0))
                self.scale_fac = float(values.get("scalefac", 60))
                self.image_width = int(values.get("width", 600))
                self.image_height = int(values.get("height", 600))
                # 1. Start from clean RAM copy
                img = self.source_image.copy()
                # 2. Apply In-Memory Transformations:
                # Rotation
                if self.rotation != 0:
                    img = img.rotate(self.rotation, expand=True)
                # Contrast
                if self.contrast != 1.0:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(self.contrast)
                if self.color != 1.0:
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(self.color)
                if self.brightness != 1.0:
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(self.brightness)
                if self.sharpness != 1.0:
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(self.sharpness) 
             # Scaling / Resize
                if self.is_scaled and self.scale_fac != 1.0:
                    new_w = max(1, int(img.width * self.scale_fac))
                    new_h = max(1, int(img.height * self.scale_fac))
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                elif self.is_resized and (self.image_width != img.width or self.image_height != img.height):
                    img = img.resize((self.image_width, self.image_height))
                # 3. Store current transformed buffer & push to preview!
                if img.mode in ("RGBA", "P") and self.outfile.lower().endswith((".jpg", ".ppm")):
                    img = img.convert("RGB")
                breakpoint()
                img.save(self.outfile)       
                self.current_transformed_image = img
        except OSError:
            return
        im = Image.open(self.outfile)
        self.show_image_window(
            im,
            title="Converted Output Preview",
            max_display_size=(im.width, im.height)
        )
     
       
    def pixel_buff_to_img(self, values: dict = None):
        limg = Image.new("RGB", (self.current_width, self.current_height), color=(0, 0, 0))
        for y, row_pixels in self.rendered_pixels.items():
            if 0 <= y < self.current_height:
                for x, rgb in enumerate(row_pixels):
                    if 0 <= x < self.current_width:
                        limg.putpixel((x, y), rgb)
        return(limg)

    def img_to_pixel_buffer(self, values: dict = None):
        pass 

if __name__ == "__main__":
    app = QuickApp(title="Progressive Ray-Tracer Studio", size=(1050, 780))
    app.set_single_tool(LiveRayTraceViewer)
    app.run()
