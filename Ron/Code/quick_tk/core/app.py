"""
Main QuickApp and BaseTool class definitions for QuickTk.
Handles application lifecycle, theme switching, layout routing, status bar, and multithreading.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from .forms import FormPanel
from .menu import MenuBarBuilder, MenuNode
from .outputs import ConsolePanel, DataTable, StatGrid, ImagePanel, show_image_window
from .theme import Theme, apply_theme


class ToolView(ttk.Frame):
    """
    Base class for any utility tool view.
    Subclass this and implement `build_ui()` and your custom callbacks.
    """

    title: str = "Tool"
    description: str = ""

    def __init__(self, parent: tk.Widget, app: "QuickApp", **kwargs):
        super().__init__(parent, style="TFrame", **kwargs)
        self.app = app
        self.theme = app.current_theme
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._main_container = ttk.Frame(self, style="TFrame")
        self._main_container.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self._main_container.columnconfigure(0, weight=1)
        self._main_container.rowconfigure(0, weight=1)

        self.build_ui()

    def build_ui(self):
        """Override this method to construct the tool's widgets."""
        pass

    def add_form(self, title: Optional[str] = None, parent: Optional[tk.Widget] = None, **kwargs) -> FormPanel:
        """Helper to create a FormPanel."""
        p = parent or self._main_container
        return FormPanel(p, title=title, theme=self.theme, **kwargs)

    def add_data_table(
        self,
        columns: Optional[List[str]] = None,
        parent: Optional[tk.Widget] = None,
        enable_search: bool = True,
        enable_export_csv: bool = True,
        **kwargs,
    ) -> DataTable:
        """Helper to create a DataTable."""
        p = parent or self._main_container
        return DataTable(
            p,
            columns=columns,
            enable_search=enable_search,
            enable_export_csv=enable_export_csv,
            theme=self.theme,
            **kwargs,
        )

    def add_stat_grid(self, columns: int = 4, parent: Optional[tk.Widget] = None, **kwargs) -> StatGrid:
        """Helper to create a StatGrid."""
        p = parent or self._main_container
        return StatGrid(p, columns=columns, theme=self.theme, **kwargs)

    def add_console(self, title: Optional[str] = "Output Console", parent: Optional[tk.Widget] = None, **kwargs) -> ConsolePanel:
        """Helper to create a ConsolePanel."""
        p = parent or self._main_container
        return ConsolePanel(p, title=title, theme=self.theme, **kwargs)

    def add_image_preview(
        self,
        title: Optional[str] = "Image Preview",
        max_size: Tuple[int, int] = (450, 350),
        parent: Optional[tk.Widget] = None,
        **kwargs,
    ) -> ImagePanel:
        """Helper to create an ImagePanel for displaying scaled image previews."""
        p = parent or self._main_container
        return ImagePanel(p, title=title, max_size=max_size, theme=self.theme, **kwargs)

    def show_image_window(
        self,
        image_or_path: Union[str, Any],
        title: str = "Image Window",
        max_display_size: Tuple[int, int] = (900, 700),
    ) -> Optional[tk.Toplevel]:
        """Opens a separate Tkinter window displaying the full converted image."""
        return show_image_window(
            image_or_path,
            title=title,
            parent_root=self.app.root,
            max_display_size=max_display_size,
        )

    def add_container(self, parent: Optional[tk.Widget] = None, padding: int = 0) -> ttk.Frame:
        """Creates a flexible styled container frame."""
        p = parent or self._main_container
        f = ttk.Frame(p, style="TFrame", padding=padding)
        f.columnconfigure(0, weight=1)
        return f

    def add_split_view(
        self,
        orientation: str = "horizontal",
        parent: Optional[tk.Widget] = None,
    ) -> Tuple[ttk.Frame, ttk.Frame]:
        """Creates a resizable PanedWindow split (left/right or top/bottom)."""
        p = parent or self._main_container
        orient = tk.HORIZONTAL if orientation == "horizontal" else tk.VERTICAL
        paned = ttk.PanedWindow(p, orient=orient)
        paned.grid(row=0, column=0, sticky="nsew")

        f1 = ttk.Frame(paned, style="TFrame")
        f2 = ttk.Frame(paned, style="TFrame")
        f1.columnconfigure(0, weight=1)
        f2.columnconfigure(0, weight=1)

        paned.add(f1, weight=1)
        paned.add(f2, weight=2)
        return f1, f2

    def add_menu(self, label: str) -> MenuNode:
        """Adds a top-level menu dropdown (e.g. 'File', 'Edit') and returns MenuNode for chaining."""
        return self.app.add_menu(label)

    def menu(self, label: str) -> MenuNode:
        """Alias for add_menu."""
        return self.app.menu(label)

    def build_menu_tree(self, tree: Dict[str, List[Union[str, Dict[str, Any]]]]):
        """Builds an entire menu tree declaratively from a nested dictionary."""
        self.app.build_menu_tree(tree)

    def set_status(self, text: str):
        """Updates the main app's status bar."""
        self.app.set_status(text)

    def run_async(
        self,
        worker_func: Callable[[], Any],
        on_done: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        status_msg: str = "Processing...",
    ):
        """Runs a heavy Python task in the background without freezing the UI."""
        self.app.run_async(worker_func, on_done=on_done, on_error=on_error, status_msg=status_msg)


