"""
Output components for QuickTk:
- DataTable: Treeview wrapper with sorting, search filter, and CSV export.
- StatGrid: KPI summary metric badges / cards.
- ConsolePanel: Scrollable rich text / code console with coloring tags.
"""

import csv
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class StatGrid(ttk.Frame):
    """
    A grid of modern metric / KPI cards displaying key stats (e.g. Win Rate, Max Drawdown).
    """

    def __init__(self, parent: tk.Widget, columns: int = 4, theme: dict = None, **kwargs):
        super().__init__(parent, style="TFrame", **kwargs)
        self.theme = theme or {}
        self.num_columns = columns
        self._cards: Dict[str, Dict[str, Any]] = {}
        for c in range(columns):
            self.columnconfigure(c, weight=1)

    def set_metrics(self, metrics: Dict[str, Union[str, int, float, Tuple[str, str]]]):
        """
        Populates or updates metric cards.
        Accepts dict of {Title: Value} or {Title: (Value, 'success'|'danger'|'info'|'warning')}
        """
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()
        self._cards.clear()

        row = 0
        col = 0
        for title, val_data in metrics.items():
            val_str = str(val_data[0]) if isinstance(val_data, tuple) else str(val_data)
            status = val_data[1] if isinstance(val_data, tuple) else "info"

            card = ttk.Frame(self, style="Card.TFrame", padding=10)
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            card.columnconfigure(0, weight=1)

            # Title label
            t_lbl = ttk.Label(card, text=title.upper(), style="DimCard.TLabel", font=("Segoe UI", 8, "bold"))
            t_lbl.grid(row=0, column=0, sticky="w")

            # Value label
            fg_color = self.theme.get("text_highlight", "#ffffff")
            if status == "success":
                fg_color = self.theme.get("success", "#16a34a")
            elif status == "danger":
                fg_color = self.theme.get("danger", "#dc2626")
            elif status == "warning":
                fg_color = self.theme.get("warning", "#d97706")
            elif status == "primary":
                fg_color = self.theme.get("primary", "#2563eb")

            v_lbl = tk.Label(
                card,
                text=val_str,
                bg=self.theme.get("card_bg", "#ffffff"),
                fg=fg_color,
                font=("Segoe UI", 16, "bold"),
                anchor="w",
            )
            v_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))

            self._cards[title] = {"card": card, "title_lbl": t_lbl, "val_lbl": v_lbl}

            col += 1
            if col >= self.num_columns:
                col = 0
                row += 1


