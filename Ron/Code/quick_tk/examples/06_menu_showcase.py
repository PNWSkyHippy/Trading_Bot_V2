"""
Menu System Showcase Tool
Demonstrates hierarchical menus, submenus, toggle checkboxes, radio groups,
file pickers, and keyboard shortcuts in QuickTk.
"""

import os
import sys

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView


class MenuShowcaseTool(ToolView):
    title = "Menu System Showcase"
    description = "Demonstration of hierarchical menus, submenus, toggles, file pickers, and shortcuts"

    def build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Output console to display menu click actions
        self.console = self.add_console(title="Menu Action Event Log", parent=self)
        self.console.grid(row=0, column=0, sticky="nsew")

        self.console.write_heading("MENU SYSTEM DEMO")
        self.console.write_line("Click on the menu items above (File, Edit, View, Tools, Help) to see actions logged here in real-time.\n", "dim")

        # Setup Menus using the new fluent API
        self.setup_menus()

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_item("New Project", self.on_new_project, shortcut="Ctrl+N")
        file_menu.add_file_open("Open Data File...", self.on_file_opened, filetypes=[("CSV/Text", "*.csv;*.txt"), ("All Files", "*.*")], shortcut="Ctrl+O")
        file_menu.add_file_save("Save Report As...", self.on_file_saved, default_filename="report.csv", default_ext=".csv", shortcut="Ctrl+S")
        file_menu.add_separator()

        # Cascading Submenu: File > Export > ...
        export_sub = file_menu.add_submenu("Export As")
        export_sub.add_item("Export to CSV", lambda: self.log_action("Exported data to CSV"))
        export_sub.add_item("Export to JSON", lambda: self.log_action("Exported data to JSON"))
        export_sub.add_item("Export to Excel (.xlsx)", lambda: self.log_action("Exported data to Excel"))

        file_menu.add_separator()
        file_menu.add_item("Exit Application", self.app.root.quit, shortcut="Alt+F4")

        # 2. EDIT MENU
        edit_menu = self.menu("Edit")
        edit_menu.add_item("Undo", lambda: self.log_action("Undo performed"), shortcut="Ctrl+Z")
        edit_menu.add_item("Redo", lambda: self.log_action("Redo performed"), shortcut="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_item("Clear Console", self.console.clear)

        # 3. VIEW MENU (With Toggle Checkboxes and Radio Groups)
        view_menu = self.menu("View")
        self.show_timestamps_var = view_menu.add_toggle(
            "Include Timestamps",
            default=True,
            on_toggle=lambda state: self.log_action(f"Toggled Timestamps: {state}"),
            shortcut="Ctrl+T",
        )
        self.auto_scroll_var = view_menu.add_toggle(
            "Auto-Scroll Log",
            default=True,
            on_toggle=lambda state: self.log_action(f"Toggled Auto-Scroll: {state}"),
        )
        view_menu.add_separator()

        # View > Layout Density (Radio Group)
        density_sub = view_menu.add_submenu("Log Detail Level")
        density_sub.add_radio_group(
            options=["Normal", "Verbose (Debug)", "Compact Summary"],
            default="Normal",
            on_change=lambda val: self.log_action(f"Detail Level set to: {val}"),
        )

        # 4. TOOLS MENU (Declarative Tree Style)
        self.build_menu_tree({
            "Tools": [
                {"label": "Run Quick Diagnostic", "command": lambda: self.log_action("Diagnostic tests passed!"), "shortcut": "F5"},
                {"label": "Calculate Metrics", "command": lambda: self.log_action("Metrics calculated: Win Rate 68%"), "shortcut": "F6"},
                "---",
                {
                    "label": "Database Utilities",
                    "submenu": [
                        {"label": "Vacuum Database", "command": lambda: self.log_action("DB Vacuumed successfully.")},
                        {"label": "Re-index Tables", "command": lambda: self.log_action("DB Re-indexed.")},
                    ]
                }
            ],
            "Help": [
                {"label": "Documentation", "command": lambda: self.log_action("Opening documentation...")},
                {"label": "Check for Updates", "command": lambda: self.log_action("QuickTk is up to date (v1.1.0)")},
                "---",
                {"label": "About QuickTk", "command": lambda: self.log_action("QuickTk v1.1.0 - Pure Python OOP Desktop Framework")},
            ]
        })

    def on_new_project(self):
        self.log_action("Created New Project", tag="primary")

    def on_file_opened(self, filepath: str):
        self.log_action(f"Opened file: {filepath}", tag="success")

    def on_file_saved(self, filepath: str):
        self.log_action(f"Saved destination set to: {filepath}", tag="success")

    def log_action(self, msg: str, tag: str = "info"):
        self.console.write_line(f"▶ {msg}", tag=tag)
        self.set_status(f"Menu action: {msg}")


if __name__ == "__main__":
    app = QuickApp(title="QuickTk Menu System Showcase", size=(920, 600), theme="Dark Obsidian")
    app.set_single_tool(MenuShowcaseTool)
    app.run()
