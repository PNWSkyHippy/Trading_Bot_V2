"""
Menu Popup Form Showcase - QuickTk
Demonstrates clearing up main window real estate by moving secondary inputs
(dropdowns, multi-selects, file pickers, and action buttons) into a popup window
launched from a top menu choice.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import FormPanel, QuickApp, ToolView


class MainWorkspaceTool(ToolView):
    title = "Main Workspace (Clean Layout)"
    description = "Inputs have been moved to a menu-driven popup window to leave room for the main display."

    def build_ui(self):
        # Configure layout: Main window is dedicated to outputs & results
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        # 1. Summary Stat Grid across the top
        self.stats = self.add_stat_grid(parent=self)
        self.stats.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.stats.set_metrics(
            {
                "Active Feed": ("Not Selected", "info"),
                "Input File": ("None", "warning"),
                "Status": ("Ready", "success"),
            }
        )

        # 2. Large Console Panel occupying the main window space
        self.console = self.add_console("Workspace Log & Output Stream", parent=self)
        self.console.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.console.write_heading("CLEAN MAIN WINDOW")
        self.console.write_line(
            "All parameter inputs, dropdowns, and file pickers have been moved to the menu.",
            "dim",
        )
        self.console.write_line(
            "Click 'Configuration' -> 'Open Input & File Dialog...' in the menu bar to set up parameters.\n",
            "primary",
        )

        # 3. Setup Top Menu Bar
        self.setup_menu()

    def setup_menu(self):
        # Top-level Menu: Configuration
        config_menu = self.menu("Configuration")
        config_menu.add_item(
            "Open Input & File Dialog... (Modal)",
            self.open_modal_inputs,
            shortcut="Ctrl+P",
        )
        config_menu.add_item(
            "Open Floating Tool Window... (Non-Modal)",
            self.open_floating_window,
            shortcut="Ctrl+Shift+P",
        )
        config_menu.add_separator()
        config_menu.add_item("Exit", self.app.root.quit, shortcut="Alt+F4")

    # =========================================================================
    # OPTION 1: MODAL POPUP DIALOG (self.prompt_form)
    # Recommended for straightforward configuration steps
    # =========================================================================
    def open_modal_inputs(self):
        def build_inputs(form: FormPanel):
            # Dropdown boxes
            form.add_dropdown(
                name="data_source",
                label="Market Data Feed",
                options=[
                    "Alpaca Trading API",
                    "Interactive Brokers",
                    "Yahoo Finance",
                    "Binance Spot",
                ],
                default="Alpaca Trading API",
            )
            form.add_dropdown(
                name="timeframe",
                label="Bar Resolution",
                options=["1 Minute", "5 Minutes", "15 Minutes", "1 Hour", "1 Day"],
                default="5 Minutes",
            )

            # File pickers
            form.add_file_picker(
                name="dataset_file",
                label="Input Dataset (CSV / Parquet)",
                mode="open",
                filetypes=[
                    ("Data Files", "*.csv;*.parquet;*.json"),
                    ("All Files", "*.*"),
                ],
            )
            form.add_file_picker(
                name="output_dir", label="Export Destination Folder", mode="directory"
            )

            # Option checkbox
            form.add_checkbox(
                "auto_clean", "Auto-clean null rows on ingest", default=True
            )

        # Opens popup dialog centered over the main window
        results = self.prompt_form(
            title="Configure Sources & File Pickers",
            form_builder_fn=build_inputs,
            size=(480, 420),
            ok_text="Apply & Ingest",
            cancel_text="Cancel",
        )

        if results:
            self.on_apply_inputs(results)

    # =========================================================================
    # OPTION 2: PERSISTENT FLOATING WINDOW (tk.Toplevel)
    # Use if you want the window to stay open while working on the main screen
    # =========================================================================
    def open_floating_window(self):
        popup = tk.Toplevel(self)
        popup.title("Floating Configuration Palette")
        popup.geometry("480x440")
        popup.configure(bg=self.theme.get("bg", "#181825"))

        container = ttk.Frame(popup, style="Surface.TFrame", padding=14)
        container.pack(fill="both", expand=True)

        form = FormPanel(container, theme=self.theme)
        form.pack(fill="both", expand=True)

        form.add_dropdown(
            name="strategy",
            label="Execution Strategy",
            options=["Momentum Breakout", "Mean Reversion", "VWAP Scalper"],
            default="Momentum Breakout",
        )
        form.add_file_picker(
            name="model_weights",
            label="Model Weights File",
            mode="open",
            filetypes=[("Model Files", "*.pth;*.onnx;*.bin"), ("All Files", "*.*")],
        )
        form.add_file_picker(
            name="log_dir", label="Diagnostics Log Directory", mode="directory"
        )

        # Action Buttons inside the popup
        def _on_submit():
            vals = form.get_values()
            self.on_apply_inputs(vals)
            popup.destroy()

        form.add_button(
            "Execute with Selected Files", callback=_on_submit, variant="primary"
        )

    def on_apply_inputs(self, values: dict):
        self.console.write_heading("RECEIVED CONFIGURATION FROM POPUP WINDOW")
        for k, v in values.items():
            self.console.write_line(f"  • {k}: {v}", "info")

        feed = values.get("data_source") or values.get("strategy") or "Custom"
        infile = (
            values.get("dataset_file") or values.get("model_weights") or "Not Specified"
        )
        filename = os.path.basename(infile) if infile else "None"

        self.stats.set_metrics(
            {
                "Active Feed": (feed, "primary"),
                "Input File": (
                    filename,
                    "success" if filename != "None" else "warning",
                ),
                "Status": ("Configured", "success"),
            }
        )
        self.set_status(f"Loaded configuration from popup: {feed}")


if __name__ == "__main__":
    app = QuickApp(
        title="QuickTk - Menu Popup Form Example",
        size=(880, 560),
        theme="Dark Obsidian",
    )
    # Run as a clean standalone single tool view
    app.set_single_tool(MainWorkspaceTool)
    app.run()
