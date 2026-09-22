# 🚀 QuickTk: Modern OOP GUI Framework for Python Utilities

> **"Repackaging muddy CLI scripts into social-setting friendly desktop apps with zero boilerplate."**

`QuickTk` is a lightweight, pure-Python object-oriented wrapper around Tkinter, TTK, and optional CustomTkinter. It eliminates tedious geometry math (`grid(row=0, col=1)`), manual variable bindings (`StringVar()`, `DoubleVar()`), and clunky styling boilerplate.

---

## 📂 Project Structure

```
quick_tk/
├── core/
│   ├── app.py            # QuickApp & ToolView (Window lifecycle, threading, sidebar/tabs, CTk mode)
│   ├── forms.py          # FormPanel, MultiSelectDropdown, CTk widgets, & all high-level inputs
│   ├── outputs.py        # DataTable (Treeview), StatGrid (KPI cards), ConsolePanel, ImagePanel
│   ├── menu.py           # MenuBarBuilder & MenuNode (Hierarchical menus, toggles, radio groups)
│   ├── dialogs.py        # Modal Dialogs (prompt_text, prompt_number, prompt_choice, prompt_form)
│   └── theme.py          # Modern Dark / Light themes with custom TTK styling
├── examples/
│   ├── 01_trade_analyzer.py          # SQLite Trade Filtering & Reporting Tool
│   ├── 02_grade_calculator.py        # College Grade Estimator & Final Target Calculator
│   ├── 03_futures_tick_calc.py       # Live Futures (ES, NQ) Tick/Contract Calculator
│   ├── 04_cheat_sheet_viewer.py      # Python Documentation & Syntax Viewer
│   ├── 05_all_in_one_suite.py        # Master Sidebar Dashboard hosting all tools
│   ├── 06_menu_showcase.py           # Hierarchical Menus, Submenus, & Shortcuts
│   ├── 07_image_converter.py         # In-Frame Image Scaling & Popup Window Viewer
│   ├── 08_multi_select_showcase.py   # Compact Multi-Select Dropdowns with Filter
│   ├── 09_customtkinter_showcase.py  # Modern CustomTkinter Shell & Controls
│   └── 10_menu_popup_form_showcase.py# Menu-Driven Popup Form & Floating Windows
├── demo_launcher.py                  # Interactive graphical launcher menu
├── tkimage_convert.py                # Standalone Production Image Converter Tool
└── README.md
```

---

## ⚡ The 3-Step Recipe: Turn Any Script into a GUI App

Every utility you build inherits from `ToolView` and implements `build_ui()`:

```python
from quick_tk import QuickApp, ToolView


class MyUtilityTool(ToolView):
    title = "Data Processing Utility"

    def build_ui(self):
        # 1. Declare your inputs
        self.form = self.add_form("Settings")
        self.form.add_text("username", "Operator Name", default="Linda")
        self.form.add_dropdown("mode", "Operation Mode", ["Quick", "Thorough", "Deep"])
        self.form.add_slider(
            "threads", "Worker Threads", min_val=1, max_val=16, default=4
        )
        self.form.add_file_picker("file_path", "Target File", mode="open")
        self.form.add_button("Execute", callback=self.on_run, variant="primary")

        # 2. Declare your outputs
        self.console = self.add_console("Live Logs")

    def on_run(self, inputs: dict):
        # 3. Drop in your backend logic!
        # inputs is automatically a clean dict: {'username': '...', 'mode': '...', 'file_path': '...'}
        self.console.write_heading("Starting Task")
        self.console.write_line(
            f"Running mode {inputs['mode']} on {inputs['file_path']}..."
        )
        self.set_status("Task completed successfully!")


if __name__ == "__main__":
    app = QuickApp(title="My Standalone Tool", size=(900, 600), theme="Dark Obsidian")
    app.set_single_tool(MyUtilityTool)
    app.run()
```

---

## 🛠️ UI Components & Features

### 1. `FormPanel` (Input Builder)

- **`add_text(name, label, default="")`**: Single-line text input.
- **`add_text_area(name, label, default="", height=4)`**: Multi-line text box.
- **`add_number(name, label, default=0, min_val, max_val, step, is_float)`**: Numeric spinbox.
- **`add_slider(name, label, min_val, max_val, default, step, on_change)`**: Slider with live badge indicator.
- **`add_dropdown(name, label, options, default, on_change)`**: Combobox dropdown.
- **`add_multi_select(name, label, options, default, placeholder, max_display, on_change)`**:
  *✨ NEW!* Compact single-row multi-select control with a popup containing live search filtering, bulk Select All/None buttons, and badge summaries (e.g. `"AAPL, NVDA (+3 more)"`).
