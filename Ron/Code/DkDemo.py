from tkinter import *


def show_info():
    message_txt.delete(0.0, "end")
    selected_calc = calc_type_entry.get()
    persist_restriction = persist_value_choice.get()

    for label in rootWindow.grid_slaves():
        if int(label.grid_info()["row"]) == 6:
            label.grid_forget()

    if persist_restriction == 1:
        if selected_calc == "Standard":
            gru_photo_label.grid(row=6, columnspan=3)
        elif selected_calc == "Temp":
            bob_photo_label.grid(row=6, columnspan=3)
        elif selected_calc == "Amortization":
            kevin_photo_label.grid(row=6, columnspan=3)
    else:
        message_txt.insert(0.0, "You are not authorized!")
        restricted_photo_label.grid(row=6, columnspan=3)


rootWindow = Tk()

rootWindow.resizable(height=None, width=None)
rootWindow.title("Calculator")

# topFrame = Frame(rootWindow)
# topFrame.pack(side=TOP, fill=BOTH)
# bottomFrame = Frame(rootWindow)
# bottomFrame.pack(side=BOTTOM)

welcome_lable = Label(
    rootWindow,
    text="Welcome to Tkinter Minion",
    fg="gray",
    font=("arial", 16, "bold"),
)

calc_type_entry = StringVar()
calc_type_entry.set("Standard")  # default value

calc_type_label = Label(
    rootWindow,
    text="Calculator Type :",
    font=("arial", 12),
)
dropdown = OptionMenu(
    rootWindow,
    calc_type_entry,
    "Standard",
    "Temp",
    "Amortization",
)
persist_confirm_label = Label(
    rootWindow,
    text="Persistant Calclations :",
    font=("arial", 12),
)

persist_value_choice = IntVar()
radio_button_yes = Radiobutton(
    rootWindow,
    text="Yes",
    variable=persist_value_choice,
    font=("arial", 12),
    value=1,
)
radio_button_yes.flash
radio_button_no = Radiobutton(
    rootWindow,
    text="No",
    variable=persist_value_choice,
    font=("arial", 12),
    value=2,
)

message_txt = Text(
    rootWindow,
    width=16,
    height=1,
    wrap=WORD,
    fg="red",
    font=("arial", 20, "bold"),
)

restricted_imag = PhotoImage(file="no_minion.png")
restricted_photo_label = Label(rootWindow, image=restricted_imag)

gru_imag = PhotoImage(file="gru.png")
gru_photo_label = Label(rootWindow, image=gru_imag)

bob_imag = PhotoImage(file="bob.png")
bob_photo_label = Label(rootWindow, image=bob_imag)

kevin_imag = PhotoImage(file="kevin.png")
kevin_photo_label = Label(rootWindow, image=kevin_imag)

lets_see_button = Button(
    rootWindow,
    text="Let me see",
    font=("arial", 12),
    command=lambda: show_info(),
)

# Setting the layout

welcome_lable.grid(row=0, columnspan=3)
calc_type_label.grid(row=1, sticky=E)
persist_confirm_label.grid(row=2, sticky=E)
dropdown.grid(row=1, column=1, sticky=E)

radio_button_yes.grid(row=2, column=1, sticky=W)
radio_button_no.grid(row=2, column=2, sticky=W)

rootWindow.grid_rowconfigure(3, minsize=20)

message_txt.grid(row=5, columnspan=3, sticky=N, rowspan=1)

lets_see_button.grid(row=4, columnspan=3)

# There are some issues with tkinter running on OSX

# clickHereButton = Button(bottomFrame, text="Click to see a Minion", fg="blue",
#                          highlightbackground="#3E4149", font=("arial", 12), relief=RAISED)

# with "from tkinter import ttk" you can use below lines
# button = ttk.Button(bottomFrame, text='Click to see a Minion!', style='green/black.TButton')
# button.pack()

rootWindow.mainloop()
