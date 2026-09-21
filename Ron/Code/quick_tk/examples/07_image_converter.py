"""
Image Converter & Format Utility Tool
Demonstrates in-frame image preview with auto-scaling and separate Toplevel popup viewer.
"""

import os
import sys
from tkinter import ttk, messagebox

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def create_demo_image() -> str:
    """Creates a sample test image if the user doesn't have one ready."""
    demo_path = os.path.join(BASE_DIR, "examples", "sample_input.png")
    if not os.path.exists(demo_path) and HAS_PIL:
        img = Image.new("RGB", (600, 400), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 550, 350], outline=(137, 180, 250), width=4)
        draw.text((180, 180), "QuickTk Sample Input Image", fill=(205, 214, 244))
        img.save(demo_path)
    return demo_path


class ImageConverterTool(ToolView):
    title = "Image Converter & Resizer"
    description = "Convert image formats, resize dimensions, and preview results"

    def build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        demo_img = create_demo_image()

        # 1. Left Form Panel (Controls & Parameters)
        self.form = self.add_form("Conversion Settings", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.form.add_file_picker(
            name="infile",
            label="Input File",
            default=demo_img,
            mode="open",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ppm;*.tif;*.pcx;*.tga"), ("All Files", "*.*")],
            on_change=self._on_input_changed,
        )

        self.form.add_output_file_picker(
            name="outfile",
            label="Output File",
            default_filename="image_converted.jpg",
            default_extension=".jpg",
            filetypes=[
                ("JPG Files", "*.jpg"),
                ("PNG Files", "*.png"),
                ("PPM Files", "*.ppm"),
                ("BMP Files", "*.bmp"),
                ("GIF Files", "*.gif"),
                ("TIFF Files", "*.tif"),
                ("All Files", "*.*"),
            ],
            on_change=self._auto_calc,
        )

        self.form.add_dropdown("format", "Target Format", ["JPG", "PNG", "PPM", "BMP", "GIF", "TIFF"], default="JPG", on_change=self._on_format_changed)
        self.form.add_number("width", "Resize Width (px)", default=600, min_val=50, max_val=4000, step=50, on_change=self._auto_calc)
        self.form.add_slider("scalefac", "Scale Factor", min_val=0.25, max_val=3.0, default=1.0, step=0.25, on_change=self._auto_calc)

        self.form.add_button("Convert & View Image ▶", callback=self.on_view_clicked, variant="primary")

        # 2. Right Side: In-Frame Input Preview + Status Info
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=1)

        # In-Frame Image Preview Component (Auto-scales to fit the frame!)
        self.preview = self.add_image_preview(
            title="Input File Preview (Scaled to Frame)",
            max_size=(500, 380),
            parent=right_box,
        )
        self.preview.grid(row=0, column=0, sticky="nsew")

        # Initial preview load
        self.on_calculate(self.form.get_values())

    def _on_input_changed(self, new_path: str):
        """Called when a new input file is picked."""
        self._auto_calc()

    def _on_format_changed(self, new_format: str):
        """Automatically updates the output filename extension when format dropdown changes."""
        values = self.form.get_values()
        cur_out = values.get("outfile", "")
        if cur_out:
            base, _ = os.path.splitext(cur_out)
            self.form.set_values({"outfile": f"{base}.{new_format.lower()}"})

    def _auto_calc(self, _=None):
        self.on_calculate(self.form.get_values())

    def on_calculate(self, values: dict):
        self.infile = values.get("infile", "")
        self.outfile = values.get("outfile", "output.jpg")
        self.target_format = values.get("format", "JPG")
        self.target_width = int(values.get("width", 600))
        self.scale_fac = float(values.get("scalefac", 1.0))

        # 1. Update In-Frame Preview of the Input File
        if self.infile and os.path.exists(self.infile):
            self.preview.set_image(self.infile)
            self.set_status(f"Loaded input preview: {os.path.basename(self.infile)}")
        else:
            self.preview.clear()

    def on_view_clicked(self, values: dict):
        self.on_calculate(values)
        self.make_image(values)

    def make_image(self, values: dict):
        if not self.infile or not os.path.exists(self.infile):
            messagebox.showwarning("Missing Input", "Please select a valid input image file first.")
            return

        if not HAS_PIL:
            messagebox.showerror("PIL Missing", "Pillow is required for image conversion.")
            return

        try:
            # 1. Perform Image Processing with Pillow
            im = Image.open(self.infile)
            
            # Convert RGBA to RGB if saving to JPG/PPM
            if self.target_format.upper() in ("JPG", "JPEG", "PPM") and im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGB")

            # Apply scale factor or custom width
            if self.scale_fac != 1.0:
                new_w = max(10, int(im.width * self.scale_fac))
                new_h = max(10, int(im.height * self.scale_fac))
                im = im.resize((new_w, new_h), resample=Image.LANCZOS)
            elif self.target_width != im.width:
                aspect = im.height / im.width
                new_h = max(10, int(self.target_width * aspect))
                im = im.resize((self.target_width, new_h), resample=Image.LANCZOS)

            # Save converted output
            out_format = "JPEG" if self.target_format.upper() == "JPG" else self.target_format.upper()
            im.save(self.outfile, format=out_format)

            self.set_status(f"Successfully converted to {self.outfile}")

            # 2. OPEN A NEW SEPARATE TKINTER WINDOW FOR THE CONVERTED OUTPUT!
            self.show_image_window(
                self.outfile,
                title="Converted Image Output",
                max_display_size=(800, 600)
            )

        except Exception as e:
            messagebox.showerror("Conversion Failed", f"Error converting image:\n{e}")


if __name__ == "__main__":
    app = QuickApp(title="QuickTk Image Converter", size=(980, 640), theme="Dark Obsidian")
    app.set_single_tool(ImageConverterTool)
    app.run()
