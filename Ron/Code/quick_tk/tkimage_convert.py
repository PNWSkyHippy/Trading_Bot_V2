"""
College Grade Calculator Tool
Demonstrates FormPanel numeric inputs, live calculation callbacks, StatGrid badges, and DataTable.
"""

import os
import sys, io
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import tkinter
# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)


class ImageConvertFrontEnd(ToolView):
    title = "Image Convert"
    description = "Convert Graphical Images"

    def create_ppm(self):
        image_width = 256
        image_height = 256
   
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
#        self.is_resize = False
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Input Form
        self.form = self.add_form("Image Creation Options", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
   

        self.form.add_dropdown("format", "Output Format", ["bmp", "jpg", "ppm", "gif", "pcx","tga","ico","png","tif"], default="ppm", on_change=self._auto_calc)
        self.form.add_checkbox("is_demo", "Demo Mode", default=False, on_change=self.demo_auto_calc)
#        self.form.add_file_picker("outfile","Output File", default="ray_traced.ppm", mode="open")
        self.form.add_output_file_picker(
            name="outfile",
            label="Output File",
            default_filename="ray_traced.ppm",
            default_extension=".ppm",
            on_change=self._auto_calc,
            filetypes=[("Ppm Files", "*.ppm"), ("Jpg Files", "*.jpg"), 
                    ("Bmp Files", "*.bmp"), ("Gif Files", "*.gif"),
                    ("Pcx Files", "*.pcx"), ("Tga Files", "*.tga"),
                    ("Png Files", "*.png"), ("Tif Files", "*.tif"),
                    ("All Files", "*.*")]
        )
        self.form.add_file_picker("infile","Input File", default="", mode="open", on_change=self.infile_auto_calc)
        self.form.add_number("scalefac","Scale Factor", default=1, min_val=.1, max_val=10, step=.1, is_float=True, on_change=self.scaled_auto_calc)
        self.form.add_number("width", "Wih of output at 15/9 aspect", default=400, min_val=100, max_val=1000, step=25, is_float=True, on_change=self.resize_auto_calc)
        self.form.add_button("Convert Image", callback=self.on_view_clicked, variant="primary")
        
        # 2. Right Results Panel: StatGrid + Breakdown Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)
        
        self.preview = self.add_image_preview(
            title="Input Preview",
            max_size=(500, 380),
            parent=right_box
        )

        self.preview.grid(row=0, column=0, sticky="nsew")
        # Initial calculation
        self.on_calculate(self.form.get_values())
        self.on_view_clicked(self.form.get_values())
        
        self.setup_menus()

    def _auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.on_calculate(self.form.get_values())
 
    def scaled_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.is_resize - False
        self.is_scaled = True
        self.on_calculate(self.form.get_values())

    def resize_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.is_resize - True
        self.is_scaled = False
        values = self.form.get_values()
        self.width = values.get("width", self.width)
        self.on_calculate(self.form.get_values())
        
    def demo_auto_calc(self, _=None):
        breakpoint()
        ppm_img = self.create_ppm()
        breakpoint()
        # 1. Convert your string buffer to bytes (if it isn't already bytes)
        ppm_bytes = ppm_img.encode('utf-8') if isinstance(ppm_img, str) else ppm_img
        # 2. Wrap the buffer in an in-memory stream
        ppm_stream = io.BytesIO(ppm_bytes)
        self.infile = ppm_stream
        self.infile_auto_calc()

        
  



    def infile_auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        values = self.form.get_values()
        file_name = values.get("infile", None)
        self.infile = file_name 
        self.on_calculate(self.form.get_values())
        
    def on_view_clicked(self, values: dict):
        self.on_calculate(values)
        self.make_image(values)


    def make_image(self, values: dict):
        # values["outfile"] contains the full, verified output Path!
        if not self.infile:
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
            with Image.open(self.infile) as img: 
                if self.is_scaled:
                    width = int(float(img.width) * float(self.scale_fac))
                    height = int(float(img.height) * float(self.scale_fac))
                    out = img.resize((width, height))
                elif self.is_resize:
                    out = img.resize((self.width, self.height))
                else:
                    # Fallback if is_resize is False so 'out' is always defined
                    out = img
                if out.mode in ("RGBA", "P") and self.outfile.lower().endswith((".jpg", ".ppm")):
                    out = out.convert("RGB")
                out.save(self.outfile)       
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
            
        self.width = int(values.get("width", None))
        self.height = int(self.width/(16/9)) if values.get("width") else 225
        self.is_resize = True if self.width is not None else False
        self.outfile = values.get("outfile", None)
        if not self.is_demo:
            self.infile =  values.get("infile", None)
       # Update In-Frame Preview
        if (self.infile and os.path.exists(self.infile)) or self.is_demo:
            self.preview.set_image(self.infile)
        else:
            self.preview.clear()
   
            
        sys.stderr.write(f'format: {self.format}, is_demo: {self.is_demo}, Sclae_fac: {self.scale_fac}, is_scaled:'
                         f'{self.is_scaled}, Width: {self.width}, Height: {self.height}, Outfile: {self.outfile}'
                         f'Infile: {self.infile}.is_resize: {self.is_resize}\n'
        )

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_item("Exit Application", self.app.root.quit, shortcut="Alt+F4")


if __name__ == "__main__":
    app = QuickApp(title="Image Convert", size=(980, 640))
    app.set_single_tool(ImageConvertFrontEnd)
    app.run()
