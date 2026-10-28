# ex12_shrink.py  -  SHRINKING the window: what survives?  (minsize, sticky, weights)
#   Drag the window smaller and watch.  Then try removing the minsize line.
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("ex12 - shrinking")
root.geometry("640x340")
root.minsize(420, 240)          # the user can't drag smaller than this. (maxsize() also exists)
# root.resizable(False, False)  # or: forbid resizing completely

root.columnconfigure(0, weight=0, minsize=140)   # sidebar: never narrower than 140
root.columnconfigure(1, weight=1)                # content: absorbs all size changes
root.rowconfigure(1, weight=1)

top = tk.Frame(root, bg="#ef476f", height=40)
top.grid(row=0, column=0, columnspan=2, sticky="ew")
tk.Label(top, text="sticky='ew': stretches sideways only", bg="#ef476f").pack(pady=8)

side = tk.Frame(root, bg="#06d6a0")
side.grid(row=1, column=0, sticky="ns")           # sticky ns: tall but NOT wide
tk.Label(side, text="minsize=140\nweight=0", bg="#06d6a0").pack(padx=10, pady=10)

content = tk.Frame(root, bg="#118ab2")
content.grid(row=1, column=1, sticky="nsew")      # nsew: fills the whole cell
content.columnconfigure(0, weight=1)
content.rowconfigure(0, weight=1)

# the Text box is the part that absorbs the shrink
txt = tk.Text(content, wrap="word")
txt.insert("1.0", "This Text widget is sticky='nsew' in a weight=1 row/column,\n"
                  "so it grows and shrinks with the window.\n\n"
                  "The buttons below keep their size: they have no sticky and the\n"
                  "row they live in has weight=0.")
txt.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

btns = tk.Frame(content, bg="#118ab2")
btns.grid(row=1, column=0, sticky="e", padx=8, pady=(0, 8))
ttk.Button(btns, text="OK").grid(row=0, column=0, padx=4)
ttk.Button(btns, text="Cancel").grid(row=0, column=1, padx=4)

root.mainloop()