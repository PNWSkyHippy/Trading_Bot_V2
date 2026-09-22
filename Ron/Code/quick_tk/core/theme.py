"""
Theme and styling configuration for QuickTk.
Provides multiple preset modern themes and a dynamic customization engine.
"""

import tkinter as tk
from tkinter import ttk


class Theme:
    # 1. Modern Obsidian Dark (Default)
    DARK = {
        "name": "dark",
        "bg": "#181825",
        "surface": "#1e1e2e",
        "surface_alt": "#28283d",
        "surface_active": "#3b3b58",
        "border": "#45475a",
        "text": "#cdd6f4",
        "text_dim": "#a6adc8",
        "text_highlight": "#ffffff",
        "primary": "#89b4fa",
        "primary_hover": "#b4befe",
        "primary_text": "#11111b",
        "success": "#a6e3a1",
        "success_bg": "#1c3327",
        "danger": "#f38ba8",
        "danger_bg": "#3c1e28",
        "warning": "#f9e2af",
        "warning_bg": "#382e18",
        "info": "#74c7ec",
        "card_bg": "#1e1e2e",
        "console_bg": "#11111b",
        "console_fg": "#cdd6f4",
        "tree_bg": "#1e1e2e",
        "tree_fg": "#cdd6f4",
        "tree_selected": "#3b3b58",
        "tree_even": "#181825",
        "entry_bg": "#11111b",
        "entry_fg": "#cdd6f4",
    }

    # 2. Clean Light Modern
    LIGHT = {
        "name": "light",
        "bg": "#f5f6f8",
        "surface": "#ffffff",
        "surface_alt": "#ebedf2",
        "surface_active": "#dfe2ea",
        "border": "#d3d7e0",
        "text": "#2d3139",
        "text_dim": "#68707d",
        "text_highlight": "#111827",
        "primary": "#2563eb",
        "primary_hover": "#1d4ed8",
        "primary_text": "#ffffff",
        "success": "#16a34a",
        "success_bg": "#dcfce7",
        "danger": "#dc2626",
        "danger_bg": "#fee2e2",
        "warning": "#d97706",
        "warning_bg": "#fef3c7",
        "info": "#0284c7",
        "card_bg": "#ffffff",
        "console_bg": "#1f2937",
        "console_fg": "#f9fafb",
        "tree_bg": "#ffffff",
        "tree_fg": "#2d3139",
        "tree_selected": "#bfdbfe",
        "tree_even": "#f9fafb",
        "entry_bg": "#ffffff",
        "entry_fg": "#2d3139",
    }

    # 3. Cyberpunk Neon Cyan
    CYBERPUNK = {
        "name": "cyberpunk",
        "bg": "#0d0f18",
        "surface": "#151824",
        "surface_alt": "#1f2438",
        "surface_active": "#2b324e",
        "border": "#00f0ff",
        "text": "#e0f8ff",
        "text_dim": "#7d97b0",
        "text_highlight": "#00f0ff",
        "primary": "#00f0ff",
        "primary_hover": "#70f7ff",
        "primary_text": "#000000",
        "success": "#00ff9d",
        "success_bg": "#003320",
        "danger": "#ff0055",
        "danger_bg": "#3d0014",
        "warning": "#ffea00",
        "warning_bg": "#3d3800",
        "info": "#00d4ff",
        "card_bg": "#151824",
        "console_bg": "#08090f",
        "console_fg": "#00f0ff",
        "tree_bg": "#151824",
        "tree_fg": "#e0f8ff",
        "tree_selected": "#2b324e",
        "tree_even": "#0d0f18",
        "entry_bg": "#08090f",
        "entry_fg": "#e0f8ff",
    }

    # 4. Emerald Forest Dark
    EMERALD = {
        "name": "emerald",
        "bg": "#0f1715",
        "surface": "#162320",
        "surface_alt": "#203430",
        "surface_active": "#2d4842",
        "border": "#345c53",
        "text": "#dcf5ee",
        "text_dim": "#8eb0a6",
        "text_highlight": "#10b981",
        "primary": "#10b981",
        "primary_hover": "#34d399",
        "primary_text": "#06281e",
        "success": "#10b981",
        "success_bg": "#0d3127",
        "danger": "#f43f5e",
        "danger_bg": "#3e101a",
        "warning": "#fbbf24",
        "warning_bg": "#3c2e07",
        "info": "#38bdf8",
        "card_bg": "#162320",
        "console_bg": "#090e0d",
        "console_fg": "#dcf5ee",
        "tree_bg": "#162320",
        "tree_fg": "#dcf5ee",
        "tree_selected": "#2d4842",
        "tree_even": "#0f1715",
        "entry_bg": "#090e0d",
        "entry_fg": "#dcf5ee",
    }

    PRESETS = {
        "Dark Obsidian": DARK,
        "Clean Light": LIGHT,
        "Cyberpunk Neon": CYBERPUNK,
        "Emerald Forest": EMERALD,
    }


