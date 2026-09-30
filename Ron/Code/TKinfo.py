from tkinter import *

rootWindow = Tk()

rootWindow.resizable(height=None, width=None)
rootWindow.title("Hello World")

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

character_name_label = Label(
    rootWindow,
    text="Name of the character :",
    font=("arial", 12),
)

character_name_entry = StringVar()
character_name_entry.set("Gru")  # default value
dropdown = OptionMenu(
    rootWindow,
    character_name_entry,
    "Gru",
    "Bob",
    "Kevin",
)

age_confirm_label = Label(
    rootWindow,
    text="Younger than 6 years :",
    font=("arial", 12),
)

age_value_choice = IntVar()
radio_button_yes = Radiobutton(
    rootWindow,
    text="Yes",
    variable=age_value_choice,
    font=("arial", 12),
    value=1,
)
radio_button_no = Radiobutton(
    rootWindow,
    text="No",
    variable=age_value_choice,
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

lets_see_button = Button(
    rootWindow,
    text="Let's me see",
    font=("arial", 12),
)

# Setting the layout

welcome_lable.grid(row=0, columnspan=3)
character_name_label.grid(row=1, sticky=E)
dropdown.grid(row=1, column=1, sticky=E)

age_confirm_label.grid(row=2, sticky=E)
radio_button_yes.grid(row=2, column=1, sticky=W)
radio_button_no.grid(row=2, column=2, sticky=W)

rootWindow.grid_rowconfigure(3, minsize=20)

message_txt.grid(row=5, columnspan=3, sticky=N, rowspan=1)

lets_see_button.grid(row=4, columnspan=3)

rootWindow.mainloop()
rootWindow.mainloop()
