# ex06_mixing_error.py  -  WHAT GOES WRONG when you mix grid and pack in ONE parent
import tkinter as tk

root = tk.Tk()
root.title("ex06 - mixing grid and pack (the mistake)")
root.geometry("520x220")

first = tk.Label(root, text="I used GRID in root", bg="#06d6a0")
first.grid(row=0, column=0)

second = tk.Label(root, text="I tried PACK in root", bg="#ef476f")
msg = ""
try:
    second.pack()          # <-- same parent (root) already uses grid -> ERROR
except tk.TclError as err:
    msg = str(err)

tk.Label(root, text="Python said:", font=("TkDefaultFont", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(20, 0))
tk.Label(root, text=msg, fg="#b00020", wraplength=480, justify="left").grid(row=2, column=0, sticky="w")

# (If tkinter did NOT raise an error you could get an endless "freeze":
#  grid and pack keep resizing the window to please each other. Never mix.)

root.mainloop()