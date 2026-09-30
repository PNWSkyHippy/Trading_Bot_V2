import sys
import tkinter as tk
from tkinter import ttk

import colllections as col
from quick_tk import QuickApp, ToolView


class TicTacToeApp(ToolView):
    title = "TK Calculator"

    def build_ui(self):
        self.mem_q = col.deque(maxlen=10)
        self.btn_list = []
        self.buttons = {}
        # 1. Main Window Split: Left (Board) & Right (Actions)
        self.columnconfigure(0, weight=0)  # Action sidebar
        self.columnconfigure(1, weight=1)  # Total Board area / Board Area

        self.rowconfigure(0, weight=0)  # Action bar
        self.rowconfigure(1, weight=0)  # Total Board area
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=1)  # board area
        self.btn_layout = [
            ["()", "0", ".", "="],
            ["1", "2", "3", "*"],
            ["4", "5", "6", "-"],
            ["7", "8", "9", "+"],
            ["C", "Bk", "%", "/"],
        ]

        self.side_box = self.add_form("Calc Options", parent=self)
        self.side_box.grid(row=0, column=0, sticky="nws", padx=0, pady=10)
        self.options = self.side_box.add_frame("Game Options", padding=10)
        self.options.add_button("Memory", self.on_memory)
        self.options.grid(row=0, column=0, sticky="nws", padx=10, pady=10)
        self.options.add_button("Clear Memory", self.on_clear_memory)
        self.options.grid(row=2, column=0, sticky="nws", padx=10, pady=10)
        self.memort_box = tk.Text(self.options, height=5, width=20)
        self.memort_box.grid(row=1, column=0, sticky="nswe", padx=10, pady=10)

        #        self.top_form = self.add_form("T", parent=self)
        self.top_form = ttk.LabelFrame(self, text="", padding=20)
        self.top_form.grid(row=0, column=1, sticky="new", padx=20, pady=8)
        self.top_form.columnconfigure(1, weight=1)

        self.entry_box = tk.Text(self.top_form, height=5, width=20)
        self.entry_box.grid(
            row=0, column=1, columnspan=3, sticky="nswe", padx=10, pady=10
        )
        self.entry_box.config(
            state="disabled", background="lightblue"
        )  # Make the text box read-only

        self.result_box = ttk.Entry(self.top_form, width=30, state="readonly")
        self.result_box.grid(row=1, column=1, sticky="nwe", padx=20, pady=10)
        self.result_box.config(state="readonly", background="lightblue")

        # -------------------------------------------------------------
        # SECTION B: Left Box (Vertically Stacked Controls)
        # -------------------------------------------------------------

        # -------------------------------------------------------------
        # self. SECTION A: Right Box (3x3 Board)
        # -------------------------------------------------------------
        board_box = ttk.LabelFrame(self, text=" TKCalculator ", padding=12)
        board_box.grid(row=3, column=1, sticky="nsew", padx=20, pady=10)

        # Make the 3x3 grid cells stretch equally
        for i in range(3):
            board_box.columnconfigure(i, weight=1)
            board_box.rowconfigure(i, weight=1)
            board_box.rowconfigure(3, weight=1)
        for i in range(1, 5):
            board_box.columnconfigure(i, weight=1)
            board_box.rowconfigure(4, weight=1)
        board_box.columnconfigure(0, weight=0)

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
                # Top calculator buttons
                command=lambda text=top_list[c - 1].strip(): self.on_cell_click(text),
            )
            btn.grid(row=0, column=j, sticky="nwse", padx=4, pady=4)
            self.btn_list.append(btn)
            # Keep the lookup key consistent with the row passed to the
            # callback.  These are the bottom calculator row (row 4), not
            # row 1; using row 1 overwrites other buttons and causes a
            # KeyError when the button is pressed.
            self.buttons[(4, 5 - c)] = btn
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
                    # Number buttons
                    command=lambda text=str((r * 3) + c + 1 - 3): self.on_cell_click(
                        text
                    ),
                )
                btn.grid(row=i, column=j, sticky="nwse", padx=4, pady=4)
                self.btn_list.append(btn)
                self.buttons[(i, j)] = btn
                btn = tk.Button(
                    board_box,
                    text=side_list[c],
                    font=("Segoe UI", 24, "bold"),
                    bg="#1e1e2e",
                    fg="#cdd6f4",
                    activebackground="#313244",
                    # Operator buttons
                    command=lambda text=side_list[c].strip(): self.on_cell_click(text),
                )
                btn.grid(row=k, column=4, sticky="nwse", padx=4, pady=4)
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
                # Bottom calculator buttons
                command=lambda text=bottom_list[c - 1].strip(): self.on_cell_click(
                    text
                ),
            )
            btn.grid(row=4, column=c, sticky="nwse", padx=4, pady=4)
            self.btn_list.append(btn)
            self.buttons[(0, c)] = btn
            j -= 1
        i = 1

        # -------------------------------------------------------------
        # Callbacks
        # -------------------------------------------------------------
        """self.btn_layout = [
                    ["()", "0", ".", "="],
                    ["1", "2", "3", "*"],
                    ["4", "5", "6", "-"],
                    ["7", "8", "9", "+"],
                    ["C", "Bk", "%", "/"],
                ]
        """

    def on_cell_click(self, txt):
        sys.stderr.write(f"Button pressed: {txt}\n")
        sys.stderr.flush()

        self.entry_box.config(state="normal")

        if txt == "Bk":
            if self.entry_box.get("1.0", "end-1c"):
                self.entry_box.delete("end-2c", "end-1c")

        elif txt == "C":
            self.mem_q.append(self.entry_box.get("1.0", "end-1c"))
            self.entry_box.delete("1.0", "end")
        elif txt == "()":
            current_text = self.entry_box.get("1.0", "end-1c")

            if current_text.count("(") > current_text.count(")"):
                self.entry_box.insert("end", ")")
            else:
                # Add multiplication for expressions such as 5(...)
                if current_text and (
                    current_text[-1].isdigit() or current_text[-1] == ")"
                ):
                    self.entry_box.insert("end", "*(")
                else:
                    self.entry_box.insert("end", "(")
        elif txt == "=":
            current_text = self.entry_box.get("1.0", "end-1c")
            try:
                result = eval(current_text, {"__builtins__": {}}, {})
                self.entry_box.delete("1.0", "end")

                self.result_box.config(state="normal")
                self.result_box.delete(0, "end")
                self.result_box.insert(0, str(result))
                self.result_box.config(state="readonly")
            except Exception as error:
                self.result_box.config(state="normal")
                self.result_box.delete(0, "end")
                self.result_box.insert(0, f"Error: {error}")
                self.result_box.config(state="readonly")

        else:
            self.entry_box.insert("end", txt)

        self.entry_box.config(state="disabled")

    def on_memory(self, values: dict):
        self.memort_q.config(state="normal")
        self.memort_q.delete("1.0", "end")
        for item in self.mem_q:
            self.memort_q.insert("end", item + "\n")
        self.memort_q.config(state="disabled")

    def on_clear_memory(self):
        self.mem_q.clear()
        self.memort_box.config(state="normal")
        self.memort_box.delete("1.0", "end")
        self.memort_box.config(state="disabled")


if __name__ == "__main__":
    app = QuickApp(title="Tic-Tac-Toe", size=(750, 750), theme="Dark Obsidian")
    app.set_single_tool(TicTacToeApp)
    app.run()
