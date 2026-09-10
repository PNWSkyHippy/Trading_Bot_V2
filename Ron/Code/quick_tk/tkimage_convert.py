"""
College Grade Calculator Tool
Demonstrates FormPanel numeric inputs, live calculation callbacks, StatGrid badges, and DataTable.
"""

import os
import sys, io
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageEnhance
import tkinter
# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

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
    title = "Image Convert"
    description = "Convert Graphical Images"
    rotated_deg = 0
    infile = None
    is_rotated = False
        
    def create_ppm(self):
        image_width = 600
        image_height = 600
   
        ppm_image = f'P3\n{image_width} {image_height}\n255\n'
        for j in range(image_height):
            row_rgb = ""
            for i in range (image_width):
                r = float(i) / (image_width-1)
                g = float(j) / (image_height-1)
                b = 0.0;

                ir = int(255.999 * r)
                ig = int(255.999 * g)
                ib = int(255.999 * b)

                row_rgb += f'{ir} {ig} {ib}\t\t'
            ppm_image += f'{row_rgb}\n'  
        return ppm_image
 
                
    def build_ui(self):
        self.source_image = None  # Holds th
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Input Form
        self.form = self.add_form("Image Creation Options", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
   

        self.form.add_dropdown("format", "Output Format", ["bmp", "jpg", "ppm", "gif", "pcx","tga","ico","png","tif"], default="ppm", on_change=self.update_live_preview)
        self.form.add_checkbox("is_blur", "Blur", default=False, on_change=self.blur_auto_calc)
        self.form.add_checkbox("is_contour", "Contour", default=False, on_change=self.contour_auto_calc)
        self.form.add_checkbox("sharpness", "Sharpen", default=False, on_change=self.sharpness_auto_calc)
        self.form.add_checkbox("is_smooth", "Smooth", default=False, on_change=self.smooth_auto_calc)
#        self.form.add_file_picker("outfile","Output File", default="ray_traced.ppm", mode="open")
        self.form.add_file_picker("infile", "Input File", default="", mode="open",on_change=self.on_file_selected)
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
       # Left Form with on_change callbacks:
        )   
        self.form.add_slider("rotation", "Rotate (°)", min_val=0, max_val=360, step=1, default=0, on_change=self.update_live_preview)
        self.form.add_slider("contrast", "Contrast", min_val=0.1, max_val=4.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("color", "Color", min_val=0.1, max_val=1.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("brightness", "Brightness", min_val=0.1, max_val=1.0, step=0.1, default=1.0, on_change=self.update_live_preview)
        self.form.add_slider("scalefac", "Scale Factor", min_val=0.1, max_val=10.0, step=0.1, default=1.0, on_change=self.scaled_auto_calc)
        self.form.add_number("width", "Width (px)", min_val=100, max_val=8192, default=600, step=16,on_change=self.resizedw_auto_calc)
        self.form.add_number("height", "Height (px)", min_val=100, max_val=4915, default=360, step=16,on_change=self.resizedh_auto_calc)
        self.form.add_button("Convert Image", callback=self.on_view_clicked, variant="primary")
        
        # 2. Right Results Panel: StatGrid + Breakdown Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)
         # Right Preview Box:

        self.preview = self.add_image_preview(
            title="Input Preview",
            max_size=(600, 600),
            parent=right_box
        )

        self.preview.grid(row=0, column=0, sticky="nsew")
        # Initial calculation
        self.on_calculate(self.form.get_values())
 #       self.on_view_clicked(self.form.get_values())
        
        self.setup_menus()
 
  
    def _auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.on_calculate(self.form.get_values())
        
    def blur_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.blur - True if values.get("blur", False) else False
        self.on_calculate(self.form.get_values())
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
        self.smooth - True if values.get("smoth", False) else False
        self.on_calculate(self.form.get_values())
        self.update_live_preview()
        
    def sharpness_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.sharpness - True if values.get("sharpness", False) else False
        self.on_calculate(self.form.get_values())
        self.update_live_preview()
        
    def scaled_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.scale_fac = float(values.get("scalefac", 1.0))
        self.is_scaled = True
        self.is_resized = False
        self.update_live_preview()
        
    def resizedw_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.image_width - int(values.get("width", 600))
        self.image_height = int(self.image_width / (15.0 / 9.0))
        values["height"] = self.image.height
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()
        self.resizedh()
        
    def resizedh_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        self.image_height - int(values.get("height", 600))
        self.image_width = int(self.image_height * (15.0 / 9.0))
        values["width"] = self.image_width
        self.is_resized = True
        self.is_scaled = False
        self.update_live_preview()
        self.resizedw()

   
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
        self.smooth = float(values.get("smooth", 1.0))
        self.blur = float(values.get("blur", 1.0))
        self.contour = float(values.get("contour", 1.0))
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


        
    def demo_auto_calc(self, _=None):
        ppm_img = self.create_ppm()
        # 1. Convert your string buffer to bytes (if it isn't already bytes)
        ppm_bytes = ppm_img.encode('utf-8') if isinstance(ppm_img, str) else ppm_img
        # 2. Wrap the buffer in an in-memory stream
        ppm_stream = io.BytesIO(ppm_bytes)
        self.infile = "default_image.ppm"
        img = Image.open(ppm_stream)
        img.save("default_image.ppm")
        self.infile_auto_calc()

        
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
 
    
    def on_calculate(self, values: dict):
        self.format = values.get("format", "ppm")
        self.is_demo = values.get("is_demo", "False")
        self.scale_fac = float(values.get("scalefac", 1.0))
        self.is_scaled = True if  self.scale_fac !=  1 else False
        self.rotate_deg = int(values.get("rotate_deg", 0))
        self.is_rotated =True if values.get("rotate_deg", "False") else False    
        self.width = int(values.get("width", None))
        self.smooth = int(values.get("smooth", 1))
        self.sharpness = int(values.get("shapness", 1))
        self.contour = int(values.get("contour", 1))
        self.blur = int(values.get("blur", 1))
        self.height = int(self.width/(16/9)) if values.get("width") else 225
        self.is_resized = True if self.width is not None else False
        self.outfile = values.get("outfile", None)
        if not self.is_demo:
            self.infile =  values.get("infile", None)
       # Update In-Frame Preview
        if (self.infile and os.path.exists(self.infile)):
            self.preview.set_image(self.infile)
        else:
            self.preview.clear()
   
            
#       sys.stderr.write(f'format: {self.format}, is_demo: {self.is_demo}, Sclae_fac: {self.scale_fac}, is_scaled:'
#                        f'{self.is_scaled}, Width: {self.width}, Height: {self.height}, Outfile: {self.outfile}'
#                        f'Infile: {self.infile}.is_resize: {self.is_resize}\n'
#        )

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_item("Exit Application", self.app.root.quit, shortcut="Alt+F4")


if __name__ == "__main__":
    app = QuickApp(title="Image Convert", size=(980, 780))
    app.set_single_tool(ImageConvertFrontEnd)
    app.run()
