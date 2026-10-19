"""ui_scroll.py - a vertically scrollable frame for tall tool panels (mouse wheel + scrollbar)."""
import tkinter as tk
from tkinter import ttk

# widgets that already use the wheel themselves - leave them alone
OWN_WHEEL = ("Treeview", "Text", "Listbox", "TSpinbox", "Spinbox", "TCombobox", "Canvas")


def scrollable(parent, padding=6):
    """Returns (holder, inner): put holder in the layout, build the widgets in inner."""
    holder = ttk.Frame(parent)
    bg = ttk.Style().lookup("TFrame", "background") or holder.winfo_toplevel().cget("bg")
    sc = tk.Canvas(holder, highlightthickness=0, bd=0, bg=bg)
    vs = ttk.Scrollbar(holder, orient=tk.VERTICAL, command=sc.yview)
    sc.configure(yscrollcommand=vs.set)
    vs.pack(side=tk.RIGHT, fill=tk.Y)
    sc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = ttk.Frame(sc, padding=padding)
    win = sc.create_window(0, 0, window=inner, anchor="nw")

    def inner_changed(_e=None):
        sc.configure(scrollregion=(0, 0, inner.winfo_reqwidth(), inner.winfo_reqheight()))
        if sc.winfo_width() < inner.winfo_reqwidth():          # never narrower than the widgets need
            sc.configure(width=inner.winfo_reqwidth())

    def canvas_changed(e):
        sc.itemconfigure(win, width=max(e.width, inner.winfo_reqwidth()))
        # stretch to fill when there's room, so nothing floats at the top of a tall window
        sc.itemconfigure(win, height=max(e.height, inner.winfo_reqheight()))
        inner_changed()

    inner.bind("<Configure>", inner_changed)
    sc.bind("<Configure>", canvas_changed)

    def wheel(e):
        try:
            w = holder.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):                 # this panel's window was closed
            return None
        if w is None or not str(w).startswith(str(sc)):
            return None
        if w.winfo_class() in OWN_WHEEL and w is not sc:
            return None
        if inner.winfo_reqheight() <= sc.winfo_height():
            return None
        sc.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    holder.bind_all("<MouseWheel>", wheel, add="+")
    return holder, inner
