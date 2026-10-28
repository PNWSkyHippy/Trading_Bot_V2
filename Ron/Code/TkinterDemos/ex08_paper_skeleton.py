# ex08_paper_skeleton.py  -  from a PAPER SKETCH to code, step 1: just the frames
#
#   +--------------------------------------------+
#   |                  TOP BAR                   |   row 0, spans all 3 columns
#   +----------+-----------------+---------------+
#   |          |                 |               |
#   |  LEFT    |    MIDDLE       |    RIGHT      |   row 1
#   |  (1/4)   |    (1/4)        |    (2/4)      |
#   +----------+-----------------+---------------+
#
# Count the rows and columns on your sketch -> that is your grid.
import tkinter as tk

root = tk.Tk()
root.title("ex08 - paper skeleton")
root.geometry("800x450")

# uniform="x" makes columns share space in EXACT proportion to their weights
# (without it, weight only divides the EXTRA space, so widths can look uneven).
root.columnconfigure(0, weight=1, uniform="cols")   # 1 part  = 1/4
root.columnconfigure(1, weight=1, uniform="cols")   # 1 part  = 1/4
root.columnconfigure(2, weight=2, uniform="cols")   # 2 parts = 2/4
root.rowconfigure(0, weight=0)                      # top bar keeps its height
root.rowconfigure(1, weight=1)                      # panels take the rest

topbar = tk.Frame(root, bg="#ef476f", height=60)
left = tk.Frame(root, bg="#06d6a0")
middle = tk.Frame(root, bg="#ffd166")
right = tk.Frame(root, bg="#118ab2")

topbar.grid(row=0, column=0, columnspan=3, sticky="nsew")
left.grid(row=1, column=0, sticky="nsew")
middle.grid(row=1, column=1, sticky="nsew")
right.grid(row=1, column=2, sticky="nsew")

for frame, name in ((topbar, "TOP BAR"), (left, "LEFT 1/4"), (middle, "MIDDLE 1/4"), (right, "RIGHT 2/4")):
    tk.Label(frame, text=name, bg=frame["bg"], font=("TkDefaultFont", 12, "bold")).place(relx=0.5, rely=0.5, anchor="center")

root.mainloop()