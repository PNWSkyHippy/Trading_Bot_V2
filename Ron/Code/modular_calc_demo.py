import tkinter as tk
from tkinter import ttk

from quick_tk import QuickApp, ToolView


class MultiModeCalculator(ToolView):
    title = "Modular Multi-Mode Calculator"

    def build_ui(self):
        # Master column/row configuration
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Row 2 holds the swapping frame area

        # -------------------------------------------------------------
        # 1. TOP BAR: Mode Selector (Dropdown or Segmented Pills)
        # -------------------------------------------------------------
        top_bar = ttk.Frame(self, padding=8)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.columnconfigure(1, weight=1)

        ttk.Label(top_bar, text="Mode: ", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, padx=(0, 6)
        )
        self.mode_var = tk.StringVar(value="Standard")
        mode_combo = ttk.Combobox(
            top_bar,
            textvariable=self.mode_var,
            values=["Standard", "Scientific", "Unit Converter"],
            state="readonly",
            width=18,
        )
        mode_combo.grid(row=0, column=1, sticky="w")
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_switched)

        # -------------------------------------------------------------
        # 2. SHARED DISPLAY SCREEN (Used across all modes)
        # -------------------------------------------------------------
        self.display_var = tk.StringVar(value="FUCK YOU!!!")
        display_frame = ttk.Frame(self, padding=10)
        display_frame.grid(row=1, column=0, sticky="ew")

        display_entry = tk.Entry(
            display_frame,
            textvariable=self.display_var,
            font=("Consolas", 22, "bold"),
            bg="#181825",
            fg="#cdd6f4",
            justify="right",
            bd=0,
            relief="flat",
        )
        display_entry.pack(fill="x", ipady=8)

        # -------------------------------------------------------------
        # 3. SWAP CONTAINER (Houses all mode frames in the same cell)
        # -------------------------------------------------------------
        self.container = ttk.Frame(self, padding=8)
        self.container.grid(row=2, column=0, sticky="nsew")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        # Build the 3 distinct mode frames
        self.mode_frames = {}
        self.mode_frames["Standard"] = self._build_standard_mode()
        self.mode_frames["Scientific"] = self._build_scientific_mode()
        self.mode_frames["Unit Converter"] = self._build_converter_mode()

        # Show Standard mode by default
        self.show_mode("Standard")

    # =================================================================
    # LAYOUT BUILDERS (Each returns its own isolated LabelFrame)
    # =================================================================
    def _build_standard_mode(self) -> ttk.Frame:
        frame = ttk.LabelFrame(self.container, text=" Standard Pad ", padding=8)
        frame.grid(row=0, column=0, sticky="nsew")

        # 4x4 keypad grid
        buttons = [
            ("7", "8", "9", "/"),
            ("4", "5", "6", "*"),
            ("1", "2", "3", "-"),
            ("C", "0", "=", "+"),
        ]
        for r, row in enumerate(buttons):
            frame.rowconfigure(r, weight=1)
            for c, char in enumerate(row):
                frame.columnconfigure(c, weight=1)
                btn = tk.Button(
                    frame,
                    text=char,
                    font=("Segoe UI", 14),
                    bg="#313244",
                    fg="#cdd6f4",
                    activebackground="#45475a",
                    command=lambda ch=char: self.handle_calc_input(ch),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
        return frame

    def _build_scientific_mode(self) -> ttk.Frame:
        frame = ttk.LabelFrame(
            self.container, text=" Scientific Extensions + Pad ", padding=8
        )
        frame.grid(row=0, column=0, sticky="nsew")

        # Scientific rows on top + Standard below
        sci_buttons = [
            ("sin", "cos", "tan", "sqrt"),
            ("ln", "log", "π", "^"),
            ("7", "8", "9", "/"),
            ("4", "5", "6", "*"),
            ("1", "2", "3", "-"),
            ("C", "0", "=", "+"),
        ]
        for r, row in enumerate(sci_buttons):
            frame.rowconfigure(r, weight=1)
            for c, char in enumerate(row):
                frame.columnconfigure(c, weight=1)
                is_sci = r < 2
                btn = tk.Button(
                    frame,
                    text=char,
                    font=("Segoe UI", 12 if is_sci else 14),
                    bg="#1e1e2e" if is_sci else "#313244",
                    fg="#89b4fa" if is_sci else "#cdd6f4",
                    command=lambda ch=char: self.handle_calc_input(ch),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
        return frame

    def _build_converter_mode(self) -> ttk.Frame:
        frame = ttk.LabelFrame(
            self.container, text=" Unit Converter & Calculations ", padding=10
        )
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        # Category dropdown (Length, Area, Temperature, Volume, Amortization)
        top_sub = self.add_form("Converter Settings", parent=frame)
        top_sub.pack(fill="x", pady=(0, 10))
        top_sub.add_dropdown(
            "category",
            "Conversion Type",
            [
                "Length (m ⇄ ft)",
                "Temperature (°C ⇄ °F)",
                "Area (sq ft ⇄ sq m)",
                "Amortization",
            ],
        )
        top_sub.add_text("from_val", "Input Value", default="100")
        top_sub.add_button(
            "Convert 🔄", callback=self.on_run_conversion, variant="primary"
        )
        return frame

    # =================================================================
    # MODE SWITCHER (Instant 0ms frame raise)
    # =================================================================
    def show_mode(self, mode_name: str):
        target_frame = self.mode_frames.get(mode_name)
        if target_frame:
            target_frame.tkraise()  # Brings target to front without destroying anything!
            self.set_status(f"Switched to {mode_name} mode")

    def on_mode_switched(self, event=None):
        self.show_mode(self.mode_var.get())

    # =================================================================
    # LOGIC HANDLERS
    # =================================================================
    def handle_calc_input(self, char: str):
        cur = self.display_var.get()
        if char == "C":
            self.display_var.set("0")
        elif char == "=":
            try:
                # Basic eval demonstration
                res = str(eval(cur.replace("^", "**").replace("π", "3.14159265")))
                self.display_var.set(res)
            except Exception:
                self.display_var.set("Error")
        else:
            self.display_var.set(char if cur == "0" else cur + char)

    def on_run_conversion(self, values: dict):
        cat = values.get("category", "")
        raw_val = float(values.get("from_val", 0) or 0)
        if "Temperature" in cat:
            converted = (raw_val * 9 / 5) + 32
            self.display_var.set(f"{raw_val}°C = {converted:.2f}°F")
        elif "Length" in cat:
            converted = raw_val * 3.28084
            self.display_var.set(f"{raw_val}m = {converted:.2f}ft")
        else:
            self.display_var.set(f"Result for {raw_val}")


if __name__ == "__main__":
    app = QuickApp(
        title="Multi-Mode Calculator", size=(520, 620), theme="Dark Obsidian"
    )
    app.set_single_tool(MultiModeCalculator)
    app.run()
