from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "trading_bot.db"


def safe_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    path.relative_to(ROOT.resolve())
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return path


def load_event(rowid: int) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM log_events WHERE rowid=?", (rowid,)).fetchone()
    if not row:
        raise SystemExit(f"log_events rowid not found: {rowid}")
    return dict(row)


def find_match(lines: list[str], term: str, prefer_line: int | None = None) -> int | None:
    matches = [i for i, line in enumerate(lines, start=1) if term and term in line]
    if not matches and term:
        fragment = term[:220]
        matches = [i for i, line in enumerate(lines, start=1) if fragment in line]
    if not matches:
        try:
            rx = re.compile(term, re.I)
            matches = [i for i, line in enumerate(lines, start=1) if rx.search(line)]
        except re.error:
            matches = []
    if not matches:
        return None
    if prefer_line:
        return min(matches, key=lambda n: abs(n - prefer_line))
    return matches[-1]


def print_context(path: Path, term: str, context: int, prefer_line: int | None = None) -> int:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    match = find_match(lines, term, prefer_line)
    if not match:
        print(f"No match found in {path}")
        return 1
    start = max(1, match - context)
    end = min(len(lines), match + context)
    print(f"{path}")
    print(f"match line {match}; showing {start}-{end}\n")
    for line_no in range(start, end + 1):
        marker = ">>" if line_no == match else "  "
        print(f"{marker} {line_no:>7}: {lines[line_no - 1]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show +/- context around a log_events row or a term in a log file."
    )
    parser.add_argument("--rowid", type=int, help="log_events rowid from DB Browser")
    parser.add_argument("--log", help="Log file path, e.g. logs/bot.log")
    parser.add_argument("--term", help="Literal or regex search term")
    parser.add_argument("-C", "--context", type=int, default=10)
    args = parser.parse_args()

    if args.rowid:
        event = load_event(args.rowid)
        path = safe_path(event["source_file"])
        term = event.get("raw_line") or event.get("message") or ""
        return print_context(path, term, args.context, event.get("line_no"))

    if not args.log or not args.term:
        parser.error("Use either --rowid OR both --log and --term")
    return print_context(safe_path(args.log), args.term, args.context)


if __name__ == "__main__":
    raise SystemExit(main())
