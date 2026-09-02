"""
QuickTk - High-Level OOP GUI Framework for Python Utilities & Scripts
"""

import sys
import os

try:
    from .core.app import QuickApp, ToolView
    from .core.forms import FormPanel
    from .core.outputs import ConsolePanel, DataTable, StatGrid
    from .core.theme import Theme, apply_theme
except ImportError:
    # Allow fallback if imported from within directory
    from core.app import QuickApp, ToolView
    from core.forms import FormPanel
    from core.outputs import ConsolePanel, DataTable, StatGrid
    from core.theme import Theme, apply_theme

__version__ = "1.0.0"

__all__ = [
    "QuickApp",
    "ToolView",
    "FormPanel",
    "DataTable",
    "StatGrid",
    "ConsolePanel",
    "Theme",
    "apply_theme",
]
