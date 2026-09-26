import sys

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
if IS_WINDOWS:
    quick_tk_dir = r"C:\Users\Linda\Trading_Bot_V2\Ron\Code"
else:
    quick_tk_dir = r"/Users/ronh/trading_bot_v2/Ron/Code"
if quick_tk_dir not in sys.path:
    sys.path.insert(0, quick_tk_dir)

import time

from quick_tk import QuickApp, ToolView


class MyUtilityTool(ToolView):
    title = "TK Calculator"
    description = "TK Based Calculator"

    def __init__(self, parent=None, app=None, calc_mode=None):
        # QuickApp supplies the content area and app instance when creating
        # the tool. Accept them while retaining support for an optional mode.
        self.calc_modes = {
            "standard": "Standard Calculator",
            "scientific": "Scientific Calculator",
            "temperature": "Temperature Converter",
            "compound-interest": "Compound Interest Calculator",
        }
        # Always initialize the calculator mode, including when the tool is
        # created by QuickApp without an explicit mode.
        self.calc_mode = calc_mode if calc_mode in self.calc_modes else "standard"
        self.calc_description = self.calc_modes[self.calc_mode]
        super().__init__(parent, app=app)
        # Start the clock
        self.start_time = time.perf_counter()
        self.last_report_time = self.start_time

    def build_ui(self):
        # 1. Declare your inputs
        self.form = self.add_form("TKCalc", parent=self)
        self.form.add_dropdown(
            "calc_mode",
            "Calculator Mode",
            self.calc_modes.keys(),
            default="None/None",
            on_change=self.calc_mode_auto_calc,
        )

        self.form.add_text("username", "Operator Name", default="Ron")
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

    def calc_mode_auto_calc(self, new_value):
        self.calc_mode = new_value
        self.console.write_line(f"Calculator mode changed to: {self.calc_mode}")
        self.calc_description = self.calc_modes[self.calc_mode]
        self.console.write_line(f"Calculator description: {self.calc_description}")


if __name__ == "__main__":
    print("In Main")
    app = QuickApp(title="My TKCalculator", size=(900, 600), theme="Dark Obsidian")
    app.set_single_tool(MyUtilityTool)
    app.run()
