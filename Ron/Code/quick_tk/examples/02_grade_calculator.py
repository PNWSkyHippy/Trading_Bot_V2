"""
College Grade Calculator Tool
Demonstrates FormPanel numeric inputs, live calculation callbacks, StatGrid badges, and DataTable.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView


class GradeCalculatorTool(ToolView):
    title = "Grade Calculator"
    description = "Calculate college course grades, weighted score breakdown, and final exam targets"

    def build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Input Form
        self.form = self.add_form("Course Component Scores (%)", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form.add_number("quizzes", "Quizzes Avg (Weight: 30%)", default=33.3, min_val=0, max_val=100, step=33.3, is_float=True, on_change=self._auto_calc)
        self.form.add_number("participation", "Participation (Weight: 10%)", default=25, min_val=0, max_val=100, step=25, is_float=True, on_change=self._auto_calc)
        self.form.add_number("bonus", "Bonus / Extra Credit (10%)", default=25, min_val=0, max_val=100, step=25, is_float=True, on_change=self._auto_calc)
        self.form.add_dropdown("target_grade", "Target Grade Goal", ["A (90%)", "A- (87%)", "B+ (83%)", "B (80%)", "C (70%)"], default="A (90%)", on_change=self._auto_calc)
        self.form.add_number("final_exam_est", "Projected Final Exam Score (Weight: 60%)", default=89.0, min_val=0, max_val=100, step=1, is_float=True, on_change=self._auto_calc)

        self.form.add_button("Calculate Breakdown", callback=self.on_calculate, variant="primary")

        # 2. Right Results Panel: StatGrid + Breakdown Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)

        self.stats = self.add_stat_grid(columns=4, parent=right_box)
        self.stats.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.table = self.add_data_table(
            columns=["Component", "Weight (%)", "Score (%)", "Weighted Points", "Max Possible"],
            parent=right_box,
            enable_search=False,
            enable_export_csv=True,
        )
        self.table.grid(row=1, column=0, sticky="nsew")

        # Initial calculation
        self.on_calculate(self.form.get_values())

    def _auto_calc(self, _=None):
        """Triggered automatically when any input changes."""
        self.on_calculate(self.form.get_values())

    def on_calculate(self, values: dict):
        q = round(float(values.get("quizzes", 0)))
        part = float(values.get("participation", 0))
        bonus = float(values.get("bonus", 0))
        final_est = float(values.get("final_exam_est", 0))
        target_str = values.get("target_grade", "A (90%)")

        # Weights: Quizzes 20%, HW 20%, Midterm 25%, Part 10%, Final 25%
        q_pts = (q * 0.30)
        part_pts = (part * 0.10)
        final_pts = (final_est * 0.60)
        final_bonus = (bonus * 0.10)
        current_earned = q_pts + part_pts + final_bonus
        total_projected = current_earned + final_pts

        # Determine target threshold
        target_pct = 90.0
        if "87" in target_str:
            target_pct = 87.0
        elif "83" in target_str:
            target_pct = 83.0
        elif "80" in target_str:
            target_pct = 80.0
        elif "70" in target_str:
            target_pct = 70.0

        # Needed on final: (target_pct - current_earned) / 0.25
        needed_on_final = max(0.0, (target_pct - current_earned) / 0.25)

        # Letter grade lookup
        def _get_letter(score):
            if score >= 93: return "A"
            if score >= 90: return "A-"
            if score >= 87: return "B+"
            if score >= 83: return "B"
            if score >= 80: return "B-"
            if score >= 77: return "C+"
            if score >= 70: return "C"
            if score >= 60: return "D"
            return "F"

        letter = _get_letter(total_projected)
        status_color = "success" if total_projected >= 80 else ("warning" if total_projected >= 70 else "danger")

        # Update Stat Badges
        self.stats.set_metrics({
            "Projected Grade": (f"{total_projected:.1f}%", status_color),
            "Letter Grade": (f"{letter}", status_color),
            "Current Points": (f"{current_earned:.1f} / 75", "info"),
            f"Score Needed for {target_str.split(' ')[0]}": (f"{needed_on_final:.1f}%" if needed_on_final <= 100 else f"{needed_on_final:.1f}% (Extra Needed)", "danger" if needed_on_final > 100 else "primary"),
        })

        # Update Table Breakdown
        rows = [
            ["Quizzes", "30%", f"{q:.1f}%", f"{q_pts:.2f}", "30.00"],
            ["Class Participation", "10%", f"{part:.1f}%", f"{part_pts:.2f}", "10.00"],
            ["Bonus / Extra Credit", "10%", f"{final_bonus:.1f}%", f"{bonus:.2f}", "10.0"],
            ["Projected Final Exam", "60%", f"{final_est:.1f}%", f"{final_pts:.2f}", "60.00"],
            ["--- TOTAL SUMMARY ---", "100%", f"{total_projected:.1f}%", f"{total_projected:.2f}", "100.00"],
        ]
        self.table.set_data(rows)
        self.set_status(f"Calculated: Projected {letter} ({total_projected:.1f}%)")


if __name__ == "__main__":
    app = QuickApp(title="College Grade Estimator", size=(980, 640))
    app.set_single_tool(GradeCalculatorTool)
    app.run()
