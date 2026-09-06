import os, sys
sys.path.insert(0, r"C:\Users\Linda\trading_bot_v2\Ron\Code\quick_tk")

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