- **`add_radio(name, label, options, default, horizontal=True, on_change)`**: Radio button group.
- **`add_checkbox(name, label, default=False, on_change)`**: Boolean checkbox.
- **`add_file_picker(name, label, default="", mode="open"|"save"|"directory", filetypes)`**: Text input with Browse button.
- **`add_output_file_picker(name, label, default="", filetypes, default_ext)`**: Dedicated destination file picker with auto-extension enforcement.
- **`add_row_container(columns=2)`**: Group multiple inputs side-by-side on the same horizontal row.
- **`add_button(label, callback, variant="primary"|"default")`**: Action button.
- **`add_button_group([{"label": "Run", "command": ..., "variant": "primary"}, ...])`**: Horizontal row of action buttons.
- **`get_values() -> dict`**: Automatically returns all input values as a clean dictionary.
- **`set_value(name, val)`** / **`set_values(dict)`** / **`clear()`**: Programmatically inspect or modify form inputs.

---

### 2. CustomTkinter (CTk) Modern Controls (*NEW*)

QuickTk seamlessly integrates with `customtkinter` when installed, giving your apps modern rounded styling, smooth hover glow animations, and OS-native dark/light mode switching.

Enable it by passing `use_ctk=True` to `QuickApp`:
```python
app = QuickApp(title="Modern Dashboard", size=(1000, 700), use_ctk=True)
```

Available CTk Form Controls:
- **`add_ctk_entry(name, label, placeholder="", default="")`**: Modern rounded text box with placeholder text.
- **`add_ctk_textbox(name, label, default="", height=100)`**: Multi-line rounded editor.
- **`add_ctk_switch(name, label, text="", default=False, on_change=None)`**: Animated iOS/macOS-style toggle switch.
- **`add_ctk_segmented(name, label, values=["1m", "5m", "1D"], default="5m", on_change=None)`**: Modern rounded segmented pill buttons.
- **`add_ctk_slider(name, label, from_=0, to=100, default=50, number_of_steps=None, on_change=None)`**: Smooth pill-thumb slider.
- **`add_ctk_progress(name, label, default=0.0, orientation="horizontal", mode="determinate")`**: Rounded progress bar.
- **`add_ctk_checkbox(name, label, text="", default=False, on_change=None)`**: Rounded checkbox with hover highlights.
- **`add_ctk_button(label, callback, variant="primary"|"secondary"|"danger"|"success", width=140)`**: Pill button with smooth hover glow.

All CTk controls participate directly in `form.get_values()`, `form.set_value()`, and `form.clear()`.

---

### 3. Hierarchical Menus & Shortcuts (`MenuBarBuilder` & `MenuNode`)

Define top-level application menus either fluently or declaratively:

#### Fluent Chained Style
```python
file_menu = self.menu("File")
file_menu.add_item("New Project", self.on_new, shortcut="Ctrl+N")
file_menu.add_file_open("Open Data File...", self.on_open, shortcut="Ctrl+O")
file_menu.add_file_save(
    "Save Report As...", self.on_save, default_ext=".csv", shortcut="Ctrl+S"
)
file_menu.add_separator()

# Cascading Submenu
export_sub = file_menu.add_submenu("Export As")
export_sub.add_item("Export to CSV", self.export_csv)
export_sub.add_item("Export to JSON", self.export_json)

# Checkbox Toggles and Radio Groups
view_menu = self.menu("View")
view_menu.add_toggle(
    "Include Timestamps",
    default=True,
    on_toggle=self.toggle_timestamps,
    shortcut="Ctrl+T",
)
density_sub = view_menu.add_submenu("Density")
density_sub.add_radio_group(
    ["Compact", "Normal", "Wide"], default="Normal", on_change=self.set_density
)
```

#### Declarative Tree Style
```python
self.build_menu_tree(
    {
        "Tools": [
            {"label": "Run Diagnostics", "command": self.run_diag, "shortcut": "F5"},
            "---",
            {
                "label": "Database Operations",
                "submenu": [
                    {"label": "Vacuum Database", "command": self.db_vacuum},
                    {"label": "Re-index Tables", "command": self.db_reindex},
                ],
            },
        ]
    }
)
```

---

### 4. Modal Dialogs & Popped Windows (`core/dialogs.py`)

Keep your main window uncluttered by moving secondary forms, file selectors, and options to popup windows:

