# ex07_mixing_safely.py  -  the RIGHT way: each PARENT uses only ONE manager.
#   root          -> uses pack   (top bar, then the rest)
#   toolbar frame -> uses pack   (buttons in a row)
#   form frame    -> uses grid   (labels + entries lined up)
# A different parent may use a different manager. Only one manager PER PARENT.
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("ex07 - mixing safely")
root.geometry("520x300")

# ---- root: PACK only ----
toolbar = tk.Frame(root, bg="#ffd166")
toolbar.pack(side="top", fill="x")
form = tk.Frame(root, bg="#d1e7dd")
form.pack(side="top", fill="both", expand=True)

# ---- toolbar: PACK only (children of toolbar) ----
for name in ("New", "Open", "Save"):
    ttk.Button(toolbar, text=name).pack(side="left", padx=4, pady=4)
ttk.Button(toolbar, text="Quit", command=root.destroy).pack(side="right", padx=4, pady=4)

# ---- form: GRID only (children of form) ----
form.columnconfigure(1, weight=1)
rows = ["First name", "Last name", "Email"]
for r, label in enumerate(rows):
    tk.Label(form, text=label + ":", bg="#d1e7dd").grid(row=r, column=0, sticky="e", padx=8, pady=6)
    ttk.Entry(form).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

# Rule of thumb: when you write  X.grid(...)  or  X.pack(...)  look at the FIRST
# word inside the brackets of X = Widget(PARENT, ...).  Every child of the same
# PARENT must use the same method.

root.mainloop()