class QuickApp:
    """
    Main application shell that manages window state, themes, menus, and views.
    """

    def __init__(
        self,
        title: str = "QuickTk App",
        size: Tuple[int, int] = (1000, 680),
        theme: str = "Dark Obsidian",
        resizable: bool = True,
    ):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{size[0]}x{size[1]}")
        self.root.minsize(700, 480)
        if not resizable:
            self.root.resizable(False, False)

        self.theme_name = theme
        self.current_theme = Theme.PRESETS.get(theme, Theme.DARK)
        apply_theme(self.root, self.current_theme)

        # Root layout: Content + StatusBar
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self._content_area = ttk.Frame(self.root, style="TFrame")
        self._content_area.grid(row=0, column=0, sticky="nsew")
        self._content_area.columnconfigure(0, weight=1)
        self._content_area.rowconfigure(0, weight=1)

        # Status Bar
        self._status_bar = ttk.Frame(self.root, style="Surface.TFrame", padding=(8, 4))
        self._status_bar.grid(row=1, column=0, sticky="ew")
        self._status_bar.columnconfigure(0, weight=1)

        self._status_lbl = ttk.Label(self._status_bar, text="Ready", style="Dim.TLabel")
        self._status_lbl.grid(row=0, column=0, sticky="w")

        # Theme Combobox in status bar
        theme_box = ttk.Frame(self._status_bar, style="Surface.TFrame")
        theme_box.grid(row=0, column=1, sticky="e")

        t_lbl = ttk.Label(theme_box, text="Theme:", style="Dim.TLabel")
        t_lbl.grid(row=0, column=0, padx=(0, 4))

        self._theme_var = tk.StringVar(value=theme if theme in Theme.PRESETS else "Dark Obsidian")
        theme_cb = ttk.Combobox(
            theme_box,
            textvariable=self._theme_var,
            values=list(Theme.PRESETS.keys()),
            state="readonly",
            width=16,
        )
        theme_cb.grid(row=0, column=1)
        theme_cb.bind("<<ComboboxSelected>>", lambda e: self.set_theme(self._theme_var.get()))

        self.menu_builder = MenuBarBuilder(self.root)
        self._menu_bar = self.menu_builder.menu_bar

        self._setup_default_menus()

        self._active_view: Optional[ToolView] = None
        self._tools: Dict[str, Type[ToolView]] = {}
        self._nav_buttons: Dict[str, ttk.Button] = {}

    def _setup_default_menus(self):
        """Sets up default top menus including theme picker."""
        theme_menu = self.menu_builder.add_menu("Themes")
        for t_name in Theme.PRESETS.keys():
            theme_menu.add_command(t_name, lambda n=t_name: self.set_theme(n))

    def set_theme(self, theme_input: Union[str, dict]):
        """Switches the theme dynamically to a preset name or custom dictionary."""
        if isinstance(theme_input, str):
            self.theme_name = theme_input
            self.current_theme = Theme.PRESETS.get(theme_input, Theme.DARK)
            if hasattr(self, "_theme_var"):
                self._theme_var.set(theme_input)
        else:
            self.current_theme = theme_input
        apply_theme(self.root, self.current_theme)

    def toggle_theme(self):
        """Toggles between Dark Obsidian and Clean Light."""
        new_theme = "Clean Light" if "Dark" in self.theme_name or "Cyber" in self.theme_name else "Dark Obsidian"
        self.set_theme(new_theme)

    def set_status(self, text: str):
        """Sets the status bar text."""
        self._status_lbl.config(text=text)

    def add_menu(self, label: str, items: Optional[List[Tuple[str, Optional[Callable]]]] = None) -> MenuNode:
        """
        Adds a top-level menu dropdown (e.g. 'File', 'Edit', 'Help') and returns MenuNode.
        If items is provided, populates legacy list of (label, callback).
        """
        node = self.menu_builder.add_menu(label)
        if items:
            for item in items:
                lbl = item[0]
                cb = item[1] if len(item) > 1 else None
                if lbl == "---" or cb is None:
                    node.add_separator()
                else:
                    node.add_command(lbl, cb)
        return node

    def menu(self, label: str) -> MenuNode:
        """Alias for add_menu."""
        return self.add_menu(label)

    def build_menu_tree(self, tree: Dict[str, List[Union[str, Dict[str, Any]]]]):
        """Builds an entire menu tree declaratively from a nested dictionary."""
        self.menu_builder.build_tree(tree)

    def exit(self, confirm: bool = False):
        """Cleanly closes the application window with optional confirmation."""
        if confirm:
            ans = messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the application?")
            if not ans:
                return
        try:
            self.root.destroy()
        except Exception:
            self.root.quit()

    def on_close(self, callback: Callable[[], bool]):
        """
        Registers a custom handler when the user clicks the OS window close (X) button.
        If callback returns False, the close action is aborted.
        """
        def _handler():
            res = callback()
            if res is not False:
                try:
                    self.root.destroy()
                except Exception:
                    self.root.quit()

        self.root.protocol("WM_DELETE_WINDOW", _handler)

    def set_single_tool(self, tool_class: Type[ToolView]) -> ToolView:
        """Sets up the app to display a single tool view filling the entire window."""
        for child in self._content_area.winfo_children():
            child.destroy()

        tool_instance = tool_class(self._content_area, app=self)
        tool_instance.grid(row=0, column=0, sticky="nsew")
        self._active_view = tool_instance
        self.root.title(f"{self.root.title()} - {tool_class.title}")
        return tool_instance

    def setup_sidebar(self, tools: List[Type[ToolView]], default_index: int = 0):
        """Creates a modern left sidebar navigation supporting multiple tools."""
        for child in self._content_area.winfo_children():
            child.destroy()

        self._content_area.columnconfigure(0, weight=0)
        self._content_area.columnconfigure(1, weight=1)
        self._content_area.rowconfigure(0, weight=1)

        # Sidebar Frame
        sidebar = ttk.Frame(self._content_area, style="Sidebar.TFrame", width=220, padding=10)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Header in sidebar
        app_title_lbl = ttk.Label(sidebar, text="UTILITY HUB", style="Title.TLabel", font=("Segoe UI", 12, "bold"))
        app_title_lbl.pack(fill="x", pady=(8, 16), padx=4)

        # Container for tool views
        view_container = ttk.Frame(self._content_area, style="TFrame")
        view_container.grid(row=0, column=1, sticky="nsew")
        view_container.columnconfigure(0, weight=1)
        view_container.rowconfigure(0, weight=1)

        self._tool_views: Dict[str, ToolView] = {}
        self._nav_buttons.clear()

        for idx, tool_cls in enumerate(tools):
            name = tool_cls.title
            self._tools[name] = tool_cls

            # Instantiate view
            view = tool_cls(view_container, app=self)
            self._tool_views[name] = view

            # Create nav button
            btn = ttk.Button(
                sidebar,
                text=f"  {name}",
                style="Nav.TButton",
                command=lambda n=name: self._show_sidebar_tool(n),
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons[name] = btn

        if tools:
            default_tool = tools[default_index].title
            self._show_sidebar_tool(default_tool)

    def _show_sidebar_tool(self, tool_name: str):
        """Switches the active view in the sidebar layout."""
        for name, view in self._tool_views.items():
            if name == tool_name:
                view.grid(row=0, column=0, sticky="nsew")
                self._active_view = view
                if name in self._nav_buttons:
                    self._nav_buttons[name].configure(style="NavActive.TButton")
            else:
                view.grid_forget()
                if name in self._nav_buttons:
                    self._nav_buttons[name].configure(style="Nav.TButton")

        self.set_status(f"Loaded {tool_name}")

    def setup_tabs(self, tools: List[Type[ToolView]]):
        """Creates a tabbed interface with each tool on a tab."""
        for child in self._content_area.winfo_children():
            child.destroy()

        notebook = ttk.Notebook(self._content_area)
        notebook.grid(row=0, column=0, sticky="nsew")

        for tool_cls in tools:
            view = tool_cls(notebook, app=self)
            notebook.add(view, text=f"  {tool_cls.title}  ")

    def run_async(
        self,
        worker_func: Callable[[], Any],
        on_done: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        status_msg: str = "Processing...",
    ):
        """Executes a worker in a background thread and posts results to Tk mainloop safely."""
        self.set_status(status_msg)

        def _thread_target():
            try:
                result = worker_func()
                if on_done:
                    self.root.after(0, lambda: on_done(result))
                self.root.after(0, lambda: self.set_status("Ready"))
            except Exception as ex:
                if on_error:
                    self.root.after(0, lambda: on_error(ex))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Task Error", str(ex)))
                self.root.after(0, lambda: self.set_status("Error occurred."))

        t = threading.Thread(target=_thread_target, daemon=True)
        t.start()

    def run(self):
        """Starts the Tkinter main event loop."""
        self.root.mainloop()
