from quick_tk import QuickApp, ToolView


class MyUtilityTool(ToolView):
    title = "Data Processing Utility"

    def build_ui(self):
        # Configure layout (Left Form / Right Console)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Declare your inputs
        self.form = self.add_form("Settings")
        self.form.add_text("username", "Operator Name", default="Linda")
        self.form.add_dropdown("mode", "Operation Mode", ["Quick", "Thorough", "Deep"])
        self.form.add_slider(
            "threads", "Worker Threads", min_val=1, max_val=16, default=4
        )
        self.form.add_file_picker("file_path", "Target File", mode="open")
        self.form.add_button("Execute", callback=self.on_run, variant="primary")

        # 2. Declare your outputs`
        # 2. Declare your outputs
        self.console = self.add_console("Live Logs", parent=self)
        self.console.grid(row=0, column=1, sticky="nsew")

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
