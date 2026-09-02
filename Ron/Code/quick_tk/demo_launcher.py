"""
QuickTk Demo Launcher & Architecture Showcase
Run this script to test all 4 interactive prototype tools or the unified Master Suite.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

# Add scratch root to sys.path so 'import quick_tk' works directly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView


class LauncherTool(ToolView):
    title = "QuickTk Showcase Launcher"
    description = "Launch any individual utility tool or the Master All-In-One Suite"

    def build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_card = ttk.Frame(self, style="Surface.TFrame", padding=24)
        main_card.grid(row=0, column=0, sticky="nsew")
        main_card.columnconfigure(0, weight=1)

        # Title & Subtitle
        t_lbl = ttk.Label(main_card, text="QuickTk Utility Framework", style="Title.TLabel", font=("Segoe UI", 18, "bold"))
        t_lbl.grid(row=0, column=0, sticky="w", pady=(0, 4))

        sub_lbl = ttk.Label(
            main_card,
            text="A clean, modern OOP wrapper around Tkinter designed to turn CLI scripts into polished desktop apps in minutes.",
            style="Dim.TLabel",
            font=("Segoe UI", 10),
        )
        sub_lbl.grid(row=1, column=0, sticky="w", pady=(0, 20))

        # Demos list
        demos = [
            ("Master All-in-One Dashboard", "Combines all 4 tools below into a single unified sidebar application.", "examples/05_all_in_one_suite.py", "primary"),
            ("1. SQLite Trade Analyzer", "Filters trades by strategy, dates, min PnL; computes Win Rate / Drawdown, and exports CSV.", "examples/01_trade_analyzer.py", "default"),
            ("2. College Grade Estimator", "Live auto-calculating grade book with weighted components and target score estimator.", "examples/02_grade_calculator.py", "default"),
            ("3. Futures Tick & Sizing Calculator", "Interactive sliders for ES, MES, NQ, contracts, profit targets, stop loss risk, and tick table.", "examples/03_futures_tick_calc.py", "default"),
            ("4. Python Reference & Cheat Sheet", "Interactive topic guide, method table, and syntax-highlighted code console.", "examples/04_cheat_sheet_viewer.py", "default"),
        ]

        for idx, (name, desc, script_path, variant) in enumerate(demos):
            card = ttk.Frame(main_card, style="Card.TFrame", padding=14)
            card.grid(row=idx + 2, column=0, sticky="ew", pady=6)
            card.columnconfigure(0, weight=1)

            btn_frame = ttk.Frame(card, style="Card.TFrame")
            btn_frame.grid(row=0, column=0, sticky="ew")
            btn_frame.columnconfigure(0, weight=1)

            demo_title = ttk.Label(btn_frame, text=name, style="Heading.TLabel", font=("Segoe UI", 11, "bold"))
            demo_title.grid(row=0, column=0, sticky="w")

            btn_style = "Primary.TButton" if variant == "primary" else "TButton"
            launch_btn = ttk.Button(
                btn_frame,
                text="Launch Tool ▶",
                style=btn_style,
                command=lambda p=script_path: self._launch_script(p),
            )
            launch_btn.grid(row=0, column=1, sticky="e")

            desc_lbl = ttk.Label(card, text=desc, style="DimCard.TLabel")
            desc_lbl.grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _launch_script(self, rel_path: str):
        full_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        self.set_status(f"Launching {os.path.basename(rel_path)}...")
        subprocess.Popen([sys.executable, full_path], cwd=BASE_DIR)


if __name__ == "__main__":
    app = QuickApp(title="QuickTk Prototype Launcher", size=(880, 680), theme="dark")
    app.set_single_tool(LauncherTool)
    app.run()
