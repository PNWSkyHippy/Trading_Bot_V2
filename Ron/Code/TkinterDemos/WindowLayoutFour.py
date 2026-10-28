# ex10_size_to_fit.py  -  how big is a window / frame if you DON'T set a size?
#   Answer: exactly big enough for its contents.  Frames SHRINK-WRAP their children.
#   (called "propagation").  Turn it off with pack_propagate(False) / grid_propagate(False).
import tkinter as tk

root = tk.Tk()
root.title("ex10 - size to fit  (no root.geometry() call!)")

# LEFT: a frame asks for width=300,height=120 but has a small label in it
# and propagation is ON (default) -> frame IGNORES 300x120, shrink-wraps the label.
f1 = tk.Frame(root, bg="#ef476f", width=300, height=120)
f1.grid(row=0, column=0, padx=10, pady=10)
tk.Label(f1, text="propagate ON (default)\nwidth/height ignored").pack()

# RIGHT: same, but propagation OFF -> frame obeys width/height.
f2 = tk.Frame(root, bg="#06d6a0", width=300, height=120)
f2.grid(row=0, column=1, padx=10, pady=10)
f2.pack_propagate(False)          # f2's children use pack -> pack_propagate(False)
tk.Label(f2, text="propagate OFF\nsize is 300x120").pack()

# BOTTOM: a frame whose children use GRID needs grid_propagate(False) instead.
f3 = tk.Frame(root, bg="#ffd166", width=620, height=60)
f3.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10))
f3.grid_propagate(False)          # f3's children use grid -> grid_propagate(False)
tk.Label(f3, text="grid_propagate(False): size is 620x60").grid(row=0, column=0, padx=10, pady=10)

# Ask what size the window wants:
root.update_idletasks()
print("window wants", root.winfo_reqwidth(), "x", root.winfo_reqheight())

root.mainloop()