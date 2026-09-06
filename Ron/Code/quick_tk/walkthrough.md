# QuickTk Framework Walkthrough & Interactive Showcase

We have designed, built, and verified **`QuickTk`**: an ergonomic, pure-Python object-oriented wrapper around Tkinter and TTK.

It is located in:
`C:\Users\Linda\.gemini\antigravity\scratch\quick_tk`

---

## 🌟 What QuickTk Gives You

1. **Zero Geometry/Grid Math**:
   - Call `self.add_form("Settings")`, `form.add_dropdown(...)`, `form.add_slider(...)`, `self.add_stat_grid(...)`, `self.add_data_table(...)`, `self.add_console(...)`.
   - Automatic vertical stacking, multi-column row grouping (`form.add_row_container()`), and resizable split panes (`self.add_split_view()`).

2. **Automatic State & Value Binding**:
   - No `tk.StringVar()` or manual `.get()`.
   - A single call to `form.get_values()` gives you a clean Python dictionary:
     ```python
     {'symbol': 'ES', 'contracts': 2, 'target_profit': 500.0}
     ```

3. **Custom Widget Freedom**:
   - Easily drop in **any** custom or raw Tkinter widget using `form.add_custom_widget(...)` and connect it to `get_values()`.

4. **Multi-Mode Flexibility (Single Window & Multi-Tool Dashboard)**:
   - **Standalone Single Tool**: `app.set_single_tool(MyTool)` runs as a standalone window.
   - **Master All-in-One Dashboard**: `app.setup_sidebar([Tool1, Tool2, Tool3])` mounts all your utilities in a sidebar dashboard.
   - **Tabbed Dashboard**: `app.setup_tabs([Tool1, Tool2])`.

5. **Instant Theme Switching & Customization**:
   - Built-in live theme picker in the bottom-right status bar with 4 presets:
     - 🌌 **Dark Obsidian** (modern dark theme)
     - 💡 **Clean Light** (crisp modern light theme)
     - ⚡ **Cyberpunk Neon** (neon cyan / dark blue accent)
     - 🌲 **Emerald Forest** (deep dark green accent)
   - Dynamic custom palette support via `app.set_theme(dict)`.

6. **Async Multithreading**:
   - `self.run_async(worker_func, on_done)` ensures SQLite queries or heavy calculations run in the background without freezing the GUI.

---

## 🎮 How to Run and Interact with the Demos

Open PowerShell and launch the demos:

### 1. Interactive Demo Launcher (Try all tools from one menu)
```powershell
python C:\Users\Linda\.gemini\antigravity\scratch\quick_tk\demo_launcher.py
```

### 2. Master All-In-One Dashboard (Sidebar with all 4 tools mounted)
```powershell
python C:\Users\Linda\.gemini\antigravity\scratch\quick_tk\examples\05_all_in_one_suite.py
```

### 3. Individual Standalone Utility Apps
- **SQLite Trade Filter & Reporting Tool**:
  ```powershell
  python C:\Users\Linda\.gemini\antigravity\scratch\quick_tk\examples\01_trade_analyzer.py
  ```
  *(Includes auto-generated sample trades database with 150 simulated trades, filtering by strategy/PnL/date, KPI stat cards, and CSV export!)*

- **College Grade Estimator & Target Calculator**:
  ```powershell
  python C:\Users\Linda\.gemini\antigravity\scratch\quick_tk\examples\02_grade_calculator.py
  ```
  *(Live real-time weighted grade calculation with score needed on final exam).*

- **Futures Tick & Sizing Calculator**:
  ```powershell
  python C:\Users\Linda\.gemini\antigravity\scratch\quick_tk\examples\03_futures_tick_calc.py
  ```
  *(Supports ES, MES, NQ, MNQ, YM, CL, GC with live sliders for win/loss targets and target tick matrices).*

- **Python Reference & Cheat Sheet Viewer**:
  ```powershell
  python C:\Users\Linda\.gemini\antigravity\scratch\quick_tk\examples\04_cheat_sheet_viewer.py
  ```
  *(Interactive reference guide with method tables and syntax-highlighted code console).*

---

## 🧑‍💻 How to Build Your Next Tool in 30 Seconds

```python
import os, sys
sys.path.insert(0, r"C:\Users\Linda\.gemini\antigravity\scratch\quick_tk")

from quick_tk import QuickApp, ToolView

class MyQuickTool(ToolView):
    title = "My Utility"

    def build_ui(self):
        # 1. Inputs
        form = self.add_form("Parameters")
        form.add_text("query", "Search Term", default="python")
        form.add_slider("limit", "Max Results", min_val=5, max_val=100, default=25)
        form.add_button("Execute", callback=self.on_run, variant="primary")

        # 2. Outputs
        self.stats = self.add_stat_grid(columns=2)
        self.table = self.add_data_table(columns=["ID", "Name", "Status"])

    def on_run(self, inputs: dict):
        # 3. Your logic!
        print("Inputs received:", inputs)
        self.stats.set_metrics({"Total Found": (42, "success"), "Query": (inputs["query"], "info")})
        self.table.set_data([[1, "Item A", "Active"], [2, "Item B", "Pending"]])

if __name__ == "__main__":
    app = QuickApp(title="My Tool")
    app.set_single_tool(MyQuickTool)
    app.run()
```
