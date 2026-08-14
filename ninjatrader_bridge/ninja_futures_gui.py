"""Click-driven, advisory-only Tkinter frontend for the futures scanner."""

from __future__ import annotations

import json
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from urllib.error import URLError
from urllib.request import urlopen


SNAPSHOT_URL = "http://127.0.0.1:8765/snapshot"
CONFIG_PATH = Path(__file__).with_name("ninja_futures_config.json")
# A single snapshot can contain 11 indicator calculations.  Do not queue a
# second request while the first one is still being served.
POLL_MS = 3000
PREP_SCORE = 70
ALERT_LATCH_SECONDS = 120


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return default


class FuturesScannerGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NinjaTrader Futures Scanner — Advisory Only")
        self.geometry("1180x720")
        self.minsize(980, 620)
        self.configure(bg="#10151c")

        self.rows = {}
        self.previous_alert_states = {}
        self.alerts = []
        self.first_snapshot = True
        self.selected_symbol = None
        self.flash_remaining = 0
        self.flash_on = False
        self.snapshot_in_flight = False
        try:
            self.settings = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("signal_engine", {})
        except (OSError, ValueError, json.JSONDecodeError):
            self.settings = {}

        self.status_var = tk.StringVar(value="Connecting to scanner…")
        self.alert_var = tk.StringVar(value="No recent PREP or READY alerts")
        self.quantity_var = tk.IntVar(value=1)
        self.profit_goal_var = tk.StringVar(
            value=f"{number(self.settings.get('manual_profit_goal_dollars'), 250.0):.2f}"
        )
        self.always_on_top_var = tk.BooleanVar(value=False)

        self._configure_styles()
        self._build_layout()
        self.after(100, self.poll)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.Treeview", background="#151c25", foreground="#e7edf5",
                        fieldbackground="#151c25", rowheight=30, borderwidth=0)
        style.configure("Dark.Treeview.Heading", background="#263241", foreground="#ffffff")
        style.map("Dark.Treeview", background=[("selected", "#315a7d")])
        style.configure("Dark.TFrame", background="#10151c")
        style.configure("Dark.TLabel", background="#10151c", foreground="#dce6f2")

    def _build_layout(self):
        header = tk.Frame(self, bg="#10151c")
        header.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(header, text="FUTURES CONFLUENCE SCANNER", bg="#10151c", fg="#ffffff",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Checkbutton(header, text="Always on top", variable=self.always_on_top_var,
                       command=self.toggle_topmost, bg="#10151c", fg="#cbd7e5",
                       selectcolor="#263241", activebackground="#10151c").pack(side="right")

        self.alert_banner = tk.Label(
            self, textvariable=self.alert_var, bg="#263241", fg="#ffffff",
            anchor="w", padx=12, pady=9, font=("Segoe UI", 11, "bold")
        )
        self.alert_banner.pack(fill="x", padx=12, pady=5)

        body = tk.PanedWindow(self, orient="horizontal", sashwidth=6, bg="#10151c")
        body.pack(fill="both", expand=True, padx=12, pady=5)

        left = tk.Frame(body, bg="#10151c", width=330)
        right = tk.Frame(body, bg="#10151c")
        body.add(left, minsize=300)
        body.add(right, minsize=620)

        self.tree = ttk.Treeview(
            left, columns=("state", "score", "direction", "fast"), show="tree headings",
            style="Dark.Treeview", selectmode="browse"
        )
        self.tree.heading("#0", text="SYMBOL")
        self.tree.heading("state", text="STATE")
        self.tree.heading("score", text="SCORE")
        self.tree.heading("direction", text="DIR")
        self.tree.heading("fast", text="FAST")
        self.tree.column("#0", width=68, anchor="center")
        self.tree.column("state", width=78, anchor="center")
        self.tree.column("score", width=54, anchor="center")
        self.tree.column("direction", width=58, anchor="center")
        self.tree.column("fast", width=62, anchor="center")
        for tag, color in {
            "READY": "#176b3a", "PREP": "#755500", "WATCH": "#594a16",
            "WAIT": "#27313d", "WARMING": "#174f62", "STALE": "#6c2424",
            "ILLIQUID": "#3a3a43",
        }.items():
            self.tree.tag_configure(tag, background=color, foreground="#ffffff")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="both", expand=True)

        title_row = tk.Frame(right, bg="#10151c")
        title_row.pack(fill="x")
        self.detail_title = tk.Label(title_row, text="Select a symbol", bg="#10151c",
                                     fg="#ffffff", font=("Segoe UI", 18, "bold"))
        self.detail_title.pack(side="left")
        tk.Label(title_row, text="Contracts:", bg="#10151c", fg="#cbd7e5").pack(side="right")
        quantity = tk.Spinbox(title_row, from_=1, to=50, width=4, textvariable=self.quantity_var,
                              command=self.render_selected, font=("Segoe UI", 11))
        quantity.pack(side="right", padx=7)
        quantity.bind("<KeyRelease>", lambda _event: self.render_selected())

        tk.Label(title_row, text="Profit goal $:", bg="#10151c", fg="#cbd7e5").pack(side="right", padx=(10, 0))
        profit_goal_entry = tk.Entry(title_row, width=8, textvariable=self.profit_goal_var,
                                     font=("Segoe UI", 11), bg="#1c2530", fg="#ffffff",
                                     insertbackground="#ffffff")
        profit_goal_entry.pack(side="right", padx=7)
        profit_goal_entry.bind("<KeyRelease>", lambda _event: self.render_selected())
        profit_goal_entry.bind("<Return>", lambda _event: (self.render_selected(), self.focus_set()))

        self.summary = tk.Label(right, text="", justify="left", anchor="nw", bg="#17202b",
                                fg="#ffffff", padx=16, pady=12, font=("Consolas", 12, "bold"))
        self.summary.pack(fill="x", pady=(8, 6))

        self.gates = tk.Label(right, text="", justify="left", anchor="nw", bg="#10151c",
                              fg="#dce6f2", padx=8, pady=8, font=("Segoe UI", 11))
        self.gates.pack(fill="both", expand=True)

        tk.Label(right, text="RECENT ALERTS", bg="#10151c", fg="#9fb4ca",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=6)
        self.alert_history = tk.Listbox(right, height=5, bg="#151c25", fg="#ffffff",
                                        selectbackground="#315a7d", borderwidth=0,
                                        font=("Consolas", 10))
        self.alert_history.pack(fill="x", padx=6, pady=(3, 0))

        tk.Label(self, textvariable=self.status_var, bg="#10151c", fg="#91a5ba",
                 anchor="w").pack(fill="x", padx=14, pady=(0, 8))

    def toggle_topmost(self):
        self.attributes("-topmost", bool(self.always_on_top_var.get()))

    def poll(self):
        if not self.snapshot_in_flight:
            self.snapshot_in_flight = True
            threading.Thread(target=self._fetch_snapshot, daemon=True).start()
        self.after(POLL_MS, self.poll)

    def _fetch_snapshot(self):
        try:
            with urlopen(SNAPSHOT_URL, timeout=8.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.after(0, self.apply_snapshot, payload)
        except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
            self.after(0, self.status_var.set, f"Scanner unavailable: {exc}")
        finally:
            self.after(0, self._finish_snapshot_request)

    def _finish_snapshot_request(self):
        self.snapshot_in_flight = False

    @staticmethod
    def display_state(row):
        if row.get("state") == "WATCH" and int(row.get("score", 0)) >= PREP_SCORE:
            return "PREP"
        return row.get("state", "WAIT")

    def apply_snapshot(self, payload):
        bridge = payload.get("bridge", {})
        bridge_age = bridge.get("age_seconds")
        bridge_text = "--" if bridge_age is None else f"{bridge_age:.0f}s"
        self.status_var.set(
            f"Bridge {'ALIVE' if bridge.get('alive') else 'NO HEARTBEAT'} · "
            f"heartbeat {bridge_text} · subscriptions {bridge.get('subscriptions', 0)} · "
            f"updated {datetime.now().strftime('%H:%M:%S')}"
        )

        incoming = {row["symbol"]: row for row in payload.get("contracts", [])}
        self.rows = incoming
        for symbol, row in incoming.items():
            state = self.display_state(row)
            values = (state, row.get("score", 0), str(row.get("direction", "wait")).upper(),
                      row.get("trend_state", "WAIT"))
            if self.tree.exists(symbol):
                self.tree.item(symbol, text=symbol, values=values, tags=(state,))
            else:
                self.tree.insert("", "end", iid=symbol, text=symbol, values=values, tags=(state,))

            previous = self.previous_alert_states.get(symbol)
            if not self.first_snapshot and state in ("PREP", "READY") and previous != state:
                self.record_alert(symbol, row, state)
            self.previous_alert_states[symbol] = state

        self.first_snapshot = False
        if self.selected_symbol not in incoming and incoming:
            self.selected_symbol = next(iter(incoming))
            self.tree.selection_set(self.selected_symbol)
        self.render_selected()
        self.refresh_latched_banner()

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if selection:
            self.selected_symbol = selection[0]
            self.render_selected()

    def render_selected(self):
        row = self.rows.get(self.selected_symbol)
        if not row:
            return
        metrics = row.get("metrics") or {}
        state = self.display_state(row)
        direction = str(row.get("direction", "wait")).upper()
        try:
            quantity = max(1, int(self.quantity_var.get() or 1))
        except (tk.TclError, TypeError, ValueError):
            quantity = 1
        contract = row.get("contract") or {}
        tick_size = number(contract.get("tick_size"))
        tick_value = number(contract.get("tick_value"))
        point_value = tick_value / tick_size if tick_size > 0 else 0.0
        profit_goal = number(self.profit_goal_var.get(), 250.0)
        goal_points = profit_goal / (point_value * quantity) if point_value > 0 else 0.0
        vwap_label = "complete" if metrics.get("vwap_complete") else "provisional"
        trends = metrics.get("trends") or {}

        self.detail_title.configure(text=f"{row['symbol']}  ·  {state} {row.get('score', 0)}  ·  {direction}")
        if not metrics:
            self.summary.configure(text=row.get("reason", "Waiting for indicator history"))
            self.gates.configure(text=(
                f"Bars received: {row.get('bars', 0)}\n"
                f"Original FAST: {row.get('trend_state')} {row.get('trend_score')}\n\n"
                f"{row.get('trend_reason', '')}"
            ))
            return
        summary_lines = [
            f"YOUR ${profit_goal:.0f} GOAL {goal_points:>7.2f} pt  "
            f"({quantity} contract{'s' if quantity != 1 else ''})",
            f"CURRENT ATR     {number(metrics.get('atr')):>7.2f} pt  (volatility, not a target)",
            f"S/R             {number(metrics.get('support')):.2f} / {number(metrics.get('resistance')):.2f}",
        ]
        self.summary.configure(text="\n".join(summary_lines))
        self.gates.configure(text=(
            f"EMA 8/20       {number(metrics.get('ema_fast')):.2f} / {number(metrics.get('ema_slow')):.2f}\n"
            f"EMA widening   {'YES' if metrics.get('ema_widening') else 'NO'}\n"
            f"VWAP           {number(metrics.get('vwap')):.2f} ({vwap_label})\n"
            f"VWAP bounce    {'CONFIRMED' if metrics.get('vwap_confirmation') else 'not confirmed'}\n\n"
            f"ADX            {number(metrics.get('adx')):.1f}  (trend threshold 25)\n"
            f"RSI            {number(metrics.get('rsi')):.1f}\n"
            f"MACD / signal  {number(metrics.get('macd')):.3f} / {number(metrics.get('macd_signal')):.3f}\n"
            f"Choppiness     {number(metrics.get('choppiness')):.1f}  (lower is smoother)\n"
            f"ATR            {number(metrics.get('atr')):.2f}\n\n"
            f"Timeframes     1m {str(trends.get('1m', '?')).upper()}   "
            f"3m {str(trends.get('3m', '?')).upper()}   15m {str(trends.get('15m', '?')).upper()}\n"
            f"Original FAST  {row.get('trend_state')} {row.get('trend_score')} — {row.get('trend_reason')}\n\n"
            f"Current detail: {row.get('reason')}"
        ))

    def record_alert(self, symbol, row, state):
        alert = {
            "at": time.time(), "clock": datetime.now().strftime("%H:%M:%S"),
            "symbol": symbol, "state": state, "score": row.get("score", 0),
            "direction": str(row.get("direction", "wait")).upper(),
        }
        self.alerts.insert(0, alert)
        self.alerts = self.alerts[:30]
        self.alert_history.insert(
            0, f"{alert['clock']}  {symbol:<4} {state:<5} {alert['score']:>3}  {alert['direction']}"
        )
        if self.alert_history.size() > 30:
            self.alert_history.delete(30, "end")
        self.play_alert(state)
        self.flash_remaining = 8
        self.flash_banner()

    def play_alert(self, state):
        if not self.settings.get("sound_alerts", True):
            return

        def worker():
            try:
                if os.name == "nt":
                    import winsound
                    if state == "READY":
                        winsound.Beep(1250, 180); winsound.Beep(1550, 260)
                    else:
                        winsound.Beep(850, 180)
                else:
                    print("\a", end="", flush=True)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def flash_banner(self):
        if self.flash_remaining <= 0:
            self.flash_on = False
            self.refresh_latched_banner()
            return
        self.flash_on = not self.flash_on
        self.alert_banner.configure(bg="#35a85b" if self.flash_on else "#173d27")
        self.flash_remaining -= 1
        self.after(250, self.flash_banner)

    def refresh_latched_banner(self):
        now = time.time()
        recent = next((item for item in self.alerts if now - item["at"] <= ALERT_LATCH_SECONDS), None)
        if not recent:
            self.alert_var.set("No PREP or READY alerts in the last two minutes")
            if self.flash_remaining <= 0:
                self.alert_banner.configure(bg="#263241")
            return
        age = int(now - recent["at"])
        self.alert_var.set(
            f"LAST ALERT: {recent['symbol']} {recent['state']} {recent['score']} "
            f"{recent['direction']} · {age}s ago"
        )
        if self.flash_remaining <= 0:
            self.alert_banner.configure(bg="#176b3a" if recent["state"] == "READY" else "#755500")


if __name__ == "__main__":
    FuturesScannerGui().mainloop()
