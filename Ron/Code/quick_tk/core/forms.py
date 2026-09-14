"""
Form components and input wrappers for QuickTk.
Handles automatic variable binding, multi-column row layouts, custom widgets, and value extraction.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


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
        self._fields: Dict[str, Tuple[str, Any, Any]] = {}  # name -> (type, widget, getter/setter_or_var)
        self._callbacks: Dict[str, List[Callable]] = {}
        self._slider_timers: Dict[str, Any] = {}
        self._row_count = 0

        self.columnconfigure(0, weight=1)

        # Optional Card/Title Header
        if title:
            header = ttk.Label(self, text=title, style="Heading.TLabel")
            header.grid(row=self._row_count, column=0, sticky="w", padx=padding, pady=(padding, 10))
            self._row_count += 1

        self.inner_frame = ttk.Frame(self, style="Surface.TFrame")
        self.inner_frame.grid(row=self._row_count, column=0, sticky="nsew", padx=padding, pady=(0, padding))
        self.inner_frame.columnconfigure(0, weight=1)
        self._row_count += 1
        self._inner_row = 0

    def _add_field_container(self, label_text: str, parent: Optional[tk.Widget] = None) -> ttk.Frame:
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

        txt = tk.Text(container, height=height, bg=bg, fg=fg, insertbackground=fg, relief="flat", font=("Segoe UI", 10))
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
            var.trace_add("write", lambda *args: self._safe_num_callback(var, on_change, is_float))

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
        is_int = (step >= 1) and (float(step).is_integer()) and (float(min_val).is_integer())
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
        default_val = default if default is not None else (options[0] if options else "")
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
        default_val = default if default is not None else (options[0] if options else "")
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
                command=(lambda v=var, cb=on_change: cb(v.get())) if on_change else None,
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
        label: str,
        default: bool = False,
        parent: Optional[tk.Widget] = None,
        on_change: Optional[Callable[[bool], None]] = None,
    ) -> ttk.Checkbutton:
        """Adds a boolean checkbutton."""
        container = self._add_field_container("", parent=parent)
        var = tk.BooleanVar(value=default)

        cb = ttk.Checkbutton(
            container,
            text=label,
            variable=var,
            style="TCheckbutton",
            command=(lambda v=var, fn=on_change: fn(v.get())) if on_change else None,
        )
        cb.grid(row=0, column=0, sticky="w", pady=(2, 2))

        self._fields[name] = ("checkbox", cb, var)
        return cb

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
                messagebox.showerror("Invalid Directory", f"The directory does not exist:\n{target_dir}")
                return

            # 2. Check for file existence & prompt overwrite
            if os.path.exists(chosen_path):
                proceed = messagebox.askyesno(
                    "File Exists",
                    f"The file already exists:\n\n{chosen_path}\n\nDo you wish to overwrite it?",
                    icon="warning",
                )
                if not proceed:
                    messagebox.showinfo("Cancelled", "File selection cancelled. Please choose another file name.")
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
        setter = (lambda v: set_value_fn(custom_widget, v)) if set_value_fn else (lambda v: None)

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

    def add_button(
        self,
        label: str,
        callback: Callable,
        variant: str = "primary",  # "primary", "default", "danger"
    ) -> ttk.Button:
        """Adds an action button that triggers a callback with form values."""
        frame = ttk.Frame(self.inner_frame, style="Surface.TFrame")
        frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(10, 4))
        frame.columnconfigure(0, weight=1)
        self._inner_row += 1

        style_map = {"primary": "Primary.TButton", "danger": "Danger.TButton", "default": "TButton"}
        style_name = style_map.get(variant, "TButton")

        def _on_click():
            values = self.get_values()
            try:
                callback(values)
            except TypeError:
                callback()

        btn = ttk.Button(frame, text=label, style=style_name, command=_on_click)
        btn.grid(row=0, column=0, sticky="ew")
        return btn

    def add_button_group(
        self,
        buttons: List[Tuple[str, Callable, str]],
    ) -> ttk.Frame:
        """Adds multiple buttons in a horizontal row. Format: [(label, callback, variant)]"""
        frame = ttk.Frame(self.inner_frame, style="Surface.TFrame")
        frame.grid(row=self._inner_row, column=0, sticky="ew", pady=(8, 4))
        self._inner_row += 1

        style_map = {"primary": "Primary.TButton", "danger": "Danger.TButton", "default": "TButton"}

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

            btn = ttk.Button(frame, text=lbl, style=style_name, command=_make_handler(cb))
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
            elif ftype == "custom":
                pass
            else:
                val_handler.set("")
