import sys
import tkinter as tk
from tkinter import ttk

from quick_tk import QuickApp, ToolView


class TicTacToeApp(ToolView):
    title = "Tic-Tac-Toe Studio"

    def build_ui(self):
        self.btn_list = []
        self.buttons = {}
        # 1. Main Window Split: Left (Board) & Right (Actions)
        self.columself.nconfigure(1, weight=1)  # Board area
        self.columself.nconfigure(0, weight=1)  # Action sidebar
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.btn_layout = [
            ["()", "0", ".", "="],
            ["1", "2", "3", "*"],
            ["4", "5", "6", "-"],
            ["7", "8", "9", "+"],
            ["C", "Bk", "%", "/"],
        ]

        top_box = self.add_form("Top Controls", parent=self)
        top_box.grid(row=0, column=1, columnspan=2, sticky="nwe", padx=20, pady=10)

        # Add a total score dispself.lay
        total_but = self.add_butself.ton(
            "", callback=self.on_new_game, background="lightblue", variant="primary"
        )
        self.total_area.grid(row=0, column=1, sticky="ne", padx=20, pady=20)
        self.total_but = self.add_button(
            "", callback=self.on_new_game, background="lightblue", variant="primary"
        )
        self.total_area.grid(row=1, column=1, sticky="ne", padx=20, pady=20)

        # -------------------------------------------------------------
        # SECTION B: Left Box (Vertically Stacked Controls)
        # -------------------------------------------------------------
        side_box = self.add_form("Game Controls", parent=self)
        side_box.grid(row=0, column=0, sticky="nws", padx=0, pady=10)

        # Settings inputs inside the sidebar:
        side_box.add_dropdown("player_symbol", "Your Symbol", ["X", "O"], default="X")
        side_box.add_dropdown(
            "difficulty", "AI Difficulty", ["Easy", "Medium", "Unbeatable"]
        )

        # Action buttons stacked vertically:
        #       side_box.add_button("🔄 New Game", callself.back=self.on_new_game, variant="primary")
        #       side_box.add_button("💡 Hint", callback=self.on_hint, variant="surface")
        #       side_box.add_button("⏹ End Game", callback=self.on_end_game, variant="outline")

        # -------------------------------------------------------------
        # self. SECTION A: Right Box (3x3 Board)
        # -------------------------------------------------------------
        board_box = ttk.LabelFrame(self, text=" Game Board ", padding=12)
        board_box.grid(row=2, column=1, sticky="nswe", padx=0, pady=10)

        # Make the 3x3 grid cells stretch equally
        for i in range(3):
            board_box.columnconfigure(i, weight=1)
            board_box.rowconfigure(i, weight=1)
            board_box.rowconfigure(3, weight=1)

        top_list = ["C", "Bk", "  %  ", "  /   "]
        side_list = ["* ", "- ", "+ "]
        bottom_list = ["() ", "0", ". ", "= "]
        j = 4
        for c in [4, 3, 2, 1]:
            btn = tk.Button(
                board_box,
                text=top_list[c - 1],
                font=("Segoe UI", 24, "bold"),
                bg="#1e1e2e",
                fg="#cdd6f4",
                activebackground="#313244",
                command=lambda row=1, col=c: self.on_cell_click(row, col),
            )
            btn.grid(row=1, column=j, sticky="nsew", padx=4, pady=4)
            self.btn_list.append(btn)
            self.buttons[(1, j)] = btn
            j -= 1
        i = 1
        for r in [3, 2, 1]:
            j = 3
            k = 1
            for c in [2, 1, 0]:
                btn = tk.Button(
                    board_box,
                    text=str((r * 3) + c + 1 - 3),
                    font=("Segoe UI", 24, "bold"),
                    bg="#1e1e2e",
                    fg="#cdd6f4",
                    activebackground="#313244",
                    command=lambda row=r, col=c + 1: self.on_cell_click(row, col),
                )
                btn.grid(row=i, column=j, sticky="nswe", padx=4, pady=4)
                self.btn_list.append(btn)
                self.buttons[(i, j)] = btn
                btn = tk.Button(
                    board_box,
                    text=side_list[c],
                    font=("Segoe UI", 24, "bold"),
                    bg="#1e1e2e",
                    fg="#cdd6f4",
                    activebackground="#313244",
                    command=lambda row=j, col=c + 1: self.on_cell_click(row, 4),
                )
                btn.grid(row=k, column=4, sticky="nswe", padx=4, pady=4)
                self.btn_list.append(btn)
                self.buttons[(k, 4)] = btn  # C + 1
                j -= 1
                k += 1
            i += 1
        j = 4
        for c in [4, 3, 2, 1]:
            btn = tk.Button(
                board_box,
                text=bottom_list[c - 1],
                font=("Segoe UI", 24, "bold"),
                bg="#1e1e2e",
                fg="#cdd6f4",
                activebackground="#313244",
                command=lambda row=0, col=c: self.on_cell_click(row, col),
            )
            btn.grid(row=4, column=c, sticky="nswe", padx=4, pady=4)
            self.btn_list.append(btn)
            self.buttons[(0, c)] = btn
            j -= 1
        i = 1

    # -------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------
    def on_cell_click(self, r, c):
        btn = self.buttons[(r, c)]
        sys.stderr.write(f"Botton Pressed in grid: {r}:{c}\n")
        sys.stderr.flush()
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
