"""
High-Level Menu System for QuickTk.
Provides fluent and declarative hierarchical menu building with submenus,
checkbox toggles, radio groups, file pickers, keyboard shortcuts, and action handlers.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class MenuNode:
    """
    Represents a top-level menu or nested submenu with fluent helper methods.
    """

    def __init__(self, master_tk_menu: tk.Menu, root: tk.Tk):
        self.menu = master_tk_menu
        self.root = root
        self._vars: List[tk.Variable] = []  # Keep references alive

    def add_command(
        self,
        label: str,
        command: Callable,
        shortcut: Optional[str] = None,
    ) -> "MenuNode":
        """Adds a standard clickable action item with optional keyboard shortcut."""
        accel = shortcut if shortcut else ""
        self.menu.add_command(label=label, command=command, accelerator=accel)
        if shortcut:
            self._bind_shortcut(shortcut, command)
        return self

    def add_item(self, label: str, command: Callable, shortcut: Optional[str] = None) -> "MenuNode":
        """Alias for add_command."""
        return self.add_command(label, command, shortcut=shortcut)

    def add_toggle(
        self,
        label: str,
        default: bool = False,
        on_toggle: Optional[Callable[[bool], None]] = None,
        shortcut: Optional[str] = None,
    ) -> tk.BooleanVar:
        """
        Adds a checkbox / toggle menu item.
        Returns the BooleanVar for tracking state.
        """
        var = tk.BooleanVar(value=default)
        self._vars.append(var)

        def _on_click():
            if on_toggle:
                on_toggle(var.get())

        accel = shortcut if shortcut else ""
        self.menu.add_checkbutton(label=label, variable=var, command=_on_click, accelerator=accel)

        if shortcut:
            def _shortcut_handler():
                var.set(not var.get())
                _on_click()
            self._bind_shortcut(shortcut, _shortcut_handler)

        return var

    def add_radio_group(
        self,
        options: List[str],
        default: Optional[str] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ) -> tk.StringVar:
        """Adds a group of mutually exclusive radio button choices."""
        default_val = default if default is not None else (options[0] if options else "")
        var = tk.StringVar(value=default_val)
        self._vars.append(var)

        for opt in options:
            def _make_handler(val=opt):
                if on_change:
                    on_change(val)

            self.menu.add_radiobutton(
                label=opt,
                value=opt,
                variable=var,
                command=(lambda v=var, cb=on_change: cb(v.get())) if on_change else None,
            )
        return var

    def add_file_open(
        self,
        label: str = "Open File...",
        callback: Optional[Callable[[str], None]] = None,
        filetypes: Optional[List[Tuple[str, str]]] = None,
        shortcut: Optional[str] = None,
    ) -> "MenuNode":
        """Adds a menu action that automatically opens a file browser and passes the selected path."""
        def _handler():
            ft = filetypes or [("All Files", "*.*")]
            path = filedialog.askopenfilename(filetypes=ft, title=label)
            if path and callback:
                callback(path)

        return self.add_command(label, _handler, shortcut=shortcut)

    def add_file_save(
        self,
        label: str = "Save As...",
        callback: Optional[Callable[[str], None]] = None,
        default_filename: str = "",
        default_ext: str = "",
        filetypes: Optional[List[Tuple[str, str]]] = None,
        shortcut: Optional[str] = None,
    ) -> "MenuNode":
        """Adds a menu action that automatically opens a Save As dialog and passes the selected path."""
        def _handler():
            ft = filetypes or [("All Files", "*.*")]
            path = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=default_ext,
                filetypes=ft,
                title=label,
            )
            if path and callback:
                callback(path)

        return self.add_command(label, _handler, shortcut=shortcut)

    def add_separator(self) -> "MenuNode":
        """Adds a visual dividing line."""
        self.menu.add_separator()
        return self

    def add_submenu(self, label: str) -> "MenuNode":
        """Creates and attaches a cascading submenu."""
        sub = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label=label, menu=sub)
        return MenuNode(sub, self.root)

    def add_exit(
        self,
        label: str = "Exit",
        confirm: bool = False,
        shortcut: str = "Alt+F4",
        on_before_exit: Optional[Callable[[], bool]] = None,
    ) -> "MenuNode":
        """
        Adds a clean application Exit/Close action.
        - confirm: If True, asks 'Are you sure you want to exit?'
        - on_before_exit: Optional callback. If returns False, aborts exit.
        """
        def _exit_handler():
            if on_before_exit:
                proceed = on_before_exit()
                if proceed is False:
                    return

            if confirm:
                ans = messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the application?")
                if not ans:
                    return

            try:
                self.root.destroy()
            except Exception:
                self.root.quit()

        return self.add_command(label, _exit_handler, shortcut=shortcut)

    def _bind_shortcut(self, shortcut: str, command: Callable):
        """Binds standard keyboard shortcuts like 'Ctrl+O', 'Ctrl+Shift+S', 'F5'."""
        key = shortcut.strip()
        # Normalization
        tokens = key.split("+")
        modifiers = []
        main_key = tokens[-1]

        for mod in tokens[:-1]:
            m = mod.lower()
            if m in ("ctrl", "control"):
                modifiers.append("Control")
            elif m == "alt":
                modifiers.append("Alt")
            elif m == "shift":
                modifiers.append("Shift")

        if modifiers:
            tk_event = f"<{''.join(m + '-' for m in modifiers)}{main_key.lower() if len(main_key) == 1 else main_key}>"
        else:
            tk_event = f"<{main_key}>" if not main_key.startswith("<") else main_key

        try:
            self.root.bind(tk_event, lambda e: command())
        except Exception:
            pass


class MenuBarBuilder:
    """
    Main Menu Bar Manager attached to QuickApp root window.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        self._menus: Dict[str, MenuNode] = {}

    def add_menu(self, label: str) -> MenuNode:
        """Adds a top-level menu dropdown (e.g. 'File', 'Edit', 'Help')."""
        if label in self._menus:
            return self._menus[label]
        top_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=label, menu=top_menu)
        node = MenuNode(top_menu, self.root)
        self._menus[label] = node
        return node

    def menu(self, label: str) -> MenuNode:
        """Alias for add_menu."""
        return self.add_menu(label)

    def build_tree(self, tree: Dict[str, List[Union[str, Dict[str, Any]]]]):
        """
        Declarative tree builder.
        Accepts a dictionary mapping top-level menu names to lists of item dicts or '---' separators.
        
        Example:
        app.build_menu_tree({
            "File": [
                {"label": "New Project", "command": self.on_new, "shortcut": "Ctrl+N"},
                {"label": "Open...", "type": "file_open", "callback": self.on_open, "shortcut": "Ctrl+O"},
                "---",
                {
                    "label": "Export",
                    "submenu": [
                        {"label": "To CSV", "command": self.export_csv},
                        {"label": "To JSON", "command": self.export_json},
                    ]
                },
                "---",
                {"label": "Exit", "command": app.root.quit}
            ],
            "View": [
                {"label": "Show Status Bar", "type": "toggle", "default": True, "on_toggle": self.toggle_sb},
                {"label": "Theme", "type": "radio", "options": ["Dark", "Light"], "on_change": self.set_t}
            ]
        })
        """
        for top_name, items in tree.items():
            menu_node = self.add_menu(top_name)
            self._populate_items(menu_node, items)

    def _populate_items(self, parent_node: MenuNode, items: List[Union[str, Dict[str, Any]]]):
        for item in items:
            if item == "---":
                parent_node.add_separator()
                continue

            if not isinstance(item, dict):
                continue

            label = item.get("label", "")
            itype = item.get("type", "command")
            shortcut = item.get("shortcut")

            if "submenu" in item:
                sub_node = parent_node.add_submenu(label)
                self._populate_items(sub_node, item["submenu"])
            elif itype == "toggle" or itype == "checkbox":
                parent_node.add_toggle(
                    label=label,
                    default=item.get("default", False),
                    on_toggle=item.get("on_toggle"),
                    shortcut=shortcut,
                )
            elif itype == "radio":
                parent_node.add_radio_group(
                    options=item.get("options", []),
                    default=item.get("default"),
                    on_change=item.get("on_change"),
                )
            elif itype == "file_open":
                parent_node.add_file_open(
                    label=label or "Open File...",
                    callback=item.get("callback"),
                    filetypes=item.get("filetypes"),
                    shortcut=shortcut,
                )
            elif itype == "file_save":
                parent_node.add_file_save(
                    label=label or "Save As...",
                    callback=item.get("callback"),
                    default_filename=item.get("default_filename", ""),
                    default_ext=item.get("default_ext", ""),
                    filetypes=item.get("filetypes"),
                    shortcut=shortcut,
                )
            elif itype == "exit":
                parent_node.add_exit(
                    label=label or "Exit",
                    confirm=item.get("confirm", False),
                    shortcut=shortcut or "Alt+F4",
                    on_before_exit=item.get("on_before_exit"),
                )
            else:
                # Standard command
                cmd = item.get("command") or item.get("callback") or (lambda: None)
                parent_node.add_command(label=label, command=cmd, shortcut=shortcut)
