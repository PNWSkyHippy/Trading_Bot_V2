# ex01_grid_basics.py  -  GRID: rows, columns, weight, minsize, span, sticky
import tkinter as tk

root = tk.Tk()
root.title("ex01 - grid basics")
root.geometry("520x320")

# 1) Define the PAGE: 3 columns x 3 rows.
#    weight = how much EXTRA space this row/column gets when the window grows.
#    weight=0 (default) -> stays its natural size.   minsize = never smaller than this.
root.columnconfigure(0, weight=0, minsize=120)   # fixed-ish column
root.columnconfigure(1, weight=1)                # grows
root.columnconfigure(2, weight=2)                # grows twice as fast as column 1
root.rowconfigure(0, weight=0, minsize=50)       # header row: fixed height
root.rowconfigure(1, weight=1)                   # middle row: grows
root.rowconfigure(2, weight=0, minsize=40)       # bottom row: fixed height


def box(text, color):
    """Tiny helper: a coloured label so you can SEE each cell."""
    return tk.Label(root, text=text, bg=color, fg="black", relief="solid", bd=1)


# 2) Put things in cells.  sticky says how a widget fills its cell:
#    "n s e w" = stretch to touch that side.  "nsew" = fill the whole cell.
box("row0 col0", "#ffd166").grid(row=0, column=0, sticky="nsew")
box("row0 col1  columnspan=2", "#ef476f").grid(row=0, column=1, columnspan=2, sticky="nsew")
box("row1-2 col0  rowspan=2", "#06d6a0").grid(row=1, column=0, rowspan=2, sticky="nsew")
box("row1 col1  sticky=nsew", "#118ab2").grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
box("row1 col2  sticky=nsew", "#9d8df1").grid(row=1, column=2, sticky="nsew", padx=4, pady=4)
box("row2 col1  no sticky (centred, natural size)", "#f4a261").grid(row=2, column=1)
box("row2 col2  sticky=w", "#e9c46a").grid(row=2, column=2, sticky="w")

root.mainloop()