def apply_theme(root: tk.Tk, theme_dict: dict):
    """Applies modern styling to ttk widgets based on the theme dictionary."""
    t = theme_dict
    root.configure(bg=t["bg"])

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    font_main = ("Segoe UI", 10)
    font_bold = ("Segoe UI", 10, "bold")
    font_heading = ("Segoe UI", 12, "bold")
    font_title = ("Segoe UI", 14, "bold")

    # Frames
    style.configure("TFrame", background=t["bg"])
    style.configure("Surface.TFrame", background=t["surface"])
    style.configure("Card.TFrame", background=t["card_bg"], relief="flat")
    style.configure("Sidebar.TFrame", background=t["surface"])

    # Labels
    style.configure("TLabel", background=t["bg"], foreground=t["text"], font=font_main)
    style.configure(
        "Surface.TLabel", background=t["surface"], foreground=t["text"], font=font_main
    )
    style.configure(
        "Card.TLabel", background=t["card_bg"], foreground=t["text"], font=font_main
    )
    style.configure(
        "Heading.TLabel",
        background=t["bg"],
        foreground=t["text_highlight"],
        font=font_heading,
    )
    style.configure(
        "Title.TLabel", background=t["bg"], foreground=t["primary"], font=font_title
    )
    style.configure(
        "Dim.TLabel", background=t["bg"], foreground=t["text_dim"], font=("Segoe UI", 9)
    )
    style.configure(
        "DimCard.TLabel",
        background=t["card_bg"],
        foreground=t["text_dim"],
        font=("Segoe UI", 9),
    )

    # Standard Buttons
    style.configure(
        "TButton",
        background=t["surface_alt"],
        foreground=t["text"],
        bordercolor=t["border"],
        darkcolor=t["surface_alt"],
        lightcolor=t["surface_alt"],
        focuscolor="none",
        relief="flat",
        padding=(12, 6),
        font=font_bold,
    )
    style.map(
        "TButton",
        background=[("active", t["surface_active"]), ("pressed", t["surface_alt"])],
        foreground=[("active", t["text_highlight"])],
    )

    # Primary Action Button
    style.configure(
        "Primary.TButton",
        background=t["primary"],
        foreground=t["primary_text"],
        bordercolor=t["primary"],
        darkcolor=t["primary"],
        lightcolor=t["primary"],
        relief="flat",
        padding=(14, 7),
        font=font_bold,
    )
    style.map(
        "Primary.TButton",
        background=[("active", t["primary_hover"])],
    )

    # Danger Button
    style.configure(
        "Danger.TButton",
        background=t["danger"],
        foreground="#ffffff",
        bordercolor=t["danger"],
        relief="flat",
        padding=(12, 6),
        font=font_bold,
    )

    # Sidebar Navigation Button
    style.configure(
        "Nav.TButton",
        background=t["surface"],
        foreground=t["text"],
        anchor="w",
        relief="flat",
        padding=(12, 9),
        font=font_main,
    )
    style.map(
        "Nav.TButton",
        background=[("active", t["surface_active"])],
        foreground=[("active", t["primary"])],
    )

    style.configure(
        "NavActive.TButton",
        background=t["surface_active"],
        foreground=t["primary"],
        anchor="w",
        relief="flat",
        padding=(12, 9),
        font=font_bold,
    )

    # Entry & Combobox
    style.configure(
        "TEntry",
        fieldbackground=t["entry_bg"],
        foreground=t["entry_fg"],
        insertcolor=t["text"],
        bordercolor=t["border"],
        lightcolor=t["border"],
        darkcolor=t["border"],
        padding=6,
    )

    style.configure(
        "TCombobox",
        fieldbackground=t["entry_bg"],
        background=t["surface_alt"],
        foreground=t["entry_fg"],
        bordercolor=t["border"],
        arrowcolor=t["text"],
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", t["entry_bg"])],
        selectbackground=[("readonly", t["primary"])],
    )

    # Checkbutton & Radiobutton
    style.configure(
        "TCheckbutton", background=t["bg"], foreground=t["text"], font=font_main
    )
    style.configure(
        "TRadiobutton", background=t["bg"], foreground=t["text"], font=font_main
    )
    style.configure(
        "Card.TCheckbutton",
        background=t["card_bg"],
        foreground=t["text"],
        font=font_main,
    )
    style.configure(
        "Card.TRadiobutton",
        background=t["card_bg"],
        foreground=t["text"],
        font=font_main,
    )

    # LabelFrames
    style.configure(
        "TLabelframe",
        background=t["card_bg"],
        bordercolor=t["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=t["card_bg"],
        foreground=t["primary"],
        font=font_bold,
    )

    # Treeview (Data Table)
    style.configure(
        "Treeview",
        background=t["tree_bg"],
        foreground=t["tree_fg"],
        fieldbackground=t["tree_bg"],
        bordercolor=t["border"],
        font=font_main,
        rowheight=28,
    )
    style.map(
        "Treeview",
        background=[("selected", t["tree_selected"])],
        foreground=[("selected", t["text_highlight"])],
    )
    style.configure(
        "Treeview.Heading",
        background=t["surface_alt"],
        foreground=t["text"],
        font=font_bold,
        padding=6,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", t["surface_active"])])

    # Notebook (Tabs)
    style.configure(
        "TNotebook",
        background=t["bg"],
        tabmargins=[2, 5, 2, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background=t["surface_alt"],
        foreground=t["text_dim"],
        padding=[14, 6],
        font=font_bold,
        relief="flat",
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", t["surface"]), ("active", t["surface_active"])],
        foreground=[("selected", t["primary"]), ("active", t["text"])],
    )

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=t["surface_alt"],
        bordercolor=t["bg"],
        troughcolor=t["bg"],
        relief="flat",
    )

    # Separator
    style.configure("TSeparator", background=t["border"])
