"""
Analyze exported trade CSV dumps without relying on fragile spreadsheet formulas.

Usage:
    python Scripts/analyze_trade_dump.py path\to\trades.csv

The script accepts CSVs from the dashboard closed-trades panel, DB tool exports,
or custom trade queries. It detects common columns by header name and writes
summary CSVs plus a small HTML index under reports/trade_dump_analysis/.
"""

from __future__ import annotations

import argparse
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "reports" / "trade_dump_analysis"


SECTION_TITLES = {
    "summary_by_strategy.csv": (
        "Summary By Strategy",
        "P&L, win rate, average win/loss, and profit factor grouped by strategy.",
    ),
    "summary_by_exit_reason.csv": (
        "Summary By Exit Reason",
        "Shows which exit paths are making or losing money.",
    ),
    "summary_by_symbol_top100.csv": (
        "Summary By Symbol",
        "Top 100 symbols by total P&L in this dump.",
    ),
    "scanner_trades.csv": (
        "Scanner Trades",
        "Raw rows for strategies with 'scanner' in the strategy name.",
    ),
    "green_then_red_mfe_ge_1_5.csv": (
        "Green Then Red",
        "Trades that were up at least 1.5% but still closed at breakeven/loss.",
    ),
    "big_winners_ge_50.csv": (
        "Big Winners",
        "Trades with P&L of $50 or more.",
    ),
    "trades_with_partials.csv": (
        "Trades With Partials",
        "Trades where at least one partial exit was recorded.",
    ),
    "mfe_mae_audit.csv": (
        "MFE / MAE Audit",
        "Maximum favorable and adverse excursion by trade.",
    ),
    "normalized_input.csv": (
        "Normalized Input",
        "Original dump with standardized column names.",
    ),
}


ALIASES = {
    "symbol": ["symbol", "ticker"],
    "strategy": ["strategy_name", "strategy", "strat"],
    "direction": ["direction", "side"],
    "status": ["status"],
    "asset_class": ["asset_class", "asset", "class"],
    "entry_time": ["entry_time", "entry", "opened", "open_time"],
    "exit_time": ["exit_time", "exit", "closed", "close_time"],
    "entry_price": ["entry_price", "entry"],
    "exit_price": ["exit_price", "exit"],
    "pnl": ["pnl", "profit_loss", "profit", "net_pnl", "p_l"],
    "pnl_pct": ["pnl_pct", "pnl_percent", "pnl_%", "return_pct", "return_%"],
    "fees_paid": ["fees_paid", "fees", "commission"],
    "exit_reason": ["exit_reason", "reason"],
    "mfe_pct": ["mfe_pct", "max_favorable", "max_favorable_pct"],
    "mae_pct": ["mae_pct", "max_adverse", "max_adverse_pct"],
    "partial_exit_count": ["partial_exit_count", "partials"],
    "partial_pnl": ["partial_pnl"],
    "position_value": ["position_value", "value", "notional"],
    "trade_id": ["trade_id", "id"],
}


