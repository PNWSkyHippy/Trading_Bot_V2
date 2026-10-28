"""Provide a Tk calculator with standard, scientific and unit converter modes."""

import base64
import collections as col
import math
import re
import sys
import tkinter as tk
from tkinter import PhotoImage, ttk
from local_functions import run_magnifyer
from calc_inc import *
from quick_tk import QuickApp, ToolView

DEBUG = False  # Set to True to enable debug output to stderr


class TkCalc(ToolView):
    """A TK Based Calculator"""

    def __init__(self, parent, **kwargs):
        """Initialize the calculator view and its mode flags.

        Args:
            parent (tk.Widget): The widget that contains this view.
            **kwargs: Extra options passed to ``ToolView``.
        """
        super().__init__(parent, **kwargs)
        self.title = "TK Calculator"
        self.scientific_extended = False
        self.standard_mode = True
        self.angle_mode = "radians"

    def build_ui(self):
        """Build the mode selector, shared display and every mode frame.

        Raises:
            FileNotFoundError: If ``buttonicon.gif`` or ``buttonicon2.gif``
                is missing from the working directory.
        """
        with open("buttonicon.gif", "rb") as image:
            image_string = base64.encodebytes(image.read())
        self.icon = PhotoImage(data=image_string)
        with open("buttonicon2.gif", "rb") as image2:
            image_string2 = base64.encodebytes(image2.read())
        self.icon2 = PhotoImage(data=image_string2)
        # The view is a two-row layout: the shared toolbar stays at the top
        # and the active mode fills the remaining space below it.
        self.display_var = tk.StringVar(value="0")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        # -------------------------------------------------------------
        # 1. TOP BAR: Mode Selector (Dropdown or Segmented Pills)
        # -------------------------------------------------------------
        top_bar = ttk.Frame(self, padding=8, relief=tk.RAISED)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.columnconfigure(0, weight=0)
        top_bar.columnconfigure(1, weight=1)
        top_bar.columnconfigure(2, weight=1)


        self._mag = None
        self.bind_all("<Control-Shift-M>", self.on_mag)
        self.bind_all("<Control-Shift-m>", self.on_mag)

        self.mode_var = tk.StringVar(value="Standard")
        mode_combo = ttk.Combobox(
            top_bar,
            textvariable=self.mode_var,
            values=["Standard", "Scientific", "Unit Converter"],
            state="readonly",
            width=18,
        )
        mode_combo.grid(row=0, column=0, sticky="nw")
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_switched)

        # -------------------------------------------------------------
        # 2. SHARED DISPLAY SCREEN (Used across all modes)
        # -------------------------------------------------------------
        # Read only text box to display the running calculations
        self.entry_box = tk.Text(
            top_bar,
            height=1,
            width=20,
            font=("Segoe UI", 16),
            undo=True,
            wrap="none",
        )
        self.entry_box.grid(
            row=0,
            column=2,
            columnspan=1,
            sticky="ew",
            padx=10,
            pady=(4, 2),
        )
        # Keep this box editable.  Tkinter now gives us arrows, selection,
        # backspace, delete, copy, cut, paste, and undo for free.
        self.entry_box.bind("<Return>", self._on_formula_enter)
        self.entry_box.bind("<KP_Enter>", self._on_formula_enter)

        # Read only entry box to display the total of the calculations
        self.result_box = ttk.Entry(
            top_bar, textvariable=self.display_var, width=30, state="readonly"
        )
        self.result_box.grid(row=1, column=2, sticky="ew", padx=10, pady=(2, 4))
        self.result_box.config(state="readonly", foreground="lightblue")

        # -------------------------------------------------------------
        # 3. SWAP CONTAINER (Houses all mode frames in the same cell)
        # -------------------------------------------------------------
        self.container = ttk.Frame(self, padding=8, relief=tk.RAISED)
        self.container.grid(row=1, column=0, sticky="nsew")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        # One memory queue shared by every calculator mode.  Each mode gets
        # its own display widget, kept in sync by the memory methods below.
        self.mem_q = col.deque(maxlen=25)
        self.recall_pending = False
        self.memory_boxes = []

        # Build the 3 distinct mode frames
        self.mode_frames = {}
        self.mode_frames["Standard"] = self._build_standard_mode()
        self.mode_frames["Scientific"] = self._build_scientific_mode()
        self.mode_frames["Scientific Extended"] = self._build_scientific_mode_ext()
        self.mode_frames["Unit Converter"] = self._build_converter_mode()

        # Show Standard mode by default
        self.show_mode("Standard")
        self.setup_menus()


    def setup_menus(self):
        """Add the File menu with its Exit item and About submenu."""
        # 1. FILE MENU (Fluent Chained Style)
       # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_item("Exit Application", self.app.root.quit, shortcut="Alt+F4")
 
        # Cascading Submenu: File > Export > ...
        export_sub = file_menu.add_submenu("About")
        export_sub.add_item(
            "TKCalc 09/2026", lambda: self.log_action("")
        )
        export_sub.add_item(
            "Coded By: Ron Hensley", lambda: self.log_action("")
        )
        export_sub.add_item(
            "ronkhensley@gmail.com", lambda: self.log_action("")
        )

    def on_mag(self, event=None):
        # already open? close it (the key toggles) instead of stacking copies
        if self._mag is not None and self._mag.master.winfo_exists():
            self._mag.master.destroy()
            self._mag = None
            return "break"
        self._mag = run_magnifyer(self.app.root)
        return "break"

    def log_action(self, msg):
        """Record a menu action. Currently a no-op.

        Args:
            msg (str): Description of the action.
        """
        return msg

    
    def show_mode(self, mode_name: str):
        """Raise the frame for a calculator mode and update the status bar.

        Args:
            mode_name (str): Key into ``mode_frames``. Unknown names are
                ignored.
        """
        target_frame = self.mode_frames.get(mode_name)
        if target_frame:
            target_frame.tkraise()  # Brings target to front without destroying anything!
            self.set_status(f"Switched to {mode_name} mode")

    def on_mode_switched(self, event=None):
        """Handle a new selection in the mode dropdown.

        Args:
            event (tk.Event | None): The ``<<ComboboxSelected>>`` event, if any.
        """
        mode = self.mode_var.get()
        if mode == "Scientific Extended":
            self.scientific_extended = True
            self.standard_mode = False
        elif mode == "Scientific":
            self.scientific_extended = False
            self.standard_mode = False
        elif mode == "Standard":
            self.standard_mode = True
            self.scientific_extended = False
        self.show_mode(mode)

    def _build_standard_mode(self):
        """Build the standard calculator frame.

        Returns:
            ttk.LabelFrame: The populated frame, placed in ``container``.
        """
        frame = ttk.LabelFrame(
            self.container, text=" Standard Mode ", padding=8, relief=tk.RAISED
        )
        # Keep the mode panel full width, but let its bottom edge follow the
        # board instead of stretching to the bottom of the window.
        frame.grid(row=0, column=0, sticky="nsew")

        # Never used litst of al the buttons in the calc
        self.buttons = {}  # Also unused dictionay f buttuns in the calc
        # 1. Main Window Split: Left (Board) & Right (Actions)
        frame.columnconfigure(0, weight=0, minsize=210)  # Action sidebar
        frame.columnconfigure(1, weight=1, minsize=460)  # Calculator board area

        frame.rowconfigure(0, weight=0)  # Action bar
        frame.rowconfigure(1, weight=1, minsize=320)  # Calculator board area
        frame.rowconfigure(2, weight=0)
        frame.rowconfigure(3, weight=0)
        self.btn_layout = [
            ["()", "0", ".", "="],
            ["1", "2", "3", "*"],
            ["4", "5", "6", "-"],
            ["7", "8", "9", "+"],
            ["C", "Bk", "%", "/"],
        ]
        # set up left hand side window add a frame for controls
        self.side_box = self.add_form("Calc Options", parent=frame)
        self.side_box.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nws",
            padx=0,
            pady=10,
        )

        self.options_form = ttk.LabelFrame(
            self.side_box, text="Calc Options", padding=10, relief=tk.RAISED
        )
        self.options_form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        # Diplay contents of memory stack
        self.options_button = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Memory",
            command=self.on_memory,
        )
        self.options_button.grid(row=0, column=0, sticky="nws", padx=10, pady=10)

        # Clear the memory stack
        self.options_button_clr = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Clear Memory",
            command=self.on_clear_memory,
        )
        self.options_button_clr.grid(row=1, column=0, sticky="nws", padx=10, pady=10)

        # Recover an item from the stack back to the working window
        self.options_button_rec = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Recall Memory",
            command=self.on_memory_rec,
        )
        self.options_button_rec.grid(row=2, column=0, sticky="nws", padx=10, pady=10)

        # Box to display the memory statck in
        memory_box = tk.Text(
            self.options_form,
            height=5,
            width=20,
            font=("Segoe UI", 24, "bold"),
        )
        memory_box.grid(row=3, column=0, sticky="nswe", padx=10, pady=10)
        self.memory_boxes.append(memory_box)

        # Setip top panel to display total and running calculations, add a frame
        self.top_form = ttk.LabelFrame(frame, text="", padding=20, relief=tk.RAISED)
        self.top_form.grid(row=0, column=1, sticky="new", padx=20, pady=8)
        self.top_form.columnconfigure(1, weight=1)

        # Setup 4 * 5 grid for calculator bvuttons to live in a frame
        board_box = ttk.LabelFrame(
            frame, text=" TKCalculator ", padding=12, relief=tk.RAISED
        )
        # Expand across the available width, but keep the board from filling
        # the entire height of the mode frame.
        board_box.grid(row=1, column=1, sticky="nsew", padx=20, pady=10)

        # Make the 4*5 grid cells stretch equally (5th row setup later at ottom)
        for i in range(3):
            board_box.columnconfigure(i, weight=1)
            board_box.rowconfigure(i, weight=1)
            board_box.rowconfigure(3, weight=1)
        for i in range(1, 5):
            board_box.columnconfigure(i, weight=1)
            board_box.rowconfigure(4, weight=1)
        board_box.columnconfigure(0, weight=0)

        # Map the button labels
        top_list = ["C", "Bk", "  %  ", "  /   "]
        side_list = ["* ", "- ", "+ "]
        bottom_list = ["() ", "0", ". ", "= "]
        # Create top row buttons all operators
        j = 4
        for c in [4, 3, 2, 1]:
            btn = tk.Button(
                board_box,
                image=self.icon,
                compound=tk.CENTER,
                text=top_list[c - 1],
                font=("Segoe UI", 24, "bold"),
                bg="#3825CB",
                fg="#89b4fa",
                command=lambda ch=top_list[c - 1].strip(): self.on_cell_click(ch),
            )
            btn.grid(row=0, column=j, sticky="nwse", padx=4, pady=4)
            self.buttons[(0, j)] = btn
            # Keep the lookup key consistent with the row passed to the
            # callback.  These are the bottom calculator row (row 4), not
            # row 1; using row 1 overwrites other buttons and causes a
            # KeyError when the button is pressed.
            self.buttons[(4, 5 - c)] = btn
            j -= 1
        i = 1
        for r in [3, 2, 1]:
            j = 3
            k = 1
            for c in [2, 1, 0]:
                btn = tk.Button(
                    board_box,
                    image=self.icon,
                    compound=tk.CENTER,
                    text=str((r * 3) + c + 1 - 3),
                    font=("Segoe UI", 24, "bold"),
                    bg="#3825CB",
                    fg="#89b4fa",
                    # Number buttons
                    command=lambda text=str((r * 3) + c + 1 - 3): self.on_cell_click(
                        text
                    ),
                )
                btn.grid(row=i, column=j, sticky="nwse", padx=4, pady=4)
                self.buttons[(i, j)] = btn
                btn = tk.Button(
                    board_box,
                    image=self.icon,
                    compound=tk.CENTER,
                    text=side_list[c],
                    font=("Segoe UI", 24, "bold"),
                    bg="#3825CB",
                    fg="#89b4fa",
                    # Operator buttons
                    command=lambda text=side_list[c].strip(): self.on_cell_click(text),
                )
                btn.grid(row=k, column=4, sticky="nwse", padx=4, pady=4)
                self.buttons[(k, 4)] = btn  # C + 1
                j -= 1
                k += 1
            i += 1
        j = 4
        for c in [4, 3, 2, 1]:
            btn = tk.Button(
                board_box,
                image=self.icon,
                compound=tk.CENTER,
                text=bottom_list[c - 1],
                font=("Segoe UI", 24, "bold"),
                bg="#3825CB",
                fg="#89b4fa",  # Bottom calculator buttons
                command=lambda text=bottom_list[c - 1].strip(): self.on_cell_click(
                    text
                ),
            )
            btn.grid(row=4, column=c, sticky="nwse", padx=4, pady=4)
            self.buttons[(0, c)] = btn
            j -= 1
        i = 1
        return frame

    def _build_scientific_mode(self):
        """Build the scientific calculator frame.

        Returns:
            ttk.LabelFrame: The populated frame, placed in ``container``.
        """
        scientific_buttons1 = [
            ("⇄", "Rad", "\u221a", "\u007cx\u007c"),
            ("sin", "cos", "tan", "\u03c0"),
            ("ln", "log", "1/x", "e"),
            ("e\u02e3", "x\u00b2", "x\u02b8", "+/-"),
            ("C", "Bk", "%", "/"),
            ("7", "8", "9", "+"),
            ("4", "5", "6", "-"),
            ("1", "2", "3", "*"),
            ("()", "0", ".", "="),
        ]

        frame = ttk.LabelFrame(
            self.container, text=" Scientific Extensions", padding=8, relief=tk.RAISED
        )
        # Keep the mode panel full width, but let its bottom edge follow the
        # board instead of stretching to the bottom of the window.
        frame.grid(row=0, column=0, sticky="nsew")

        # Never used litst of al the buttons in the calc
        self.buttons = {}  # Also unused dictionay f buttuns in the calc
        # 1. Main Window Split: Left (Board) & Right (Actions)
        frame.columnconfigure(0, weight=0, minsize=210)  # Action sidebar
        frame.columnconfigure(1, weight=1, minsize=460)  # Calculator board area

        frame.rowconfigure(1, weight=1)  # Calculator board area
        frame.rowconfigure(2, weight=0)
        frame.rowconfigure(3, weight=0)
        frame.rowconfigure(4, weight=0)
        frame.rowconfigure(5, weight=0)
        frame.rowconfigure(6, weight=0)
        frame.rowconfigure(7, weight=0)

        self.btn_layout = [
            ["()", "0", ".", "="],
            ["1", "2", "3", "*"],
            ["4", "5", "6", "-"],
            ["7", "8", "9", "+"],
            ["C", "Bk", "%", "/"],
        ]
        # set up left hand side window add a frame for controls
        self.side_box = self.add_form("Calc Options", parent=frame)
        self.side_box.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nws",
            padx=0,
            pady=10,
        )

        self.options_form = ttk.LabelFrame(
            self.side_box, text="Calc Options", padding=10, relief=tk.RAISED
        )
        self.options_form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        # Diplay contents of memory stack
        self.options_button = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Memory",
            command=self.on_memory,
        )
        self.options_button.grid(row=0, column=0, sticky="nws", padx=10, pady=10)

        # Clear the memory stack
        self.options_button_clr = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Clear Memory",
            command=self.on_clear_memory,
        )
        self.options_button_clr.grid(row=1, column=0, sticky="nws", padx=10, pady=10)

        # Recover an item from the stack back to the working window
        self.options_button_rec = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Recall Memory",
            command=self.on_memory_rec,
        )
        self.options_button_rec.grid(row=2, column=0, sticky="nws", padx=10, pady=10)

        # Box to display the memory statck in
        memory_box = tk.Text(
            self.options_form,
            height=5,
            width=20,
            font=("Segoe UI", 24, "bold"),
        )
        memory_box.grid(row=3, column=0, sticky="nswe", padx=10, pady=10)
        self.memory_boxes.append(memory_box)

        # Setip top panel to display total and running calculations, add a frame
        self.top_form = ttk.LabelFrame(frame, text="", padding=20, relief=tk.RAISED)
        self.top_form.grid(row=0, column=1, sticky="new", padx=20, pady=8)
        self.top_form.columnconfigure(1, weight=1)

        # Setup 4 * 5 grid for calculator bvuttons to live in a frame
        board_box = ttk.LabelFrame(
            frame, text=" TKCalculator ", padding=12, relief=tk.RAISED
        )
        # Expand across the available width, but keep the board from filling
        # the entire height of the mode frame.
        board_box.grid(row=1, column=1, sticky="nsew", padx=20, pady=10)

        for column in range(4):
            board_box.columnconfigure(column, weight=1)
        for row in range(len(scientific_buttons1)):
            board_box.rowconfigure(row, weight=1)

        for r, row in enumerate(scientific_buttons1):
            for c, char in enumerate(row):
                board_box.columnconfigure(c, weight=1)
                is_sci = r < 2
                btn = tk.Button(
                    board_box,
                    image=self.icon,
                    compound=tk.CENTER,
                    text=char,
                    font=("Segoe UI", 24, "bold"),
                    bg="#1e1e2e",
                    fg="#89b4fa",
                    command=lambda ch=char: self.on_cell_click(ch),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)

        return frame

    def _build_scientific_mode_ext(self):
        """Build the extended scientific frame with inverse and hyperbolic keys.

        Returns:
            ttk.LabelFrame: The populated frame, placed in ``container``.
        """
        scientific_buttons2 = [
            ("⇄", "Rad", "\u221b", "2\u02e3"),  # 2 to x
            (
                "sin\u207b\u00b9",
                "cos\u207b\u00b9",
                "tan\u207b\u00b9",
                "x\u00b3",
            ),  # X to 3
            ("sinh", "cosh", "tanh", "x!"),
            ("sinh\u207b\u00b9", "cosh\u207b\u00b9", "tanh\u207b\u00b9", "+/-"),
            ("C", "Bk", "%", "/"),
            ("7", "8", "9", "+"),
            ("4", "5", "6", "-"),
            ("1", "2", "3", "*"),
            ("()", "0", ".", "="),
        ]

        frame = ttk.LabelFrame(
            self.container,
            text=" Scientific Extensions Extended",
            padding=8,
            relief=tk.RAISED,
        )
        # Keep the mode panel full width, but let its bottom edge follow the
        # board instead of stretching to the bottom of the window.
        frame.grid(row=0, column=0, sticky="nsew")

        # Never used litst of al the buttons in the calc
        self.buttons = {}  # Also unused dictionay f buttuns in the calc
        # 1. Main Window Split: Left (Board) & Right (Actions)
        frame.columnconfigure(0, weight=0, minsize=210)  # Action sidebar
        frame.columnconfigure(1, weight=1, minsize=460)  # Calculator board area

        frame.rowconfigure(1, weight=1)  # Calculator board area

        self.btn_layout = [
            ["()", "0", ".", "="],
            ["1", "2", "3", "*"],
            ["4", "5", "6", "-"],
            ["7", "8", "9", "+"],
            ["C", "Bk", "%", "/"],
        ]
        # set up left hand side window add a frame for controls
        self.side_box = self.add_form("Calc Options", parent=frame)
        self.side_box.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nws",
            padx=0,
            pady=10,
        )

        self.options_form = ttk.LabelFrame(
            self.side_box, text="Calc Options", padding=10, relief=tk.RAISED
        )
        self.options_form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        # Diplay contents of memory stack
        self.options_button = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Memory",
            command=self.on_memory,
        )
        self.options_button.grid(row=0, column=0, sticky="nws", padx=10, pady=10)

        # Clear the memory stack
        self.options_button_clr = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Clear Memory",
            command=self.on_clear_memory,
        )
        self.options_button_clr.grid(row=1, column=0, sticky="nws", padx=10, pady=10)

        # Recover an item from the stack back to the working window
        self.options_button_rec = ttk.Button(
            self.options_form,
            image=self.icon,
            compound=tk.CENTER,
            text="Recall Memory",
            command=self.on_memory_rec,
        )
        self.options_button_rec.grid(row=2, column=0, sticky="nws", padx=10, pady=10)

        # Box to display the memory statck in
        memory_box = tk.Text(
            self.options_form,
            height=5,
            width=20,
            font=("Segoe UI", 24, "bold"),
        )
        memory_box.grid(row=3, column=0, sticky="nswe", padx=10, pady=10)
        self.memory_boxes.append(memory_box)

        # Setip top panel to display total and running calculations, add a frame
        self.top_form = ttk.LabelFrame(frame, text="", padding=20, relief=tk.RAISED)
        self.top_form.grid(row=0, column=1, sticky="new", padx=20, pady=8)
        self.top_form.columnconfigure(1, weight=1)

        # Setup 4 * 5 grid for calculator bvuttons to live in a frame
        board_box = ttk.LabelFrame(
            frame, text=" TKCalculator ", padding=12, relief=tk.RAISED
        )
        # Expand across the available width, but keep the board from filling
        # the entire height of the mode frame.
        board_box.grid(row=1, column=1, sticky="nsew", padx=20, pady=10)

        for column in range(4):
            board_box.columnconfigure(column, weight=1)
        for row in range(len(scientific_buttons2)):
            board_box.rowconfigure(row, weight=1)

        for r, row in enumerate(scientific_buttons2):
            for c, char in enumerate(row):
                board_box.columnconfigure(c, weight=1)
                is_sci = r < 2
                btn = tk.Button(
                    board_box,
                    image=self.icon,
                    compound=tk.CENTER,
                    text=char,
                    font=("Segoe UI", 24, "bold"),
                    bg="#1e1e2e",
                    fg="#89b4fa",
                    command=lambda ch=char: self.on_cell_click(ch),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)

        return frame

    def _build_converter_mode(self) -> ttk.Frame:
        """Build the unit converter frame.

        Returns:
            ttk.Frame: The populated frame, placed in ``container``.
        """
        frame = ttk.LabelFrame(
            self.container,
            text=" Unit Converter & Calculations ",
            padding=10,
            relief=tk.GROOVE,
        )
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        # 1. Top Category Selector
        self.top_cat_form = self.add_form("Converter Category", parent=frame)
        self.top_cat_form.pack(fill="x", pady=0)
        self.top_cat_form.add_dropdown(
            "category",
            "Conversion Type",
            [
                "Temperature (°C ⇄ °F)",
                "Length (m ⇄ ft)",
                "Area (sq ft ⇄ sq m)",
                "Volume (US Gal ⇄ Lit)",
                "Mass (lbs ⇄ Kg)",
                "Data (Kb ⇄ Mb)",
                "Speed (Met/s ⇄ In/s)",
                "time (seconds ⇄ hours)",
                "tip (% / Tot People ⇄ Tip Each)",
                "compinter (Principle, Rate, time ⇄ Total)",
            ],
            default="Temperature (°C ⇄ °F)",
            on_change=self.on_category_changed,
        )

        # 2. Dynamic Container for inputs
        self.dynamic_inputs_box = ttk.Frame(frame)
        self.dynamic_inputs_box.pack(fill="x", expand=True)
        # 3. Convert Button Action Bar
        self.action_form = self.add_form("Actions", parent=frame)
        self.action_form.pack()
        conv_btn = self.action_form.add_button(
            "Convert 🔄",
            image=self.icon2,
            compound=tk.CENTER,
            callback=self.on_run_conversion,
            variant="primary",
        )
        conv_btn.config(image=self.icon2, compound=tk.CENTER)
        #       conv_btn.config(background="#7101F9", foreground="#7101F9")
        # Initialize with default category
        self.on_category_changed("Temperature (°C ⇄ °F)")
        return frame

    def on_category_changed(self, cat: str):
        """Builds the specific input controls when a user selects a category."""
        for child in self.dynamic_inputs_box.winfo_children():
            child.destroy()

        self.sub_form = self.add_form("Inputs", parent=self.dynamic_inputs_box)
        self.sub_form.pack(fill="both", expand=True)

        if "Temperature" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                ["Fahrenheit", "Celsius"],
                default="Fahrenheit",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["Fahrenheit", "Celsius"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                ["Celsius", "Fahrenheit"],
                default="Celsius",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["Celsius", "Fahrenheit"]
                ),
            )
            self.sub_form.add_text("from_val", "Degrees", default="100")

        elif "Length" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                lengths_list,
                default="Meters",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["Meters", "Feet"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                lengths_list,
                default="Feet",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["Feet", "Meters"]
                ),
            )
            self.sub_form.add_text("from_val", "Length choices", default="100")

        elif "Area" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                areas_list,
                default="square feet",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["square feet", "square meters"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                areas_list,
                default="square meters",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["square meters", "square feet"]
                ),
            )
            self.sub_form.add_text("from_val", "Area Value", default="100")

        elif "Volume" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                volume_list,
                default="gallons us",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["gallons us", "liters"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                volume_list,
                default="liters",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["liters", "gallons us"]
                ),
            )
            self.sub_form.add_text("from_val", "Volume Value", default="100")

        elif "Mass" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                mass_list,
                default="pounds",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["pounds", "kilograms"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                mass_list,
                default="kilograms",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["kilograms", "pounds"]
                ),
            )
            self.sub_form.add_text("from_val", "Mass Value", default="100")

        elif "Data" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                data_list,
                default="kilobytes",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["kilobytes", "megabytes"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                data_list,
                default="megabytes",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["megabytes", "kilobytes"]
                ),
            )
            self.sub_form.add_text("from_val", "Data Value", default="100")

        elif "Speed" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                speed_list,
                default="Meters/sec",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["Meters/sec", "Inches/sec"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                speed_list,
                default="Inches/sec",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["Inches/sec", "Meters/sec"]
                ),
            )
            self.sub_form.add_text("from_val", "Speed Value", default="100")

        elif "compinter" in cat:
            self.sub_form.add_text("from_val_one", "Principal ($)", default="1000")
            self.sub_form.add_text("from_val_two", "Rate (% per period)", default="5")
            self.sub_form.add_text("from_val_three", "Time (years)", default="1")
            self.sub_form.add_dropdown(
                "compound_period",
                "Compounding",
                [
                    "Annual",
                    "Monthly",
                    "Crypto (365)",
                    "Futures (312)",
                    "Stocks (252)",
                ],
                default="Annual",
            )

        elif "time" in cat:
            self.sub_form.add_dropdown(
                "from_unit",
                "From",
                self.time_list,
                default="Seconds",
                on_change=lambda val: self._on_update_choices(
                    "from_unit", "to_unit", val, ["Seconds", "Hours"]
                ),
            )
            self.sub_form.add_dropdown(
                "to_unit",
                "To",
                self.time_list,
                relief=tk.GROOVE,
                default="Hours",
                on_change=lambda val: self._on_update_choices(
                    "to_unit", "from_unit", val, ["Hours", "Seconds"]
                ),
            )
            self.sub_form.add_text("from_val", "Time Value", default="100")

        elif "tip" in cat:
            self.sub_form.add_text("from_val_one", "Total Bill ($)", default="100")
            self.sub_form.add_text("from_val_two", "Number of People", default="2")
            self.sub_form.add_text("from_val_three", "Tip (%)", default="15")

        else:
            self.sub_form.add_text("from_val", "Input Value", default="100")

    def _on_update_choices(
        self, src_key: str, target_key: str, choice: str, options: list
    ):
        """Flip the opposite unit dropdown. Currently disabled.

        The method returns immediately, so the auto-flip logic below it
        never runs.

        Args:
            src_key (str): Form key of the dropdown that changed.
            target_key (str): Form key of the dropdown to update.
            choice (str): The unit just selected.
            options (list): The two units available in the category.
        """
        return
        """Auto-flips the opposite dropdown to the other unit."""
        if len(options) >= 2:
            other = options[1] if choice == options[0] else options[0]
            self.sub_form.set_value(target_key, other)
            self.display_var.set(f"Mode: {choice} ➔ {other}")

    def on_run_conversion(self, values: dict):
        """Processes the conversion calculation when the Convert button is clicked."""
        cat_values = self.top_cat_form.get_values()
        cat = cat_values.get("category", "")

        # Read values from the active sub_form
        sub_vals = self.sub_form.get_values() if hasattr(self, "sub_form") else {}

        raw_val = float(sub_vals.get("from_val", 0) or 0)
        from_u = sub_vals.get("from_unit", "")
        to_u = sub_vals.get("to_unit", "")

        try:
            if "Temperature" in cat:
                if from_u == "Celsius" and to_u == "Fahrenheit":
                    res = (raw_val * 9 / 5) + 32
                    self.display_var.set(f"{raw_val}°C = {res:.2f}°F")
                elif from_u == "Fahrenheit" and to_u == "Celsius":
                    res = (raw_val - 32) * 5 / 9
                    self.display_var.set(f"{raw_val}°F = {res:.2f}°C")
                else:
                    self.display_var.set(f"{raw_val} {from_u} = {raw_val:.2f} {to_u}")

            elif "Length" in cat:
                len_res = calc_lengths(from_u, to_u, raw_val)
                if len_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {len_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid length units: {from_u} to {to_u}")

            elif "Area" in cat:
                area_res = calc_areas(from_u, to_u, raw_val)
                if area_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {area_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid units: {from_u} to {to_u}")

            elif "Volume" in cat:
                vol_res = calc_volume(from_u, to_u, raw_val)
                if DEBUG:
                    sys.stderr.write(
                        f"Volume conversion: {raw_val} {from_u} to {to_u} = {vol_res}\n"
                    )
                    sys.stderr.flush()
                if vol_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {vol_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid units: {from_u} to {to_u}")

            elif "Mass" in cat:
                mass_res = calc_mass(from_u, to_u, raw_val)
                if mass_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {mass_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid units: {from_u} to {to_u}")

            elif "Data" in cat:
                data_res = calc_data(from_u, to_u, raw_val)
                if data_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {data_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid units: {from_u} to {to_u}")

            elif "Speed" in cat:
                speed_res = calc_speed(from_u, to_u, raw_val)
                if speed_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {speed_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid units: {from_u} to {to_u}")

            elif "compinter" in cat:
                principal = float(sub_vals.get("from_val_one", 0) or 0)
                rate = float(sub_vals.get("from_val_two", 0) or 0)
                years = float(sub_vals.get("from_val_three", 0) or 0)
                compound_period = sub_vals.get("compound_period", "Annual")
                periods_per_year = {
                    "Annual": 1,
                    "Monthly": 12,
                    "Crypto (365)": 365,
                    "Futures (312)": 312,
                    "Stocks (252)": 252,
                }[compound_period]
                periods = years * periods_per_year
                total = principal * ((1 + (rate / 100.0)) ** periods)
                interest = total - principal
                self.display_var.set(f"Interest: ${interest:.2f} | Total: ${total:.2f}")

            elif "time" in cat:
                time_res = calc_time(from_u, to_u, raw_val)
                if time_res is not None:
                    self.display_var.set(f"{raw_val} {from_u} = {time_res:.2f} {to_u}")
                else:
                    self.display_var.set(f"Invalid units: {from_u} to {to_u}")

            elif "tip" in cat:
                bill = float(sub_vals.get("from_val_one", 0) or 0)
                num_people = max(1, float(sub_vals.get("from_val_two", 1) or 1))
                tip_pct = float(sub_vals.get("from_val_three", 15) or 15)
                tip_total = bill * (tip_pct / 100.0)
                grand_total = bill + tip_total
                per_person = grand_total / num_people
                self.display_var.set(
                    f"Tip: ${tip_total:.2f} | Total: ${grand_total:.2f} | Each: ${per_person:.2f}"
                )

            else:
                self.display_var.set(f"Value: {raw_val}")

        except Exception as err:
            self.display_var.set(f"Calculation Error: {err}")

    def on_cell_click(self, txt):
        """Handle the click event for each button"""
        if DEBUG:
            sys.stderr.write(f"Button pressed: {txt}\n")
            sys.stderr.flush()

        # After recalling a memory item, a new number starts a fresh
        # calculation instead of being appended to the recalled expression.
        if self.recall_pending and (txt.isdigit() or txt == "."):
            self.entry_box.delete("1.0", "end")
            self.result_box.config(state="normal")
            self.result_box.delete(0, "end")
            self.result_box.config(state="readonly")
        self.recall_pending = False

        if txt == "⇄":
            if self.scientific_extended:
                self.scientific_extended = False
                self.standard_mode = False
                self.mode_var.set("Scientific")
                self.on_mode_switched()
            #                self._build_scientific_mode()
            else:
                self.scientific_extended = True
                self.standard_mode = False
                self.mode_var.set("Scientific Extended")
                self.on_mode_switched()
        #                self._build_scientific_mode_ext()
        elif txt == "Bk":
            self._backspace_formula()
        elif txt == "%":
            current_text = self.entry_box.get("1.0", "end-1c")
            number_match = re.search(r"(?:\d+(?:\.\d*)?|\.\d+)$", current_text)
            if number_match:
                number = float(number_match.group())
                percentage = str(number / 100)
                start = f"1.0+{number_match.start()} chars"
                end = f"1.0+{number_match.end()} chars"
                self.entry_box.delete(start, end)
                self.entry_box.insert(start, percentage)
        elif txt == "C":
            self.entry_box.delete("1.0", "end")
        elif txt == "()":
            current_text = self.entry_box.get("1.0", "end-1c")

            if current_text.count("(") > current_text.count(")"):
                self._insert_formula_text(")")
            else:
                # Add multiplication for expressions such as 5(...)
                if current_text and (
                    current_text[-1].isdigit() or current_text[-1] == ")"
                ):
                    self._insert_formula_text("*(")
                else:
                    self._insert_formula_text("(")
        elif txt == "Rad":
            self.angle_mode = "degrees" if self.angle_mode == "radians" else "radians"
            self.display_var.set(f"Angle mode: {self.angle_mode}")
        elif txt in {
            "√",
            "∛",
            "|x|",
            "sin",
            "cos",
            "tan",
            "sin⁻¹",
            "cos⁻¹",
            "tan⁻¹",
            "ln",
            "log",
            "1/x",
            "eˣ",
            "x²",
            "x³",
            "2ˣ",
            "sinh",
            "cosh",
            "tanh",
            "sinh⁻¹",
            "cosh⁻¹",
            "tanh⁻¹",
            "x!",
            "+/-",
        }:
            self._append_scientific_operation(txt)
        elif txt == "xʸ":
            if self.entry_box.get("1.0", "end-1c"):
                self._insert_formula_text("**")
        elif txt in {"π", "e"}:
            current_text = self.entry_box.get("1.0", "end-1c")
            if current_text and (current_text[-1].isdigit() or current_text[-1] == ")"):
                self._insert_formula_text(f"*{txt}")
            else:
                self._insert_formula_text(txt)
        elif txt == "=":
            current_text = self.entry_box.get("1.0", "end-1c")
            try:
                result = eval(
                    current_text,
                    {"__builtins__": {}, **self._scientific_namespace()},
                    {},
                )
                self.entry_box.delete("1.0", "end")

                self.result_box.config(state="normal")
                self.result_box.delete(0, "end")
                self.result_box.insert(0, str(result))
                self.result_box.config(state="readonly")
            except Exception as error:
                self.result_box.config(state="normal")
                self.result_box.delete(0, "end")
                self.result_box.insert(0, f"Error: {error}")
                self.result_box.config(state="readonly")
            # Store the expression captured before entry_box is cleared,
            # together with its result, as one memory item.
            self.mem_q.append((current_text, self.result_box.get()))
        else:
            self._insert_formula_text(txt)

    def _insert_formula_text(self, text):
        """Type button text where the cursor is, replacing selected text."""
        try:
            self.entry_box.delete("sel.first", "sel.last")
        except tk.TclError:
            # There is no selection.  That is perfectly normal.
            pass
        self.entry_box.insert("insert", text)

    def _backspace_formula(self):
        """Delete selected text, or one character before the cursor."""
        try:
            self.entry_box.delete("sel.first", "sel.last")
        except tk.TclError:
            self.entry_box.delete("insert-1c", "insert")

    def _on_formula_enter(self, event):
        """Make the keyboard Enter key behave like the equals button."""
        self.on_cell_click("=")
        return "break"

    def _scientific_namespace(self):
        """Return the names used when evaluating scientific expressions."""
        angle = math.radians if self.angle_mode == "degrees" else lambda x: x
        inverse_angle = math.degrees if self.angle_mode == "degrees" else lambda x: x

        return {
            "π": math.pi,
            "e": math.e,
            "sqrt": math.sqrt,
            "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
            "abs": abs,
            "sin": lambda x: math.sin(angle(x)),
            "cos": lambda x: math.cos(angle(x)),
            "tan": lambda x: math.tan(angle(x)),
            "asin": lambda x: inverse_angle(math.asin(x)),
            "acos": lambda x: inverse_angle(math.acos(x)),
            "atan": lambda x: inverse_angle(math.atan(x)),
            "ln": math.log,
            "log": math.log10,
            "recip": lambda x: 1 / x,
            "exp": math.exp,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "asinh": math.asinh,
            "acosh": math.acosh,
            "atanh": math.atanh,
            "factorial": lambda x: (
                math.factorial(int(x))
                if x >= 0 and float(x).is_integer()
                else (_ for _ in ()).throw(
                    ValueError("factorial needs a non-negative integer")
                )
            ),
            "neg": lambda x: -x,
        }

    def _append_scientific_operation(self, operation):
        """Wrap the current expression in a scientific operation."""
        expression = self.entry_box.get("1.0", "end-1c")
        if not expression:
            return

        function_names = {
            "√": "sqrt",
            "∛": "cbrt",
            "|x|": "abs",
            "sin": "sin",
            "cos": "cos",
            "tan": "tan",
            "sin⁻¹": "asin",
            "cos⁻¹": "acos",
            "tan⁻¹": "atan",
            "ln": "ln",
            "log": "log",
            "1/x": "recip",
            "eˣ": "exp",
            "sinh": "sinh",
            "cosh": "cosh",
            "tanh": "tanh",
            "sinh⁻¹": "asinh",
            "cosh⁻¹": "acosh",
            "tanh⁻¹": "atanh",
            "x!": "factorial",
            "+/-": "neg",
        }

        if operation == "x²":
            updated_expression = f"({expression})**2"
        elif operation == "x³":
            updated_expression = f"({expression})**3"
        elif operation == "2ˣ":
            updated_expression = f"2**({expression})"
        else:
            updated_expression = f"{function_names[operation]}({expression})"

        self.entry_box.delete("1.0", "end")
        self.entry_box.insert("end", updated_expression)

    def on_memory(self):
        """Display the shared memory queue in every mode's memory box."""
        for memory_box in self.memory_boxes:
            memory_box.config(state="normal")
            memory_box.delete("1.0", "end")
            for expression, result in self.mem_q:
                memory_box.insert("end", f"{expression}\n{result}\n")
            memory_box.config(state="disabled")

    def on_clear_memory(self):
        """Clear memory and reset the visible calculator state."""
        self.mem_q.clear()
        self.recall_pending = False
        for memory_box in self.memory_boxes:
            memory_box.config(state="normal")
            memory_box.delete("1.0", "end")
            memory_box.config(state="disabled")

        # A recalled expression may still be in entry_box.  Clear it here so
        # a new calculation cannot be appended to the recalled expression.
        self.entry_box.config(state="normal")
        self.entry_box.delete("1.0", "end")
        self.result_box.config(state="normal")
        self.result_box.delete(0, "end")
        self.result_box.config(state="readonly")

    def on_memory_rec(self):
        """Recall last memorized sequence , put it back in the visible text box and remove it from queue"""
        if self.mem_q:
            last_mem = self.mem_q.pop()
            self.entry_box.config(state="normal")
            self.entry_box.delete("1.0", "end")
            self.entry_box.insert("1.0", last_mem[0])
            self.result_box.config(state="normal")
            self.result_box.delete(0, "end")
            self.result_box.insert(0, last_mem[1])
            self.result_box.config(state="readonly")
            self.recall_pending = True
            self.on_memory()  # Update the memory display


if __name__ == "__main__":
    app = QuickApp(title="TK Calculator", size=(960, 860), theme="Dark Obsidian")
    app.set_single_tool(TkCalc)
    app.run()
