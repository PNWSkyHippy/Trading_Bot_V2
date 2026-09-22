"""
Verification test for QuickTk imports and core classes.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

import quick_tk
from quick_tk import (
    QuickApp,
    ToolView,
    FormPanel,
    DataTable,
    StatGrid,
    ConsolePanel,
    Theme,
)

print("=== QuickTk Verification Success ===")
print("Version:", quick_tk.__version__)
print("Available Themes:", list(Theme.PRESETS.keys()))
print("All classes loaded properly!")
