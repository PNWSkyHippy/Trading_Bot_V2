"""
Modal Dialog and Input Box System for QuickTk.
Provides synchronous popup dialogs (text, numbers, choices, confirmations, and full multi-field forms)
that wait for user input and return results or None if cancelled.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .forms import FormPanel
from .theme import Theme, apply_theme


class ModalDialog(tk.Toplevel):
    """Base modal dialog with keyboard shortcuts (Enter=OK, Escape=Cancel) and window grab."""

    def __init__(
        self,
        parent: Optional[tk.Widget] = None,
        title: str = "Input",
        theme: dict = None,
        min_size: Tuple[int, int] = (360, 160),
    ):
        super().__init__(parent)
        self.parent = parent
        self.theme = theme or Theme.DARK
        self.result = None

        self.title(title)
        self.minsize(min_size[0], min_size[1])
        self.resizable(False, False)
        self.configure(bg=self.theme.get("bg", "#181825"))

        if parent:
            self.transient(parent.winfo_toplevel())

        # Center on parent or screen
        self._center_window(min_size[0], min_size[1])

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self, style="Surface.TFrame", padding=16)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)

        # Bind keyboard shortcuts
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        if self.parent:
            p_root = self.parent.winfo_toplevel()
            x = p_root.winfo_x() + (p_root.winfo_width() // 2) - (width // 2)
            y = p_root.winfo_y() + (p_root.winfo_height() // 2) - (height // 2)
        else:
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def show(self) -> Any:
        """Makes dialog modal, grabs input focus, and blocks until closed."""
        self.grab_set()
        self.focus_set()
        self.wait_window(self)
        return self.result

    def on_ok(self):
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


def prompt_text(
    title: str = "Input Required",
    prompt: str = "Please enter a value:",
    default: str = "",
    password: bool = False,
    parent: Optional[tk.Widget] = None,
    theme: Optional[dict] = None,
) -> Optional[str]:
    """Pops up a single-line text input dialog. Returns string or None if cancelled."""
    dlg = ModalDialog(parent=parent, title=title, theme=theme, min_size=(380, 160))

    lbl = ttk.Label(dlg.main_frame, text=prompt, style="Heading.TLabel")
    lbl.grid(row=0, column=0, sticky="w", pady=(0, 8))

    var = tk.StringVar(value=default)
    entry = ttk.Entry(dlg.main_frame, textvariable=var, show="*" if password else "")
    entry.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    entry.focus_set()
    entry.select_range(0, tk.END)

    btn_box = ttk.Frame(dlg.main_frame, style="Surface.TFrame")
    btn_box.grid(row=2, column=0, sticky="e")

    def _ok():
        dlg.result = var.get()
        dlg.destroy()

    cancel_btn = ttk.Button(btn_box, text="Cancel", command=dlg.on_cancel)
    cancel_btn.pack(side="right", padx=(6, 0))
    ok_btn = ttk.Button(btn_box, text="OK", style="Primary.TButton", command=_ok)
    ok_btn.pack(side="right")

    dlg.on_ok = _ok
    return dlg.show()


def prompt_number(
    title: str = "Numeric Input",
    prompt: str = "Please enter a number:",
    default: Union[int, float] = 0,
    is_float: bool = False,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    step: float = 1,
    parent: Optional[tk.Widget] = None,
    theme: Optional[dict] = None,
) -> Optional[Union[int, float]]:
    """Pops up a numeric spinbox dialog. Returns number or None if cancelled."""
    dlg = ModalDialog(parent=parent, title=title, theme=theme, min_size=(380, 160))

    lbl = ttk.Label(dlg.main_frame, text=prompt, style="Heading.TLabel")
    lbl.grid(row=0, column=0, sticky="w", pady=(0, 8))

    var = (
        tk.DoubleVar(value=float(default))
        if is_float
        else tk.IntVar(value=int(default))
    )
    from_ = min_val if min_val is not None else -999999999
    to = max_val if max_val is not None else 999999999

    spin = ttk.Spinbox(
        dlg.main_frame, from_=from_, to=to, increment=step, textvariable=var
    )
    spin.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    spin.focus_set()

    btn_box = ttk.Frame(dlg.main_frame, style="Surface.TFrame")
    btn_box.grid(row=2, column=0, sticky="e")

    def _ok():
        try:
            val = float(var.get()) if is_float else int(var.get())
            dlg.result = val
            dlg.destroy()
        except Exception:
            messagebox.showerror(
                "Invalid Input", "Please enter a valid number.", parent=dlg
            )

    cancel_btn = ttk.Button(btn_box, text="Cancel", command=dlg.on_cancel)
    cancel_btn.pack(side="right", padx=(6, 0))
    ok_btn = ttk.Button(btn_box, text="OK", style="Primary.TButton", command=_ok)
    ok_btn.pack(side="right")

    dlg.on_ok = _ok
    return dlg.show()


def prompt_choice(
    title: str = "Select Option",
    prompt: str = "Please choose an option:",
    options: Optional[List[str]] = None,
    default: Optional[str] = None,
    parent: Optional[tk.Widget] = None,
    theme: Optional[dict] = None,
) -> Optional[str]:
    """Pops up a dropdown selection dialog. Returns chosen string or None."""
    opts = options or []
    dlg = ModalDialog(parent=parent, title=title, theme=theme, min_size=(380, 160))

    lbl = ttk.Label(dlg.main_frame, text=prompt, style="Heading.TLabel")
    lbl.grid(row=0, column=0, sticky="w", pady=(0, 8))

    var = tk.StringVar(
        value=default if default is not None else (opts[0] if opts else "")
    )
    combo = ttk.Combobox(
        dlg.main_frame, textvariable=var, values=opts, state="readonly"
    )
    combo.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    combo.focus_set()

    btn_box = ttk.Frame(dlg.main_frame, style="Surface.TFrame")
    btn_box.grid(row=2, column=0, sticky="e")

    def _ok():
        dlg.result = var.get()
        dlg.destroy()

    cancel_btn = ttk.Button(btn_box, text="Cancel", command=dlg.on_cancel)
    cancel_btn.pack(side="right", padx=(6, 0))
    ok_btn = ttk.Button(btn_box, text="OK", style="Primary.TButton", command=_ok)
    ok_btn.pack(side="right")

    dlg.on_ok = _ok
    return dlg.show()


def prompt_confirm(
    title: str = "Confirmation",
    message: str = "Are you sure you want to proceed?",
    parent: Optional[tk.Widget] = None,
) -> bool:
    """Standard confirmation popup. Returns True or False."""
    return messagebox.askyesno(title, message, parent=parent)


def prompt_form(
    title: str,
    form_builder_fn: Callable[[FormPanel], None],
    parent: Optional[tk.Widget] = None,
    theme: Optional[dict] = None,
    size: Tuple[int, int] = (460, 360),
    ok_text: str = "Submit",
    cancel_text: str = "Cancel",
) -> Optional[Dict[str, Any]]:
    """
    Pops up a full multi-field FormPanel inside a modal dialog window.
    Accepts a builder function that configures the form inputs.
    Returns a clean dictionary of values or None if cancelled.

    Example:
        def build_fields(form):
            form.add_text("db_name", "Database Name", default="trades.db")
            form.add_dropdown("strategy", "Strategy", ["All", "Scalp", "Breakout"])
            form.add_number("limit", "Row Limit", default=500)
            form.add_checkbox("export_csv", "Auto-Export to CSV", default=True)

        data = prompt_form("Query Settings", build_fields, parent=self)
        if data:
            print("User entered:", data)
    """
    dlg = ModalDialog(parent=parent, title=title, theme=theme, min_size=size)
    dlg.geometry(f"{size[0]}x{size[1]}")
    dlg.resizable(True, True)

    dlg.main_frame.columnconfigure(0, weight=1)
    dlg.main_frame.rowconfigure(0, weight=1)

    # Embed FormPanel
    form = FormPanel(dlg.main_frame, theme=dlg.theme)
    form.grid(row=0, column=0, sticky="nsew")

    form_builder_fn(form)

    # Bottom OK / Cancel action buttons
    btn_box = ttk.Frame(dlg.main_frame, style="Surface.TFrame")
    btn_box.grid(row=1, column=0, sticky="e", pady=(10, 0))

    def _ok():
        dlg.result = form.get_values()
        dlg.destroy()

    cancel_btn = ttk.Button(btn_box, text=cancel_text, command=dlg.on_cancel)
    cancel_btn.pack(side="right", padx=(6, 0))
    ok_btn = ttk.Button(btn_box, text=ok_text, style="Primary.TButton", command=_ok)
    ok_btn.pack(side="right")

    dlg.on_ok = _ok
    return dlg.show()
