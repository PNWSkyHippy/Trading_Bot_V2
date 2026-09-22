"""
QuickTk - High-Level OOP GUI Framework for Python Utilities & Scripts
"""

import sys
import os

try:
    from .core.app import QuickApp, ToolView
    from .core.forms import FormPanel, MultiSelectDropdown, HAS_CTK
    from .core.menu import MenuBarBuilder, MenuNode
    from .core.outputs import (
        ConsolePanel,
        DataTable,
        ImagePanel,
        StatGrid,
        show_image_window,
    )
    from .core.theme import Theme, apply_theme
except ImportError:
    # Allow fallback if imported from within directory
    from core.app import QuickApp, ToolView
    from core.forms import FormPanel, MultiSelectDropdown, HAS_CTK
    from core.menu import MenuBarBuilder, MenuNode
    from core.outputs import (
        ConsolePanel,
        DataTable,
        ImagePanel,
        StatGrid,
        show_image_window,
    )
    from core.theme import Theme, apply_theme

__version__ = "1.4.0"

__all__ = [
    "QuickApp",
    "ToolView",
    "FormPanel",
    "MultiSelectDropdown",
    "HAS_CTK",
    "MenuBarBuilder",
    "MenuNode",
    "DataTable",
    "StatGrid",
    "ConsolePanel",
    "ImagePanel",
    "show_image_window",
    "Theme",
    "apply_theme",
]
