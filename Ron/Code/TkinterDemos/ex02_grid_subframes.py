# ex02_grid_subframes.py  -  GRID: split the window into frames, then split a frame again
import tkinter as tk

root = tk.Tk()
root.title("ex02 - grid with sub-frames")
root.geometry("640x400")

# ---- Level 1: the window (root) has 2 rows x 2 columns ----------------
root.columnconfigure(0, weight=0, minsize=160)   # sidebar: fixed width
root.columnconfigure(1, weight=1)                # content: takes the rest
root.rowconfigure(0, weight=0)                   # top bar: natural height
root.rowconfigure(1, weight=1)                   # body: takes the rest

top = tk.Frame(root, bg="#ef476f", height=50)
side = tk.Frame(root, bg="#06d6a0")
body = tk.Frame(root, bg="#118ab2")

top.grid(row=0, column=0, columnspan=2, sticky="ew")     # spans both columns
side.grid(row=1, column=0, sticky="ns")                  # full height
body.grid(row=1, column=1, sticky="nsew")                # fills everything left

# ---- Level 2: split the BODY frame into its own grid -------------------
# NOTE: these use  body  as the parent, not root.  body has its own rows/columns.
body.columnconfigure(0, weight=1)
body.columnconfigure(1, weight=1)
body.rowconfigure(0, weight=1)
body.rowconfigure(1, weight=2)

a = tk.Frame(body, bg="#ffd166")
b = tk.Frame(body, bg="#f4a261")
c = tk.Frame(body, bg="#e9c46a")
a.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
b.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
c.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)

# ---- Labels so you can see what is what --------------------------------
tk.Label(top, text="TOP (root row 0, columnspan 2)", bg="#ef476f").pack(pady=14)
tk.Label(side, text="SIDE\n(root row 1, col 0)", bg="#06d6a0").pack(padx=10, pady=10)
tk.Label(a, text="A  (body 0,0)", bg="#ffd166").pack(expand=True)
tk.Label(b, text="B  (body 0,1)", bg="#f4a261").pack(expand=True)
tk.Label(c, text="C  (body row 1, columnspan 2)", bg="#e9c46a").pack(expand=True)

root.mainloop()