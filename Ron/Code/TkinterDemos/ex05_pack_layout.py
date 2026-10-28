# ex05_pack_layout.py  -  the SAME layout as ex02, built with PACK
#   top bar across the window, a sidebar on the left, a body filling the rest,
#   and the body split into 2 frames side by side with one underneath.
import tkinter as tk

root = tk.Tk()
root.title("ex05 - pack layout")
root.geometry("640x400")

# Level 1  (order = top first, then left, then the body LAST with expand)
top = tk.Frame(root, bg="#ef476f", height=50)
top.pack(side="top", fill="x")

side = tk.Frame(root, bg="#06d6a0", width=160)
side.pack(side="left", fill="y")

body = tk.Frame(root, bg="#118ab2")
body.pack(side="left", fill="both", expand=True)

# Level 2 inside body: a "row" frame holding A and B, then C underneath
row = tk.Frame(body, bg="#118ab2")
row.pack(side="top", fill="both", expand=True)

a = tk.Frame(row, bg="#ffd166")
b = tk.Frame(row, bg="#f4a261")
a.pack(side="left", fill="both", expand=True, padx=6, pady=6)
b.pack(side="left", fill="both", expand=True, padx=6, pady=6)

c = tk.Frame(body, bg="#e9c46a", height=120)
c.pack(side="top", fill="both", expand=True, padx=6, pady=6)

tk.Label(top, text="TOP  (pack side=top, fill=x)", bg="#ef476f").pack(pady=14)
tk.Label(side, text="SIDE\n(side=left, fill=y)", bg="#06d6a0").pack(padx=10, pady=10)
tk.Label(a, text="A", bg="#ffd166").pack(expand=True)
tk.Label(b, text="B", bg="#f4a261").pack(expand=True)
tk.Label(c, text="C  (under A and B)", bg="#e9c46a").pack(expand=True)

# A pack gotcha: the side panel has width=160 but its Label is small.
# A Frame SHRINKS to fit its children, so width=160 would be ignored!
# Fix:  side.pack_propagate(False)   (more on this in ex10)
side.pack_propagate(False)

root.mainloop()