import tkinter as tk
from tkinter import ttk

from quick_tk import QuickApp, ToolView


class TicTacToeApp(ToolView):
    title = "Tic-Tac-Toe Studio"

    def build_ui(self):
        # 1. Main Window Split: Left (Board) & Right (Actions)
        self.columnconfigure(0, weight=1)  # Board area
        self.columnconfigure(1, weight=0)  # Action sidebar
        self.rowconfigure(0, weight=1)

        # -------------------------------------------------------------
        # SECTION B: Right Box (Vertically Stacked Controls)
        # -------------------------------------------------------------
        side_box = self.add_form("Game Controls", parent=self)
        side_box.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        # Settings inputs inside the sidebar:
        side_box.add_dropdown("player_symbol", "Your Symbol", ["X", "O"], default="X")
        side_box.add_dropdown(
            "difficulty", "AI Difficulty", ["Easy", "Medium", "Unbeatable"]
        )

        # Action buttons stacked vertically:
        side_box.add_button("🔄 New Game", callback=self.on_new_game, variant="primary")
        side_box.add_button("💡 Hint", callback=self.on_hint, variant="surface")
        side_box.add_button("⏹ End Game", callback=self.on_end_game, variant="outline")

        # -------------------------------------------------------------
        # SECTION A: Left Box (3x3 Board)
        # -------------------------------------------------------------
        board_box = ttk.LabelFrame(self, text=" Game Board ", padding=12)
        board_box.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Make the 3x3 grid cells stretch equally
        for i in range(3):
            board_box.columnconfigure(i, weight=1)
            board_box.rowconfigure(i, weight=1)

        # Create the 9 grid buttons
        self.buttons = {}
        for r in range(3):
            for c in range(3):
                btn = tk.Button(
                    board_box,
                    text=" ",
                    font=("Segoe UI", 24, "bold"),
                    bg="#1e1e2e",
                    fg="#cdd6f4",
                    activebackground="#313244",
                    command=lambda row=r, col=c: self.on_cell_click(row, col),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
                self.buttons[(r, c)] = btn

    # -------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------
    def on_cell_click(self, r, c):
        btn = self.buttons[(r, c)]
        if btn["text"] == " ":
            btn.config(text="X", fg="#89b4fa")  # Soft blue
            self.set_status(f"Placed X at row {r + 1}, col {c + 1}")

    def on_new_game(self, values: dict):
        for btn in self.buttons.values():
            btn.config(text=" ", bg="#1e1e2e")
        self.set_status(f"New game started! Mode: {values.get('difficulty')}")

    def on_hint(self, values: dict):
        self.set_status("Hint: Take the center square (Row 2, Col 2)!")

    def on_end_game(self, values: dict):
        self.set_status("Game ended.")


if __name__ == "__main__":
    app = QuickApp(title="Tic-Tac-Toe", size=(750, 450), theme="Dark Obsidian")
    app.set_single_tool(TicTacToeApp)
    app.run()
