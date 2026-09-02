"""
All-In-One Utility Suite
Combines all 4 utility tools into a single, unified modern dashboard with sidebar navigation.
"""

import os
import sys
import importlib

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp

trade_mod = importlib.import_module("examples.01_trade_analyzer")
grade_mod = importlib.import_module("examples.02_grade_calculator")
futures_mod = importlib.import_module("examples.03_futures_tick_calc")
cheat_mod = importlib.import_module("examples.04_cheat_sheet_viewer")


def launch_suite():
    app = QuickApp(title="Master Python Utility Suite", size=(1200, 780), theme="dark")

    # Add Top Menu
    app.add_menu("File", [
        ("Switch Theme (Dark/Light)", app.toggle_theme),
        ("---", None),
        ("Exit", app.root.quit),
    ])

    tools = [
        trade_mod.TradeAnalyzerTool,
        grade_mod.GradeCalculatorTool,
        futures_mod.FuturesTickCalcTool,
        cheat_mod.CheatSheetTool,
    ]

    app.setup_sidebar(tools, default_index=0)
    app.run()


if __name__ == "__main__":
    launch_suite()
