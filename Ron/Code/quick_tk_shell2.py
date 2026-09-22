import os, sys
from PIL import Image, ImageTk, ImageEnhance
import PIL
from tkinter import *
import tkinter

sys.path.insert(0, r"C:\Users\Linda\trading_bot_v2\Ron\Code\quick_tk")

from quick_tk import QuickApp, ToolView


class PaintCanvas(tkinter.Canvas):
    def __init__(self, master, image):
        tkinter.Canvas.__init__(self, master, width=image.size[0], height=image.size[1])

        # fill the canvas
        self.tile = {}
        self.tilesize = tilesize = 32
        xsize, ysize = image.size
        for x in range(0, xsize, tilesize):
            for y in range(0, ysize, tilesize):
                box = x, y, min(xsize, x + tilesize), min(ysize, y + tilesize)
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
        for x in range(box[0] - dx, box[2] + 1, self.tilesize):
            for y in range(box[1] - dy, box[3] + 1, self.tilesize):
                try:
                    xy, tile = self.tile[(x, y)]
                    tile.paste(self.image.crop(xy))
                except KeyError:
                    pass  # outside the image
        self.update_idletasks()


class MyQuickTool(ToolView):
    title = "My Utility"

    def build_ui(self):
        # 1. Inputs
        form = self.add_form("Parameters")
        form.add_text("query", "Search Term", default="python")
        form.add_slider("limit", "Max Results", min_val=5, max_val=100, default=25)
        form.add_button("Execute", callback=self.on_run, variant="primary")

        # 2. Outputs
        self.stats = self.add_stat_grid(columns=2)
        self.table = self.add_data_table(columns=["ID", "Name", "Status"])
        if len(sys.argv) != 2:
            print("Usage: enhancer file")
            sys.exit(1)
        im = PIL.Image.open(sys.argv[1])
        mycanvas = self.tk
        PaintCanvas(self, im)

    def on_run(self, inputs: dict):
        # 3. Your logic!

        print("Inputs received:", inputs)
        self.stats.set_metrics(
            {"Total Found": (42, "success"), "Query": (inputs["query"], "info")}
        )
        self.table.set_data([[1, "Item A", "Active"], [2, "Item B", "Pending"]])


if __name__ == "__main__":
    app = QuickApp(title="My Tool")
    app.set_single_tool(MyQuickTool)
    app.run()
