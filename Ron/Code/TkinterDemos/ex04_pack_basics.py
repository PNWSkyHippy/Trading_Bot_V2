# ex04_pack_basics.py  -  PACK: side, fill, expand, anchor, padx, pady
import tkinter as tk

root = tk.Tk()
root.title("ex04 - pack basics")
root.geometry("560x360")


def box(parent, text, color):
    return tk.Label(parent, text=text, bg=color, relief="solid", bd=1)


# pack works like stacking: each widget grabs a SLICE off the free space.
# Order matters!  First packed = first slice.

box(root, "1) side=top, fill=x   (stretches left-right)", "#ef476f").pack(side="top", fill="x")
box(root, "2) side=bottom, fill=x", "#ffd166").pack(side="bottom", fill="x")
box(root, "3) side=left, fill=y\n(stretches up-down)", "#06d6a0").pack(side="left", fill="y")

# expand=True : "give me any leftover space".  fill says how to use it.
box(root, "4) side=left, fill=both, expand=True\n(grabs ALL leftover space)", "#118ab2").pack(
    side="left", fill="both", expand=True, padx=10, pady=10)   # padx/pady = space OUTSIDE

# anchor : where the widget sits inside a slice that is bigger than it needs.
box(root, "5) side=top, anchor=ne", "#f4a261").pack(side="top", anchor="ne")
box(root, "6) side=top, anchor=w", "#e9c46a").pack(side="top", anchor="w", ipadx=20, ipady=8)  # ipad = padding INSIDE

root.mainloop()