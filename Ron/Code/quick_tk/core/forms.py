"""
Form components and input wrappers for QuickTk.
Handles automatic variable binding, multi-column row layouts, custom widgets, and value extraction.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import customtkinter as ctk

    HAS_CTK = True
except ImportError:
    ctk = None
    HAS_CTK = False


class MultiSelectDropdown(ttk.Frame):
    """
    A compact multi-select combobox dropdown with checkboxes,
    search filtering, and Select All / Clear All toggles.
    Designed for uncluttered forms with large option lists.
    """

    def __init__(
        self,
        parent: tk.Widget,
        options: List[str],
        default: Optional[List[str]] = None,
        placeholder: str = "Select options...",
        max_display: int = 2,
        theme: Optional[dict] = None,
        on_change: Optional[Callable[[List[str]], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        self.options = list(options)
        self.placeholder = placeholder
        self.max_display = max_display
        self.theme = theme or {}
        self.on_change = on_change

        self.selected_vars: Dict[str, tk.BooleanVar] = {
            opt: tk.BooleanVar(value=(opt in (default or []))) for opt in self.options
        }
        self.summary_var = tk.StringVar()

        self.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(
            self, textvariable=self.summary_var, state="readonly", cursor="hand2"
        )
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Button-1>", lambda e: self.toggle_popup())

        self.btn = ttk.Button(self, text="▼", width=3, command=self.toggle_popup)
        self.btn.grid(row=0, column=1, sticky="e", padx=(2, 0))

        self.popup: Optional[tk.Toplevel] = None
        self._filter_var = tk.StringVar()
        self._check_widgets: Dict[str, ttk.Checkbutton] = {}
        self._update_summary()

    def _update_summary(self):
        sel = self.get()
        if not sel:
            self.summary_var.set(self.placeholder)
        elif len(sel) == len(self.options) and len(self.options) > 1:
            self.summary_var.set(f"All selected ({len(sel)})")
        elif len(sel) <= self.max_display:
            self.summary_var.set(", ".join(sel))
        else:
            shown = ", ".join(sel[: self.max_display])
            rem = len(sel) - self.max_display
            self.summary_var.set(f"{shown} (+{rem} more)")

    def get(self) -> List[str]:
        """Returns the list of currently selected string values."""
        return [opt for opt in self.options if self.selected_vars[opt].get()]

    def set(self, values: List[str]):
        """Sets the selected items programmatically."""
        val_set = set(values or [])
        for opt, var in self.selected_vars.items():
            var.set(opt in val_set)
        self._update_summary()
        if self.on_change:
            self.on_change(self.get())

    def clear_all(self):
        """Deselects all options."""
        for var in self.selected_vars.values():
            var.set(False)
        self._on_changed()

    clear = clear_all

    def select_all(self):
        """Selects all options."""
        for var in self.selected_vars.values():
            var.set(True)
        self._on_changed()

    all = select_all

    def set_options(self, new_options: List[str], default: Optional[List[str]] = None):
        """Dynamically updates the available options list."""
        self.options = list(new_options)
        self.selected_vars = {
            opt: tk.BooleanVar(value=(opt in (default or []))) for opt in self.options
        }
        self._update_summary()
        if self.popup and self.popup.winfo_exists():
            self._close_popup()

    def toggle_popup(self):
        if self.popup and self.popup.winfo_exists():
            self._close_popup()
        else:
            self.show_popup()

    def _close_popup(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
        self.popup = None

    def show_popup(self):
        self._close_popup()
        root = self.winfo_toplevel()
        self.popup = tk.Toplevel(root)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)

        # Geometry calculation
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
        w = max(240, self.winfo_width())
        h = min(320, 75 + len(self.options) * 26)

        # Screen boundary clamping (flip up if near bottom of screen)
        screen_h = root.winfo_screenheight()
        if y + h > screen_h - 40:
            y = max(10, self.entry.winfo_rooty() - h - 2)

        self.popup.geometry(f"{w}x{h}+{x}+{y}")

        bg = self.theme.get("surface_bg", "#1e1e2e")
        fg = self.theme.get("text", "#cdd6f4")
        border = self.theme.get("border", "#45475a")

        container = tk.Frame(
            self.popup, bg=bg, highlightbackground=border, highlightthickness=1
        )
        container.pack(fill="both", expand=True)

        # Live Search / Filter Bar (if 6 or more options)
        if len(self.options) >= 6:
            search_frame = tk.Frame(container, bg=bg)
            search_frame.pack(fill="x", padx=6, pady=(6, 2))
            search_entry = ttk.Entry(search_frame, textvariable=self._filter_var)
            search_entry.pack(fill="x", expand=True)
            self._filter_var.trace_add("write", self._apply_filter)

        # Quick Actions Bar
        act_frame = tk.Frame(container, bg=bg)
        act_frame.pack(fill="x", padx=6, pady=4)
        ttk.Button(act_frame, text="All", width=5, command=self.select_all).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(act_frame, text="None", width=5, command=self.clear_all).pack(
            side="left"
        )

        self._count_lbl = tk.Label(
            act_frame,
            text=f"{len(self.get())}/{len(self.options)} selected",
            bg=bg,
            fg=fg,
            font=("Segoe UI", 9),
        )
        self._count_lbl.pack(side="right", padx=(0, 4))

        # Scrollable Checklist Canvas
        canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=bg)

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(6, 2), pady=(2, 6))
        if len(self.options) > 7:
            scrollbar.pack(side="right", fill="y", pady=(2, 6))

        # Windows mousewheel binding scoped to popup elements
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        self.popup.bind("<MouseWheel>", _on_mousewheel)

        # Checkbuttons
        self._check_widgets.clear()
        for opt in self.options:
            cb = ttk.Checkbutton(
                scroll_frame,
                text=opt,
                variable=self.selected_vars[opt],
                style="TCheckbutton",
                command=self._on_changed,
            )
            cb.pack(anchor="w", fill="x", padx=4, pady=2)
            cb.bind("<MouseWheel>", _on_mousewheel)
            self._check_widgets[opt] = cb

        root.bind_all("<Button-1>", self._on_root_click, add="+")
        self.popup.bind("<Escape>", lambda e: self._close_popup())

    def _apply_filter(self, *args):
        query = self._filter_var.get().lower().strip()
        for opt, cb in self._check_widgets.items():
            if not query or query in opt.lower():
                cb.pack(anchor="w", fill="x", padx=4, pady=2)
            else:
                cb.pack_forget()

    def _on_changed(self):
        self._update_summary()
        if hasattr(self, "_count_lbl") and self._count_lbl.winfo_exists():
            self._count_lbl.config(
                text=f"{len(self.get())}/{len(self.options)} selected"
            )
        if self.on_change:
            self.on_change(self.get())

    def _on_root_click(self, event):
        if not self.popup or not self.popup.winfo_exists():
            return
        x, y = event.x_root, event.y_root
        px, py = self.popup.winfo_rootx(), self.popup.winfo_rooty()
        pw, ph = self.popup.winfo_width(), self.popup.winfo_height()
        sx, sy = self.winfo_rootx(), self.winfo_rooty()
        sw, sh = self.winfo_width(), self.winfo_height()

        if not (
            (px <= x <= px + pw and py <= y <= py + ph)
            or (sx <= x <= sx + sw and sy <= y <= sy + sh)
        ):
            self._close_popup()


class FormPanel(ttk.Frame):
    """
    A declarative form container that automatically manages labels, inputs,
    variable bindings, multi-column layouts, and value extraction without manual grid calculations.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: Optional[str] = None,
        padding: int = 12,
        theme: dict = None,
        **kwargs,
    ):
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        self.theme = theme or {}
        self._fields: Dict[
            str, Tuple[str, Any, Any]
        ] = {}  # name -> (type, widget, getter/setter_or_var)
        self._callbacks: Dict[str, List[Callable]] = {}
        self._slider_timers: Dict[str, Any] = {}
        self._row_count = 0

        self.columnconfigure(0, weight=1)

        # Optional Card/Title Header
        if title:
            header = ttk.Label(self, text=title, style="Heading.TLabel")
            header.grid(
                row=self._row_count,
                column=0,
                sticky="w",
                padx=padding,
                pady=(padding, 10),
            )
            self._row_count += 1

        self.inner_frame = ttk.Frame(self, style="Surface.TFrame")
        self.inner_frame.grid(
            row=self._row_count,
            column=0,
            sticky="nsew",
            padx=padding,
            pady=(0, padding),
        )
        self.inner_frame.columnconfigure(0, weight=1)
        self._row_count += 1
        self._inner_row = 0

    def _add_field_container(
        self, label_text: str, parent: Optional[tk.Widget] = None
    ) -> ttk.Frame:
        """Helper to create a standard labeled container row."""
        p = parent if parent is not None else self.inner_frame
        frame = ttk.Frame(p, style="Surface.TFrame")
        if parent is None:
            frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(4, 6))
            frame.columnconfigure(0, weight=1)
            self._inner_row += 1

        if label_text:
            lbl = ttk.Label(frame, text=label_text, style="Surface.TLabel")
            lbl.grid(row=0, column=0, sticky="w", pady=(0, 2))

        return frame

    def add_text(
        self,
        name: str,
        label: str,
        default: str = "",
        placeholder: str = "",
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ) -> ttk.Entry:
        """Adds a single-line text input field."""
        container = self._add_field_container(label, parent=parent)
        var = tk.StringVar(value=default)

        entry = ttk.Entry(container, textvariable=var)
        entry.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)

        if on_change:
            var.trace_add("write", lambda *args: on_change(var.get()))

        self._fields[name] = ("text", entry, var)
        return entry

    def add_text_area(
        self,
        name: str,
        label: str,
        default: str = "",
        height: int = 4,
        parent: Optional[tk.Widget] = None,
    ) -> tk.Text:
        """Adds a multi-line text area."""
        container = self._add_field_container(label, parent=parent)
        bg = self.theme.get("entry_bg", "#11111b")
        fg = self.theme.get("entry_fg", "#cdd6f4")

        txt = tk.Text(
            container,
            height=height,
            bg=bg,
            fg=fg,
            insertbackground=fg,
            relief="flat",
            font=("Segoe UI", 10),
        )
        txt.insert("1.0", default)
        txt.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)

        def _get():
            return txt.get("1.0", "end-1c")

        def _set(v):
            txt.delete("1.0", "end")
            txt.insert("1.0", str(v))

        self._fields[name] = ("custom", txt, (_get, _set))
        return txt

    def add_number(
        self,
        name: str,
        label: str,
        default: Union[int, float] = 0,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        step: float = 1,
        is_float: bool = False,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[Union[int, float]], None]] = None,
    ) -> ttk.Spinbox:
        """Adds a numeric spinbox field."""
        container = self._add_field_container(label, parent=parent)
        var = tk.DoubleVar(value=default) if is_float else tk.IntVar(value=int(default))

        from_ = min_val if min_val is not None else -999999999
        to = max_val if max_val is not None else 999999999

        spin = ttk.Spinbox(
            container,
            from_=from_,
            to=to,
            increment=step,
            textvariable=var,
        )
        spin.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)

        if on_change:
            var.trace_add(
                "write", lambda *args: self._safe_num_callback(var, on_change, is_float)
            )

        self._fields[name] = ("number", spin, var)
        return spin

    def _safe_num_callback(self, var: tk.Variable, callback: Callable, is_float: bool):
        try:
            val = float(var.get()) if is_float else int(var.get())
            callback(val)
        except Exception:
            pass

    def add_slider(
        self,
        name: str,
        label: str,
        min_val: float = 0,
        max_val: float = 100,
        default: float = 0,
        step: float = 1,
        show_value: bool = True,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[float], None]] = None,
    ) -> ttk.Scale:
        """Adds a slider / scale with a one-shot final callback after user interaction completes."""
        container = self._add_field_container(label, parent=parent)
        is_int = (
            (step >= 1) and (float(step).is_integer()) and (float(min_val).is_integer())
        )
        var = tk.DoubleVar(value=default)

        slider_frame = ttk.Frame(container, style="Surface.TFrame")
        slider_frame.grid(row=1, column=0, sticky="ew")
        slider_frame.columnconfigure(0, weight=1)

        scale = ttk.Scale(
            slider_frame,
            from_=min_val,
            to=max_val,
            variable=var,
            orient="horizontal",
        )
        scale.grid(row=0, column=0, sticky="ew", padx=(0, 8 if show_value else 0))

        def _normalize_value(raw_value):
            raw = float(raw_value)
            raw = max(min_val, min(max_val, raw))
            if is_int:
                raw = int(round(raw))
            return raw

        def _fire_callback(value):
            if not on_change:
                return
            try:
                on_change(value)
            except Exception:
                pass

        def _schedule_callback(value):
            timer = self._slider_timers.get(name)
            if timer is not None:
                try:
                    self.after_cancel(timer)
                except Exception:
                    pass
            self._slider_timers[name] = self.after(150, lambda: _fire_callback(value))

        def _commit_from_scale(event=None):
            val = _normalize_value(var.get())
            if var.get() != val:
                var.set(val)
            _schedule_callback(val)

        scale.bind("<ButtonRelease-1>", _commit_from_scale)
        scale.bind("<FocusOut>", _commit_from_scale)

        if show_value:
            spin = ttk.Spinbox(
                slider_frame,
                from_=min_val,
                to=max_val,
                increment=step,
                textvariable=var,
                width=6,
            )
            spin.grid(row=0, column=1, sticky="e")

            def _commit_spin(event=None):
                try:
                    raw = spin.get()
                    val = _normalize_value(raw)
                    var.set(val)
                    _schedule_callback(val)
                except Exception:
                    pass

            spin.bind("<Return>", _commit_spin)
            spin.bind("<FocusOut>", _commit_spin)

        self._fields[name] = ("slider", scale, var)
        return scale

    def add_dropdown(
        self,
        name: str,
        label: str,
        options: List[str],
        default: Optional[str] = None,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ) -> ttk.Combobox:
        """Adds a dropdown combobox."""
        container = self._add_field_container(label, parent=parent)
        default_val = (
            default if default is not None else (options[0] if options else "")
        )
        var = tk.StringVar(value=default_val)

        combo = ttk.Combobox(
            container,
            textvariable=var,
            values=options,
            state="readonly",
        )
        combo.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)

        if on_change:
            combo.bind("<<ComboboxSelected>>", lambda e: on_change(var.get()))

        self._fields[name] = ("dropdown", combo, var)
        return combo

    def add_multi_select(
        self,
        name: str,
        label: str,
        options: List[str],
        default: Optional[List[str]] = None,
        placeholder: str = "Select options...",
        max_display: int = 2,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[List[str]], None]] = None,
    ) -> MultiSelectDropdown:
        """
        Adds a compact, multi-selectable dropdown combobox with checkboxes,
        instant search/filter, and 'Select All' / 'Clear All' quick toggles.
        Keeps menus completely uncluttered while supporting single, multiple, or all selections.
        """
        container = self._add_field_container(label, parent=parent)
        ms = MultiSelectDropdown(
            container,
            options=options,
            default=default,
            placeholder=placeholder,
            max_display=max_display,
            theme=self.theme,
            on_change=on_change,
        )
        ms.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)

        self._fields[name] = ("multi_select", ms, ms)
        return ms

    def add_radio(
        self,
        name: str,
        label: str,
        options: List[str],
        default: Optional[str] = None,
        horizontal: bool = True,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ) -> ttk.Frame:
        """Adds radio button choices."""
        container = self._add_field_container(label, parent=parent)
        default_val = (
            default if default is not None else (options[0] if options else "")
        )
        var = tk.StringVar(value=default_val)

        radio_frame = ttk.Frame(container, style="Surface.TFrame")
        radio_frame.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        for idx, opt in enumerate(options):
            rb = ttk.Radiobutton(
                radio_frame,
                text=opt,
                value=opt,
                variable=var,
                style="TRadiobutton",
                command=(lambda v=var, cb=on_change: cb(v.get()))
                if on_change
                else None,
            )
            if horizontal:
                rb.grid(row=0, column=idx, sticky="w", padx=(0, 10))
            else:
                rb.grid(row=idx, column=0, sticky="w", pady=(2, 2))

        self._fields[name] = ("radio", radio_frame, var)
        return radio_frame

    def add_checkbox(
        self,
        name: str,
        label: Optional[str] = None,
        default: bool = False,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[bool], None]] = None,
        command: Optional[Callable] = None,
        **kwargs,
    ) -> ttk.Checkbutton:
        """Adds a boolean checkbutton with set/get helper methods."""
        callback = (
            command
            or on_change
            or kwargs.pop("commande", None)
            or kwargs.pop("command", None)
            or kwargs.pop("on_change", None)
            or kwargs.pop("callback", None)
        )
        display_label = label if label is not None else name
        field_name = name if label is not None else name.lower().replace(" ", "_")
        container = self._add_field_container("", parent=parent)
        var = tk.BooleanVar(value=default)

        def _on_toggle():
            if callback:
                val = bool(var.get())
                try:
                    callback(val)
                except TypeError:
                    try:
                        callback()
                    except Exception:
                        pass

        cb = ttk.Checkbutton(
            container,
            text=display_label,
            variable=var,
            style="TCheckbutton",
            command=_on_toggle if callback else None,
            **kwargs,
        )
        cb.grid(row=0, column=0, sticky="w", pady=(2, 2))

        cb.var = var
        orig_var_set = var.set

        def _safe_set(v):
            try:
                orig_var_set(bool(v))
            except Exception:
                pass

        cb.set = _safe_set
        cb.get = var.get

        self._fields[field_name] = ("checkbox", cb, var)
        return cb

    # Aliases for add_checkbox
    addCheckBox = add_checkbox
    CheckBox = add_checkbox

    def add_file_picker(
        self,
        name: str,
        label: str,
        default: str = "",
        mode: str = "open",  # "open", "save", "directory"
        filetypes: Optional[List[Tuple[str, str]]] = None,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ) -> ttk.Frame:
        """Adds a file/directory picker with Browse... dialog."""
        container = self._add_field_container(label, parent=parent)
        var = tk.StringVar(value=default)

        box = ttk.Frame(container, style="Surface.TFrame")
        box.grid(row=1, column=0, sticky="ew")
        box.columnconfigure(0, weight=1)

        entry = ttk.Entry(box, textvariable=var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        def _browse():
            ft = filetypes or [("All Files", "*.*")]
            if mode == "open":
                path = filedialog.askopenfilename(filetypes=ft)
            elif mode == "save":
                path = filedialog.asksaveasfilename(filetypes=ft)
            elif mode == "directory":
                path = filedialog.askdirectory()
            else:
                path = ""

            if path:
                var.set(path)
                if on_change:
                    on_change(path)

        btn = ttk.Button(box, text="Browse...", command=_browse)
        btn.grid(row=0, column=1, sticky="e")

        if on_change:
            var.trace_add("write", lambda *args: on_change(var.get()))

        self._fields[name] = ("file_picker", box, var)
        return box

    def add_output_file_picker(
        self,
        name: str,
        label: str,
        default: str = "",
        default_filename: str = "output.txt",
        default_extension: str = ".txt",
        filetypes: Optional[List[Tuple[str, str]]] = None,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ) -> ttk.Frame:
        """
        Adds an output destination picker that:
        1. Lets user select target directory and file name.
        2. Validates the path and write permissions with a ghost file probe.
        3. Prompts overwrite confirmation if the file already exists.
        4. Fills the entry only if verified, otherwise sets user back to retry.
        """
        container = self._add_field_container(label, parent=parent)
        var = tk.StringVar(value=default)

        box = ttk.Frame(container, style="Surface.TFrame")
        box.grid(row=1, column=0, sticky="ew")
        box.columnconfigure(0, weight=1)

        entry = ttk.Entry(box, textvariable=var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        def _browse_output():
            ft = filetypes or [("All Files", "*.*")]

            # Initial setup for save dialog
            init_dir = os.path.dirname(var.get()) if var.get() else ""
            init_file = os.path.basename(var.get()) if var.get() else default_filename

            chosen_path = filedialog.asksaveasfilename(
                initialdir=init_dir or None,
                initialfile=init_file,
                defaultextension=default_extension,
                filetypes=ft,
                confirmoverwrite=False,  # Handle overwrite manually with custom validation
                title=f"Select {label}",
            )

            if not chosen_path:
                return  # User closed/cancelled dialog

            # 1. Check folder directory validity
            target_dir = os.path.dirname(chosen_path)
            if not os.path.exists(target_dir):
                messagebox.showerror(
                    "Invalid Directory", f"The directory does not exist:\n{target_dir}"
                )
                return

            # 2. Check for file existence & prompt overwrite
            if os.path.exists(chosen_path):
                proceed = messagebox.askyesno(
                    "File Exists",
                    f"The file already exists:\n\n{chosen_path}\n\nDo you wish to overwrite it?",
                    icon="warning",
                )
                if not proceed:
                    messagebox.showinfo(
                        "Cancelled",
                        "File selection cancelled. Please choose another file name.",
                    )
                    return

                # Test writeability on existing file (e.g. check if locked by Excel/another process)
                try:
                    with open(chosen_path, "a"):
                        pass
                except (IOError, PermissionError, OSError) as err:
                    messagebox.showerror(
                        "Permission / Lock Error",
                        f"Cannot write to this file (it may be locked by another program):\n\n{err}",
                    )
                    return
            else:
                # 3. Ghost creation test to verify folder write permissions
                try:
                    with open(chosen_path, "a"):
                        pass
                    # Remove ghost file immediately so we leave no artifacts
                    if os.path.exists(chosen_path):
                        os.remove(chosen_path)
                except (IOError, PermissionError, OSError) as err:
                    messagebox.showerror(
                        "Cannot Write to Folder",
                        f"You do not have write permissions for this folder:\n\n{target_dir}\n\nError: {err}",
                    )
                    return

            # 4. Verified & approved: fill the path into the entry box
            var.set(chosen_path)
            if on_change:
                on_change(chosen_path)

        btn = ttk.Button(box, text="Save As...", command=_browse_output)
        btn.grid(row=0, column=1, sticky="e")

        if on_change:
            var.trace_add("write", lambda *args: on_change(var.get()))

        self._fields[name] = ("output_file_picker", box, var)
        return box

    def add_custom_widget(
        self,
        name: str,
        label: str,
        widget_factory: Callable[[tk.Widget], tk.Widget],
        get_value_fn: Callable[[tk.Widget], Any],
        set_value_fn: Optional[Callable[[tk.Widget, Any], None]] = None,
        parent: Optional[tk.Widget] = None,
    ) -> tk.Widget:
        """
        Allows dropping ANY custom widget (e.g. matplotlib canvas, custom dial, custom datepicker)
        into the form with seamless integration into get_values() and set_values().
        """
        container = self._add_field_container(label, parent=parent)
        custom_widget = widget_factory(container)
        custom_widget.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)

        getter = lambda: get_value_fn(custom_widget)
        setter = (
            (lambda v: set_value_fn(custom_widget, v))
            if set_value_fn
            else (lambda v: None)
        )

        self._fields[name] = ("custom", custom_widget, (getter, setter))
        return custom_widget

    def add_row_container(self, columns: int = 2) -> ttk.Frame:
        """Creates a horizontal row container for placing multiple inputs side-by-side."""
        row_frame = ttk.Frame(self.inner_frame, style="Surface.TFrame")
        row_frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(4, 6))
        self._inner_row += 1

        for c in range(columns):
            row_frame.columnconfigure(c, weight=1)

        return row_frame

    # -------------------------------------------------------------
    # CustomTkinter (CTk) Modern Controls Integration
    # -------------------------------------------------------------
    def _require_ctk(self):
        if not HAS_CTK:
            raise ImportError(
                "customtkinter is required to use this modern control. "
                "Install it using: pip install customtkinter"
            )

    def add_ctk_switch(
        self,
        name: str,
        label: str,
        text: str = "",
        default: bool = False,
        on_change: Optional[Callable[[bool], None]] = None,
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern iOS/Win11 style animated toggle switch."""
        self._require_ctk()
        container = self._add_field_container(label, parent=parent)
        sw = ctk.CTkSwitch(
            container,
            text=text,
            command=(lambda: on_change(bool(sw.get()))) if on_change else None,
            **kwargs,
        )
        if default:
            sw.select()
        else:
            sw.deselect()
        sw.grid(row=1, column=0, sticky="w", pady=(2, 4))

        getter = lambda: bool(sw.get())
        setter = lambda v: sw.select() if v else sw.deselect()
        self._fields[name] = ("custom", sw, (getter, setter))
        return sw

    # Aliases
    CTkSwitch = add_ctk_switch
    addCTkSwitch = add_ctk_switch

    def add_ctk_segmented(
        self,
        name: str,
        label: str,
        values: List[str],
        default: Optional[str] = None,
        on_change: Optional[Callable[[str], None]] = None,
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern rounded segmented pill button group (e.g. for timeframes)."""
        self._require_ctk()
        container = self._add_field_container(label, parent=parent)
        seg = ctk.CTkSegmentedButton(
            container,
            values=values,
            command=on_change,
            **kwargs,
        )
        initial_val = (
            default
            if (default and default in values)
            else (values[0] if values else "")
        )
        if initial_val:
            seg.set(initial_val)
        seg.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        container.columnconfigure(0, weight=1)

        getter = lambda: seg.get()
        setter = lambda v: seg.set(v if v is not None else initial_val)
        self._fields[name] = ("custom", seg, (getter, setter))
        return seg

    # Aliases
    CTkSegmentedButton = add_ctk_segmented
    addCTkSegmentedButton = add_ctk_segmented

    def add_ctk_slider(
        self,
        name: str,
        label: str,
        from_: float = 0,
        to: float = 100,
        default: float = 50,
        number_of_steps: Optional[int] = None,
        on_change: Optional[Callable[[float], None]] = None,
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern rounded thumb slider."""
        self._require_ctk()
        container = self._add_field_container(label, parent=parent)
        slider_kwargs = {"from_": from_, "to": to, **kwargs}
        if number_of_steps is not None:
            slider_kwargs["number_of_steps"] = number_of_steps
        sl = ctk.CTkSlider(
            container,
            command=on_change,
            **slider_kwargs,
        )
        sl.set(default)
        sl.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        container.columnconfigure(0, weight=1)

        getter = lambda: sl.get()
        setter = lambda v: sl.set(float(v) if v is not None else default)
        self._fields[name] = ("custom", sl, (getter, setter))
        return sl

    # Aliases
    CTkSlider = add_ctk_slider
    addCTkSlider = add_ctk_slider

    def _parse_progress_val(self, v: Any) -> float:
        """Parses float, int, or string like '45%' or '0.45' into a 0.0 - 1.0 float."""
        if v is None:
            return 0.0
        if isinstance(v, str):
            v_clean = v.replace("%", "").strip()
            try:
                num = float(v_clean)
                return num / 100.0 if num > 1.0 else num
            except ValueError:
                return 0.0
        try:
            num = float(v)
            return num / 100.0 if num > 1.0 else num
        except (ValueError, TypeError):
            return 0.0

    def add_ctk_progress(
        self,
        name: str,
        label: Optional[str] = None,
        default: Union[float, str] = 0.0,
        orientation: str = "horizontal",
        mode: str = "determinate",
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern rounded CustomTkinter progress bar."""
        self._require_ctk()
        display_label = label if label is not None else name
        field_name = name if label is not None else name.lower().replace(" ", "_")
        container = self._add_field_container(display_label, parent=parent)
        pb = ctk.CTkProgressBar(
            container,
            orientation=orientation,
            mode=mode,
            **kwargs,
        )
        init_val = self._parse_progress_val(default)
        pb.set(init_val)
        pb.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        container.columnconfigure(0, weight=1)

        getter = lambda: float(pb.get())
        setter = lambda v: pb.set(self._parse_progress_val(v))
        self._fields[field_name] = ("custom", pb, (getter, setter))
        return pb

    # Aliases
    CTkProgressBar = add_ctk_progress
    addCTkProgressBar = add_ctk_progress
    add_ctk_progressbar = add_ctk_progress

    def add_progress(
        self,
        name: str,
        label: str,
        default: Union[float, str] = 0.0,
        maximum: float = 100.0,
        orientation: str = "horizontal",
        mode: str = "determinate",
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> ttk.Progressbar:
        """Adds a standard ttk.Progressbar."""
        container = self._add_field_container(label, parent=parent)
        pb = ttk.Progressbar(
            container,
            orient=orientation,
            maximum=maximum,
            mode=mode,
            **kwargs,
        )
        init_val = self._parse_progress_val(default) * maximum
        pb["value"] = init_val
        pb.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        container.columnconfigure(0, weight=1)

        getter = lambda: float(pb["value"]) / maximum
        setter = lambda v: pb.configure(value=self._parse_progress_val(v) * maximum)
        self._fields[name] = ("custom", pb, (getter, setter))
        return pb

    add_progressbar = add_progress

    def add_ctk_entry(
        self,
        name: str,
        label: str,
        placeholder: str = "",
        default: str = "",
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern rounded text entry with integrated placeholder text."""
        self._require_ctk()
        container = self._add_field_container(label, parent=parent)
        en = ctk.CTkEntry(
            container,
            placeholder_text=placeholder,
            **kwargs,
        )
        if default:
            en.insert(0, default)
        en.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        container.columnconfigure(0, weight=1)

        def _set(v):
            en.delete(0, "end")
            if v is not None and str(v) != "":
                en.insert(0, str(v))

        getter = lambda: en.get()
        setter = _set
        self._fields[name] = ("custom", en, (getter, setter))
        return en

    # Aliases
    CTkEntry = add_ctk_entry
    addCTkEntry = add_ctk_entry

    def add_ctk_textbox(
        self,
        name: str,
        label: str,
        default: str = "",
        height: int = 100,
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern multi-line text editor with native rounded dark/light styling."""
        self._require_ctk()
        container = self._add_field_container(label, parent=parent)
        tb = ctk.CTkTextbox(
            container,
            height=height,
            **kwargs,
        )
        if default:
            tb.insert("0.0", default)
        tb.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        container.columnconfigure(0, weight=1)

        def _set(v):
            tb.delete("0.0", "end")
            if v is not None and str(v) != "":
                tb.insert("0.0", str(v))

        getter = lambda: tb.get("0.0", "end-1c")
        setter = _set
        self._fields[name] = ("custom", tb, (getter, setter))
        return tb

    # Aliases
    CTkTextbox = add_ctk_textbox
    addCTkTextbox = add_ctk_textbox

    def add_ctk_checkbox(
        self,
        name: Any,
        label: Optional[str] = None,
        text: str = "",
        default: bool = False,
        on_change: Optional[Callable[[bool], None]] = None,
        command: Optional[Callable] = None,
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern rounded checkbox with hover highlights."""
        self._require_ctk()

        # If user passed a widget master as the first argument, e.g. adj_form.CTkCheckBox(cb_frame, "Blur", ...)
        if not isinstance(name, str) and hasattr(name, "winfo_id"):
            parent = name
            name = label if label is not None else (text or "checkbox")
            label = None

        row = kwargs.pop("row", None)
        col = kwargs.pop("column", kwargs.pop("col", None))
        columnspan = kwargs.pop("columnspan", kwargs.pop("colspan", 1))
        grid_sticky = kwargs.pop("sticky", "w")
        grid_padx = kwargs.pop("padx", 4)
        grid_pady = kwargs.pop("pady", (2, 4))

        callback = (
            command
            or on_change
            or kwargs.pop("commande", None)
            or kwargs.pop("command", None)
            or kwargs.pop("on_change", None)
            or kwargs.pop("callback", None)
        )

        if "checkbox_color" in kwargs:
            kwargs.setdefault("checkmark_color", kwargs.pop("checkbox_color"))

        display_text = text or (label if label is not None else str(name))
        field_name = str(name) if label is not None else str(name).lower().replace(" ", "_")

        if parent is not None:
            master = parent
        else:
            master = self._add_field_container("", parent=None)

        def _on_toggle():
            if callback:
                val = bool(cb.get())
                try:
                    callback(val)
                except TypeError:
                    try:
                        callback()
                    except Exception:
                        pass

        cb = ctk.CTkCheckBox(
            master,
            text=display_text,
            command=_on_toggle if callback else None,
            **kwargs,
        )

        orig_set = cb.set

        def _safe_set(v, *args, **kwargs_set):
            try:
                if hasattr(cb, "winfo_exists") and not cb.winfo_exists():
                    return
                return orig_set(bool(v), *args, **kwargs_set)
            except Exception:
                pass

        cb.set = _safe_set

        orig_get = cb.get

        def _safe_get(*args, **kwargs_get):
            try:
                if hasattr(cb, "winfo_exists") and not cb.winfo_exists():
                    return 0
                return orig_get(*args, **kwargs_get)
            except Exception:
                return 0

        cb.get = _safe_get

        if default:
            cb.select()
        else:
            cb.deselect()

        if row is not None and col is not None:
            cb.grid(
                row=row,
                column=col,
                columnspan=columnspan,
                sticky=grid_sticky,
                padx=grid_padx,
                pady=grid_pady,
            )
        elif parent is None:
            cb.grid(row=1, column=0, sticky="w", pady=(2, 4))

        getter = lambda: bool(cb.get())
        setter = lambda v: cb.set(bool(v))
        self._fields[field_name] = ("custom", cb, (getter, setter))
        return cb

    # Aliases for CTkCheckBox
    CTkCheckBox = add_ctk_checkbox
    addCTkCheckBox = add_ctk_checkbox
    add_ctkcheckbox = add_ctk_checkbox

    def add_ctk_button(
        self,
        label: str,
        callback: Callable,
        variant: str = "primary",  # "primary", "secondary", "danger", "success"
        width: int = 140,
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> Any:
        """Adds a modern pill-shaped button with smooth hover glow effects."""
        self._require_ctk()
        p = parent or self.inner_frame
        frame = ttk.Frame(p, style="Surface.TFrame")
        frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(8, 4))
        frame.columnconfigure(0, weight=1)
        self._inner_row += 1

        color_map = {
            "primary": ("#3b82f6", "#2563eb"),
            "secondary": ("#475569", "#334155"),
            "danger": ("#ef4444", "#dc2626"),
            "success": ("#10b981", "#059669"),
        }
        default_fg, default_hover = color_map.get(variant, ("#3b82f6", "#2563eb"))
        fg_col = kwargs.pop("fg_color", default_fg)
        hover_col = kwargs.pop("hover_color", default_hover)

        cb = callback or kwargs.pop("command", None)

        def _on_click():
            values = self.get_values()
            if cb:
                try:
                    cb(values)
                except TypeError:
                    cb()

        btn = ctk.CTkButton(
            frame,
            text=label,
            command=_on_click,
            fg_color=fg_col,
            hover_color=hover_col,
            width=width,
            **kwargs,
        )
        btn.grid(row=0, column=0, sticky="ew")
        return btn

    # Aliases for CTkButton
    CTkButton = add_ctk_button
    addCTkButton = add_ctk_button

    def add_button(
        self,
        *args,
        label: Optional[str] = None,
        callback: Optional[Callable] = None,
        variant: str = "primary",  # "primary", "default", "danger"
        command: Optional[Callable] = None,
        **kwargs,
    ) -> ttk.Button:
        """Adds an action button that triggers a callback with form values."""
        # Flexible argument handling supporting:
        # 1) add_button("Execute", callback=...)
        # 2) add_button("Execute", on_click_fn)
        # 3) add_button("name", "Label", callback=...)
        if len(args) == 1:
            btn_label = str(args[0])
            cb = callback if callback is not None else command
        elif len(args) >= 2:
            if callable(args[1]):
                btn_label = str(args[0])
                cb = args[1]
            else:
                btn_label = str(args[1])
                cb = callback if callback is not None else (args[2] if len(args) > 2 and callable(args[2]) else command)
        else:
            btn_label = str(label or "Button")
            cb = callback if callback is not None else command
        frame = ttk.Frame(self.inner_frame, style="Surface.TFrame")
        frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(10, 4))
        frame.columnconfigure(0, weight=1)
        self._inner_row += 1

        style_map = {
            "primary": "Primary.TButton",
            "danger": "Danger.TButton",
            "default": "TButton",
        }
        style_name = style_map.get(variant, "TButton")

        def _on_click():
            values = self.get_values()
            if cb:
                try:
                    cb(values)
                except TypeError:
                    cb()

        btn = ttk.Button(frame, text=btn_label, style=style_name, command=_on_click)
        btn.grid(row=0, column=0, sticky="ew")
        return btn

    def add_command(
        self,
        label: str,
        command: Optional[Callable] = None,
        callback: Optional[Callable] = None,
        variant: str = "primary",
        **kwargs,
    ) -> ttk.Button:
        """Alias for add_button() supporting standard Tkinter command syntax."""
        cb = command if command is not None else callback
        return self.add_button(label=label, callback=cb, variant=variant, **kwargs)

    def add_button_group(
        self,
        buttons: List[Tuple[str, Callable, str]],
    ) -> ttk.Frame:
        """Adds multiple buttons in a horizontal row. Format: [(label, callback, variant)]"""
        frame = ttk.Frame(self.inner_frame, style="Surface.TFrame")
        frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(8, 4))
        self._inner_row += 1

        style_map = {
            "primary": "Primary.TButton",
            "danger": "Danger.TButton",
            "default": "TButton",
        }

        for idx, item in enumerate(buttons):
            lbl, cb, *rest = item
            variant = rest[0] if rest else "default"
            frame.columnconfigure(idx, weight=1)
            style_name = style_map.get(variant, "TButton")

            def _make_handler(handler=cb):
                def _h():
                    try:
                        handler(self.get_values())
                    except TypeError:
                        handler()

                return _h

            btn = ttk.Button(
                frame, text=lbl, style=style_name, command=_make_handler(cb)
            )
            btn.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 4, 0))

        return frame

    def get_values(self) -> Dict[str, Any]:
        """Extracts current values of all registered fields as a clean dictionary."""
        result = {}
        for name, (ftype, widget, val_handler) in self._fields.items():
            if ftype == "custom":
                getter, _ = val_handler
                result[name] = getter()
            else:
                result[name] = val_handler.get()
        return result

    def get_value(self, name: str, default: Any = None) -> Any:
        """Extracts the value of a single field by name."""
        if name not in self._fields:
            return default
        ftype, widget, val_handler = self._fields[name]
        if ftype == "custom":
            getter, _ = val_handler
            return getter()
        return val_handler.get()

    def set_value(self, name: str, val: Any):
        """Sets the value of a single form field by name."""
        if name in self._fields:
            ftype, widget, val_handler = self._fields[name]
            if ftype == "custom":
                _, setter = val_handler
                setter(val)
            else:
                val_handler.set(val)

    def set_values(self, data: Dict[str, Any]):
        """Sets form fields programmatically from a dictionary."""
        for name, val in data.items():
            self.set_value(name, val)

    def clear(self):
        """Resets all fields to empty/default values."""
        for name, (ftype, widget, val_handler) in self._fields.items():
            if ftype == "checkbox":
                val_handler.set(False)
            elif ftype == "number" or ftype == "slider":
                val_handler.set(0)
            elif ftype == "multi_select":
                val_handler.clear_all()
            elif ftype == "custom":
                pass
            else:
                val_handler.set("")

    def get_widget(self, name: str) -> Optional[Any]:
        """Returns the underlying widget instance for a field by name."""
        if name in self._fields:
            return self._fields[name][1]
        cleaned = name.lower().replace(" ", "_")
        if cleaned in self._fields:
            return self._fields[cleaned][1]
        return None

    def configure_field(self, name: str, **kwargs) -> Optional[Any]:
        """Convenience method to configure an underlying field widget by name."""
        widget = self.get_widget(name)
        if widget is not None and hasattr(widget, "configure"):
            widget.configure(**kwargs)
            return widget
        return None