class DataTable(ttk.Frame):
    """
    High-level tabular Treeview wrapper supporting instant data loading,
    column sorting, search filtering, row selection events, and CSV export.
    """

    def __init__(
        self,
        parent: tk.Widget,
        columns: Optional[List[str]] = None,
        enable_search: bool = True,
        enable_export_csv: bool = True,
        theme: dict = None,
        **kwargs,
    ):
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        self.theme = theme or {}
        self._columns = columns or []
        self._raw_data: List[List[Any]] = []
        self._sort_reverse: Dict[str, bool] = {}
        self._on_select_cb: Optional[Callable[[Dict[str, Any]], None]] = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top Control Bar (Search & Export)
        top_bar = ttk.Frame(self, style="Surface.TFrame")
        top_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        top_bar.columnconfigure(1, weight=1)

        col_idx = 0
        if enable_search:
            s_lbl = ttk.Label(top_bar, text="Filter:", style="Surface.TLabel")
            s_lbl.grid(row=0, column=col_idx, sticky="w", padx=(0, 6))
            col_idx += 1

            self._search_var = tk.StringVar()
            self._search_var.trace_add("write", lambda *args: self._apply_search())
            search_entry = ttk.Entry(top_bar, textvariable=self._search_var)
            search_entry.grid(row=0, column=col_idx, sticky="ew", padx=(0, 10))
            col_idx += 1

        self._row_count_lbl = ttk.Label(top_bar, text="0 rows", style="Dim.TLabel")
        self._row_count_lbl.grid(row=0, column=col_idx, sticky="e", padx=(0, 10))
        col_idx += 1

        if enable_export_csv:
            export_btn = ttk.Button(top_bar, text="Export CSV", command=self.export_csv)
            export_btn.grid(row=0, column=col_idx, sticky="e")
            col_idx += 1

        # Treeview + Scrollbars
        table_container = ttk.Frame(self, style="Surface.TFrame")
        table_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        table_container.columnconfigure(0, weight=1)
        table_container.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_container, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.tree.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._handle_selection)

        if self._columns:
            self.set_columns(self._columns)

    def set_columns(self, columns: List[str]):
        """Sets the column headers and enables click-to-sort."""
        self._columns = columns
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, minwidth=60, width=120, anchor="w")
            self._sort_reverse[col] = False

    def set_data(self, data: Union[List[List[Any]], List[Dict[str, Any]]]):
        """Populates the table with rows (list of lists or list of dicts)."""
        self._raw_data.clear()
        if not data:
            self._refresh_view([])
            return

        if isinstance(data[0], dict):
            # Auto populate columns if not set
            if not self._columns:
                self.set_columns(list(data[0].keys()))
            # Convert dicts to ordered row lists
            for item in data:
                row = [item.get(c, "") for c in self._columns]
                self._raw_data.append(row)
        else:
            self._raw_data = [list(r) for r in data]

        self._refresh_view(self._raw_data)

    def _refresh_view(self, rows: List[List[Any]]):
        """Rerenders rows inside treeview with zebra striping."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        even_bg = self.theme.get("tree_even", "#f9fafb")
        odd_bg = self.theme.get("tree_bg", "#ffffff")

        self.tree.tag_configure("even", background=even_bg)
        self.tree.tag_configure("odd", background=odd_bg)

        for idx, row in enumerate(rows):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=row, tags=(tag,))

        self._row_count_lbl.config(text=f"{len(rows):,} rows")

    def _sort_column(self, col: str):
        """Sorts data by the selected column header."""
        if col not in self._columns:
            return
        col_idx = self._columns.index(col)
        rev = self._sort_reverse.get(col, False)

        def _sort_key(r):
            val = r[col_idx]
            try:
                # Try numeric sort first
                clean_val = str(val).replace("$", "").replace("%", "").replace(",", "").strip()
                return (0, float(clean_val))
            except Exception:
                return (1, str(val).lower())

        self._raw_data.sort(key=_sort_key, reverse=rev)
        self._sort_reverse[col] = not rev
        self._apply_search()

    def _apply_search(self):
        """Filters table data according to search string."""
        query = self._search_var.get().lower().strip() if hasattr(self, "_search_var") else ""
        if not query:
            self._refresh_view(self._raw_data)
            return

        filtered = [
            row for row in self._raw_data
            if any(query in str(cell).lower() for cell in row)
        ]
        self._refresh_view(filtered)

    def _handle_selection(self, event):
        selected_items = self.tree.selection()
        if not selected_items or not self._on_select_cb:
            return
        item = selected_items[0]
        values = self.tree.item(item, "values")
        if self._columns and len(values) == len(self._columns):
            row_dict = dict(zip(self._columns, values))
            self._on_select_cb(row_dict)

    def on_select(self, callback: Callable[[Dict[str, Any]], None]):
        """Sets a callback triggered when a row is selected."""
        self._on_select_cb = callback

    def get_selected_row(self) -> Optional[Dict[str, Any]]:
        """Returns the currently selected row as a dictionary."""
        selected_items = self.tree.selection()
        if not selected_items:
            return None
        values = self.tree.item(selected_items[0], "values")
        return dict(zip(self._columns, values)) if self._columns else None

    def export_csv(self, filepath: Optional[str] = None):
        """Exports the current table data to a CSV file."""
        if not self._raw_data:
            messagebox.showinfo("Export CSV", "No data to export.")
            return

        if not filepath:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="Export Table to CSV",
            )

        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if self._columns:
                    writer.writerow(self._columns)
                writer.writerows(self._raw_data)
            messagebox.showinfo("Export Successful", f"Saved {len(self._raw_data)} rows to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error exporting CSV: {e}")


class ConsolePanel(ttk.Frame):
    """
    A scrollable terminal / log / syntax-highlighted code console.
    """

    def __init__(self, parent: tk.Widget, title: Optional[str] = None, theme: dict = None, **kwargs):
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        self.theme = theme or {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        row_idx = 0
        if title:
            header_bar = ttk.Frame(self, style="Surface.TFrame")
            header_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
            header_bar.columnconfigure(0, weight=1)

            lbl = ttk.Label(header_bar, text=title, style="Heading.TLabel")
            lbl.grid(row=0, column=0, sticky="w")

            clear_btn = ttk.Button(header_bar, text="Clear", command=self.clear)
            clear_btn.grid(row=0, column=1, sticky="e", padx=(0, 4))

            copy_btn = ttk.Button(header_bar, text="Copy All", command=self.copy_all)
            copy_btn.grid(row=0, column=2, sticky="e")
            row_idx = 1

        box = ttk.Frame(self, style="Surface.TFrame")
        box.grid(row=row_idx, column=0, sticky="nsew", padx=8, pady=(0, 8))
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)

        bg = self.theme.get("console_bg", "#181825")
        fg = self.theme.get("console_fg", "#cdd6f4")

        self.text_widget = tk.Text(
            box,
            wrap="word",
            bg=bg,
            fg=fg,
            insertbackground=fg,
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(box, orient="vertical", command=self.text_widget.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.text_widget.configure(yscrollcommand=v_scroll.set)

        self._setup_tags()

    def _setup_tags(self):
        t = self.theme
        self.text_widget.tag_configure("info", foreground=t.get("text", "#cdd6f4"))
        self.text_widget.tag_configure("success", foreground=t.get("success", "#a6e3a1"))
        self.text_widget.tag_configure("danger", foreground=t.get("danger", "#f38ba8"))
        self.text_widget.tag_configure("warning", foreground=t.get("warning", "#f9e2af"))
        self.text_widget.tag_configure("primary", foreground=t.get("primary", "#89b4fa"))
        self.text_widget.tag_configure("dim", foreground=t.get("text_dim", "#a6adc8"))
        self.text_widget.tag_configure("heading", foreground=t.get("primary", "#89b4fa"), font=("Consolas", 11, "bold"))
        self.text_widget.tag_configure("code_kw", foreground=t.get("danger", "#f38ba8"), font=("Consolas", 10, "bold"))
        self.text_widget.tag_configure("code_str", foreground=t.get("success", "#a6e3a1"))
        self.text_widget.tag_configure("code_comment", foreground=t.get("text_dim", "#a6adc8"), font=("Consolas", 10, "italic"))

    def write(self, text: str, tag: Optional[str] = None):
        """Appends text to the console, optionally with a style tag."""
        self.text_widget.config(state="normal")
        if tag:
            self.text_widget.insert("end", text, tag)
        else:
            self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.config(state="disabled")

    def write_line(self, text: str = "", tag: Optional[str] = None):
        """Appends a line of text."""
        self.write(text + "\n", tag)

    def write_heading(self, text: str):
        """Appends a styled section header."""
        divider = "=" * max(40, len(text))
        self.write(f"\n{divider}\n  {text}\n{divider}\n", "heading")

    def write_code(self, code_str: str):
        """Appends code with basic syntax highlighting."""
        self.text_widget.config(state="normal")
        keywords = {"def", "class", "import", "from", "return", "if", "elif", "else", "for", "while", "in", "try", "except", "with", "as", "lambda", "yield"}

        lines = code_str.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                self.text_widget.insert("end", line + "\n", "code_comment")
                continue

            tokens = line.split(" ")
            for idx, tok in enumerate(tokens):
                if tok in keywords:
                    self.text_widget.insert("end", tok, "code_kw")
                elif (tok.startswith('"') and tok.endswith('"')) or (tok.startswith("'") and tok.endswith("'")):
                    self.text_widget.insert("end", tok, "code_str")
                else:
                    self.text_widget.insert("end", tok)
                if idx < len(tokens) - 1:
                    self.text_widget.insert("end", " ")
            self.text_widget.insert("end", "\n")

        self.text_widget.see("end")
        self.text_widget.config(state="disabled")

    def clear(self):
        """Clears all text in the console."""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.config(state="disabled")

    def copy_all(self):
        """Copies all text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self.text_widget.get("1.0", "end-1c"))

    def get_text(self) -> str:
        """Returns entire text content."""
        return self.text_widget.get("1.0", "end-1c")


