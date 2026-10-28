# ex11_chopped.py  -  TOO MANY CONTROLS: what gets chopped, and the fix
#   LEFT  window area: a fixed-size frame (propagate OFF) with 12 buttons -> bottom ones CUT OFF.
#   RIGHT window area: same 12 buttons, but in a scrollable Canvas -> scrollbar appears.
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("ex11 - chopped content")
root.geometry("640x300")
root.columnconfigure((0, 1), weight=1, uniform="c")
root.rowconfigure(1, weight=1)

tk.Label(root, text="CHOPPED  (fixed frame, 12 buttons)", fg="#b00020").grid(row=0, column=0, pady=4)
tk.Label(root, text="FIXED with a scrollable canvas", fg="#007a3d").grid(row=0, column=1, pady=4)

# ---------- LEFT: the chopped one ----------
chopped = tk.Frame(root, bg="#ef476f", width=280, height=200)
chopped.grid(row=1, column=0, sticky="n", padx=10, pady=4)
chopped.grid_propagate(False)             # frame stays 280x200 no matter what's inside
for i in range(12):
    ttk.Button(chopped, text=f"Button {i + 1}").grid(row=i, column=0, padx=6, pady=2)
# Buttons that don't fit are simply NOT SHOWN. No error, no warning.

# ---------- RIGHT: the scrollable one ----------
holder = tk.Frame(root)
holder.grid(row=1, column=1, sticky="nsew", padx=10, pady=4)
holder.columnconfigure(0, weight=1)
holder.rowconfigure(0, weight=1)

canvas = tk.Canvas(holder, bg="#d1e7dd", highlightthickness=0)
bar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=bar.set)
canvas.grid(row=0, column=0, sticky="nsew")
bar.grid(row=0, column=1, sticky="ns")

inner = tk.Frame(canvas, bg="#d1e7dd")                   # put your widgets in THIS frame
canvas.create_window((0, 0), window=inner, anchor="nw")
for i in range(12):
    ttk.Button(inner, text=f"Button {i + 1}").grid(row=i, column=0, padx=6, pady=2)
# tell the canvas how big the inner frame really is, so it knows how far to scroll
inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

root.mainloop()