# 🚀 QuickTk: Modern OOP GUI Framework for Python Utilities

> **"Repackaging muddy CLI scripts into social-setting friendly desktop apps with zero boilerplate."**

`QuickTk` is a lightweight, pure-Python object-oriented wrapper around Tkinter and TTK. It eliminates the tedious geometry math (`grid(row=0, col=1)`), manual variable bindings (`StringVar()`, `DoubleVar()`), and clunky styling boilerplate.

---

## 📂 Project Structure

```
quick_tk/
├── core/
│   ├── app.py            # QuickApp & ToolView (Window lifecycle, threading, sidebar routing)
│   ├── forms.py          # FormPanel & all high-level inputs (text, numbers, sliders, pickers)
│   ├── outputs.py        # DataTable (Treeview), StatGrid (KPI cards), ConsolePanel (Text/Code)
│   └── theme.py          # Modern Dark / Light themes with custom TTK styling
├── examples/
│   ├── 01_trade_analyzer.py      # SQLite Trade Filtering & Reporting Tool
│   ├── 02_grade_calculator.py    # College Grade Estimator & Final Target Calculator
│   ├── 03_futures_tick_calc.py   # Live Futures (ES, NQ, etc.) Tick/Contract Calculator
│   ├── 04_cheat_sheet_viewer.py  # Python Documentation & Syntax Viewer
│   └── 05_all_in_one_suite.py    # Master Sidebar Dashboard hosting all 4 tools
├── demo_launcher.py              # Interactive launcher menu
└── README.md
```

---

## ⚡ The 3-Step Recipe: Turn Any Script into a GUI App

Every utility you build inherits from `ToolView` and implements two methods:

```python
from quick_tk import QuickApp, ToolView

class MyUtilityTool(ToolView):
    title = "My Script Title"

    def build_ui(self):
        # 1. Declare your inputs
        self.form = self.add_form("Settings")
        self.form.add_text("username", "Your Name", default="Linda")
        self.form.add_dropdown("mode", "Operation Mode", ["Quick", "Thorough", "Deep"])
        self.form.add_slider("threads", "Worker Threads", min_val=1, max_val=16, default=4)
        self.form.add_file_picker("file_path", "Target File", mode="open")
        self.form.add_button("Execute", callback=self.on_run, variant="primary")

        # 2. Declare your outputs
        self.console = self.add_console("Results")

    def on_run(self, inputs: dict):
        # 3. Drop in your backend logic!
        # inputs is automatically a clean dict: {'username': '...', 'mode': '...', ...}
        self.console.write_heading("Starting Task")
        self.console.write_line(f"Running mode {inputs['mode']} on {inputs['file_path']}...")
        
        # Done!
        self.set_status("Complete!")

if __name__ == "__main__":
    app = QuickApp(title="My Tool")
    app.set_single_tool(MyUtilityTool)
    app.run()
```

---

## 🛠️ Available UI Components

### 1. `FormPanel` (Input Builder)
- **`add_text(name, label, default="")`**: Single-line text entry.
- **`add_number(name, label, default=0, min_val, max_val, step, is_float)`**: Numeric spinbox.
- **`add_slider(name, label, min_val, max_val, default, step, on_change)`**: Slider with live badge.
- **`add_dropdown(name, label, options, default, on_change)`**: Combobox dropdown.
- **`add_radio(name, label, options, default, horizontal=True, on_change)`**: Radio button group.
- **`add_checkbox(name, label, default=False, on_change)`**: Boolean checkbox.
- **`add_file_picker(name, label, default="", mode="open"|"save"|"directory")`**: Input with Browse... button.
- **`add_button(label, callback, variant="primary"|"default")`**: Action button.
- **`get_values() -> dict`**: Automatically returns all inputs as a clean dictionary.
- **`set_values(dict)`** / **`clear()`**: Programmatically sets or clears inputs.

### 2. `StatGrid` (KPI / Metric Badges)
Display bold metrics with automatic status colors:
```python
self.stats.set_metrics({
    "Win Rate": ("68.5%", "success"),
    "Total PnL": ("+$4,250", "success"),
    "Max Drawdown": ("-$320", "danger"),
    "Status": ("Active", "info"),
})
```

### 3. `DataTable` (Sortable Treeview)
- **`set_columns(["Col 1", "Col 2", ...])`**: Column headers with click-to-sort.
- **`set_data(rows)`**: Accepts a list of lists or list of dicts.
- **`enable_search=True`**: Adds real-time instant search filter bar.
- **`enable_export_csv=True`**: Adds one-click CSV export button.
- **`on_select(callback)`**: Captures row selection events.

### 4. `ConsolePanel` (Rich Log & Code Viewer)
- **`write(text, tag)`**: Colored text (`info`, `success`, `danger`, `warning`, `primary`, `dim`).
- **`write_line(text, tag)`**: Appends a line.
- **`write_heading(title)`**: Section header banners.
- **`write_code(code_str)`**: Syntax-highlighted code blocks.
- **`clear()`** / **`copy_all()`**: Toolbar actions.

### 5. `QuickApp` (Multi-Tool Hub & Async Runner)
- **`app.set_single_tool(ToolClass)`**: Runs as a focused standalone window.
- **`app.setup_sidebar([Tool1, Tool2, Tool3])`**: Mounts multiple tools in a left-sidebar navigation dashboard.
- **`app.setup_tabs([Tool1, Tool2])`**: Tabbed notebook interface.
- **`self.run_async(worker_fn, on_done, on_error)`**: Multithreaded background worker so DB queries or long scripts never freeze the GUI.

---

## 🎮 How to Test the Demos

You can test each prototype directly from PowerShell:

```powershell
cd C:\Users\Linda\.gemini\antigravity\scratch\quick_tk

# 1. Run the interactive Showcase Launcher:
python demo_launcher.py

# 2. Or run the Master All-In-One Dashboard:
python examples/05_all_in_one_suite.py

# 3. Or run any individual tool:
python examples/01_trade_analyzer.py
python examples/02_grade_calculator.py
python examples/03_futures_tick_calc.py
python examples/04_cheat_sheet_viewer.py
```