class ImagePanel(ttk.Frame):
    """
    A modern image preview container that automatically scales images to fit
    within its frame bounds while preserving aspect ratio, and keeps PhotoImage
    references alive to prevent garbage collection blanking.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: Optional[str] = "Image Preview",
        max_size: Tuple[int, int] = (450, 350),
        theme: dict = None,
        **kwargs,
    ):
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        self.theme = theme or {}
        self.max_width, self.max_height = max_size
        self._current_image = None
        self._photo_ref = None  # Crucial: prevents Python GC from blanking image

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        row_idx = 0
        if title:
            header_bar = ttk.Frame(self, style="Surface.TFrame")
            header_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
            header_bar.columnconfigure(0, weight=1)

            lbl = ttk.Label(header_bar, text=title, style="Heading.TLabel")
            lbl.grid(row=0, column=0, sticky="w")
            row_idx = 1

        # Canvas/Label container for the image
        self.image_container = ttk.Frame(self, style="Card.TFrame", padding=6)
        self.image_container.grid(row=row_idx, column=0, sticky="nsew", padx=8, pady=4)
        self.image_container.columnconfigure(0, weight=1)
        self.image_container.rowconfigure(0, weight=1)

        bg = self.theme.get("card_bg", "#1e1e2e")
        self.img_label = tk.Label(
            self.image_container,
            text="No Image Loaded",
            bg=bg,
            fg=self.theme.get("text_dim", "#a6adc8"),
            font=("Segoe UI", 10),
            justify="center",
        )
        self.img_label.grid(row=0, column=0, sticky="nsew")

        # Info subtitle bar (dimensions, filesize)
        self.info_lbl = ttk.Label(self, text="Ready", style="Dim.TLabel", anchor="center")
        self.info_lbl.grid(row=row_idx + 1, column=0, sticky="ew", padx=8, pady=(2, 6))

    def set_image(self, image_or_path: Union[str, Any, None], info_text: Optional[str] = None):
        """
        Loads and displays an image from a filepath or PIL Image object.
        Automatically scales the image proportionally to fit within max_size.
        """
        if not image_or_path:
            self.clear()
            return

        if not HAS_PIL:
            self.img_label.config(text="PIL (Pillow) required for image preview.\nInstall with: pip install Pillow", image="")
            return

        try:
            if isinstance(image_or_path, str):
                if not os.path.exists(image_or_path):
                    self.img_label.config(text=f"File not found:\n{os.path.basename(image_or_path)}", image="")
                    return
                im = Image.open(image_or_path)
                orig_w, orig_h = im.size
                fsize = os.path.getsize(image_or_path) / 1024
                details = f"{orig_w}x{orig_h} px | {fsize:.1f} KB | {os.path.basename(image_or_path)}"
            else:
                im = image_or_path
                orig_w, orig_h = im.size
                details = f"{orig_w}x{orig_h} px (In-Memory Image)"

            # Scale to fit proportionally within max_width and max_height
            scale = min(self.max_width / orig_w, self.max_height / orig_h, 1.0)
            target_w = max(1, int(orig_w * scale))
            target_h = max(1, int(orig_h * scale))

            # Resample image
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
            resized = im.resize((target_w, target_h), resample=resample_filter)

            # Convert to ImageTk PhotoImage
            photo = ImageTk.PhotoImage(resized)
            self._photo_ref = photo  # Keep reference alive!
            self._current_image = im

            self.img_label.config(image=photo, text="")
            self.info_lbl.config(text=info_text or details)

        except Exception as ex:
            self.img_label.config(text=f"Error previewing image:\n{ex}", image="")
            self._photo_ref = None

    def clear(self):
        """Clears the image and displays empty placeholder."""
        self._current_image = None
        self._photo_ref = None
        self.img_label.config(text="No Image Loaded", image="")
        self.info_lbl.config(text="Ready")


def show_image_window(
    image_or_path: Union[str, Any],
    title: str = "Converted Image",
    parent_root: Optional[tk.Widget] = None,
    max_display_size: Tuple[int, int] = (900, 700),
) -> Optional[tk.Toplevel]:
    """
    Opens a clean, dedicated separate Tkinter window (Toplevel) displaying the image
    scaled to fit the screen without requiring external default OS image viewers.
    """
    if not HAS_PIL:
        messagebox.showerror("Pillow Required", "PIL (Pillow) is required to display image windows.")
        return None

    try:
        if isinstance(image_or_path, str):
            if not os.path.exists(image_or_path):
                messagebox.showerror("File Error", f"Image file not found:\n{image_or_path}")
                return None
            im = Image.open(image_or_path)
            win_title = f"{title} - {os.path.basename(image_or_path)}"
            orig_w, orig_h = im.size
            fsize = os.path.getsize(image_or_path) / 1024
            info_str = f"Dimensions: {orig_w}x{orig_h} px | Size: {fsize:.1f} KB | Format: {im.format or os.path.splitext(image_or_path)[1].upper()}"
        else:
            im = image_or_path
            orig_w, orig_h = im.size
            win_title = title
            info_str = f"Dimensions: {orig_w}x{orig_h} px"

        # Create separate Toplevel window
        win = tk.Toplevel(parent_root)
        win.title(win_title)
        win.configure(bg="#181825")

        # Calculate proportional fit for window display
        max_w, max_h = max_display_size
        scale = min(max_w / orig_w, max_h / orig_h, 1.0)
        disp_w = max(1, int(orig_w * scale))
        disp_h = max(1, int(orig_h * scale))

        resample_filter = getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
        disp_img = im.resize((disp_w, disp_h), resample=resample_filter)
        photo = ImageTk.PhotoImage(disp_img)
        win._photo_ref = photo  # Keep reference alive on window object

        # Layout
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)

        # Image label
        lbl = tk.Label(win, image=photo, bg="#181825")
        lbl.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="nsew")

        # Bottom info and close bar
        bar = ttk.Frame(win, padding=(12, 6))
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)

        meta_lbl = ttk.Label(bar, text=info_str, style="Dim.TLabel")
        meta_lbl.grid(row=0, column=0, sticky="w")

        close_btn = ttk.Button(bar, text="Close Window", command=win.destroy)
        close_btn.grid(row=0, column=1, sticky="e")

        return win

    except Exception as e:
        messagebox.showerror("Error Opening Image", f"Failed to load image:\n{e}")
        return None
