#!/usr/bin/env python3
# encoding: utf-8
import tkinter as tk
from pyautogui import position
from PIL import Image, ImageTk, ImageGrab


pyratio = 1.6
pynew_image = None 

class PyMag(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack()
        self.master.title("pymag - a simple screen magnifier")
        # widget
        self.state_txt = None
        self.state_label = tk.Label(self, text=None)
        self.state_label.pack()
        self.label_img = tk.Label(self, image=None)
        self.label_img.pack()
        # bind event
        self.width = self.master.winfo_width()
        self.mouse_x, self.mouse_y = position()
        self.height = self.master.winfo_height()
        self.bind('<Configure>', self.on_resize)
        # bind to this window only (bind_all would hijack the host app's keys/wheel)
        self.master.bind('<Key>', self.key_pressed)
        # with Windows OS
        self.master.bind('<MouseWheel>', self.mouse_wheel)
        # with Linux OS
        self.master.bind('<Button-4>', self.mouse_wheel)
        self.master.bind('<Button-5>', self.mouse_wheel)
        # main loop 
        self.forever()

    def update_state(self):
        global pyratio
        self.mouse_x, self.mouse_y = position()
        self.state_txt = 'X{} | x: {}, y: {} |  w: {}, h: {}'.format(pyratio,
                self.mouse_x, self.mouse_y, self.width, self.height)
        self.state_label['text'] = self.state_txt

    def on_resize(self, event):
        # print("w: {}, h: {}".format(self.master.winfo_width(),
        # self.master.winfo_height())) 
        self.width = self.master.winfo_width()
        self.height = self.master.winfo_height()
        self.update_state()

    def key_pressed(self, event):
        # print(event.char)
        if event.keysym == "Escape":
            self.master.destroy()

    def mouse_wheel(self, event):
        global pyratio
        # respond to Linux or Windows wheel event
        if event.num == 5 or event.delta == -120:
            pyratio -= 0.1
        if event.num == 4 or event.delta == 120:
            pyratio += 0.1
        pyratio = round(pyratio, 2)
        if pyratio < 1:
            pyratio = 1.0
    def forever(self):
        global pynew_image, pyratio
        self.update_state()
        ss_region = (self.mouse_x, self.mouse_y, self.mouse_x +
                self.width/pyratio, self.mouse_y + self.height/pyratio) 
        ss_img = ImageGrab.grab(ss_region)
        resized_image = ss_img.resize((round(self.width*pyratio),
            round(self.height*pyratio)), Image.Resampling.LANCZOS)
        pynew_image = ImageTk.PhotoImage(resized_image, master=self.master)
        self.label_img['image'] = pynew_image
        self.master.after(round(pyratio*25), self.forever)

def pyrun(parent=None):
    """Standalone: makes its own root and runs the loop.
    From another Tk app: pass that app's root/window as parent and the magnifier
    opens as a Toplevel on the already-running loop (never a second Tk())."""
    if parent is None:
        root = tk.Tk()
    else:
        root = tk.Toplevel(parent)
    root.geometry("400x300") # width x height
    # create object
    app = PyMag(root)
    if parent is None:
        app.mainloop()
    return app

if __name__ == "__main__":
    pyrun() 