#### Single Input Prompts
```python
# 1. Text Prompt
name = self.prompt_text(
    title="Project Name", prompt="Enter title:", default="Alpha Scan"
)

# 2. Number Prompt
limit = self.prompt_number(
    title="Row Limit",
    prompt="Max rows to fetch:",
    default=500,
    min_val=10,
    max_val=10000,
)

# 3. Dropdown Choice
choice = self.prompt_choice(
    title="Format",
    prompt="Select output type:",
    options=["CSV", "JSON", "Parquet"],
    default="CSV",
)

# 4. Confirmation
if self.prompt_confirm(title="Confirm", message="Delete selected record?"):
    self.delete_record()
```

#### Multi-Field Form Dialog (`prompt_form`)
Pop up an entire form window (with dropdowns, file pickers, sliders, and buttons) from a menu choice:
```python
def on_open_settings(self):
    def build_settings_form(form):
        form.add_dropdown(
            "feed",
            "Market Data Feed",
            ["Alpaca Paper", "Alpaca Live", "Interactive Brokers"],
        )
        form.add_file_picker("input_file", "Historical CSV", mode="open")
        form.add_file_picker("export_dir", "Export Directory", mode="directory")
        form.add_slider(
            "risk_pct",
            "Account Risk %",
            min_val=0.5,
            max_val=5.0,
            default=2.0,
            step=0.5,
        )

    # Opens modal dialog, centers over main window, blocks until user clicks Submit or Cancel
    settings = self.prompt_form(
        title="Data Source & Path Configuration",
        form_builder_fn=build_settings_form,
        size=(480, 360),
        ok_text="Apply Configuration",
    )

    if settings:
        # settings is automatically a clean dict!
        self.apply_configuration(settings)
```

---

### 5. Outputs & Displays (`core/outputs.py`)

- **`DataTable` (Sortable Treeview)**:
  - `set_columns(["Ticker", "Side", "PnL", "Date"])`
  - `set_data(rows)` (accepts lists or dicts)
  - `enable_search=True` (instant real-time search filter bar)
  - `enable_export_csv=True` (one-click CSV export)
  - `on_select(callback)` (row selection handler)
- **`StatGrid` (KPI Cards)**:
  - Bold metrics with status tags: `set_metrics({"Win Rate": ("68%", "success"), "Drawdown": ("-$320", "danger")})`
- **`ConsolePanel` (Rich Log & Code Viewer)**:
  - `write(text, tag)`, `write_line(text, tag)`, `write_heading(title)`, `write_code(code_str)`
  - Tags: `info`, `success`, `danger`, `warning`, `primary`, `dim`
  - Toolbar with Clear and Copy All buttons.
- **`ImagePanel`**:
  - Auto-scaling image preview pane maintaining aspect ratio.
- **`show_image_window(image_path, title, max_display_size)`**:
  - *✨ NEW!* Opens an image in a separate floating Toplevel window.

---

### 6. Window Topologies & Lifecycle (`QuickApp`)

- **`app.set_single_tool(ToolClass)`**: Focuses the entire application window on a single tool view.
- **`app.setup_sidebar([Tool1, Tool2, Tool3])`**: Modern left-sidebar navigation dashboard for multi-tool utility suites.
- **`app.setup_tabs([Tool1, Tool2])`**: Tabbed notebook interface.
- **`self.add_split_view(orientation="horizontal"|"vertical")`**: Embeds a resizable dual-pane container.
- **`self.run_async(worker_fn, on_done, on_error)`**: Thread pool worker to keep heavy operations (DB queries, network downloads, conversions) off the GUI thread.

---

## 🎮 How to Test the Examples

Run any of the 9 example utilities directly from PowerShell:

```powershell
cd C:\Users\Linda\Trading_Bot_V2\Ron\Code\quick_tk

# 1. Run the interactive Graphical Showcase Launcher:
python demo_launcher.py

# 2. Master All-In-One Sidebar Suite:
python examples/05_all_in_one_suite.py

# 3. Individual Showcase Demos:
python examples/01_trade_analyzer.py          # SQLite Trade Analyzer
python examples/02_grade_calculator.py        # Grade & GPA Calculator
python examples/03_futures_tick_calc.py       # Futures Tick Calculator
python examples/04_cheat_sheet_viewer.py      # Python Cheat Sheet Viewer
python examples/06_menu_showcase.py           # Menus, Submenus & Shortcuts
python examples/07_image_converter.py         # Image Converter & Viewer
python examples/08_multi_select_showcase.py   # Multi-Select Dropdowns
python examples/09_customtkinter_showcase.py  # CustomTkinter Modern Controls
python examples/10_menu_popup_form_showcase.py # Menu-Driven Popup Dialogs
```
