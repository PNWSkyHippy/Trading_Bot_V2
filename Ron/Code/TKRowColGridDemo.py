from tkinter import *

rootWindow = Tk()
rootWindow.geometry("450x100")
rootWindow.title("Hello World")

# topFrame = Frame(rootWindow)
# topFrame.pack(side=TOP, fill=BOTH)
# bottomFrame = Frame(rootWindow)
# bottomFrame.pack(side=BOTTOM)

label1 = Label(rootWindow, text="| Row-0, Column-0 |")
label2 = Label(rootWindow, text="| Row-0, Column-1 |")
label3 = Label(rootWindow, text="| Row-1, Column-0 |")
label4 = Label(rootWindow, text="| Row-1, Column-1| ")
label5 = Label(rootWindow, text="| Row-3, Column-0| ")
label6 = Label(rootWindow, text="| Row-3, Column-1| ")
label7 = Label(rootWindow, text="| Row-3, Column-2| ")


# label1.grid(row=0) This will also work because default column value is 0
label1.grid(row=0, column=0)
label2.grid(row=0, column=1)
label3.grid(row=1, column=0)
label4.grid(row=1, column=1)
rootWindow.grid_rowconfigure(2, minsize=20)
label5.grid(row=3, column=0)
label6.grid(row=3, column=1)
label7.grid(row=3, column=2)

rootWindow.mainloop()