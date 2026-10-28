# ex03_grid_widgets.py  -  GRID with real widgets: Label, Entry, Combobox, Button,
#                          Listbox, Treeview, Text (+ scrollbars)
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("ex03 - grid with real widgets")
root.geometry("720x520")
root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)

# ---------- Frame 1: a FORM (labels left, inputs right) ----------------
form = tk.LabelFrame(root, text=" form frame ", bg="#fff3cd", padx=8, pady=8)
form.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
form.columnconfigure(1, weight=1)          # the Entry column stretches
form.columnconfigure(3, weight=1)

ttk.Label(form, text="Name:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

ttk.Label(form, text="Type:").grid(row=0, column=2, sticky="e", padx=4, pady=4)
combo = ttk.Combobox(form, values=["Stock", "Crypto", "Futures"], state="readonly")
combo.current(0)
combo.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

ttk.Label(form, text="Notes:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
ttk.Entry(form).grid(row=1, column=1, columnspan=3, sticky="ew", padx=4, pady=4)

# buttons in a row, linear (all row 2, columns 0..)
ttk.Button(form, text="Add").grid(row=2, column=1, sticky="w", padx=4, pady=4)
ttk.Button(form, text="Clear").grid(row=2, column=2, padx=4, pady=4)

# ---------- Frame 2: three data widgets side by side -------------------
data = tk.Frame(root, bg="#d1e7dd")
data.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
data.columnconfigure(0, weight=1)          # listbox
data.columnconfigure(2, weight=3)          # treeview (3x wider)
data.rowconfigure(0, weight=1)

# Listbox + its scrollbar (scrollbar sits in the NEXT column, sticky ns)
lb = tk.Listbox(data, width=14)
for i in range(1, 31):
    lb.insert("end", f"item {i}")
lb_sb = ttk.Scrollbar(data, orient="vertical", command=lb.yview)
lb.configure(yscrollcommand=lb_sb.set)
lb.grid(row=0, column=0, sticky="nsew")
lb_sb.grid(row=0, column=1, sticky="ns")

# Treeview + its scrollbar
tree = ttk.Treeview(data, columns=("sym", "qty", "px"), show="headings", height=8)
for col, w in (("sym", 80), ("qty", 60), ("px", 80)):
    tree.heading(col, text=col.upper())
    tree.column(col, width=w)
for n in range(20):
    tree.insert("", "end", values=(f"SYM{n}", n * 10, f"{100 + n:.2f}"))
tr_sb = ttk.Scrollbar(data, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=tr_sb.set)
tree.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
tr_sb.grid(row=0, column=3, sticky="ns")

# ---------- Frame 3: Text box with scrollbar ---------------------------
logf = tk.Frame(root, bg="#cfe2ff")
logf.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
logf.columnconfigure(0, weight=1)
txt = tk.Text(logf, height=5, wrap="word")
txt.insert("1.0", "A Text widget: type here.\n" * 8)
tx_sb = ttk.Scrollbar(logf, orient="vertical", command=txt.yview)
txt.configure(yscrollcommand=tx_sb.set)
txt.grid(row=0, column=0, sticky="nsew")
tx_sb.grid(row=0, column=1, sticky="ns")

root.mainloop()