"""
College Grade Calculator Tool
Demonstrates FormPanel numeric inputs, live calculation callbacks, StatGrid badges, and DataTable.
"""

import os
import sys
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


class PaintCanvas(tkinter.Canvas):
    def __init__(self, master, image):
        tkinter.Canvas.__init__(self, master,
                                width=image.size[0], height=image.size[1])

        # fill the canvas
        self.tile = {}
        self.tilesize = tilesize = 32
        xsize, ysize = image.size
        for x in range(0, xsize, tilesize):
            for y in range(0, ysize, tilesize):
                box = x, y, min(xsize, x+tilesize), min(ysize, y+tilesize)
                tile = ImageTk.PhotoImage(image.crop(box))
                self.create_image(x, y, image=tile, anchor=tkinter.NW)
                self.tile[(x, y)] = box, tile

        self.image = image

        self.bind("<B1-Motion>", self.paint)

    def paint(self, event):
        xy = event.x - 10, event.y - 10, event.x + 10, event.y + 10
        im = self.image.crop(xy)

        # process the image in some fashion
        im = im.convert("L")

        self.image.paste(im, xy)
        self.repair(xy)

    def repair(self, box):
        # update canvas
        dx = box[0] % self.tilesize
        dy = box[1] % self.tilesize
        for x in range(box[0]-dx, box[2]+1, self.tilesize):
            for y in range(box[1]-dy, box[3]+1, self.tilesize):
                try:
                    xy, tile = self.tile[(x, y)]
                    tile.paste(self.image.crop(xy))
                except KeyError:
                    pass  # outside the image
        self.update_idletasks()

class ImageConvertFrontEnd(ToolView):
    title = "Image Convert"
    description = "Convert Graphical Images"
   
    def build_ui(self):
        self.is_resize = False
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Input Form
        self.form = self.add_form("Image Creation Options", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
   

        self.form.add_dropdown("format", "Output Format", ["bmp", "jpg", "ppm", "gif", "pcx","tga","ico","png","tif"], default="ppm", on_change=self._auto_calc)
        self.form.add_checkbox("is_demo", "Demo Mode", default=False, on_change=self._auto_calc)
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
        self.form.add_file_picker("infile","Input File", default="", mode="open", on_change=self._auto_calc)
        self.form.add_number("scalefac","Scale Factor", default=1, min_val=.1, max_val=10, step=.1, is_float=True, on_change=self._auto_calc)
        self.form.add_number("width", "Wih of output at 15/9 aspect", default=400, min_val=100, max_val=1000, step=25, is_float=True, on_change=self._auto_calc)
        self.form.add_button("Convert Image", callback=self.on_view_clicked, variant="primary")
        
        # 2. Right Results Panel: StatGrid + Breakdown Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)
        
        # Initial calculation
        self.on_calculate(self.form.get_values())
        self.on_view_clicked(self.form.get_values())

    def _auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.on_calculate(self.form.get_values())

    def on_view_clicked(self, values: dict):
        self.make_image(values)


    def make_image(self, values: dict):
        # values["export_file"] contains the full, verified output Path!
        self.outfile = values.get("export_file","ray_traced.ppm")
 
#        sys.stderr.write(f'Outfile is: {self.outfile}')
#        sys.stderr.flush()
#       with open(dest_path, "w") as f:
#           f.write("id,symbol,pnl\n1,ES,500.00\n")

    
    def on_calculate(self, values: dict):
        self.format = values.get("format", "ppm")
        self.is_demo = values.get("is_demo", "False")
        self.scale_fac = float(values.get("scalefac", 1.0))
        self.is_scaled = True if  self.scale_fac > 1 else False
            
        self.width = int(values.get("width", 400))
        self.height = int(self.width/(16/9)) if values.get("width") else 225
        self.is_resize = True if self.width != 400 else False
        self.outfile = values.get("outfile", "ray-traced.py")
        self.infile =  values.get("infile", None)
        if self.infile  :
            root = tkinter.Tk()
            root.title("PPM Image Display")
            root.geometry("400x400")

            # 2. Create the ttk.Frame panel
            frame = ttk.Frame(root, padding="10")
            frame.pack(fill="both", expand=True)

            # 3. Load the PPM image using PhotoImage
            # Replace 'example.ppm' with the actual path to your file
            try:
                ppm_image = tk.PhotoImage(file=self.infile)

                # 4. Create a ttk.Label to hold the image
                image_label = ttk.Label(frame, image=ppm_image)
                image_label.pack(fill="both", expand=True)

                # CRITICAL: Keep a reference to the image object to prevent garbage collection
                image_label.image = ppm_image

            except tk.TclError:
                # Fallback error handling if the file is missing or invalid
                error_label = ttk.Label(frame, text="Error: Could not load PPM image file.")
                error_label.pack()

            # Start the application loop
#            root.mainloop()














            img = Image.open(self.infile)
            PaintCanvas(root, img).pack()
   
            
#        sys.stderr.write(f'format: {self.format}, is_demo: {self.is_demo}, Sclae_fac: {self.scale_fac}, is_scaled:'
#                         f'{self.is_scaled}, Width: {self.width}, Height: {self.height}, Outfile: {self.outfile}'
#                         f'Infile: {self.infile}.is_resize: {self.is_resize}\n'
#        )
            
#       sys.stderr.flush()
"""
        # Weights: Quizzes 20%, HW 20%, Midterm 25%, Part 10%, Final 25%
        q_pts = (q * 0.30)
        part_pts = (part * 0.10)
        final_pts = (final_est * 0.60)
        final_bonus = (bonus * 0.10)
        current_earned = q_pts + part_pts + final_bonus
        total_projected = current_earned + final_pts

        # Determine target threshold
        target_pct = 90.0
        if "87" in target_str:
            target_pct = 87.0
        elif "83" in target_str:
            target_pct = 83.0
        elif "80" in target_str:
            target_pct = 80.0
        elif "70" in target_str:
            target_pct = 70.0

        # Needed on final: (target_pct - current_earned) / 0.25
        needed_on_final = max(0.0, (target_pct - current_earned) / 0.25)
"""
"""       # Letter grade lookup
        def _get_letter(score):
            if score >= 93: return "A"
            if score >= 90: return "A-"
            if score >= 87: return "B+"
            if score >= 83: return "B"
            if score >= 80: return "B-"
            if score >= 77: return "C+"
            if score >= 70: return "C"
            if score >= 60: return "D"
            return "F"
"""


if __name__ == "__main__":
    app = QuickApp(title="Image Convert", size=(980, 640))
    app.set_single_tool(ImageConvertFrontEnd)
    app.run()
