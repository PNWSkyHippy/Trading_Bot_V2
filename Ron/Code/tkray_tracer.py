import os
import subprocess
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
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

        # Resolution controls
        self.form.add_slider("width", "Width (px)", min_val=100, max_val=1920, default=600, step=16)
        self.form.add_slider("height", "Height (px)", min_val=100, max_val=1080, default=600, step=16)

        # Action Buttons
        self.form.add_button("Start Progressive Render ▶", callback=self.on_start_render, variant="primary")
        self.form.add_button("Cancel / Stop Render ⏹", callback=self.on_stop_render, variant="outline")
        self.form.add_button("Save Rendered Image 💾", callback=self.on_save_image, variant="surface")

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
        self.form.set_value("width", w)
        self.form.set_value("height", h)

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


if __name__ == "__main__":
    app = QuickApp(title="Progressive Ray-Tracer Studio", size=(1050, 780))
    app.set_single_tool(LiveRayTraceViewer)
    app.run()