def normalize_header(name: str) -> str:
    text = str(name or "").strip().lower()
    text = text.replace("%", "pct")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def money_to_number(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.replace(r"[$,%+,]", "", regex=True)
    text = text.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    return pd.to_numeric(text, errors="coerce")


def first_present(columns: Iterable[str], canonical: str) -> str | None:
    column_set = set(columns)
    for candidate in ALIASES.get(canonical, [canonical]):
        normalized = normalize_header(candidate)
        if normalized in column_set:
            return normalized
    return None


def load_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        df = pd.read_csv(path)

    df = df.rename(columns={col: normalize_header(col) for col in df.columns})
    df = df.dropna(axis=1, how="all")
    for canonical in (
        "pnl", "pnl_pct", "fees_paid", "mfe_pct", "mae_pct",
        "partial_exit_count", "partial_pnl", "position_value",
        "entry_price", "exit_price",
    ):
        col = first_present(df.columns, canonical)
        if col:
            df[col] = money_to_number(df[col])
    return df


def write_csv(df: pd.DataFrame, out_dir: Path, name: str) -> Path | None:
    if df is None or df.empty:
        return None
    path = out_dir / name
    df.to_csv(path, index=False)
    return path


def summary_by_group(df: pd.DataFrame, group_col: str, pnl_col: str) -> pd.DataFrame:
    grouped = df.groupby(group_col, dropna=False)
    result = grouped.agg(
        trades=(pnl_col, "count"),
        wins=(pnl_col, lambda s: int((s > 0).sum())),
        losses=(pnl_col, lambda s: int((s <= 0).sum())),
        total_pnl=(pnl_col, "sum"),
        avg_pnl=(pnl_col, "mean"),
        avg_win=(pnl_col, lambda s: float(s[s > 0].mean()) if (s > 0).any() else 0.0),
        avg_loss=(pnl_col, lambda s: float(s[s <= 0].mean()) if (s <= 0).any() else 0.0),
        gross_wins=(pnl_col, lambda s: float(s[s > 0].sum())),
        gross_losses=(pnl_col, lambda s: float(abs(s[s <= 0].sum()))),
    ).reset_index()
    result["win_rate_pct"] = (result["wins"] / result["trades"] * 100).round(1)
    result["profit_factor"] = result.apply(
        lambda r: round(r["gross_wins"] / r["gross_losses"], 3)
        if r["gross_losses"] else None,
        axis=1,
    )
    for col in ("total_pnl", "avg_pnl", "avg_win", "avg_loss", "gross_wins", "gross_losses"):
        result[col] = result[col].round(4)
    ordered = result.sort_values("total_pnl", ascending=False)
    return append_total_row(ordered, group_col, pnl_col, df)


def append_total_row(
    result: pd.DataFrame, label_col: str, pnl_col: str, source: pd.DataFrame
) -> pd.DataFrame:
    pnl = source[pnl_col].dropna()
    if pnl.empty:
        return result
    gross_losses = float(abs(pnl[pnl <= 0].sum()))
    total = {
        label_col: "TOTAL",
        "trades": int(pnl.count()),
        "wins": int((pnl > 0).sum()),
        "losses": int((pnl <= 0).sum()),
        "total_pnl": round(float(pnl.sum()), 4),
        "avg_pnl": round(float(pnl.mean()), 4),
        "avg_win": round(float(pnl[pnl > 0].mean()), 4) if (pnl > 0).any() else 0.0,
        "avg_loss": round(float(pnl[pnl <= 0].mean()), 4) if (pnl <= 0).any() else 0.0,
        "gross_wins": round(float(pnl[pnl > 0].sum()), 4),
        "gross_losses": round(gross_losses, 4),
        "win_rate_pct": round(float((pnl > 0).sum() / pnl.count() * 100), 1),
        "profit_factor": (
            round(float(pnl[pnl > 0].sum()) / gross_losses, 3)
            if gross_losses else None
        ),
    }
    return pd.concat([result, pd.DataFrame([total])], ignore_index=True)


def build_outputs(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    pnl_col = first_present(df.columns, "pnl")
    strategy_col = first_present(df.columns, "strategy")
    exit_col = first_present(df.columns, "exit_reason")
    symbol_col = first_present(df.columns, "symbol")
    mfe_col = first_present(df.columns, "mfe_pct")
    mae_col = first_present(df.columns, "mae_pct")
    partial_col = first_present(df.columns, "partial_exit_count")

    if pnl_col and strategy_col:
        path = write_csv(df, out_dir, "normalized_input.csv")
        if path:
            outputs.append(path)
        path = write_csv(
            summary_by_group(df, strategy_col, pnl_col),
            out_dir,
            "summary_by_strategy.csv",
        )
        if path:
            outputs.append(path)

    if pnl_col and exit_col:
        path = write_csv(
            summary_by_group(df, exit_col, pnl_col),
            out_dir,
            "summary_by_exit_reason.csv",
        )
        if path:
            outputs.append(path)

    if pnl_col and symbol_col:
        path = write_csv(
            summary_by_group(df, symbol_col, pnl_col).head(100),
            out_dir,
            "summary_by_symbol_top100.csv",
        )
        if path:
            outputs.append(path)

    if pnl_col and strategy_col:
        mask = df[strategy_col].astype(str).str.contains("scanner", case=False, na=False)
        path = write_csv(df.loc[mask].copy(), out_dir, "scanner_trades.csv")
        if path:
            outputs.append(path)

    if pnl_col and mfe_col:
        green_then_red = df[(df[mfe_col] >= 1.5) & (df[pnl_col] <= 0)].copy()
        path = write_csv(green_then_red, out_dir, "green_then_red_mfe_ge_1_5.csv")
        if path:
            outputs.append(path)

    if pnl_col:
        big_winners = df[df[pnl_col] >= 50].copy().sort_values(pnl_col, ascending=False)
        path = write_csv(big_winners, out_dir, "big_winners_ge_50.csv")
        if path:
            outputs.append(path)

    if pnl_col and partial_col:
        partials = df[df[partial_col].fillna(0) > 0].copy()
        path = write_csv(partials, out_dir, "trades_with_partials.csv")
        if path:
            outputs.append(path)

    if pnl_col and mfe_col and mae_col:
        cols = [c for c in [strategy_col, symbol_col, pnl_col, mfe_col, mae_col, exit_col] if c]
        audit = df[cols].copy().sort_values(mfe_col, ascending=False)
        path = write_csv(audit, out_dir, "mfe_mae_audit.csv")
        if path:
            outputs.append(path)

    return outputs


def read_output_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def write_combined_csv(outputs: list[Path], out_dir: Path) -> Path | None:
    """Write one Calc-friendly CSV with labeled sections."""
    report_paths = [p for p in outputs if p.name != "normalized_input.csv"]
    if not report_paths:
        return None

    path = out_dir / "combined_report.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        for idx, csv_path in enumerate(report_paths):
            title, desc = SECTION_TITLES.get(csv_path.name, (csv_path.stem, ""))
            section = read_output_csv(csv_path)
            if idx:
                f.write("\n\n")
            pd.DataFrame([[title], [desc]]).to_csv(f, index=False, header=False)
            section.to_csv(f, index=False)
    return path


def write_combined_html(
    df: pd.DataFrame,
    outputs: list[Path],
    out_dir: Path,
    source: Path,
) -> Path | None:
    """Write one readable HTML report with every useful output as a section."""
    report_paths = [p for p in outputs if p.name != "normalized_input.csv"]
    if not report_paths:
        return None

    pnl_col = first_present(df.columns, "pnl")
    strategy_col = first_present(df.columns, "strategy")
    total_pnl = float(df[pnl_col].sum()) if pnl_col else None
    wins = int((df[pnl_col] > 0).sum()) if pnl_col else None
    losses = int((df[pnl_col] <= 0).sum()) if pnl_col else None

    cards = [
        ("Source", str(source)),
        ("Rows", f"{len(df):,}"),
        ("Columns", f"{len(df.columns):,}"),
    ]
    if total_pnl is not None:
        cards.extend(
            [
                ("Total P&L", f"${total_pnl:,.2f}"),
                ("Wins / Losses", f"{wins} / {losses}"),
            ]
        )
    if strategy_col:
        cards.append(("Strategies", str(df[strategy_col].nunique(dropna=True))))

    card_html = "\n".join(
        f"<div class='card'><b>{html.escape(label)}</b><span>{html.escape(value)}</span></div>"
        for label, value in cards
    )

    sections = []
    for csv_path in report_paths:
        title, desc = SECTION_TITLES.get(csv_path.name, (csv_path.stem, ""))
        section_df = read_output_csv(csv_path)
        shown_df = section_df.head(500)
        more = ""
        if len(section_df) > len(shown_df):
            more = (
                f"<p class='note'>Showing first {len(shown_df):,} of "
                f"{len(section_df):,} rows. Open "
                f"<a href='{html.escape(csv_path.name)}'>{html.escape(csv_path.name)}</a> "
                "for the full section.</p>"
            )
        table = shown_df.to_html(index=False, classes="report-table sortable", border=0)
        sections.append(
            f"""
  <section>
    <h2>{html.escape(title)}</h2>
    <p>{html.escape(desc)}</p>
    {more}
    {table}
  </section>"""
        )

    page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Combined Trade Dump Analysis</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 28px; background: #f7f8fa; color: #17202a; }}
    h1 {{ margin-bottom: 6px; }}
    h2 {{ margin-top: 30px; border-bottom: 1px solid #d9dee7; padding-bottom: 6px; }}
    .cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0 26px; }}
    .card {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 12px 16px; min-width: 160px; }}
    .card b {{ display: block; color: #4b5563; font-size: 12px; text-transform: uppercase; margin-bottom: 6px; }}
    .card span {{ font-size: 20px; }}
    .note {{ color: #5f6b7a; font-size: 13px; }}
    table.report-table {{ border-collapse: collapse; width: 100%; background: white; font-size: 13px; }}
    .report-table th, .report-table td {{ border: 1px solid #d9dee7; padding: 6px 8px; text-align: right; }}
    .report-table th:first-child, .report-table td:first-child {{ text-align: left; }}
    .report-table th {{ background: #edf1f7; position: sticky; top: 0; cursor: pointer; user-select: none; }}
    .report-table th.sorted-asc::after {{ content: " ▲"; color: #2563eb; }}
    .report-table th.sorted-desc::after {{ content: " ▼"; color: #2563eb; }}
    section {{ margin-bottom: 36px; }}
  </style>
</head>
<body>
  <h1>Combined Trade Dump Analysis</h1>
  <p class="note">One-file reading report. Individual CSV files are still generated for filtering or deeper spreadsheet work.</p>
  <div class="cards">{card_html}</div>
  {''.join(sections)}
  <script>
    function parseCell(value) {{
      const text = String(value || '').trim();
      const cleaned = text.replace(/[$,%+,]/g, '').replace(/^\\((.*)\\)$/, '-$1');
      const number = Number(cleaned);
      if (text !== '' && Number.isFinite(number)) return {{ type: 'number', value: number }};
      const time = Date.parse(text.replace(' ', 'T'));
      if (Number.isFinite(time)) return {{ type: 'date', value: time }};
      return {{ type: 'text', value: text.toLowerCase() }};
    }}

    document.querySelectorAll('table.sortable').forEach(table => {{
      table.querySelectorAll('th').forEach((th, colIdx) => {{
        th.title = 'Click to sort';
        th.addEventListener('click', () => {{
          const tbody = table.tBodies[0];
          const rows = Array.from(tbody.rows);
          const current = th.classList.contains('sorted-asc') ? 'asc'
            : th.classList.contains('sorted-desc') ? 'desc'
            : '';
          const dir = current === 'asc' ? 'desc' : 'asc';
          table.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
          th.classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
          rows.sort((a, b) => {{
            const av = parseCell(a.cells[colIdx]?.innerText);
            const bv = parseCell(b.cells[colIdx]?.innerText);
            let cmp;
            if (av.type === bv.type && av.type !== 'text') cmp = av.value - bv.value;
            else cmp = String(av.value).localeCompare(String(bv.value));
            return dir === 'asc' ? cmp : -cmp;
          }});
          rows.forEach(row => tbody.appendChild(row));
        }});
      }});
    }});
  </script>
</body>
</html>
"""
    path = out_dir / "combined_report.html"
    path.write_text(page, encoding="utf-8")
    return path


def write_html_index(df: pd.DataFrame, outputs: list[Path], out_dir: Path, source: Path) -> Path:
    pnl_col = first_present(df.columns, "pnl")
    strategy_col = first_present(df.columns, "strategy")
    total_pnl = float(df[pnl_col].sum()) if pnl_col else None
    wins = int((df[pnl_col] > 0).sum()) if pnl_col else None
    losses = int((df[pnl_col] <= 0).sum()) if pnl_col else None

    cards = [
        ("Source", str(source)),
        ("Rows", f"{len(df):,}"),
        ("Columns", f"{len(df.columns):,}"),
    ]
    if total_pnl is not None:
        cards.extend([
            ("Total P&L", f"${total_pnl:,.2f}"),
            ("Wins / Losses", f"{wins} / {losses}"),
        ])
    if strategy_col:
        cards.append(("Strategies", str(df[strategy_col].nunique(dropna=True))))

    card_html = "\n".join(
        f"<div class='card'><b>{html.escape(label)}</b><span>{html.escape(value)}</span></div>"
        for label, value in cards
    )
    links = "\n".join(
        f"<li><a href='{html.escape(path.name)}'>{html.escape(path.name)}</a></li>"
        for path in outputs
    )
    columns = ", ".join(html.escape(c) for c in df.columns)

    page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Trade Dump Analysis</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 28px; background: #f7f8fa; color: #17202a; }}
    .cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }}
    .card {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 12px 16px; min-width: 160px; }}
    .card b {{ display: block; color: #4b5563; font-size: 12px; text-transform: uppercase; margin-bottom: 6px; }}
    .card span {{ font-size: 20px; }}
    code {{ background: #eceff4; padding: 2px 5px; border-radius: 4px; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>
  <h1>Trade Dump Analysis</h1>
  <div class="cards">{card_html}</div>
  <h2>Generated Files</h2>
  <ul>{links}</ul>
  <h2>Detected Columns</h2>
  <p>{columns}</p>
</body>
</html>
"""
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a trade CSV dump.")
    parser.add_argument("csv_path", type=Path, help="CSV exported from dashboard or DB tool")
    parser.add_argument("--out", type=Path, default=None, help="Optional output directory")
    args = parser.parse_args()

    csv_path = args.csv_path.resolve()
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or OUT_ROOT / f"{csv_path.stem}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_csv(csv_path)
    outputs = build_outputs(df, out_dir)
    combined_csv = write_combined_csv(outputs, out_dir)
    combined_html = write_combined_html(df, outputs, out_dir, csv_path)
    index = write_html_index(df, outputs, out_dir, csv_path)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {', '.join(df.columns)}")
    print(f"Output: {out_dir}")
    if combined_html:
        print(f"Open combined report: {combined_html}")
    if combined_csv:
        print(f"Open combined CSV: {combined_csv}")
    print(f"Open file index: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
