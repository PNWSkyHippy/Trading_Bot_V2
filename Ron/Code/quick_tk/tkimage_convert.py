"""
College Grade Calculator Tool
Demonstrates FormPanel numeric inputs, live calculation callbacks, StatGrid badges, and DataTable.
"""

import os
import sys
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageEnhance, ImageFilter

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)
from local_functions import run_magnifyer
try:
    from quick_tk import QuickApp, ToolView
except ImportError:
    # When running or compiling directly inside the quick_tk folder:
    from core.app import QuickApp, ToolView


# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)


class ImageConvertFrontEnd(ToolView):
    """Provide a form-and-preview tool for converting and adjusting images.

    Attributes:
        title (str): The tool's display title.
        description (str): The tool's short description.
        rotated_deg (int): The last rotation angle in degrees.
        image_width (int): The target width in pixels.
        image_height (int): The target height in pixels.
        infile (str | None): The path of the input file.
        is_rotated (bool): Whether a rotation has been requested.
        aspratio (str): The chosen aspect ratio as ``"w/h"``, or ``"None/None"``.
    """
    title = "Image Convert"
    description = "Convert Graphical Images"
    rotated_deg = 0
    image_width = 600
    image_height = 600
    infile = None
    is_rotated = False
    aspratio = "None/None"

    def build_ui(self):
        """Build the options form and the image preview, then set up the menus.

        The form holds filter checkboxes, an input file picker, a save button,
        sliders for contrast, color, brightness, scale and rotation, an aspect
        ratio dropdown, and width and height fields. The preview sits to its right.
        """
        self.source_image = None  # Holds th
        self.orig_image_height = 600
        self.orig_image_width = 600
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.is_scaled = False
        self.is_resized = False
        # 1. Left Input Form
        self.form = self.add_form("Image Creation Options", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._mag = None
        self.bind_all("<Control-Shift-M>", self.on_mag)
        self.bind_all("<Control-Shift-m>", self.on_mag)

        #        self.form.add_dropdown("format", "Output Format", ["bmp", "jpg", "ppm", "gif", "pcx","tga","ico","png","tif"], default="ppm", on_change=self.update_live_preview)
        self.form.add_checkbox(
            "blur", "Blur", default=False, on_change=self.blur_auto_calc
        )
        self.form.add_checkbox(
            "contour", "Contour", default=False, on_change=self.contour_auto_calc
        )
        self.form.add_checkbox(
            "smooth", "Smooth", default=False, on_change=self.smooth_auto_calc
        )
        self.form.add_checkbox(
            "sharpen", "Sharpen", default=False, on_change=self.sharpen_auto_calc
        )
        self.form.add_file_picker(
            "infile",
            "Input File",
            default="",
            mode="open",
            on_change=self.on_file_selected,
        )
        self.form.add_button(
            "Save Image", callback=self.on_save_image, variant="primary"
        )
        self.form.add_slider(
            "contrast",
            "Contrast",
            min_val=0.1,
            max_val=4.0,
            step=0.1,
            default=1.0,
            on_change=self.update_live_preview,
        )
        self.form.add_slider(
            "color",
            "Color",
            min_val=0.1,
            max_val=1.0,
            step=0.1,
            default=1.0,
            on_change=self.update_live_preview,
        )
        self.form.add_slider(
            "brightness",
            "Brightness",
            min_val=0.1,
            max_val=1.0,
            step=0.1,
            default=1.0,
            on_change=self.update_live_preview,
        )
        self.form.add_slider(
            "scalefac",
            "Scale Factor",
            min_val=0.1,
            max_val=10.0,
            step=0.1,
            default=1.0,
            on_change=self.scaled_auto_calc,
        )
        self.form.add_slider(
            "rotation",
            "Rotate (°)",
            min_val=0,
            max_val=360,
            step=1,
            default=0,
            on_change=self.rotated_auto_calc,
        )
        self.form.add_dropdown(
            "aspratio",
            "Aspec Ratio",
            ["16/9", "16/10", "21/9", "4/3", "5/4", "None/None"],
            default="None/None",
            on_change=self.aspratio_auto_calc,
        )
        spin_w = self.form.add_number(
            "width", "Width (px)", min_val=100, max_val=8192, default=600, step=16
        )
        spin_w.bind("<Return>", self.resizedw_auto_calc)
        spin_h = self.form.add_number(
            "height", "Height (px)", min_val=100, max_val=8192, default=600, step=16
        )
        spin_h.bind("<Return>", self.resizedh_auto_calc)

        # 2. Right Results Panel: StatGrid + Breakdown Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)
        # Right Preview Box:
        self.preview = self.add_image_preview(
            title="Input Preview", max_size=(600, 600), parent=right_box
        )
        self.preview.grid(row=0, column=0, sticky="nsew")
        self.on_calculate(self.form.get_values())

        # 2. Right Results Panel: StatGrid + Breakdown Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)
        # Right Preview Box:

        self.preview = self.add_image_preview(
            title="Input Preview", max_size=(600, 600), parent=right_box
        )

        self.preview.grid(row=0, column=0, sticky="nsew")
        # Initial calculation
        self.on_calculate(self.form.get_values())

        self.setup_menus()

    def on_mag(self, event=None):
        # already open? close it (the key toggles) instead of stacking copies
        if self._mag is not None and self._mag.master.winfo_exists():
            self._mag.master.destroy()
            self._mag = None
            return "break"
        self._mag = run_magnifyer(self.app.root)
        return "break"

    def _auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.on_calculate(self.form.get_values())

    def blur_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.blur = bool(values.get("blur", False))
        self.on_calculate(self.form.get_values())
        self.update_live_preview()

    def aspratio_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.aspratio = values.get("aspratio", "16/9")
        self.resizedh_auto_calc()
        self.resizedw_auto_calc()
        #        self.on_calculate(self.form.get_values())
        self.update_live_preview()

    def contour_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.contour - True if values.get("contour", False) else False
        self.on_calculate(self.form.get_values())
        self.update_live_preview()

    def smooth_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.smooth - True if values.get("smooth", False) else False
        self.on_calculate(self.form.get_values())
        self.update_live_preview()

    def sharpen_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.sharpen = bool(values.get("sharpen", False))
        self.on_calculate(self.form.get_values())
        self.update_live_preview()

    def scaled_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.scale_fac = min(10, float(values.get("scalefac", 1.0)))
        self.is_scaled = True
        self.is_resized = False
        self.update_live_preview()

    def rotated_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.rotation = float(values.get("rotation", 1.0))
        self.update_live_preview()

    def pre_on_file_selected(self):
        """Refresh the preview, then run the file-selected handler.

        Raises:
            TypeError: If called without a file path, because ``on_file_selected``
                requires one.
        """
        self.update_live_preview()
        self.on_file_selected()

    def on_save_image(self, values: dict | None = None):
        """Ask for a file name and save the transformed image.

        A warning is shown if no image has been loaded, and an error dialog is
        shown if saving fails.

        Args:
            values (dict | None): Accepted for the button callback but unused.
        """
        if self.source_image is None:
            messagebox.showwarning("Save Image", "No rendered image data to save yet!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Rendered Image",
            defaultextension=".ppm",
            filetypes=[
                ("Ppm Files", "*.ppm"),
                ("Jpg Files", "*.jpg"),
                ("Bmp Files", "*.bmp"),
                ("Gif Files", "*.gif"),
                ("Pcx Files", "*.pcx"),
                ("Tga Files", "*.tga"),
                ("Png Files", "*.png"),
                ("Tif Files", "*.tif"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            img = self.current_transformed_image.copy()
            img.save(file_path)
            messagebox.showinfo(
                "Image Saved", f"Successfully saved image to:\n{file_path}"
            )
            self.set_status(f"💾 Saved to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image: {e}")

    def resizedw_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.image_width = int(values.get("width", self.orig_image_width))
        aspa, aspb = self.aspratio.split("/")
        if aspa != "None" and aspb != "None":
            aspa = float(aspa)
            aspb = float(aspb)
            if aspa:
                self.image_height = int(self.image_width / (aspa / aspb))
            else:
                self.image_height = self.image_height
        self.form.set_value("height", self.image_height)
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()

    #       self.resizedh()

    def resizedh_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.image_height = int(values.get("height", 600))
        aspa, aspb = self.aspratio.split("/")
        if aspa != "None" and aspb != "None":
            aspa = float(aspa)
            aspb = float(aspb)
            if aspa:
                self.image_width = int(self.image_height * (aspa / aspb))
            else:
                self.image_width = self.image_width
        self.form.set_value("width", self.image_width)
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()

    #       self.resizedw()

    def on_file_selected(self, filepath: str):
        """Called the instant the user chooses a file."""
        if filepath and os.path.exists(filepath):
            try:
                self.source_image = Image.open(filepath)
                self.orig_image_width = self.source_image.width
                self.orig_image_height = self.source_image.height
                self.update_live_preview()
            except Exception:
                self.preview.clear()
        self.orig_image_width = self.source_image.width
        self.orig_image_height = self.source_image.height
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
        self.smooth = values.get("smooth", False)
        self.blur = values.get("blur", False)
        self.contour = values.get("contour", False)
        self.sharpen = values.get("sharpen", False)
        self.scale_fac = min(10, float(values.get("scalefac", 60)))
        #       self.image_width = int(values.get("width", 600))
        #        self.image_height = int(values.get("height", 600))
        # 1. Start from clean RAM copy
        img = self.source_image.copy()
        # 2. Apply In-Memory Transformations:
        # Rotation
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
        if self.color != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(self.color)
        if self.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness)
        # Scaling / Resize
        if self.is_scaled:
            new_w = max(1, int(img.width * self.scale_fac))
            new_h = max(1, int(img.height * self.scale_fac))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        elif self.is_resized and (
            self.image_width != img.width or self.image_height != img.height
        ):
            img = img.resize((self.image_width, self.image_height))
        elif (self.image_width != img.width) or (self.image_height != img.height):
            img = img.resize(self.image_width, self.image_height)
        # 3. Store current transformed buffer & push to preview!
        self.current_transformed_image = img
        self.preview.set_image(
            img, info_text=f"{img.width}x{img.height} px | In-Memory"
        )

    def on_calculate(self, values: dict):
        """Copy the form values onto the tool and refresh the preview.

        Updates the scale, filter, size and file attributes, then shows the input
        file in the preview or clears the preview if there is no such file.

        Args:
            values (dict): The current form values keyed by field name.

        Raises:
            TypeError: If ``values`` has no ``width`` entry, because ``int(None)``
                is not valid.
        """
        #       self.format = values.get("format", "ppm")
        self.is_demo = values.get("is_demo", "False")
        self.scale_fac = min(10, float(values.get("scalefac", 1.0)))
        self.is_scaled = self.scale_fac != 1
        self.rotate_deg = int(values.get("rotate_deg", 0))
        self.is_rotated = bool(values.get("rotate_deg", "False"))
        self.width = int(values.get("width", None))
        self.smooth = values.get("smooth", False)
        self.sharpen = values.get("sharpen", False)
        self.contour = values.get("contour", False)
        self.blur = values.get("blur", False)
        aspa, aspb = self.aspratio.split("/")
        if aspa != "None" and aspb != "None":
            aspa = float(aspa)
            aspb = float(aspb)
            if aspa:
                self.image_height = int(self.orig_image_width / (aspa / aspb))
            else:
                self.height = values.get("height")
        self.is_resized = self.orig_image_width is not None
        self.outfile = values.get("outfile", None)
        if not self.is_demo:
            self.infile = values.get("infile", None)
        # Update In-Frame Preview
        if self.infile and os.path.exists(self.infile):
            self.preview.set_image(self.infile)
        else:
            self.preview.clear()

    #       sys.stderr.write(f'format: {self.format}, is_demo: {self.is_demo}, Sclae_fac: {self.scale_fac}, is_scaled:'
    #                        f'{self.is_scaled}, Width: {self.width}, Height: {self.height}, Outfile: {self.outfile}'
    #                        f'Infile: {self.infile}.is_resize: {self.is_resize}\n'
    #        )

    def setup_menus(self):
        """Add the File menu with its Exit item."""
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_item("Exit Application", self.app.root.quit, shortcut="Alt+F4")


if __name__ == "__main__":
    app = QuickApp(title="Image Convert", size=(980, 920))
    app.set_single_tool(ImageConvertFrontEnd)
    app.run()
