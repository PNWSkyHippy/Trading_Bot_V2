# ex09_paper_filled.py  -  paper sketch step 2: controls inside each panel, stretch-friendly
#   Try it: drag the window bigger and smaller.  Notice what grows and what doesn't.
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("ex09 - paper design, filled in")
root.geometry("820x460")
root.minsize(600, 320)                        # can't shrink below this (see ex12)

root.columnconfigure(0, weight=1, uniform="cols")
root.columnconfigure(1, weight=1, uniform="cols")
root.columnconfigure(2, weight=2, uniform="cols")
root.rowconfigure(1, weight=1)

# ---------------- the 4 panels ----------------
topbar = tk.Frame(root, bg="#ef476f")
left = tk.Frame(root, bg="#d9f7ee")
middle = tk.Frame(root, bg="#fff3cd")
right = tk.Frame(root, bg="#d6ebf5")
topbar.grid(row=0, column=0, columnspan=3, sticky="ew")
left.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)
middle.grid(row=1, column=1, sticky="nsew", padx=4, pady=8)
right.grid(row=1, column=2, sticky="nsew", padx=(4, 8), pady=8)

# ---------------- TOP BAR: title on the left, buttons on the right ----------------
topbar.columnconfigure(1, weight=1)           # the empty middle column soaks up the stretch
tk.Label(topbar, text="My App", bg="#ef476f", fg="white",
         font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, padx=12, pady=10)
ttk.Button(topbar, text="Help").grid(row=0, column=2, padx=4, pady=10)
ttk.Button(topbar, text="Quit", command=root.destroy).grid(row=0, column=3, padx=(4, 12), pady=10)

# ---------------- LEFT: a column of buttons, all the same width ----------------
left.columnconfigure(0, weight=1)             # one column, buttons fill its width
tk.Label(left, text="Actions", bg="#d9f7ee", font=("TkDefaultFont", 11, "bold")).grid(
    row=0, column=0, pady=(10, 4))
for i, name in enumerate(["Open", "Save", "Export", "Settings"], start=1):
    ttk.Button(left, text=name).grid(row=i, column=0, sticky="ew", padx=10, pady=4)

# ---------------- MIDDLE: a small form (labels + entries) ----------------
middle.columnconfigure(1, weight=1)
tk.Label(middle, text="Details", bg="#fff3cd", font=("TkDefaultFont", 11, "bold")).grid(
    row=0, column=0, columnspan=2, pady=(10, 4))
for i, name in enumerate(["Name", "City", "Phone"], start=1):
    tk.Label(middle, text=name + ":", bg="#fff3cd").grid(row=i, column=0, sticky="e", padx=(10, 4), pady=5)
    ttk.Entry(middle).grid(row=i, column=1, sticky="ew", padx=(4, 10), pady=5)
size = ttk.Combobox(middle, values=["Small", "Medium", "Large"], state="readonly")
size.current(0)
size.grid(
    row=4, column=1, sticky="ew", padx=(4, 10), pady=5)
tk.Label(middle, text="Size:", bg="#fff3cd").grid(row=4, column=0, sticky="e", padx=(10, 4))

# ---------------- RIGHT: a big list that takes all the room ----------------
right.columnconfigure(0, weight=1)
right.rowconfigure(1, weight=1)               # row 1 (the table) is the one that grows
tk.Label(right, text="Results", bg="#d6ebf5", font=("TkDefaultFont", 11, "bold")).grid(
    row=0, column=0, columnspan=2, pady=(10, 4))
tree = ttk.Treeview(right, columns=("a", "b"), show="headings")
tree.heading("a", text="Name")
tree.heading("b", text="Value")
for n in range(40):
    tree.insert("", "end", values=(f"row {n}", n * 7))
sb = ttk.Scrollbar(right, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=sb.set)
tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
sb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))

root.mainloop()